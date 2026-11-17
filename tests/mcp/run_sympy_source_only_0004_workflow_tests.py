#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Run the shared native/MCP/Lunar/PRISM fixtures for the 0004 contract.

WORKFLOW_CONTRACT_PATH must explicitly select the candidate or installed file.
All scientific inputs and writes are temporary. The native five stage CLIs,
their gates, controller, logging and report emission are exercised unchanged.
There is no model/provider or external compiler boundary in these stages;
the real PRISM parser, checker, compiler and runtime are used.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])

import unittest  # noqa: E402
import run_sympy_source_only_workflow_tests as suite  # noqa: E402

suite.CASE = "formalphysics_0004"
suite.ID = "hub_physics_sympy_source_only_recursive_0004_workflow"
suite.DESCRIPTOR = (
    "skills/control/workflow-contract-validator/references/normalized-workflows/hub/"
    + suite.ID
    + "/workflow.yaml"
)
suite.AUTHORED = ROOT / (
    "skills/control/workflow-contract-validator/references/"
    "sympy-source-only-0004.workflow.json"
)
suite.OUTPUT_PORT = "report"

if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(suite.SourceOnlyTests)
    )
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
