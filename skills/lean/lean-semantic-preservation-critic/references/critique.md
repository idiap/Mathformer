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

# Lean Semantic Preservation Critique

## Aspect Prompt

```text
Check whether the Lean formalization preserves the semantic meaning of the original informal mathematical statement or proof. Compare assumptions, domains, quantifier order, definitions, theorem direction, equivalence versus implication, conclusion strength, dependency usage, and any source-aligned Lean doc comments. Return False if the Lean artifact changes the claim materially, drops a core hypothesis or conclusion, proves a different theorem, narrows/broadens the domain without justification, or hides the original content behind unrelated placeholders.
```

## Required Evidence

- Original informal statement or proof.
- Generated Lean code.
- Core statement annotations or dependency context when available.
- Mathlib alignment hints when they affect representation choices.

## Output Checklist

- Identify the source claim in one sentence.
- Identify the Lean claim in one sentence.
- List semantic mismatches with assumption/conclusion references.
- Return a binary judgement.
