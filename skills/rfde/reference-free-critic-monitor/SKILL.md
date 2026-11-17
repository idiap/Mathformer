---
name: reference-free-critic-monitor
description: Compute and compare benchmark-free critic measures for Lean artifacts, tracking monotonic improvement without requiring a gold formalization or external benchmark.
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

# Reference-Free Critic Monitor

## Purpose

Use this skill after Lean execution, critique-suite passes, or artifact saving
when the workflow needs an internal measurement record that does not rely on a
benchmark or gold formalization. The monitor converts critic outputs, Lean file
structure, semantic source anchors, non-vacuity signals, placeholder counts,
and mathlib-grounding signals into a monotonic snapshot. It also builds a
reference-free evolution view over the accepted baseline, ledger history, and
current snapshot, including trend statistics and plot artifacts.

This skill is an evaluator of process evidence, not a proof of mathematical
correctness. Its job is to make regressions visible and to prevent a refinement
from looking better by only satisfying one critic while weakening source
alignment, theorem substance, or artifact realness.

Runtime:
- `scripts/monitor_reference_free_critics.py`
- hook: `critique.reference_free_monitor`

## Workflow

1. Collect the generated Lean artifact, workflow report, and reasoning log when
   available.
2. Compute reference-free measures:
   - prover health,
   - placeholder freedom,
   - logical non-vacuity,
   - semantic/source-anchor coverage,
   - mathlib grounding,
   - critic agreement,
   - artifact substance.
3. Compare the snapshot against an optional accepted baseline.
4. Apply anti-gaming checks: theorem/source-anchor counts must not silently
   shrink while aggregate scores improve.
5. Compute formalization-evolution statistics across baseline, ledger, and
   current snapshot:
   - score deltas and slopes,
   - risk-count deltas,
   - monotonicity/regression counts,
   - latest score/risk summaries.
6. Emit SVG, CSV, and JSON evolution artifacts unless `--no-evolution-plots` is
   requested.
7. Emit a monitor packet with scores, regressions, improvements, limitations,
   evolution statistics, plot paths, and self-explanatory TODOs.
8. Append the snapshot to a ledger only after the user or workflow accepts the
   gate result.
9. Feed the monitor packet into `autoformalization-reflective-refinement-loop`
   before changing prompts or skills.

## Monotonicity Policy

The accepted trend is monotonic when:

- every score with `nondecreasing` orientation stays at or above its accepted
  baseline floor,
- every risk count with `nonincreasing` orientation stays at or below its
  accepted baseline ceiling,
- no previously present theorem-like surface disappears without an explicit
  source-preservation justification,
- source-anchor coverage does not drop while critic agreement rises,
- `sorry`, `admit`, target `axiom`, unresolved `exact?`, and scaffold markers
  do not increase.

The monitor intentionally separates these local signals from benchmark metrics.
ProofNet or other benchmarks can be used as external evidence, but they are not
required for this gate.

## Command

```bash
python3 skills/rfde/reference-free-critic-monitor/scripts/monitor_reference_free_critics.py \
  --lean-file backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean \
  --report-file artifacts/autoformalization/latest.report.json \
  --reasoning-log-file artifacts/autoformalization/reasoning-log.jsonl \
  --baseline-file artifacts/reference_free_critic_monitor/baseline.json \
  --output-file artifacts/reference_free_critic_monitor/latest.json \
  --evolution-output-dir artifacts/reference_free_critic_monitor/evolution \
  --json
```

The default evolution output directory contains:

- `formalization_evolution.svg`
- `formalization_evolution.csv`
- `formalization_evolution.json`

Create or refresh an accepted baseline only after the current packet is
reviewed:

```bash
python3 skills/rfde/reference-free-critic-monitor/scripts/monitor_reference_free_critics.py \
  --lean-file backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean \
  --write-baseline \
  --baseline-file artifacts/reference_free_critic_monitor/baseline.json \
  --json
```

## References

- Read `references/reference_free_monitor.md` before changing score weights,
  monotonicity rules, or anti-gaming checks.
