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

"""Build a deterministic informal physics derivation elicitation packet."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Sequence

STYLE = "physics_informal_derivation_elicitation_packet"

TARGETS = [
    (
        "target_shape",
        "What exact relation, implication, equivalence, existence, uniqueness, or approximation is being derived?",
        "formal theorem shape and final reviewer",
    ),
    (
        "quantities",
        "Which symbols denote physical quantities, vectors, fields, operators, constants, coordinates, or dimensionless parameters?",
        "typing and symbol table",
    ),
    (
        "dimensions_units",
        "What dimensions and unit conventions apply to each non-dimensionless quantity?",
        "unit and dimension obligations",
    ),
    (
        "frames_conventions",
        "Which coordinate frame, sign convention, gauge, orientation, or basis is assumed?",
        "contextual assumptions",
    ),
    (
        "regimes_approximations",
        "Which idealizations, limits, linearizations, steady-state assumptions, or approximation regimes are used?",
        "regime modeling and semantic preservation",
    ),
    (
        "domains_side_conditions",
        "Which positivity, nonzero, smoothness, differentiability, integrability, boundary, or initial conditions are required?",
        "Lean hypotheses and non-vacuity",
    ),
    (
        "physical_laws",
        "Which named physical laws, conservation principles, constitutive equations, or transformation rules justify each step?",
        "law grounding and proof expansion",
    ),
    (
        "derivation_gaps",
        "Which transitions between displayed equations need intermediate algebra, calculus, or physical explanation?",
        "informal derivation expansion",
    ),
    (
        "expected_formal_grounding",
        "Which definitions, background results, bridge lemmas, and Mathlib-native theorem surfaces should the formalization be expected to use?",
        "background dependency plan and Mathlib grounding",
    ),
]


def read_source(path: Path | None, text: str | None) -> tuple[str, str]:
    """Document the responsibility of ``read_source``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if text is not None:
        return text, "inline"
    if path is not None:
        return path.read_text(encoding="utf-8"), str(path)
    return "", "unspecified"


def count_cues(source: str) -> dict[str, int]:
    """Document the responsibility of ``count_cues``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``count_cues`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {
        "equation_like_lines": sum(
            1
            for line in source.splitlines()
            if any(op in line for op in ["=", "\\le", "\\ge", "\\approx"])
        ),
        "latex_commands": len(re.findall(r"\\[A-Za-z]+", source)),
        "derivative_cues": len(
            re.findall(
                r"\\frac\{d|\\partial|derivative|gradient|divergence|curl",
                source,
                flags=re.I,
            )
        ),
        "integral_cues": len(re.findall(r"\\int|integral", source, flags=re.I)),
        "vector_cues": len(
            re.findall(
                r"\\vec|\\mathbf|\\times|cross|component|projection|vector",
                source,
                flags=re.I,
            )
        ),
        "unit_cues": len(
            re.findall(
                r"\b(m|s|kg|K|A|mol|cd|J|N|Pa|W|C|V|T|Hz)\b|\\hbar|Hamiltonian|energy|force|mass|charge|velocity|current",
                source,
                flags=re.I,
            )
        ),
        "law_cues": len(
            re.findall(
                r"Newton|Maxwell|Hamilton|Hamiltonian|Lagrange|Euler|Poisson|conservation|Noether|Schr[oö]dinger|TDSE|Fourier",
                source,
                flags=re.I,
            )
        ),
        "field_cues": len(
            re.findall(
                r"(?<!\{)\bfield\b|potential|gradient|curl|divergence|\\nabla|electric field|magnetic field",
                source,
                flags=re.I,
            )
        ),
        "operator_cues": len(
            re.findall(
                r"operator|Hamiltonian|\\hat|\\ket|\\bra|inner product|Schr[oö]dinger|TDSE",
                source,
                flags=re.I,
            )
        ),
    }


def expected_grounding(source: str, cues: dict[str, int]) -> dict[str, Any]:
    """Document the responsibility of ``expected_grounding``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``expected_grounding`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    expectations: list[dict[str, Any]] = []

    def add(
        item_id: str, kind: str, expectation: str, status: str, targets: list[str]
    ) -> None:
        """Document the responsibility of ``expected_grounding.add``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Provide the local operation named ``expected_grounding.add`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        expectations.append(
            {
                "id": item_id,
                "kind": kind,
                "expectation": expectation,
                "support_status": status,
                "preferred_grounding_targets": targets,
            }
        )

    if cues["vector_cues"] or re.search(
        r"component|projection|cross|\\times", source, re.I
    ):
        add(
            "expect.vector_surface",
            "Mathlib surface",
            "Represent vectors/components with a Mathlib-native finite vector carrier and explicit projection bridge.",
            "mathlib_backed",
            [
                "EuclideanSpace Real (Fin n)",
                "Fin component projection",
                "projection bridge lemma",
            ],
        )
    if cues["field_cues"]:
        add(
            "expect.field_definitions",
            "definition",
            "Make scalar/vector field carriers, potential-derived fields, and smoothness assumptions explicit before formalization.",
            "source_backed_or_generated_support",
            [
                "X -> EuclideanSpace Real (Fin 3)",
                "HasFDerivAt",
                "Differentiable",
                "ContDiff",
            ],
        )
    if cues["derivative_cues"]:
        add(
            "expect.calculus_support",
            "background result",
            "Name the derivative, product-rule, chain-rule, or partial-derivative facts expected to justify transitions.",
            "mathlib_backed",
            ["HasDerivAt", "HasFDerivAt", "deriv_add", "deriv_mul", "fderiv"],
        )
    if cues["operator_cues"]:
        add(
            "expect.operator_surface",
            "Mathlib surface",
            "Represent operators, state vectors, adjoints, and inner products on Mathlib-native linear algebra surfaces.",
            "mathlib_backed",
            ["LinearMap", "Matrix", "InnerProductSpace", "Hermitian", "IsSelfAdjoint"],
        )
    if cues["law_cues"]:
        add(
            "expect.source_law_support",
            "background result",
            "Separate named physical law substitutions from the final target and formalize them as source-backed support.",
            "source_backed",
            [
                "source-law support lemma",
                "constitutive-law lemma",
                "physical substitution lemma",
            ],
        )
    if cues["unit_cues"] or re.search(
        r"force|mass|charge|velocity|energy|current|dimension|unit", source, re.I
    ):
        add(
            "expect.unit_dimension_bridge",
            "bridge lemma",
            "Track unit and dimension homogeneity for every non-dimensionless transformation.",
            "generated_support",
            ["unit/dimension homogeneity bridge", "dimension obligation"],
        )
    if cues["equation_like_lines"]:
        add(
            "expect.algebraic_core",
            "background result",
            "Extract reusable algebraic rearrangements as compact support theorems before the physics-rich theorem.",
            "source_backed_or_generated_support",
            ["ring", "linarith", "nlinarith", "compact algebraic core theorem"],
        )
    return {
        "status": "expected" if expectations else "no_grounding_cues_detected",
        "purpose": "steer informal expansion, background dependency planning, type-system construction, and Mathlib grounding from the beginning",
        "expectations": expectations,
        "blocker_if_missing_downstream": bool(expectations),
    }


