#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Execute the explicitly supplied 0009 route through real MCP and PRISM.

All source helpers run in temporary repository mounts. Only the external
compiler is substituted; provider/network access fails closed in the fixture.
"""

import os
from pathlib import Path
import sys
import unittest

lunar = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = lunar / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (lunar / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])

import run_recursive_goal_workflow_tests as suite

suite.DESCRIPTOR = (
    "skills/control/workflow-contract-validator/references/normalized-workflows/"
    "route/route_formalize_physics_lean_goal_sample_0009_workflow/workflow.yaml"
)

if __name__ == "__main__":
    unittest.main(module=suite, verbosity=2)
