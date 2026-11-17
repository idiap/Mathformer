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

# Lean-Inspired Physics SymPy Enrichment Plan

This plan enriches `sympy_physics_derivation_trace_loop` using lessons from the
Lean physics autoformalization pipeline while preserving the intended SymPy
scope: executable equational derivations, not theorem proving. The goal is to
capture real physics at the equation-trace level: quantities, dimensions, units,
frames, regimes, laws, assumptions, and transformation semantics.

## Translation Principle

The Lean pipeline adds type, proof, and final-review controls. The SymPy pipeline
should reuse those controls as equational analogues:

| Lean physics control | SymPy equational analogue |
| --- | --- |
| `Quantity dim`, `VectorQuantity`, fields, operators | `QUANTITY_SURFACE` metadata over SymPy symbols, functions, matrices, vectors, indexed components, and operators |
| Lean hypotheses and theorem binders | SymPy symbol assumptions plus `CONTEXT_ASSUMPTIONS` and `SIDE_CONDITIONS` ledgers |
| Lean typed projection lemmas | `PROJECTION_BRIDGES` linking scalar equations to vector, field, coordinate, or component claims |
| Lean proof obligations | Executable transformation checks: `simplify(lhs - rhs) == 0`, solve/substitution residuals, matrix equality, derivative/integral checks, and numeric probes |
| Lean unit obligations | Dimension and unit validators over every equation and generated transformation |
| Lean physical-semantics critics | Equational semantics critics that detect target leakage, law loss, scalar erasure, and source drift |
| Lean final hypothesis reviewers | Final equation reviewers that validate the derived equation graph before complete status |
| Lean localized refinement | Monotonic local repair over symbol assumptions, equation parsing, unit bridges, law links, transformation steps, or numeric domains |

The SymPy backend may use raw scalar algebra, but only when the scalar equation
is dimensionless or connected to a physical quantity through an explicit
projection bridge. A passing SymPy artifact should not be merely a correct
algebraic identity detached from the physics that motivated it.

## Enriched Artifact Contract

Keep the existing contract from the [physics SymPy backend guide](PHYSICS_SYMPY_BACKEND.md) and add these
equational physics surfaces:

- `QUANTITY_SURFACE`: source-backed quantity entries with symbol, kind, domain,
  dimension, unit note, scalar/vector/field/operator role, and source anchor.
- `CONTEXT_ASSUMPTIONS`: frame, sign convention, regime, idealization,
  boundary/initial condition, smoothness, positivity, nonzero, and constancy
  assumptions, each labeled `source_backed`, `generated_support`, `api_backed`,
  or `blocked`.
- `LAW_TABLE`: physical laws and mathematical rules used by each transformation,
  with source anchors or generated-support labels.
- `EQUATION_GRAPH`: nodes for source equations, generated bridge equations,
  target equations, and derived equations; edges for substitution, solve,
  simplify, differentiate, integrate, expand, factor, limit, or projection
  steps.
- `PROJECTION_BRIDGES`: explicit links from vector, tensor, field, or operator
  statements to scalar component equations used by SymPy.
- `SIDE_CONDITIONS`: domain restrictions needed by transformations, including
  denominator nonzero constraints, branch assumptions, positivity, monotonicity,
  differentiability, and integration constants.
- `EQUIVALENCE_CERTIFICATES`: per-step residual checks, inverse-substitution
  checks, matrix equality checks, numeric samples, and known limitations.

Add validator functions when artifacts are enriched:

- `validate_equational_semantics()`
- `validate_assumption_context()`
- `validate_projection_bridges()`
- `validate_no_hidden_target()`
- `validate_law_usage()`
- `review_final_equations()`

## Reused Existing Skills

Reuse these existing skills before creating new ones:

- Physics informal preformalization:
  `physics-informal-derivation-elicitor`,
  `physics-informal-derivation-expander`, and
  `physics-informal-derivation-readiness-reviewer`.
- Physics source and context spine:
  `physics-derivation-source-extractor`,
  `physics-symbol-table-builder`,
  `physics-dimension-modeler`,
  `physics-unit-system-grounder`,
  `physics-equation-parser`,
  `physics-regime-assumption-modeler`,
  `physics-coordinate-frame-context-builder`,
  `physics-implicit-gap-detector`,
  `physics-derivation-gap-expander`, and
  `physics-law-concept-grounding-navigator`.
- Generic SymPy backend skills:
  `sympy-dependency-prober`,
  `sympy-api-docs-indexer`,
  `sympy-expression-parser`,
  `sympy-assumption-modeler`,
  `sympy-concept-grounding-navigator`,
  `sympy-autoformalization-drafter`,
  `sympy-execution-runner`,
  `sympy-identity-validator`,
  `sympy-counterexample-searcher`,
  `sympy-transformation-trace-verifier`, and
  `sympy-consistency-report-orchestrator`.
- Physics SymPy executor stack:
  `physics-sympy-dependency-prober`,
  `physics-sympy-derivation-drafter`,
  `physics-sympy-execution-runner`,
  `physics-unit-analysis-verifier`,
  `physics-derivation-step-verifier`,
  `physics-numeric-sanity-sampler`, and
  `physics-derivation-consistency-report-orchestrator`.
