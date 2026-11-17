---
name: lean-compile-checker
description: Run concrete Lean4 compile checks with `lake env lean` for target `.lean` files and capture compiler errors. Use when the task is theorem-prover health, syntax/typecheck validation, final Lean checking, or structured compile diagnostics rather than broader mathlib compatibility review.
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

# Lean Compile Checker

## Purpose

Use this skill for concrete Lean compiler health. It owns the raw `lake env lean` check
surface and the structured `lake_check` portion of compatibility reports.

Use `lean-execution-runner` for the execution hook that runs immediately after initial
formalization delivery. Use this skill to interpret or package compiler diagnostics.

Shared runtime owner:
- `../mathlib-compatibility-auditor/scripts/check_mathlib_compat.py`

## Workflow

1. Confirm the target is a `.lean` file.
2. Run from the project root or pass the correct Lake workdir.
3. Capture return code, Lean errors, and stderr/stdout needed for refinement.
4. Use the structured auditor command when a JSON report or reasoning-log entry is needed.
5. Use `lean-execution-runner` when the task is the post-draft execution act itself.
6. Use `mathlib-abstraction-auditor` when the task is library alignment, documentation hygiene, placeholder hygiene, or scoring.

## Commands

Direct Lean check:

```bash
lake env lean backends/lean/Mathformer/AutoformalizedExample.lean
```

Structured compile check report:

```bash
python3 skills/mathlib/mathlib-compatibility-auditor/scripts/check_mathlib_compat.py \
  --lean-file backends/lean/Mathformer/AutoformalizedExample.lean \
  --run-lake-check \
  --lake-workdir . \
  --json
```

Structured compile check with reasoning trace:

```bash
python3 skills/mathlib/mathlib-compatibility-auditor/scripts/check_mathlib_compat.py \
  --lean-file backends/lean/Mathformer/AutoformalizedExample.lean \
  --run-lake-check \
  --lake-workdir . \
  --reasoning-log-file artifacts/reasoning/lean-compile.jsonl \
  --json
```

## Output Focus

For refinement, preserve:

- `lake_check.ok`
- `lake_check.returncode`
- `lake_check.error_count`
- `lake_check.errors`
