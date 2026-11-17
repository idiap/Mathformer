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

# Lean Cross-File Concept Consistency Prompts

When using this skill generatively, inspect the concept families it reports:

- Are repeated local definitions really the same concept?
- Do different signatures reflect genuine domain differences or accidental
  drift?
- Should the concept move into MathformerLib?
- Is each generated theorem using the most canonical available declaration?

Do not merge declarations just because their names resemble each other. Require
compatible statements, compatible assumptions, and a clear reuse path.
