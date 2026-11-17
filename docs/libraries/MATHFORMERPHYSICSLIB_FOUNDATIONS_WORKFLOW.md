<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Plan a reusable foundations workflow for MathformerPhysicsLib that formalizes
  physics concepts before individual benchmark cases need them.

Intent:
  Define a controlled, Mathlib-first pipeline from physics concepts and
  mathematical objects to promoted Lean foundations modules.

Function:
  Serves as the implementation plan for skills, scripts, artifacts, and gates
  that accumulate reusable MathformerPhysicsLib foundations.

Maintenance Notes:
  Keep this workflow synchronized with MathformerPhysicsLib registry,
  promotion, pathology repair, and recursive repair-control semantics.
-->

# MathformerPhysicsLib Foundations Workflow

Companion workflow: [MathformerPhysicsLib coherence and grounding workflow](MATHFORMERPHYSICSLIB_COHERENCE_GROUNDING_WORKFLOW.md).

## Goal

Build a controlled workflow that receives fundamental physics concepts and
mathematical objects, searches for existing Mathlib representations first,
autoformalizes only the missing reusable support, and promotes accepted Lean
modules into `libraries/MathformerPhysicsLib/Lean/Foundations`.

This workflow is concept-first, not benchmark-first. Benchmark cases should
consume foundations modules rather than repeatedly generating local wrappers for
vector fields, operators, laws, units, frames, assumptions, and calculus
operators.

## Core Principle

Every physics foundation object must be classified into one of these states:

- `mathlib_reused`: represented directly by verified Mathlib declarations.
- `mathformer_reused`: already accepted in MathformerPhysicsLib.
- `candidate_generated`: a generated module compiles but is not promoted.
- `blocked`: no faithful formalization exists yet, with an explicit reason.
- `out_of_scope`: the concept is too domain-specific for foundations.

Candidate text must never count as accepted support until registry, promotion,
compile, realness, and physics-review gates pass.

The workflow therefore optimizes for **Mathlib-native public interfaces** and
only introduces MathformerPhysicsLib declarations when they are true reusable
bridges. A foundation declaration is good when downstream physics artifacts can
import it without relearning the same carrier, operator, law, unit, or context
shape.

## Workflow Contract

Given a list of fundamental physics concepts or mathematical objects, the
workflow must return a controlled `physics_foundation_run_report` with:

- normalized object packets;
- verified Mathlib candidates, failed candidates, and explicit gaps;
- a surface-design decision for every object;
- generated Lean only for objects that cannot be represented by Mathlib alone;
- compile, realness, non-vacuity, import, semantic, dimension, and pathology
  gate results;
- a registry/promotion decision;
- downstream reuse instructions for future autoformalization or repair loops.

The run is successful only if every input object reaches exactly one terminal
state: `mathlib_reused`, `mathformer_reused`, `candidate_generated`,
`blocked`, or `out_of_scope`.

## Input Artifact

The workflow starts from a `physics_foundation_object_packet`:

```json
{
  "style": "physics_foundation_object_packet",
  "packet_id": "em_vector_calculus_v1",
  "source": "manual | benchmark_cluster | detected_pathology | generated",
  "objects": [
    {
      "object_id": "vector_field.real.euclidean3",
      "object_class": "vector_field",
      "display_name": "Real vector field on Euclidean 3-space",
      "physics_roles": ["electric field", "magnetic field", "velocity field"],
      "required_semantics": ["carrier", "pointwise operations", "projection"],
      "mathlib_search_terms": ["EuclideanSpace", "Pi", "Module", "ContinuousMap"],
      "candidate_imports": [],
      "source_examples": ["formalphysics_0000", "formalphysics_0020"],
      "priority": "high"
    }
  ]
}
```

## Foundations Taxonomy

Start with these object families:

- **Carriers**: scalar fields, Euclidean vectors, fields over domains,
  configuration spaces, Hilbert spaces, state spaces.
- **Maps and Operators**: linear maps, continuous linear maps, differential
  operators, time-derivative operators, curl/divergence/gradient projections,
  Hamiltonians, observables.
- **Algebraic Operations**: commutators, adjoints, inner products, norms,
  projections, pointwise field operations.
- **Calculus Surfaces**: derivatives, partial derivatives, Fréchet derivatives,
  integrals, limits, smoothness assumptions, boundary terms.
- **Physics Laws**: source-backed law records, constitutive equations,
  conservation laws, Maxwell/Lorentz/Schrodinger-style law witnesses.
