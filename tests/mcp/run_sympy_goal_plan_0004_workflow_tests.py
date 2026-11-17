#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Run the shared planner oracle and real MCP/Lunar fixtures for case 0004.

WORKFLOW_CONTRACT_PATH explicitly selects the candidate or installed contract.
Only temporary Python artifact fixtures are imported; no production derivation,
provider, external compiler or theorem prover runs.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])

import run_sympy_goal_plan_workflow_tests as suite  # noqa: E402

suite.CASE_ID = "formalphysics_0004"
suite.WORKFLOW_ID = "hub_physics_sympy_goal_sample_plan_0004_workflow"
suite.DESCRIPTOR = (
    "skills/control/workflow-contract-validator/references/normalized-workflows/hub/"
    + suite.WORKFLOW_ID
    + "/workflow.yaml"
)
suite.AUTHORED = (
    ROOT / "skills/control/workflow-contract-validator/references/"
    "sympy-goal-plan-0004.workflow.json"
)

if __name__ == "__main__":
    sys.exit(suite.main())
