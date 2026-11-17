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

"""Build a deterministic Lean-physics autoformalization workflow plan."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

STYLE = "lean_physics_derivation_trace"
DESIGN_TODO_ARTIFACT = (
    "artifacts/physics_lean/reviews/autoformalization_design_todos.md"
)

PHYSICS_PREFORMALIZATION_HOOKS = [
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

PHYSICS_LEAN_SETUP_HOOKS = [
    "physics.lean.workflow.plan",
    "physics.lean.type_system.build",
    "physics.lean.assumptions.encode",
]

SHARED_MATH_AUTOFORMALIZATION_HOOKS = [
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
    "draft.physics_lean_derivation",
    "execute.initial",
    "execute.physics_lean_interpret",
    "check.compile",
    "critique.semantic",
    "critique.syntax",
    "critique.semantic_preservation",
    "critique.logical_soundness",
    "critique.mathlib_alignment",
    "critique.suite",
    "critique.reference_free_monitor",
    "refine.formal",
    "refine.semantic",
    "output.denoise",
    "annotate.line_comment_guard",
    "transition.taxonomy",
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
]

PHYSICS_LEAN_CRITIC_REVIEW_HOOKS = [
    "physics.lean.units.verify",
    "critique.physics_lean_semantics",
    "critique.physics_lean_assumptions",
    "critique.physics_lean_dimensions",
    "critique.physics_lean_generative_panel",
    "critique.physics_lean_drift_pathology_monitor",
    "repair.physics_math_object_detect",
    "repair.mathformerphysicslib_object_workbench",
    "repair.physics_lean_notational_collapse",
    "repair.physics_lean_abstraction_elevation",
    "repair.physics_lean_proof_strategy_alignment",
    "repair.physics_lean_implicit_premise_normalize",
    "repair.physics_lean_pathology_loop",
    "repair.physics_lean_generative_repair",
    "repair.physics_lean_repair_expansion_cartography",
    "repair.physics_lean_recursive_repair_control",
    "review.physics_final_hypotheses",
    "review.mathematical_final_hypotheses",
    "review.final_derivation_hypotheses",
    "refine.physics_lean",
    "refine.physics_lean_review",
    "consistency.physics_lean_report",
    "reflection.physics_lean_process",
]

OPTIONAL_POSTHOC_REFLECTION_HOOKS = [
    "reflection.physics_formal_answer_compare",
]

SHARED_PREFORMALIZATION_PREFIX_COUNT = 8

REQUIRED_HOOKS = (
    SHARED_MATH_AUTOFORMALIZATION_HOOKS[:SHARED_PREFORMALIZATION_PREFIX_COUNT]
    + PHYSICS_PREFORMALIZATION_HOOKS
    + PHYSICS_LEAN_SETUP_HOOKS
    + SHARED_MATH_AUTOFORMALIZATION_HOOKS[SHARED_PREFORMALIZATION_PREFIX_COUNT:]
    + PHYSICS_LEAN_CRITIC_REVIEW_HOOKS
)


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
    return {
        "style": STYLE,
        "case_id": case_id,
        "source_ref": source_ref,
        "source_sha256": (
            hashlib.sha256(source.encode("utf-8")).hexdigest() if source else None
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "required_hooks": REQUIRED_HOOKS,
        "optional_posthoc_hooks": OPTIONAL_POSTHOC_REFLECTION_HOOKS,
        "design_review_todo_artifact": DESIGN_TODO_ARTIFACT,
        "generative_design_guards": {
            "source": DESIGN_TODO_ARTIFACT,
            "status": "active_for_new_or_repaired_lean_physics_artifacts",
            "must_address_before_complete": [
                "semantic_preservation_contract",
                "non_vacuous_physics_contexts",
                "non_reflexive_unit_dimension_evidence",
                "unbounded_operator_domain_semantics_for_qm",
                "lean_metadata_or_decl_shape_evidence_for_source_steps",
                "final_theorem_dependency_trust_state",
            ],
            "advisory_until_deterministic_gate": (
                "Generative proposals may suggest repairs, but completion still "
                "requires Lean compile, source-only recursive reports, final review, "
                "and thoroughness evidence."
            ),
        },
        "dataset_formal_answer_reflection_policy": {
            "status": "inspiration_only_not_benchmark",
            "timing": "after an informal-first candidate, draft blocker report, or final consistency report exists",
            "forbidden_use": "do not inspect withheld dataset formal_answer before first-pass drafting or reviewer critique",
            "allowed_use": [
                "compile withheld formal answer as portability evidence",
                "compare theorem shape, abstraction level, imports, source anchors, assumptions, and unit/dimension surfaces",
                "propose localized monotonic refinements routed through review refinement",
            ],
            "not_allowed_as": [
                "ground truth label",
                "benchmark score",
                "permission to erase physics semantics into a weaker theorem",
            ],
        },
        "pipeline_parity_contract": {
            "comparison_target": "mathematical_autoformalization_pipeline",
            "shared_mathematical_gates": [
                "source-unit inventory before backend-specific physics extraction",
                "proof-expansion support, difficulty estimation, web research for hard gaps, prerequisite expansion, and expansion review",
                "dependency resolution for intermediate definitions, background lemmas, and support declarations before target drafting",
                "source line translation and source-anchor preservation",
                "result-existence precheck before first-pass drafting",
                "mathlib result search, local verification, web grounding, import planning, and import minimization",
                "Lean execution, compile checking, denoising, line-comment hygiene, and transition taxonomy",
                "generic Lean critique suite: syntax, semantic preservation, logical soundness, mathlib alignment, and suite orchestration",
                "formal and semantic refinement loops",
                "reverse informalization, declaration-shape consistency, informal internal consistency, informal consistency, non-vacuity, cross-file concepts, unified consistency, artifact statistics, RFDE, and reference-free monitoring",
            ],
            "physics_adaptations": [
                "physics informal elicitation, expansion, and readiness review run before symbol tables, law grounding, and Lean typing, and must state expected formal grounding roles",
                "proof-expansion web support is reused for hard physics derivation gaps, with physics-specific unit/law/frame search terms",
                "the generic initial drafter is replaced by a source-anchored typed Lean physics drafter",
                "generic semantic preservation remains required and is strengthened by physical-semantics, assumption, and dimension critics",
                "generic mathlib grounding remains required, is supplemented by physics-law grounding, and must prefer Mathlib-native physics carriers before local wrappers",
                "generic final consistency remains required and is supplemented by a physics Lean consistency report",
            ],
            "physics_only_extensions": [
                "physical quantity and dimension typing",
                "unit-system grounding and Lean unit obligations",
                "coordinate frame, regime, gauge, boundary, and approximation context",
                "physics-law provenance",
                "physics background dependency plan for intermediate definitions, bridge lemmas, source-law support, and algebraic cores",
                "Codex-exec generative adversarial critics for empty-formalism risk",
                "physics and mathematical final hypothesis reviewers",
                "FormalScience pathology repair loop that detects missing physics objects, works over them in MathformerPhysicsLib, then routes target refinement",
                "guarded Codex-exec generative repair proposals that remain advisory until deterministic gates rerun",
                "recursive repair expansion cartography that enumerates every pathology, object, library, generative, and rerun-gate obligation before iteration",
                "bounded recursive repair control with iteration signatures, exhaustive coverage checks, and repeated-state blocking",
                "localized monotonic review-refinement routing",
            ],
        },
        "semantic_preservation_policy": {
            "generic_gate": "critique.semantic_preservation",
            "commentary_contract": {
                "required_header": "Semantic preservation contract",
                "required_fields": [
                    "Source target",
                    "Lean target",
                    "Preservation status",
                    "Source assumptions preserved",
                    "Additional mathematical assumptions introduced",
                    "Not modeled here",
                    "Semantic deltas",
                    "Step alignment",
                    "Trust boundary",
                ],
                "allowed_preservation_statuses": [
                    "exact",
                    "component_projection",
                    "scalar_expectation_projection",
                    "conditional_replay_over_frontier",
                    "blocked_or_not_modeled",
                ],
            },
            "physics_strengthening_gates": [
                "critique.physics_lean_semantics",
                "critique.physics_lean_assumptions",
                "critique.physics_lean_dimensions",
                "critique.physics_lean_drift_pathology_monitor",
                "repair.physics_lean_pathology_loop",
                "repair.physics_lean_generative_repair",
                "repair.physics_lean_repair_expansion_cartography",
                "repair.physics_lean_recursive_repair_control",
                "review.physics_final_hypotheses",
                "review.mathematical_final_hypotheses",
            ],
            "protected_content": [
                "source logical shape and quantifier structure",
                "target equation or relation direction",
                "physical quantities, vectors, fields, dimensions, and units",
                "frames, regimes, gauges, boundary conditions, and sign conventions",
                "physical-law dependencies and generated-support assumptions",
            ],
            "vacuity_markers_to_repair_or_block": [
                "PhysicsContext True for boundary, smoothness, frame, domain, nonzero, normalization, or regime obligations",
                "UnitDimensionCompatible x x used as the only unit/dimension evidence",
                "required_grounding_terms audit anchors after their checklist role is complete",
                "source-law closure recognized only by declaration name without declaration-shape or metadata evidence",
            ],
            "failure_route": "refine.semantic or refine.physics_lean_review, followed by affected generic and physics gates",
        },
        "maximal_mathlib_grounding_policy": {
            "target": "Mathlib-native physics theorem surfaces before local wrappers",
            "minimum_complete_level": "high",
            "preferred_surfaces": [
                "EuclideanSpace Real (Fin n) for finite vectors and component projections",
                "X -> EuclideanSpace Real (Fin 3) or module-valued functions for vector fields",
                "LinearMap, continuous linear maps, or module homomorphisms for linear physics operators",
                "HasDerivAt, HasFDerivAt, Differentiable, or ContDiff for derivative assumptions",
                "Matrix, inner-product, module, and Hermitian/self-adjoint surfaces for quantum/operator examples",
                "typed Prop assumptions or source-law structures with propositional fields for physics context",
            ],
            "fallback_only_surfaces": [
                "local Quantity wrappers",
                "local VectorQuantity wrappers",
                "opaque dimension marker types",
                "String-valued context, source-law, frame, or smoothness labels",
                "raw Real scalar wrapper theorem without a Mathlib-typed projection bridge",
            ],
            "fallback_acceptance_rule": "fallback surfaces block complete status unless the mathlib grounding report records an explicit abstraction boundary and the final physics reviewer waives the gap",
            "measurement": [
                "run mathlib.grounding_maximize on saved Lean artifacts",
                "run review.physics_final_hypotheses with Mathlib grounding checks enabled",
                "route low or fallback-only grounding to refine.physics_lean_review",
            ],
        },
        "background_dependency_policy": {
            "packet": "physics_lean_background_dependency_plan",
            "builder": "physics-lean-workflow-orchestrator/scripts/build_physics_lean_background_plan.py",
            "purpose": "autoformalize required intermediate definitions and background results before the target theorem",
            "early_steering_input": "physics informal elicitation/expansion expected_formal_grounding roles",
            "item_kinds": [
                "definition",
                "background_result",
                "bridge_lemma",
                "algebraic_core",
                "source_law_support",
            ],
            "required_before_target": [
                "Mathlib-native carriers and projections",
                "field/operator definitions",
                "calculus/product/chain-rule support",
                "source-law support lemmas",
                "unit/dimension homogeneity bridge lemmas",
                "compact algebraic core theorem",
            ],
            "completion_rule": "every required item is formalized, reused from Mathlib/MathformerPhysicsLib, or explicitly blocked before complete status",
            "failure_route": "dependency.resolve, then refine.physics_lean_review on the smallest open support item",
        },
        "lean_artifact_contract": {
            "module_comment": [
                "source anchors",
                "physics context",
                "dimension policy",
                "semantic preservation contract",
                "semantic deltas",
                "trust boundary",
            ],
            "required_sections": [
                "line translation packet",
                "result existence and mathlib grounding",
                "background dependency plan",
                "intermediate definitions",
                "background results and bridge lemmas",
                "source quantities",
                "informal derivation elicitation and expansion",
                "dimensions and units",
                "contextual assumptions",
                "physical laws",
                "derivation theorem",
                "unit consistency lemmas",
                "generic Lean critique evidence",
                "semantic preservation evidence",
                "physics critic evidence",
                "maximal Mathlib grounding evidence",
                "final hypothesis review evidence",
                "reference-free monitor evidence",
                "semantic-preservation contract fields",
                "dependency trust-state ledger",
            ],
            "forbidden_completion_patterns": [
                "target axiom",
                "hypothesis identical to target",
                "target theorem depending on unformalized background obligations",
                "background lemma identical to the target conclusion",
                "unjustified raw Real erasure",
                "silent regime strengthening",
                "weakened theorem avoiding source physics",
                "sorry/admit in complete status",
                "local wrappers or opaque dimensions reported as maximally grounded",
                "String-valued context or source-law labels used as final evidence",
                "vacuous PhysicsContext True used as source-backed smoothness, boundary, frame, domain, nonzero, normalization, or regime evidence",
                "reflexive UnitDimensionCompatible x x used as the only unit/dimension evidence",
            ],
        },
        "refinement_loops": [
            {
                "id": "background_dependency_autoformalization_loop",
                "trigger": "source uses definitions, laws, projections, calculus rules, unit bridges, or algebraic support not yet formalized",
                "evidence": [
                    "physics_lean_background_dependency_plan",
                    "dependency_resolution_trace",
                    "mathlib_candidate_verification",
                    "background_declaration_compile_report",
                    "background_support_review",
                ],
                "repair_surface": [
                    "intermediate definitions",
                    "background lemmas",
                    "projection bridges",
                    "source-law support declarations",
                    "unit/dimension bridge lemmas",
                    "imports",
                ],
                "monotonicity": [
                    "formalize or reuse prerequisites before editing the target theorem",
                    "preserve already compiled support declarations",
                    "do not strengthen a background lemma beyond its source or generated-support label",
                    "rerun dependency.resolve, mathlib grounding, Lean execution, and final reviews",
                ],
            },
            {
                "id": "informal_elicitation_expansion_loop",
                "trigger": "terse source derivation, missing physical context, missing expected grounding, unresolved generated support, or readiness review failure",
                "evidence": [
                    "physics_informal_elicitation_packet",
                    "expected_formal_grounding",
                    "physics_informal_derivation_expansion_packet",
                    "physics_informal_readiness_report",
                    "proof_expansion_web_research_packets",
                ],
                "repair_surface": [
                    "informal step expansion",
                    "generated-support labels",
                    "source anchors",
                    "missing assumptions",
                    "law/rule provenance",
                    "unit and dimension notes",
                    "expected formal grounding roles",
                    "background dependency expectations",
                ],
                "monotonicity": [
                    "new informal steps must be added as generated support unless literally source-backed",
                    "do not remove source anchors or blocker labels to make formalization easier",
                ],
            },
            {
                "id": "lean_diagnostic_loop",
                "trigger": "Lean parser/elaborator/type/proof errors",
                "evidence": ["lean_error_log", "physics_lean_execution_interpretation"],
                "repair_surface": ["imports", "types", "proof script", "local lemmas"],
            },
            {
                "id": "generic_lean_critique_loop",
                "trigger": "syntax, logical soundness, mathlib alignment, or critique-suite failures",
                "evidence": [
                    "lean_syntax_critic_report",
                    "lean_logical_soundness_report",
                    "lean_mathlib_alignment_report",
                    "lean_critique_suite_report",
                ],
                "repair_surface": [
                    "imports",
                    "binder domains",
                    "theorem statement",
                    "proof dependencies",
                    "mathlib API choices",
                ],
            },
            {
                "id": "mathematical_semantic_preservation_loop",
                "trigger": "generic Lean semantic-preservation critic reports source-to-Lean drift",
                "evidence": [
                    "line_translation_packet",
                    "semantic_preservation_report",
                    "reverse_informalization_packet",
                    "source_anchor_drift_report",
                ],
                "repair_surface": [
                    "theorem statement",
                    "binder domains",
                    "quantifier shape",
                    "conclusion shape",
                    "source anchors",
                    "comments",
                ],
                "monotonicity": [
                    "only weaken or strengthen the Lean statement when the source anchor justifies the shape correction",
                    "rerun declaration-shape, semantic-preservation, non-vacuity, and affected physics reviewers",
                ],
            },
            {
                "id": "unit_dimension_loop",
                "trigger": "dimension or unit obligation fails",
                "evidence": [
                    "physics_lean_unit_report",
                    "dimension_packet",
                    "unit_packet",
                ],
                "repair_surface": [
                    "quantity types",
                    "dimension lemmas",
                    "assumption packet",
                ],
            },
            {
                "id": "explicit_critic_loop",
                "trigger": "deterministic or generative physics critic reports semantic, assumption, dimension, or empty-formalism risk",
                "evidence": [
                    "physics_lean_physical_semantics_critic_report",
                    "physics_lean_assumption_critic_report",
                    "physics_lean_dimension_critic_report",
                    "physics_lean_generative_critic_report",
                ],
                "repair_surface": [
                    "theorem statement",
                    "quantity typing",
                    "projection lemmas",
                    "assumption labels",
                    "source law grounding",
                ],
            },
            {
                "id": "assumption_context_loop",
                "trigger": "missing, ambiguous, or silently strengthened assumptions",
                "evidence": ["physics_lean_assumption_packet", "source anchors"],
                "repair_surface": ["hypotheses", "structure fields", "regime notes"],
            },
            {
                "id": "semantic_reverse_loop",
                "trigger": "reverse informalization diverges from source physics",
                "evidence": [
                    "lean_informalization_packet",
                    "source_anchor_drift_report",
                ],
                "repair_surface": [
                    "theorem statement",
                    "physical law grounding",
                    "comments",
                ],
            },
            {
                "id": "mathlib_grounding_loop",
                "trigger": "private abstractions replace available mathlib APIs or physics final review reports low Mathlib grounding",
                "evidence": [
                    "result_existence_report",
                    "mathlib_grounding_report",
                    "mathlib_web_grounding_packet",
                    "import_plan_findings",
                    "import_context_report",
                    "physics_final_hypothesis_review.mathlib_grounding_level",
                ],
                "repair_surface": [
                    "imports",
                    "API use",
                    "declaration shapes",
                    "physics-law grounding",
                    "quantity_typing",
                    "projection_bridge",
                    "contextual assumptions as typed propositions",
                ],
            },
            {
                "id": "reference_free_monotonicity_loop",
                "trigger": "accepted refinement decreases reference-free critic scores or shrinks protected theorem/source surfaces",
                "evidence": [
                    "reference_free_critic_packet",
                    "rfde_report",
                    "artifact_statistics",
                    "transition_taxonomy",
                ],
                "repair_surface": [
                    "theorem statement",
                    "source anchors",
                    "critic waivers",
                    "refinement plan",
                ],
                "monotonicity": [
                    "do not accept a smaller theorem, fewer anchors, or lower realness/non-vacuity evidence without explicit semantic-preservation justification",
                ],
            },
            {
                "id": "final_review_refinement_loop",
                "trigger": "physics or mathematical final hypothesis review fails",
                "evidence": [
                    "physics_final_hypothesis_review",
                    "mathematical_final_hypothesis_review",
                    "final_derivation_hypothesis_review",
                    "physics_lean_review_refinement_plan",
                ],
                "repair_surface": [
                    "quantity typing",
                    "unit obligations",
                    "contextual assumptions",
                    "law grounding",
                    "mathlib grounding",
                    "binder domains",
                    "quantifier shape",
                    "conclusion shape",
                    "proof realness",
                    "non-vacuity",
                ],
                "monotonicity": [
                    "localize edits to reviewer findings",
                    "preserve already passing source anchors and gates",
                    "rerun affected reviewers before complete status",
                ],
            },
            {
                "id": "process_reflection_loop",
                "trigger": "recurring blockers or costly plateau",
                "evidence": ["rfde_report", "critic history", "gate decisions"],
                "repair_surface": ["prompts", "skills", "tests", "hook policy"],
            },
            {
                "id": "posthoc_dataset_formal_answer_reflection_loop",
                "trigger": "FormalPhysics withheld formal_answer is available after the informal-first run",
                "evidence": [
                    "physics_formal_answer_comparison_reflection",
                    "local Mathformer candidate or explicit draft blockers",
                    "dataset formal_answer compile report",
                ],
                "repair_surface": [
                    "lemma decomposition",
                    "operator abstraction choices",
                    "proof tactics",
                    "import policy",
                    "source-anchor comments",
                ],
                "monotonicity": [
                    "treat dataset code as inspiration only, never as a benchmark label",
                    "reroute accepted changes through refine.physics_lean_review and affected critics",
                    "preserve stronger Mathformer physics typing, units, dimensions, and assumptions even when dataset code is simpler",
                ],
            },
        ],
        "acceptance_gates": [
            "Line translation packet covers the selected source spans",
            "informal elicitation, informal expansion, expected grounding summary, and informal readiness review pass before backend drafting",
            "hard informal derivation gaps have proof-expansion web support or explicit unresolved status",
            "background dependency plan is complete: required definitions, support lemmas, bridge lemmas, and algebraic cores are formalized, reused, or explicitly blocked",
            "result-existence precheck does not find an existing local or official-source result requiring reuse",
            "mathlib grounding, web evidence, candidate verification, import context, and import minimization are complete or explicitly blocked",
            "physics theorem surfaces reach high Mathlib grounding or carry explicit abstraction-boundary blockers",
            "Lean compiles under intended imports",
            "source anchors valid and sufficiently covered",
            "realness gate passes",
            "generic Lean semantic-preservation, syntactic, logical-soundness, mathlib-alignment, and critique-suite gates pass",
            "unit and dimension verification passes or has explicit blockers",
            "explicit physics critics pass or report justified blockers",
            "contextual assumptions are source-backed or generated-support",
            "reverse informalization agrees with the source physics",
            "informal internal consistency, informal consistency, cross-file concept, non-vacuity, and declaration-shape gates pass",
            "final physics and mathematical hypothesis reviewers pass",
            "review-driven refinements are localized and monotonic",
            "reference-free monitor and RFDE report no unprotected regression",
            "no hidden final answer, target axiom, or raw-scalar erasure blocker",
            "no local wrapper, opaque-dimension, or String-context scaffold is treated as maximally grounded",
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
    parser.add_argument("--case-id", default="physics_lean_case")
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
        plan = build_plan("F = ma", "self-test", "self_test")
        assert STYLE == plan["style"]
        assert "critique.semantic_preservation" in plan["required_hooks"]
        assert "physics.informal.elicit" in plan["required_hooks"]
        assert "preformalization.expansion_web_support" in plan["required_hooks"]
        assert "dependency.resolve" in plan["required_hooks"]
        assert "review.final_derivation_hypotheses" in plan["required_hooks"]
        assert plan["required_hooks"].index("intake.source_unit_inventory") < plan[
            "required_hooks"
        ].index("physics.source.extract")
        assert plan["required_hooks"].index("physics.informal.review") < plan[
            "required_hooks"
        ].index("physics.symbols.build")
        assert plan["required_hooks"].index("physics.lean.assumptions.encode") < plan[
            "required_hooks"
        ].index("preformalization.line_translation_packet")
        assert plan["required_hooks"].index("dependency.resolve") < plan[
            "required_hooks"
        ].index("preformalization.line_translation_packet")
        assert (
            "reflection.physics_formal_answer_compare" in plan["optional_posthoc_hooks"]
        )
        assert (
            plan["dataset_formal_answer_reflection_policy"]["status"]
            == "inspiration_only_not_benchmark"
        )
        assert (
            plan["semantic_preservation_policy"]["generic_gate"]
            == "critique.semantic_preservation"
        )
        assert plan["design_review_todo_artifact"] == DESIGN_TODO_ARTIFACT
        assert (
            "semantic_preservation_contract"
            in plan["generative_design_guards"]["must_address_before_complete"]
        )
        assert (
            plan["semantic_preservation_policy"]["commentary_contract"][
                "required_header"
            ]
            == "Semantic preservation contract"
        )
        assert (
            "vacuous PhysicsContext True used as source-backed smoothness, boundary, frame, domain, nonzero, normalization, or regime evidence"
            in plan["lean_artifact_contract"]["forbidden_completion_patterns"]
        )
        assert (
            plan["maximal_mathlib_grounding_policy"]["minimum_complete_level"] == "high"
        )
        assert (
            plan["background_dependency_policy"]["packet"]
            == "physics_lean_background_dependency_plan"
        )
        assert (
            plan["background_dependency_policy"]["early_steering_input"]
            == "physics informal elicitation/expansion expected_formal_grounding roles"
        )
        assert len(plan["refinement_loops"]) >= 10
        print(json.dumps({"ok": True, "style": STYLE}, indent=2))
        return 0
    source, source_ref = read_source(args.source_file, args.source_text)
    plan = build_plan(source, source_ref, args.case_id)
    text = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
