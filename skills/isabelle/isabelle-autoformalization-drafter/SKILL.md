---
name: isabelle-autoformalization-drafter
description: Draft initial Isabelle/HOL theory files from informal or LaTeX mathematical statements. Use when creating a first Isabelle autoformalization attempt, choosing an Isar proof style, preserving source anchors, or routing a non-Lean prover backend through the Mathformer workflow.
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

# Isabelle Autoformalization Drafter

## Purpose

Use this skill for first-pass Isabelle/HOL code generation. It is the Isabelle
counterpart of the Lean drafter, but it owns only Isabelle-specific choices:
theory headers, imports, Isar proof style, source-aware comments, and handoff to
Isabelle execution.

## Style

Implement one Isabelle style at a time. The current supported style is:

- `isar_direct`: a normal `.thy` theory importing `Main`, with structured Isar
  statements and short proofs. Prefer explicit `fix`, `assume`, `have`, `show`,
  `qed` blocks over opaque one-line automation when the source proof has a
  readable argument.

Do not mix styles in one artifact. Add a new style only after the current one
has deterministic execution tests.

## Workflow

1. Start from reviewed LaTeX/NL and any source-line translation packet.
2. Run `isarmathlib-grounding-navigator` before drafting when concepts may
   already exist in Isabelle sessions or IsarMathLib.
3. Choose imports conservatively. Start from `Main`; add IsarMathLib imports
   only when the local grounding report identifies a concrete theory.
4. Write one source-aware module comment at the top and one compact declaration
   comment per source-backed theorem/definition.
5. Preserve original source prose/LaTeX and `Source anchors: ...` when available.
6. Keep generated support facts clearly marked as generated notes.
7. Do not emit Lean syntax in Isabelle theories.
8. Do not claim completion when a theory still has `sorry`, `oops`,
   `quickcheck_params` scaffolding, or unexecuted checks.
9. Immediately hand the `.thy` file to `isabelle-execution-runner`.

## Deterministic Fixture

For the controlled Wikipedia-level smoke case:

```bash
python3 skills/isabelle/isabelle-autoformalization-drafter/scripts/draft_isabelle_wiki_case.py \
  --latex-file tests/latex/wiki_level/injective_composition.tex \
  --case-id wiki_injective_composition \
  --output-file backends/isabelle/Isabelle/AutoformalizedWikiInjectiveComposition.thy \
  --report-file artifacts/isabelle_wiki_level/wiki_injective_composition.draft.json \
  --json
```

