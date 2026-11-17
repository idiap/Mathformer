#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Automate repository maintenance tasks that would be error-prone if performed by hand.
#
# Intent:
#   Expose command-line entry points for setup, generation, indexing, auditing, and proof execution.
#
# Function:
#   Implements operational glue used by tests, skills, docs, and developer workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Compatibility entrypoint for regenerating the FormalPhysics top-10 SymPy library."""

from __future__ import annotations

import runpy
from pathlib import Path

SCRIPT = Path(__file__).with_name("generate_formalphysics_original_two_sympy.py")


if __name__ == "__main__":
    runpy.run_path(str(SCRIPT), run_name="__main__")
