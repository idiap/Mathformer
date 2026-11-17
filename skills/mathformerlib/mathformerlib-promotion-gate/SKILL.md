---
name: mathformerlib-promotion-gate
description: Decide whether a Lean formalization may be promoted into accepted Mathformerlib status by running realness, optional compile, placeholder/scaffold, and registry-aware checks. Use before moving generated Lean into MathformerLib or counting a Mathformerlib entry as accepted.
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

# Mathformerlib Promotion Gate

## Purpose

Use this skill before a generated or manually curated Lean artifact becomes an
accepted Mathformerlib entry. It rejects mocked, scaffold-only, placeholder, or
uncompiled candidates.

Runtime:
- `scripts/evaluate_mathformerlib_promotion.py`
- hook: `mathformerlib.promotion_gate`

## Commands

```bash
python3 skills/mathformerlib/mathformerlib-promotion-gate/scripts/evaluate_mathformerlib_promotion.py \
  --lean-file libraries/MathformerLib/Basic.lean \
  --compile \
  --json
```

```bash
python3 skills/mathformerlib/mathformerlib-promotion-gate/scripts/evaluate_mathformerlib_promotion.py \
  --text "theorem t : True := by sorry" \
  --name sorry_fixture \
  --expect-blocking \
  --json
```

## Gate Semantics

- `accepted`: all required checks pass.
- `blocked`: a final artifact has blocking realness or compile findings.

Draft artifacts should be registered by `mathformerlib-registry-manager`, not
promoted.
