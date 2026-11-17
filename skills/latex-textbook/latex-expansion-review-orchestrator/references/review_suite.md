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

# LaTeX Expansion Review Suite

## Hook Order

The suite runs between prerequisite expansion and initial formal drafting:

1. `preformalization.expand`
2. `preformalization.review.suite`
3. `preformalization.review.completeness`
4. `preformalization.review.bindings`
5. `mathlib.discovery` / `mathlib.verify`
6. `draft.initial`

## Reasoning-Log Events

- `latex_expansion_review_suite_start`
- `latex_expansion_completeness_review_start`
- `latex_expansion_completeness_review_complete`
- `latex_expansion_completeness_review_error`
- `latex_expansion_completeness_review_skipped`
- `latex_expansion_binding_review_start`
- `latex_expansion_binding_review_complete`
- `latex_expansion_binding_review_error`
- `latex_expansion_binding_review_skipped`
- `latex_expansion_review_suite_complete`
- `latex_expansion_review_suite_skipped`

## Gate Semantics

`latex_expansion_review_passed` is:

- `True` when every configured reviewer returns `Judgement: True`,
- `False` when any configured reviewer errors or returns `False` or an unknown judgement,
- `None` when no expanded statement or no configured reviewer result is available.

The default runtime records the gate result but does not abort legacy workflows.
