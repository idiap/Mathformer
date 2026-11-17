#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real filesystem fixtures, registered MCP tools, Lunar compilation and PRISM runtime.

No provider/model or external compiler exists in this planner. Nothing in the
PRISM parser/checker/compiler/runtime or native planner is substituted.
"""

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
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
import yaml
from coherence_repair_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathformerphysicslib_coherence_repair_plan_workflow/workflow.yaml"


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in {r["path"]: r for r in document["provenance"]["sources"]}.values()
    ]


def reports_fixture():
    kinds = [
        "concept_spread_without_foundation_owner",
        "confirmed_competing_concept_owner",
        "manifest_missing_foundations",
        "missing_foundations_index",
        "foundation_owner_not_indexed",
        "foundation_without_operable_api",
        "thin_foundation_api",
        "unknown",
        None,
    ]
    return [
        {},
        {"findings": []},
        {
            "findings": [
                {
                    "kind": k,
                    "severity": "high" if i % 2 else "low",
                    "concept_id": str(i),
                }
                for i, k in enumerate(kinds)
            ]
        },
    ]


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.native = source()
        loader = SourceFileLoader(
            "repair_original",
            str(ROOT / "tests/mcp/fixtures/coherence_repair_original.py.txt"),
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.original)

    def paths(self, reports):
        paths = []
        for i, report in enumerate(reports):
            p = self.root / f"report-{i}.json"
            p.write_text(json.dumps(report))
            paths += ["--report", str(p)]
        return paths

    def test_native_cli_equivalence_and_traversal(self):
        reports = reports_fixture()
        payload = self.native.repair_plan(reports)
        self.assertEqual(payload["action_count"], 9)
        self.assertEqual(
            [a["action"] for a in payload["actions"]],
            ["consolidate_concept_owner"] * 2
            + ["repair_integration_surface"] * 3
            + ["add_operable_bridge_api"] * 2
            + ["record_or_block_gap"] * 2,
        )
        self.assertEqual(
            [a["concept_id"] for a in payload["actions"]], [str(i) for i in range(9)]
        )
        self.assertEqual(
            [a["severity"] for a in payload["actions"]],
            [f["severity"] for f in reports[-1]["findings"]],
        )
        self.assertEqual(
            [a["source_kind"] for a in payload["actions"]],
            [f["kind"] for f in reports[-1]["findings"]],
        )
        self.assertTrue(
            all(isinstance(a["monotonicity_gate"], str) for a in payload["actions"])
        )
        argv = self.paths(reports)
        for extra in (
            [],
            ["--json"],
            ["--self-test"],
            ["--output", str(self.root / "nested/plan.json")],
        ):
            results = []
            for main in (self.original.main, self.native.main):
                stream = io.StringIO()
                with redirect_stdout(stream):
                    code = main(argv + extra)
                results.append((code, stream.getvalue()))
            self.assertEqual(*results)
            self.assertEqual(
                results[0], (0, json.dumps(payload, indent=2, sort_keys=True) + "\n")
            )
        before = deepcopy(reports)
        self.native.repair_plan(reports)
        self.assertEqual(reports, before)
        self.assertEqual(self.native.repair_plan([])["status"], "no_repairs_required")
        self.assertEqual(
            self.native.repair_plan([{"findings": [{}] * 2001}])["action_count"], 2001
        )
        for main in (self.original.main, self.native.main):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(["--invalid"])
            with self.assertRaises(FileNotFoundError):
                main(["--report", str(self.root / "absent")])
        with self.assertRaises(AttributeError):
            self.native.repair_plan([{"findings": [None]}])

    def test_default_cli_equivalence_in_filesystem_context(self):
        common = sys.modules["coherence_common"]
        names = ["REPO_ROOT", "LIB_ROOT", "LEAN_ROOT", "FOUNDATIONS_INDEX"]
        previous = {name: getattr(common, name) for name in names}
        context = [
            self.root,
            self.root / "MathformerPhysicsLib",
            self.root / "MathformerPhysicsLib/Lean",
            self.root / "MathformerPhysicsLib/Lean/Foundations.lean",
        ]
        try:
            for name, value in zip(names, context):
                setattr(common, name, value)
            for argv in ([], ["--json"], ["--self-test"], ["--self-test", "--json"]):
                observed = []
                for main in (self.original.main, self.native.main):
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        code = main(argv)
                    observed.append((code, stream.getvalue()))
                self.assertEqual(*observed)
                expected = self.native.repair_plan(
                    self.native.default_reports("--self-test" in argv, self.root)
                )
                self.assertEqual(json.loads(observed[0][1]), expected)
        finally:
            for name, value in previous.items():
                setattr(common, name, value)

    def test_registered_mcp_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_mathformerphysicslib_coherence_repair_plan_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "repair",
            StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=["-c", server],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=tools):
                received = assets(doc)
                w = compile_workflow(
                    "mcp:repair",
                    workflow_documents([DESCRIPTOR], received)[0],
                    inventory,
                )
                return w, received

            w, a = compile(document)
            self.assertTrue(w["runnable"], w["diagnostics"])
            self.assertTrue(w["runtime_source"])
            self.assertEqual(set(w["bindings"]), set(document["operations"]))
            self.assertFalse(compile(document, [])[0]["runnable"])

            async def allow():
                pass

            async def run(argv, doc=document):
                compiled, received = compile(doc) if doc is not document else (w, a)
                return await execute(
                    compiled,
                    received,
                    {"argv": argv, "repository_root": str(self.root)},
                    remote,
                    allow,
                )

            for reports in ([], reports_fixture(), [{"findings": [{}] * 2001}]):
                # A supplied empty report takes the native supplied-reports branch.
                argv = self.paths(reports or [{}])
                output = self.root / "out.json"
                result = await run(argv + ["--output", str(output)])
                self.assertEqual(result["status"], "accepted", result)
                expected = self.native.repair_plan(reports)
                self.assertEqual(
                    result["outputs"], {"payload": expected, "exit_code": 0}
                )
                self.assertEqual(json.loads(output.read_text()), expected)
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [
                        "mathformer_coherence_repair_" + n
                        for n in [
                            "parse_arguments",
                            "load_reports",
                            "plan",
                            "write_output",
                            "emit",
                        ]
                    ],
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
            for argv in ([], ["--json"], ["--self-test", "--json"]):
                result = await run(argv)
                self.assertEqual(result["status"], "accepted", result)
                reports = self.native.default_reports("--self-test" in argv, self.root)
                self.assertEqual(
                    result["outputs"],
                    {"payload": self.native.repair_plan(reports), "exit_code": 0},
                )
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [
                        "mathformer_coherence_repair_" + n
                        for n in ["parse_arguments", "default_reports", "plan", "emit"]
                    ],
                )
                if "--self-test" in argv:
                    # Preserve the result-bundle/empty-graph quirk.
                    self.assertEqual(len(reports), 4)
                    self.assertEqual(reports[3]["finding_count"], 0)
                    self.assertTrue(
                        any(
                            f["kind"] == "missing_foundations_index"
                            for f in reports[2]["findings"]
                        )
                    )
            invalid = self.root / "invalid.json"
            invalid.write_text("{")
            bad = self.root / "bad.json"
            bad.write_text('{"findings":[null]}')
            blocker = self.root / "blocker"
            blocker.write_text("file")
            for argv, calls in [
                (["--invalid"], 1),
                (["--report", str(invalid)], 2),
                (["--report", str(self.root / "missing")], 2),
                (["--report", str(bad)], 3),
                (self.paths([{}]) + ["--output", str(blocker / "out")], 4),
            ]:
                result = await run(argv)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), calls)
                self.assertEqual(result["calls"][-1]["status"], "rejected")
            # Default report generation propagates inventory input errors.
            lib = self.root / "MathformerPhysicsLib"
            lib.mkdir()
            (lib / "MANIFEST.json").write_text("{")
            result = await run([])
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 2)
            self.assertIsNone(result["outputs"])
            # No retry or emit after budget exhaustion, even though planning can succeed.
            bounded = deepcopy(document)
            bounded["policy"]["limits"]["max_operation_calls"] = 2
            result = await run(self.paths(reports_fixture()), bounded)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 2
            )
            self.assertIn("budget", str(result).lower())
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    "mathformer_coherence_repair_plan",
                    {"reports": [{"findings": [None]}]},
                )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
