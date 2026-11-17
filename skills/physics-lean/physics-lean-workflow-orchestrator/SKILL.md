---
name: physics-lean-workflow-orchestrator
description: Orchestrate Lean autoformalization of physics derivations using source anchoring, physical quantity typing, contextual assumptions, unit analysis, explicit deterministic and generative physics critics, final physics and mathematical hypothesis reviewers, mathlib grounding, Lean execution interpretation, localized monotonic refinement loops, and final physics consistency gates.
---

<!--
File Documentation

Motivation:
  Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

Intent:
  Tell coding agents what context to load, what invariants to preserve, and how to validate their work.

Function:
  Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Physics Lean Workflow Orchestrator

Use when a physics derivation should be formalized in Lean rather than only
executed in SymPy.

## Core Contract

The workflow reuses the existing physics preformalization spine:
source extraction, symbol tables, dimensions, units, equations, regimes, frames,
implicit gaps, physical-law grounding, and derivation planning.

Then it adds Lean-specific control:

1. Elicit missing informal physics context and expected formal grounding before
   formalization, preserving source-backed versus generated-support labels.
2. Review the expanded informal derivation for source anchors, law/rule
   provenance, assumptions, dimensions, units, frames, regimes, expected
   grounding roles, dependency-resolution handoff, and unresolved web-support
   needs.
3. Build a Lean physics typing packet with Mathlib-native carriers first:
   finite vectors, fields, modules, linear maps, calculus predicates, operator
   surfaces, quantity dimensions, vector/scalar status, frames, regimes, and
   law provenance.
4. Build a background dependency plan for intermediate definitions, background
   results, projection bridges, source-law support lemmas, unit/dimension
   bridge lemmas, and compact algebraic cores. Search Mathlib and existing
   `MathformerPhysicsLib` declarations before creating local support.
5. Encode contextual assumptions as explicit Lean parameters, hypotheses, type
   classes, namespaces, or structure fields.
6. Draft Lean from the source packet, mathlib hints, type packet, unit packet,
   and assumption packet. The artifact must keep the full original informal
   statement/derivation as a module doc-comment header and map every informal
   derivation step to its corresponding Lean hypotheses, lemmas, or proof
   blocks as commentary. The header must also include a `Semantic preservation
   contract` stating the source target, Lean target, preservation status,
   source assumptions preserved, additional assumptions introduced, unmodeled
   source content, semantic deltas, step alignment, and trust boundary. When the
   derivation has a reusable algebraic heart, draft a compact core theorem for
   that algebra and prove the physics-rich typed/contextual theorem by invoking
   the core.
   Local `Quantity`/`VectorQuantity` wrappers, opaque dimension markers, and
   string-valued context labels are fallback scaffolds only; complete status
   requires Mathlib-native grounding or an explicit blocker/waiver.
7. Execute Lean immediately through the standard Lean runner.
8. Interpret Lean diagnostics as physics/type/unit/assumption/mathlib/proof
   failures before refinement.
9. Verify unit and dimension obligations on the Lean artifact.
10. Run deterministic physics critics for semantic preservation, contextual
   assumptions, and dimensions; run Codex-exec generative critics for high-risk
   or near-final artifacts; run the FormalScience drift-pathology monitor for
   notational collapse, abstraction elevation, proof strategy substitution, and
   implicit premise selection.
11. When the drift-pathology monitor reports actionable findings, detect the
   missing physics mathematical object, work over it first in
   `MathformerPhysicsLib`, run the pathology-specific repair planner, and only
   then allow localized target theorem refinement.
12. For high-risk or blocked pathology repairs, run guarded Codex-exec
   generative repair proposals. Treat those proposals as advisory until the
   MathformerPhysicsLib registry, promotion gate, Lean build, drift monitor,
   critics, and consistency report rerun.
13. Map the recursive repair expansion exhaustively and run recursive loop
   control before another iteration, final acceptance, or target refinement.
14. Run final physics and mathematical hypothesis reviewers before consistency
   acceptance.
15. Route failed reviews to localized monotonic review refinement.
16. Run refinement loops until the artifact is complete, blocked, or marked
   draft with explicit blockers.
17. Run realness, source-anchor, reverse-informalization, non-vacuity, mathlib,
   and physics consistency gates before claiming success.

Prefer `scripts/build_physics_lean_workflow_plan.py` for the deterministic
workflow plan packet.

Use `scripts/compare_math_physics_pipeline.py` when the task asks whether the
Lean physics loop preserves the mathematical autoformalization contract. The
physics loop must inherit the shared mathematical gates for line translation,
result-existence precheck, proof-expansion support, proof-expansion web
research, prerequisite expansion/review, mathlib web grounding, Lean execution,
syntax critique, semantic preservation, logical soundness, mathlib alignment,
refinement, denoising, source-anchor drift, realness, reverse informalization,
declaration-shape review, informal consistency, non-vacuity, cross-file
concepts, unified consistency, RFDE, and reference-free monitoring. Physics
informal elicitation/expansion and physics critics strengthen these gates; they
do not replace them.

## Protected Invariants

- No formalization may hide the target as an axiom or hypothesis.
- No physical equation may be reduced to untyped scalar algebra unless the
  source is explicitly only scalar algebra.
- No complete artifact may treat local wrappers, opaque dimensions, or
  `String` labels as maximal Mathlib grounding when a native Mathlib carrier or
  predicate can represent the same surface.
- Every source-backed quantity should have a dimension, unit note, type, or
  explicit blocker.
- Every contextual assumption introduced for Lean must be source-backed or
  marked generated-support.
- Every complete Lean physics artifact must preserve original-informal to
  formal alignment and an explicit semantic-preservation contract in a header
  commentary before the namespace or first declaration.
- Generative workflows must consult
  `artifacts/physics_lean/reviews/autoformalization_design_todos.md` and treat
  its high-severity TODOs as design guards before claiming a new artifact is
  complete.
- `PhysicsContext True` and reflexive `UnitDimensionCompatible x x` are
  transitional scaffolds only. New complete artifacts must either replace them
  with typed source-backed propositions or record a semantic-delta blocker.
- Algebra-heavy physics artifacts should keep proof noise out of the
  typed/contextual wrapper by delegating to a compact reusable core theorem
  with the smallest sound mathematical surface.
- Every required intermediate definition, background result, projection bridge,
  source-law support lemma, unit/dimension bridge, and algebraic core must be
  formalized, reused from Mathlib/MathformerPhysicsLib, or explicitly blocked
  before the target theorem can be complete.
- Every detected FormalScience drift pathology must route through the
  MathformerPhysicsLib object workbench before the target theorem is repaired.
- Generative repair output must never bypass deterministic object work,
  promotion, compile, realness, non-vacuity, source-anchor, or consistency gates.
- Background lemmas must not be target-shaped assumptions, and already-correct
  support declarations are protected during later refinement.
- Complete status requires Lean execution, physics unit consistency, and
  explicit generic semantic-preservation, Mathlib grounding, physics critic,
  FormalScience drift-pathology monitor, and final reviewer evidence.
