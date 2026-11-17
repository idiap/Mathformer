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

"""Build a deterministic expanded informal physics derivation skeleton."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Sequence

STYLE = "physics_informal_derivation_expansion_packet"
UNRESOLVED_HINTS = {"unresolved law or algebraic rule", "unresolved transition rule"}


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


def law_hints(text: str) -> list[str]:
    """Document the responsibility of ``law_hints``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``law_hints`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    hints = []
    patterns = {
        "Newton law": r"Newton|F(?:_\{?[\w]+\}?)?\s*=|ma\b|m\\ddot",
        "Maxwell equation": r"Maxwell|\\nabla|curl|divergence",
        "Hamiltonian dynamics": r"Hamilton|Hamiltonian",
        "Quantum/TDSE identity": r"TDSE|Schr[oö]dinger|\\hat|\\ket|\\bra|\\hbar|inner product",
        "Lagrangian mechanics": r"Lagrange|Lagrangian|Euler-Lagrange",
        "conservation law": r"conservation|conserved",
        "Fourier/Poisson relation": r"Fourier|Poisson",
        "calculus transformation": r"\\frac|\\partial|derivative|integral|\\int",
    }
    for name, pattern in patterns.items():
        if re.search(pattern, text, flags=re.I):
            hints.append(name)
    return hints or ["unresolved law or algebraic rule"]


def grounding_roles(text: str) -> list[str]:
    """Document the responsibility of ``grounding_roles``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``grounding_roles`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    roles = []
    patterns = {
        "mathlib_vector_surface": r"\\vec|\\mathbf|vector|component|projection|cross|\\times",
        "field_definition": r"(?<!\{)\bfield\b|potential|gradient|curl|divergence|\\nabla|electric field|magnetic field",
        "calculus_support": r"\\frac|\\partial|derivative|integral|\\int|\\dot|d/dt|product rule|chain rule",
        "source_law_support": r"Newton|F(?:_\{?[\w]+\}?)?\s*=|m\\ddot|Maxwell|Hamilton|Lagrange|Euler-Lagrange|Lorentz|conservation|Schr[oö]dinger|TDSE",
        "unit_dimension_bridge": r"unit|dimension|force|mass|charge|velocity|energy|current|newton|joule|\\hbar|Hamiltonian|F(?:_\{?[\w]+\}?)?\s*=",
        "algebraic_core": r"=|\\le|\\ge|\\approx|solve|rearrange|substitut|cancel|therefore|hence|thus",
        "operator_surface": r"operator|Hamiltonian|\\hat|\\ket|\\bra|inner product|adjoint",
    }
    for role, pattern in patterns.items():
        if re.search(pattern, text, flags=re.I):
            roles.append(role)
    return roles or ["source_alignment"]


def expected_grounding_from_roles(roles: list[str]) -> list[dict[str, str]]:
    """Document the responsibility of ``expected_grounding_from_roles``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``expected_grounding_from_roles`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    targets = {
        "mathlib_vector_surface": (
            "Mathlib carrier",
            "EuclideanSpace Real (Fin n) plus projection bridge",
        ),
        "field_definition": (
            "definition",
            "field/potential definitions with explicit smoothness predicates",
        ),
        "calculus_support": (
            "background result",
            "HasDerivAt/HasFDerivAt or derivative rule support",
        ),
        "source_law_support": (
            "background result",
            "source-backed physical law support lemma",
        ),
        "unit_dimension_bridge": (
            "bridge lemma",
            "unit/dimension homogeneity obligation",
        ),
        "algebraic_core": ("background result", "compact algebraic core theorem"),
        "operator_surface": (
            "Mathlib carrier",
            "LinearMap/Matrix/InnerProductSpace operator surface",
        ),
        "source_alignment": ("commentary", "source-aligned formal declaration/comment"),
    }
    return [
        {
            "role": role,
            "formal_object_kind": targets[role][0],
            "expected_grounding": targets[role][1],
        }
        for role in roles
    ]


def merge_unique(*items: list[str]) -> list[str]:
    """Document the responsibility of ``merge_unique``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``merge_unique`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    merged = []
    seen = set()
    for group in items:
        for item in group:
            if item not in seen:
                merged.append(item)
                seen.add(item)
    return merged


def transition_law_hints(
    previous: dict[str, Any], current: dict[str, Any]
) -> list[str]:
    """Document the responsibility of ``transition_law_hints``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``transition_law_hints`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    hints = [
        hint
        for hint in merge_unique(
            previous.get("law_or_rule_hints", []), current.get("law_or_rule_hints", [])
        )
        if hint not in UNRESOLVED_HINTS
    ]
    return hints or ["unresolved transition rule"]


