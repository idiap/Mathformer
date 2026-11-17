<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make the framework understandable without requiring readers to inspect implementation details first.

Intent:
  Explain architecture, installation, principles, tutorials, licensing, and generated library outputs.

Function:
  Provides human-facing documentation that should stay aligned with tested behavior and code paths.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Mathformer Lean Physics Pipeline

The Lean physics pipeline is the controlled Lean counterpart to
`sympy_physics_derivation_trace`. It reuses the existing physics
preformalization spine and adds Lean-specific type, unit, execution, and
reflection gates.

Style: `lean_physics_derivation_trace`

Named loop: `lean_physics_derivation_trace_loop`

## Goal

Formalize physics derivations in Lean without collapsing the physics into
empty scalar algebra. A complete artifact must represent the actual physical
content behind the equations: quantities, dimensions, units, frames, regimes,
laws, contextual assumptions, and derivation steps.

## Workflow

1. Source extraction: preserve literal question/answer text, source anchors,
   target equation, support equations, and uncertainty notes.
2. Informal elicitation: surface missing target shape, quantities, units,
   dimensions, frames, regimes, side assumptions, laws, and unclear transitions
   before formalization.
3. Informal expansion: expand terse derivation steps into source-anchored
   literal steps and labeled generated-support transitions.
4. Informal readiness review: block backend drafting when expanded steps lack
   anchors, law/rule provenance, unit/dimension status, or needed web-support
   packets.
5. Quantity binding: build source-backed symbol tables and distinguish
   quantities, generated support symbols, vectors, fields, operators, and
   parameters.
6. Dimension and unit modeling: assign base dimensions and unit notes, or mark
   unresolved dimensions as blockers.
7. Equation, regime, and frame modeling: parse equations, identify coordinate
   frames, sign conventions, smoothness, positivity, nonzero side conditions,
   boundary conditions, idealizations, and approximation regimes.
8. Physical law grounding: map each transformation to a source-backed law,
   generated support lemma, mathlib concept, or explicit blocker.
9. Lean workflow planning: produce a `physics_lean_workflow_plan` with gates,
   protected metrics, and refinement loops.
10. Lean physics typing: produce a `physics_lean_type_system_packet` for
   dimensions, quantities, vector quantities, fields, operators, contexts, and
   source laws.
11. Assumption encoding: produce a `physics_lean_assumption_packet` that labels
   assumptions as source-backed, mathlib-backed, generated-support, or blocked.
12. Mathlib grounding and import verification: reuse generic mathlib discovery,
   coverage, import planning, and import-context verification.
13. Lean drafting: generate a source-anchored Lean artifact with typed
   quantities or explicit projection lemmas, contextual assumptions, physical
   law lemmas, and unit obligations.
14. Lean execution: run the standard Lean execution/compile checks immediately.
15. Physics Lean interpretation: classify diagnostics as mathlib/import,
   physics typing, unit/dimension, assumption-context, proof-gap, syntax, or
   empty-formalism risk.
16. Unit analysis: verify that dimension and unit obligations are represented
   in Lean and that raw scalar erasure is not hiding physical content.
17. Refinement loops: repair imports, types, unit obligations, assumptions,
   proof gaps, semantic drift, and mathlib grounding in that order.
18. Final hypothesis review: run physics and mathematical reviewers over the
   final formalized hypotheses and route failures to localized monotonic review
   refinement.
19. Acceptance: run source-anchor, realness, reverse informalization,
   declaration-shape, non-vacuity, mathlib, final review, RFDE, and physics Lean
   consistency gates.
20. Optional post-hoc dataset reflection: when a FormalPhysics `formal_answer`
    exists, compare it only after the informal-first candidate, draft blockers,
    or final consistency report exist. Treat it as inspiration, not as a
    benchmark label or ground truth.

## Parity With Mathematical Autoformalization

The Lean physics loop is an extension of the mathematical Lean
autoformalization pipeline, not a replacement for it. It inherits the shared
mathematical gates:

- source line translation and source-anchor preservation;
- proof-expansion support, difficulty estimation, web research for hard
  derivation gaps, prerequisite expansion, and expansion review;
- result-existence precheck before first-pass drafting;
- mathlib result search, concept discovery, hierarchy navigation, candidate
  verification, web grounding, API planning, import planning, import-context
  verification, and import minimization;
- Lean execution, compile checks, denoising, line-comment hygiene, and
  refinement taxonomy;
- generic Lean critics for syntax, semantic preservation, logical soundness,
  mathlib alignment, suite orchestration, and reference-free monitoring;
- formal and semantic refinement loops;
- reverse informalization, declaration-shape review, informal internal
  consistency, informal consistency, non-vacuity, cross-file concept indexing,
  unified consistency reporting, artifact statistics, and RFDE reporting.

