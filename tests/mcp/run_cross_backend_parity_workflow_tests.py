#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Filesystem fixtures exercise native steps, real MCP and Lunar/PRISM.

There is no model/provider or external compiler in this workflow. Fixture
artifacts are actual imported Python and read Lean/Isabelle source text; no
production source operation, parser, checker or runtime is replaced.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]

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
from cross_backend_parity_tools import source
from libraries.MathformerPhysicsLib.physics_ir import compare_backend_packets
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathformerphysicslib_cross_backend_parity_workflow/workflow.yaml"
ORACLE = ROOT / "tests/mcp/fixtures/cross_backend_parity_original.py.txt"
ARTIFACT = """CLAIM = {"statement_nl": "Force equals mass times acceleration", "statement_latex": "F=ma", "source_anchors": ["fixture:1"]}
QUANTITY_TABLE = {"F": ["force", "M L T^-2", "N"]}
ASSUMPTION_CONTEXT = {"CONTEXT_ASSUMPTIONS": [{"text": "constant mass"}]}
DERIVATION_STEPS = [{"id": "step1", "expression": "F=ma"}]
def derive_target(): return "F=ma"
def validate_dimensions(): return {"dimensionally_consistent": False}
def validate_numeric_samples(): return {"passed": False}
def review_final_equations(): return {"F": {"status": "fixture"}}
"""