def transition_grounding_roles(
    previous: dict[str, Any], current: dict[str, Any]
) -> list[str]:
    """Document the responsibility of ``transition_grounding_roles``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``transition_grounding_roles`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    adjacent_roles = [
        role
        for role in merge_unique(
            previous.get("expected_grounding_roles", []),
            current.get("expected_grounding_roles", []),
        )
        if role != "source_alignment"
    ]
    return merge_unique(["calculus_support", "algebraic_core"], adjacent_roles)


def support_status(line: str) -> str:
    """Document the responsibility of ``support_status``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``support_status`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if any(token in line.lower() for token in ["therefore", "hence", "so ", "thus"]):
        return "source_supported_transition"
    if any(op in line for op in ["=", "\\le", "\\ge", "\\approx", "\\to"]):
        return "literal_source"
    return "context_note"


def build_steps(source: str) -> list[dict[str, Any]]:
    """Document the responsibility of ``build_steps``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    raw_lines = [line.strip() for line in source.splitlines() if line.strip()]
    if not raw_lines and source.strip():
        raw_lines = [source.strip()]
    source_steps = []
    for index, line in enumerate(raw_lines, start=1):
        status = support_status(line)
        source_steps.append(
            {
                "step_id": f"S{index}",
                "source_anchor": f"Source:{index}",
                "statement": line,
                "support_status": status,
                "law_or_rule_hints": law_hints(line),
                "expected_grounding_roles": grounding_roles(line),
                "expected_formal_grounding": expected_grounding_from_roles(
                    grounding_roles(line)
                ),
                "assumptions_needed": [],
                "dimension_unit_status": "needs_check",
                "formalization_role": (
                    "candidate_derivation_step"
                    if status != "context_note"
                    else "context"
                ),
                "expansion_needed": status != "literal_source",
            }
        )
    steps = []
    generated_index = 1
    for index, current in enumerate(source_steps):
        if index > 0:
            previous = source_steps[index - 1]
            if (
                previous["support_status"] == "literal_source"
                and current["support_status"] == "literal_source"
            ):
                hints = transition_law_hints(previous, current)
                roles = transition_grounding_roles(previous, current)
                steps.append(
                    {
                        "step_id": f"G{generated_index}",
                        "source_anchor": f"{previous['source_anchor']}->{current['source_anchor']}",
                        "statement": "Generated-support transition required between adjacent source equations; prove the local bridge without rewriting either source equation.",
                        "support_status": "generated_support_needed",
                        "law_or_rule_hints": hints,
                        "expected_grounding_roles": roles,
                        "expected_formal_grounding": expected_grounding_from_roles(
                            roles
                        ),
                        "transition_context": {
                            "from_step": previous["step_id"],
                            "to_step": current["step_id"],
                            "inherited_rule_hints": hints,
                            "locality_constraint": "only add/prove the bridge; preserve both source-anchored steps",
                        },
                        "assumptions_needed": [],
                        "dimension_unit_status": "needs_check",
                        "formalization_role": "gap_bridge",
                        "expansion_needed": True,
                    }
                )
                generated_index += 1
        steps.append(current)
    return steps


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
    steps = build_steps(source)
    generated = [
        step for step in steps if step["support_status"] == "generated_support_needed"
    ]
    roles = sorted(
        {role for step in steps for role in step.get("expected_grounding_roles", [])}
    )
    return {
        "style": STYLE,
        "case_id": case_id,
        "source_ref": source_ref,
        "source_sha256": (
            hashlib.sha256(source.encode("utf-8")).hexdigest() if source else None
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expansion_policy": {
            "literal_source_is_preserved": True,
            "generated_support_must_be_labeled": True,
            "hard_gaps_route_to_web_support": True,
            "expected_grounding_must_be_explicit_before_backend_drafting": True,
        },
        "expected_grounding_summary": {
            "status": "expected" if roles else "missing",
            "roles": roles,
            "formalization_steering": [
                "create or reuse support declarations before the target theorem",
                "prefer Mathlib-native surfaces before local wrappers",
                "route unresolved definitions/results through dependency.resolve",
            ],
        },
        "steps": steps,
        "generated_support_queue": generated,
        "handoff": [
            "preformalization.expansion_support",
            "preformalization.expansion_web_support",
            "dependency.resolve",
            "physics.informal.review",
            "physics.laws.ground",
            "physics.lean.workflow.plan",
            "physics.lean.type_system.build",
            "mathlib.grounding_maximize",
        ],
        "blockers": ["generated_support_unreviewed"] if generated else [],
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
        packet = build_packet("F = m a\nTherefore a = F / m", "self-test", "self_test")
        assert packet["style"] == STYLE
        assert packet["steps"]
        assert packet["expected_grounding_summary"]["status"] == "expected"
        assert all(step.get("expected_formal_grounding") for step in packet["steps"])
        multi_gap = build_packet(
            "F = m a\nF = m \\frac{dv}{dt}\np = m v", "self-test", "self_test"
        )
        assert len(multi_gap["generated_support_queue"]) == 2
        assert multi_gap["generated_support_queue"][0]["law_or_rule_hints"] != [
            "unresolved transition rule"
        ]
        assert multi_gap["generated_support_queue"][0]["transition_context"][
            "locality_constraint"
        ]
        assert "physics.informal.review" in packet["handoff"]
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
