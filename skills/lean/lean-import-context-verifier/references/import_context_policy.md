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

# Import Context Policy

## Verification Rule

Expected declarations should be checked under the intended import set, not only
under broad `import Mathlib`.

## Blocking In Final Artifacts

- `import Mathlib` without an explicit waiver.
- Missing expected imports declared by the fixture or import planner.
- Expected declarations that fail `#check` under the intended import set.
- Generated Lean that compiles only when the import context is broadened.

## Draft Handling

Drafts may temporarily use broad imports to locate APIs, but the next hook must
plan and verify a narrower import set before the result is counted complete.