- **Units and Dimensions**: dimension tags, homogeneity propositions, unit
  bridges, dimensional compatibility checks.
- **Frames and Regimes**: coordinate frames, basis choices, inertial-frame
  assumptions, gauge/regime/boundary context.
- **Support Assumptions**: nonzero, positivity, smoothness, integrability,
  boundary, domain, and generated-support labels.

## Mathlib Grounding Matrix

Each object family starts from the most Mathlib-native surface available:

| Physics object family | First Mathlib target | Allowed MathformerPhysicsLib bridge |
| --- | --- | --- |
| Scalars and parameters | `Real`, ordered fields, normed fields | only source-label records for physical role or dimension |
| Finite vectors | `EuclideanSpace Real (Fin n)` or `Fin n -> Real` | named projection lemmas and coordinate conventions |
| Fields | `X -> V`, `Pi`, modules, `ContinuousMap` when needed | source-backed field role records and domain assumptions |
| Linear operators | `LinearMap`, continuous linear maps, matrices | law-specific wrappers tying an operator to a physical source |
| Hilbert/quantum states | inner product spaces, modules, matrices, star algebra | quantum role/context records, not new inner-product APIs |
| Calculus | `HasDerivAt`, `HasFDerivAt`, `Differentiable`, `ContDiff`, integrals, limits | source-law bridge lemmas and narrowed regularity packages |
| Algebraic physics operations | multiplication, commutators via algebraic expressions, `Commute`, `star` | named theorem surfaces for physical interpretation |
| Units/dimensions | existing algebra plus explicit homogeneity propositions | conservative dimension tags and bridge lemmas marked as support |
| Frames and bases | `Basis`, coordinate functions, finite index projections | frame-context records with sign/convention provenance |
| Laws and regimes | propositions over Mathlib carriers | thin source-backed law/context structures |

If the first target exists but is awkward, the workflow must still start there.
Local wrappers are accepted only when they preserve a verified Mathlib object and
make a physics-specific role, law, regime, or provenance obligation explicit.

## Mathlib-First Decision Procedure

For each object:

1. **Name the semantics**: carrier, operations, equations, assumptions,
   source role, downstream examples, and forbidden collapses.
2. **Search Mathlib and MathformerPhysicsLib**: use ontology hints, module-tree
   navigation, declaration neighborhoods, candidate verification, and existing
   library search.
3. **Classify representation**:
   - direct Mathlib object: mark `mathlib_reused`;
   - accepted local support: mark `mathformer_reused`;
   - Mathlib object plus missing physics bridge: plan a minimal bridge;
   - no faithful representation: mark `blocked` with the missing concept.
4. **Design a public Lean surface**: choose imports, declarations, comments,
   examples, and abstraction boundaries.
5. **Draft only the gap**: generated Lean must be smaller than the physics
   target theorem and must not encode a target conclusion as an assumption.
6. **Verify and minimize**: compile, remove broad imports when possible,
   check realness and non-vacuity, and record Mathlib grounding level.
7. **Promote or block**: update the registry and downstream object workbench
   only after gates pass.

This procedure is deterministic at the control layer even when drafting or
repair is generative.

## Workflow Stages

### 1. Concept Intake

Skills:

- `physics-math-object-detector`
- new `physics-foundation-object-intake`

Responsibilities:

- Normalize user concepts, benchmark-derived objects, and pathology-detected
  objects into `physics_foundation_object_packet`.
- Merge duplicate objects by semantic role, not by surface string.
- Attach examples from FormalPhysics cases when available.
- Assign priority from recurrence, pathology severity, and downstream blockers.
- Preserve user-level names while adding canonical `object_id` values.
- Split overloaded objects into separate carrier/operator/law/context items.

Outputs:

- `physics_foundation_object_packet`
- `physics_foundation_object_inventory`
- `artifacts/mathformerphysicslib/foundations/intake/<run_id>.json`

### 2. Mathlib Grounding Search

Skills:

- `mathlib-concept-candidate-mapper`
- `mathlib-concept-ontology-manager`
- `mathlib-hierarchy-navigator`
- `mathlib-declaration-neighborhood-navigator`
- `mathlib-candidate-verifier`
- `mathlib-import-set-builder`
- `mathlib-grounding-maximizer`

Responsibilities:

