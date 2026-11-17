#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native text fixtures through registered MCP and real PRISM.

This source has no external provider/compiler boundary to substitute. Lean text
is data only. The actual Lunar parser, checker, compiler and runtime are used.
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
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import tempfile
import unittest
import yaml
from derivation_completeness_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_derivation_completeness_workflow/workflow.yaml"
PREFIX = "mathformer_derivation_completeness_"
GOOD = "import Mathlib\ntheorem target (x y : Nat) (h : x = y) : y = x := by\n  exact h.symm\n"
BAD = "theorem target (x y : Nat) (h : PhysicalLawWitness (x = y)) : x = y := by\n  exact physicalLawHolds h\n"
DIRECT = "theorem target (x y : Nat) (h : x = y) : x = y := by\n  exact h\n"


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
        for r in document["provenance"]["sources"]
    ]


class DerivationTests(unittest.TestCase):
    def setUp(self):
        self.native = source()
        namespace = dict(vars(self.native))
        exec(
            (
                ROOT / "tests/mcp/fixtures/derivation_completeness_entrypoint.py"
            ).read_text(),
            namespace,
        )
        self.original = namespace["main"]
        self.original_build = namespace["build_report"]
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.good = self.write("good.lean", GOOD)
        self.bad = self.write("bad.lean", BAD)
        self.direct = self.write("direct.lean", DIRECT)
        self.empty = self.write("empty.lean", "")
        self.plan = self.write(
            "plan.json", json.dumps({"recursive_frontier": ["a", "b"]})
        )
        self.record = self.write(
            "record.json", json.dumps({"concepts": ["energy law"]})
        )

    def write(self, name, text):
        p = self.root / name
        p.write_text(text)
        return str(p)

    def baseline(self, argv):
        output = io.StringIO()
        with redirect_stdout(output):
            code = self.original([*argv, "--json"])
        return {"report": json.loads(output.getvalue()), "exit_code": code}

    def test_cli_equivalence_and_state(self):
        for argv in (
            ["--lean-file", self.good],
            ["--lean-file", self.good, "--lean-file", self.bad, "--expect-complete"],
            ["--lean-file", self.good, "--recursive-plan", self.plan],
            ["--lean-file", self.empty],
            ["--lean-file", self.good, "--source-record", self.record],
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                code = self.native.main([*argv, "--json"])
            self.assertEqual(
                {"report": json.loads(output.getvalue()), "exit_code": code},
                self.baseline(argv),
            )
        for args in ([], ["--recursive-plan", self.plan, "--lean-file", self.good]):
            parsed = self.native.parse_args(args)
            self.assertEqual(
                self.native.build_report(parsed), self.original_build(parsed)
            )
        state = self.native.initialize_report(
            self.native.parse_args(["--lean-file", self.good, "--lean-file", self.bad])
        )
        first = self.native.analyze_current(state)
        visited = self.native.advance_report(state, first)
        self.assertEqual(state["index"], 0)
        self.assertEqual(state["artifacts"], [])
        self.assertFalse(visited["done"])
        self.assertEqual(visited["state"]["artifacts"], [first])
        visited = self.native.advance_report(
            visited["state"], self.native.analyze_current(visited["state"])
        )
        self.assertTrue(visited["done"])
        self.assertEqual(visited["state"]["index"], 2)
        self.assertEqual(
            self.native.aggregate_report(visited["state"])["status"],
            "blocked_target_restating_assumption",
        )
        for argv, expected in (([], "--lean-file"), (["--unknown"], "2")):
            for call in (self.original, self.native.main):
                with self.assertRaises(SystemExit) as error:
                    call(argv)
                self.assertIn(expected, str(error.exception))

    def test_native_detection_and_obligation_branches(self):
        for name in (
            "physicalLawHolds",
            "generatedSupportHolds",
            "dimensionCompatibleEq",
        ):
            declaration = self.native.split_declaration_blocks(
                DIRECT.replace("target", name)
            )[0]
            analyzed = self.native.analyze_declaration(declaration)
            self.assertTrue(analyzed["ignored_projection_declaration"])
            self.assertEqual(analyzed["findings"], [])
        for wrapper, unwrap in (
            ("PhysicalLawWitness", "physicalLawHolds"),
            ("GeneratedSupportAssumption", "generatedSupportHolds"),
        ):
            text = BAD.replace("PhysicalLawWitness", wrapper).replace(
                "physicalLawHolds", unwrap
            )
            analyzed = self.native.analyze_declaration(
                self.native.split_declaration_blocks(text)[0]
            )
            self.assertEqual(analyzed["target_like_hypotheses"], ["h"])
            self.assertGreaterEqual(len(analyzed["findings"]), 2)
            self.assertTrue(all(f["severity"] == "high" for f in analyzed["findings"]))
        # Case routing takes precedence over required terms and concepts.
        for case in ("0015", "0021", "0052", "0074"):
            record = {"case_id": "formalphysics_" + case}
            self.assertEqual(
                self.native.generic_obligations(record, GOOD),
                self.native.generic_obligations(
                    {
                        **record,
                        "required_terms": ["missing"],
                        "concepts": ["heisenberg"],
                    },
                    GOOD,
                ),
            )
        self.assertEqual(
            self.native.generic_obligations({"concepts": ["ordinary", "cauchy"]}, GOOD),
            self.native.heisenberg_obligations(GOOD),
        )
        stages = {
            "source_extraction": {"ok": True, "path": "fixture", "payload_ok": False},
            "informal_expansion": {"ok": True, "path": "fixture"},
            "recursive_control": {
                "ok": True,
                "path": "fixture",
                "payload_decision": "complete",
            },
        }
        obligations = self.native.generic_obligations(
            {"required_terms": ["Mathlib"], "workflow_stage_reports": stages}, GOOD
        )
        statuses = {o["id"]: o["status"] for o in obligations}
        self.assertEqual(
            statuses["required_grounding_term_1"], "mathformerphysicslib_reused"
        )
        self.assertEqual(
            statuses["workflow_stage_source_extraction"],
            "blocked_missing_workflow_stage",
        )
        self.assertEqual(
            statuses["workflow_stage_informal_expansion"], "workflow_stage_evidenced"
        )
        self.assertEqual(
            statuses["workflow_stage_recursive_control"], "workflow_stage_evidenced"
        )
        self.assertEqual(
            self.native.recursive_frontier_count(
                {"recursive_frontier_count": 3, "recursive_frontier": ["a"]}
            ),
            3,
        )
        self.assertEqual(
            self.native.recursive_frontier_count({"recursive_frontier": None}), 0
        )

    def test_registered_mcp_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_physics_lean_derivation_completeness_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp,apply_runtime_config;apply_runtime_config(allowed_write_roots=[sys.argv[1]]);mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "derivation",
            StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=["-c", server, str(self.root)],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    received = assets(doc)
                    selected = workflow_documents([DESCRIPTOR], received)[0]
                    return (
                        compile_workflow(
                            "mcp:derivation",
                            selected,
                            tools if inventory is None else inventory,
                        ),
                        received,
                    )

                workflow, received = compile(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def allow():
                    pass

                async def run(argv, doc=None):
                    w, a = compile(doc) if doc else (workflow, received)
                    return await execute(
                        w,
                        a,
                        {
                            "argv": argv,
                            "self_test_directory": str(self.root / "self-test"),
                        },
                        remote,
                        allow,
                    )

                # Complete, blocked, frontier-only, required stages, recognized cases,
                # specialized Heisenberg, empty Lean and explicit override paths.
                samples = [
                    (["--lean-file", self.good], "complete_autoformalization"),
                    (
                        ["--lean-file", self.good, "--lean-file", self.bad],
                        "blocked_target_restating_assumption",
                    ),
                    (
                        ["--lean-file", self.direct, "--expect-complete"],
                        "blocked_target_restating_assumption",
                    ),
                    (
                        ["--lean-file", self.good, "--recursive-plan", self.plan],
                        "derivation_partial",
                    ),
                    (
                        [
                            "--lean-file",
                            self.good,
                            "--recursive-plan",
                            self.plan,
                            "--recursive-frontier-count",
                            "0",
                        ],
                        "complete_autoformalization",
                    ),
                    (["--lean-file", self.empty], "complete_autoformalization"),
                    (
                        ["--lean-file", self.good, "--source-record", self.record],
                        "derivation_partial",
                    ),
                ]
                records = [
                    {"case_id": "formalphysics_" + case}
                    for case in ("0015", "0021", "0052", "0074")
                ]
                records += [
                    {"concepts": ["heisenberg"]},
                    {
                        "required_terms": ["absent"],
                        "workflow_stage_reports": {
                            "source_extraction": {
                                "ok": True,
                                "path": "fixture",
                                "payload_ok": False,
                            }
                        },
                    },
                ]
                for i, record in enumerate(records):
                    path = self.write(f"source-{i}.json", json.dumps(record))
                    samples.append(
                        (
                            ["--lean-file", self.good, "--source-record", path],
                            "derivation_partial",
                        )
                    )
                for argv, status in samples:
                    result = await run(argv)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], self.baseline(argv))
                    report = result["outputs"]["report"]
                    self.assertEqual(report["status"], status)
                    self.assertEqual(
                        result["outputs"]["exit_code"],
                        int("--expect-complete" in argv and not report["ok"]),
                    )
                    count = argv.count("--lean-file")
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [PREFIX + "parse", PREFIX + "initialize"]
                        + [
                            name
                            for _ in range(count)
                            for name in (PREFIX + "analyze_current", PREFIX + "advance")
                        ]
                        + [PREFIX + "aggregate", PREFIX + "emit"],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                # Output bytes, report and source CLI formatting are retained.
                output = str(self.root / "nested/report.json")
                argv = [
                    "--lean-file",
                    self.bad,
                    "--expect-complete",
                    "--output",
                    output,
                    "--json",
                ]
                expected = self.baseline(argv)
                expected_bytes = Path(output).read_bytes()
                Path(output).unlink()
                result = await run(argv)
                self.assertEqual(result["outputs"], expected)
                self.assertEqual(Path(output).read_bytes(), expected_bytes)
                # Service roots and native write failures both stop at emission.
                for bad_output in (
                    str(self.root.parent / "outside-derivation-report.json"),
                    self.good + "/report.json",
                ):
                    result = await run(
                        ["--lean-file", self.good, "--output", bad_output]
                    )
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["calls"][-1]["tool"], PREFIX + "emit")
                    self.assertIsNone(result["outputs"])
                parsed = await remote.call(
                    PREFIX + "parse", {"argv": ["--lean-file", self.good]}
                )
                packet = await remote.call(PREFIX + "initialize", parsed)
                self.assertEqual(
                    packet["state"],
                    self.native.initialize_report(
                        self.native.parse_args(["--lean-file", self.good])
                    ),
                )
                analyzed = await remote.call(PREFIX + "analyze_current", packet)
                self.assertEqual(
                    analyzed["artifact"], self.native.analyze_current(packet["state"])
                )
                advanced = await remote.call(
                    PREFIX + "advance", {"state": packet["state"], **analyzed}
                )
                self.assertTrue(advanced["done"])
                self.assertEqual(advanced["state"]["artifacts"], [analyzed["artifact"]])
                # Self-test branches before any required file/source/plan access.
                result = await run(
                    [
                        "--self-test",
                        "--source-record",
                        "missing.json",
                        "--expect-complete",
                    ]
                )
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"]["exit_code"], 0)
                self.assertEqual(result["outputs"]["report"]["checks"], [True] * 3)
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [
                        PREFIX + "parse",
                        PREFIX + "initialize_self_test",
                        PREFIX + "self_test",
                        PREFIX + "finish_self_test",
                        PREFIX + "aggregate",
                        PREFIX + "emit",
                    ],
                )
                self.assertTrue((self.root / "self-test/bad.lean").exists())
                # Empty argv stops before input loads; invalid args stop at parse.
                for argv, count in (
                    ([], 2),
                    (["--wat"], 1),
                    (["--help"], 1),
                    (
                        [
                            "--lean-file",
                            self.good,
                            "--recursive-plan",
                            self.write("broken.json", "{"),
                        ],
                        2,
                    ),
                    (
                        [
                            "--lean-file",
                            self.good,
                            "--lean-file",
                            str(self.root / "missing.lean"),
                            "--lean-file",
                            self.bad,
                        ],
                        5,
                    ),
                ):
                    result = await run(argv)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), count)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    self.assertIsNone(result["outputs"])
                # Parse the full admitted argv domain and reject overflow pre-call.
                large = ["--lean-file", self.good] * 512
                packet = await remote.call(PREFIX + "parse", {"argv": large})
                self.assertEqual(len(packet["args"]["lean_file"]), 512)
                with self.assertRaises(ExecutionRejected):
                    await run(large + ["--json"])
                with self.assertRaises(MCPConnectionError):
                    await remote.call(PREFIX + "parse", {"argv": large + ["--json"]})
                # A reduced test bound proves real runtime exhaustion, without
                # changing native production traversal or installing a new contract.
                bounded = deepcopy(document)
                bounded["flow"]["steps"][2]["max_iterations"] = 1
                result = await run(["--lean-file", self.good], bounded)
                self.assertEqual(result["status"], "accepted", result)
                result = await run(
                    ["--lean-file", self.good, "--lean-file", self.bad], bounded
                )
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertEqual(len(result["calls"]), 4)
                self.assertIsNone(result["outputs"])
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                result = await run(["--lean-file", self.good], budget)
                self.assertEqual(result["status"], "failed")
                self.assertIn("budget", str(result).lower())
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    1,
                )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
