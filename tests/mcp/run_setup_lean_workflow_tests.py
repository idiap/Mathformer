#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native installer parity, registered tools, real PRISM compile and execution."""

from tempfile import gettempdir

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
import asyncio
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import yaml
import install_env as native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_setup_lean_workflow/workflow.yaml"
ARGV = ["--skip-python", "--with-lean"]


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(p, (ROOT / p).read_text())
        for p in sorted({r["path"] for r in document["provenance"]["sources"]})
    ]


class SetupLeanTests(unittest.TestCase):
    def test_original_entrypoint_parity_and_native_branches(self):
        oracle = dict(vars(native), __name__="original_installer")
        exec(
            compile(
                (ROOT / "tests/mcp/fixtures/setup_lean_original.py.txt").read_text(),
                "source-original.py",
                "exec",
            ),
            oracle,
        )
        for argv in (ARGV, ["--skip-python"], [*ARGV, "--skip-lean"], ["--unknown"]):
            for mode in ("success", "missing", "update_failure", "build_failure"):
                observed = []
                for main in (oracle["main"], native.main):
                    calls = []

                    def compiler(command, **kw):
                        self.assertEqual(kw, dict(cwd=native.ROOT_DIR, check=True))
                        calls.append(command)
                        if mode == command[1] + "_failure":
                            raise subprocess.CalledProcessError(7, command)
                        return subprocess.CompletedProcess(command, 0)

                    output, error = io.StringIO(), io.StringIO()
                    with (
                        patch.object(sys, "argv", ["install_env.py", *argv]),
                        patch.object(
                            native.shutil,
                            "which",
                            return_value=(
                                None
                                if mode == "missing"
                                else str(
                                    Path(gettempdir())
                                    / "mathformer-test-fixtures/fixture/lake"
                                )
                            ),
                        ),
                        patch.object(native.subprocess, "run", compiler),
                        redirect_stdout(output),
                        redirect_stderr(error),
                    ):
                        try:
                            code = main()
                        except SystemExit as exc:
                            code = ("SystemExit", str(exc.code))
                        except subprocess.CalledProcessError as exc:
                            code = ("failed", exc.returncode)
                    # argparse uses the same docstring and argv in both modules.
                    observed.append((code, output.getvalue(), error.getvalue(), calls))
                self.assertEqual(*observed)
                if argv == ARGV:
                    expected = {
                        "success": 2,
                        "missing": 0,
                        "update_failure": 1,
                        "build_failure": 2,
                    }[mode]
                    self.assertEqual(len(observed[0][3]), expected)
                    self.assertEqual(
                        "Environment setup complete." in observed[0][1],
                        mode == "success",
                    )
        with patch.object(native.sys, "version_info", (3, 9)):
            with self.assertRaisesRegex(SystemExit, "3.10"):
                native.initialize(ARGV)

    def test_real_registered_tools_and_lunar_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/setup-lean.workflow.json"
                ).read_text()
            ),
        )
        self.assertEqual(document["id"], "hub_setup_lean_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            dict(wall_time_seconds=3600, max_operation_calls=5),
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

        async def allow():
            pass

        for mode, count, launched in [
            ("success", 5, 2),
            ("missing", 2, 0),
            ("update_failure", 3, 1),
            ("build_failure", 4, 2),
            ("launch_error", 3, 1),
            ("readonly", 3, 0),
            ("write_denied", 3, 0),
        ]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manager = SessionManager()
                failure = None
                async with manager.open(
                    "setup-lean",
                    StdioConfig(
                        command=sys.executable,
                        args=[
                            "-B",
                            str(ROOT / "tests/mcp/fixtures/setup_lean_server.py"),
                            mode,
                            str(root),
                        ],
                        cwd=str(ROOT),
                    ),
                    {},
                ) as remote:
                    try:
                        tools = [
                            t.model_dump(by_alias=True, exclude_none=True)
                            for t in await remote.tools()
                        ]

                        def compiled(doc):
                            assets = snapshot(doc)
                            workflow = compile_workflow(
                                "mcp:setup-lean",
                                workflow_documents([DESCRIPTOR], assets)[0],
                                tools,
                            )
                            self.assertTrue(
                                workflow["runnable"], workflow["diagnostics"]
                            )
                            self.assertTrue(workflow["runtime_source"])
                            self.assertEqual(
                                set(workflow["bindings"]), set(doc["operations"])
                            )
                            return workflow, assets

                        workflow, assets = compiled(document)
                        inputs = dict(argv=ARGV, allow_mutating=True)
                        result = await execute(workflow, assets, inputs, remote, allow)
                        self.assertEqual(len(result["calls"]), count, result)
                        ledger = root / "calls.jsonl"
                        commands = (
                            [
                                json.loads(line)
                                for line in ledger.read_text().splitlines()
                            ]
                            if ledger.exists()
                            else []
                        )
                        self.assertEqual(
                            commands,
                            [
                                [
                                    str(
                                        Path(gettempdir())
                                        / "mathformer-test-fixtures/fixture/lake"
                                    ),
                                    x,
                                ]
                                for x in ["update", "build"][:launched]
                            ],
                        )
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]],
                            list(document["operations"])[:count],
                        )
                        if mode == "success":
                            self.assertEqual(result["status"], "accepted", result)
                            self.assertEqual(result["outputs"], {"exit_code": 0})
                        else:
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(result["calls"][-1]["status"], "rejected")
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        if mode == "success":
                            denied = await execute(
                                workflow,
                                assets,
                                {**inputs, "allow_mutating": False},
                                remote,
                                allow,
                            )
                            self.assertEqual(denied["status"], "failed", denied)
                            self.assertEqual(len(denied["calls"]), 3)
                            with self.assertRaises(ExecutionRejected):
                                await execute(
                                    workflow,
                                    assets,
                                    {**inputs, "argv": [*ARGV, "--skip-lean"]},
                                    remote,
                                    allow,
                                )
                            bounded = deepcopy(document)
                            bounded["policy"]["limits"]["max_operation_calls"] = 2
                            w, a = compiled(bounded)
                            exhausted = await execute(w, a, inputs, remote, allow)
                            self.assertEqual(exhausted["status"], "failed", exhausted)
                            self.assertIn("budget", json.dumps(exhausted).lower())
                            self.assertEqual(
                                sum(
                                    bool(c.get("transport_call_performed"))
                                    for c in exhausted["calls"]
                                ),
                                2,
                            )
                            self.assertEqual(len(ledger.read_text().splitlines()), 2)
                            missing = deepcopy(document)
                            missing["operations"]["build"]["execution"]["binding"][
                                "target"
                            ] = "missing_setup_lean_tool"
                            rejected = compile_workflow(
                                "mcp:setup-lean",
                                workflow_documents([DESCRIPTOR], snapshot(missing))[0],
                                tools,
                            )
                            self.assertFalse(rejected["runnable"])
                            timed = deepcopy(document)
                            timed["policy"]["limits"]["wall_time_seconds"] = 1
                            w, a = compiled(timed)

                            async def stall():
                                await asyncio.Event().wait()

                            with self.assertRaises(TimeoutError):
                                await execute(w, a, inputs, remote, stall)
                    except Exception as exc:
                        failure = exc
                self.assertFalse(manager.active)
                if failure is not None:
                    raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