- Search Mathlib declarations and modules for each object.
- Verify candidates with local Lean checks, not name similarity alone.
- Prefer direct Mathlib surfaces such as:
  - `EuclideanSpace Real (Fin n)` for finite vectors;
  - `X -> V`, `Pi`, and module instances for fields;
  - `LinearMap` / continuous linear maps for operators;
  - `InnerProductSpace` for Hilbert-style state spaces;
  - `HasDerivAt`, `HasFDerivAt`, `Differentiable`, `ContDiff` for calculus;
  - `Matrix`, `star`, and algebraic structures for adjoints/commutators.
- Emit explicit blockers when Mathlib lacks a faithful primitive.
- Keep failed candidates in the report so future runs avoid repeating them.

Outputs:

- `physics_foundation_mathlib_grounding_packet`
- `mathlib_candidate_verification_report`
- `physics_foundation_import_plan`

### 3. Foundation Surface Design

Skill: `mathformerphysicslib-foundation-surface-designer`

Responsibilities:

- Decide whether the foundation should be:
  - a pure import/re-export and notation note;
  - a small bridge theorem;
  - a source-law record structure;
  - a reusable assumption-labeling structure;
  - a deliberately blocked abstraction boundary.
- Keep wrappers thin. A wrapper must explain what Mathlib object it preserves
  and why a direct Mathlib surface is insufficient.
- Create stable module paths:
  - `libraries/MathformerPhysicsLib/Lean/Foundations.lean`
  - `libraries/MathformerPhysicsLib/Lean/Foundations/Carriers.lean`
  - `libraries/MathformerPhysicsLib/Lean/Foundations/Fields.lean`
  - `libraries/MathformerPhysicsLib/Lean/Foundations/Operators.lean`
  - `libraries/MathformerPhysicsLib/Lean/Foundations/VectorCalculus.lean`
  - `libraries/MathformerPhysicsLib/Lean/Foundations/Units.lean`
  - `libraries/MathformerPhysicsLib/Lean/Foundations/Laws.lean`
  - `libraries/MathformerPhysicsLib/Lean/Foundations/Contexts.lean`

Outputs:

- `physics_foundation_surface_plan`
- candidate module skeletons
- `physics_foundation_abstraction_boundaries`

### 4. Lean Candidate Generation

Skill: `mathformerphysicslib-foundation-drafter`

Responsibilities:

- Generate Lean modules from the surface plan.
- Use narrow imports when known; allow `import Mathlib` only in draft.
- Include declaration-level comments with:
  - physics role;
  - Mathlib grounding;
  - accepted abstraction boundary;
  - example downstream cases.
- Avoid `abbrev Foo : Prop := True` except in blocked draft modules.
- Avoid generated axioms and final-claim-shaped assumptions.
- Prefer propositions that expose obligations over propositions that hide
  physics semantics.

Outputs:

- `libraries/MathformerPhysicsLib/Lean/Foundations/*.lean`
- `physics_foundation_generation_report`

### 5. Local Verification

Skills:

- `lean-execution-runner`
- `lean-compile-checker`
- `autoformalization-result-realness-verifier`
- `lean-declaration-shape-consistency-checker`
- `lean-nonvacuity-consistency-checker`
- `mathlib-import-minimizer`
- `lean-mathlib-alignment-critic`
- `mathlib-abstraction-auditor`

Responsibilities:

- Compile every generated foundation module.
- Reject placeholders, vacuous support, target-shaped hypotheses, and local
  wrappers that duplicate Mathlib.
- Minimize imports after compile success.
- Measure Mathlib grounding level and record residual local scaffolds.
- Enforce monotonic grounding: a repair may not reduce verified Mathlib reuse
  unless the report explains why the old mapping was semantically wrong.

Outputs:

- `physics_foundation_verification_report`
- minimized modules or explicit blockers

### 6. Physics Semantic Review

Skills:

- `physics-lean-physical-semantics-critic`
- `physics-lean-assumption-critic`
- `physics-lean-dimension-critic`
- `physics-lean-drift-pathology-monitor`
- `physics-final-hypothesis-reviewer`
- `physics-lean-generative-critic-orchestrator`

Responsibilities:

- Check that each foundation object preserves physics semantics rather than
  erasing them into raw scalar algebra.
- Confirm every assumption label is source-backed, Mathlib-backed,
  generated-support, or blocked.
- Run the pathology monitor against candidate support to catch notational
  collapse and abstraction elevation before promotion.
