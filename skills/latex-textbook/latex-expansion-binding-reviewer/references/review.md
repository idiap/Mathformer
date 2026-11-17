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

# LaTeX Expansion Binding Review

## Runtime Agent

`LatexExpansionBindingReviewAgent` checks the output of `LatexExpansionAgent`
before the statement is passed to `AutoformalizationAgent`.

## Checklist

- Every symbol introduced in the expansion has a clear binder, domain, or dependency.
- Free variables in the conclusion are bound or declared in the hypotheses.
- Quantifier order matches the original theorem's dependency structure.
- Indices, subscripts, parameters, and overloaded notation remain consistent across assumptions and conclusion.
- Definitions expanded from the source do not silently reuse variables with changed meaning.

## Response Contract

```text
%%%%%%%%%%
Explanation: Concrete explanation of any dangling, ambiguous, or consistently scoped symbols.
Judgement: True
%%%%%%%%%%
```

Use `Judgement: False` when binder ambiguity or variable drift makes the expansion unsafe
for initial drafting.
