#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native/MCP/real Lunar PRISM parity with a deterministic Lake boundary only."""

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
from contextlib import asynccontextmanager
import asyncio
from copy import deepcopy
import hashlib
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import yaml
import mathformer as hub
from lean_build_tools import wire
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

BASE = "skills/control/workflow-contract-validator/references/normalized-workflows/"
DESCRIPTOR = BASE + "hub/hub_lean_build_workflow/workflow.yaml"
CONTEXT = dict(
    dry_run=False,
    json_output=False,
    keep_going=False,
    allow_mutating=False,
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

    paths = {row["path"] for row in document["provenance"]["sources"]} | {
        BASE + "hub-interface.schema.json",
        BASE + "lean-build-interface.schema.json",
    }
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(p, (ROOT / p).read_text()) for p in sorted(paths)
    ]


@asynccontextmanager
async def session(manager, config):
    failure = None
    async with manager.open("lean-build", config, {}) as remote:
        try:
            yield remote
        except Exception as exc:
            failure = exc
    if failure is not None:
        raise failure


class LeanBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )

    def test_original_entrypoint_parity(self):
        # Frozen original entrypoints execute the same external compiler fixture.
        original = dict(vars(hub))
        exec(
            compile(
                (ROOT / "tests/mcp/fixtures/lean_build_original.py.txt").read_text(),
                "source-original.py",
                "exec",
            ),
            original,
        )
        for mode in ("success", "nonzero", "timeout", "launch_error"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                for name in ("lakefile.toml", "lean-toolchain"):
                    (root / name).touch()
                calls = []

                def compiler(argv, **kw):
                    calls.append((argv, kw))
                    self.assertEqual(argv, ["lake", "build"])
                    self.assertEqual(
                        kw,
                        dict(
                            cwd=root,
                            text=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=1200,
                        ),
                    )
                    if mode == "timeout":
                        raise subprocess.TimeoutExpired(
                            argv, 1200, output=b"partial\xff", stderr=b"err"
                        )
                    if mode == "launch_error":
                        raise OSError("launch")
                    return subprocess.CompletedProcess(
                        argv, 2 if mode == "nonzero" else 0, "compiled", "diagnostic"
                    )

                original["REPO_ROOT"] = root
                with (
                    patch.object(hub, "REPO_ROOT", root),
                    patch.object(
                        hub.shutil,
                        "which",
                        return_value=str(
                            Path(gettempdir()) / "mathformer-test-fixtures/fixture/lake"
                        ),
                    ),
                    patch.object(hub.subprocess, "run", compiler),
                ):
                    for context, extra, seen in (
                        (CONTEXT, [], None),
                        ({**CONTEXT, "dry_run": True}, [], None),
                        (CONTEXT, ["bad"], None),
                        (CONTEXT, [], {"lean:build"}),
                    ):
                        outputs = []
                        for run in (original["run_action"], hub.run_action):
                            try:
                                outputs.append(
                                    run(
                                        "lean:build",
                                        hub.build_registry(),
                                        hub.RunContext(**context),
                                        extra_args=extra,
                                        seen=seen,
                                    )
                                )
                            except OSError as exc:
                                outputs.append(type(exc).__name__)
                        self.assertEqual(outputs[0], outputs[1])
                self.assertEqual(len(calls), 2)

    def test_registered_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        self.assertEqual(self.document["id"], "hub_lean_build_workflow")
        self.assertEqual(
            self.document["policy"]["limits"],
            dict(wall_time_seconds=3600, max_operation_calls=4),
        )
        for row in self.document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

        async def allow():
            pass

        cases = [
            ("success", {}, [], [], 4),
            ("nonzero", {}, [], [], 4),
            ("timeout", {}, [], [], 4),
            ("write", {}, [], [], 4),
            ("timeout_write", {}, [], [], 4),
            ("launch_error", {}, [], [], 3),
            ("missing_tool", {}, [], [], 3),
            ("missing_path", {}, [], [], 3),
            ("success", {"dry_run": True}, [], [], 3),
            ("success", {"dry_run": True}, ["bad"], [], 3),
            ("success", {}, [], ["lean:build"], 2),
        ]
        for mode, context, extra, seen, count in cases:
            with (
                self.subTest(mode=mode, context=context, extra=extra, seen=seen),
                tempfile.TemporaryDirectory() as temp,
            ):
                root = Path(temp) / "repo"
                root.mkdir()
                for name in ("lakefile.toml", "lean-toolchain"):
                    if mode != "missing_path":
                        (root / name).touch()
                manager = SessionManager()
                async with session(
                    manager,
                    StdioConfig(
                        command=sys.executable,
                        args=[
                            "-B",
                            str(ROOT / "tests/mcp/fixtures/lean_build_server.py"),
                            mode,
                            str(root),
                        ],
                        cwd=str(ROOT),
                    ),
                ) as remote:
                    inventory = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compiled(doc):
                        assets = snapshot(doc)
                        workflow = compile_workflow(
                            "mcp:lean-build",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            inventory,
                        )
                        self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                        self.assertTrue(workflow["runtime_source"])
                        self.assertEqual(
                            set(workflow["bindings"]), set(doc["operations"])
                        )
                        return workflow, assets

                    workflow, assets = compiled(self.document)
                    inputs = dict(
                        context={**CONTEXT, **context}, extra_args=extra, seen=seen
                    )
                    result = await execute(workflow, assets, inputs, remote, allow)
                    self.assertEqual(len(result["calls"]), count, result)
                    ledger = root.parent / "launches.txt"
                    self.assertEqual(
                        len(ledger.read_text().splitlines()) if ledger.exists() else 0,
                        1 if count == 4 or mode == "launch_error" else 0,
                    )
                    if mode == "launch_error":
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertFalse(
                            any(c["operation"] == "audit" for c in result["calls"])
                        )
                        continue
                    self.assertEqual(result["status"], "accepted", result)
                    payload = result["outputs"]["result"]
                    if seen:
                        self.assertEqual(
                            payload,
                            dict(
                                ok=False,
                                status="dependency_cycle",
                                action_id="lean:build",
                                cycle=["lean:build"],
                            ),
                        )
                    elif mode in ("missing_tool", "missing_path") or extra:
                        self.assertFalse(payload["ok"])
                        self.assertTrue(payload["preflight_errors"])
                        self.assertNotIn("status", payload)
                    elif context:
                        self.assertEqual(payload["status"], "dry_run")
                        self.assertTrue(payload["ok"])
                    else:
                        self.assertEqual(payload["argv"], ["lake", "build"])
                        self.assertEqual(payload["action"]["timeout_seconds"], 1200)
                        self.assertEqual(
                            payload["status"],
                            (
                                "undeclared_writes"
                                if "write" in mode
                                else "timeout" if mode == "timeout" else "completed"
                            ),
                        )
                        self.assertEqual(payload["ok"], mode == "success")
                        self.assertEqual(
                            payload["returncode"],
                            (
                                None
                                if mode.startswith("timeout")
                                else 2 if mode == "nonzero" else 0
                            ),
                        )
                        self.assertEqual(
                            payload["write_audit"]["unexpected_paths"],
                            ["unexpected.txt"] if "write" in mode else [],
                        )
                        if mode == "timeout":
                            self.assertEqual(
                                wire(payload, decode=True)["stdout"], b"partial\xff"
                            )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    if mode == "success" and not context and not seen:
                        # Exhaustion must stop before launch, without retry or audit.
                        budget = deepcopy(self.document)
                        budget["policy"]["limits"]["max_operation_calls"] = 2
                        w, a = compiled(budget)
                        limited = await execute(w, a, inputs, remote, allow)
                        self.assertEqual(limited["status"], "failed", limited)
                        self.assertIsNone(limited["outputs"])
                        self.assertIn("budget", json.dumps(limited).lower())
                        self.assertEqual(len(ledger.read_text().splitlines()), 1)
                        missing = deepcopy(self.document)
                        missing["operations"]["launch"]["execution"]["binding"][
                            "target"
                        ] = "unregistered"
                        rejected = compile_workflow(
                            "mcp:lean-build",
                            workflow_documents([DESCRIPTOR], snapshot(missing))[0],
                            inventory,
                        )
                        self.assertFalse(rejected["runnable"])
                        timed = deepcopy(self.document)
                        timed["policy"]["limits"]["wall_time_seconds"] = 1
                        w, a = compiled(timed)

                        async def stall():
                            await asyncio.Event().wait()

                        with self.assertRaises(TimeoutError):
                            await execute(w, a, inputs, remote, stall)
                self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
