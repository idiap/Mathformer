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

# Lean Mathlib Alignment Critique

## Aspect Prompt

```text
Check whether the Lean formalization is aligned with mathlib-native objects and APIs. Return False or warning-level findings when it duplicates concepts already available in mathlib, uses broad or missing imports, ignores verified candidate declarations, introduces parallel abstraction routes, uses local predicates where native predicates exist, or lacks operational lemmas connecting assumptions to reusable APIs.
```

## Finding Categories

- `native_object_reuse`: prefer existing mathlib notions.
- `verified_candidate_usage`: use checked declarations/imports when relevant.
- `duplicate_abstraction`: avoid local predicates duplicating library concepts.
- `import_hygiene`: avoid broad or missing imports.
- `api_operability`: add bridge lemmas or usable assumptions.

## Output Checklist

- Name the mathlib-native concepts that should be reused.
- Name any local definitions that duplicate library concepts.
- Identify missing or excessive imports.
- Return a binary judgement or warning-level pass with concrete suggestions.
