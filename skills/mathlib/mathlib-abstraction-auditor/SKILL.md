---
name: mathlib-abstraction-auditor
description: Audit Lean formalizations for mathlib-native object reuse, abstraction-boundary discipline, theorem-layer shape, API operability, documentation hygiene, placeholders, thin wrappers, compatibility scoring, and strict merge gates. Use when reviewing Lean files for library alignment rather than just compiling them.
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

# Mathlib Abstraction Auditor

## Purpose

Use this skill for heuristic compatibility and design review of Lean formalization artifacts.
It owns mathlib-native alignment, custom abstraction detection, placeholder/documentation
hygiene, artifact-substance checks, compatibility scoring, and strict gate behavior.

Shared runtime owner:
- `../mathlib-compatibility-auditor/scripts/check_mathlib_compat.py`

## Workflow

1. Run the auditor on the target Lean file without `--run-lake-check` for a fast design scan.
2. Fix `high` findings first, then `medium`, then useful `low` findings.
3. Prefer mathlib-native objects and one explicit abstraction boundary for genuinely missing notions.
4. Track `axiom`, `sorry`, missing doc comments, broad imports, and thin wrapper ratios.
5. Add `--strict` for CI/merge gates where high-severity findings should fail.
6. Add `--run-lake-check` only when compile health also belongs in the same report; pure compiler work belongs to `lean-compile-checker`.
7. When placeholders, target `axiom`s, mock markers, or scaffold-only complete claims remain, run `autoformalization-result-realness-verifier` and block final completion.
8. When score targets fail, route the findings through `mathlib-compatibility-loop-orchestrator` for another compatibility-focused cycle.

## Commands

Basic text report:

```bash
python3 skills/mathlib/mathlib-compatibility-auditor/scripts/check_mathlib_compat.py \
  --lean-file backends/lean/Mathformer/AutoformalizedHilleYosida.lean
```

JSON report for pipelines:

```bash
python3 skills/mathlib/mathlib-compatibility-auditor/scripts/check_mathlib_compat.py \
  --lean-file backends/lean/Mathformer/AutoformalizedSazonov.lean \
  --json \
  --output artifacts/compatibility/sazonov.compat.json
```

Append reasoning trace:

```bash
python3 skills/mathlib/mathlib-compatibility-auditor/scripts/check_mathlib_compat.py \
  --lean-file backends/lean/Mathformer/AutoformalizedHilleYosida.lean \
  --reasoning-log-file artifacts/reasoning/mathlib-compat.jsonl \
  --json
```

Fail CI when severe findings exist:

```bash
python3 skills/mathlib/mathlib-compatibility-auditor/scripts/check_mathlib_compat.py \
  --lean-file backends/lean/Mathformer/AutoformalizedHilleYosida.lean \
  --strict
```

## References

- Read `references/mathlib_abstraction_checklist.md` when interpreting findings or planning fixes.