Physics-specific machinery is additive. The physical-semantics, assumption,
dimension, generative, and final hypothesis reviewers strengthen the generic
semantic-preservation contract by asking whether the formal statement still
means the same physics, not merely whether it compiles as Lean mathematics.
Failures from the generic mathematical gates and the physics gates route to the
same controlled refinement discipline: local edits, preserved passing evidence,
and reruns of every affected gate.

## Informal Elicitation And Expansion

Before Lean or SymPy drafting, the pipeline runs a physics-specific informal
stage:

- `physics-informal-derivation-elicitor` asks for or records missing target
  shape, quantities, units, dimensions, frames, regimes, assumptions, laws, and
  unclear transitions.
- `physics-informal-derivation-expander` expands terse source derivations into
  source-anchored steps and labels every added bridge as generated support.
- `physics-informal-derivation-readiness-reviewer` blocks formalization when
  expanded steps lack anchors, law/rule provenance, assumption labels,
  dimension/unit status, or required web-support evidence.

This stage is deliberately informal, but it is not free-form. It must preserve
literal source content, expose uncertainty, and route hard derivation gaps to
the reused proof-expansion web-support skills before those gaps become Lean
theorem statements or SymPy traces.

## Lean Typing Policy

The initial type policy is intentionally small:

- `PhysDim`: a dimension vector over base exponents.
- `Quantity dim`: scalar value with a physical dimension.
- `VectorQuantity dim n`: coordinate vector with a physical dimension.
- `PhysicsContext`: assumptions, laws, frame, regime, and source notes.
- `SourceLaw`: law name, source anchors, generated-support status.

This interface is a scaffold for preserving physical constraints, not an
ontology for all physics. It should be replaced by mathlib-native or
MathformerLib-native objects whenever better structures exist.

Raw `ℝ` values are allowed for:

- dimensionless algebra;
- coordinate projections of typed quantities;
- local algebraic substeps where a projection lemma relates the scalar step
  back to typed physical quantities.

Raw `ℝ` values are not enough for complete status when the source claim is about
dimensioned physical quantities.

## Contextual Assumptions

The assumption encoder must surface:

- positivity and nonzero side conditions;
- differentiability, smoothness, integrability, and domain assumptions;
- coordinate frame and sign conventions;
- boundary and initial conditions;
- constant-quantity assumptions;
- gauge choices and idealizations;
- quantum operator assumptions such as self-adjointness, normalization, and
  commutator laws.

Assumptions that are not directly in the source may be used only as
generated-support assumptions and must be visible in the artifact comments and
reports. Silent strengthening blocks complete status.

## Explicit Critic Stack

The Lean physics path adds physics-specific critics after execution and unit
analysis:

- Physical semantics critic: checks whether the Lean artifact preserves
  quantities, vector/field structure, frames, regimes, physical laws, and
  source-backed derivation meaning.
- Assumption critic: checks hidden strengthening, missing side conditions,
  unlabeled generated assumptions, and frame/regime/gauge drift.
- Dimension critic: stress-tests unit and dimension discipline, raw-scalar
  erasure, and vector/scalar projection bridges.
- Generative critic orchestrator: runs the deterministic critics and can launch
  Codex-exec adversarial probes for near-final or high-risk artifacts.

The generative critics should not be treated as authorities. They generate
candidate objections: possible counter-interpretations, missing assumptions,
unit substitutions, alternate frame conventions, or smaller vacuous Lean
statements. A generative objection blocks complete status only when it is backed
by source anchors, Lean diagnostics, unit reports, deterministic critic reports,
or repeated independent Codex-exec probes with the same blocker class.

Useful generative probes include:

- Can the Lean theorem be true while the source physics is false because the
  artifact erased quantities, vectors, frames, or laws?
- Which Lean side condition lacks a source sentence or generated-support label?
- What unit-system substitution or base-dimension scaling should the theorem
  resist?
- Is there a smaller target-as-assumption, axiom, or raw-scalar theorem hiding
  under the artifact?

## Final Reviewer Stack

The final reviewer stack is stricter than the critic stack. It validates the
final formalized derivation hypotheses before acceptance:

- Physics final hypothesis reviewer: checks physical quantities, dimensions,
  units, frames, regimes, contextual assumptions, law grounding, projection
  bridges, and target non-vacuity.
- Mathematical final hypothesis reviewer: checks binder domains, quantifier
  shape, side conditions, conclusion shape, support dependencies, proof
  realness, and non-vacuity.
- Final derivation review orchestrator: combines both reports and blocks
  complete status unless failures are routed to a localized refinement plan.
- Review refinement router: converts review findings into repair surfaces and
  monotonic non-regression checks.

Common final-review errors include:

- dropped universal, existential, uniqueness, or equivalence structure;
- hidden positivity, nonzero, smoothness, or differentiability assumptions;
- wrong implication direction or weakened conclusion;
- frame, sign, gauge, or approximation context missing from hypotheses;
- physical law encoded as a target-shaped axiom;
- scalar projection not connected back to the typed physical claim;
- contradictory or target-shaped hypotheses making the theorem vacuous;
- proof repair that changes the theorem instead of proving it.

