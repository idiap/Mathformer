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

"""Validate Mathformer mathlib concept ontology profiles."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from reasoning_log import (
    append_reasoning_log_entry,
)
from ontology import (
    DEFAULT_PROFILE,
    all_surface_terms,
    concept_profiles,
    keyword_hints,
    load_profile,
    phrase_hints,
    preferred_decls,
    synonym_map,
    validate_profile,
)

SKILL_NAME = "mathlib-concept-ontology-manager"
HOOK_ID = "mathlib.ontology.validate"


def append_event(
    reasoning_log: Optional[Path], step: str, payload: Dict[str, Any]
) -> None:
    """Document the responsibility of ``append_event``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``append_event`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if reasoning_log is None:
        return
    append_reasoning_log_entry(
        reasoning_log,
        step=step,
        payload={"skill": SKILL_NAME, "hook_id": HOOK_ID, **payload},
    )


def build_report(profile_path: Path) -> Dict[str, Any]:
    """Document the responsibility of ``build_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    profile = load_profile(profile_path)
    findings = validate_profile(profile)
    blocking = [item for item in findings if item.get("severity") == "high"]
    concepts = concept_profiles(profile)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": not blocking,
        "profile": str(profile_path),
        "summary": {
            "concept_count": len(concepts),
            "synonym_key_count": len(synonym_map(profile)),
            "keyword_hint_count": len(keyword_hints(profile)),
            "phrase_hint_count": len(phrase_hints(profile)),
            "preferred_decl_key_count": len(preferred_decls(profile)),
            "surface_term_count": len(all_surface_terms(profile)),
            "finding_count": len(findings),
            "blocking_finding_count": len(blocking),
        },
        "findings": findings,
    }


def render_text(report: Dict[str, Any]) -> str:
    """Document the responsibility of ``render_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    summary = report["summary"]
    lines = [
        f"ok: {report['ok']}",
        f"profile: {report['profile']}",
        f"concepts: {summary['concept_count']}",
        f"surface_terms: {summary['surface_term_count']}",
        f"findings: {summary['finding_count']}",
        f"blocking: {summary['blocking_finding_count']}",
    ]
    for finding in report["findings"]:
        lines.append(f"- {finding['severity']} {finding['code']}: {finding['message']}")
    return "\n".join(lines)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Document the responsibility of ``parse_args``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--reasoning-log-file", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    args = parse_args(argv)
    append_event(
        args.reasoning_log_file,
        "mathlib_ontology_validation_start",
        {"profile": str(args.profile)},
    )
    try:
        report = build_report(args.profile)
    except Exception as exc:
        append_event(
            args.reasoning_log_file,
            "mathlib_ontology_validation_error",
            {"profile": str(args.profile), "error": str(exc)},
        )
        raise
    append_event(
        args.reasoning_log_file,
        "mathlib_ontology_validation_complete",
        {"profile": str(args.profile), "ok": report["ok"], **report["summary"]},
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
