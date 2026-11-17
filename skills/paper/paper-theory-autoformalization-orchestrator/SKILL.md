---
name: paper-theory-autoformalization-orchestrator
description: Coordinate paper-level theory autoformalization from PDF/layout extraction through main-result localization, supporting-reference expansion, intermediate-result expansion, mathlib grounding, duplicate-result precheck, proof expansion support, and Lean drafting. Use when the user asks to autoformalize the main theory of a paper rather than a single theorem.
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

# Paper Theory Autoformalization Orchestrator

## Purpose

Use this skill when a full paper is the source and the goal is to autoformalize its main
theory, not merely a single statement.

Hook:
- `preformalization.paper_theory_expand`

## Workflow

1. Run `scripts/build_paper_theory_plan.py` on the PDF URL/file or source text.
2. The script runs `paper-docling-layout-extractor` and `paper-main-theory-localizer`.
3. Build an expansion queue:
   - main theorem-like results,
   - local definitions and assumptions,
   - intermediate lemmas/propositions/corollaries,
   - proof blocks,
   - notation/equation bindings,
   - cited external results and bibliography entries.
4. For each selected result, require:
   - original source span,
   - dependency queue,
   - proof or cited-support status,
   - mathlib concept hints,
   - duplicate-result precheck route.
5. Expand intermediate results before the main theorem and preserve their source spans in
   generated Lean declaration comments.
6. Use `proof-expansion-difficulty-estimator` to decide which proof segments need web support.
7. Use `proof-expansion-web-researcher` for external referenced theorems or ambiguous citations.
8. Hand the reviewed queue to the existing source-unit, LaTeX expansion, mathlib grounding,
   import planning, Lean drafting, execution, critique, and realness gates.

## Output Contract

Emit a paper-theory plan containing:

- `layout_packet`
- `theory_localization_packet`
- `expanded_intermediate_queue`
- `reference_support_packet`
- `main_result_drafting_queue`
- `blocked_or_unresolved_dependencies`

Do not draft a final Lean artifact for a paper-level theorem until its intermediate queue
has been expanded or explicitly marked unresolved.

## Commands

Build a plan from the NeurIPS example PDF:

```bash
python3 skills/paper/paper-theory-autoformalization-orchestrator/scripts/build_paper_theory_plan.py \
  --url "https://proceedings.neurips.cc/paper_files/paper/2024/file/4a68bb0e075a3215d4ff37382ea598dc-Paper-Conference.pdf" \
  --json
```

Self-test with embedded paper-like theory text:

```bash
python3 skills/paper/paper-theory-autoformalization-orchestrator/scripts/build_paper_theory_plan.py \
  --self-test \
  --json
```

The PDF path is docling-first. If docling and other PDF text engines are unavailable, the
plan must return `status: blocked` with an explicit extraction-engine report instead of
inventing theorem blocks.

To enable the docling path in the local project environment:

```bash
scripts/install_uv_env.sh --with-paper-extraction --skip-lean
```
