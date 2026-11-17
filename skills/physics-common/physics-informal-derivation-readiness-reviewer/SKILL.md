---
name: physics-informal-derivation-readiness-reviewer
description: Review expanded informal physics derivation packets before formalization, checking source anchors, generated-support labels, physical-law provenance, assumptions, dimensions, units, frames, regimes, and unresolved blockers. Use after physics-informal-derivation-expander and before Lean or SymPy drafting.
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

# Physics Informal Derivation Readiness Reviewer

Use this skill after informal elicitation and expansion. It decides whether the
expanded informal derivation is ready to become a formalization prompt.

Hook:
- `physics.informal.review`

## Review Criteria

Fail or block when:

- no source-anchored derivation steps exist;
- generated support is unlabeled or unreviewed;
- a formalization-critical step lacks law or rule provenance;
- assumptions, dimensions, units, frames, or regimes are missing where the
  source physics requires them;
- expected grounding is missing for formalization-critical steps;
- dependency-resolution handoff is missing when expected grounding calls for
  intermediate definitions, background results, bridge lemmas, or algebraic
  cores;
- the target statement shape changed during expansion;
- hard derivation gaps need proof-expansion web support but have no web-support
  packet or explicit unresolved status.

Pass only when the expansion can be handed to dependency resolution, source-line
translation, mathlib web grounding, unit analysis, and backend drafting without
hiding uncertainty.

Prefer `scripts/review_physics_informal_derivation_readiness.py` for a
deterministic readiness check.
