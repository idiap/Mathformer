#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Run the supplied profile through actual registered MCP and Lunar/PRISM.

Reuse the selected suite's deterministic command-boundary fixture and acceptance
scenarios. All eleven local stage entrypoints run for real in temporary mounts.
This source has no external model/provider or compiler to emulate. PRISM parsing,
checking, compilation and execution are real, with no runtime substitution.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_sympy_equational_trace_loop_tests as shared
import hashlib
import importlib.util
import json
import unittest
from unittest.mock import patch

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/profile/profile_executable_symbolic_derivation_workflow/workflow.yaml"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/executable-symbolic-derivation.workflow.json"
)
# The shared scenarios serialize this explicitly supplied document under its
# real repository path. They never load a different installed loop contract.
shared.DESCRIPTOR = DESCRIPTOR


class Tests(shared.Tests):
    def test_authored_contract_and_provenance(self):
        self.assertEqual(
            self.doc["id"], "profile_executable_symbolic_derivation_workflow"
        )
        self.assertEqual(self.doc["aliases"], ["executable_symbolic_derivation"])
        self.assertEqual(self.doc["lifecycle"], "active")
        self.assertEqual(self.doc, json.loads(AUTHORED.read_text()))
        self.assertEqual(
            self.doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 15},
        )
        self.assertEqual(self.doc["policy"]["effects"]["network"], [])
        self.assertEqual(
            self.doc["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertEqual(self.doc["policy"]["resume"]["mode"], "none")
        self.assertEqual(
            self.doc["policy"]["claim_ceiling"],
            "Source-linked specification only; no scientific truth, runtime qualification or promotion.",
        )
        self.assertEqual(
            self.doc["outputs"]["exit_code"]["value"],
            {"ref": "flow.outputs.completion.exit_code"},
        )
        self.assertEqual(
            self.doc["extensions"]["mathformer.materialization"]["sources_in_order"],
            [str(p) for p in shared.source().SOURCES],
        )
        self.assertEqual(
            self.doc["extensions"]["mathformer.source"]["native_id"],
            "executable_symbolic_derivation",
        )
        for row in self.doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
                row["path"],
            )
        self.assertIn(
            "tests/sympy/run_controlled_suite.py",
            [r["path"] for r in self.doc["provenance"]["sources"]],
        )
        # The selected source backup provided for this task is byte-identical to
        # the checked-in frozen entrypoint exercised by the shared comparisons.
        self.assertEqual(
            hashlib.sha256(
                (
                    ROOT / "tests/mcp/fixtures/sympy_equational_trace_original.py.txt"
                ).read_bytes()
            ).hexdigest(),
            "8e53dbfa203e0dbeeb12cf02c56ef62335773cad0292db344e6ebe4791642d3d",
        )
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location(
            "symbolic_profile_normalizer", path
        )
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        self.assertEqual(
            normalizer.executable_symbolic_derivation_descriptor(), self.doc
        )
        # Limit unrelated inventories only; exercise the actual profile branch.
        with (
            patch.object(normalizer.hub, "build_registry", return_value={}),
            patch.object(normalizer.hub, "build_intent_routes", return_value=[]),
            patch.object(normalizer, "parse_loop_contracts", return_value=[]),
        ):
            generated = next(
                d for d in normalizer.inventory() if d["id"] == self.doc["id"]
            )
        self.assertEqual(generated, self.doc)

    async def scenario(self, base):
        # Inherited scenarios check runnable qualification, actual bound calls,
        # exact argv and state histories, both preflight failures, case fail-fast,
        # continuation, timeout/launch/write propagation, both loop exhaustions,
        # budgets, denied writes and equivalence to the original entrypoint.
        await super().scenario(base)
        report = json.loads((base / "success/out/suite_report.json").read_text())
        for case, sample_count in zip(
            report["cases"], [101, 40401, 606, 201, 1], strict=True
        ):
            folder = Path(case["artifact"]).parent
            self.assertEqual(case["consistency"]["status"], "complete")
            numeric = json.loads((folder / "counterexample_report.json").read_text())
            self.assertTrue(numeric["passed"])
            self.assertEqual(numeric["counterexamples"], [])
            self.assertEqual(numeric["sample_count"], sample_count)
            self.assertTrue((folder / "sympy_consistency_report.md").is_file())

        # Verify the profile's extra top-level exit_code port through the real
        # runtime, including failure data returned by the early branch.
        manager = shared.SessionManager()
        server = (
            "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
            + repr(
                [
                    str(ROOT / "scripts"),
                    str(ROOT / "tests/mcp/fixtures"),
                    str(ROOT),
                    *shared.SITES,
                ]
            )
            + ";from sympy_equational_trace_boundary import serve;serve("
            + repr(str(base))
            + ")"
        )
        async with manager.open(
            "profile",
            shared.StdioConfig(
                command=sys.executable,
                args=["-c", server],
                cwd=str(ROOT),
                timeout_seconds=600,
            ),
            {},
        ) as remote:
            assets = shared.snapshot(self.doc)
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]
            compiled = shared.compile_workflow(
                "mcp:profile", shared.workflow_documents([DESCRIPTOR], assets)[0], tools
            )
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])

            async def allow():
                pass

            for code, mode, command_count in [
                (0, None, 47),
                (1, {"stage": "dependency_probe", "fault": "nonzero"}, 1),
            ]:
                root = shared.fixture(base / ("profile-exit-code-" + str(code)), mode)
                result = await shared.execute(
                    compiled,
                    assets,
                    {
                        "context": {
                            "working_directory": str(root),
                            "allow_mutating": True,
                        },
                        "artifact_root": "out",
                        "json_output": True,
                    },
                    remote,
                    allow,
                )
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"]["exit_code"], code)
                self.assertEqual(
                    result["outputs"]["exit_code"],
                    result["outputs"]["completion"]["exit_code"],
                )
                self.assertEqual(len(shared.ledger(root)), command_count)
        self.assertFalse(manager.active)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
