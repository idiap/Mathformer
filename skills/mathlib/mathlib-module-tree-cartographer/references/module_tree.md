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

# Mathlib Module Tree

## Node Kinds

- `prefix`: internal namespace-like module prefix without a concrete `.lean` file.
- `module`: concrete importable module with a `.lean` file.
- `module_prefix`: concrete importable module that also has descendants.

## Selection Rules

- Prefer child prefixes whose names match the mathematical domain.
- Inspect siblings before leaving a parent prefix.
- Use leaf counts as a breadth signal, not a quality score.
- Confirm concrete imports with Lean before relying on them in generated code.
