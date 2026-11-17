---
name: physics-lean-drift-pathology-monitor
description: "Monitor Lean physics autoformalization artifacts for FormalScience/FormalPhysics semantic-drift pathologies: notational collapse, abstraction elevation, proof strategy substitution, and implicit premise selection. Use during Lean physics drafting, refinement transitions, critic review, and final consistency gating."
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

# Physics Lean Drift Pathology Monitor

Use this skill while autoformalizing physics into Lean, especially after a
candidate compiles, after a refinement transition, or before final consistency
acceptance.

## Core Contract

Classify possible FormalScience/FormalPhysics drift pathologies:

1. `notational_collapse`: domain-specific physics objects, notation, or
   structures are replaced by simpler mathematical objects.
2. `abstraction_elevation`: concrete symbolic, calculus, integral, operator, or
   coordinate operations are lifted into hypotheses or abstract algebraic
   properties.
3. `proof_strategy_substitution`: the Lean artifact proves the target through a
   different route than the informal derivation.
4. `implicit_premise_selection`: Lean exposes unstated side conditions as formal
   hypotheses.

The first two categories are high-risk by default; proof strategy substitution
is acceptable only when the same physics-bearing objects and target semantics
are preserved; implicit premise selection is beneficial only when every new
premise is source-backed, mathlib-backed, or generated-support labeled.

## Workflow

1. Load the informal physics source, the Lean candidate, and available type,
   assumption, unit, and critic reports.
2. Detect source cues for dense physics notation, quantum operators, vector
   calculus, field/integral content, frames, laws, and implicit side conditions.
3. Compare those cues against Lean surfaces: typed quantities, Hilbert spaces,
   operators, vector fields, coordinate/frame context, calculus/integral
   lemmas, source-law support, and assumption labels.
4. Emit one JSON monitor report with category findings, evidence cues, severity,
   repair surface, and required rerun gates.
5. Route critical findings to localized physics Lean review refinement; never
   use the monitor to weaken the source statement or accept scalar algebra as a
   complete physics formalization.

Prefer `scripts/monitor_physics_lean_drift_pathologies.py` for deterministic
first-pass screening.

## References

- Read `references/formalscience_semantic_drift_taxonomy.md` for the local
  paper-derived taxonomy and severity policy.
