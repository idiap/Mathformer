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

"""Build a safe Isabelle/HOL physics autoformalization workflow plan."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

STYLE = "isabelle_physics_derivation_trace"

SHARED_PHYSICS_PREFORMALIZATION_HOOKS = [
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
]

SHARED_MATH_PREFORMALIZATION_HOOKS = [
    "intake.source_unit_inventory",
    "preformalization.expansion_support",
    "preformalization.expansion_difficulty",
    "preformalization.expansion_web_support",
    "preformalization.expand",
    "preformalization.review.suite",
    "preformalization.review.completeness",
    "preformalization.review.bindings",
    "dependency.resolve",
    "preformalization.line_translation_packet",
    "preformalization.result_existence_precheck",
]

ISABELLE_BACKEND_HOOKS = [
    "isabelle.grounding.search",
    "physics.isabelle.workflow.plan",
    "physics.isabelle.type_system.build",
    "physics.isabelle.background.plan",
    "physics.isabelle.assumptions.encode",
    "draft.physics_isabelle_derivation",
    "execute.physics_isabelle_derivation",
    "review.physics_isabelle_final_hypotheses",
    "review.mathematical_isabelle_final_hypotheses",
    "consistency.physics_isabelle_report",
    "reflection.physics_isabelle_process",
]

FORBIDDEN_LEAN_HOOKS = [
    "physics.lean.workflow.plan",
    "physics.lean.type_system.build",
    "physics.lean.assumptions.encode",
    "draft.physics_lean_derivation",
    "execute.physics_lean_interpret",
    "consistency.physics_lean_report",
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


def build_plan(source: str, source_ref: str, case_id: str) -> dict[str, Any]:
    """Document the responsibility of ``build_plan``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    required_hooks = (
        SHARED_MATH_PREFORMALIZATION_HOOKS
        + SHARED_PHYSICS_PREFORMALIZATION_HOOKS
        + ISABELLE_BACKEND_HOOKS
    )
    return {
        "style": STYLE,
        "case_id": case_id,
        "source_ref": source_ref,
        "source_sha256": (
            hashlib.sha256(source.encode("utf-8")).hexdigest() if source else None
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "required_hooks": required_hooks,
        "backend": "isabelle",
        "artifact_contract": {
            "theory_extension": ".thy",
            "artifact_roots": ["artifacts/physics_isabelle", "Isabelle"],
            "imports_policy": (
                "use Complex_Main for scalar baselines; prefer HOL-Analysis.Analysis for vector, "
                "calculus, field, norm/inner-product, and operator surfaces when the local Isabelle "
                "installation exposes it; add optional sessions only when grounding cites an installed theory"
            ),
            "source_comment_policy": [
                "top-level Isabelle text block preserves original informal statement",
                "source anchors remain visible",
                "generated support assumptions are labeled",
                "formal alignment maps informal steps to theorem assumptions or proof blocks",
            ],
            "completion_forbidden_patterns": [
                "sorry",
                "oops",
                "quickcheck_params",
                "target as assumption",
            ],
        },
        "isabelle_library_grounding_policy": {
            "status": "maximal_isabelle_hol_native_first",
            "preferred_surfaces": [
                "real and complex from Complex_Main",
                "'a::euclidean_space or real ^ 'n from HOL-Analysis for vectors/components",
                "continuous_on, DERIV, has_derivative, has_vector_derivative for calculus",
                "inner, norm, bounded_linear, and linear for vector/operator structure",
                "locale/context assumptions with typed propositions instead of string-only physics context",
            ],
            "background_dependency_policy": [
                "autoformalize or reuse intermediate definitions, field definitions, law substitutions, and algebraic core lemmas before the target theorem is accepted",
                "route open requirements through dependency.resolve and physics.isabelle.background.plan",
                "do not replace missing library support with an empty local formalism unless the artifact is explicitly blocked",
            ],
            "completion_threshold": "high",
        },
        "lean_flow_isolation_contract": {
            "status": "safe_parallel_backend",
            "forbidden_hook_rewrites": FORBIDDEN_LEAN_HOOKS,
            "forbidden_artifact_overwrites": [
                "artifacts/physics_lean",
                "backends/lean/Mathformer/*.lean",
                "skills/physics-lean-*",
            ],
            "allowed_shared_inputs": [
                "physics source packets",
                "informal derivation expansion packets",
                "dimension/unit/law/frame/regime packets",
                "source line translation packets",
            ],
            "required_separate_outputs": [
                "physics_isabelle_workflow_plan",
                "physics_isabelle_type_system_packet",
                "physics_isabelle_background_dependency_plan",
                "physics_isabelle_assumption_packet",
                "isabelle_theory_file",
                "isabelle_execution_report",
                "physics_isabelle_consistency_report",
            ],
        },
        "semantic_preservation_policy": {
            "shared_preservation_goal": "preserve source target, quantities, physical laws, assumptions, units, dimensions, and derivation steps",
            "isabelle_specific_surface": [
                "Isar theorem statements",
                "locale or context blocks for assumptions when useful",
                "HOL-Analysis-native carriers, calculus predicates, and linear algebra surfaces before local scaffolds",
                "explicit generated-support facts for algebraic or operator bridges",
                "compact algebraic core lemmas called by physics-rich wrapper theorems",
            ],
            "failure_route": "local Isabelle repair followed by execution, final reviews, and physics Isabelle consistency report",
        },
        "review_gates": [
            "isabelle build succeeds or reports an explicit dependency blocker",
            "placeholder-free theory for complete status",
            "Isabelle/HOL library grounding level is high for physics-bearing sources",
            "background dependency plan has no open formalization obligations",
            "physics Isabelle final hypothesis review passes",
            "mathematical Isabelle final hypothesis review passes",
            "source anchors, unit/dimension notes, assumptions, and law provenance are visible",
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
    parser.add_argument("--case-id", default="physics_isabelle_case")
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
        source = "Show a physics force identity with units and source anchors."
        source_ref = "self-test"
    else:
        source, source_ref = read_source(args.source_file, args.source_text)
    plan = build_plan(source, source_ref, args.case_id)
    if args.self_test:
        assert plan["backend"] == "isabelle"
        assert "physics.lean.workflow.plan" not in plan["required_hooks"]
        assert "dependency.resolve" in plan["required_hooks"]
        assert "physics.isabelle.background.plan" in plan["required_hooks"]
        assert "draft.physics_isabelle_derivation" in plan["required_hooks"]
        assert (
            plan["isabelle_library_grounding_policy"]["completion_threshold"] == "high"
        )
        assert plan["lean_flow_isolation_contract"]["status"] == "safe_parallel_backend"
    text = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
