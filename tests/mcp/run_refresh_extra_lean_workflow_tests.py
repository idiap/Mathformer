#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Original/source/MCP/Lunar parity with only the external compiler substituted."""

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
    str(ROOT / "tests/mcp/fixtures"),
]
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
from importlib.machinery import SourceFileLoader
import importlib.util
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
import refresh_formalphysics_extra_lean_reports as native
import refresh_compiler_boundary as boundary
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_formalphysics_refresh_extra_lean_reports_workflow/workflow.yaml"


def oracle():
    path = ROOT / "tests/mcp/fixtures/refresh_extra_lean_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "refresh_oracle", SourceFileLoader("refresh_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(root):
    for case, spec in native.CASES.items():
        source = (
            root
            / native.SOURCE_ROOT.relative_to(native.REPO_ROOT)
            / f"{spec['rank']}_{case}.tex"
        )
        lean = (
            root
            / native.LIB_ROOT.relative_to(native.REPO_ROOT)
            / case
            / "MathformerPhysics.lean"
        )
        source.parent.mkdir(parents=True, exist_ok=True)
        lean.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            "Source law: energy conservation. Smooth field in an inertial frame.\n"
        )
        lean.write_text(
            "import Mathlib\n-- source-backed smooth field energy conservation\ntheorem fixture : (1 : Nat) = 1 := rfl\n"
        )
    return root


def outputs(root):
    return {
        str(p.relative_to(root)): p.read_bytes()
        for base in ("artifacts", "libraries")
        for p in (root / base).rglob("*")
        if p.is_file()
    }


def run_main(module, root):
    stream, calls = io.StringIO(), []

    def compiler(args, **kwargs):
        calls.append(args)
        return boundary.run(args, **kwargs)

    with (
        patch.multiple(
            module,
            REPO_ROOT=root,
            SOURCE_ROOT=root / native.SOURCE_ROOT.relative_to(native.REPO_ROOT),
            ARTIFACT_ROOT=root / native.ARTIFACT_ROOT.relative_to(native.REPO_ROOT),
            LIB_ROOT=root / native.LIB_ROOT.relative_to(native.REPO_ROOT),
        ),
        patch.object(module.subprocess, "run", compiler),
        redirect_stdout(stream),
    ):
        code = module.main()
    return code, stream.getvalue(), calls


