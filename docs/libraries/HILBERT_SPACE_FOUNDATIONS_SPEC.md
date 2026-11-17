<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Use Hilbert space as a complex physics abstraction benchmark for
  MathformerPhysicsLib foundations.

Intent:
  Specify a source-grounded, Mathlib-first, controllably recursive development
  workflow that starts from conservative support and expands toward richer
  theorem-usable Hilbert APIs.

Function:
  Connects source concepts, Mathlib grounding, skills, Lean surfaces, promotion
  gates, recursive frontiers, and acceptance tests.

Maintenance Notes:
  Keep this spec synchronized with the foundations workflow, HilbertSpace Lean
  module, and recursive surface-plan artifacts.
-->

# Hilbert Space Foundations Spec

Companion workflow: [MathformerPhysicsLib foundations workflow](MATHFORMERPHYSICSLIB_FOUNDATIONS_WORKFLOW.md).

## Goal

Verify how well Mathformer can autoformalize a complex mathematical abstraction
used in physics by treating Hilbert space as a controlled foundations benchmark.

The workflow must not stop at permanent wrappers. It starts with level-0
Mathlib-grounded support, then recursively expands toward theorem-usable
physics APIs when source evidence, Mathlib grounding, Lean compilation, and
promotion gates allow it.

## Sources

- Wikipedia, `Hilbert space`: broad definition, completeness, inner-product
  geometry, infinite-dimensional behavior, and applications including quantum
  mechanics.
- Locally supplied chapter PDF `ch6.pdf`, OCR artifacts under
  `artifacts/hilbert_space_spec/ocr/`: chapter-level source for inner products,
  physics/applied convention, completeness, examples, orthogonality,
  projections, bases, Bessel, Parseval, and a quantum Hamiltonian exercise.

The PDF's raw text extraction was noisy, so source extraction used OCR pages.
OCR evidence is acceptable for concept inventory and routing, but exact theorem
statements should be rechecked before promotion.

## Key Properties To Formalize

| Source concept | Mathlib-first grounding | MathformerPhysicsLib role |
| --- | --- | --- |
| Inner product space | `InnerProductSpace 𝕜 H` with `RCLike 𝕜` | expose physics state role and convention notes |
| Hilbert space completeness | `CompleteSpace H` plus normed additive group | distinguish pre-Hilbert from Hilbert states |
| Induced norm and distance | Mathlib norm from inner product APIs | route norm/metric statements to Mathlib, not local axioms |
| Cauchy-Schwarz, parallelogram, polarization | Mathlib inner-product theorems | recursive theorem-reuse frontier |
| Orthogonality | `inner 𝕜 x y = 0`, orthogonal submodule APIs | source-backed orthogonality witness for physics prose |
| Projection theorem / best approximation | `orthogonalProjection`, closed submodule APIs | recursive projection-surface frontier |
| Orthogonal direct sums | Mathlib submodule/direct-sum APIs | modal decomposition and closed-subspace splits |
| Orthonormal bases | `HilbertBasis`, `Orthonormal`, summability APIs | basis, coordinate, Fourier/mode expansion roles |
| Bessel and Parseval | Mathlib Hilbert basis theorem APIs | recursive expansion from basis surface to theorem support |
| Examples | finite `C^n`, `l2`, `L2`, matrix trace inner products | benchmark cases for future examples |
| Operators | `ContinuousLinearMap`, adjoint/self-adjoint/unitary APIs | Hamiltonians, observables, unitary evolution |
| Hilbert-Schmidt operators | finite matrix trace first; basis-relative summability frontier | controlled operator-theory expansion, not a fake full theory |

## Implemented Foundation Surfaces

The current level-0 Lean surface lives in:

- `libraries/MathformerPhysicsLib/Lean/Foundations/HilbertSpace.lean`
- `libraries/MathformerPhysicsLib/Lean/Foundations.lean`

It introduces Mathlib-grounded support for:

- `HilbertStateCarrier`
- `hilbertInner`
- `HilbertBoundedOperator`
- `HilbertBasisSurface`
- `HilbertOrthogonalityWitness`
- `HilbertProjectionWitness`
- `HilbertOperatorAdjointWitness`
- `SelfAdjointOperatorWitness`
- `UnitaryOperatorWitness`
- `HilbertSchmidtWithBasisWitness`

These are not final replacements for Mathlib theory. They are physics-facing
entry points that preserve Mathlib carriers and make source roles explicit.

## Recursive Promotion Ladder

Every Hilbert surface carries a promotion ladder in
`skills/mathformerphysicslib/mathformerphysicslib-foundation-surface-designer/scripts/design_foundation_surfaces.py`.

The controlled ladder is:

