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

# Lean Syntactic Correctness Critique

## Aspect Prompt

```text
Check whether the Lean code is syntactically valid and elaborates in the target project. Treat parser errors, unknown identifiers, invalid imports, type mismatches, failed typeclass synthesis, invalid projections, unexpected tokens, and unresolved required goals as failures. If concrete Lean diagnostics are provided, ground the judgement in those diagnostics. Do not treat semantic plausibility as syntactic success.
```

## Required Evidence

- Lean file or Lean code.
- `lake env lean` / hard-critique result when available.
- Error log lines, line numbers, and categories when available.

## Output Checklist

- `Judgement: True` only when local Lean diagnostics show success or no syntactic/typechecking issue is found in supplied evidence.
- `Judgement: False` when Lean reports syntax, elaboration, import, name-resolution, or type errors.
- Mention whether `sorry`/`axiom` placeholders remain, but do not classify them as syntax failures unless they cause Lean failure.
