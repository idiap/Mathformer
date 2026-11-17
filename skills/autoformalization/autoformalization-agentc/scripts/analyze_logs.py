#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.
#
# Intent:
#   Tell coding agents what context to load, what invariants to preserve, and how to validate their work.
#
# Function:
#   Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Generate JSON + LaTeX statistics reports from autoformalization artifacts."""

from __future__ import annotations

import argparse
from dataclasses import fields
import json
from pathlib import Path
from typing import Any, Dict

from agentc import (
    SystematicAutoformalizationReport,
    save_autoformalization_statistics,
)


def _load_report_payload(path: str | Path) -> Dict[str, Any]:
    """Document the responsibility of ``_load_report_payload``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    report_path = Path(path)
    if not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_path}")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Report JSON must be an object.")
    return payload


def _coerce_report(payload: Dict[str, Any]) -> SystematicAutoformalizationReport:
    """Document the responsibility of ``_coerce_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_coerce_report`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    allowed = {f.name for f in fields(SystematicAutoformalizationReport)}
    filtered = {k: v for k, v in payload.items() if k in allowed}
    filtered.setdefault("expanded_statement", None)
    filtered.setdefault("core_statement_annotations", None)
    filtered.setdefault("latex_expansion_reviews", None)
    filtered.setdefault("latex_expansion_review_passed", None)
    filtered.setdefault("mathlib_concept_coverage", None)
    filtered.setdefault("mathlib_concept_compatibility_rounds", None)
    return SystematicAutoformalizationReport(**filtered)


def parse_options(argv: list[str] | None = None) -> dict:
    """Parse the native CLI interface for both main and MCP callers."""
    parser = argparse.ArgumentParser(
        description=(
            "Analyze autoformalization reasoning logs/intermediate Lean files and "
            "emit a JSON + LaTeX statistics report."
        )
    )
    parser.add_argument(
        "--report-file",
        required=True,
        help="Path to a workflow report JSON (from run_systematic_workflow).",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional output path for statistics JSON.",
    )
    parser.add_argument(
        "--output-tex",
        default=None,
        help="Optional output path for statistics LaTeX.",
    )
    return vars(parser.parse_args(argv))


def finish_paths(paths: dict | None) -> int:
    """Emit the native completion paths in order."""
    if paths is None:
        return 0  # argparse help completed before report processing.
    print(str(paths["json"]))
    print(str(paths["tex"]))
    return 0


def main() -> int:
    args = argparse.Namespace(**parse_options())
    payload = _load_report_payload(args.report_file)
    report = _coerce_report(payload)
    stats_json, stats_tex, _ = save_autoformalization_statistics(
        report,
        statistics_file=args.output_json,
        statistics_tex_file=args.output_tex,
    )
    return finish_paths({"json": str(stats_json), "tex": str(stats_tex)})


if __name__ == "__main__":
    raise SystemExit(main())
