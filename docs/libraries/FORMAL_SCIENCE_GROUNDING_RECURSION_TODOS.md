<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Plan how to move FormalPhysics Lean outputs from algebraic shells toward
  recursively grounded MathformerPhysicsLib artifacts.

Intent:
  Name the current grounding pathologies and define implementation TODOs that
  use the new foundations, Mathlib grounding, and recursive repair skills.

Function:
  Serves as a task list for making generated formal-science outputs build
  required physics mathematical objects before proving benchmark algebra.

Maintenance Notes:
  Keep this document synchronized with FormalPhysics generators, foundation
  object intake, recursive expansion control, and downstream verification tests.
-->

# Formal Science Grounding Recursion TODOs

## Diagnosis

The current FormalPhysics Lean outputs are too often correct only after the
physics is compressed into algebra. This is visible in examples such as
`formalphysics_0191` and `formalphysics_0059`:

- local `Unit`, `Dimension`, `Law`, and `UnitDimensionCompatible` definitions
  collapse support into `True`;
- source-backed laws such as adjoint TDSE, expectation-product differentiation,
  chain rule, and differentiation under the integral are represented as `True`
  assumptions rather than typed mathematical objects;
- Hilbert-space states are only `[InnerProductSpace ℂ H]`, without complete
  Hilbert carrier reuse or operator topology;
- Hamiltonians are plain `LinearMap`s rather than bounded/self-adjoint or
  explicitly blocked unbounded operators;
- bra-ket expressions are reduced to scalar variables like `leftTerm`,
  `rightTerm`, `paramInner`, and `lhs`;
- derivatives, parameter curves, integrals, and boundary conditions are
  compressed into equality hypotheses;
- the proof obligation becomes a ring/linarith identity instead of a statement
  over reusable physics objects.

This is not merely a theorem-generation problem. It is a missing-object problem:
the output should recursively build and ground the required physics
mathematical objects before the algebraic core is allowed to discharge the final
identity.

## Target Shape

Every generated FormalPhysics Lean artifact should have three layers:

1. **Physics object layer**: canonical MathformerPhysicsLib objects for states,
   fields, operators, laws, regimes, units, derivatives, integrals, and
   boundary conditions.
2. **Source law layer**: source-backed propositions over those objects, using
   Mathlib carriers and accepted foundation records.
3. **Algebraic core layer**: the smallest remaining scalar/vector algebra after
   the object and law layers have produced the needed equalities.

The algebraic core is still useful, but it should be the end of the pipeline,
not the substitute for the pipeline.

## Recursive Grounding Loop

For each benchmark target:

1. Detect physics mathematical objects from the informal statement, current Lean
   candidate, and source derivation.
2. Canonicalize each object into a MathformerPhysicsLib owner candidate.
3. Audit Mathlib grounding before creating local support.
4. If support is missing, run the foundations workflow to create level-0
   support and emit a recursive promotion frontier.
5. Rerun the object workbench and pathology loop.
6. Generate advisory repair proposals only after deterministic object gaps are
   recorded.
7. Build an expansion map containing every missing object, law, bridge, theorem
   API, and target-edit obligation.
8. Use the recursive controller to decide `recurse`, `complete`, or `blocked`.
9. Permit target theorem edits only when the required library-first object work
   is promoted, reused, or explicitly blocked.

## Implemented Completeness Gate

Lean physics generation now has a derivation-completeness gate that separates
kernel validity from complete autoformalization. The gate emits these statuses:

- `compiled_surface`: Lean accepted the artifact.
- `grounded_scaffold`: the artifact uses Mathlib or MathformerPhysicsLib
  surfaces.
- `derivation_partial`: source-step obligations or recursive frontier remain.
- `blocked_target_restating_assumption`: a hypothesis or witness carries the
  final target.
- `complete_autoformalization`: all source-step obligations are proved, reused,
  or legitimate external laws.

The implementation checklist and acceptance criteria live in
[`docs/operations/LEAN_PHYSICS_DERIVATION_COMPLETENESS_TODOS.md`](../operations/LEAN_PHYSICS_DERIVATION_COMPLETENESS_TODOS.md).

## TODOs

Implementation evidence, 2026-07-08:

- Deterministic debt surface: `grounding_debt_report` in
  `physics-lean-drift-pathology-monitor`.
- Compact gate: `physics-lean:formal-science-grounding-debt`.
- Natural-language route:
  `ground FormalPhysics outputs recursively before algebraic proof`.
- Regression report:
  `artifacts/physics_lean/formal_science_grounding_debt/report.json`.

### 1. Grounding Debt Detector

- [x] Add a deterministic detector for algebraic-shell pathologies in generated
  FormalPhysics Lean files.
- [x] Flag local support definitions equivalent to `Prop := True`,
  `abbrev Law (_ : Prop) : Prop := True`, and one-off unit/dimension wrappers.
- [x] Flag source laws whose type is exactly `True`.
- [x] Flag physics terms represented only as free scalar variables when a known
  object class exists, for example Hilbert inner products, Hamiltonian actions,
  derivatives, integrals, and boundary terms.
- [x] Emit a `formal_science_grounding_debt_report` with file, declaration,
  source concept, missing object class, and severity.

### 2. FormalPhysics Object Intake

- [ ] Extend `physics-foundation-object-intake` with FormalPhysics-specific
  concept extraction from theorem comments, variables, assumptions, and names.
- [ ] Add object profiles for variational functionals, trial functions, endpoint
  constraints, Lagrangian density, differentiation under the integral, and
  Euler-Lagrange-adjacent chain-rule surfaces.
