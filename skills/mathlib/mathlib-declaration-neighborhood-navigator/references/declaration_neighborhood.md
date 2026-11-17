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

# Mathlib Declaration Neighborhoods

## Review Order

1. Imports in the focused module.
2. Declarations matching the target term.
3. Nearby declarations with related prefixes or suffixes.
4. Sibling modules under the same parent prefix.
5. Verification with `#check` before generated Lean relies on a name.

## Cautions

- Local declaration names may be namespace-qualified in Lean; verify the qualified name.
- A module containing a relevant declaration may still require a narrower import.
- Do not assume theorem direction from a declaration name alone; inspect the signature.
