#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real registered MCP tools and Lunar/PRISM over temporary native audit inputs.

No provider or external Lean compiler occurs in this textual workflow. Filesystem
fixtures are its deterministic inputs; the real PRISM compiler/runtime is used.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(Path(__file__).parent),
]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import yaml

import run_physics_lean_grounding_workflow_tests as fixture
from physics_lean_grounding_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.workflow_contract.validator import validate
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_update_grounding_audit_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/physics-lean-update-grounding.workflow.json"
PREFIX = "mathformer_physics_grounding_"


def document():
    return yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())


def snapshot(doc):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in doc["provenance"]["sources"]
    ]


class UpdateGroundingTests(unittest.TestCase):
    def test_native_entrypoint_equivalence(self):
        # Saved pre-extraction entrypoint: all four CLI flag combinations, empty,
        # high/mixed levels, bad reads/JSON and JSON-before-Markdown failures.
        fixture.GroundingTests(
            "test_native_entrypoint_equivalence"
        ).test_native_entrypoint_equivalence()

    def test_contract_and_generator(self):
        doc = document()
        self.assertEqual(doc["id"], "hub_physics_lean_update_grounding_audit_workflow")
        self.assertEqual(doc["aliases"], ["physics-lean:update-grounding-audit"])
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 2052},
        )
        self.assertEqual(doc["policy"]["failure"]["retry"]["max_attempts"], 1)
        # The supplied candidate may live outside the project before installation.
        # Validate its equal authored source with repository-relative provenance.
        self.assertEqual(json.loads((ROOT / AUTHORED).read_text()), doc)
        validation = validate(ROOT / AUTHORED, ROOT, True)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertIn(
            "scripts/audit_mathformer_physics_lean_grounding.py",
            [s["path"] for s in doc["provenance"]["sources"]],
        )
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        spec = importlib.util.spec_from_file_location(
            "update_grounding_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        self.assertEqual(
            next(d for d in normalizer.inventory() if d["id"] == doc["id"]), doc
        )

    def test_registered_mcp_lunar_paths(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = document()
        with tempfile.TemporaryDirectory(prefix="update-grounding-") as directory:
            base = Path(directory)
            root = (base / "mount").resolve()
            root.mkdir()
            manager = SessionManager()
            config = StdioConfig(
                command=sys.executable,
                args=[str(Path(__file__).resolve()), "--serve", str(root)],
                cwd=str(ROOT),
            )
            async with fixture.diagnosed_session(
                manager, "update-grounding", config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(selected, advertised=tools):
                    assets = snapshot(selected)
                    bound = compile_workflow(
                        "mcp:update-grounding",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        advertised,
                    )
                    return bound, assets

                compiled, assets = compile(doc)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertEqual(compiled["runtime_status"], "ready")
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
                self.assertFalse(
                    compile(
                        doc,
                        [t for t in tools if t["name"] != PREFIX + "discover_update"],
                    )[0]["runnable"]
                )
                self.assertEqual(
                    len([m for m in compiled["source_mapping"] if m["role"] == "loop"]),
                    2,
                )

                async def authorize():
                    pass

                async def run(selected=doc, scope=None):
                    bound, received = (
                        (compiled, assets) if selected is doc else compile(selected)
                    )
                    self.assertTrue(bound["runnable"], bound["diagnostics"])
                    inputs = {
                        "repository_root": str(root),
                        "scope": (
                            {
                                "eligible_paths": source.discover_cases(
                                    root / "MathformerPhysicsLib/Lean"
                                )
                            }
                            if scope is None
                            else scope
                        ),
                    }
                    return await execute(bound, received, inputs, remote, authorize)

                def names(result):
                    return [
                        c.get("tool", "").removeprefix(PREFIX) for c in result["calls"]
                    ]

                def no_audit():
                    self.assertFalse(
                        (
                            root / "MathformerPhysicsLib/MATHLIB_GROUNDING_AUDIT.json"
                        ).exists()
                    )

                async def success(selected=doc):
                    result = await run(selected)
                    self.assertEqual(result["status"], "accepted", result["calls"])
                    out = result["outputs"]
                    self.assertEqual(out["exit_code"], 0)
                    self.assertEqual(
                        out["printed_counts"],
                        {
                            "cases": len(out["audit_json"]["cases"]),
                            "updated_consistency": True,
                        },
                    )
                    self.assertEqual(
                        json.loads(
                            (
                                root
                                / "MathformerPhysicsLib/MATHLIB_GROUNDING_AUDIT.json"
                            ).read_text()
                        ),
                        out["audit_json"],
                    )
                    self.assertEqual(
                        (
                            root / "MathformerPhysicsLib/MATHLIB_GROUNDING_AUDIT.md"
                        ).read_text(),
                        out["audit_markdown"],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    return result

                fixture.clean(root)
                result = await success()
                self.assertEqual(
                    names(result),
                    [
                        "discover_update",
                        "empty_traversal",
                        "extract_cases",
                        "prepare_updates",
                        "empty_traversal",
                        "emit_audit",
                    ],
                )
                self.assertEqual(result["outputs"]["audit_json"]["summary"]["cases"], 0)
                # Unsorted creation, all classifications and report status branches,
                # missing reports, deduplication, and ignored paths; compare bytes.
                fixture.clean(root)
                fixture.case(root, "formalphysics_c", fixture.LOW, fixture.report())
                fixture.case(
                    root,
                    "formalphysics_b",
                    fixture.MEDIUM,
                    fixture.report(
                        {"compile_ok": True, "realness_ok": True, "anchor_ok": True},
                        ["keep", "keep", "mathlib_grounding_low"],
                    ),
                )
                fixture.case(
                    root,
                    "formalphysics_a",
                    fixture.HIGH,
                    fixture.report(
                        {
                            "background_packet_present": True,
                            "final_derivation_review_style": "physics_final_hypothesis_review",
                        },
                        ["mathlib_grounding_low"],
                    ),
                )
                fixture.case(root, "formalphysics_d", fixture.HIGH)
                fixture.case(root, "ignored", fixture.LOW)
                (root / "MathformerPhysicsLib/Lean/formalphysics_empty").mkdir()
                initial = fixture.files(root)
                old = fixture.oracle()
                stream = io.StringIO()
                with fixture.mount(old, root), redirect_stdout(stream):
                    self.assertEqual(old.main(["--update-consistency"]), 0)
                expected = fixture.files(root)
                fixture.clean(root)
                for name, content in initial.items():
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
                result = await success()
                self.assertEqual(fixture.files(root), expected)
                self.assertEqual(
                    json.loads(stream.getvalue()), result["outputs"]["printed_counts"]
                )
                self.assertEqual(
                    names(result),
                    [
                        "discover_update",
                        *(["audit_next"] * 4),
                        "extract_cases",
                        "prepare_updates",
                        *(["update_next"] * 4),
                        "emit_audit",
                    ],
                )
                self.assertEqual(
                    [
                        c["grounding_level"]
                        for c in result["outputs"]["audit_json"]["cases"]
                    ],
                    ["high", "medium", "low", "high"],
                )
                reports = [
                    json.loads(
                        (
                            root
                            / "MathformerPhysicsLib/Lean"
                            / f"formalphysics_{i}"
                            / "consistency_report.json"
                        ).read_text()
                    )
                    for i in "abc"
                ]
                self.assertEqual(
                    [r["status"] for r in reports], ["complete", "draft", "blocked"]
                )
                self.assertEqual(
                    reports[1]["blockers"],
                    [
                        "keep",
                        "missing_physics_final_hypothesis_review",
                        "mathlib_grounding_medium",
                        "missing_background_dependency_plan",
                    ],
                )
                self.assertEqual(reports[0]["unrelated"], {"retained": True})
                # Inspect actual carried states and serialized history through MCP.
                state = (
                    await remote.call(
                        PREFIX + "discover_update",
                        {
                            "repository_root": str(root),
                            "scope": {
                                "eligible_paths": source.discover_cases(
                                    root / "MathformerPhysicsLib/Lean"
                                )
                            },
                        },
                    )
                )["state"]
                self.assertEqual(state["cases"], [])
                self.assertEqual(state["case_history"], [])
                for index in range(4):
                    value = await remote.call(
                        PREFIX + "audit_next",
                        {"repository_root": str(root), "state": state},
                    )
                    state = value["state"]
                    self.assertEqual(len(state["pending"]), 3 - index)
                    self.assertEqual(
                        [json.loads(v) for v in state["case_history"]], state["cases"]
                    )
                    self.assertEqual(value["done"], index == 3)
                    self.assertEqual(state["nonempty"], index < 3)
                self.assertEqual(
                    state["cases"], result["outputs"]["audit_json"]["cases"]
                )
                # Witness mismatch fails before scanning or writing.
                fixture.clean(root)
                fixture.case(root, "formalphysics_a")
                failed = await run(scope={"eligible_paths": []})
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(names(failed), ["discover_update"])
                no_audit()
                # Reduced real bounds: exact-bound success, then scan exhaustion.
                fixture.case(root, "formalphysics_b")
                bounded = deepcopy(doc)
                bounded["flow"]["steps"][1]["max_iterations"] = 2
                bounded["flow"]["steps"][4]["max_iterations"] = 2
                await success(bounded)
                fixture.clean(root)
                first = fixture.case(
                    root, "formalphysics_a", consistency=fixture.report()
                )
                second = fixture.case(
                    root, "formalphysics_b", consistency=fixture.report()
                )
                bounded["flow"]["steps"][1]["max_iterations"] = 1
                failed = await run(bounded)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(failed["failure_disposition"], "fail")
                self.assertEqual(names(failed), ["discover_update", "audit_next"])
                self.assertEqual(
                    json.loads((first / "consistency_report.json").read_text())[
                        "status"
                    ],
                    "legacy",
                )
                no_audit()
                bounded["flow"]["steps"][1]["max_iterations"] = 2
                bounded["flow"]["steps"][4]["max_iterations"] = 1
                before = (second / "consistency_report.json").read_bytes()
                failed = await run(bounded)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(failed["failure_disposition"], "fail")
                self.assertEqual(names(failed).count("update_next"), 1)
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
                # Parse and read errors propagate once, retaining earlier writes.
                (second / "consistency_report.json").write_text("{")
                failed = await run()
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(names(failed).count("update_next"), 2)
                self.assertNotIn("emit_audit", names(failed))
                self.assertNotEqual(
                    json.loads((first / "consistency_report.json").read_text())[
                        "status"
                    ],
                    "legacy",
                )
                no_audit()
                (second / "MathformerPhysics.lean").write_bytes(b"\xff")
                failed = await run()
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(
                    names(failed), ["discover_update", "audit_next", "audit_next"]
                )
                no_audit()
                fixture.clean(root)
                fixture.case(root, "formalphysics_a")
                (root / "MathformerPhysicsLib/MATHLIB_GROUNDING_AUDIT.md").mkdir()
                failed = await run()
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(names(failed)[-1], "emit_audit")
                self.assertTrue(
                    (
                        root / "MathformerPhysicsLib/MATHLIB_GROUNDING_AUDIT.json"
                    ).exists()
                )
                fixture.clean(root)
                fixture.case(root, "formalphysics_a")
                budget = deepcopy(doc)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                failed = await run(budget)
                self.assertEqual(failed["status"], "failed")
                self.assertIn("budget", failed["calls"][-1]["error"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in failed["calls"]
                    ),
                    1,
                )
                no_audit()
                # The published domain limit is checked before any case read;
                # the native CLI still discovers all cases without a cap.
                fixture.clean(root)
                shared = root / "fixture.lean"
                shared.write_text(fixture.HIGH)
                lean = root / "MathformerPhysicsLib/Lean"
                for i in range(1024):
                    path = lean / f"formalphysics_{i:04d}"
                    path.mkdir()
                    (path / "MathformerPhysics.lean").symlink_to(shared)
                paths = source.discover_cases(lean)
                initialized = await remote.call(
                    PREFIX + "discover_update",
                    {"repository_root": str(root), "scope": {"eligible_paths": paths}},
                )
                self.assertEqual(
                    initialized["options"],
                    {"update_consistency": True, "self_test": False},
                )
                self.assertEqual(initialized["state"]["pending"], paths)
                self.assertEqual(len(paths), 1024)
                extra = lean / "formalphysics_overflow"
                extra.mkdir()
                (extra / "MathformerPhysics.lean").symlink_to(shared)
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "discover_update",
                        {
                            "repository_root": str(root),
                            "scope": {"eligible_paths": source.discover_cases(lean)},
                        },
                    )
                self.assertEqual(len(source.discover_cases(lean)), 1025)
                no_audit()
                outside = base / "outside"
                (outside / "MathformerPhysicsLib").mkdir(parents=True)
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "discover_update",
                        {
                            "repository_root": str(outside),
                            "scope": {"eligible_paths": []},
                        },
                    )
                self.assertEqual(list((outside / "MathformerPhysicsLib").iterdir()), [])
            self.assertFalse(manager.active)
            # Real service mutation gate rejects even an empty selected action.
            readonly = StdioConfig(
                command=sys.executable,
                args=[str(Path(__file__).resolve()), "--serve-readonly", str(root)],
                cwd=str(ROOT),
            )
            async with manager.open(
                "update-grounding-readonly",
                readonly,
                {"LUNAR_PLATFORM_ROOT": str(LUNAR)},
            ) as remote:
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "discover_update",
                        {"repository_root": str(root), "scope": {"eligible_paths": []}},
                    )
            self.assertFalse(manager.active)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("--serve"):
        import mcp_server

        mcp_server.apply_runtime_config(allowed_write_roots=[sys.argv[2]])
        if sys.argv[1] == "--serve-readonly":
            mcp_server._READONLY = True
        mcp_server.mcp.run(transport="stdio")
    else:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(UpdateGroundingTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        sys.exit(
            0
            if result.wasSuccessful() and result.testsRun and not result.skipped
            else 1
        )
