---
name: mathlib-result-existence-checker
description: Deterministically check whether a theorem, lemma, or target result already exists before autoformalization by searching local mathlib candidates, the MathformerLib registry, and an official-source mathlib web-search plan. Use before drafting a new formalization, when deciding whether to reuse an existing declaration, or when duplicate-result risk must block autoformalization.
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

# Mathlib Result Existence Checker

## Purpose

Use this skill before generating a new Lean formalization for a named or recognizable
result. It checks whether the target is already present in:

- local mathlib search output,
- the local `MathformerLib` registry,
- a planned official-source web search over mathlib docs/source.

Hook:
- `mathlib.result_existence_search`

This skill is a gate. It must run before `draft.initial` unless a seed formalization is
explicitly provided and the workflow records a waiver.

## Workflow

1. Normalize the source theorem/result statement, expected theorem names, and important
   concepts.
2. Run `scripts/check_result_existence.py` with JSON output.
3. Interpret the gate:
   - `likely_existing`: stop drafting and reuse or inspect the existing declaration.
   - `candidate_overlap`: do not draft until candidates are manually or locally verified as
     non-duplicates.
   - `needs_web_confirmation`: run the web-search plan through official mathlib docs/source
     before drafting.
   - `not_found`: drafting is allowed only when web search is disabled by policy or was
     explicitly confirmed absent.
4. For web-found candidates, hand declarations back to local Lean verification before reuse.

## Commands

Check a theorem with expected names:

```bash
python3 skills/mathlib/mathlib-result-existence-checker/scripts/check_result_existence.py \
  --statement "Every compact metric space is complete and totally bounded." \
  --concept compact \
  --concept complete \
  --expected-name CompactSpace.isComplete \
  --json
```

Offline deterministic check over `MathformerLib` only:

```bash
python3 skills/mathlib/mathlib-result-existence-checker/scripts/check_result_existence.py \
  --statement "Truth is derivable in the seed library." \
  --expected-name MathformerLib.true_intro \
  --no-mathlib \
  --no-web-plan \
  --json
```

After official-source web search has found no duplicate:

```bash
python3 skills/mathlib/mathlib-result-existence-checker/scripts/check_result_existence.py \
  --statement-file tests/latex/hellys_theorem.tex \
  --concept Helly \
  --concept convex \
  --web-confirmed-absent \
  --json
```

## Output Contract

The JSON report includes:

- `status`: `likely_existing`, `candidate_overlap`, `needs_web_confirmation`, or `not_found`.
- `gate.decision`: reuse, verify before drafting, run web search, or proceed.
- `gate.drafting_allowed`: boolean release signal for `draft.initial`.
- `top_candidates`: ranked mathlib/MathformerLib overlap candidates.
- `web_search_plan`: official-source search tasks and local verification handoffs.

## References

- Read `references/existence_policy.md` when deciding whether a candidate should block
  drafting or route to web/local verification.