Review-driven refinement must be localized. It may edit only the declaration,
support lemma, assumption label, law grounding, projection bridge, or proof
fragment identified by a review finding. It must preserve already-passing source
anchors, theorem names, unit coverage, assumption labels, mathlib grounding,
proof realness, non-vacuity, and Lean execution evidence unless a source-backed
theorem-shape correction forces a broader rerun.

## Refinement Loops

The Lean physics workflow has twelve required controlled loops plus one
optional post-hoc dataset-reflection loop:

- Informal elicitation/expansion loop: repair missing source context,
  generated-support labels, source anchors, law/rule provenance, and unit or
  dimension notes before backend drafting.
- Lean diagnostic loop: repair parser, elaborator, type, import, and proof
  diagnostics.
- Generic Lean critique loop: repair syntax, logical soundness, mathlib
  alignment, and critique-suite failures.
- Mathematical semantic-preservation loop: repair source-to-Lean drift in
  statement shape, binders, quantifiers, conclusions, anchors, and comments.
- Unit/dimension loop: repair typed quantities, projections, and dimension
  lemmas.
- Critic loop: run deterministic physics critics and, when needed, Codex-exec
  generative critics before changing theorem statements.
- Assumption-context loop: repair missing or over-strong assumptions.
- Semantic reverse loop: repair source drift found by reverse informalization.
- Mathlib grounding loop: replace private abstractions with verified mathlib
  surfaces where possible.
- Reference-free monotonicity loop: prevent accepted refinements from shrinking
  protected theorem, source-anchor, realness, or non-vacuity evidence.
- Final review refinement loop: repair failed physics or mathematical final
  hypothesis reviews with localized monotonic edits.
- Process reflection loop: update prompts, skills, or tests only after repeated
  blockers or costly plateaus.
- Optional dataset formal-answer reflection loop: after an informal-first
  FormalPhysics run has a candidate or explicit blockers, compile and inspect
  the withheld `formal_answer` for theorem-shape, proof-tactic, import, and
  abstraction inspiration. Do not use it as a gold label, and route any accepted
  change through localized review refinement.

## Complete Status

Complete status requires:

- Lean compiles under intended imports;
- no `sorry`, `admit`, target axioms, target-as-hypothesis, or scaffold-only
  completion;
- source anchors are valid and sufficiently covered;
- informal derivation elicitation, expansion, and readiness review pass before
  backend drafting;
- unit and dimension analysis passes or records explicit blockers;
- physical semantics, assumption, dimension, and generative critic findings are
  either passing, justified warnings, or explicit blockers;
- final physics and mathematical hypothesis reviewers pass;
- failed final reviews have localized monotonic refinement plans and are not
  silently waived;
- contextual assumptions are labeled and justified;
- mathlib grounding or explicit gaps are recorded;
- reverse informalization agrees with the source physics;
- declaration-shape and non-vacuity gates pass;
- RFDE reports the run trajectory and protected-regression status.

## FormalPhysics Post-Hoc Comparison

`physics-formal-answer-comparison-reflector` compares Mathformer artifacts with
withheld FormalPhysics `formal_answer` code only after first-pass drafting or
blocking evidence exists. The report is explicitly
`inspiration_only_not_benchmark`: a dataset formalization may compile and still
be physically weaker than a Mathformer artifact that preserves dimensions,
units, frames, assumptions, and source anchors.

The comparison checks:

- whether the withheld Lean code compiles locally;
- theorem names, imports, proof tactics, and abstraction choices;
- raw-scalar erasure versus quantity/unit/dimension surfaces;
- source-anchor strength;
- reusable ideas such as algebraic lemma decomposition or linear-operator
  surfaces;
- localized refinements that must return through `refine.physics_lean_review`.

## Skills

Lean-specific physics skills:

- `physics-lean-workflow-orchestrator`
- `physics-informal-derivation-elicitor`
- `physics-informal-derivation-expander`
- `physics-informal-derivation-readiness-reviewer`
- `physics-lean-type-system-builder`
- `physics-lean-assumption-context-encoder`
- `physics-lean-derivation-drafter`
- `physics-lean-execution-interpreter`
- `physics-lean-unit-analysis-verifier`
- `physics-lean-physical-semantics-critic`
- `physics-lean-assumption-critic`
- `physics-lean-dimension-critic`
- `physics-lean-generative-critic-orchestrator`
- `physics-final-hypothesis-reviewer`
- `mathematical-final-hypothesis-reviewer`
- `final-derivation-review-orchestrator`
- `physics-lean-review-refinement-router`
- `physics-lean-refinement-loop`
- `physics-lean-consistency-report-orchestrator`
- `physics-formal-answer-comparison-reflector`

These skills reuse the existing physics, mathlib, Lean execution, Lean
consistency, realness, Codex-exec content testing, and RFDE skills.
