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
#   Give agents and tests a stable command for generating Rocq proof scripts.
#
# Intent:
#   Reuse the central Rocq backend while exposing skill-friendly argument names.
#
# Function:
#   Supports full-suite generation, single-case generation, validation-only mode, and self-test mode.
#
# Maintenance Notes:
#   Keep this script thin; update `MathformerRocq.autoformalize` for template or validation behavior changes.

"""Draft Rocq proof scripts for controlled Mathformer cases."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.rocq.MathformerRocq.autoformalize import (
    main,
)

if __name__ == "__main__":
    raise SystemExit(main())
