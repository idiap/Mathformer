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

# Reflective Refinement Packet

The packet is an advisory artifact. It may propose prompt or skill changes, but
it must not apply them automatically.

Required top-level fields:

- `ok`: whether the observation gate passes.
- `summary`: suite, cases, metrics, and opportunity counts.
- `baseline_comparison`: regressions against previous successful cases.
- `reference_free_monitor`: optional benchmark-free critic-measure packet used
  to set monotonic score floors and hard-risk ceilings.
- `monotonicity_contract`: commands and acceptance checks every proposed change
  must satisfy.
- `opportunities`: localized candidate improvements.
- `gate_decision`: normalized pass/warn/fail result.
- `todos`: actionable follow-up items derived from opportunities.

Opportunity fields:

- `id`
- `priority`
- `owner_skill`
- `target_surface`
- `evidence`
- `proposed_refinement`
- `monotonicity_gate`
- `invalidation_risk`
- `apply_mode`

Baseline shape:

```json
{
  "suite": "wiki_level_latex_to_lean",
  "successful_cases": {
    "wiki_contrapositive": true
  },
  "metrics": {
    "compatibility_score": 100,
    "case_count": 5
  }
}
```

The observer can write a baseline snapshot with `--write-baseline` after a clean
run. Future runs compare against that file.

Reference-free monitor packets should come from
`skills/rfde/reference-free-critic-monitor/scripts/monitor_reference_free_critics.py`.
They are not correctness proofs; they are internal non-regression evidence for
prompt or skill changes when no benchmark or gold formalization is available.
