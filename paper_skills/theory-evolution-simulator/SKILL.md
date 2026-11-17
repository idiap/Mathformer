---
name: theory-evolution-simulator
description: Simulate predictive Mathformer theory-evolution trajectories from phase/metric priors, compute relative-improvement delta signatures, estimate plausible parameters from simulated outputs, and render trajectory plots. Use when exploring expected RFDE dynamics before enough empirical runs exist.
---

<!--
File Documentation

Motivation:
  Capture the research-paper production workflow as auditable agent skills and helper scripts.

Intent:
  Separate scientific writing, evidence mapping, figure generation, and theory-evolution modeling roles.

Function:
  Provides structured guidance and automation for paper-oriented artifacts.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Theory Evolution Simulator

## Purpose

Use this skill after `theory-evolution-modeler` produces a model JSON. It
simulates ensembles of RFDE metric trajectories, derives plausible parameters
from the simulated outputs, and renders plots for paper/model development.

## Workflow

1. Read a theory-evolution model JSON.
2. Simulate an ensemble of trajectories with a fixed random seed.
3. Compute per-transition:
   - signed metric deltas;
   - relative improvements `Dhat^{q,up}`;
   - relative regressions `Dhat^{q,down}`;
   - cost-normalized velocity `eta^S`.
4. Estimate plausible parameters from the simulated ensemble:
   - phase duration;
   - phase cost;
   - per-metric relative improvement velocity;
   - regression rate;
   - probability of terminal complete/draft/blocked status.
5. Mark each output as simulated or observational depending on the evidence
   source.
6. Include observability scenarios in which instrumentation improves before
   backend success and dashboard inspection reveals missing trace stages.
7. Emit JSON, Markdown, CSV, and SVG outputs.
8. When comparing alternative mechanism hypotheses, run the simulation suite and
   render scenario comparison plots.

## Command

```bash
python3 paper_skills/theory-evolution-simulator/scripts/simulate_theory_evolution.py \
  --model artifacts/theory_evolution/default_model.json \
  --runs 64 \
  --seed 7 \
  --output-dir artifacts/theory_evolution/default_simulation \
  --json
```

For a multi-regime comparison suite:

```bash
python3 paper_skills/theory-evolution-simulator/scripts/run_theory_evolution_simulation_suite.py \
  --model artifacts/theory_evolution/default_model.json \
  --runs 128 \
  --seed 17 \
  --output-dir artifacts/theory_evolution/simulation_suite \
  --json
```

## Guardrails

- Treat outputs as plausible priors unless calibrated against real RFDE runs.
- Keep the random seed in the report.
- Do not infer correctness from simulated convergence.
- Prefer ensemble summaries over single-run narratives.
