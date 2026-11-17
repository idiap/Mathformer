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

# Lean Logical Soundness Critique

## Aspect Prompt

```text
Check whether the Lean formalization is logically sound and non-vacuous as a representation of the intended theorem. Return False if the theorem is made true by contradictory assumptions, arbitrary predicates, unconstrained axioms that assert the target, unused abstract fields, irrelevant hypotheses, a conclusion disconnected from the source claim, or a placeholder interface presented as a completed theorem. Distinguish honest scaffold boundaries from unsound overclaims.
```

## Red Flags

- `axiom` or predicate declarations that encode the target conclusion directly.
- Hypotheses that imply `False` or make the theorem vacuous.
- Abstract properties with no laws or operational use.
- Equivalences stated over unconstrained predicates.
- Theorem names/comments claiming completion while the body is only scaffolding.

## Output Checklist

- State whether the Lean theorem has a meaningful non-vacuous target.
- Identify any assumption or abstraction that forces the claim.
- Identify whether placeholders are honest scaffolding or overclaiming.
- Return a binary judgement.
