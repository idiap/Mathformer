---
name: skill-test-program-orchestrator
description: Build and run an aggressive test program for Mathformer deterministic, generative, and hybrid skills. Use when validating all skills, generating skill-test TODOs, running deterministic contract checks, or executing content-quality probes through codex exec.
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

# Skill Test Program Orchestrator

## Purpose

Use this skill to test Mathformer skills aggressively across two lanes:

- deterministic skills: scripts, contracts, Lean checks, hook checks, JSON schema,
  and suite regressions;
- generative/content skills: prompt behavior, critique quality, mathematical
  discipline, semantic preservation, and skill-output usefulness through
  `codex exec` probes.

Runtime:
- `scripts/inventory_skills.py`
- `scripts/run_deterministic_skill_tests.py`
- `scripts/run_content_skill_codex_exec_tests.py`
- `scripts/generate_skill_test_todos.py`
- hook: `test.skill_program`

## Workflow

1. Run the skill inventory to classify deterministic, generative, and hybrid
   skill surfaces.
2. Run deterministic checks first; do not trust content probes while contracts
   or schema checks are failing.
3. Run Codex-exec content probes for generative and hybrid skills.
4. Convert failures and untested surfaces into self-explanatory TODOs.
5. Promote important failures into repeatable probes or deterministic regression
   checks.

## Commands

```bash
python3 skills/control/skill-test-program-orchestrator/scripts/inventory_skills.py --json
```

```bash
python3 skills/control/skill-test-program-orchestrator/scripts/run_deterministic_skill_tests.py \
  --include-slow \
  --json
```

```bash
python3 skills/control/skill-test-program-orchestrator/scripts/run_content_skill_codex_exec_tests.py \
  --execute \
  --json
```

Add `--limit 1` only when you need a quick Codex-exec smoke check.
Use `--reuse-existing` only after changing probe oracles, when saved final
messages already exist and you need to re-score them without launching Codex
again.

```bash
python3 skills/control/skill-test-program-orchestrator/scripts/generate_skill_test_todos.py
```

## References

- Read `references/test_program.md` for the test matrix, content oracle, exit
  criteria, and failure-to-regression policy.
- Read `references/content_probes.json` when editing Codex-exec probe seeds.
