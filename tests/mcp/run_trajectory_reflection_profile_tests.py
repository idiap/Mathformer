#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Qualify the trajectory profile's native observer, offline through Lunar.

Reuse the observer's deterministic report/log/baseline/critic fixtures and
original-entrypoint oracle. There are no model or external compiler calls in
this source, so no production boundary needs substitution. The actual PRISM
parser/checker/compiler/runtime and production MCP registrations run unchanged.
The candidate/installed descriptor must be supplied as WORKFLOW_CONTRACT_PATH.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])

import json
import unittest

import run_reflection_observer_workflow_tests as observer
from normalize_workflows_tools import source as normalizer_source


class TrajectoryReflectionProfileTests(observer.ReflectionObserverTests):
    identity = "profile_trajectory_reflection_and_process_improvement_workflow"
    descriptor = (
        "skills/control/workflow-contract-validator/references/"
        "normalized-workflows/profile/" + identity + "/workflow.yaml"
    )
    authored = (
        "skills/control/workflow-contract-validator/references/"
        "trajectory-reflection-profile.workflow.json"
    )

    def test_authored_generator_preserves_identity_and_authority(self):
        doc = observer.document()
        self.assertEqual(doc["id"], self.identity)
        self.assertEqual(
            doc["aliases"], ["trajectory_reflection_and_process_improvement"]
        )
        self.assertEqual(doc["extensions"]["mathformer.source"]["category"], "profile")
        self.assertEqual(doc["provenance"]["coverage"], "partial")
        self.assertIn("dispositions remain declarative", doc["provenance"]["gaps"][0])
        for action in (
            "execute_regression_commands",
            "apply_proposed_changes",
            "adopt_reasoning_revision",
        ):
            self.assertIn(action, doc["policy"]["authority"]["forbidden"])
        self.assertEqual(doc["policy"]["effects"]["network"], [])
        self.assertEqual(doc["policy"]["resume"]["mode"], "none")
        self.assertIn(
            observer.source().__file__.removeprefix(str(ROOT) + "/"),
            [row["path"] for row in doc["provenance"]["sources"]],
        )
        # Exercise the native generator in memory; never write host YAML/catalog
        # or run a scientific workflow just to qualify this component.
        self.assertEqual(
            normalizer_source().trajectory_reflection_profile_descriptor(), doc
        )
        self.assertEqual(doc, json.loads((ROOT / self.authored).read_text()))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TrajectoryReflectionProfileTests
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    # A skipped-only or empty invocation must never qualify runtime bindings.
    sys.exit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
