#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic artifact inputs, native stages, registered MCP and real PRISM.

This selected builder has no provider/model or external compiler boundary.
Fixtures supply actual importable Python and Lean/Isabelle text, never a fake
source operation. Lunar's parser, checker, compiler and runtime are unmodified.
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
import yaml
from cross_backend_semantic_packet_tools import source, PacketStages
from libraries.MathformerPhysicsLib.physics_ir import compare_backend_packets
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DOCUMENT = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
CASE = DOCUMENT["types"]["CaseId"]["schema"].get("const", "formalphysics_0004")
EXPLICIT_GUARD = "packet_ir_ready" in DOCUMENT["operations"]
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_sympy_cross_backend_semantic_packet_0004_workflow/workflow.yaml"
DESCRIPTOR = DESCRIPTOR.replace("0004", CASE[-4:])
AUTHORED = ROOT / (
    "skills/control/workflow-contract-validator/references/cross-backend-semantic-packet-0000.workflow.json"
    if CASE.endswith("0000")
    else "skills/control/workflow-contract-validator/references/cross-backend-semantic-packet.workflow.json"
)
ORACLE = ROOT / "tests/mcp/fixtures/cross_backend_semantic_packet_original.py.txt"
ARTIFACT = """EVENTS = ['import']
CLAIM = {'statement_nl': 'Force equals mass times acceleration', 'statement_latex': 'F=ma', 'source_anchors': ['fixture:4']}
QUANTITY_TABLE = {'F': ['force', 'M L T^-2', 'N'], 'm': ['mass', 'M', 'kg']}
ASSUMPTION_CONTEXT = {'CONTEXT_ASSUMPTIONS': [{'text': 'constant mass'}, {}, 'ignored', {'text': ''}]}
DERIVATION_STEPS = [{'id': 'first', 'expression': 'F=ma'}, {'id': 'last', 'expression': 'a=F/m', 'generated': True}]
PROJECTION_BRIDGES = [{'id': 'component', 'source': 'vector', 'target': 'scalar'}]
SYMPY_LIBRARY_GROUNDING = {'grounding_level': 'fixture'}
def derive_target():
    EVENTS.append('derive')
    return '|'.join(EVENTS)
def validate_dimensions():
    EVENTS.append('dimensions')
    return {'dimensionally_consistent': False, 'target_dimension': 'force'}
def validate_numeric_samples():
    EVENTS.append('numeric')
    return {'passed': False}
def review_final_equations():
    EVENTS.append('review')
    return {'force': {'status': '|'.join(EVENTS)}, 'ignored': 'scalar'}
"""
LEAN = "\n\n/-- next --/\n".join(
    [
        "def lorentz_force_x := " + "x " * 800,
        "theorem lorentz_force_x_core_replay := " + "x " * 800,
        "def lorentz_force_x_witness := PhysicalLawWitness",
        "def lorentz_magnetic_component := Differentiable\n-- LorentzForceXComponentFrontier",
    ]
)
VARIANTS = {
    "good": ARTIFACT,
    "missing_sympy": None,
    "import_failed": 'raise RuntimeError("artifact import failure")\n',
    "dependency": 'raise ModuleNotFoundError("fixture missing SymPy", name="sympy.fixture")\n',
    "no_claim_dict": ARTIFACT + '\nCLAIM = ["non-dict claim"]\n',
    "bad_ir": ARTIFACT + '\nQUANTITY_TABLE = {"x": ["unknown quantity"]}\n',
    "derive_failure": ARTIFACT.replace(
        "EVENTS.append('derive')", "raise ValueError('derivation failure')"
    ),
    "dimension_failure": ARTIFACT.replace(
        "EVENTS.append('dimensions')", "raise ValueError('dimension failure')"
    ),
    "numeric_failure": ARTIFACT.replace(
        "EVENTS.append('numeric')", "raise ValueError('numeric failure')"
    ),
    "no_review": ARTIFACT + "\ndel review_final_equations\n",
    "no_assumptions": ARTIFACT + "\nASSUMPTION_CONTEXT = []\n",
    "mismatch": ARTIFACT
    + """
class ChangingFrame:
    def __init__(self): self.n = 0
    def __deepcopy__(self, memo):
        self.n += 1
        return 'axis-' + str(self.n)
CLAIM['frame'] = {'axis': ChangingFrame()}
""",
    "foreign_dependency": 'raise ModuleNotFoundError("fixture dependency", name="unrelated_fixture_dependency")\n',
    "review_failure": ARTIFACT.replace(
        "EVENTS.append('review')", "raise RuntimeError('final review failure')"
    ),
    "ir_failure": ARTIFACT + '\nQUANTITY_TABLE = ["invalid mapping"]\n',
    "assemble_failure": ARTIFACT + "\ndef review_final_equations(): return []\n",
}