1. `level 0`: compile a Mathlib-grounded bridge or reuse surface.
2. `level 1`: identify and expose theorem-usable Mathlib APIs.
3. `level 2`: connect the APIs to physics examples and downstream target
   theorem repair.
4. `blocked`: if Mathlib support is missing or semantics are unclear, record an
   explicit blocker and keep downstream repair from silently depending on it.

Current Hilbert frontiers:

- inner product carrier -> norm, metric, Cauchy-Schwarz, parallelogram,
  polarization, quantum-state role;
- orthogonality/projection -> closed-subspace projection theorem,
  best-approximation, decomposition;
- orthonormal basis -> Bessel, Parseval, coordinates, Fourier/l2/L2 examples;
- operators -> adjoint, self-adjoint, unitary, Hamiltonian/evolution APIs;
- Hilbert-Schmidt -> finite matrix trace grounding, then infinite-dimensional
  operator-ideal blocker or promoted API.

## Skill Strategy

Use existing skills in this order:

1. `physics-foundation-object-intake`: normalize source concepts into canonical
   Hilbert foundation objects.
2. `mathformerphysicslib-foundation-surface-designer`: choose Mathlib-first
   surfaces and emit the recursive frontier.
3. `mathformerphysicslib-foundation-drafter`: draft level-0 support only.
4. `mathformerphysicslib-foundation-verifier`: compile and reject vacuous
   support.
5. `mathformerphysicslib-object-workbench`: check whether downstream repair can
   reuse the support.
6. `physics-lean-repair-expansion-cartographer` and
   `physics-lean-recursive-repair-loop-controller`: recurse only when the
   frontier changes, gates rerun, and blockers are explicit.
7. Coherence and grounding critics: audit redefinition, Mathlib reuse,
   integration, API operability, and generative coherence before promotion.

No parallel Hilbert-only workflow should be created unless these skills cannot
represent a required frontier item.

## Goal-Based Development Loop

Each iteration must produce an inspectable artifact and either shrink the
frontier or record a blocker.

1. **Source goal**: extract source concepts and provenance from Wikipedia and
   the OCR chapter.
2. **Object goal**: classify concepts into canonical objects, including
   Hilbert carrier, projection, basis, operators, and Hilbert-Schmidt support.
3. **Grounding goal**: map every object to Mathlib targets or blockers.
4. **Surface goal**: emit level-0 declarations plus recursive frontier items.
5. **Draft goal**: compile candidate Lean without `sorry`, `admit`, axioms, or
   scaffold-only propositions.
6. **Verifier goal**: run structural verifier, Lean index compile, workbench
   reuse, and strict workflow audit.
7. **Expansion goal**: pick one frontier item, add the next theorem-usable API
   or blocker, then rerun the full suite.
8. **Promotion goal**: only promote after deterministic gates and coherence
   critics agree that the support is reusable.

## Acceptance Gates

A Hilbert expansion pass is accepted only if:

- `lake env lean libraries/MathformerPhysicsLib/Lean/Foundations.lean` succeeds;
- `python tests/physics_lean/run_foundations_workflow.py --json` reports
  `surface_plan_is_recursive` and `hilbert_recursive_frontier_present`;
- the natural-language router maps a Hilbert recursive-foundations request to
  `formalize.physics.lean.foundations`;
- `python scripts/mathformer.py audit --strict --json` reports no uncontrolled
  entrypoints;
- any generated theorem support is justified by Mathlib APIs or explicit
  source-backed assumptions;
- frontier items are never silently dropped.

## Implemented TODOs

- [x] Add Hilbert foundation object profiles for inner-product spaces,
  orthogonal projection, bases, adjoint/self-adjoint operators, and
  Hilbert-Schmidt support.
- [x] Prioritize specific Hilbert matches before generic projection/operator
  routing.
- [x] Add `libraries/MathformerPhysicsLib/Lean/Foundations/HilbertSpace.lean`.
- [x] Import Hilbert foundations from the accepted foundations index.
- [x] Add recursive promotion ladders and frontier output to the surface
  designer.
- [x] Check recursive Hilbert frontier presence in the foundations workflow
  test.
- [x] Add `foundation.recursive_expansion` to workflow hooks.
- [x] Teach the natural-language router to recognize recursive Hilbert
  foundations requests.

## Next Controlled Frontier

- [ ] Promote level-1 norm/metric theorem wrappers by reusing exact Mathlib
  theorem names.
- [ ] Promote projection theorem support around closed submodules and
  `orthogonalProjection`.
- [ ] Promote Parseval/Bessel support around `HilbertBasis`.
- [ ] Bind self-adjoint Hamiltonian examples to the existing TDSE
  FormalPhysics cases.
- [ ] Decide whether Hilbert-Schmidt should stay finite-dimensional first or
  expose an explicit infinite-dimensional blocker.
