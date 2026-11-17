---
name: source-formalizable-unit-extractor
description: Identify definitions, theorem-like claims, lemmas, corollaries, proofs, examples, equivalences, formulas, notation, and prerequisite units in a mathematical source URL or text before autoformalization. Use when a source such as a Wikipedia page must be decomposed into autoformalizable candidates with provenance, dependency order, mathlib concept hints, and downstream workflow routing.
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

# Source Formalizable Unit Extractor

## Purpose

Use this skill at source intake, before LaTeX expansion, duplicate-result precheck, mathlib
grounding, or first Lean drafting. It turns a page or excerpt into a typed inventory of
formalization candidates rather than asking the drafter to infer the whole page structure.

Hook:
- `intake.source_unit_inventory`

## Workflow

1. Preserve provenance: source URL, title, section heading, quoted source span, and retrieval date.
2. Run `scripts/extract_autoformalizable_units.py` on the source text or URL for a deterministic first pass.
3. Refine the inventory generatively only by adding structured fields, never by erasing original source spans.
4. Classify units with this vocabulary:
   - `definition`: term introduction, iff-style definition, notation, named property.
   - `theorem`: named theorem, major result, proposition, criterion.
   - `lemma`: supporting claim, property, inequality, closure fact, implication.
   - `corollary`: consequence explicitly derived from a prior result.
   - `proof`: proof paragraph, derivation, construction, counterexample argument.
   - `example`: example, non-example, special case, boundary case.
   - `formula`: displayed equation, bound, recurrence, representation, quantified condition.
   - `notation`: symbols, parameter conventions, abbreviation, indexing convention.
   - `prerequisite`: concept needed before another unit can be formalized.
5. For every theorem-like unit, record assumptions, conclusion, proof availability, dependency ids,
   expected duplicate-search names, mathlib concepts, and an initial difficulty label.
6. Route the inventory:
   - definitions/prerequisites -> `latex-prerequisite-expander`
   - theorem-like units -> `result-existence-precheck-orchestrator`
   - concepts -> `mathlib-concept-candidate-mapper`
   - proof units -> `proof-expansion-support-orchestrator`
   - hard or ambiguous units -> `proof-expansion-difficulty-estimator`
7. Do not draft Lean until each selected theorem-like unit is source-linked, typed, and either
   has a proof unit, a cited result, or an explicit dependency gap.

## Commands

From a URL:

```bash
python3 skills/autoformalization/source-formalizable-unit-extractor/scripts/extract_autoformalizable_units.py \
  --url "https://en.wikipedia.org/wiki/Lipschitz_continuity" \
  --json
```

From pasted source text:

```bash
python3 skills/autoformalization/source-formalizable-unit-extractor/scripts/extract_autoformalizable_units.py \
  --text "A function f is Lipschitz continuous if ..." \
  --title "Lipschitz continuity" \
  --json
```

## Output Contract

Each unit should include:

- `id`: stable local id such as `unit_003`.
- `kind`: one of the controlled kinds above.
- `section`: nearest source section when available.
- `source_span`: compact original text span.
- `statement`: normalized mathematical statement when available.
- `formalization_signal`: why the span is likely formalizable.
- `proof_present`: whether the unit contains proof text.
- `dependencies`: earlier unit ids or unresolved concept names.
- `mathlib_concepts`: terms to pass to mathlib grounding.
- `suggested_lean_surface`: likely `def`, `structure`, `theorem`, `lemma`, `example`, or comment-only context.
- `priority`: `high`, `medium`, or `low`.

Read `references/unit_inventory_schema.json` when validating stored inventory packets.
