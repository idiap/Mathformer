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

"""Compare the Lean physics loop against shared mathematical pipeline gates."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Sequence

SHARED_REQUIRED_HOOKS = {
    "source_readiness": [
        "intake.source_unit_inventory",
        "preformalization.line_translation_packet",
        "preformalization.result_existence_precheck",
    ],
    "proof_expansion_and_web_support": [
        "preformalization.expansion_support",
        "preformalization.expansion_difficulty",
        "preformalization.expansion_web_support",
        "preformalization.expand",
        "preformalization.review.suite",
        "preformalization.review.completeness",
        "preformalization.review.bindings",
        "dependency.resolve",
    ],
    "mathlib_grounding": [
        "mathlib.result_existence_search",
        "mathlib.discovery",
        "mathlib.ontology.validate",
        "mathlib.hierarchy.navigate",
        "mathlib.hierarchy.module_tree",
        "mathlib.hierarchy.declaration_neighborhood",
        "mathlib.verify",
        "mathlib.compatibility_loop",
        "mathlib.coverage",
        "mathlib.web_strategy",
        "mathlib.web_evidence",
        "mathlib.web_grounding_loop",
        "mathlib.grounding_maximize",
        "mathlib.api_plan",
        "mathlib.import.plan",
        "mathlib.import.context",
    ],
    "generic_lean_critique": [
        "critique.semantic",
        "critique.syntax",
        "critique.semantic_preservation",
        "critique.logical_soundness",
        "critique.mathlib_alignment",
        "critique.suite",
        "critique.reference_free_monitor",
    ],
    "generic_refinement_and_cleanup": [
        "refine.formal",
        "refine.semantic",
        "output.denoise",
        "annotate.line_comment_guard",
        "transition.taxonomy",
    ],
    "artifact_acceptance": [
        "postformalization.source_anchor_drift_guard",
        "artifact.realness_gate",
        "mathlib.import.minimize",
        "audit.compatibility",
        "postformalization.informalize",
        "consistency.declaration_shape",
        "postformalization.informal_internal_consistency",
        "postformalization.informal_consistency",
        "consistency.nonvacuity",
        "consistency.cross_file_concepts",
        "consistency.unified_report",
        "artifact.statistics",
        "evaluation.rfde_report",
    ],
}


DOMAIN_ADAPTATIONS = {
    "draft.initial": "draft.physics_lean_derivation",
    "draft.seed": "draft.physics_lean_derivation",
    "preformalization.expansion_web_support": "reused directly for hard derivation/proof gaps; physics packets add unit/law/frame search terms",
    "preformalization.review.suite": "reused directly; physics.gaps.expand and final reviewers strengthen it",
    "preformalization.review.completeness": "reused directly; physics gaps and physics final review strengthen it",
    "preformalization.review.bindings": "reused directly; physics symbol and Lean type packets strengthen it",
    "dependency.resolve": "reused directly; physics background dependency plans specialize it for definitions, laws, bridges, and algebraic cores",
    "consistency.unified_report": "consistency.unified_report + consistency.physics_lean_report",
}


PHYSICS_ADDITIONS = [
    "physics.source.extract",
    "physics.informal.elicit",
    "physics.informal.expand",
    "physics.informal.review",
    "physics.symbols.build",
    "physics.dimensions.model",
    "physics.units.ground",
    "physics.equations.parse",
    "physics.regimes.model",
    "physics.frames.build",
    "physics.gaps.detect",
    "physics.gaps.expand",
    "physics.laws.ground",
    "physics.lean.workflow.plan",
    "physics.lean.type_system.build",
    "physics.lean.assumptions.encode",
    "physics.lean.units.verify",
    "critique.physics_lean_semantics",
    "critique.physics_lean_assumptions",
    "critique.physics_lean_dimensions",
    "critique.physics_lean_generative_panel",
    "review.physics_final_hypotheses",
    "review.mathematical_final_hypotheses",
    "review.final_derivation_hypotheses",
    "refine.physics_lean_review",
    "consistency.physics_lean_report",
]


def extract_loop_hooks(text: str, loop_id: str) -> list[str]:
    """Document the responsibility of ``extract_loop_hooks``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_loop_hooks`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = text.splitlines()
    in_loop = False
    in_hooks = False
    hooks: list[str] = []
    for line in lines:
        if re.match(r"\s*-\s+id:\s+", line):
            current = re.sub(r"^\s*-\s+id:\s*", "", line).strip()
            if in_loop and current != loop_id:
                break
            in_loop = current == loop_id
            in_hooks = False
            continue
        if not in_loop:
            continue
        if re.match(r"\s*required_hooks:\s*$", line):
            in_hooks = True
            continue
        if in_hooks:
            match = re.match(r"\s*-\s+([A-Za-z0-9_.-]+)\s*$", line)
            if match:
                hooks.append(match.group(1))
                continue
            if re.match(r"\s*required_owner_skills:\s*$", line):
                break
    return hooks


def build_report(hooks_text: str) -> dict[str, object]:
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
    physics_hooks = set(
        extract_loop_hooks(hooks_text, "lean_physics_derivation_trace_loop")
    )
    categories = {}
    missing_all: list[str] = []
    for category, hooks in SHARED_REQUIRED_HOOKS.items():
        missing = [hook for hook in hooks if hook not in physics_hooks]
        missing_all.extend(missing)
        categories[category] = {
            "required": hooks,
            "present": [hook for hook in hooks if hook in physics_hooks],
            "missing": missing,
        }
    physics_additions = [hook for hook in PHYSICS_ADDITIONS if hook in physics_hooks]
    missing_physics_additions = [
        hook for hook in PHYSICS_ADDITIONS if hook not in physics_hooks
    ]
    return {
        "style": "lean_physics_mathematical_pipeline_parity_report",
        "status": (
            "pass" if not missing_all and not missing_physics_additions else "fail"
        ),
        "physics_loop_hook_count": len(physics_hooks),
        "shared_categories": categories,
        "missing_shared_hooks": missing_all,
        "domain_adaptations": DOMAIN_ADAPTATIONS,
        "physics_additions_present": physics_additions,
        "missing_physics_additions": missing_physics_additions,
        "semantic_preservation_explicit": "critique.semantic_preservation"
        in physics_hooks,
        "web_search_explicit": (
            "preformalization.expansion_web_support" in physics_hooks
            and "mathlib.web_strategy" in physics_hooks
            and "mathlib.web_evidence" in physics_hooks
            and "mathlib.web_grounding_loop" in physics_hooks
        ),
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
    parser.add_argument(
        "--hooks-file", type=Path, default=Path("skills/SKILL_HOOKS.yaml")
    )
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
        fake = """
loop_contracts:
  - id: lean_physics_derivation_trace_loop
    required_hooks:
      - intake.source_unit_inventory
      - preformalization.expansion_support
      - preformalization.expansion_difficulty
      - preformalization.expansion_web_support
      - preformalization.expand
      - preformalization.review.suite
      - preformalization.review.completeness
      - preformalization.review.bindings
      - dependency.resolve
      - preformalization.line_translation_packet
      - preformalization.result_existence_precheck
      - mathlib.result_existence_search
      - mathlib.discovery
      - mathlib.ontology.validate
      - mathlib.hierarchy.navigate
      - mathlib.hierarchy.module_tree
      - mathlib.hierarchy.declaration_neighborhood
      - mathlib.verify
      - mathlib.compatibility_loop
      - mathlib.coverage
      - mathlib.web_strategy
      - mathlib.web_evidence
      - mathlib.web_grounding_loop
      - mathlib.grounding_maximize
      - mathlib.api_plan
      - mathlib.import.plan
      - mathlib.import.context
      - critique.semantic
      - critique.syntax
      - critique.semantic_preservation
      - critique.logical_soundness
      - critique.mathlib_alignment
      - critique.suite
      - critique.reference_free_monitor
      - refine.formal
      - refine.semantic
      - output.denoise
      - annotate.line_comment_guard
      - transition.taxonomy
      - postformalization.source_anchor_drift_guard
      - artifact.realness_gate
      - mathlib.import.minimize
      - audit.compatibility
      - postformalization.informalize
      - consistency.declaration_shape
      - postformalization.informal_internal_consistency
      - postformalization.informal_consistency
      - consistency.nonvacuity
      - consistency.cross_file_concepts
      - consistency.unified_report
      - artifact.statistics
      - evaluation.rfde_report
      - physics.source.extract
      - physics.informal.elicit
      - physics.informal.expand
      - physics.informal.review
      - physics.symbols.build
      - physics.dimensions.model
      - physics.units.ground
      - physics.equations.parse
      - physics.regimes.model
      - physics.frames.build
      - physics.gaps.detect
      - physics.gaps.expand
      - physics.laws.ground
      - physics.lean.workflow.plan
      - physics.lean.type_system.build
      - physics.lean.assumptions.encode
      - physics.lean.units.verify
      - critique.physics_lean_semantics
      - critique.physics_lean_assumptions
      - critique.physics_lean_dimensions
      - critique.physics_lean_generative_panel
      - review.physics_final_hypotheses
      - review.mathematical_final_hypotheses
      - review.final_derivation_hypotheses
      - refine.physics_lean_review
      - consistency.physics_lean_report
    required_owner_skills:
      - x
"""
        report = build_report(fake)
        assert report["status"] == "pass"
        assert report["missing_physics_additions"] == []
        assert report["semantic_preservation_explicit"] is True
        assert report["web_search_explicit"] is True
    else:
        report = build_report(args.hooks_file.read_text(encoding="utf-8"))
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
