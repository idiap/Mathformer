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

"""Reflect on FormalPhysics formal_answer after a SymPy candidate exists."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Sequence


def read_text(path: Path | None, inline: str | None) -> str:
    """Document the responsibility of ``read_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if inline is not None:
        return inline
    if path is not None:
        return path.read_text(encoding="utf-8")
    return ""


def load_json(path: Path | None) -> dict[str, Any]:
    """Load an optional JSON object."""
    if path is None:
        return {}
    parsed = json.loads(path.read_text(encoding="utf-8"))
    return parsed if isinstance(parsed, dict) else {}


def extract_features(text: str) -> dict[str, Any]:
    """Document the responsibility of ``extract_features``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_features`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {
        "imports": re.findall(r"^\s*(?:import|open)\s+(.+)$", text, re.M),
        "theorem_like": re.findall(
            r"\b(theorem|lemma|def|axiom)\s+([A-Za-z0-9_'.]+)", text
        ),
        "assumption_terms": sorted(
            set(
                re.findall(
                    r"\b(positive|nonzero|non-zero|smooth|differentiable|inertial|field|vector|law|dimension|unit)\b",
                    text,
                    re.I,
                )
            )
        ),
        "equation_count": len(re.findall(r"=", text)),
        "projection_terms": sorted(
            set(
                re.findall(
                    r"\b(component|projection|coordinate|scalar|vector|field)\b",
                    text,
                    re.I,
                )
            )
        ),
    }


def validate_pre_reflection_ledger(
    ledger: dict[str, Any], *, formal_answer_provided: bool
) -> tuple[str, list[dict[str, Any]]]:
    """Validate that source-first evidence existed before formal_answer inspection."""
    findings: list[dict[str, Any]] = []
    if not formal_answer_provided:
        return "not_required_until_formal_answer_is_provided", findings
    if not ledger:
        findings.append(
            {
                "severity": "error",
                "code": "pre_reflection_ledger_missing",
                "message": "A pre-reflection ledger is required before FormalPhysics formal_answer inspection.",
                "repair_surface": "trace_realness",
            }
        )
        return "missing", findings

    evidence_flags = [
        bool(ledger.get("candidate_report_exists")),
        bool(ledger.get("blocker_report_exists")),
        bool(ledger.get("final_consistency_report_exists")),
    ]
    if not any(evidence_flags):
        findings.append(
            {
                "severity": "error",
                "code": "pre_reflection_evidence_missing",
                "message": "Ledger must prove that a candidate, blocker, or final consistency report existed before formal_answer inspection.",
                "repair_surface": "trace_realness",
            }
        )
    if ledger.get("created_before_formal_answer_inspection") is not True:
        findings.append(
            {
                "severity": "error",
                "code": "ledger_not_pre_reflection",
                "message": "Ledger does not state that it was created before formal_answer inspection.",
                "repair_surface": "target_nonleakage",
            }
        )
    if ledger.get("formal_answer_inspected_before_ledger") is True:
        findings.append(
            {
                "severity": "error",
                "code": "formal_answer_inspected_before_ledger",
                "message": "Ledger records formal_answer inspection before pre-reflection evidence existed.",
                "repair_surface": "target_nonleakage",
            }
        )
    return ("valid" if not findings else "invalid"), findings


def build_reflection(
    candidate_text: str,
    formal_answer_text: str,
    case_id: str,
    pre_reflection_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Document the responsibility of ``build_reflection``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings: list[dict[str, Any]] = []
    ledger_status, ledger_findings = validate_pre_reflection_ledger(
        pre_reflection_ledger or {},
        formal_answer_provided=bool(formal_answer_text.strip()),
    )
    findings.extend(ledger_findings)
    if not candidate_text.strip():
        findings.append(
            {
                "severity": "error",
                "code": "candidate_missing",
                "message": "Formal answer reflection is blocked until an informal-first SymPy candidate or blocker exists.",
                "repair_surface": "trace_realness",
            }
        )
    if not formal_answer_text.strip():
        findings.append(
            {
                "severity": "warning",
                "code": "formal_answer_missing",
                "message": "No FormalPhysics formal_answer text was provided.",
                "repair_surface": "trace_realness",
            }
        )

    candidate_features = extract_features(candidate_text)
    formal_features = extract_features(formal_answer_text)
    improvements: list[dict[str, Any]] = []
    formal_terms = set(term.lower() for term in formal_features["assumption_terms"])
    candidate_terms = set(
        term.lower() for term in candidate_features["assumption_terms"]
    )
    missing_terms = sorted(formal_terms - candidate_terms)
    if missing_terms:
        improvements.append(
            {
                "kind": "assumption_or_context_inspiration",
                "terms": missing_terms,
                "route": "review.physics_sympy_final_equations -> refine.physics_sympy_review",
                "evidence_source": "post_hoc_inspiration",
                "acceptance_policy": "requires localized monotonic review refinement before any artifact change",
            }
        )
    formal_projection = set(
        term.lower() for term in formal_features["projection_terms"]
    )
    candidate_projection = set(
        term.lower() for term in candidate_features["projection_terms"]
    )
    missing_projection = sorted(formal_projection - candidate_projection)
    if missing_projection:
        improvements.append(
            {
                "kind": "projection_inspiration",
                "terms": missing_projection,
                "route": "critique.physics_sympy_dimensions -> review.physics_sympy_final_equations",
                "evidence_source": "post_hoc_inspiration",
                "acceptance_policy": "requires localized monotonic review refinement before any artifact change",
            }
        )

    max_severity = max(
        (
            {"info": 0, "warning": 1, "error": 2, "critical": 3}[item["severity"]]
            for item in findings
        ),
        default=0,
    )
    return {
        "style": "physics_sympy_formal_answer_reflection",
        "case_id": case_id,
        "status": (
            "blocked"
            if max_severity >= 2
            else "warn" if max_severity == 1 else "complete"
        ),
        "policy": {
            "formal_answer_role": "inspiration_only_not_benchmark",
            "not_ground_truth": True,
            "accepted_changes_require": "localized monotonic review refinement",
            "pre_reflection_ledger_required": True,
            "bypass_rejected": True,
        },
        "pre_reflection_ledger_status": ledger_status,
        "accepted_change_sources": {
            "accepted_changes": [],
            "allowed_evidence_sources": [
                "source_evidence",
                "execution_evidence",
                "deterministic_critic",
                "post_hoc_inspiration",
            ],
            "policy": "this reflector proposes inspiration only; accepted changes must be produced by a later localized monotonic review-refinement step",
        },
        "candidate_features": candidate_features,
        "formal_answer_features": formal_features,
        "improvement_candidates": improvements,
        "findings": findings,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
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
    parser.add_argument("--case-id", default="unspecified")
    parser.add_argument("--candidate-file", type=Path)
    parser.add_argument("--candidate-text")
    parser.add_argument("--formal-answer-file", type=Path)
    parser.add_argument("--formal-answer-text")
    parser.add_argument("--pre-reflection-ledger", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def render_md(report: dict[str, Any]) -> str:
    """Document the responsibility of ``render_md``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = [
        f"# SymPy FormalPhysics Reflection: {report['case_id']}",
        "",
        f"Status: `{report['status']}`",
        "",
        "Policy: FormalPhysics formal_answer is inspiration only, not ground truth.",
        "",
        "## Improvement Candidates",
    ]
    if report["improvement_candidates"]:
        for item in report["improvement_candidates"]:
            lines.append(f"- `{item['kind']}`: {', '.join(item.get('terms', []))}")
    else:
        lines.append("- None detected by deterministic feature comparison.")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
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
    if args.self_test:
        report = build_reflection(
            "SymPy candidate with force equation.",
            "theorem sample (h : positive m) : vector_projection = scalar := by ring",
            "case",
            {
                "candidate_report_exists": True,
                "created_before_formal_answer_inspection": True,
                "formal_answer_inspected_before_ledger": False,
            },
        )
        assert report["status"] == "complete"
        assert report["policy"]["not_ground_truth"] is True
        assert report["pre_reflection_ledger_status"] == "valid"
    else:
        report = build_reflection(
            read_text(args.candidate_file, args.candidate_text),
            read_text(args.formal_answer_file, args.formal_answer_text),
            args.case_id,
            load_json(args.pre_reflection_ledger),
        )
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    if args.output_md:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_md(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
