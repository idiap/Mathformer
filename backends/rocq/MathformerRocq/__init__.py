# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Keep Rocq autoformalization reusable from skills, scripts, tests, and future backend orchestration.
#
# Intent:
#   Expose the public Python surface for deterministic Mathformer-to-Rocq drafting and validation.
#
# Function:
#   Re-exports the backend primitives used to generate `.v` files and validate their proof-artifact contract.
#
# Maintenance Notes:
#   Keep exports small and stable; add new backend operations in `autoformalize.py` before exporting them here.

"""Rocq backend helpers for Mathformer autoformalization."""

from .autoformalize import (
    DEFAULT_CASE_ORDER,
    RocqCase,
    draft_case,
    draft_manifest,
    find_rocq_compiler,
    run_external_check,
    validate_file,
    validate_rocq_text,
)

__all__ = [
    "DEFAULT_CASE_ORDER",
    "RocqCase",
    "draft_case",
    "draft_manifest",
    "find_rocq_compiler",
    "run_external_check",
    "validate_file",
    "validate_rocq_text",
]
