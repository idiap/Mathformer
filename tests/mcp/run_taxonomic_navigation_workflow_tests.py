#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native taxonomy fixtures through production MCP, real PRISM and Lunar runtime.

This workflow has no provider or external compiler boundary to substitute.
"""

from tempfile import gettempdir

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
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
from taxonomic_navigation_tools import source, path_for
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_meta_skills_taxonomic_navigation_workflow/workflow.yaml"


def row(identity, fields=None):
    return {
        "workflow_id": identity,
        "task_id": identity + "-task",
        "reasoning_types": fields or ["grounding"],
        "object_domains": [],
        "backend_families": [],
        "risk_classes": [],
    }


def fixture(cases):
    return {
        "workflow_coordinates": [
            row("z"),
            row("a"),
            row(
                "physics_lean.goal_sample.recursive_autoformalization",
                ["pathology_repair"],
            ),
        ],
        "navigation_examples": cases,
    }


def case(request="mathlib", expected="a"):
    return {"request": request, "expected_workflow_id": expected}


def oracle():
    path = ROOT / "tests/mcp/fixtures/taxonomic_navigation_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "taxonomic_oracle", SourceFileLoader("taxonomic_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(doc):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in {r["path"]: r for r in doc["provenance"]["sources"]}.values()
    ]


class TaxonomyTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="taxonomy-fixture-", dir=base)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.taxonomy = self.directory / "taxonomy.json"
        self.report = self.directory / "report.json"
        self.native = source()

    def put(self, cases):
        self.taxonomy.write_text(json.dumps(fixture(cases)))

    def test_native_original_equivalence_scoring_cli_and_bounds(self):
        native, old = self.native, oracle()
        for cases in (
            [],
            [case()],
            [
                case("unmatched", "a"),
                case(),
                case(
                    "repair sample",
                    "physics_lean.goal_sample.recursive_autoformalization",
                ),
            ],
        ):
            self.put(cases)
            with (
                patch.object(native, "TAXONOMY_PATH", self.taxonomy),
                patch.object(native, "REPORT_PATH", self.report),
                patch.object(old, "TAXONOMY_PATH", self.taxonomy),
                patch.object(old, "REPORT_PATH", self.directory / "old.json"),
            ):
                self.assertEqual(native.self_test(), old.self_test())
                self.assertEqual(
                    self.report.read_bytes(), (self.directory / "old.json").read_bytes()
                )
                for args in (
                    ["--self-test", "--json", "--request", "unmatched"],
                    ["--self-test"],
                    ["--request", "mathlib", "--json"],
                ):
                    with (
                        patch.object(sys, "argv", ["navigate", *args]),
                        redirect_stdout(io.StringIO()) as actual,
                    ):
                        code = native.main()
                    with (
                        patch.object(sys, "argv", ["navigate", *args]),
                        redirect_stdout(io.StringIO()) as expected,
                    ):
                        old_code = old.main()
                    self.assertEqual(
                        (code, actual.getvalue()), (old_code, expected.getvalue())
                    )
                with (
                    patch.object(sys, "argv", ["navigate"]),
                    self.assertRaises(SystemExit),
                ):
                    native.main()
            for request in ("mathlib", "repair", "repair sample", "a task", "zzzz"):
                self.assertEqual(
                    native.navigate(request, self.taxonomy),
                    self._old_navigate(old, request),
                )
        self.assertEqual(
            native.score_request(
                "repair",
                row(
                    "physics_lean.goal_sample.recursive_autoformalization",
                    ["pathology_repair"],
                ),
            ),
            (0, []),
        )
        self.assertEqual(
            native.score_request("grounding", row("a")), (4, ["grounding"])
        )
        # Exact specialization boundary terminates at its final case; no truncation.
        self.put([case()] * 10000)
        state = native.initialize(self.taxonomy)
        result = native.evaluate_case(state)
        for _ in range(10000):
            state = native.advance(state, result)
        self.assertEqual((state["index"], len(state["results"])), (10000, 10000))
        self.assertTrue(native.finalize(state, self.report)["ok"])
        self.put([])
        state = native.initialize(self.taxonomy)
        blocked = self.directory / "blocker"
        blocked.write_text("file")
        with self.assertRaises(OSError):
            native.finalize(state, blocked / "report.json")
        self.taxonomy.write_text("{")
        with self.assertRaises(json.JSONDecodeError):
            native.initialize(self.taxonomy)
        with self.assertRaises(ValueError):
            path_for(str(Path(gettempdir()) / "outside.json"), native.REPORT_PATH)

    def _old_navigate(self, old, request):
        with patch.object(old, "TAXONOMY_PATH", self.taxonomy):
            return old.navigate(request)

    def test_registered_mcp_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["id"], "hub_meta_skills_taxonomic_navigation_workflow"
        )
        for r in document["provenance"]["sources"]:
            self.assertEqual(
                r["digest"],
                "sha256:" + hashlib.sha256((ROOT / r["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from taxonomic_navigation_tools import main;main()'
        async with manager.open(
            "taxonomy",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=tools):
                assets = snapshot(doc)
                workflow = workflow_documents([DESCRIPTOR], assets)[0]
                return compile_workflow("mcp:taxonomy", workflow, inventory), assets

            compiled, assets = compile(document)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
            self.assertFalse(compile(document, [])[0]["runnable"])

            async def authorize():
                pass

            async def run(doc=None, path=None):
                selected, received = compile(doc) if doc else (compiled, assets)
                return await execute(
                    selected,
                    received,
                    {
                        "taxonomy": str(self.taxonomy),
                        "report_path": str(path or self.report),
                    },
                    remote,
                    authorize,
                )

            for cases in ([], [case()], [case("unmatched", "a"), case()]):
                self.put(cases)
                expected = self.native.finalize(
                    self._native_state(), self.directory / "expected.json"
                )
                result = await run()
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"],
                    {
                        "report": expected,
                        "exit_code": 0 if expected["ok"] else 1,
                        "stdout": json.dumps(expected, indent=2, sort_keys=True) + "\n",
                    },
                )
                self.assertEqual(json.loads(self.report.read_text()), expected)
                names = [c["tool"] for c in result["calls"]]
                middle = (
                    ["empty_state"]
                    if not cases
                    else ["evaluate_case", "advance"] * len(cases)
                )
                self.assertEqual(
                    names,
                    [
                        "mathformer_taxonomic_" + n
                        for n in ["initialize", *middle, "finalize", "finish_cli"]
                    ],
                )
                self.assertTrue(result["runtime"]["effect_records"])
            # Native reread semantics: loaded examples persist while coordinates change.
            self.put([case()])
            state = (
                await remote.call(
                    "mathformer_taxonomic_initialize", {"taxonomy": str(self.taxonomy)}
                )
            )["state"]
            updated = fixture([])
            updated["workflow_coordinates"] = [row("replacement")]
            self.taxonomy.write_text(json.dumps(updated))
            evaluated = await remote.call(
                "mathformer_taxonomic_evaluate_case", {"state": state}
            )
            self.assertEqual(
                evaluated["result"],
                {
                    "request": "mathlib",
                    "expected": "a",
                    "got": "replacement",
                    "ok": False,
                },
            )
            advanced = await remote.call(
                "mathformer_taxonomic_advance",
                {"state": state, "result": evaluated["result"]},
            )
            self.assertTrue(advanced["done"])
            self.assertEqual(advanced["state"]["index"], 1)
            self.assertEqual(state["results"], [])
            # Lower descriptor bound: final permitted iteration succeeds, overflow fails
            # after two evaluations, before writing or CLI completion.
            bounded = deepcopy(document)
            bounded["flow"]["steps"][1]["max_iterations"] = 2
            self.put([case()] * 2)
            self.assertEqual((await run(bounded))["status"], "accepted")
            self.put([case()] * 3)
            self.report.unlink()
            failed = await run(bounded)
            self.assertEqual(failed["status"], "failed", failed)
            self.assertEqual(len(failed["calls"]), 5)
            self.assertFalse(self.report.exists())
            # Actual decode/read and write errors propagate at the native step.
            self.taxonomy.write_text("{")
            failed = await run()
            self.assertEqual(failed["status"], "failed")
            self.assertEqual(len(failed["calls"]), 1)
            self.taxonomy.unlink()
            self.assertEqual((await run())["status"], "failed")
            self.put([case()])
            blocked = self.directory / "blocked"
            blocked.write_text("file")
            failed = await run(path=blocked / "report.json")
            self.assertEqual(failed["status"], "failed")
            self.assertEqual(len(failed["calls"]), 4)
            self.assertEqual(failed["calls"][-1]["status"], "rejected")
            self.put([case()] * 10001)
            failed = await run()
            self.assertEqual(failed["status"], "failed")
            self.assertEqual(len(failed["calls"]), 1)
            self.put([case()])
            budget = deepcopy(document)
            budget["policy"]["limits"]["max_operation_calls"] = 2
            failed = await run(budget)
            self.assertEqual(failed["status"], "failed")
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in failed["calls"]), 2
            )
        self.assertFalse(manager.active)

    def _native_state(self):
        state = self.native.initialize(self.taxonomy)
        for _ in state["cases"]:
            state = self.native.advance(state, self.native.evaluate_case(state))
        return state


if __name__ == "__main__":
    unittest.main(verbosity=2)
