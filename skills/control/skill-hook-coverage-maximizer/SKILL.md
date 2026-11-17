---
name: skill-hook-coverage-maximizer
description: Audit Mathformer skill coverage through the hook contract, direct request routing, shared runtime scripts, and named loop contracts. Use after adding skills, editing SKILL_HOOKS.yaml, or changing workflow loops to ensure the maximum appropriate number of skills are systematically applied.
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

# Skill Hook Coverage Maximizer

## Purpose

Use this skill to make sure the framework is not relying on undocumented memory for
skill application. It audits whether non-wrapper skills are reachable through hooks or
direct routes, and whether named workflow loops declare their required hooks.

Hook:
- `control.skill_hook_coverage`

Runtime:
- `scripts/audit_skill_hook_coverage.py`

## Workflow

1. Run after creating a skill, editing `skills/SKILL_HOOKS.yaml`, changing direct routes,
   or changing workflow loop order.
2. Require every non-wrapper skill to have a hook or a direct route.
3. Require compatibility wrappers to be explicitly exempted rather than silently uncovered.
4. Check `loop_contracts` in `skills/SKILL_HOOKS.yaml` for required hook presence and
   required owner-skill coverage.
5. Treat high findings as blockers before accepting the skill or hook change.

## Command

```bash
python3 skills/control/skill-hook-coverage-maximizer/scripts/audit_skill_hook_coverage.py \
  --hooks-file skills/SKILL_HOOKS.yaml \
  --skills-dir skills \
  --expect-ok \
  --json
```

## References

- Read `references/coverage_policy.md` before changing coverage thresholds, wrapper
  exemptions, or named loop contracts.
