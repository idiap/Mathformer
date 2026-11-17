---
name: lean-consistency-report-orchestrator
description: Run the unified Lean reference-free consistency loop, coordinating compilation, realness, informalization, declaration-shape, internal/reverse informal consistency, non-vacuity, cross-file concept, and mathlib-grounding critics into one report. Use after saving an autoformalized Lean file or before MathformerLib promotion.
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

# Lean Consistency Report Orchestrator

Use this skill when Lean autoformalization files should be tested for
reference-free consistency by running all deterministic and semi-deterministic
critics as one controlled loop.

## Purpose

This skill coordinates the Lean consistency stack:

- Lean compilation, optionally per file.
- Lean comment and source-annotation hygiene.
- Artifact realness.
- Lean-to-informal extraction.
- Declaration-shape consistency.
- Informal proof internal consistency.
- Reverse informal consistency against the Lean artifact.
- Non-vacuity consistency.
- Cross-file concept consistency.
- Mathlib grounding maximization.
- Reference-free critic monitoring.

## When To Run

- After an autoformalized Lean file is saved.
- Before declaring a theorem fully autoformalized.
- Before MathformerLib promotion.
- After changes to critic prompts, hooks, or workflow gates.

## Procedure

1. Run `scripts/run_lean_consistency_report.py` on the target Lean files.
2. Use `--run-lean-check` for final acceptance or whenever compilation has not
   already been checked.
3. Inspect the per-layer `ok` values and high-severity findings.
4. Repair the earliest failing layer first, then re-run the full report.
5. Persist the report under `artifacts/lean_consistency/latest.json` so
   reference-free critic trends can be compared monotonically.

## Command

```bash
python3 skills/lean/lean-consistency-report-orchestrator/scripts/run_lean_consistency_report.py \
  --lean-file backends/lean/Mathformer/AutoformalizedExample.lean \
  --run-lean-check \
  --expect-ok --json
```

## Output Contract

The JSON report contains:

- `ok`: true iff all required layers pass.
- `summary.consistency_score`: aggregate reference-free score.
- `layers`: ordered layer results with commands, summaries, and findings.
- `blocking_layers`: layer ids that failed required gates.
- `output_files`: paths to persisted reports.

## Hook

Canonical hook id: `consistency.unified_report`.