def module_at(path, name):
    spec = importlib.util.spec_from_loader(name, SourceFileLoader(name, str(path)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(directory, cases, registry=None):
    directory.mkdir(parents=True, exist_ok=True)
    rows = []
    for case, backends in cases.items():
        for backend in backends:
            path = directory / backend / case
            path.mkdir(parents=True)
            suffix = {"SymPy": "py", "Lean": "lean", "Isabelle": "thy"}[backend]
            (path / ("MathformerPhysics." + suffix)).write_text(
                ARTIFACT if backend == "SymPy" else "-- fixture backend text\n"
            )
        rows.extend(
            {"case_id": case, "backend": b, "status": "promoted"}
            for b in ("Lean", "SymPy")
        )
    manifest = directory / "manifest.json"
    manifest.write_text(
        json.dumps({"artifact_registry": rows if registry is None else registry})
    )
    return {
        "json_output": True,
        "case_cap": 10000,
        "manifest_path": str(manifest),
        "artifact_root": str(directory),
    }


def native_result(request, frozen=False):
    native = module_at(ORACLE, "parity_oracle") if frozen else source()
    native.MANIFEST = Path(request["manifest_path"])
    native.BUILDER = ROOT / "tests/physics_sympy/run_cross_backend_semantic_packet.py"
    load = native.load_builder

    def contextual_builder():
        # Configure the actual loaded source module's filesystem roots. No source
        # step is simulated: original main calls the real loader and build_packet.
        builder = load()
        root = Path(request["artifact_root"])
        builder.SYMPY_ROOT, builder.LEAN_ROOT, builder.ISABELLE_ROOT = [
            root / b for b in ("SymPy", "Lean", "Isabelle")
        ]
        return builder

    stream = io.StringIO()
    argv = ["parity", "--json"] if request["json_output"] else ["parity"]
    with (
        patch.object(native, "load_builder", contextual_builder),
        patch.object(sys, "argv", argv),
        redirect_stdout(stream),
    ):
        code = native.main()
    return code, stream.getvalue()


def snapshot(document):
    def asset(path, content):
        return {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in document["provenance"]["sources"]
    ]


class ParityTests(unittest.TestCase):
    def test_native_original_equivalence_and_packet_semantics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for label, cases in [
                ("empty", {}),
                ("full", {"z": ["Lean", "SymPy"], "a": ["Lean", "SymPy", "Isabelle"]}),
                ("missing", {"a": ["SymPy"]}),
            ]:
                request = fixture(root / label, cases)
                for json_output in (False, True):
                    request["json_output"] = json_output
                    self.assertEqual(
                        native_result(request), native_result(request, True)
                    )
            builder = source().load_builder()
            packet = builder.build_packet("a", root / "full")
            self.assertTrue(packet["semantic_parity"]["semantic_parity"])
            self.assertFalse(
                packet["unit_dimension_treatment"]["sympy"]["dimensionally_consistent"]
            )
            self.assertFalse(
                packet["unit_dimension_treatment"]["sympy"]["numeric_sample_passed"]
            )
            # Native parity gate deliberately ignores overall packet ok.
            artifact = root / "full/SymPy/a/MathformerPhysics.py"
            artifact.write_text(
                ARTIFACT.replace(
                    'def derive_target(): return "F=ma"',
                    'def derive_target(): raise ValueError("derivation fixture")',
                )
            )
            packet = builder.build_packet("a", root / "full")
            self.assertFalse(packet["ok"])
            self.assertTrue(packet["semantic_parity"]["semantic_parity"])
            plan = {
                "registered": {"Isabelle": ["a"]},
                "promoted": {b: ["a"] for b in ("Lean", "SymPy", "Isabelle")},
            }
            rows = source().append_case(plan, [], "a", packet)
            self.assertTrue(source().build_report(plan, rows)["release_ok"])
            fields = (
                "case_id",
                "source_digest",
                "ir_digest",
                "quantity_roles",
                "assumption_ids",
                "obligation_ids",
                "target_claim",
            )
            baseline = packet["backend_semantic_packets"][0]
            changed = {
                **baseline,
                "backend": "different",
                **{key: ["changed"] for key in fields},
            }
            compared = compare_backend_packets([baseline, changed, changed])
            self.assertEqual(
                [r["field"] for r in compared["findings"]], list(fields) * 2
            )
            self.assertFalse(compared["semantic_parity"])
            self.assertEqual(
                compare_backend_packets([])["findings"], [{"code": "no_packets"}]
            )

    def test_real_registered_tools_compile_and_execute(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_mathformerphysicslib_cross_backend_parity_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(
            "tests/physics_sympy/run_cross_backend_parity_gate.py",
            [r["path"] for r in document["provenance"]["sources"]],
        )
        loop = document["flow"]["steps"][1]
        self.assertEqual(
            (loop["max_iterations"], loop["on_exhausted"]), (10000, "fail")
        )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from cross_backend_parity_tools import create_server;create_server().run(transport="stdio")'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            failure = None
            async with manager.open(
                "parity",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile(doc, inventory=None):
                        assets = snapshot(doc)
                        compiled = compile_workflow(
                            "mcp:parity",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools if inventory is None else inventory,
                        )
                        return compiled, assets

                    compiled, assets = compile(document)
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(
                        set(compiled["bindings"]), set(document["operations"])
                    )
                    self.assertFalse(compile(document, [])[0]["runnable"])

                    async def allow():
                        pass

                    async def run(request, doc=None):
                        workflow, received = compile(doc) if doc else (compiled, assets)
                        self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                        return await execute(
                            workflow, received, {"request": request}, remote, allow
                        )

                    rows = [
                        {"case_id": c, "backend": b, "status": "promoted"}
                        for c in ("z", "a")
                        for b in ("Lean", "SymPy")
                    ]
                    rows += [
                        {"case_id": "a", "backend": "Isabelle", "status": "candidate"},
                        {
                            "case_id": "only_lean",
                            "backend": "Lean",
                            "status": "promoted",
                        },
                    ]
                    request = fixture(
                        root / "good",
                        {"z": ["Lean", "SymPy"], "a": ["Lean", "SymPy", "Isabelle"]},
                        rows,
                    )
                    result = await run(request)
                    self.assertEqual(result["status"], "accepted", result)
                    expected_code, expected_stdout = native_result(request, True)
                    self.assertEqual(
                        result["outputs"],
                        {
                            "report": json.loads(expected_stdout),
                            "exit_code": expected_code,
                            "stdout": expected_stdout,
                        },
                    )
                    self.assertEqual(expected_code, 0)
                    self.assertEqual(
                        [r["case_id"] for r in result["outputs"]["report"]["cases"]],
                        ["a", "z"],
                    )
                    self.assertEqual(
                        result["outputs"]["report"]["cases"][0]["expected_backends"],
                        ["isabelle", "lean", "sympy"],
                    )
                    self.assertEqual(
                        result["outputs"]["report"]["coverage"]["Isabelle"][
                            "promoted_count"
                        ],
                        0,
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_parity_prepare"]
                        + [
                            "mathformer_parity_select_case",
                            "mathformer_parity_build_packet",
                            "mathformer_parity_append_case",
                        ]
                        * 2
                        + ["mathformer_parity_report"],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    for label, cases, registry in [
                        ("empty", {}, []),
                        (
                            "extra",
                            {
                                "z": ["Lean", "SymPy"],
                                "a": ["Lean", "SymPy", "Isabelle"],
                            },
                            None,
                        ),
                        ("missing", {"z": ["Lean", "SymPy"], "a": ["SymPy"]}, None),
                        (
                            "required",
                            {"a": ["Lean", "SymPy"], "z": ["Lean", "SymPy"]},
                            rows,
                        ),
                    ]:
                        req = fixture(root / label, cases, registry)
                        req["json_output"] = label != "extra"
                        result = await run(req)
                        self.assertEqual(result["status"], "accepted", result)
                        code, stdout = native_result(req, True)
                        self.assertEqual(code, 1)
                        self.assertEqual(result["outputs"]["exit_code"], code)
                        self.assertEqual(result["outputs"]["stdout"], stdout)
                        self.assertEqual(
                            result["outputs"]["report"]["terminal_states"], ["blocked"]
                        )
                        self.assertEqual(
                            result["outputs"]["report"]["case_count"], len(cases)
                        )
                        self.assertEqual(
                            len(result["calls"]), 2 + 3 * len(cases) if cases else 3
                        )
                    # Uncaught final-equation review and nullable IR access abort;
                    # no retry and no report or later case is executed.
                    for label, text, failure_calls in [
                        (
                            "review",
                            ARTIFACT.replace(
                                'return {"F": {"status": "fixture"}}',
                                'raise RuntimeError("review boundary failure")',
                            ),
                            3,
                        ),
                        ("no_ir", 'raise RuntimeError("import failure")\n', 4),
                    ]:
                        req = fixture(
                            root / label,
                            {"a": ["Lean", "SymPy"], "z": ["Lean", "SymPy"]},
                        )
                        (root / label / "SymPy/a/MathformerPhysics.py").write_text(text)
                        with self.assertRaises((RuntimeError, AttributeError)):
                            native_result(req, True)
                        result = await run(req)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(len(result["calls"]), failure_calls)
                        self.assertEqual(result["calls"][-1]["status"], "rejected")
                    # Exercise runtime exhaustion using the same native operations.
                    bounded = deepcopy(document)
                    bounded["flow"]["steps"][1]["max_iterations"] = 1
                    result = await run(request, bounded)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["failure_disposition"], "fail")
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 4)
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 2
                    result = await run(request, budget)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        2,
                    )
                    # Admission boundary uses real preparation of finite manifests.
                    big_rows = [
                        {"case_id": str(i), "backend": b, "status": "promoted"}
                        for i in range(10000)
                        for b in ("Lean", "SymPy")
                    ]
                    big = fixture(root / "big", {}, big_rows)
                    prepared = await remote.call(
                        "mathformer_parity_prepare", {"request": big}
                    )
                    self.assertEqual(len(prepared["plan"]["aligned_cases"]), 10000)
                    # Native accumulation supplies actual case state to last-item
                    # selection; packet is produced by the real builder fixture.
                    packet = source().load_builder().build_packet("a", root / "good")
                    state = []
                    native = source()
                    for case in prepared["plan"]["aligned_cases"][:-1]:
                        native.append_case(prepared["plan"], state, case, packet)
                    selected = await remote.call(
                        "mathformer_parity_select_case",
                        {"plan": prepared["plan"], "cases": state},
                    )
                    final = await remote.call(
                        "mathformer_parity_append_case",
                        {
                            "plan": prepared["plan"],
                            "cases": state,
                            "case_id": selected["case_id"],
                            "packet": packet,
                        },
                    )
                    self.assertTrue(final["done"])
                    self.assertEqual(len(final["cases"]), 10000)
                    big_rows += [
                        {"case_id": "overflow", "backend": b, "status": "promoted"}
                        for b in ("Lean", "SymPy")
                    ]
                    Path(big["manifest_path"]).write_text(
                        json.dumps({"artifact_registry": big_rows})
                    )
                    result = await run(big)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 1)
                    self.assertIsNone(result["outputs"])
                    # Invalid manifest parse failure propagates before iteration.
                    Path(big["manifest_path"]).write_text("{")
                    result = await run(big)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 1)
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
