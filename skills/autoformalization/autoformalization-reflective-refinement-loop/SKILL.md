---
name: autoformalization-reflective-refinement-loop
description: Observe full Mathformer autoformalization runs and produce monotonic prompt/skill improvement opportunities. Use after workflow reports, reasoning logs, suite runs, or process audits when improvements should preserve all previously successful cases and be guarded by non-regression checks.
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

# Autoformalization Reflective Refinement Loop

## Purpose

Use this skill after an autoformalization workflow or controlled suite has
produced a report and reasoning log. It observes the whole process, identifies
prompt and skill improvement opportunities, and attaches monotonicity gates so
successful prior cases are not invalidated.

Runtime:
- `scripts/observe_autoformalization_process.py`
- hook: `reflection.process_refinement`

## Workflow

1. Read the latest workflow or suite report.
2. Validate the reasoning log with `reasoning-log-schema-guardian`.
3. Compare current success cases against an optional baseline.
4. Read the optional `reference-free-critic-monitor` packet and treat its score
   floors, hard risk counts, and anti-gaming warnings as process evidence.
5. Identify localized opportunities for prompt, skill, hook, or suite-control
   improvement.
6. Attach a non-regression gate to every opportunity.
7. Emit a refinement packet; do not apply prompt or skill changes automatically.
8. Apply any candidate change only after the packet's regression commands pass.

## Monotonicity Rule

A proposed refinement is admissible only when it preserves every case that was
previously successful in the baseline and keeps core gates passing:

- controlled suite summary remains passing,
- Lean execution remains passing,
- compatibility score does not decrease below the accepted floor,
- reference-free critic confidence does not decrease below the accepted floor,
- reference-free hard risk counts do not increase,
- expected declaration checks remain passing,
- hook contract validation remains strict-clean,
- reasoning-log validation remains strict-clean.

## Command

```bash
python3 skills/autoformalization/autoformalization-reflective-refinement-loop/scripts/observe_autoformalization_process.py \
  --report-file artifacts/wiki_level_suite/report.json \
  --reasoning-log-file artifacts/wiki_level_suite/reasoning.jsonl \
  --reference-free-monitor-file artifacts/reference_free_critic_monitor/latest.json \
  --hooks-file skills/SKILL_HOOKS.yaml \
  --output-file artifacts/reflection/wiki_level_refinement_packet.json \
  --json
```

## References

- Read `references/refinement_loop.md` when changing the packet schema or
  monotonicity policy.
