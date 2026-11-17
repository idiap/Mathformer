#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native parity and real MCP/Lunar PRISM compile and execution."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT),
    str(ROOT / "tests/mcp/fixtures"),
]
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
from physics_release_gate_tools import native, SOURCE
from physics_release_boundary import prepare, boundaries
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathformerphysicslib_release_gate_workflow/workflow.yaml"
MODES = (
    "success",
    "no_manifest",
    "build_fail",
    "build_timeout",
    "lean_fail",
    "lean_timeout",
    "coherence_medium",
    "coherence_high",
    "build_launch",
    "lean_launch",
)


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    descriptor = str(Path(DESCRIPTOR).parent.parent / document["id"] / "workflow.yaml")
    return [asset(descriptor, json.dumps(document))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in document["provenance"]["sources"]
    ]


@asynccontextmanager
async def session(manager, config):
    failure = None
    async with manager.open("release-gate", config, {}) as remote:
        try:
            yield remote
        except Exception as exc:
            failure = exc
    if failure:
        raise failure


def stable(payload):
    return {k: v for k, v in payload.items() if k != "generated_at_utc"}


class ReleaseTests(unittest.TestCase):
    expected_id = "hub_mathformerphysicslib_release_gate_workflow"

    @classmethod
    def setUpClass(cls):
        cls.document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )

    def test_original_parity(self):
        import types

        original = types.ModuleType("release_original")
        original.__file__ = str(SOURCE)
        exec(
            compile(
                (
                    ROOT / "tests/mcp/fixtures/physics_release_original.py.txt"
                ).read_text(),
                str(SOURCE),
                "exec",
            ),
            original.__dict__,
        )
        for mode in MODES:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                prepare(root, mode)
                outputs = []
                histories = []
                for module in (original, native):
                    calls = []
                    with boundaries(module, root, mode, calls):
                        if mode.endswith("_launch"):
                            with self.assertRaisesRegex(
                                OSError, "fixture launch failure"
                            ):
                                module.run(root / "report.json")
                            outputs.append(None)
                        else:
                            payload = module.run(root / "report.json")
                            self.assertEqual(
                                json.loads((root / "report.json").read_text()), payload
                            )
                            outputs.append(stable(payload))
                    histories.append(calls)
                self.assertEqual(outputs[0], outputs[1])
                self.assertEqual(histories[0], histories[1])
                self.assertEqual(len(histories[0]), 1 if mode == "build_launch" else 3)
        # The original CLI keeps exit semantics and prints exactly its source-owned report.
        for mode in ("success", "build_fail"):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                prepare(root, mode)
                import io
                from contextlib import redirect_stdout

                with (
                    boundaries(native, root, mode, []),
                    patch.object(
                        sys,
                        "argv",
                        ["gate", "--json", "--output", str(root / "cli.json")],
                    ),
                    redirect_stdout(io.StringIO()) as text,
                ):
                    self.assertEqual(native.main(), 0 if mode == "success" else 1)
                self.assertEqual(
                    json.loads(text.getvalue()),
                    json.loads((root / "cli.json").read_text()),
                )

    def test_registered_lunar_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = self.document
        self.assertEqual(doc["id"], self.expected_id)
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(
            doc["policy"]["limits"], dict(wall_time_seconds=3600, max_operation_calls=6)
        )
        self.assertEqual(doc["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertIn(
            "tests/physics_lean/run_mathformerphysicslib_release_gate.py",
            [r["path"] for r in doc["provenance"]["sources"]],
        )
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

        async def allow():
            pass

        for mode in MODES + ("write_error",):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                prepare(root, mode)
                manager = SessionManager()
                async with session(
                    manager,
                    StdioConfig(
                        command=sys.executable,
                        args=[
                            "-B",
                            str(ROOT / "tests/mcp/fixtures/physics_release_server.py"),
                            mode,
                            str(root),
                        ],
                        cwd=str(ROOT),
                    ),
                ) as remote:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile_doc(document):
                        assets = snapshot(document)
                        workflow = compile_workflow(
                            "mcp:release",
                            workflow_documents([assets[0]["path"]], assets)[0],
                            tools,
                        )
                        self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                        self.assertTrue(workflow["runtime_source"])
                        self.assertEqual(
                            set(workflow["bindings"]), set(document["operations"])
                        )
                        advertised = {tool["name"]: tool for tool in tools}
                        for operation in document["operations"].values():
                            tool = advertised[
                                operation["execution"]["binding"]["target"]
                            ]
                            self.assertEqual(
                                set(tool["inputSchema"]["properties"]),
                                set(operation["inputs"]),
                            )
                            self.assertEqual(
                                set(tool["inputSchema"].get("required", [])),
                                set(operation["inputs"]),
                            )
                            self.assertEqual(
                                set(tool["outputSchema"]["properties"]),
                                set(operation["outputs"]),
                            )
                        return workflow, assets

                    workflow, assets = compile_doc(doc)
                    output = root / "output/report.json"
                    if mode == "write_error":
                        output.parent.write_text("parent is a file")
                    result = await execute(
                        workflow, assets, {"output": str(output)}, remote, allow
                    )
                    count = (
                        1
                        if mode == "build_launch"
                        else 3 if mode == "lean_launch" else 6
                    )
                    self.assertEqual(len(result["calls"]), count, result)
                    commands = [
                        json.loads(line)
                        for line in (root / "commands.jsonl").read_text().splitlines()
                    ]
                    self.assertEqual(
                        [c[1] for c in commands],
                        [900] if mode == "build_launch" else [900, 180, 30],
                    )
                    if mode.endswith("_launch") or mode == "write_error":
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertFalse(output.exists())
                        continue
                    self.assertEqual(result["status"], "accepted", result)
                    payload = result["outputs"]["report"]
                    # Compare the whole native payload as well as each branch
                    # oracle. Only the native UTC generation time differs.
                    with tempfile.TemporaryDirectory() as comparison:
                        native_root = Path(comparison)
                        prepare(native_root, mode)
                        with boundaries(native, native_root, mode, []):
                            expected_payload = native.run(native_root / "native.json")
                        self.assertEqual(stable(payload), stable(expected_payload))
                    self.assertEqual(json.loads(output.read_text()), payload)
                    self.assertEqual(
                        output.read_text(),
                        json.dumps(payload, indent=2, sort_keys=True) + "\n",
                    )
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        [step["operation"] for step in doc["flow"]["steps"]],
                    )
                    expected = mode in ("success", "no_manifest")
                    self.assertEqual(payload["release_ok"], expected)
                    self.assertEqual(
                        payload["artifact_status"],
                        "promoted" if expected else "blocked",
                    )
                    self.assertEqual(
                        payload["library_status"],
                        (
                            "blocked"
                            if mode.startswith(("build_", "coherence_"))
                            else "accepted"
                        ),
                    )
                    self.assertEqual(
                        payload["terminal_states"],
                        (
                            []
                            if expected
                            else [
                                (
                                    "compile_failed"
                                    if mode.startswith("build_")
                                    else "blocked"
                                )
                            ]
                        ),
                    )
                    self.assertEqual(
                        [r["path"] for r in payload["imported_modules"]],
                        ["Fixture/A.lean"] * 2,
                    )
                    self.assertEqual(
                        payload["public_root_sha256"],
                        hashlib.sha256(
                            (root / "libraries/MathformerPhysicsLib.lean").read_bytes()
                        ).hexdigest(),
                    )
                    self.assertTrue(
                        all(
                            r["sha256"]
                            == hashlib.sha256(
                                (root / r["path"]).read_bytes()
                            ).hexdigest()
                            for r in payload["imported_modules"]
                        )
                    )
                    self.assertEqual(
                        payload["lake_manifest_sha256"],
                        (
                            None
                            if mode == "no_manifest"
                            else hashlib.sha256(
                                (root / "lake-manifest.json").read_bytes()
                            ).hexdigest()
                        ),
                    )
                    for key in ("build", "coherence", "lean_version"):
                        row = payload[key]
                        self.assertEqual(
                            row["diagnostic_sha256"],
                            hashlib.sha256(
                                (row["stdout"] + "\n" + row["stderr"]).encode()
                            ).hexdigest(),
                        )
                    if mode.endswith("_timeout"):
                        row = payload[
                            "build" if mode.startswith("build") else "lean_version"
                        ]
                        self.assertIsNone(row["returncode"])
                        self.assertTrue(row["timeout"])
                        self.assertEqual(row["stdout"], "partial\ufffd")
                        self.assertIn("timeout after", row["stderr"])
                    coherence = json.loads(payload["coherence"]["stdout"])
                    if mode.startswith("coherence_"):
                        self.assertFalse(coherence["release_ok"])
                        self.assertEqual(payload["coherence"]["returncode"], 3)
                        self.assertGreater(
                            coherence[
                                (
                                    "medium_findings"
                                    if mode.endswith("medium")
                                    else "high_findings"
                                )
                            ],
                            0,
                        )
                        self.assertGreater(coherence["repair_action_count"], 0)
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    if mode == "success":
                        budget = deepcopy(doc)
                        budget["policy"]["limits"]["max_operation_calls"] = 2
                        w, a = compile_doc(budget)
                        limited = await execute(
                            w, a, {"output": str(root / "limited.json")}, remote, allow
                        )
                        self.assertEqual(limited["status"], "failed", limited)
                        # The refused third attempt has a receipt but never
                        # reaches the server or launches the version command.
                        self.assertEqual(len(limited["calls"]), 3)
                        self.assertFalse(limited["calls"][-1]["execution_performed"])
                        self.assertFalse(
                            limited["calls"][-1].get("transport_call_performed", False)
                        )
                        self.assertIsNone(limited["outputs"])
                        self.assertFalse((root / "limited.json").exists())
                        self.assertIn("budget", json.dumps(limited).lower())
                        self.assertEqual(
                            len((root / "commands.jsonl").read_text().splitlines()), 5
                        )
                        missing = deepcopy(doc)
                        missing["operations"][doc["flow"]["steps"][0]["operation"]][
                            "execution"
                        ]["binding"]["target"] = "absent_tool"
                        bad_assets = snapshot(missing)
                        bad = compile_workflow(
                            "mcp:release",
                            workflow_documents([bad_assets[0]["path"]], bad_assets)[0],
                            tools,
                        )
                        self.assertFalse(bad["runnable"])
                        timed = deepcopy(doc)
                        timed["policy"]["limits"]["wall_time_seconds"] = 1
                        w, a = compile_doc(timed)

                        async def stall():
                            await asyncio.Event().wait()

                        with self.assertRaises(TimeoutError):
                            await execute(
                                w,
                                a,
                                {"output": str(root / "timed.json")},
                                remote,
                                stall,
                            )
                self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
