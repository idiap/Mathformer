---
name: mathlib-concept-candidate-mapper
description: Map informal proof text or explicit mathematical concepts to ranked Lean mathlib declaration candidates and relevant import modules without running Lean verification. Use when generating mathlib alignment hints, candidate theorem names, source references, or module navigation lists for autoformalization.
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

# Mathlib Concept Candidate Mapper

## Purpose

Use this skill for discovery and ranking only. It extracts or accepts mathematical concepts,
loads the local mathlib declaration index, ranks declarations and modules, and emits import
hints plus source references. It does not validate candidates with Lean.

Shared runtime owner:
- `../informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py`

## Workflow

1. Ensure the project has a local mathlib checkout (`lake update` / `lake build` if needed).
2. Provide either informal proof text or repeated explicit `--concept` values.
3. Run without `--verify-checks` to keep this phase fast and deterministic.
4. Prefer JSON output for downstream prompt conditioning.
5. Hand the highest-value candidates to `mathlib-candidate-verifier` when exact `#check` status matters.
6. Hand mapped/verified output to `mathlib-concept-coverage-reviewer` before drafting when maximum mathlib compatibility is required.
7. Use `mathlib-hierarchy-navigator` when relevant modules need parent/child/sibling context before choosing imports.

## Commands

Map from informal proof text:

```bash
python3 skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py \
  --proof-file inputs/proof.txt \
  --top-k 10 \
  --top-modules 12 \
  --show-modules 4
```

Map from explicit concepts:

```bash
python3 skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py \
  --concept commutative \
  --concept associative \
  --concept bijective \
  --top-modules 8
```

JSON output for workflow handoff:

```bash
python3 skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py \
  --proof-file inputs/proof.txt \
  --top-k 10 \
  --top-modules 12 \
  --json
```

Append reasoning trace:

```bash
python3 skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py \
  --proof-file inputs/proof.txt \
  --top-k 10 \
  --top-modules 12 \
  --reasoning-log-file artifacts/reasoning/concept-mapping.jsonl \
  --json
```

## Output Fields

In JSON mode each concept includes:

- `relevant_modules`: ranked module navigation rows with imports and source refs.
- `candidates`: ranked declaration rows with `qualified_name`, `import`, `source_path`, `source_ref`, and `source_excerpt`.
