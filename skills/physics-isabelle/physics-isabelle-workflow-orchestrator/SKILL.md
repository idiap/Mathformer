---
name: physics-isabelle-workflow-orchestrator
description: Plan and run a safe Isabelle/HOL backend path for physics autoformalization by reusing the physics and mathematical preformalization pipeline while keeping all Lean hooks, artifacts, and review gates isolated.
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

# Physics Isabelle Workflow Orchestrator

Use this skill when a physics derivation should be routed to Isabelle/HOL
without disturbing the existing Lean physics flow.

## Core Contract

- Reuse shared physics preformalization: source extraction, informal
  elicitation/expansion, symbol tables, dimensions, units, equations, regimes,
  frames, gaps, and law grounding.
- Reuse shared mathematical preformalization: semantic-preservation checks,
  source-unit inventory, proof-expansion support, web/library grounding,
  prerequisite expansion, line translation, result-existence precheck,
  dependency resolution, syntax critique, non-vacuity, reverse
  informalization, and final mathematical hypothesis review.
- Reuse Isabelle-specific infrastructure: Isabelle/HOL and HOL-Analysis
  grounding, optional IsarMathLib grounding, `physics-isabelle-derivation-drafter`,
  Isabelle execution, final physics and mathematical reviewers, and the
  Isabelle physics consistency report.
- Do not rename, replace, or repoint `physics.lean.*` hooks.
- Store Isabelle artifacts under `artifacts/physics_isabelle/` or `backends/isabelle/Isabelle/`
  and use `.thy` theory files.
- Use `Complex_Main` for scalar baselines, and prefer installed
  `HOL-Analysis.Analysis` surfaces for vector, field, calculus, norm/inner,
  and operator structure whenever they fit the source.
- Elicit and review missing informal physics context and expected grounding
  before formalization. Preserve source-backed versus generated-support labels.
- Route every required intermediate definition, field definition, source law,
  calculus support fact, unit/dimension bridge, operator identity, projection
  bridge, and algebraic core lemma through `dependency.resolve` and the
  Isabelle background dependency plan.
- Draft the Isabelle theory with the full original informal statement and
  derivation in a header `text \<open>...\<close>` block, followed by explicit
  informal-to-formal alignment commentary. Map every informal step to theorem
  assumptions, support lemmas, locales, or proof blocks.
- When the derivation has a reusable algebraic heart, create a compact
  dataset-style algebraic core lemma and prove the physics-rich theorem by
  calling that core.
- Keep local records, string labels, bool-only labels, and raw scalar-only
  surfaces as draft-only fallbacks unless an explicit dependency blocker
  explains why no library grounding is available. Complete physics-bearing
  Isabelle artifacts require high Isabelle/HOL-native grounding.
- Execute Isabelle immediately, interpret diagnostics as physics/type/unit/
  assumption/library/proof failures, and refine locally.
- Run deterministic physics critics, Codex-exec generative critics for
  high-risk or near-final artifacts, final physics and mathematical hypothesis
  reviewers, and the Isabelle physics consistency report before claiming
  complete status.
- Failed review items must return to a localized monotonic refinement point:
  preserve already-correct source anchors, proved support declarations, theorem
  conclusions, unit/dimension/context labels, and native Isabelle/HOL surfaces.
- Mark the workflow style as `isabelle_physics_derivation_trace`.

Prefer `scripts/build_physics_isabelle_workflow_plan.py` for deterministic
planning and safety checks.
Use `scripts/build_physics_isabelle_background_plan.py` when a typed packet or
informal expansion exposes background definitions/results that must be
formalized before the target theorem.

## Protected Invariants

- No formalization may hide the target as an axiom, `consts`, or theorem
  assumption.
- No complete artifact may contain `sorry`, `oops`, `quickcheck_params`, or
  TODO placeholders.
- No physics-bearing source may be reduced to untyped scalar algebra unless
  the source is explicitly scalar-only; scalar cores must be exposed as
  projections from a typed/native physics wrapper.
- No complete artifact may treat local wrappers, opaque dimensions, bool-only
  context flags, or string labels as maximal Isabelle grounding when
  `Complex_Main`, `HOL-Analysis`, installed Isabelle/HOL theories, IsarMathLib,
  or `MathformerPhysicsLib` can represent the same surface.
- Every source-backed quantity should have a type, dimension/unit note,
  projection bridge, or explicit blocker.
- Every contextual assumption introduced for Isabelle must be source-backed,
  generated-support, or blocked; silent strengthening is not allowed.
- Every complete Isabelle physics artifact must preserve original-informal to
  formal alignment in header commentary before the first support declaration.
- Every required background item must be formalized, reused from
  Isabelle/HOL/IsarMathLib/MathformerPhysicsLib, marked not required, or
  explicitly blocked before the target theorem can be complete.
- Background lemmas must not be target-shaped assumptions, and already-correct
  support declarations are protected during later refinement.
- Complete status requires Isabelle execution, placeholder-free proof,
  source-anchor evidence, realness/non-vacuity evidence, high Isabelle/HOL
  grounding, closed background obligations, and passing physics plus
  mathematical final reviews.