- Use generative critique to look for missing regimes, hidden units, erased
  vector/operator structure, and over-broad law assumptions.

Outputs:

- `physics_foundation_semantic_review_report`
- `physics_foundation_generative_review_report`

### 7. Registry And Promotion

Skills:

- `mathformerlib-registry-manager`
- `mathformerlib-promotion-gate`
- `mathformerphysicslib-object-workbench`

Responsibilities:

- Register foundation candidates with status `candidate_generated`.
- Promote only modules that pass compile, realness, placeholder, registry, and
  semantic gates.
- Update object-workbench resolution so future pathology loops can return
  `mathformer_reused` for promoted foundations.

Outputs:

- `artifacts/mathformerphysicslib/foundations_registry.json`
- `physics_foundation_promotion_report`
- promoted modules under `libraries/MathformerPhysicsLib/Lean/Foundations`

### 8. Downstream Regression

Skills:

- `physics-math-object-detector`
- `mathformerphysicslib-object-workbench`
- `physics-lean-pathology-repair-orchestrator`
- `physics-lean-repair-expansion-cartographer`
- `physics-lean-recursive-repair-loop-controller`
- `physics-lean-consistency-report-orchestrator`

Responsibilities:

- Rerun blocked physics cases against the newly promoted foundations.
- Require the object workbench to switch from `reuse_candidate` to
  `mathformer_reused` before target theorem repair is allowed.
- Track whether recursive repair frontiers shrink monotonically.

Outputs:

- `physics_foundation_downstream_regression_report`
- per-case before/after pathology deltas

## Acceptance Gates

A foundation module is accepted only if:

- it compiles under Lean;
- it has no `sorry`, `admit`, generated axioms, placeholder markers, or
  scaffold-only `Prop := True` surfaces counted as final support;
- every nontrivial declaration names its Mathlib grounding or explicit
  abstraction boundary;
- the Mathlib grounding score is nondecreasing across refinement;
- import minimization succeeds or the broad import is justified;
- physics critics do not flag semantic erasure;
- pathology monitor reports no critical notational collapse or abstraction
  elevation;
- promotion gate returns accepted;
- registry status is updated;
- at least one downstream case can reuse or explicitly block the foundation.

## Recursive And Exhaustive Expansion Loop

The foundations workflow is embedded in the existing repair loop:

1. A target physics autoformalization runs semantic/pathology checks.
2. Detected pathologies produce concrete physics mathematical objects.
3. Every object is routed to the MathformerPhysicsLib foundations workflow
   before target-theorem repair.
4. The object workbench may return `mathlib_reused`, `mathformer_reused`,
   `candidate_required`, or `blocked`.
5. If `candidate_required`, the foundation loop runs through grounding,
   surface design, drafting, verification, semantic review, and promotion.
6. If promotion succeeds, the target repair loop restarts with the new import.
7. If promotion fails, the object remains an explicit blocker and the target
   theorem may not hide the missing object as a hypothesis.
8. The loop terminates only when all objects are reused, promoted, blocked, or
   out of scope, and the repair frontier stops growing.

Exhaustiveness is measured by object coverage, not by whether one theorem
compiles. A compile success with unresolved object blockers is still incomplete.

## Artifact Layout

Planned durable artifacts:

```text
libraries/MathformerPhysicsLib/Lean/Foundations.lean
libraries/MathformerPhysicsLib/Lean/Foundations/Carriers.lean
libraries/MathformerPhysicsLib/Lean/Foundations/Fields.lean
libraries/MathformerPhysicsLib/Lean/Foundations/Operators.lean
libraries/MathformerPhysicsLib/Lean/Foundations/VectorCalculus.lean
libraries/MathformerPhysicsLib/Lean/Foundations/Units.lean
libraries/MathformerPhysicsLib/Lean/Foundations/Laws.lean
libraries/MathformerPhysicsLib/Lean/Foundations/Contexts.lean
artifacts/mathformerphysicslib/foundations/intake/
artifacts/mathformerphysicslib/foundations/grounding/
artifacts/mathformerphysicslib/foundations/surface_plans/
artifacts/mathformerphysicslib/foundations/verification/
artifacts/mathformerphysicslib/foundations/reviews/
artifacts/mathformerphysicslib/foundations/promotion/
artifacts/mathformerphysicslib/foundations/downstream/
```

The `Foundations.lean` index should re-export only accepted modules. Drafts and
blocked sketches belong under artifacts or `ObjectWorkbench`, never under the
accepted index.

