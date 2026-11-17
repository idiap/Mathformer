#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

# File Documentation
#
# Motivation:
#   Provide a repository-level entry point for Rocq autoformalization without requiring users to know package internals.
#
# Intent:
#   Delegate controlled-case Rocq drafting, validation, and reporting to `MathformerRocq.autoformalize`.
#
# Function:
#   Runs the Rocq backend CLI as a script from the project root.
#
# Maintenance Notes:
#   Keep this wrapper thin; substantive Rocq behavior belongs in `backends/rocq/MathformerRocq/autoformalize.py`.

"""Run Mathformer Rocq autoformalization."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.rocq.MathformerRocq.autoformalize import (
    main,
)

if __name__ == "__main__":
    raise SystemExit(main())
