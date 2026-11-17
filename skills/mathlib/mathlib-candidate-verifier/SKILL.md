---
name: mathlib-candidate-verifier
description: Verify ranked Lean mathlib declaration candidates with `lake env lean` `#check` calls and capture checker errors. Use when candidate declarations from mathlib concept mapping must be confirmed before prompt injection, proof translation, or autoformalization refinement.
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

# Mathlib Candidate Verifier

## Purpose

Use this skill after candidate discovery when exact Lean availability matters. It reruns the
mathlib mapping script with `--verify-checks`, schedules bounded `#check` calls, and records
`check_ok` plus checker diagnostics for top candidates.

Shared runtime owner:
- `../informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py`

## Workflow

1. Start from the same proof text or explicit concept list used for mapping.
2. Set `--lean-workdir` to the project root where `lake env lean` works.
3. Bound verification with `--verify-max-concepts` and `--verify-max-candidates`.
4. Prefer `--json` so downstream agents can filter on `check_ok`.
5. Keep candidates only when they both typecheck and match the intended informal meaning.
6. Send verified output to `mathlib-concept-coverage-reviewer` and `mathlib-api-compatibility-planner` before drafting.

## Commands

Verify top candidates from proof text:

```bash
python3 skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py \
  --proof-file inputs/proof.txt \
  --verify-checks \
  --lean-workdir . \
  --top-k 10 \
  --top-modules 12 \
  --verify-max-concepts 6 \
  --verify-max-candidates 3 \
  --json
```

Verify explicit concepts:

```bash
python3 skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py \
  --concept commutative \
  --concept bijective \
  --verify-checks \
  --lean-workdir . \
  --verify-max-candidates 5 \
  --json
```

Append reasoning trace:

```bash
python3 skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py \
  --proof-file inputs/proof.txt \
  --verify-checks \
  --lean-workdir . \
  --reasoning-log-file artifacts/reasoning/concept-mapping.jsonl \
  --json
```

## Notes

- Verification is batched through the local `.elan` toolchain.
- `check_errors` should be preserved when a candidate fails; those errors often identify bad imports or unavailable declarations.
- Use `mathlib-concept-candidate-mapper` when verification is not needed.
