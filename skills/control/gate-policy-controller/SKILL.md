---
name: gate-policy-controller
description: Normalize Mathformer gate decisions from structured checks, severities, blocking flags, and waivers. Use when a workflow phase must decide pass, warn, fail, skip, or waived status after validators, critiques, Lean checks, coverage checks, or compatibility audits.
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

# Gate Policy Controller

## Purpose

Use this skill to make phase gates uniform. It converts heterogeneous validator,
critique, Lean, coverage, and audit checks into one decision object with a stable
status and explicit blocking failures.

Runtime:
- `scripts/gate_policy.py`
- hook: `control.gate_policy`

## Workflow

1. Collect checks with `id`, `passed`, `severity`, `blocking`, and `message`.
2. Apply explicit waivers only when a failure is intentionally accepted.
3. Fail the gate when any unwaived blocking check fails.
4. Warn when nonblocking checks fail.
5. Record the decision in a reasoning log when the gate belongs to a workflow run.

## Command

```bash
python3 skills/control/gate-policy-controller/scripts/gate_policy.py \
  --gate-id wiki-level-suite \
  --hook-id control.gate_policy \
  --check lean=true:high:true:"Lean gold file compiles" \
  --check compatibility=true:medium:false:"Compatibility target met" \
  --json
```

## References

- Read `references/gate_decision.md` when adding new gate-producing scripts.