def snapshot(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="refresh-extra-lean-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def test_native_shared_steps_match_original(self):
        old, new = fixture(self.directory / "old"), fixture(self.directory / "new")
        before = run_main(oracle(), old)
        after = run_main(native, new)
        self.assertEqual(after, before)
        self.assertEqual(after[0], 0)
        self.assertEqual(after[1].splitlines(), list(native.CASES))
        self.assertEqual(
            len(after[2]), 80
        )  # one compiler and nine real helper programs per case
        self.assertEqual(outputs(new), outputs(old))
        # Independent feature checks cover all fixed branches plus absent features.
        self.assertEqual(native.assumption_packet("empty", [])["assumptions"], [])
        self.assertEqual(len(native.type_packet("empty", [])["lean_surfaces"]), 2)
        self.assertEqual(
            len(native.background_packet("empty", [])["background_items"]), 4
        )
        for cursor, (case, spec) in enumerate(native.CASES.items()):
            selected = native.select_case(cursor)
            self.assertEqual(selected, dict(case_id=case, **spec))
            directory = new / native.ARTIFACT_ROOT.relative_to(native.REPO_ROOT) / case
            flags = json.loads((directory / "type_system_packet.json").read_text())[
                "feature_flags"
            ]
            self.assertEqual(
                flags["has_vectors"],
                bool(set(spec["features"]) & {"quantum", "vector"}),
            )
            self.assertEqual(flags["has_integrals"], "calculus" in spec["features"])
            assumptions = json.loads(
                (directory / "assumption_packet.json").read_text()
            )["detected_context"]
            self.assertEqual("positivity" in assumptions, "quantum" in spec["features"])
            self.assertEqual("nonzero" in assumptions, "nonzero" in spec["features"])
            self.assertEqual(
                (directory / "physics_lean_consistency_report.json").read_bytes(),
                (
                    new
                    / native.LIB_ROOT.relative_to(native.REPO_ROOT)
                    / case
                    / "consistency_report.json"
                ).read_bytes(),
            )
        for cursor in (-1, 8):
            with self.assertRaises(IndexError):
                native.select_case(cursor)
        # Compiler failure preserves its log/candidate and prevents packet construction.
        for module, label in (
            (native, "new-compile-fail"),
            (oracle(), "old-compile-fail"),
        ):
            failed = fixture(self.directory / label)
            with self.assertRaisesRegex(RuntimeError, "Lean failed"):
                run_main(module, failed)
            second = (
                failed
                / native.ARTIFACT_ROOT.relative_to(native.REPO_ROOT)
                / list(native.CASES)[1]
            )
            self.assertTrue((second / "lean_execution.log").exists())
            self.assertFalse((second / "type_system_packet.json").exists())
        self.assertEqual(
            outputs(self.directory / "new-compile-fail"),
            outputs(self.directory / "old-compile-fail"),
        )

    def test_registered_tools_and_real_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_formalphysics_refresh_extra_lean_reports_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/refresh-extra-lean-reports.workflow.json"
                ).read_text()
            ),
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        async with manager.open(
            "refresh",
            StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=["tests/mcp/fixtures/refresh_compiler_boundary.py"],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=tools):
                assets = snapshot(doc)
                selected = workflow_documents([DESCRIPTOR], assets)[0]
                return compile_workflow("mcp:refresh", selected, inventory), assets

            compiled, assets = compile(document)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
            self.assertFalse(compile(document, [])[0]["runnable"])

            async def authorize():
                pass

            async def run(root, doc=None):
                workflow, received = compile(doc) if doc else (compiled, assets)
                return await execute(
                    workflow,
                    received,
                    {"repository_root": str(root)},
                    remote,
                    authorize,
                )

            root, old = fixture(self.directory / "runtime"), fixture(
                self.directory / "oracle"
            )
            original = run_main(oracle(), old)
            result = await run(root)
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(result["outputs"], {"exit_code": original[0]})
            self.assertEqual(outputs(root), outputs(old))
            expected = [
                "select_case",
                "prepare_compile",
                "packets",
                "critics",
                "reviews",
                "aggregate_copy",
                "advance",
            ] * 8
            self.assertEqual(
                [c["tool"] for c in result["calls"]],
                ["mathformer_refresh_" + n for n in expected],
            )
            self.assertTrue(result["runtime"]["effect_records"])
            self.assertTrue(result["replay_artifacts"])
            # Public cursor projection and normal eighth-iteration termination.
            for cursor, case_id in enumerate(native.CASES):
                selected = await remote.call(
                    "mathformer_refresh_select_case", {"cursor": cursor}
                )
                self.assertEqual(selected["case"], native.select_case(cursor))
                completed = dict(
                    case_id=case_id,
                    source=str(
                        root
                        / native.SOURCE_ROOT.relative_to(native.REPO_ROOT)
                        / f"{native.CASES[case_id]['rank']}_{case_id}.tex"
                    ),
                    lean=str(
                        root
                        / native.LIB_ROOT.relative_to(native.REPO_ROOT)
                        / case_id
                        / "MathformerPhysics.lean"
                    ),
                    directory=str(
                        root
                        / native.ARTIFACT_ROOT.relative_to(native.REPO_ROOT)
                        / case_id
                    ),
                )
                advanced = await remote.call(
                    "mathformer_refresh_advance",
                    {"cursor": cursor, "completed": completed},
                )
                self.assertEqual(advanced, {"cursor": cursor + 1, "done": cursor == 7})
            forged = dict(completed, directory=str(self.directory))
            with self.assertRaises(Exception):
                await remote.call(
                    "mathformer_refresh_critics",
                    {"files": forged, "repository_root": str(root)},
                )
            # Exact stopping/budget paths use the same compiled workflow and native tools.
            for label, count in [
                ("runtime-compile-fail", 9),
                ("runtime-helper-fail", 5),
            ]:
                failed = fixture(self.directory / label)
                result = await run(failed)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), count)
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                if "helper" in label:
                    directory = (
                        failed
                        / native.ARTIFACT_ROOT.relative_to(native.REPO_ROOT)
                        / next(iter(native.CASES))
                    )
                    self.assertTrue((directory / "physics_final_review.json").exists())
                    self.assertFalse(
                        (directory / "physics_lean_consistency_report.json").exists()
                    )
            bounded = deepcopy(document)
            bounded["flow"]["max_iterations"] = 1
            result = await run(fixture(self.directory / "exhausted"), bounded)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 7)
            self.assertIn("exhaust", str(result).lower())
            budget = deepcopy(document)
            budget["policy"]["limits"]["max_operation_calls"] = 3
            result = await run(fixture(self.directory / "budget"), budget)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 3
            )
            self.assertIn("budget", str(result).lower())
            with self.assertRaises(Exception):
                await remote.call("mathformer_refresh_select_case", {"cursor": 8})
            # Service policy is part of the actual registered tool, checked before writes.
        self.assertFalse(manager.active)
        blocked = fixture(self.directory / "readonly")
        async with manager.open(
            "readonly-refresh",
            StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=["tests/mcp/fixtures/refresh_compiler_boundary.py", "--readonly"],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            with self.assertRaises(Exception):
                await remote.call(
                    "mathformer_refresh_prepare_compile",
                    {"case": native.select_case(0), "repository_root": str(blocked)},
                )
            self.assertFalse((blocked / "artifacts").exists())
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
