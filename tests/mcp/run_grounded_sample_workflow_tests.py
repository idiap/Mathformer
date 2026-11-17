#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native fixture audits, registered MCP, and real Lunar/PRISM execution.

The selected workflow has no model/provider or compiler calls to replace: its
checker is a deterministic Python text analyzer, also executed here unmodified.
Every input and output belongs to a temporary repository data context.
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
from functools import partial
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import yaml
from grounded_sample_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_grounded_sample_thoroughness_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/grounded-sample-thoroughness.workflow.json"
PREFIX = "mathformer_grounded_sample_"
FIXTURES = ROOT / "tests/mcp/fixtures/grounded_sample"


def assets(document):
    def asset(path, content):
        return dict(
            path=path,
            content=content,
            encoding="text",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


class GroundedSampleTests(unittest.TestCase):
    def setUp(self):
        self.native = source()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.fixed = self.native.report_path(self.root)
        self.good = (FIXTURES / "good.lean").read_text()
        # More declarations/steps than the largest curated threshold. Curated
        # terms are intentionally in comments: native curated policy uses text.
        self.good += "".join(f"def fixture_{i} := {i}\n" for i in range(60))
        self.good += "".join(
            f"theorem reverse_{i} (x y : Nat) (h : x = y) : y = x := by\n  exact h.symm\n"
            for i in range(10)
        )
        self.bad = (FIXTURES / "blocked.lean").read_text()
        for case, spec in self.native.CASE_SPECS.items():
            self.lean(
                case, self.good + "\n/- " + " ".join(spec["required_terms"]) + " -/\n"
            )
        evidence = json.loads((FIXTURES / "source_record.json").read_text())
        for case, record in (
            (
                "generated_operator",
                {"field": "operator", "required_terms": ["FixtureAnchor"]},
            ),
            (
                "generated_calculus",
                {"question": "integral", "required_terms": ["FixtureAnchor"]},
            ),
            (
                "generated_plain",
                {"question": "ordinary", "required_terms": ["FixtureAnchor"]},
            ),
            (
                "generated_bad",
                {"field": "operator", "required_terms": ["FixtureAnchor"]},
            ),
        ):
            self.record(case, {**evidence, **record})
            self.lean(case, self.bad if case == "generated_bad" else self.good)
        # Frozen original orchestration uses the unchanged native audit functions;
        # partials relocate their data context, without substituting algorithms.
        namespace = dict(vars(self.native))
        namespace.update(
            selected_case_specs=partial(
                self.native.selected_case_specs, repository_root=self.root
            ),
            audit_case=partial(self.native.audit_case, repository_root=self.root),
            rel=partial(self.native.rel, repository_root=self.root),
            ARTIFACT_ROOT=self.fixed.parent,
        )
        exec(
            (ROOT / "tests/mcp/fixtures/grounded_sample_entrypoint.py").read_text(),
            namespace,
        )
        self.original = namespace["main"]

    def write(self, relative, content):
        p = self.root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p

    def lean(self, case, text, checker=True):
        p = self.write(f"MathformerPhysicsLib/Lean/{case}/MathformerPhysics.lean", text)
        if checker:
            self.write(
                f"libraries/MathformerPhysicsLib/Lean/{case}/MathformerPhysics.lean",
                text,
            )
        return p

    def record(self, case, record, location="recursive_goal_runs"):
        filename = (
            "source_record.rebuilt.json"
            if location == "recursive_goal_runs"
            else "source_record.json"
        )
        return self.write(
            f"artifacts/physics_lean/{location}/{case}/{filename}", json.dumps(record)
        )

    def request(self, cases=(), output=None, json_output=True):
        return dict(
            case_ids=list(cases),
            output=str(output) if output else None,
            json=json_output,
        )

    def baseline(self, request):
        argv = [part for case in request["case_ids"] for part in ("--case", case)]
        if request["output"]:
            argv += ["--output", request["output"]]
        if request["json"]:
            argv += ["--json"]
        output = io.StringIO()
        with redirect_stdout(output):
            code = self.original(argv)
        return {
            "result": json.loads(self.fixed.read_text()),
            "exit_code": code,
        }, output.getvalue()

    def test_native_entrypoint_equivalence_state_and_features(self):
        for cases in (
            (),
            ("generated_operator",),
            ("generated_calculus", "generated_plain"),
            ("generated_bad", "formalphysics_0000", "generated_bad"),
        ):
            for json_output in (True, False):
                request = self.request(cases, self.root / "optional.json", json_output)
                expected, expected_stdout = self.baseline(request)
                expected_bytes = self.fixed.read_bytes()
                argv = [part for case in cases for part in ("--case", case)] + [
                    "--output",
                    request["output"],
                ]
                if json_output:
                    argv += ["--json"]
                captured = io.StringIO()
                with redirect_stdout(captured):
                    code = self.native.main(argv, self.root)
                self.assertEqual(captured.getvalue(), expected_stdout)
                self.assertEqual(code, expected["exit_code"])
                self.assertEqual(self.fixed.read_bytes(), expected_bytes)
                self.assertEqual(Path(request["output"]).read_bytes(), expected_bytes)
        state = self.native.initialize_suite(
            ["generated_bad", "generated_plain", "generated_bad"], self.root
        )
        first = self.native.audit_next(state, self.root)
        self.assertFalse(first["ok"])
        self.assertEqual(first["status"], "blocked_target_restating_assumption")
        self.assertIn("sorry", first["forbidden_hits"])
        transition = self.native.append_guard(state, first)
        self.assertEqual(state["completed"], [])
        self.assertEqual(len(state["pending"]), 2)
        self.assertFalse(transition["done"])
        self.assertEqual(transition["state"]["completed"], [first])
        transition = self.native.append_guard(
            transition["state"], self.native.audit_next(transition["state"], self.root)
        )
        self.assertTrue(transition["done"])
        self.assertEqual(transition["state"]["pending"], [])
        specs = self.native.selected_case_specs(
            ["generated_operator", "generated_calculus", "generated_plain"], self.root
        )
        self.assertEqual(
            [
                (
                    s["minimum_proof_steps"],
                    s["minimum_bridge_declarations"],
                    s["minimum_deep_grounding_signals"],
                )
                for s in specs.values()
            ],
            [(4, 8, 2), (2, 4, 2), (2, 4, 1)],
        )
        self.record(
            "generated_plain", {"required_terms": ["absent"]}, "dirac_recursive_batch"
        )
        self.assertIn(
            "recursive_goal_runs",
            str(self.native.source_record_path("generated_plain", self.root)),
        )
        with self.assertRaises(SystemExit):
            self.native.initialize_suite(["generated_plain", "unknown"], self.root)
        self.assertEqual(
            self.native.deep_grounding_signals(
                self.native.lean_code_surface(
                    '-- LinearMap\n/- Matrix -/\n"HasDerivAt"'
                )
            ),
            [],
        )
        # Operator wrappers lack high operator grounding even if two lower signals
        # pass the numerical signal gate. Required generated terms use code only.
        wrapper = (
            self.good.replace("LinearMap", "Grounding")
            + "\nvariable {A : Type*} [Ring A] [Module ℂ A]\ndef wrapper := HeisenbergEquationEvidence A\n"
        )
        self.lean("generated_operator", wrapper)
        result = self.native.audit_case(
            "generated_operator", specs["generated_operator"], self.root
        )
        self.assertTrue(result["checks"]["deep_grounding_signals_present"])
        self.assertFalse(result["checks"]["operator_source_not_abstract_wrapper_only"])
        self.lean(
            "generated_plain",
            self.good.replace("def FixtureAnchor := 0", "-- FixtureAnchor"),
        )
        result = self.native.audit_case(
            "generated_plain", specs["generated_plain"], self.root
        )
        self.assertEqual(result["missing_terms"], ["FixtureAnchor"])
        self.assertFalse(result["checks"]["required_grounding_terms_present"])

    def test_registered_tools_and_lunar_execution(self):
        asyncio.run(self.scenario())

    def test_generator_retains_authored_contract(self):
        # Read-only inventory generation must preserve this graph rather than
        # falling back to the generic opaque hub-command representation.
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location(
            "grounded_sample_normalizer", path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        expected = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        selected = [row for row in module.inventory() if row["id"] == expected["id"]]
        self.assertEqual(selected, [expected])

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document, json.loads((ROOT / AUTHORED).read_text()))
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["id"], "hub_physics_lean_grounded_sample_thoroughness_workflow"
        )
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
            "grounded-sample",
            StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=["-c", server, str(self.root)],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            try:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    received = assets(doc)
                    selected = workflow_documents([DESCRIPTOR], received)[0]
                    return (
                        compile_workflow(
                            "mcp:grounded-sample",
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

                async def run(request, doc=None):
                    w, a = compile(doc) if doc else (workflow, received)
                    return await execute(
                        w,
                        a,
                        {"request": request, "repository_root": str(self.root)},
                        remote,
                        allow,
                    )

                # Default 15-item traversal completes exactly at the bound, and
                # a false audit is retained while later cases continue normally.
                for cases in (
                    (),
                    ("generated_operator",),
                    ("generated_calculus", "generated_plain"),
                    ("generated_bad", "formalphysics_0000", "generated_bad"),
                ):
                    request = self.request(cases, self.root / "nested/optional.json")
                    expected, _ = self.baseline(request)
                    expected_bytes = self.fixed.read_bytes()
                    self.fixed.unlink()
                    Path(request["output"]).unlink()
                    result = await run(request)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], expected)
                    self.assertEqual(self.fixed.read_bytes(), expected_bytes)
                    self.assertEqual(
                        Path(request["output"]).read_bytes(), expected_bytes
                    )
                    n = expected["result"]["case_count"]
                    self.assertEqual(
                        [call["tool"] for call in result["calls"]],
                        [PREFIX + "select_initialize"]
                        + [
                            tool
                            for _ in range(n)
                            for tool in (PREFIX + "audit_next", PREFIX + "append_guard")
                        ]
                        + [PREFIX + "finalize"],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    self.assertEqual(
                        expected["exit_code"], int("generated_bad" in cases)
                    )
                    self.assertEqual(
                        expected["result"]["case_count"],
                        len(dict.fromkeys(cases)) if cases else 15,
                    )
                # Direct registered ports expose the same state, results and guard.
                request = self.request(["generated_plain"])
                packet = await remote.call(
                    PREFIX + "select_initialize",
                    {"request": request, "repository_root": str(self.root)},
                )
                self.assertEqual(
                    packet["state"],
                    self.native.initialize_suite(request["case_ids"], self.root),
                )
                audited = await remote.call(
                    PREFIX + "audit_next", {**packet, "repository_root": str(self.root)}
                )
                self.assertEqual(
                    audited["result"],
                    self.native.audit_next(packet["state"], self.root),
                )
                advanced = await remote.call(
                    PREFIX + "append_guard", {**packet, **audited}
                )
                self.assertTrue(advanced["done"])
                self.assertEqual(advanced["state"]["completed"], [audited["result"]])
                # Unknown cases and malformed source records stop before any audit.
                self.record("malformed", {}).write_text("{")
                for cases in (["generated_plain", "unknown"], ["malformed"]):
                    self.fixed.unlink(missing_ok=True)
                    result = await run(self.request(cases))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 1)
                    self.assertIsNone(result["outputs"])
                    self.assertFalse(self.fixed.exists())
                # Native file failures and checker non-JSON subprocess failures
                # stop immediately, with no subsequent audit or final report.
                self.record("missing", {})
                self.record("checker_missing", {})
                self.lean("checker_missing", self.good, checker=False)
                for case in ("missing", "checker_missing"):
                    result = await run(
                        self.request(["generated_plain", case, "generated_operator"])
                    )
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 4)
                    self.assertEqual(result["calls"][-1]["tool"], PREFIX + "audit_next")
                    self.assertIsNone(result["outputs"])
                    self.assertFalse(self.fixed.exists())
                # The native reporter writes its fixed report first, then an
                # optional write may fail or be rejected by the service roots.
                for output in (
                    self.root
                    / "MathformerPhysicsLib/Lean/generated_plain/MathformerPhysics.lean/report.json",
                    self.root.parent / "outside-grounded-report.json",
                ):
                    self.fixed.unlink(missing_ok=True)
                    result = await run(self.request(["generated_plain"], output))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["calls"][-1]["tool"], PREFIX + "finalize")
                    self.assertTrue(self.fixed.exists())
                    self.assertIsNone(result["outputs"])
                bounded = deepcopy(document)
                bounded["flow"]["steps"][1]["max_iterations"] = 1
                result = await run(self.request(["generated_plain"]), bounded)
                self.assertEqual(result["status"], "accepted", result)
                self.fixed.unlink()
                result = await run(
                    self.request(["generated_plain", "generated_operator"]), bounded
                )
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertEqual(len(result["calls"]), 3)
                self.assertIsNone(result["outputs"])
                self.assertFalse(self.fixed.exists())
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                result = await run(self.request(["generated_plain"]), budget)
                self.assertEqual(result["status"], "failed", result)
                self.assertIn("budget", str(result).lower())
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    1,
                )
                with self.assertRaises(ExecutionRejected):
                    await run(self.request(["generated_plain"] * 16))
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "select_initialize",
                        {
                            "request": self.request(["generated_plain"] * 16),
                            "repository_root": str(self.root),
                        },
                    )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
