---
name: physics-informal-derivation-expander
description: Expand terse informal physics derivations into source-anchored step-by-step derivation packets before formalization, preserving physical laws, assumptions, units, dimensions, frames, regimes, generated-support labels, and unresolved blockers. Use after physics-informal-derivation-elicitor and before Lean or SymPy drafting.
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

# Physics Informal Derivation Expander

Use this skill to turn a terse physics answer into a fuller informal derivation
that can be inspected before any formal backend sees it.

Hook:
- `physics.informal.expand`

## Workflow

1. Read the source packet and elicitation packet.
2. Split the derivation into source-anchored steps.
3. For each step record:
   - input expression or physical state;
   - output expression or target subclaim;
   - physical law or mathematical rule;
   - assumptions and side conditions;
   - dimension/unit checks;
   - expected formal grounding role: Mathlib carrier, definition, background
     result, bridge lemma, source-law support, calculus support, or algebraic
     core;
   - whether the step is literal source, source-supported, generated support,
     or blocked.
4. Expand missing transitions only as generated support unless the source
   explicitly states them.
5. Send hard or research-level gaps to proof-expansion support and web
   research before treating them as usable.
6. Hand the expanded packet to `physics-informal-derivation-readiness-reviewer`
   and then to dependency resolution, physics law grounding, line translation,
   mathlib web grounding, and backend drafting.
7. Preserve a backend-ready `commentary_header` view containing the original
   informal statement, the full informal derivation, and an alignment table from
   each informal step to the formal object that should carry it.

Prefer `scripts/expand_informal_physics_derivation.py` for a deterministic
expansion skeleton.

## Completion Bar

An expanded informal derivation is ready for formalization only when every
formalization-critical step has source anchors, explicit assumptions, law or
rule provenance, dimension/unit status, expected formal grounding, and a support
label. Unsupported generated steps must remain visible blockers or web-support
tasks.
The packet must be rich enough for the Lean or SymPy drafter to place the full
commentary in a header without reconstructing it from memory, including the
backend-specific alignment from informal steps to formal declarations or
executable SymPy trace steps.
For Lean, the packet must also steer the background dependency plan: expected
definitions, Mathlib-native surfaces, support lemmas, bridge lemmas, and
algebraic cores should be explicit before the type-system builder runs.
