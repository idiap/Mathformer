---
name: theory-evolution-modeler
description: Build predictive state-space models for the evolution of an autoformalized theory under backends/lean/Mathformer/RFDE dynamics, including phase priors, metric priors, coupling assumptions, acceptance thresholds, and plausible parameter ranges. Use before simulation or when the paper needs a generative model of theory-growth trajectories.
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

# Theory Evolution Modeler

## Purpose

Use this skill to define a predictive model for how an autoformalization theory
evolves through phases. The model is not fitted truth; it is a plausible prior
over trajectories that can later be calibrated from RFDE runs.

## Model

Represent the run as a state-space process over RFDE metrics:

```text
M_t = (E,A,V,S,R,M,N,D,P,B,W)
```

Each phase has:

- target metric vector;
- gain rates toward targets;
- regression probabilities;
- cost profile;
- acceptance thresholds;
- coupling rules, such as grounding helping semantic shape and repair helping
  executability.
- instrumentation density and dashboard inspection rate when observability is
  part of the model.

The model emits parameters for relative-improvement deltas:

```text
Dhat_t^{q,up}, Dhat_t^{q,down}
```

where `q` ranges over RFDE metrics.

## Workflow

1. Choose a model preset:
   - `default-mathformer-theory`: one chapter-scale autoformalization run.
2. Build metric priors and phase targets.
3. Encode phase costs and expected durations.
4. Encode acceptance thresholds and protected metrics.
5. Mark monitor-derived parameters as empirical calibration candidates and
   hand-set parameters as simulated priors.
6. Include scenarios where observability improves before theorem success and
   where dashboard inspection detects legacy trace gaps.
7. Save the model JSON and pass it to `theory-evolution-simulator`.

## Command

```bash
python3 paper_skills/theory-evolution-modeler/scripts/build_theory_evolution_model.py \
  --preset default-mathformer-theory \
  --output artifacts/theory_evolution/default_model.json \
  --json
```

## Guardrails

- Do not present simulated parameters as measured system performance.
- Use simulated outputs as priors, stress tests, or visualization scaffolds.
- Keep protected metrics explicit: executability, anchor coverage, anchor
  validity, realness, and non-vacuity.
