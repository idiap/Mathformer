#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic filesystem fixtures over production MCP and real Lunar/PRISM.

This textual audit has no provider/model or external compiler boundary. Nothing
is substituted for its native operations or PRISM parser/checker/compiler/runtime.
The saved entrypoint is mounted on temporary fixture roots for byte comparisons.
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
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from contextlib import contextmanager, asynccontextmanager, redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import shutil
import tempfile
import unittest
import yaml
from physics_lean_grounding_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_audit_grounding_workflow/workflow.yaml"
HIGH = "import Mathlib\nvariable (f : LinearMap)\n-- Quantity opaque Mass : Type\n/- PhysicsContext : String -/\n"
MEDIUM = "import Mathlib\nvariable (x : EuclideanSpace)\nstructure Quantity where\n  label : String\nopaque Mass : Type\n"
LOW = "import Init\n-- LinearMap\n/- HasDerivAt -/\n theorem t : True := by trivial\n"


def oracle():
    path = ROOT / "tests/mcp/fixtures/physics_lean_grounding_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "grounding_oracle", SourceFileLoader("grounding_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def mount(module, root):
    """Mount the legacy CLI's fixed filesystem context; no behavior is replaced."""
    lib = root / "MathformerPhysicsLib"
    values = dict(
        LEAN_ROOT=lib / "Lean",
        AUDIT_JSON=lib / "MATHLIB_GROUNDING_AUDIT.json",
        AUDIT_MD=lib / "MATHLIB_GROUNDING_AUDIT.md",
    )
    before = {key: getattr(module, key) for key in values}
    for key, value in values.items():
        setattr(module, key, value)
    try:
        yield
    finally:
        for key, value in before.items():
            setattr(module, key, value)


def report(evidence=None, blockers=None):
    return {
        "evidence": evidence or {},
        "blockers": blockers or [],
        "status": "legacy",
        "unrelated": {"retained": True},
    }


def case(root, name, text=HIGH, consistency=None):
    path = root / "MathformerPhysicsLib/Lean" / name
    path.mkdir(parents=True, exist_ok=True)
    (path / "MathformerPhysics.lean").write_text(text)
    if consistency is not None:
        (path / "consistency_report.json").write_text(json.dumps(consistency))
    return path


def clean(root):
    shutil.rmtree(root / "MathformerPhysicsLib", ignore_errors=True)
    (root / "MathformerPhysicsLib/Lean").mkdir(parents=True)


def files(root):
    return {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in document["provenance"]["sources"]
    ]


@asynccontextmanager
async def diagnosed_session(manager, *args):
    async with manager.open(*args) as remote:
        try:
            yield remote
        except Exception:
            import traceback

            traceback.print_exc()
            raise


