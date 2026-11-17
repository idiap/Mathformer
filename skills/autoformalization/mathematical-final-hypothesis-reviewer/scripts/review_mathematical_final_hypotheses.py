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

"""Review final mathematical hypotheses and theorem shape."""

from __future__ import annotations

from typing import Any

import argparse
import json
import re
from pathlib import Path
from typing import Sequence


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
    if path is None:
        return ""
    return path.read_text(encoding="utf-8")


def add_finding(
    findings: list[dict[str, str]],
    *,
    severity: str,
    code: str,
    message: str,
    repair_surface: str,
) -> None:
    """Document the responsibility of ``add_finding``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings.append(
        {
            "severity": severity,
            "code": code,
            "message": message,
            "repair_surface": repair_surface,
        }
    )


def has_source_claim(text: str, patterns: Sequence[str]) -> bool:
    """Document the responsibility of ``has_source_claim``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_source_claim`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lower = text.lower()
    return any(pattern in lower for pattern in patterns)


def theorem_lines(lean_text: str) -> list[str]:
    """Document the responsibility of ``theorem_lines``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``theorem_lines`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return [
        line.strip()
        for line in lean_text.splitlines()
        if re.search(r"^\s*(theorem|lemma|def)\b", line)
    ]


def build_report(*, source_text: str, lean_text: str) -> dict[str, Any]:
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
    findings: list[dict[str, str]] = []
    decls = theorem_lines(lean_text)
    _lean_lower = lean_text.lower()
    has_theorem = any(line.startswith(("theorem ", "lemma ")) for line in decls)
    has_placeholder = bool(
        re.search(r"\b(sorry|admit|todo|exact\?|by\s+omega\?)\b", lean_text, re.I)
    )
    has_axiom_or_constant = bool(re.search(r"^\s*(axiom|constant)\b", lean_text, re.M))
    proves_true = bool(re.search(r":\s*True\s*(:=|:=\s*by|where|$)", lean_text))
    false_hypothesis = bool(re.search(r"\([^)]*:\s*False\s*\)|\bFalse\s*->", lean_text))
    target_as_hypothesis = bool(
        re.search(r"\((h|htarget|hclaim)[^)]*:\s*[^)]*\)\s*:\s*\1\b", lean_text)
    )
    unknown_type_hole = bool(re.search(r":\s*(_|Sort\s*\*)", lean_text))

    source_forall = has_source_claim(
        source_text, ["for all", "forall", "every", "any "]
    )
    source_exists = has_source_claim(source_text, ["there exists", "exists", "some "])
    source_unique = has_source_claim(source_text, ["unique", "uniquely", "exactly one"])
    source_iff = has_source_claim(
        source_text, ["if and only if", " iff ", "equivalent"]
    )
    source_not = has_source_claim(
        source_text, ["not ", "nonzero", "non-zero", "contradiction"]
    )

    lean_has_forall = bool(re.search(r"\bforall\b|[({].*:", lean_text, re.I))
    lean_has_exists = bool(re.search(r"\bExists\b|\bexists\b|\u2203", lean_text))
    lean_has_unique = bool(
        re.search(r"\bUnique\b|\bExistsUnique\b|\bexists_unique\b|\u2203!", lean_text)
    )
    lean_has_iff = bool(re.search(r"\bIff\b|<->|\u2194", lean_text))
    lean_has_not = bool(re.search(r"\bNot\b|\u00ac|->\s*False|!=|\u2260", lean_text))

    if not has_theorem:
        add_finding(
            findings,
            severity="critical",
            code="missing_final_theorem",
            message="No final theorem or lemma declaration is visible.",
            repair_surface="conclusion_shape",
        )
    if has_placeholder:
        add_finding(
            findings,
            severity="critical",
            code="placeholder_in_complete_candidate",
            message="Complete status cannot contain sorry, admit, todo, or unresolved tactic placeholders.",
            repair_surface="proof_realness",
        )
    if has_axiom_or_constant:
        add_finding(
            findings,
            severity="critical",
            code="unchecked_axiom_or_constant",
            message="Final derivation introduces unchecked axioms or constants.",
            repair_surface="support_dependency",
        )
    if proves_true:
        add_finding(
            findings,
            severity="critical",
            code="trivial_true_conclusion",
            message="Final theorem appears to prove True rather than the source conclusion.",
            repair_surface="conclusion_shape",
        )
    if false_hypothesis and "false" not in source_text.lower():
        add_finding(
            findings,
            severity="critical",
            code="vacuous_false_hypothesis",
            message="A False hypothesis or contradictory premise may make the theorem vacuous.",
            repair_surface="nonvacuity",
        )
    if target_as_hypothesis:
        add_finding(
            findings,
            severity="critical",
            code="target_as_hypothesis",
            message="The final target appears to be available as a hypothesis.",
            repair_surface="nonvacuity",
        )
    if unknown_type_hole:
        add_finding(
            findings,
            severity="error",
            code="unresolved_or_overgeneral_type",
            message="A binder has an unresolved or overly generic type surface.",
            repair_surface="binder_domain",
        )
    if source_forall and not lean_has_forall:
        add_finding(
            findings,
            severity="error",
            code="forall_shape_missing",
            message="Source has universal structure but final Lean hypotheses do not visibly bind variables.",
            repair_surface="quantifier_shape",
        )
    if source_exists and not lean_has_exists:
        add_finding(
            findings,
            severity="error",
            code="exists_shape_missing",
            message="Source has existential structure but final Lean theorem lacks an existential conclusion.",
            repair_surface="quantifier_shape",
        )
    if source_unique and not lean_has_unique:
        add_finding(
            findings,
            severity="error",
            code="uniqueness_shape_missing",
            message="Source has uniqueness structure but final Lean theorem lacks uniqueness.",
            repair_surface="quantifier_shape",
        )
    if source_iff and not lean_has_iff:
        add_finding(
            findings,
            severity="error",
            code="iff_shape_missing",
            message="Source has equivalence structure but final Lean theorem lacks Iff.",
            repair_surface="conclusion_shape",
        )
    if source_not and not lean_has_not:
        add_finding(
            findings,
            severity="warning",
            code="negation_or_nonzero_shape_missing",
            message="Source has negation or nonzero structure not visibly represented in Lean.",
            repair_surface="side_condition",
        )

    severity_rank = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    max_severity = max(
        (severity_rank[item["severity"]] for item in findings), default=0
    )
    status = "fail" if max_severity >= 2 else "warn" if max_severity == 1 else "pass"
    return {
        "style": "mathematical_final_hypothesis_review",
        "status": status,
        "reviewed_properties": {
            "declaration_count": len(decls),
            "has_theorem": has_theorem,
            "has_placeholder": has_placeholder,
            "has_axiom_or_constant": has_axiom_or_constant,
            "proves_true": proves_true,
            "false_hypothesis": false_hypothesis,
        },
        "findings": findings,
        "refinement_required": status == "fail",
        "refinement_handoff": {
            "router": "physics-lean-review-refinement-router",
            "repair_surfaces": sorted({item["repair_surface"] for item in findings}),
            "monotonicity_constraints": [
                "preserve theorem names unless source-shape repair requires a rename",
                "do not weaken conclusions",
                "do not add stronger hypotheses without source or generated-support labels",
                "do not introduce placeholders",
                "rerun affected reviewers and protected gates",
            ],
        },
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
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--source-text")
    parser.add_argument("--lean-file", type=Path)
    parser.add_argument("--lean-text")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


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
        report = build_report(
            source_text="For every real x there exists a unique y.",
            lean_text="theorem bad : True := by trivial",
        )
        assert report["status"] == "fail"
        assert any(
            item["code"] == "trivial_true_conclusion" for item in report["findings"]
        )
    else:
        report = build_report(
            source_text=read_text(args.source_file, args.source_text),
            lean_text=read_text(args.lean_file, args.lean_text),
        )
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
