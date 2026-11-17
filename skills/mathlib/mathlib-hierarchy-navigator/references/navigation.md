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

# Mathlib Hierarchical Navigation

## Traversal Strategy

1. Start at `Mathlib` or a likely top-level domain.
2. Prefer prefixes with many relevant leaf modules over isolated name hits.
3. Inspect sibling modules before jumping to unrelated domains.
4. Open concrete modules to read imports and declarations.
5. Feed promising imports and declarations into verification before drafting.

## Output Shape

- `focus`: current prefix or module.
- `ancestors`: root-to-focus path.
- `children`: immediate child prefixes/modules and leaf counts.
- `siblings`: alternatives under the same parent.
- `module`: imports and declarations when the focus is a concrete module.
- `query_results`: module and declaration matches organized under the hierarchy.
