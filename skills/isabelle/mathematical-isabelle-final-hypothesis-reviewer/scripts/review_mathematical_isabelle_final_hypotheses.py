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

"""Review final mathematical hypothesis shape for Isabelle/HOL theories."""

from __future__ import annotations

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


def theorem_lines(theory_text: str) -> list[str]:
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
        for line in theory_text.splitlines()
        if re.search(r"^\s*(theorem|lemma)\b", line)
    ]


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


def target_as_assumption(theory_text: str) -> bool:
    """Document the responsibility of ``target_as_assumption``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``target_as_assumption`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    assumptions = {
        re.sub(r"\s+", " ", match).strip()
        for match in re.findall(
            r"\b(?:assumes|and)\s+[A-Za-z0-9_']+\s*:\s*\"([^\"]+)\"", theory_text
        )
    }
    shows = {
        re.sub(r"\s+", " ", match).strip()
        for match in re.findall(r"\bshows\s*\"([^\"]+)\"", theory_text)
    }
    return bool(assumptions.intersection(shows))


def build_report(*, source_text: str, theory_text: str) -> dict[str, object]:
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
    decls = theorem_lines(theory_text)
    has_theorem = bool(decls)
    has_placeholder = bool(
        re.search(r"\b(sorry|oops|quickcheck_params|TODO)\b", theory_text, re.I)
    )
    has_unchecked_axiom = bool(
        re.search(r"^\s*(axiomatization|consts)\b", theory_text, re.M)
    )
    proves_true = bool(
        re.search(r"\b(theorem|lemma)\b[^:]*:\s*\"?True\"?", theory_text)
    )
    false_assumption = bool(re.search(r"assumes\s+\w+:\s*\"False\"", theory_text))
    source_exists = has_source_claim(source_text, ["there exists", "exists", "some "])
    source_unique = has_source_claim(source_text, ["unique", "uniquely", "exactly one"])
    source_iff = has_source_claim(
        source_text, ["if and only if", " iff ", "equivalent"]
    )
    source_not = has_source_claim(source_text, ["not ", "nonzero", "non-zero"])
    has_exists = bool(re.search(r"\bEx\b|\<exists>|\\<exists>|∃", theory_text))
    has_unique = bool(re.search(r"\<exists>!|\\<exists>!|∃!", theory_text))
    has_iff = bool(
        re.search(r"\<longleftrightarrow>|\\<longleftrightarrow>|\biff\b", theory_text)
    )
    has_not = bool(re.search(r"\<not>|\\<not>|~=", theory_text))
    target_assumed = target_as_assumption(theory_text)

    if not has_theorem:
        add_finding(
            findings,
            "critical",
            "missing_final_theorem",
            "No Isabelle theorem or lemma declaration is visible.",
            "conclusion_shape",
        )
    if has_placeholder:
        add_finding(
            findings,
            "critical",
            "placeholder_in_complete_candidate",
            "Complete status cannot contain sorry, oops, quickcheck_params, or TODO.",
            "proof_realness",
        )
    if has_unchecked_axiom:
        add_finding(
            findings,
            "critical",
            "unchecked_axiomatization_or_consts",
            "Final theory introduces unchecked axiomatization or consts.",
            "support_dependency",
        )
    if proves_true and "true" not in source_text.lower():
        add_finding(
            findings,
            "critical",
            "trivial_true_conclusion",
            "Final theorem appears to prove True rather than the source conclusion.",
            "conclusion_shape",
        )
    if false_assumption and "false" not in source_text.lower():
        add_finding(
            findings,
            "critical",
            "vacuous_false_assumption",
            "A False assumption may make the theorem vacuous.",
            "nonvacuity",
        )
    if target_assumed:
        add_finding(
            findings,
            "critical",
            "target_equation_as_assumption",
            "The theorem target appears verbatim as an assumption.",
            "nonvacuity",
        )
    if source_exists and not has_exists:
        add_finding(
            findings,
            "error",
            "exists_shape_missing",
            "Source has existential structure but Isabelle theorem lacks an existential surface.",
            "quantifier_shape",
        )
    if source_unique and not has_unique:
        add_finding(
            findings,
            "error",
            "unique_shape_missing",
            "Source has uniqueness structure but Isabelle theorem lacks uniqueness.",
            "quantifier_shape",
        )
    if source_iff and not has_iff:
        add_finding(
            findings,
            "error",
            "iff_shape_missing",
            "Source has equivalence structure but Isabelle theorem lacks an equivalence surface.",
            "conclusion_shape",
        )
    if source_not and not has_not:
        add_finding(
            findings,
            "warning",
            "negation_or_nonzero_shape_missing",
            "Source has negation/nonzero structure not visibly represented.",
            "side_condition",
        )

    severity_rank = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    max_severity = max(
        (severity_rank[item["severity"]] for item in findings), default=0
    )
    status = "fail" if max_severity >= 2 else "warn" if max_severity == 1 else "pass"
    return {
        "style": "mathematical_isabelle_final_hypothesis_review",
        "status": status,
        "reviewed_properties": {
            "declaration_count": len(decls),
            "has_theorem": has_theorem,
            "has_placeholder": has_placeholder,
            "has_unchecked_axiom": has_unchecked_axiom,
            "proves_true": proves_true,
            "false_assumption": false_assumption,
            "target_as_assumption": target_assumed,
        },
        "findings": findings,
        "refinement_required": status == "fail",
        "refinement_handoff": {
            "router": "physics-isabelle-workflow-orchestrator",
            "repair_surfaces": sorted({item["repair_surface"] for item in findings}),
            "monotonicity_constraints": [
                "preserve theorem names unless source-shape repair requires a rename",
                "do not weaken conclusions",
                "do not introduce placeholders",
                "rerun Isabelle execution and consistency gates",
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
    parser.add_argument("--theory-file", type=Path)
    parser.add_argument("--theory-text")
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
            source_text="For all x, x = x.",
            theory_text='theory T\nimports Main\nbegin\ntheorem refl: "x = x" by simp\nend\n',
        )
        assert report["status"] == "pass"
        iff_report = build_report(
            source_text="x and y are equivalent if and only if p holds.",
            theory_text='theory T\nimports Main\nbegin\ntheorem bad: "x = x" by simp\nend\n',
        )
        assert iff_report["status"] == "fail"
        target_assumption_report = build_report(
            source_text="Show x = y.",
            theory_text='theory T\nimports Main\nbegin\ntheorem bad:\n  assumes h: "x = y"\n  shows "x = y"\n  using h by simp\nend\n',
        )
        assert target_assumption_report["status"] == "fail"
    else:
        report = build_report(
            source_text=read_text(args.source_file, args.source_text),
            theory_text=read_text(args.theory_file, args.theory_text),
        )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