class GroundingTests(unittest.TestCase):
    def test_native_entrypoint_equivalence(self):
        old = oracle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for mode in (
                "empty",
                "high",
                "mixed",
                "malformed_report",
                "bad_utf8",
                "markdown_failure",
            ):
                for self_test, update in (
                    (False, False),
                    (False, True),
                    (True, False),
                    (True, True),
                ):
                    with self.subTest(mode=mode, self_test=self_test, update=update):

                        def setup():
                            clean(root)
                            if mode != "empty":
                                evidence = {
                                    "background_packet_present": True,
                                    "final_derivation_review_style": "physics_final_hypothesis_review",
                                }
                                case(
                                    root,
                                    "formalphysics_a",
                                    HIGH,
                                    report(evidence, ["mathlib_grounding_low"]),
                                )
                            if mode in ("mixed", "malformed_report", "bad_utf8"):
                                second = case(
                                    root,
                                    "formalphysics_b",
                                    MEDIUM,
                                    report(
                                        {
                                            "compile_ok": True,
                                            "realness_ok": True,
                                            "anchor_ok": True,
                                        },
                                        ["kept", "kept", "mathlib_grounding_low"],
                                    ),
                                )
                                case(root, "formalphysics_c", LOW, report())
                                case(
                                    root, "formalphysics_d", HIGH
                                )  # absent reports are skipped
                                if mode == "malformed_report":
                                    (second / "consistency_report.json").write_text("{")
                                if mode == "bad_utf8":
                                    (second / "MathformerPhysics.lean").write_bytes(
                                        b"\xff"
                                    )
                            if mode == "markdown_failure":
                                (
                                    root
                                    / "MathformerPhysicsLib/MATHLIB_GROUNDING_AUDIT.md"
                                ).mkdir()
                            # Ineligible paths never enter discovery.
                            (
                                root / "MathformerPhysicsLib/Lean/formalphysics_empty"
                            ).mkdir()
                            ignored = root / "MathformerPhysicsLib/Lean/not_a_case"
                            ignored.mkdir()
                            (ignored / "MathformerPhysics.lean").write_text(LOW)

                        argv = (["--self-test"] if self_test else []) + (
                            ["--update-consistency"] if update else []
                        )
                        outcomes = []
                        for module in (old, source):
                            setup()
                            stream = io.StringIO()
                            with mount(module, root), redirect_stdout(stream):
                                try:
                                    outcome = ("return", module.main(argv))
                                except Exception as error:
                                    outcome = ("raise", type(error).__name__)
                            outcomes.append((outcome, stream.getvalue(), files(root)))
                        self.assertEqual(outcomes[0], outcomes[1])
                        if outcomes[1][0][0] == "return":
                            packet = json.loads(
                                (
                                    root
                                    / "MathformerPhysicsLib/MATHLIB_GROUNDING_AUDIT.json"
                                ).read_text()
                            )
                            expected = (
                                ["high", "medium", "low", "high"]
                                if mode in ("mixed", "malformed_report")
                                else [] if mode == "empty" else ["high"]
                            )
                            self.assertEqual(
                                [c["grounding_level"] for c in packet["cases"]],
                                expected,
                            )
                            self.assertEqual(
                                json.loads(outcomes[1][1]),
                                {"cases": len(expected), "updated_consistency": update},
                            )
                            if mode == "mixed" and update:
                                loaded = [
                                    json.loads(
                                        (
                                            root
                                            / "MathformerPhysicsLib/Lean"
                                            / f"formalphysics_{name}"
                                            / "consistency_report.json"
                                        ).read_text()
                                    )
                                    for name in "abc"
                                ]
                                self.assertEqual(
                                    [r["status"] for r in loaded],
                                    ["complete", "draft", "blocked"],
                                )
                                self.assertEqual(
                                    loaded[1]["blockers"],
                                    [
                                        "kept",
                                        "missing_physics_final_hypothesis_review",
                                        "mathlib_grounding_medium",
                                        "missing_background_dependency_plan",
                                    ],
                                )
                                self.assertEqual(
                                    loaded[0]["unrelated"], {"retained": True}
                                )
            # Signals exercise the typed-context requirement independently.
            signals = {
                "mathlib_native_surface_count": 1,
                "local_scaffold_count": 0,
                "opaque_dimension_surface_count": 0,
                "string_context_surface_count": 0,
                "typed_prop_context": False,
            }
            self.assertEqual(source.grounding_level(signals), "medium")
            signals["typed_prop_context"] = True
            self.assertEqual(source.grounding_level(signals), "high")
            for key in (
                "local_scaffold_count",
                "opaque_dimension_surface_count",
                "string_context_surface_count",
            ):
                self.assertEqual(source.grounding_level({**signals, key: 1}), "medium")
            self.assertEqual(
                source.grounding_level({**signals, "mathlib_native_surface_count": 0}),
                "low",
            )

    def test_registered_mcp_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_physics_lean_audit_grounding_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 20004},
        )
        self.assertIn(
            "scripts/audit_mathformer_physics_lean_grounding.py",
            [s["path"] for s in document["provenance"]["sources"]],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        # The authored generator source stays native and does not rewrite host YAML.
        spec = importlib.util.spec_from_file_location(
            "grounding_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        regenerated = next(
            d for d in normalizer.inventory() if d["id"] == document["id"]
        )
        self.assertEqual(regenerated, document)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "mounted"
            root.mkdir()
            manager = SessionManager()
            async with diagnosed_session(
                manager,
                "grounding",
                StdioConfig(
                    command=sys.executable,
                    args=[str(Path(__file__).resolve()), "--serve", str(root)],
                    cwd=str(ROOT),
                ),
                {"LUNAR_PLATFORM_ROOT": str(LUNAR)},
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(d, advertised=tools):
                    assets = snapshot(d)
                    compiled = compile_workflow(
                        "mcp:grounding",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        advertised,
                    )
                    return compiled, assets

                compiled, assets = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(self_test=False, update=False, doc=document):
                    selected, received = (
                        (compiled, assets) if doc is document else compile(doc)
                    )
                    self.assertTrue(selected["runnable"], selected["diagnostics"])
                    return await execute(
                        selected,
                        received,
                        {
                            "options": {
                                "self_test": self_test,
                                "update_consistency": update,
                            },
                            "repository_root": str(root),
                        },
                        remote,
                        authorize,
                    )

                def names(result):
                    return [
                        c.get("tool", "").removeprefix("mathformer_physics_grounding_")
                        for c in result["calls"]
                    ]

                def no_audit():
                    self.assertFalse(
                        (
                            root / "MathformerPhysicsLib/MATHLIB_GROUNDING_AUDIT.json"
                        ).exists()
                    )

                async def success(self_test=False, update=False, doc=document):
                    result = await run(self_test, update, doc)
                    self.assertEqual(result["status"], "accepted", result)
                    outputs = result["outputs"]
                    self.assertEqual(outputs["exit_code"], 0)
                    self.assertEqual(
                        outputs["printed_counts"],
                        {
                            "cases": len(outputs["audit_json"]["cases"]),
                            "updated_consistency": update,
                        },
                    )
                    self.assertEqual(
                        json.loads(
                            (
                                root
                                / "MathformerPhysicsLib/MATHLIB_GROUNDING_AUDIT.json"
                            ).read_text()
                        ),
                        outputs["audit_json"],
                    )
                    self.assertEqual(
                        (
                            root / "MathformerPhysicsLib/MATHLIB_GROUNDING_AUDIT.md"
                        ).read_text(),
                        outputs["audit_markdown"],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    return result

                for update in (False, True):
                    clean(root)
                    result = await success(update=update)
                    self.assertEqual(
                        result["outputs"]["audit_json"]["summary"]["cases"], 0
                    )
                    self.assertNotIn("audit_next", names(result))
                    self.assertNotIn("update_next", names(result))
                    clean(root)
                    result = await run(True, update)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(
                        names(result),
                        ["initialize_scan", "empty_traversal", "assert_grounding"],
                    )
                    no_audit()
                for self_test, update in (
                    (False, False),
                    (False, True),
                    (True, False),
                    (True, True),
                ):
                    clean(root)
                    first = case(
                        root,
                        "formalphysics_a",
                        HIGH,
                        report(
                            {
                                "background_packet_present": True,
                                "final_derivation_review_style": "physics_final_hypothesis_review",
                            }
                        ),
                    )
                    case(root, "formalphysics_b", HIGH)  # missing report
                    before = files(root)
                    result = await success(self_test, update)
                    self.assertEqual(
                        names(result),
                        [
                            "initialize_scan",
                            "audit_next",
                            "audit_next",
                            "assert_grounding" if self_test else "retain_cases",
                            "initialize_updates",
                            *(
                                ["update_next", "update_next"]
                                if update
                                else ["empty_traversal"]
                            ),
                            "emit_audit",
                        ],
                    )
                    self.assertEqual(
                        [c["case"] for c in result["outputs"]["audit_json"]["cases"]],
                        ["formalphysics_a", "formalphysics_b"],
                    )
                    if update:
                        self.assertEqual(
                            json.loads((first / "consistency_report.json").read_text())[
                                "status"
                            ],
                            "complete",
                        )
                    else:
                        self.assertEqual(
                            (first / "consistency_report.json").read_bytes(),
                            before[
                                "MathformerPhysicsLib/Lean/formalphysics_a/consistency_report.json"
                            ],
                        )
                # Mixed levels and ordered blocker/evidence updates match original bytes.
                clean(root)
                case(
                    root,
                    "formalphysics_b",
                    MEDIUM,
                    report(
                        {"compile_ok": True, "realness_ok": True, "anchor_ok": True},
                        ["kept", "kept"],
                    ),
                )
                case(root, "formalphysics_a", HIGH, report())
                case(root, "formalphysics_c", LOW, report())
                initial = files(root)
                old = oracle()
                with mount(old, root), redirect_stdout(io.StringIO()):
                    old.main(["--update-consistency"])
                expected = files(root)
                clean(root)
                for name, data in initial.items():
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                result = await success(update=True)
                self.assertEqual(files(root), expected)
                self.assertEqual(
                    [
                        c["grounding_level"]
                        for c in result["outputs"]["audit_json"]["cases"]
                    ],
                    ["high", "medium", "low"],
                )
                clean(root)
                case(root, "formalphysics_a", HIGH, report())
                case(root, "formalphysics_b", LOW, report())
                before = files(root)
                failed = await run(True, True)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(files(root), before)
                self.assertEqual(names(failed)[-1], "assert_grounding")
                # Exact reduced loop bound succeeds; one lower exhausts before emit.
                bounded = deepcopy(document)
                bounded["flow"]["steps"][1]["max_iterations"] = 2
                await success(doc=bounded)
                clean(root)
                case(root, "formalphysics_a")
                case(root, "formalphysics_b")
                bounded["flow"]["steps"][1]["max_iterations"] = 1
                failed = await run(doc=bounded)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(failed["failure_disposition"], "fail")
                self.assertEqual(names(failed), ["initialize_scan", "audit_next"])
                no_audit()
                bounded = deepcopy(document)
                bounded["flow"]["steps"][4]["max_iterations"] = 1
                clean(root)
                first = case(root, "formalphysics_a", HIGH, report())
                second = case(root, "formalphysics_b", HIGH, report())
                before = (second / "consistency_report.json").read_bytes()
                failed = await run(update=True, doc=bounded)
                self.assertEqual(failed["failure_disposition"], "fail")
                self.assertEqual(names(failed)[-1], "update_next")
                self.assertNotEqual(
                    json.loads((first / "consistency_report.json").read_text())[
                        "status"
                    ],
                    "legacy",
                )
                self.assertEqual(
                    (second / "consistency_report.json").read_bytes(), before
                )
                no_audit()
                # Real failures propagate without retry or rollback of prior writes.
                (second / "consistency_report.json").write_text("{")
                failed = await run(update=True)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(names(failed).count("update_next"), 2)
                no_audit()
                (second / "MathformerPhysics.lean").write_bytes(b"\xff")
                failed = await run(update=True)
                self.assertEqual(failed["status"], "failed")
                self.assertNotIn("initialize_updates", names(failed))
                no_audit()
                clean(root)
                case(root, "formalphysics_a")
                (root / "MathformerPhysicsLib/MATHLIB_GROUNDING_AUDIT.md").mkdir()
                failed = await run()
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(names(failed)[-1], "emit_audit")
                self.assertTrue(
                    (
                        root / "MathformerPhysicsLib/MATHLIB_GROUNDING_AUDIT.json"
                    ).exists()
                )
                clean(root)
                case(root, "formalphysics_a")
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                failed = await run(doc=budget)
                self.assertEqual(failed["status"], "failed")
                self.assertIn("budget", failed["calls"][-1]["error"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in failed["calls"]
                    ),
                    1,
                )
                no_audit()
                # Service root authorization uses real registrations and public config.
                outside = base / "outside"
                (outside / "MathformerPhysicsLib").mkdir(parents=True)
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_physics_grounding_emit_audit",
                        {
                            "repository_root": str(outside),
                            "cases": [],
                            "case_history": [],
                            "options": {
                                "self_test": False,
                                "update_consistency": False,
                            },
                        },
                    )
                self.assertFalse(
                    (
                        outside / "MathformerPhysicsLib/MATHLIB_GROUNDING_AUDIT.json"
                    ).exists()
                )
                # Check the full normalized discovery domain without 10000 remote iterations.
                clean(root)
                shared = root / "fixture.lean"
                shared.write_text(HIGH)
                lean = root / "MathformerPhysicsLib/Lean"
                for i in range(10000):
                    path = lean / f"formalphysics_{i:05d}"
                    path.mkdir()
                    (path / "MathformerPhysics.lean").symlink_to(shared)
                prepared = await remote.call(
                    "mathformer_physics_grounding_initialize_scan",
                    {
                        "repository_root": str(root),
                        "options": {"self_test": False, "update_consistency": False},
                    },
                )
                self.assertEqual(len(prepared["state"]["pending"]), 10000)
                self.assertEqual(prepared["state"]["cases"], [])
                self.assertEqual(
                    prepared["state"]["pending"], sorted(prepared["state"]["pending"])
                )
                path = lean / "formalphysics_overflow"
                path.mkdir()
                (path / "MathformerPhysics.lean").symlink_to(shared)
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_physics_grounding_initialize_scan",
                        {
                            "repository_root": str(root),
                            "options": {
                                "self_test": False,
                                "update_consistency": False,
                            },
                        },
                    )
                self.assertEqual(
                    len(source.discover_cases(lean)), 10001
                )  # CLI has no cap
            self.assertFalse(manager.active)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        import mcp_server

        mcp_server.apply_runtime_config(allowed_write_roots=[sys.argv[2]])
        mcp_server.mcp.run(transport="stdio")
    else:
        unittest.main(verbosity=2)
