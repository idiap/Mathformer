<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# FormalPhysics Comparison Metrics

## Measurement Unit

Score a candidate as a full artifact:

1. top-level generated Lean code,
2. imported MathformerPhysicsLib Foundations dependency slice,
3. invoked external dependency declaration excerpts, including file path, line
   span, declaration kind, declaration name, and invocation count,
4. reasoning logs and review packets when available,
5. qualitative role-review packets for theorem-prover and physics lenses.

For a external single-file snippet, record the absent dependency surface as
evidence rather than pretending both systems expose the same library context.

## Hard Gates

- `lean_compiles`: the submitted Lean artifact compiles with the local toolchain.
- `no_unsound_placeholders`: no `sorry`, `admit`, fake proof terminators, or
  unreviewed `axiom` declarations in final claims.
- `non_vacuous_target`: the theorem is not merely `True`, identity-only, or a
  restatement that drops the physics conclusion.
- `reference_policy_respected`: reference answer is non-gold evidence.

## Scored Metrics

Use a 0-5 scale with evidence snippets and confidence.

- `source_semantic_preservation`: preserves quantities, objects, hypotheses,
  quantifier scope, conclusion, and derivation intent from the problem text.
- `physics_object_fidelity`: models the right physical objects, for example
  fields, frames, units, dimensions, operators, domains, or boundary terms.
- `foundations_dependency_quality`: uses or extends canonical
  `libraries/MathformerPhysicsLib/Lean/Foundations` surfaces without duplicating,
  bypassing, or weakening them.
- `mathlib_grounding`: reuses Mathlib and MathformerPhysicsLib APIs instead of
  avoidable local replacements.
- `mathlib_concept_grounding`: grounds physics concepts in recognizable Mathlib
  structures such as modules, linear maps, inner-product spaces, derivatives,
  real/complex scalars, topology/normed-space surfaces, and algebraic laws.
  Useful indicators: number of Mathlib concept families hit, number and kind of
  invoked Foundation declarations, and whether the candidate uses them directly
  rather than relying on an opaque import.
- `variable_naming_quality`: uses declaration and variable names that expose
  source concepts instead of generic algebra placeholders.
- `formal_physics_modeling_depth`: represents physics concepts through typed
  structures, witnesses, contexts, units, operators, and reusable frontiers
  rather than a bare algebraic equality.
  Useful indicators: typed modeling declaration count, invoked external
  declaration excerpt count, physics-complexity family coverage, and absence of
  single-claim algebraic-shell risk.
- `physics_representation_completeness`: captures the complexity of the
  underlying physics, including assumptions, regimes, units, dimensions,
  operators, domains, boundary conditions, and source derivation steps.
  Useful indicators: source-overlap ratio, missing source terms,
  physics-complexity families, explicit unit/dimension surfaces, explicit
  context/assumption surfaces, and source-step coverage.
- `assumption_transparency`: labels regimes, regularity, boundary conditions,
  differentiability, domain restrictions, and source-to-formal deltas.
- `proof_integrity`: proof terms or tactics justify the theorem shape rather
  than proving an unrelated algebraic shell.
- `derivation_coverage`: major informal derivation steps have formal objects,
  lemmas, or comments with source anchors.
- `reference_delta_quality`: explains agreement and disagreement with the
  reference answer without treating the reference as an oracle.
- `reviewability_clarity`: provides concise annotations, source-step mapping,
  named bridge lemmas, and evidence surfaces that make the formalization easy
  to review.
  Useful indicators: module docs, doc comments, source-step annotations,
  bridge/support/witness/grounding names, and imported dependency excerpts.
- `maintainability`: declarations are named, modular, reusable, and stable
  under library evolution.
- `reportability`: evidence is machine-processable and human-readable.

## Critic Profiles

Each score must be accompanied by enough evidence for a human or consumer
application to inspect the decision.

- `mathlib_grounding_critic`: checks concrete Mathlib concept families,
  import discipline, canonical Foundation reuse, and avoidable local
  replacements.
- `naming_reviewability_critic`: checks declaration names, source/domain token
  coverage, generic-name risk, comments, and source-step annotations.
- `formality_depth_critic`: checks typed frontiers, contexts, witnesses,
  bridge lemmas, and whether a candidate is more than an algebraic shell.
- `physics_completeness_critic`: checks physical quantities, laws, operators,
  fields, states, frames, units, dimensions, domains, boundary assumptions,
  and whether source complexity was simplified away.

## Best-Solution Rule

A best solution is the highest-ranked artifact after hard gates. If no artifact
passes hard gates, select `no_accepted_solution` and show the least risky repair
path. A non-compiling solution can still be informative, but cannot be the best
functional Lean formalization.

## Foundations Rule

For Mathformer candidates, compare all files under:

- `libraries/MathformerPhysicsLib/Lean/Foundations.lean`
- `libraries/MathformerPhysicsLib/Lean/Foundations/*.lean`

Report declaration counts, imports, concept ownership, local redefinitions,
and the specific Foundation concepts used or duplicated by each candidate.
