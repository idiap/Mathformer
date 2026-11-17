---
name: lean-nonvacuity-consistency-checker
description: Detect Lean theorem-like declarations that compile but give no useful mathematical evidence, such as axioms, false hypotheses, targets copied into hypotheses, bare True conclusions, or proofs that trivially exact a visible hypothesis. Use after Lean compilation succeeds and before accepting a generated formalization into MathformerLib.
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

# Lean Nonvacuity Consistency Checker

Use this skill when a generated Lean theorem should be checked for vacuity,
trivialization, or hidden restatement of its target as an assumption.

## Purpose

This deterministic critic looks for theorem-like declarations that compile but
do not give useful mathematical evidence: axioms, false hypotheses, targets
copied into hypotheses, bare `True` conclusions, or proof bodies that simply
`exact` a visible hypothesis without an explicit representation-boundary note.

## When To Run

- After Lean compilation succeeds.
- After informalization and declaration-shape checks.
- Before accepting a generated formalization into MathformerLib or reporting it
  as a completed theorem.

## Procedure

1. Run `scripts/check_lean_nonvacuity_consistency.py` on the target files.
2. Treat high-severity findings as blockers.
3. Treat medium-severity findings as required review items unless the
   declaration is intentionally an interface theorem, accessor, certificate
   wrapper, or external-assumption boundary.
4. Repair by strengthening the Lean statement/proof, moving assumptions into a
   named certificate, or adding a precise generated note that documents the
   boundary.

## Command

```bash
python3 skills/lean/lean-nonvacuity-consistency-checker/scripts/check_lean_nonvacuity_consistency.py \
  --lean-file backends/lean/Mathformer/AutoformalizedExample.lean \
  --expect-ok --json
```

## Output Contract

The JSON report contains:

- `ok`: true iff no high-severity non-vacuity blocker was found.
- `summary.nonvacuity_score`: reference-free score from 0 to 100.
- `findings`: localized vacuity and thin-wrapper findings.

## Hook

Canonical hook id: `consistency.nonvacuity`.
