#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Verify the loop contract explicitly supplied by the normalization host.

Reuse the native runner fixture suite: all helper Python programs execute;
only the external compiler boundary is replaced. No provider is called by
this one-pass planner, and the fixture denies network and unknown processes.
"""

import os
from pathlib import Path
import sys
import unittest

# Keep this entrypoint when switching to the host's PRISM environment.
lunar = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = lunar / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (lunar / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])

import run_recursive_goal_workflow_tests as suite

suite.DESCRIPTOR = (
    "skills/control/workflow-contract-validator/references/normalized-workflows/"
    "loop/loop_lean_physics_derivation_trace_loop_workflow/workflow.yaml"
)

if __name__ == "__main__":
    unittest.main(module=suite, verbosity=2)
