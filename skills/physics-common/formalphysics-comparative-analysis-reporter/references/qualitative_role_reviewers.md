<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Qualitative Role Reviewers

## Purpose

Role reviewers turn deterministic comparison packets into concise,
human-readable, machine-processable reports. They do not replace Lean
compilation, source-grounding checks, or Codex-exec generative judges. They
summarize the strategy evidence already present in the report.

## Theorem Prover Expert

Primary question: is this a plausible functional Lean formalization artifact?

Criteria:

- Lean compile status and import discipline.
- Absence of `sorry`, `admit`, and unreviewed `axiom` placeholders.
- Non-vacuous theorem or lemma target.
- Proof-integrity evidence from target shape, tactics, and term structure.
- Mathlib concept grounding, including concrete Mathlib APIs for scalars,
  modules, linear maps, inner-product spaces, derivatives, and algebraic laws.
- Variable and declaration names expose source-domain concepts.
- Formal modeling depth goes beyond a pure algebraic shell.
- Maintainability of declarations, names, and dependency choices.

Preferred evidence:

- `hard_gates.lean_compiles`
- `hard_gates.no_unsound_placeholders`
- `hard_gates.non_vacuous_target`
- `scores.proof_integrity`
- `scores.mathlib_grounding`
- `scores.mathlib_concept_grounding`
- `scores.variable_naming_quality`
- `scores.formal_physics_modeling_depth`
- `scores.reviewability_clarity`
- `scores.foundations_dependency_quality`
- `scores.maintainability`

## Physics Expert

Primary question: does the formalization preserve the physical content of the
source problem?

Criteria:

- Source quantities, regimes, and conclusions are preserved.
- Physical objects such as fields, frames, units, dimensions, operators, and
  boundary terms are represented rather than erased.
- The representation is complete enough for the underlying physics complexity:
  laws, operators, states, regimes, domains, units, dimensions, and boundary
  assumptions are not flattened away.
- Assumptions, domains, regularity, and boundary conditions are explicit.
- Essential derivation steps are covered by formal objects, lemmas, or source
  anchors.
- Reviewability aids such as source-step annotations and named bridge lemmas are
  present.
- Reference-answer deltas are explained under the non-gold reference policy.
- Reusable physics Foundations are used or exposed when they make the claim
  more meaningful.

Preferred evidence:

- `source_reference_delta.source_overlap`
- `source_reference_delta.classification`
- `scores.source_semantic_preservation`
- `scores.physics_object_fidelity`
- `scores.physics_representation_completeness`
- `scores.formal_physics_modeling_depth`
- `scores.assumption_transparency`
- `scores.derivation_coverage`
- `scores.reviewability_clarity`
- `scores.reference_delta_quality`
- `scores.foundations_dependency_quality`

## Strategy Synthesis

The summary report compares the two role preferences case by case. Agreement
increases confidence that a strategy is both theorem-proving friendly and
physics-faithful. Disagreement is not averaged away; it marks a useful repair
target where Lean functionality and physical semantics need separate attention.

The synthesis must report:

- role rubrics and primary metrics;
- per-case role preferences;
- agreement and disagreement counts;
- essential strategy tags for each candidate;
- provisional status when compile checks were not run;
- reference-answer policy as non-gold evidence.
