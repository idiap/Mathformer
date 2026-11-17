<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Preserve a compact demonstration output for the reference-free monitor.

Intent:
  Explain how Mathformer reads formalization evolution without requiring a gold
  reference formalization.

Function:
  Summarizes the monitor output shape: score dimensions, risk counts, trend
  statistics, plots, and the refinement interpretation.

Maintenance Notes:
  Keep this summary aligned with the reference-free critic monitor schema and
  the tutorial's monitoring demonstration.
-->

# Reference-Free Monitor Evolution Demo

Target:

```text
Track whether a Lean formalization is improving when no gold Lean reference
exists.
```

The monitor treats formalization as a sequence of evidence states. Each accepted
state is a snapshot. A snapshot is not judged by resemblance to a hidden answer;
it is judged by local signals that should tighten over time.

## Core Scores

| Score | Meaning |
| --- | --- |
| `reference_free_confidence` | Aggregate confidence from local evidence |
| `prover_health` | Whether the prover-facing artifact is executable or structurally healthy |
| `placeholder_freedom` | Whether placeholders, admits, and unfinished markers are absent |
| `logical_nonvacuity` | Whether theorem shapes avoid trivial or target-restating claims |
| `semantic_anchor_coverage` | Whether formal declarations are tied to source-facing meaning |
| `mathlib_grounding` | Whether the artifact uses appropriate library concepts |
| `critic_agreement` | Whether independent critic dimensions agree on the artifact state |
| `artifact_substance` | Whether the file contains enough definitions, declarations, and evidence to inspect |

## Core Risks

| Risk | Meaning |
| --- | --- |
| `unresolved_proof_count` | Proof obligations or validation failures still open |
| `target_axiom_count` | Axioms that directly assume the intended target |
| `placeholder_marker_count` | `sorry`, `admit`, placeholder, or TODO-style proof markers |
| `trivial_statement_count` | Theorem shapes that are too weak or vacuous |
| `low_score_dimension_count` | Number of score dimensions below the acceptance threshold |

## Evolution Statistics

The monitor writes an evolution model with:

- `observation_count`: number of snapshots in the compared timeline;
- `reference_free_confidence_delta`: confidence change from first to latest
  snapshot;
- `reference_free_confidence_slope_per_step`: average confidence change per
  snapshot step;
- `score_regression_event_count`: score dimensions that moved in the wrong
  direction;
- `risk_regression_event_count`: risk dimensions that increased;
- per-metric first, last, minimum, maximum, delta, slope, improvement count, and
  regression count.

## Plot Interpretation

The generated SVG plot shows selected score trajectories and total risk bars.
Read it as a diagnostic view:

- rising score lines suggest stronger source grounding, non-vacuity, prover
  health, or artifact substance;
- shrinking risk bars suggest fewer unresolved proof or artifact-quality risks;
- flat curves suggest the latest refinement did not change the measured state;
- downward score movement or rising hard risk should become the next blocker to
  inspect.

## Generated Local Artifacts

Typical monitor runs write:

- `artifacts/reference_free_critic_monitor/latest.json`
- `artifacts/reference_free_critic_monitor/evolution/formalization_evolution.svg`
- `artifacts/reference_free_critic_monitor/evolution/formalization_evolution.csv`
- `artifacts/reference_free_critic_monitor/evolution/formalization_evolution.json`
- `artifacts/reference_free_critic_monitor/reasoning.jsonl`

The useful reading order is:

1. open `latest.json` for the current measured state;
2. open `formalization_evolution.svg` for the trajectory;
3. open `formalization_evolution.csv` for the numeric timeline;
4. open `formalization_evolution.json` for full statistics;
5. use the weakest score or newest regression as the next refinement target.
