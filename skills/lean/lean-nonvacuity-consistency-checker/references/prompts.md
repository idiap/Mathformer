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

# Lean Nonvacuity Consistency Prompts

Ask the critic to inspect whether a compiled theorem is materially stronger
than its assumptions:

- Is the conclusion exactly one of the hypotheses?
- Does a false hypothesis make the theorem vacuous?
- Is the declaration an axiom or an unproved interface boundary?
- Does the proof use only `trivial`, `rfl`, or `exact h` for a theorem that was
  supposed to encode a substantive source result?
- If the result is intentionally an accessor or wrapper, is that documented in
  a generated note?

The preferred repair is to expose the real mathematical dependency structure,
not to hide vacuity behind weaker prose.