## Initial Foundation Backlog

Priority 1:

- `vector_field.real.euclidean3`
- `projection.fin3.component`
- `linear_operator.field`
- `curl_like_linear_operator`
- `time_derivative_linear_operator`
- `physical_law.witness`
- `unit_dimension.compatible`
- `generated_support.assumption_label`

Priority 2:

- `hilbert_state.inner_product_space`
- `quantum_operator.linear_map`
- `commutator.algebra`
- `adjoint.operator`
- `smoothness.context`
- `boundary_condition.context`

Priority 3:

- `coordinate_frame.basis`
- `gauge_context`
- `regime_context`
- `integral_boundary_support`
- `conservation_law.schema`

## Implementation Status

1. [x] Add `physics-foundation-object-intake` skill and script that can ingest:
   user concept lists, detector packets, and benchmark clusters.
2. [x] Add `mathformerphysicslib-foundation-surface-designer` skill and script that
   emits module plans, imports, declarations, and abstraction-boundary records.
3. [x] Add `mathformerphysicslib-foundation-drafter` skill and script that generates
   Lean candidates from surface plans.
4. [x] Add `mathformerphysicslib-foundation-verifier` orchestration script that
   runs compile, import minimization, realness, non-vacuity, Mathlib alignment,
   abstraction, semantic, dimension, and pathology gates.
5. [x] Add `libraries/MathformerPhysicsLib/Lean/Foundations/` modules plus
   `libraries/MathformerPhysicsLib/Lean/Foundations.lean` as the accepted index.
6. [x] Extend `mathformerphysicslib-object-workbench` so promoted foundations can
   be classified as `mathformer_reused` and draft foundations remain
   `candidate_required`.
7. [x] Add foundation status fields to `libraries/MathformerPhysicsLib/MANIFEST.json` and
   `libraries/MathformerPhysicsLib/MATHLIB_GROUNDING_AUDIT.json`.
8. [x] Add a hub action:
   `physics-lean:foundation-formalization-loop`.
9. [x] Add hooks:
   - `foundation.physics_object_intake`
   - `foundation.mathlib_grounding`
   - `foundation.surface_design`
   - `foundation.lean_draft`
   - `foundation.verify`
   - `foundation.promote`
   - `foundation.downstream_regression`
10. [x] Add a controlled suite over the priority-1 backlog.
11. [x] Add JSON run reports under
    `artifacts/mathformerphysicslib/foundations/`.
12. [~] Rerun the recursive pipeline entrypoint over the priority-1 object
    frontier. The controlled suite now verifies object intake, surface design,
    draft preview, verifier gates, and object-workbench reuse; case-specific
    before/after frontier shrinkage remains the next stronger Lean execution
    validation for `formalphysics_0000`, `formalphysics_0020`, and
    `formalphysics_0054`.

## Example End-To-End Run

Input:

```json
{
  "concepts": [
    "real vector field on Euclidean 3-space",
    "component projection",
    "curl-like differential operator",
    "dimension-compatible equality",
    "source-backed physical law witness"
  ]
}
```

Expected route:

1. Intake splits the concepts into `vector_field.real.euclidean3`,
   `projection.fin3.component`, `curl_like_linear_operator`,
   `unit_dimension.compatible`, and `physical_law.witness`.
2. Grounding maps vectors to `EuclideanSpace Real (Fin 3)` or `Fin 3 -> Real`,
   projections to finite-index functions, and laws/units to thin local records.
3. Surface design plans accepted modules in `Carriers`, `Fields`,
   `VectorCalculus`, `Units`, and `Laws`.
4. Drafting generates only missing bridge lemmas and law/context records.
5. Verification rejects any `Prop := True` final support or broad `Mathlib`
   import that can be minimized.
6. Semantic review checks that vector calculus has not collapsed into raw scalar
   algebra and that units/laws are explicit.
7. Promotion updates the foundations registry.
8. Downstream repair imports `MathformerPhysicsLib.Lean.Foundations` and
   restarts with fewer object blockers.

## Expected Payoff

The next time a benchmark or paper formalization detects `vector_field`,
`physical_law`, `unit_bridge`, or `gradient_divergence_curl`, the repair loop
should not rediscover ad hoc candidate snippets. It should import accepted
foundation support from MathformerPhysicsLib, shrinking recursive repair
frontiers and moving target theorem repair from blocked to allowed.
