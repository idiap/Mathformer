---
name: reference-free-descriptive-evaluator
description: Build trajectory-first Reference-Free Descriptive Evaluation (RFDE) reports, metrics, visual dashboards, claim ledgers, obligation ledgers, state/action/transition models, phase-transition models, trajectory diagnostics, and cost-normalized progress summaries from Mathformer reasoning logs and artifact reports. Use after autoformalization, consistency checks, source-anchor checks, or agentic workflow runs when no gold reference output is available.
---
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

# Reference-Free Descriptive Evaluator

## Purpose

Use this skill after workflow artifacts exist and before final interpretation or
documentation. It evaluates the reasoning trajectory without requiring a gold
formalization or benchmark answer. The primary object is the trajectory model:
states, actions, transitions, phase segments, loops, dynamics predicates,
phase transitions, convergence conditions, and temporal/generative/deterministic
cost surfaces. Static metrics remain secondary summaries of the terminal
artifact.

Hook:
- `evaluation.rfde_report`

Runtime:
- `scripts/build_rfde_report.py`

## Workflow

1. Collect available artifacts:
   - reasoning log JSONL,
   - workflow report/history/statistics,
   - Lean files,
   - line translation packets,
   - source-anchor drift reports,
   - realness reports,
   - unified consistency reports,
   - mathlib grounding or reference-free critic snapshots.
2. Build a task packet and compact trace summary.
3. Construct the trajectory model:
   - state sequence `s_0, ..., s_t`,
   - action sequence with phase, hook, skill, action kind, and source type,
   - transition sequence with observed metric deltas and cost-normalized
     progress,
   - phase segments,
   - phase transitions with kind, trigger, confidence, irreversibility pressure,
     protected-metric regressions, and order-parameter deltas,
   - repeated-hook and critic-repair-gate loop candidates,
   - convergence, plateau, oscillation, phase-transition, and
     under-instrumentation predicates.
4. Extract claim and obligation ledgers.
5. Score RFDE metric surfaces, Mathformer-specialized metrics, and trajectory
   metrics.
6. Evaluate hard gates, including the trajectory-presence gate.
7. Detect trajectory diagnostics such as grounding gain, drift risk, obligation
   closure, plateau, costly cycling, and unsupported assertion risk.
8. Emit:
   - `rfde_report.json`,
   - `rfde_report.md`,
   - `rfde_dashboard.html`,
   - `trajectory_timeline.html`,
   - `metrics_timeseries.json`,
   - `trajectory_model.json`.
9. Treat RFDE as descriptive: it explains why a run is strong, partial,
   blocked, or wasteful; it does not replace Lean, realness, or consistency
   gates.

## Command

```bash
python3 skills/rfde/reference-free-descriptive-evaluator/scripts/build_rfde_report.py \
  --run-id cbt-chapters-1-2 \
  --task "Autoformalize CBT chapters 1 and 2" \
  --lean-file backends/lean/Mathformer/AutoformalizedCBTChapter1.lean \
  --lean-file backends/lean/Mathformer/AutoformalizedCBTChapter2.lean \
  --reference-free-snapshot artifacts/reference_free_critic_monitor/latest.json \
  --output-dir artifacts/rfde/cbt-chapters-1-2 \
  --expect-ok \
  --json
```

## Acceptance Rules

The RFDE report is acceptable when:
- the JSON report contains task packet, observation surfaces, claim ledger,
  obligation ledger, metrics, hard gates, diagnostics, cost, and a
  state/action/transition trajectory model;
- Markdown and HTML reports render the trajectory model before static metrics;
- `trajectory_timeline.html` shows the run through time with phase bands,
  phase-transition markers, loop arcs, action nodes, transition-duration bars,
  cumulative observed metrics, heatmap rows, phase segments, phase-transition
  tables, loops, and transition tables;
- the timeseries file contains final metrics plus state and transition
  timeseries;
- `trajectory_model.json` exists and contains states, actions, transitions,
  phase segments, phase transitions, dynamics predicates, convergence
  conditions, and temporal cost surfaces;
- hard gates and weak dimensions are explicit rather than hidden behind a single
  score;
- the script exits nonzero under `--expect-ok` if report construction fails.
