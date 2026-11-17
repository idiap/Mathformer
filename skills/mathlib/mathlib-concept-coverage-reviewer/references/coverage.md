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

# Mathlib Concept Coverage

## Status Values

- `verified`: at least one candidate declaration has `check_ok: true`.
- `checked_without_verified_candidate`: candidates were checked, but none passed.
- `candidate_unverified`: candidate declarations exist but were not checked.
- `module_only`: relevant modules exist but no declaration candidate is available.
- `unmapped`: no useful declaration or module candidate was found.

## Gate

The strict concept gate passes when:

- `total_concepts > 0`,
- every concept has status `verified`,
- every verified candidate has a usable import or qualified name.

When the gate fails, feed the gaps into `mathlib-api-compatibility-planner` and prefer
one explicit abstraction boundary for concepts not represented in mathlib.
