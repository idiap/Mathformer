#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Backend wrapper equivalence and real MCP / Lunar / PRISM execution."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]
import asyncio
from contextlib import redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml
from backend_test_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_test_backend_workflow/workflow.yaml"


def snapshot(doc):
    def asset(path, content):
        return {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in doc["provenance"]["sources"]
    ]


class BackendTests(unittest.TestCase):
    def test_original_equivalence_and_native_states(self):
        fixture = ROOT / "tests/mcp/fixtures/backend_test_original.py.txt"
        spec = importlib.util.spec_from_loader(
            "backend_original", SourceFileLoader("backend_original", str(fixture))
        )
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        original.REPO_ROOT = ROOT
        native = source()
        cases = [
            [],
            ["--backend", "all", "--backend", "sympy", "--json", "--fail-on-warning"],
            ["--backend", "sympy", "--backend", "isabelle", "--backend", "sympy"],
            ["--backend", "physics_sympy", "--fail-on-warning"],
        ]
        for argv in cases:
            for code in [0, 3, -9]:
                observed = []

                def child(command, **kw):
                    observed.append((command, kw))
                    return code

                with (
                    patch.object(original, "subprocess", SimpleNamespace(call=child)),
                    patch.object(native, "subprocess", SimpleNamespace(call=child)),
                    patch.object(sys, "argv", ["run_backend.py", *argv]),
                ):
                    self.assertEqual(original.main(), code)
                    self.assertEqual(native.main(), code)
                self.assertEqual(observed[0], observed[1])
                self.assertEqual(observed[0][1], {"cwd": ROOT})
        for argv in [["--backend", "bad"], ["--unexpected"]]:
            with (
                patch.object(sys, "argv", ["run_backend.py", *argv]),
                redirect_stderr(io.StringIO()),
            ):
                for module in [original, native]:
                    with self.assertRaises(SystemExit) as error:
                        module.main()
                    self.assertEqual(error.exception.code, 2)
        state = native.pack(native.select_all({}))
        history = []
        for index in range(4):
            prior = deepcopy(state)
            result = native.append_family(state)
            self.assertEqual(state, prior)
            state = result["state"]
            history.append(state)
            self.assertEqual(state["index"], index + 1)
            self.assertEqual(result["done"], index == 3)
            self.assertEqual(len(state["command"]), 2 + 2 * (index + 1))
        self.assertEqual(history[0]["index"], 1)
        with self.assertRaises(IndexError):
            native.append_family(state)
        with patch.object(
            native,
            "subprocess",
            SimpleNamespace(
                call=lambda *a, **kw: (_ for _ in ()).throw(
                    OSError("compiler process unavailable")
                )
            ),
        ):
            with self.assertRaises(OSError):
                native.main()

    def test_real_registered_tools_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["id"], "hub_test_backend_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        async with manager.open(
            "backend-fixture",
            StdioConfig(
                command=sys.executable,
                args=["tests/mcp/fixtures/backend_test_server.py"],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(document, inventory=None):
                assets = snapshot(document)
                selected = workflow_documents([DESCRIPTOR], assets)[0]
                return (
                    compile_workflow(
                        "mcp:backend-fixture",
                        selected,
                        tools if inventory is None else inventory,
                    ),
                    assets,
                )

            compiled, assets = compile(doc)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
            self.assertFalse(compile(doc, [])[0]["runnable"])

            async def authorize():
                pass

            async def run(argv, document=None):
                workflow, received = (
                    compile(document) if document else (compiled, assets)
                )
                return await execute(
                    workflow, received, {"extra_args": argv}, remote, authorize
                )

            result = await run([])
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(result["outputs"], {"exit_code": 3})
            self.assertEqual(len(result["calls"]), 9)
            names = [c["tool"] for c in result["calls"]]
            self.assertEqual(
                names,
                [
                    "mathformer_backend_test_" + s
                    for s in [
                        "parse",
                        "select_all",
                        "pack",
                        *(["append_family"] * 4),
                        "finalize",
                        "launch",
                    ]
                ],
            )
            evidence = (await remote.call("backend_test_fixture_evidence", {}))[
                "launches"
            ]
            self.assertEqual(len(evidence), 1)
            first = evidence[0]
            self.assertEqual(
                [r["status"] for r in first["report"]["results"]],
                ["fail", "fail", "pass", "pass", "skip"],
            )
            self.assertEqual(
                first["report"]["summary"],
                {"fail": 2, "pass": 2, "skip": 1, "warn": 0, "total": 5},
            )
            self.assertEqual(
                [c["timeout"] for c in first["compiler_calls"]], [7, 7, 7, 120]
            )
            self.assertEqual(len(first["jsonl"].splitlines()), 5)
            self.assertIn("testsuite", first["junit"])
            self.assertIn("providers", first["dependency"])
            self.assertTrue(
                all(
                    r.get("write_audit", {}).get("ok", True)
                    for r in first["report"]["results"]
                )
            )
            self.assertTrue(result["replay_artifacts"])
            # Sorted/deduplicated branch; skips remain successful unless strict flag.
            for flags, code in [(["--json"], 0), (["--json", "--fail-on-warning"], 3)]:
                argv = ["--backend", "sympy", "--backend", "sympy", *flags]
                result = await run(argv)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"], {"exit_code": code})
                self.assertEqual(len(result["calls"]), 6)
                last = (await remote.call("backend_test_fixture_evidence", {}))[
                    "launches"
                ][-1]
                self.assertEqual(
                    last["command"][2:6],
                    ["--module-family", "sympy", "--write-jsonl", "--write-junit"],
                )
                self.assertEqual(last["command"][6:], flags)
                self.assertEqual(len(last["compiler_calls"]), 1)
                self.assertEqual(json.loads(last["stdout"]), last["report"])
                self.assertEqual(
                    last["report"]["results"][-1]["status"],
                    "skip" if code == 0 else "fail",
                )
            count = len(
                (await remote.call("backend_test_fixture_evidence", {}))["launches"]
            )
            failed = await run(["--backend", "invalid"])
            self.assertEqual(failed["status"], "failed", failed)
            self.assertEqual(len(failed["calls"]), 1)
            self.assertIsNone(failed["outputs"])
            # Real loop exhaustion stops before finalize/launch; no retry.
            bounded = deepcopy(doc)
            bounded["flow"]["steps"][3]["max_iterations"] = 3
            failed = await run([], bounded)
            self.assertEqual(failed["status"], "failed", failed)
            self.assertEqual(len(failed["calls"]), 6)
            budget = deepcopy(doc)
            budget["policy"]["limits"]["max_operation_calls"] = 8
            failed = await run([], budget)
            self.assertEqual(failed["status"], "failed", failed)
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in failed["calls"]), 8
            )
            self.assertEqual(
                len(
                    (await remote.call("backend_test_fixture_evidence", {}))["launches"]
                ),
                count,
            )
            with self.assertRaises(Exception):
                await remote.call(
                    "mathformer_backend_test_launch", {"command": ["sh", "-c", "false"]}
                )
            self.assertEqual(
                len(
                    (await remote.call("backend_test_fixture_evidence", {}))["launches"]
                ),
                count,
            )
        self.assertFalse(manager.active)
        # A child compiler launch exception traverses the actual comprehensive
        # runner and the native launch tool; no result or automatic retry follows.
        async with manager.open(
            "backend-error",
            StdioConfig(
                command=sys.executable,
                args=["tests/mcp/fixtures/backend_test_server.py", "error"],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            failed = await execute(
                compiled,
                assets,
                {"extra_args": ["--backend", "sympy"]},
                remote,
                authorize,
            )
            self.assertEqual(failed["status"], "failed", failed)
            self.assertIsNone(failed["outputs"])
            self.assertEqual(len(failed["calls"]), 6)
            self.assertEqual(failed["calls"][-1]["status"], "rejected")
            evidence = await remote.call("backend_test_fixture_evidence", {})
            self.assertEqual(len(evidence["attempts"]), 1)
            self.assertEqual(len(evidence["compiler_calls"]), 1)
            self.assertEqual(evidence["launches"], [])
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
