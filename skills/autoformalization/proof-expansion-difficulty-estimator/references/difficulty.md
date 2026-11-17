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

# Proof Expansion Difficulty

## Difficulty Bands

- `easy` (`0-34`): explicit local reasoning; expansion can proceed without web support.
- `moderate` (`35-59`): several definitions or lemmas must be unpacked; use local mathlib and source context first.
- `hard` (`60-79`): likely hidden theorem dependencies or dense analytic/probabilistic machinery; web support is recommended.
- `research` (`80-100`): named theorem, citation, or specialized proof technique likely needed; web support is required before expansion.

## Search Decision Rules

Recommend or require web support when a segment contains:

- citations, reference labels, or theorem names,
- "standard", "well-known", "clear", or "follows from" without details,
- specialized machinery outside the local proof text,
- ambiguous theorem hypotheses whose exact statement matters,
- high risk of expanding a statement into a non-equivalent theorem.

Do not search for purely syntactic binder cleanup, local notation, or explicit definitions
already available in the provided text.
