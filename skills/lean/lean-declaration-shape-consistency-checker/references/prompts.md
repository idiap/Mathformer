<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

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

# Lean Declaration Shape Consistency Prompts

When using this skill generatively, ask the critic to compare only the shape of
the claim:

- Does an "if and only if" source claim become an `Iff` or equivalent theorem?
- Does an existence source claim have an existential, witness record, subtype,
  certificate, or explicit representation note?
- Does uniqueness remain visible as unique existence, equality, or a documented
  uniqueness structure?
- Does an implication or conditional statement expose its hypotheses?

Do not accept a repair that only weakens the natural-language annotation. The
repair should usually change the Lean statement or add a precise generated note
that documents a deliberate representation boundary.