def fixture(root, variant="good", lean=True, isabelle=False):
    for backend, suffix, text in [
        ("SymPy", "py", VARIANTS[variant]),
        ("Lean", "lean", LEAN if lean else None),
        ("Isabelle", "thy", "theory Fixture" if isabelle else None),
    ]:
        if text is not None:
            path = root / backend / CASE / ("MathformerPhysics." + suffix)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    return root


def original():
    spec = importlib.util.spec_from_loader(
        "semantic_packet_oracle",
        SourceFileLoader("semantic_packet_oracle", str(ORACLE)),
    )
    native = importlib.util.module_from_spec(spec)
    # Preserve the original file's repository context after freezing its bytes
    # under fixtures; no implementation function is replaced.
    native.__file__ = str(
        ROOT / "tests/physics_sympy/run_cross_backend_semantic_packet.py"
    )
    spec.loader.exec_module(native)
    return native


def wire(value):
    return json.loads(json.dumps(value, default=str))


def snapshot(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    paths = dict.fromkeys(r["path"] for r in document["provenance"]["sources"])
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(path, (ROOT / path).read_text()) for path in paths
    ]


class SemanticPacketTests(unittest.TestCase):
    def test_native_stages_original_cli_and_retained_module_state(self):
        native = source()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for variant in VARIANTS:
                path = fixture(root / variant, variant, isabelle=True)
                if variant in (
                    "foreign_dependency",
                    "review_failure",
                    "ir_failure",
                    "assemble_failure",
                ):
                    for module in (native, original()):
                        with self.assertRaises(
                            (ModuleNotFoundError, RuntimeError, AttributeError)
                        ):
                            module.build_packet(CASE, path)
                    continue
                expected = wire(original().build_packet(CASE, path))
                self.assertEqual(
                    wire(native.build_packet(CASE, path)), expected, variant
                )
            path = root / "good"
            state = native.inspect_packet(CASE, path)
            imported = state["sympy_module"]
            findings = state["findings"]
            self.assertEqual(imported.EVENTS, ["import"])
            self.assertIs(native.collect_packet(state), state)
            self.assertIs(state["sympy_module"], imported)
            self.assertIs(state["findings"], findings)
            self.assertEqual(
                imported.EVENTS, ["import", "derive", "dimensions", "numeric", "review"]
            )
            self.assertEqual(state["target_expression"], "import|derive")
            self.assertTrue(native.packet_ir_ready(state))
            self.assertIs(native.align_packet(state), state)
            packet = wire(native.assemble_packet(state))
            self.assertTrue(packet["ok"])
            self.assertEqual(len(packet["backend_semantic_packets"]), 3)
            self.assertEqual(
                packet["physics_ir"]["obligations"][1]["depends_on"], ["first"]
            )
            self.assertEqual(len(packet["physics_ir"]["assumptions"]), 1)
            self.assertEqual(
                len(packet["backend_targets"]["lean"]["target_statements"]), 3
            )
            self.assertEqual(
                max(
                    len(t["statement_excerpt"])
                    for t in packet["backend_targets"]["lean"]["target_statements"]
                ),
                700,
            )
            self.assertFalse(
                packet["unit_dimension_treatment"]["sympy"]["numeric_sample_passed"]
            )
            self.assertFalse(
                packet["unit_dimension_treatment"]["sympy"]["dimensionally_consistent"]
            )
            self.assertEqual(
                packet["support_object_status"]["sympy_final_review_statuses"]["force"],
                "import|derive|dimensions|numeric|review",
            )
            for module in (native, original()):
                module.SYMPY_ROOT, module.LEAN_ROOT, module.ISABELLE_ROOT = [
                    path / b for b in ("SymPy", "Lean", "Isabelle")
                ]
                stream = io.StringIO()
                with redirect_stdout(stream):
                    self.assertEqual(module.main(["--case", CASE[-4:], "--json"]), 0)
                self.assertEqual(json.loads(stream.getvalue()), packet)
                output = root / (module.__name__ + ".json")
                self.assertEqual(
                    module.main(
                        ["--case", str(int(CASE[-4:])), "--output", str(output)]
                    ),
                    0,
                )
                self.assertEqual(json.loads(output.read_text()), packet)
                module.SYMPY_ROOT = root / "absent"
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(module.main(["--case", CASE[-4:]]), 3)
            self.assertEqual(
                native.load_sympy_module(root / "unknown.extension", CASE)[1]["status"],
                "missing_spec",
            )
            # Single-use state cannot replay an import, skip alignment or survive
            # success/failure; none of this introduces a native retry loop.
            stages = PacketStages()
            ref = stages.inspect(CASE, str(path))["state"]
            collected = stages.collect(ref)
            with self.assertRaises(KeyError):
                stages.collect(ref)
            aligned = stages.align(collected["state"])["state"]
            self.assertEqual(wire(stages.assemble(aligned)["packet"]), packet)
            self.assertFalse(stages.states)
            ref = stages.collect(stages.inspect(CASE, str(path))["state"])["state"]
            with self.assertRaisesRegex(ValueError, "must complete"):
                stages.assemble(ref)
            ref = stages.inspect(CASE, str(root / "review_failure"))["state"]
            with self.assertRaisesRegex(RuntimeError, "final review"):
                stages.collect(ref)
            self.assertFalse(stages.states)
            ref = stages.collect(
                stages.inspect(CASE, str(root / "missing_sympy"))["state"]
            )["state"]
            with self.assertRaisesRegex(ValueError, "unavailable"):
                stages.align(ref)
            self.assertFalse(stages.states)

    def test_comparison_field_and_packet_traversal_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet = source().build_packet(CASE, fixture(Path(tmp), isabelle=True))
            baseline = packet["backend_semantic_packets"][0]
            fields = (
                "case_id",
                "source_digest",
                "ir_digest",
                "quantity_roles",
                "assumption_ids",
                "obligation_ids",
                "target_claim",
            )
            other = {
                **baseline,
                "backend": "different",
                **{f: ["changed"] for f in fields},
            }
            result = compare_backend_packets([baseline, other, other])
            self.assertEqual([f["field"] for f in result["findings"]], list(fields) * 2)
            self.assertFalse(result["semantic_parity"])
            self.assertFalse(result["coverage_ok"])
            self.assertEqual(
                compare_backend_packets([])["findings"], [{"code": "no_packets"}]
            )

    def test_real_registered_mcp_lunar_compile_execute_branches_and_failure(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"],
            "hub_physics_sympy_cross_backend_semantic_packet_"
            + CASE[-4:]
            + "_workflow",
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document, json.loads(AUTHORED.read_text()))
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(
            "tests/physics_sympy/run_cross_backend_semantic_packet.py",
            [r["path"] for r in document["provenance"]["sources"]],
        )
        # Verify authored discovery without writing host-owned YAML/catalog.
        generator_path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location(
            "semantic_contract_generator", generator_path
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(
            generator.semantic_packet_descriptor(document["aliases"][0]), document
        )
        manager = SessionManager()
        error = None
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            async with manager.open(
                "semantic-packet",
                StdioConfig(
                    command=sys.executable,
                    args=["scripts/cross_backend_semantic_packet_tools.py"],
                    cwd=str(ROOT),
                ),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]
                    self.assertEqual(
                        {t["name"] for t in tools},
                        {
                            "mathformer_semantic_packet_" + s
                            for s in (
                                "inspect",
                                "collect",
                                "readiness",
                                "align",
                                "assemble",
                            )
                        },
                    )

                    def compile(doc, inventory=None):
                        assets = snapshot(doc)
                        compiled = compile_workflow(
                            "mcp:semantic-packet",
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

                    async def run(path, doc=None):
                        workflow, received = compile(doc) if doc else (compiled, assets)
                        self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                        inputs = {"case_id": CASE}
                        if path is not None:
                            inputs["artifact_root"] = str(path)
                        elif EXPLICIT_GUARD:
                            inputs["artifact_root"] = None
                        return await execute(workflow, received, inputs, remote, allow)

                    for variant in VARIANTS:
                        for lean, isabelle in (
                            [(True, True), (True, False), (False, False)]
                            if variant == "good"
                            else [(True, True)]
                        ):
                            path = fixture(
                                root / (variant + str(lean) + str(isabelle)),
                                variant,
                                lean,
                                isabelle,
                            )
                            with self.subTest(
                                variant=variant, lean=lean, isabelle=isabelle
                            ):
                                result = await run(path)
                                failed_at = {
                                    "foreign_dependency": 1,
                                    "review_failure": 2,
                                    "ir_failure": 3,
                                    "assemble_failure": 4,
                                }.get(variant)
                                if failed_at:
                                    if EXPLICIT_GUARD and failed_at >= 3:
                                        failed_at += 1
                                    self.assertEqual(result["status"], "failed", result)
                                    self.assertIsNone(result["outputs"])
                                    self.assertEqual(len(result["calls"]), failed_at)
                                    self.assertEqual(
                                        result["calls"][-1]["status"], "rejected"
                                    )
                                    continue
                                self.assertEqual(result["status"], "accepted", result)
                                packet = result["outputs"]["packet"]
                                self.assertEqual(
                                    packet, wire(original().build_packet(CASE, path))
                                )
                                skip = variant in (
                                    "missing_sympy",
                                    "import_failed",
                                    "dependency",
                                    "no_claim_dict",
                                )
                                calls = (
                                    ["inspect", "collect"]
                                    + (["readiness"] if EXPLICIT_GUARD else [])
                                    + ([] if skip else ["align"])
                                    + ["assemble"]
                                )
                                self.assertEqual(
                                    [c["tool"] for c in result["calls"]],
                                    ["mathformer_semantic_packet_" + s for s in calls],
                                )
                                self.assertTrue(result["runtime"]["effect_records"])
                                self.assertTrue(result["replay_artifacts"])
                                self.assertEqual(
                                    len(packet["backend_semantic_packets"]),
                                    0 if skip else 1 + lean + isabelle,
                                )
                                self.assertEqual(
                                    packet["ok"],
                                    lean
                                    and variant
                                    in (
                                        "good",
                                        "no_claim_dict",
                                        "no_review",
                                        "no_assumptions",
                                    ),
                                )
                                if variant == "mismatch":
                                    self.assertEqual(
                                        [f["field"] for f in packet["findings"]],
                                        ["ir_digest", "ir_digest"],
                                    )
                                if variant.endswith("_failure"):
                                    self.assertEqual(
                                        packet["findings"][0]["code"],
                                        "sympy_validation_failed",
                                    )
                                    self.assertTrue(
                                        packet["semantic_parity"]["semantic_parity"]
                                    )
                                    self.assertEqual(
                                        packet["backend_targets"]["sympy"][
                                            "target_expression"
                                        ],
                                        (
                                            None
                                            if variant == "derive_failure"
                                            else "import|derive"
                                        ),
                                    )
                                    expected = {
                                        "derive_failure": "import|review",
                                        "dimension_failure": "import|derive|review",
                                        "numeric_failure": "import|derive|dimensions|review",
                                    }[variant]
                                    self.assertEqual(
                                        packet["support_object_status"][
                                            "sympy_final_review_statuses"
                                        ]["force"],
                                        expected,
                                    )
                                if not lean:
                                    self.assertEqual(
                                        [f["code"] for f in packet["findings"]],
                                        ["lean_artifact_missing"],
                                    )
                                if variant == "bad_ir":
                                    self.assertEqual(
                                        packet["findings"][0]["code"],
                                        "physics_ir_invalid",
                                    )
                                    self.assertTrue(
                                        packet["semantic_parity"]["semantic_parity"]
                                    )
                    # Directory at the Lean text path: read errors propagate at
                    # inspect, before collection or any alignment operation.
                    path = fixture(root / "lean_directory", lean=False)
                    (path / "Lean" / CASE / "MathformerPhysics.lean").mkdir(
                        parents=True
                    )
                    result = await run(path)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 1)
                    self.assertIsNone(result["outputs"])
                    # No builder loop exists: the finite traversals finish after
                    # <=3 packets and <=14 field comparisons. Enclosing operation
                    # budget exhaustion must abort, with no automatic retry.
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 2
                    result = await run(fixture(root / "budget"), bounded)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIn(
                        "operation-call budget is exhausted",
                        result["calls"][-1]["error"],
                    )
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        2,
                    )
                    self.assertIsNone(result["outputs"])
                    # Raw advertised ports retain one imported module over calls.
                    path = fixture(root / "ports")
                    ref = (
                        await remote.call(
                            "mathformer_semantic_packet_inspect",
                            {"case_id": CASE, "artifact_root": str(path)},
                        )
                    )["state"]
                    collected = await remote.call(
                        "mathformer_semantic_packet_collect", {"state": ref}
                    )
                    self.assertTrue(collected["ir_ready"])
                    readiness = await remote.call(
                        "mathformer_semantic_packet_readiness",
                        {"state": collected["state"]},
                    )
                    self.assertTrue(readiness["ready"])
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_semantic_packet_collect", {"state": ref}
                        )
                    aligned = await remote.call(
                        "mathformer_semantic_packet_align",
                        {"state": collected["state"]},
                    )
                    final = await remote.call(
                        "mathformer_semantic_packet_assemble", aligned
                    )
                    self.assertEqual(
                        final["packet"], wire(original().build_packet(CASE, path))
                    )
                    relative = Path(os.path.relpath(path, ROOT))
                    result = await run(relative)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"]["packet"],
                        wire(original().build_packet(CASE, relative)),
                    )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_semantic_packet_assemble", aligned
                        )
                except BaseException as exc:
                    error = exc
            if error is not None:
                raise error
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
