#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real registered MCP tools and PRISM execution with offline external uv only."""

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
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]
import asyncio
from copy import deepcopy
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import shutil
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
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_setup_sympy_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTEXT = dict(
    dry_run=False,
    json_output=True,
    keep_going=False,
    allow_mutating=True,
    write_report=False,
)


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    paths = {SCHEMA, *[r["path"] for r in document["provenance"]["sources"]]}
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(p, (ROOT / p).read_text()) for p in sorted(paths)
    ]


class SetupTests(unittest.TestCase):
    def test_original_main_parity(self):
        oracle = dict(vars(native), __name__="original_installer")
        exec(
            compile(
                (ROOT / "tests/mcp/fixtures/setup_sympy_original.py.txt").read_text(),
                "source-original.py",
                "exec",
            ),
            oracle,
        )
        for mode in (
            "success",
            "venv_failure",
            "pip_failure",
            "missing_python",
            "missing_uv",
        ):
            observed = []
            for main in (oracle["main"], native.main):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    calls = []

                    def run(command, **kw):
                        self.assertEqual(kw, dict(cwd=None, check=True))
                        calls.append([s.replace(str(root), "<root>") for s in command])
                        if command[1] == "venv" and mode != "missing_python":
                            p = native.venv_python(root / ".venv")
                            p.parent.mkdir(parents=True)
                            p.touch()
                        if (command[1] == "venv" and mode == "venv_failure") or (
                            command[1] == "pip" and mode == "pip_failure"
                        ):
                            raise subprocess.CalledProcessError(7, command)

                    stream, error = io.StringIO(), io.StringIO()
                    # The backup's functions resolve globals in their own dictionary.
                    old = oracle["ROOT_DIR"]
                    oracle["ROOT_DIR"] = root
                    with (
                        patch.object(native, "ROOT_DIR", root),
                        patch.dict(os.environ, {"VENV_PATH": str(root / ".venv")}),
                        patch.object(sys, "argv", ["install_env.py", "--with-sympy"]),
                        patch.object(
                            native.shutil,
                            "which",
                            return_value=(
                                None
                                if mode == "missing_uv"
                                else str(
                                    Path(gettempdir())
                                    / "mathformer-test-fixtures/fixture/uv"
                                )
                            ),
                        ),
                        patch.object(native.subprocess, "run", run),
                        redirect_stdout(stream),
                        redirect_stderr(error),
                    ):
                        try:
                            outcome = main()
                        except SystemExit as exc:
                            outcome = ("SystemExit", str(exc))
                        except subprocess.CalledProcessError as exc:
                            outcome = ("CalledProcessError", exc.returncode)
                    oracle["ROOT_DIR"] = old
                    observed.append(
                        (
                            str(outcome).replace(str(root), "<root>"),
                            stream.getvalue().replace(str(root), "<root>"),
                            error.getvalue(),
                            calls,
                        )
                    )
            self.assertEqual(*observed)
            self.assertEqual(
                len(observed[0][3]),
                {
                    "success": 2,
                    "venv_failure": 1,
                    "pip_failure": 2,
                    "missing_python": 1,
                    "missing_uv": 0,
                }[mode],
            )
            self.assertEqual(
                "Environment setup complete." in observed[0][1], mode == "success"
            )
        with patch.object(native.sys, "version_info", (3, 9)):
            with self.assertRaisesRegex(SystemExit, "3.10"):
                native.initialize(["--with-sympy"])

    def test_registered_mcp_and_lunar(self):
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
                    / "skills/control/workflow-contract-validator/references/setup-sympy.workflow.json"
                ).read_text()
            ),
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            dict(wall_time_seconds=3600, max_operation_calls=4),
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        for mode in (
            "success",
            "missing_uv",
            "missing_script",
            "venv_failure",
            "missing_python",
            "pip_failure",
            "launch_failure",
            "undeclared_write",
            "readonly",
            "write_denied",
        ):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                parent = Path(directory)
                root = parent / "repository"
                root.mkdir()
                (root / "scripts").mkdir()
                (parent / "bin").mkdir()
                (parent / "empty").mkdir()
                if mode != "missing_script":
                    shutil.copy(
                        ROOT / "scripts/install_env.py", root / "scripts/install_env.py"
                    )
                uv = parent / "bin/uv"
                uv.write_text(
                    "#!"
                    + sys.executable
                    + "\n"
                    + (ROOT / "tests/mcp/fixtures/setup_sympy_uv.py").read_text()
                )
                uv.chmod(0o755)
                manager = SessionManager()
                failure = None
                async with manager.open(
                    "setup",
                    StdioConfig(
                        command=sys.executable,
                        args=[
                            "-B",
                            str(ROOT / "tests/mcp/fixtures/setup_sympy_server.py"),
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

                        def compile_doc(doc, inventory=None):
                            assets = snapshot(doc)
                            w = compile_workflow(
                                "mcp:setup",
                                workflow_documents([DESCRIPTOR], assets)[0],
                                tools if inventory is None else inventory,
                            )
                            return w, assets

                        workflow, assets = compile_doc(document)
                        self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                        self.assertTrue(workflow["runtime_source"])
                        self.assertEqual(
                            set(workflow["bindings"]), set(document["operations"])
                        )
                        self.assertFalse(compile_doc(document, [])[0]["runnable"])

                        async def authorize():
                            pass

                        async def run(context=None, extra=None, doc=None):
                            w, a = compile_doc(doc) if doc else (workflow, assets)
                            return await execute(
                                w,
                                a,
                                dict(
                                    context=context or CONTEXT, extra_args=extra or []
                                ),
                                remote,
                                authorize,
                            )

                        result = await run()
                        ledger = root / ".venv/commands.jsonl"
                        commands = (
                            [json.loads(s) for s in ledger.read_text().splitlines()]
                            if ledger.exists()
                            else []
                        )
                        if mode in ("readonly", "write_denied"):
                            self.assertEqual(result["status"], "failed", result)
                            self.assertEqual(len(result["calls"]), 2)
                            self.assertEqual(commands, [])
                            continue
                        self.assertEqual(result["status"], "accepted", result)
                        payload = result["outputs"]["result"]
                        if mode in ("missing_uv", "missing_script"):
                            self.assertFalse(payload["ok"])
                            self.assertTrue(payload["preflight_errors"])
                            self.assertEqual(commands, [])
                            self.assertEqual(len(result["calls"]), 2)
                            continue
                        self.assertEqual(len(result["calls"]), 3)
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]],
                            ["prepare_boundary", "launch_installer", "audit_result"],
                        )
                        self.assertEqual(
                            commands[0],
                            ["run", "python", "scripts/install_env.py", "--with-sympy"],
                        )
                        self.assertEqual(
                            len(commands),
                            {
                                "success": 3,
                                "undeclared_write": 3,
                                "venv_failure": 2,
                                "missing_python": 2,
                                "pip_failure": 3,
                                "launch_failure": 1,
                            }[mode],
                        )
                        self.assertEqual(
                            payload["returncode"],
                            {
                                "success": 0,
                                "undeclared_write": 0,
                                "venv_failure": 1,
                                "missing_python": 1,
                                "pip_failure": 1,
                                "launch_failure": 9,
                            }[mode],
                        )
                        self.assertEqual(payload["ok"], mode == "success")
                        self.assertEqual(
                            "Environment setup complete." in payload["stdout"],
                            mode in ("success", "undeclared_write"),
                        )
                        self.assertEqual(
                            payload["write_audit"]["ok"], mode != "undeclared_write"
                        )
                        if mode == "undeclared_write":
                            self.assertEqual(payload["status"], "undeclared_writes")
                        if len(commands) == 3:
                            self.assertEqual(
                                commands[2][4:], ["sympy>=1.12,<2", "numpy>=1.26,<3"]
                            )
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        if mode == "success":
                            self.assertIn(
                                "Lean setup not requested.", payload["stdout"]
                            )
                            self.assertIn("fixture pip output", payload["stdout"])
                            baseline = ledger.read_text()
                            for context, extra in [
                                (
                                    {
                                        **CONTEXT,
                                        "dry_run": True,
                                        "allow_mutating": False,
                                    },
                                    [],
                                ),
                                ({**CONTEXT, "allow_mutating": False}, []),
                                (CONTEXT, ["--with-lean"]),
                            ]:
                                stopped = await run(context, extra)
                                self.assertEqual(stopped["status"], "accepted", stopped)
                                self.assertEqual(len(stopped["calls"]), 2)
                                self.assertEqual(
                                    stopped["outputs"]["result"]["ok"],
                                    context["dry_run"],
                                )
                            self.assertEqual(ledger.read_text(), baseline)
                            budget = deepcopy(document)
                            budget["policy"]["limits"]["max_operation_calls"] = 1
                            stopped = await run(doc=budget)
                            self.assertEqual(stopped["status"], "failed", stopped)
                            self.assertIn("budget", str(stopped).lower())
                            self.assertEqual(
                                sum(
                                    bool(c.get("transport_call_performed"))
                                    for c in stopped["calls"]
                                ),
                                1,
                            )
                            self.assertEqual(ledger.read_text(), baseline)
                            timed = deepcopy(document)
                            timed["policy"]["limits"]["wall_time_seconds"] = 1
                            w, a = compile_doc(timed)

                            async def pending():
                                await asyncio.Event().wait()

                            with self.assertRaises(TimeoutError):
                                await execute(
                                    w,
                                    a,
                                    dict(context=CONTEXT, extra_args=[]),
                                    remote,
                                    pending,
                                )
                            self.assertEqual(ledger.read_text(), baseline)
                            prepared = await remote.call(
                                "mathformer_setup_sympy_prepare_boundary",
                                dict(context=CONTEXT, extra_args=[]),
                            )
                            boundary = prepared["boundary"]
                            captured = await remote.call(
                                "mathformer_setup_sympy_launch_installer",
                                dict(boundary=boundary),
                            )
                            with self.assertRaises(ValueError):
                                await remote.call(
                                    "mathformer_setup_sympy_launch_installer",
                                    dict(boundary=boundary),
                                )
                            tampered = deepcopy(captured["result"])
                            tampered["ok"] = False
                            with self.assertRaises(ValueError):
                                await remote.call(
                                    "mathformer_setup_sympy_audit_result",
                                    dict(boundary=boundary, result=tampered),
                                )
                            audited = await remote.call(
                                "mathformer_setup_sympy_audit_result",
                                dict(boundary=boundary, **captured),
                            )
                            self.assertTrue(audited["result"]["ok"])
                            with self.assertRaises(ValueError):
                                await remote.call(
                                    "mathformer_setup_sympy_audit_result",
                                    dict(boundary=boundary, **captured),
                                )
                    except Exception as exc:
                        failure = exc
                self.assertFalse(manager.active)
                if failure is not None:
                    raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
