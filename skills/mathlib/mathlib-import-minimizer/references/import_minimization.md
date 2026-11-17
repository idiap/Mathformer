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

# Import Minimization Policy

## Final Rule

A final artifact should avoid broad `import Mathlib` unless there is an explicit
waiver. A compile-checked minimized import block is preferred.

## Conservative Behavior

- Text-only mode deduplicates and flags broad imports, but does not claim an
  import is unused.
- `--check-lean` mode may remove an import only after the file still compiles.
- If expected declarations are known, run `lean-import-context-verifier` after
  minimization.