- Mathematical support and web research:
  proof-expansion difficulty estimation, web-supported proof expansion,
  prerequisite expansion, source-line translation, semantic preservation
  checks, and API/web evidence validation should be reused when a physics law,
  SymPy API behavior, or derivation bridge is too large to infer locally.

## New Skills To Build

Build only the new skills that add control surfaces not already covered by the
existing stack.

### `physics-sympy-workflow-orchestrator`

Purpose: produce a backend-specific plan that names the equational physics
gates, protected evidence, refinement order, and output artifacts.

Inputs: source packet, informal expansion, quantity table, dimensions, units,
regimes, frame packet, gap packet, law packet, and selected backend style.

Outputs: `physics_sympy_workflow_plan`.

Exit criteria: plan identifies required validators, critic stack, final review
gates, local repair surfaces, and optional FormalPhysics reflection.

### `physics-sympy-equation-surface-builder`

Purpose: translate Lean-style type preservation into an equational quantity and
equation surface for SymPy.

Checks:

- scalar, vector, field, operator, parameter, and generated-support symbols are
  distinguished;
- dimensions and units are attached to every quantity when available;
- vector or field reductions create `PROJECTION_BRIDGES`;
- each equation is classified as source, generated bridge, target, derived, or
  blocked;
- derived equations are not target assumptions.

Output: `physics_sympy_equation_surface_packet`.

### `physics-sympy-assumption-context-encoder`

Purpose: encode contextual physics assumptions into SymPy-compatible symbol
assumptions and an explicit side-condition ledger.

Checks:

- positivity, nonzero, realness, integrality, smoothness, differentiability,
  boundary, initial, constant-quantity, frame, gauge, and regime assumptions are
  labeled;
- SymPy assumptions are not silently stronger than the source;
- generated support assumptions are visible to reviewers.

Output: `physics_sympy_assumption_context_packet`.

### `physics-sympy-execution-interpreter`

Purpose: classify Python/SymPy execution diagnostics before refinement.

Diagnostic classes:

- dependency/import failure;
- parse failure;
- symbol or assumption mismatch;
- unit/dimension failure;
- transformation residual failure;
- numeric counterexample;
- projection-bridge failure;
- law-grounding failure;
- hidden-target or empty-equation risk.

Output: `physics_sympy_execution_interpretation`.

### `physics-sympy-equational-semantics-critic`

Purpose: check whether the executable equations preserve the source physics.

Critical failures:

- target equation appears as an input equation or all-purpose law;
- source law is missing from the transformation that uses it;
- scalar algebra erases vector, field, operator, or frame structure without a
  projection bridge;
- source conclusion is weakened from equivalence to implication, from vector to
  component, or from general regime to special case without labels;
- generated bridge equations lack source or law support.

Output: `physics_sympy_equational_semantics_critic_report`.

### `physics-sympy-dimension-projection-critic`

Purpose: stress-test the unit and projection discipline beyond basic dimension
checks.

Checks:

- addition, subtraction, transcendental functions, exponentials, and logarithms
  respect dimension constraints;
- vector and field component equations reconstruct the intended physical claim;
- coordinate/sign conventions are visible for component-level equations;
- dimensionless constants and normalized quantities are labeled.

Output: `physics_sympy_dimension_projection_critic_report`.

### `physics-sympy-generative-critic-orchestrator`

Purpose: run optional Codex-exec adversarial probes for high-risk or near-final
SymPy physics artifacts.

Generative probes should ask:

- Can the equation trace be correct while the source physics is false because a
  law, frame, vector structure, or assumption was dropped?
- Which unit substitution or domain choice breaks the derivation?
- Is there a smaller executable artifact that passes by assuming the target?
- Which transformation needs a missing side condition?

Generative findings are hypotheses. They block only when backed by source
anchors, deterministic reports, execution diagnostics, or repeated independent
probes.

Output: `physics_sympy_generative_critic_report`.

### `physics-sympy-final-equation-reviewer`

Purpose: review the final physics equation graph before complete status.

Required properties:

- every source quantity is represented or explicitly projected;
- units and dimensions pass for all source, bridge, and derived equations;
- frames, regimes, approximations, and side conditions are explicit;
- each transformation cites a physical law, generated bridge, or SymPy rule;
- target derivation is computed from prior equations;
- numeric samples respect physical domains;
- no target-shaped equation, axiom, or shortcut is used.

Output: `physics_sympy_final_equation_review`.

### `mathematical-sympy-final-equation-reviewer`

Purpose: review the mathematics of the final equation trace independently of
the physics context.

Required properties:

- all expressions parse into the intended SymPy objects;
- equality direction and equivalence claims are preserved;
- transformation residuals are zero under declared assumptions;
- branch, denominator, invertibility, matrix-shape, and function-domain side
  conditions are explicit;
- counterexample search finds no admissible counterexample;
- the trace is executable and non-vacuous.

Output: `mathematical_sympy_final_equation_review`.

### `physics-sympy-review-refinement-router`

