#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Candidate-selected 0004 bindings, frozen-source parity and real Lunar execution.

The map has no external model or scientific compiler step. The shared test
transport denies those boundaries and admits only the real planner's invalid
CLI input, which stops before artifact import or validator execution.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])

import run_sympy_expansion_workflow_tests as suite

suite.DESCRIPTOR = (
    "skills/control/workflow-contract-validator/references/normalized-workflows/hub/"
    "hub_physics_sympy_repair_expansion_map_0004_workflow/workflow.yaml"
)
suite.AUTHORED = "skills/control/workflow-contract-validator/references/sympy-expansion-map-0004.workflow.json"
suite.MAP_OUTPUT = "map"
suite.EMISSION_OUTPUT = "emission"
suite.PARSE_NAME = "parse_cli_0004"
suite.CASE_ID = "formalphysics_0004"
suite.MISSING_NAME = "missing_input"
# The candidate leaves malformed finding values source-owned: build_map fails.
suite.BAD_PLAN_CALLS = 4

if __name__ == "__main__":
    raise SystemExit(suite.main())
