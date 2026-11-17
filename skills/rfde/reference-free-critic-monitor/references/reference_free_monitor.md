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

# Reference-Free Critic Monitoring

## Method

The monitor estimates improvement without a benchmark by measuring independent
failure surfaces of the current formalization. It never claims that these
signals are complete correctness evidence. A packet is useful when it makes the
following question auditable:

> Did the next refinement improve or preserve every local correctness proxy
> that the previous accepted artifact satisfied?

The monitor is also an evolution instrument. It combines the accepted baseline,
the accepted snapshot ledger, and the current snapshot into a reference-free
formalization trajectory. That trajectory supports trend statistics and plots
without requiring a gold formalization.

## Measures

- `prover_health`: Lean/check/report evidence that the artifact elaborates.
- `placeholder_freedom`: absence of `sorry`, `admit`, unresolved `exact?`, and
  scaffold/mock markers.
- `logical_nonvacuity`: absence of target axioms, theorem statements that only
  prove `True`, contradiction-assumption shortcuts, or empty theorem surfaces.
- `semantic_anchor_coverage`: original-source and generated semantic comments
  attached near declarations.
- `mathlib_grounding`: use of explicit mathlib imports and native vocabulary,
  with broad `import Mathlib` treated as weaker evidence than narrow imports.
- `critic_agreement`: consistency among workflow summary booleans, critique
  pass reports, compatibility scores, and hard/soft critique log events.
- `artifact_substance`: theorem-like declaration surface, average theorem
  statement size, and proof-bearing declarations.

## Anti-Gaming Checks

- A composite score cannot mask an increase in placeholders, axioms, or
  unresolved tactics.
- Higher critic agreement cannot compensate for reduced semantic anchors.
- A smaller artifact is not automatically better; theorem-like declaration
  counts and original-source anchors must be preserved unless an explicit
  semantic-preservation review justifies removal.
- Broad imports can keep an artifact compiling, but they do not improve
  mathlib-grounding evidence.

## Packet Shape

Required top-level fields:

- `ok`
- `summary`
- `reference_free_snapshot`
- `measures`
- `monotonicity_comparison`
- `formalization_evolution`
- `method_notes`
- `todos`
- `gate_decision`

The accepted baseline should store only the snapshot, not the full packet, so
future comparisons are compact and stable.

## Evolution Outputs

When plots are enabled, the monitor writes three files:

- `formalization_evolution.svg`: score and risk trajectories for quick visual
  inspection;
- `formalization_evolution.csv`: tabular score/risk series for statistical
  analysis;
- `formalization_evolution.json`: timeline, statistics, and plot metadata.

The core evolution statistics are:

- observation count;
- score, risk, and structure metric counts;
- reference-free confidence delta and slope per step;
- score-regression and risk-regression event counts;
- latest scores and latest risks;
- per-metric first, last, min, max, delta, slope, monotonicity, improvement
  count, and regression count.
