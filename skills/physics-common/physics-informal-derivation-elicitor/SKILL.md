---
name: physics-informal-derivation-elicitor
description: Elicit missing informal physics derivation context before formalization, including target meaning, quantities, units, dimensions, frames, regimes, boundary conditions, side assumptions, physical laws, and unclear derivation transitions. Use before physics derivation expansion, Lean drafting, or SymPy drafting when the source derivation is terse or underspecified.
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

# Physics Informal Derivation Elicitor

Use this skill before formalization when a physics derivation is too terse to
translate safely. The goal is to make missing informal context explicit without
pretending generated support is source text.

Hook:
- `physics.informal.elicit`

## Workflow

1. Start from the source question, answer, and source packet when available.
2. Identify what must be known before formalization:
   - target relation and intended logical shape;
   - physical quantities, dimensions, units, vectors, fields, and operators;
   - frames, sign conventions, gauges, regimes, approximations, and domains;
   - initial, boundary, smoothness, positivity, and nonzero conditions;
   - physical laws, constitutive equations, conservation principles, and
     transformation rules;
   - gaps between displayed equations;
   - expected formal grounding: Mathlib-native carriers, intermediate
     definitions, background results, bridge lemmas, source-law support, and
     compact algebraic cores that should exist before the target theorem.
3. Produce an elicitation packet with source-backed facts, missing questions,
   generated-support candidates, and blockers.
4. Ask the user only for genuinely missing context when the source cannot
   decide it. If proceeding without user input, label assumptions as
   generated-support or blocked.
5. Hand the packet to `physics-informal-derivation-expander`, then to source
   anchoring, proof-expansion web support, dependency resolution, mathlib web
   grounding, and backend formalization.

Prefer `scripts/build_physics_informal_elicitation_packet.py` for the
deterministic packet skeleton.

## Guardrails

- Do not silently add physical assumptions to make the derivation easier.
- Do not collapse vector, field, operator, or dimensioned claims into raw scalar
  algebra.
- Every elicited item must be labeled `source_backed`, `generated_support`,
  `user_needed`, or `blocked`.
- Expected grounding must be stated before Lean typing begins. Missing expected
  grounding is a readiness blocker for physics-bearing derivations.
- Missing units, frames, regimes, or law provenance are blockers for complete
  formalization unless explicitly irrelevant to the source claim.
