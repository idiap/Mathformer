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

# LaTeX Expansion Completeness Review

## Runtime Agent

`LatexExpansionCompletenessReviewAgent` checks the output of `LatexExpansionAgent`
before the statement is passed to `AutoformalizationAgent`.

## Checklist

- Every named concept used by the theorem is expanded or explicitly preserved as a named prerequisite.
- All hypotheses, domains, regularity/size/order assumptions, and side conditions from the original are present.
- The theorem direction, conclusion, and scope are unchanged.
- Extra assumptions are rejected unless they are logically required definitions already implicit in the source.
- The expansion is detailed enough that a Lean drafter can identify declarations, hypotheses, and goals.

## Response Contract

```text
%%%%%%%%%%
Explanation: Concrete explanation of missing, changed, or successfully preserved source content.
Judgement: True
%%%%%%%%%%
```

Use `Judgement: False` when the expansion should not be trusted for initial drafting on
completeness grounds.