def build_packet(source: str, source_ref: str, case_id: str) -> dict[str, Any]:
    """Document the responsibility of ``build_packet``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    cues = count_cues(source)
    questions = []
    for target_id, question, required_for in TARGETS:
        severity = "blocker_if_missing"
        if target_id == "dimensions_units" and cues["unit_cues"] == 0:
            severity = "needs_decision"
        if target_id == "frames_conventions" and cues["vector_cues"] == 0:
            severity = "review_if_relevant"
        questions.append(
            {
                "id": target_id,
                "question": question,
                "required_for": required_for,
                "status": "user_needed",
                "severity": severity,
                "source_anchor_hint": "source text" if source else "missing source",
            }
        )
    return {
        "style": STYLE,
        "case_id": case_id,
        "source_ref": source_ref,
        "source_sha256": (
            hashlib.sha256(source.encode("utf-8")).hexdigest() if source else None
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "observed_cues": cues,
        "elicitation_targets": questions,
        "expected_formal_grounding": expected_grounding(source, cues),
        "source_backed_facts": [],
        "generated_support_candidates": [],
        "blockers": [
            q["id"] for q in questions if q["severity"] == "blocker_if_missing"
        ],
        "handoff": [
            "physics.informal.expand",
            "preformalization.expansion_support",
            "dependency.resolve",
            "physics.informal.review",
            "physics.lean.type_system.build",
            "mathlib.grounding_maximize",
        ],
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
    parser.add_argument("--case-id", default="physics_informal_case")
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
        packet = build_packet("F = m a in an inertial frame", "self-test", "self_test")
        assert packet["style"] == STYLE
        assert any(
            item["id"] == "physical_laws" for item in packet["elicitation_targets"]
        )
        assert any(
            item["id"] == "expected_formal_grounding"
            for item in packet["elicitation_targets"]
        )
        assert packet["expected_formal_grounding"]["status"] == "expected"
        assert "physics.informal.expand" in packet["handoff"]
        assert "dependency.resolve" in packet["handoff"]
        print(json.dumps({"ok": True, "style": STYLE}, indent=2))
        return 0
    source, source_ref = read_source(args.source_file, args.source_text)
    packet = build_packet(source, source_ref, args.case_id)
    text = json.dumps(packet, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