- [ ] Add object profiles for quantum expectation values, parameterized
  Hamiltonians, TDSE ket law, adjoint bra law, and parameter derivatives.
- [ ] Preserve source benchmark ids and derivation-step provenance on every
  object packet item.

### 3. Canonical Ownership

- [ ] Route detected objects through
  `mathformerphysicslib-concept-canonicalizer` before generation.
- [ ] Require every object to name an owner module under
  `libraries/MathformerPhysicsLib/Lean/Foundations` or an explicit future module.
- [ ] Block target theorem generation when an object appears in multiple local
  files without a canonical owner.
- [ ] Add a spread-risk report for repeated local definitions of units, laws,
  Hilbert carriers, derivative assumptions, and integral assumptions.

### 4. Mathlib Grounding

- [ ] Run `mathformerphysicslib-mathlib-grounding-auditor` on each canonical
  object graph before drafting local support.
- [ ] Record direct Mathlib targets such as `InnerProductSpace`,
  `CompleteSpace`, `ContinuousLinearMap`, `HasDerivAt`, `HasFDerivAt`,
  `Differentiable`, interval integrals, `MeasureTheory`, `Submodule`,
  `orthogonalProjection`, and `HilbertBasis`.
- [ ] Require a blocker when a physics concept should be an unbounded operator,
  distributional state, or domain-sensitive operator not faithfully represented
  by the current bounded/operator surface.
- [x] Store failed Mathlib candidates so recursive passes do not repeat the same
  search.

### 5. Replace Local Trivial Bridges

- [ ] Replace local `Law` and `source_backed_law_support` shims with
  `MathformerPhysicsLib.Lean.Foundations.Laws`.
- [ ] Replace local `UnitDimensionCompatible` shims with
  `MathformerPhysicsLib.Lean.Foundations.Units`.
- [ ] Replace local generated-support assumptions with
  `MathformerPhysicsLib.Lean.Foundations.Contexts`.
- [ ] Import `MathformerPhysicsLib.Lean.Foundations` in generated FormalPhysics
  files that use accepted foundation support.
- [ ] Add a verifier rule that rejects newly generated local copies of accepted
  foundation declarations.

### 6. Hilbert/Quantum Deepening

- [ ] Update quantum generators to use `HilbertStateCarrier` with
  `CompleteSpace` when the source requires a Hilbert space.
- [ ] Use `HilbertBoundedOperator` for bounded Hamiltonian surfaces and emit an
  explicit blocker for unbounded Hamiltonians until a domain-aware API exists.
- [ ] Represent TDSE ket laws as propositions over the Hamiltonian, state curve,
  and time derivative, not as already-computed scalar equalities.
- [ ] Represent adjoint/bra laws through `HilbertOperatorAdjointWitness` or a
  promoted Mathlib adjoint API.
- [ ] Represent expectation values as `inner ℂ psi (T psi)` or a named
  foundation surface, then derive scalar terms from that expression.
- [ ] Add a recursive frontier item for self-adjoint Hamiltonian support and
  unitary evolution support.

### 7. Calculus-of-Variations Deepening

- [ ] Add foundations for trial-function families
  `g_epsilon x = g x + epsilon * eta x`.
- [ ] Represent fixed endpoint constraints as reusable boundary-context
  records, not anonymous hypotheses.
- [ ] Ground chain-rule steps in Mathlib derivative APIs before reducing to a
  scalar equality.
- [ ] Ground differentiation under the integral using a source-backed theorem
  surface or explicit blocker, not a generated `True` assumption.
- [ ] Represent functional derivatives and integral terms as typed expressions
  before they become scalar placeholders.

### 8. Generator Contract

- [ ] Change FormalPhysics Lean generation so each output includes an
  `object_packet_path`, `grounding_audit_path`, and `recursive_frontier_path`.
- [ ] Require the generator to ask the foundations workflow for every detected
  object before emitting the target theorem wrapper.
- [ ] Allow algebraic core generation only after object-layer obligations are
  terminal or blocked.
- [ ] Make target theorem variables typed by accepted foundation surfaces
  whenever possible.
- [ ] For each scalar placeholder, attach its originating typed expression and
  theorem/law that produced it.

### 9. Recursive Expansion Artifacts

- [ ] Adapt `physics-lean-repair-expansion-cartographer` to include
  `foundation_recursive_frontier` nodes from surface plans.
- [ ] Add node kinds for `missing_foundation_object`, `unpromoted_theorem_api`,
  `trivial_local_bridge`, `source_law_untyped`, and `scalar_placeholder`.
- [ ] Include generated repair proposals as advisory nodes, never as terminal
  support.
- [ ] Block recursion on repeated signatures unless a new object, grounding
  result, or blocker has appeared.

### 10. Tests And Gates

- [x] Add regression tests over `formalphysics_0191` and `formalphysics_0059`
  that fail when source laws are typed as `True`.
- [x] Add tests that fail when accepted foundation declarations are locally
  redefined in generated files.
- [x] Add tests that require quantum examples to use Hilbert foundation support.
- [x] Add tests that require variational examples to expose derivative and
  integral object packets.
- [x] Add a compact gate:
  `python scripts/mathformer.py ask "ground FormalPhysics outputs recursively before algebraic proof" --run --json`.

## Promotion Principle

An output should be considered grounded only when it can answer:

- what physics object each symbol denotes;
- where that object is owned in MathformerPhysicsLib;
- which Mathlib declaration grounds it;
- which source law justifies each equality;
- which assumptions are mathematical, physical, generated, or blocked;
- which recursive frontier items remain before the result is theorem-usable.