Purpose: convert failed final reviews into localized monotonic repair plans.

Repair surfaces:

- `quantity_surface`
- `assumption_context`
- `unit_dimension`
- `law_grounding`
- `equation_parse`
- `projection_bridge`
- `transformation_step`
- `numeric_domain`
- `target_nonleakage`
- `trace_realness`

Monotonicity constraints:

- preserve every passing source anchor;
- preserve already-correct equation nodes and transformation certificates;
- do not strengthen assumptions without labels;
- do not weaken the target equation;
- do not replace a local repair with a broad rewrite;
- rerun every affected critic and final reviewer.

Output: `physics_sympy_review_refinement_plan`.

### `physics-sympy-formal-answer-reflector`

Purpose: optional inspiration-only comparison with a withheld FormalPhysics
`formal_answer` after the informal-first SymPy candidate or blocker report
exists.

The dataset formalization is not a benchmark target for SymPy. Use it only to
extract theorem-shape, law, assumption, or decomposition inspiration. Accepted
changes must route through the final reviewers and the localized refinement
router.

Output: `physics_sympy_formal_answer_reflection`.

## Enriched Workflow

The enriched loop should be:

1. Probe SymPy and physics dependencies.
2. Extract source physics packet.
3. Run informal elicitation, expansion, and readiness review.
4. Build symbol table, dimensions, units, equations, regimes, and frame packet.
5. Detect and expand implicit derivation gaps.
6. Ground physical laws and SymPy APIs, using web support when local evidence is
   insufficient.
7. Build the SymPy workflow plan.
8. Build the equational quantity surface and equation graph.
9. Encode contextual assumptions and side conditions.
10. Draft the executable SymPy artifact.
11. Execute immediately and interpret diagnostics.
12. Verify units, steps, symbolic residuals, and numeric samples.
13. Run equational semantics and dimension/projection critics.
14. Run generative critics only for high-risk or near-final artifacts.
15. Run physics and mathematical final equation reviewers.
16. Route failures to localized monotonic refinement.
17. Emit enriched physics derivation consistency report.
18. Optionally run inspiration-only FormalPhysics formal-answer reflection.

## Refinement Order

Refinements should proceed in this order:

1. Dependency or import failures.
2. Parse and symbol-binding failures.
3. Assumption-context failures.
4. Unit and dimension failures.
5. Projection-bridge failures.
6. Law-grounding failures.
7. Transformation residual failures.
8. Numeric-domain failures.
9. Equational semantics failures.
10. Final review failures.
11. Process or skill improvements after repeated blockers.

Each repair must be local. A failed derivative step should not rewrite the whole
artifact. A missing nonzero side condition should not alter unrelated equations.
An incorrect vector projection should repair the projection bridge and rerun the
impacted reviewers.

## Acceptance Criteria

A SymPy physics derivation can be `complete` only when:

- the artifact imports and executes;
- the target equation is derived from source or generated-support equations;
- every transformation has an executable certificate or explicit blocker;
- units and dimensions pass at the equation and transformation level;
- contextual assumptions are visible and not silently strengthened;
- scalar reductions are connected back to physical quantities when needed;
- numeric samples and counterexample probes pass under admissible domains;
- physics and mathematical final equation reviews pass;
- consistency report marks no critical blocker;
- optional FormalPhysics comparison, when used, remains inspiration-only.

## Implementation Status

Implemented slices:

1. Documentation and hook plan:
   - this enrichment plan is in the docs;
   - the [physics SymPy backend guide](PHYSICS_SYMPY_BACKEND.md) describes the enriched contract;
   - `skills/SKILL_HOOKS.yaml` includes the enriched hooks, loop entries,
     shared runtime scripts, and direct routes.
2. Minimal skill slice:
   - `physics-sympy-workflow-orchestrator`;
   - `physics-sympy-equation-surface-builder`;
   - `physics-sympy-assumption-context-encoder`;
   - `physics-sympy-equational-semantics-critic`;
   - `physics-sympy-review-refinement-router`.
3. Reviewer slice:
   - `physics-sympy-final-equation-reviewer`;
   - `mathematical-sympy-final-equation-reviewer`;
   - the controlled pipeline consistency report now includes enriched evidence
     and requires final equation reviews for complete status.
4. Generative and reflection slice:
   - `physics-sympy-dimension-projection-critic`;
   - `physics-sympy-generative-critic-orchestrator`;
   - `physics-sympy-formal-answer-reflector`.
5. Executable backend slice:
   - generated controlled SymPy physics artifacts now expose
     `QUANTITY_SURFACE`, `EQUATION_GRAPH`, `LAW_TABLE`,
     `PROJECTION_BRIDGES`, `CONTEXT_ASSUMPTIONS`, `SIDE_CONDITIONS`,
     `EQUIVALENCE_CERTIFICATES`, and the enriched validators.

Remaining validation work is empirical rather than structural: run the existing
controlled and adversarial SymPy physics suites in an environment with SymPy
installed, add FormalPhysics-inspired equational cases, and broaden adversarial
probes for target leakage, hidden assumptions, scalar erasure, unit
inconsistency, and invalid branch assumptions.
