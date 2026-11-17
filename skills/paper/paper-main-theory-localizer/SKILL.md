---
name: paper-main-theory-localizer
description: Locate the main theoretical results in a paper layout packet and expand the supporting theory context. Use after docling/layout extraction to identify main theorems, definitions, assumptions, lemmas, corollaries, proofs, cited reference support, dependency order, and intermediate results that must be expanded before autoformalization.
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

# Paper Main Theory Localizer

## Purpose

Use this skill after `paper-docling-layout-extractor`. It finds the paper's main theory
payload and builds an expansion queue around it.

Hook:
- `intake.paper_theory_localize`

## Workflow

1. Read a layout packet with sections, blocks, citations, labels, and references.
2. Score theorem-like blocks higher when they:
   - appear in theory, method, analysis, or main result sections,
   - are named `Theorem`, `Proposition`, `Lemma`, `Corollary`, `Assumption`, or `Definition`,
   - are referenced by nearby proof blocks,
   - contain rates, bounds, equivalences, convergence claims, sample complexity, or guarantees.
3. Select main results conservatively and keep supporting results in dependency order.
4. Expand intermediate results:
   - definitions and assumptions before each selected result,
   - lemmas/propositions used in proof blocks,
   - cited external theorem names and bibliography entries,
   - notation/equation blocks needed to bind variables.
5. Route selected theorem-like units to duplicate-result precheck before Lean drafting.
6. Route proof blocks and hard theoretical dependencies to proof expansion support.

## Commands

```bash
python3 skills/paper/paper-main-theory-localizer/scripts/localize_paper_theory.py \
  --layout-json artifacts/paper/layout.json \
  --json
```

Self-test:

```bash
python3 skills/paper/paper-main-theory-localizer/scripts/localize_paper_theory.py \
  --self-test \
  --json
```

## Output Contract

The JSON packet contains:

- `main_results`: selected theorem/proposition/corollary candidates.
- `support_units`: definitions, assumptions, lemmas, formulas, proof blocks, and examples.
- `intermediate_expansion_queue`: ordered units to expand before first Lean drafting.
- `reference_support`: cited bibliography entries and missing citation-resolution warnings.
- `mathlib_concepts`: concept hints aggregated from selected and supporting units.
- `downstream_routes`: workflow skills that must consume each unit.

Read `references/theory_localization_schema.json` when validating stored packets.
