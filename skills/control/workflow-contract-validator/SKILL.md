---
name: workflow-contract-validator
description: Validate Mathformer skill hook contracts, owner-skill directories, direct-request routing, shared runtime paths, and optional reasoning-log evidence. Use when adding or editing skills, hooks, routing entries, shared scripts, or workflow-gate metadata.
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

# Workflow Contract Validator

## Purpose

Use this skill to keep `skills/SKILL_HOOKS.yaml` executable as a contract instead
of prose. It validates hook ids, owner skills, direct-request routing targets,
shared runtime scripts, and optional reasoning-log evidence.

Runtime:
- `scripts/validate_skill_hooks.py`
- hook: `control.workflow_contract`

## Workflow

1. Run the validator after changing `skills/SKILL_HOOKS.yaml` or creating a skill.
2. Treat missing owner skill folders, missing `SKILL.md`, duplicate hook ids, and
   missing shared runtime scripts as blocking.
3. Run with `--reasoning-log-file` when validating an actual workflow trace.
4. Use strict mode for release gates and suite checks.

## Command

```bash
python3 skills/control/workflow-contract-validator/scripts/validate_skill_hooks.py \
  --hooks-file skills/SKILL_HOOKS.yaml \
  --skills-dir skills \
  --strict \
  --json
```

## References

- Read `references/contract.md` when changing the hook manifest structure.

## Normalized workflow skill contracts

The generated `references/normalized-workflows/catalog.json` links every controlled
hub action, NL route, hook loop contract and semantic reasoning profile to its
`workflow-skill/v1` descriptor and owning skill. Sources remain authoritative;
these descriptions do not replace native execution. All canonical IDs end in
`_workflow`. Native aliases and semantic/operational boundaries are preserved.

Use `python scripts/mathformer.py ask "validate normalized workflows" --run --json`
for schema, dataflow, provenance and coverage checks. Regenerate after changing
canonical contracts through `python scripts/mathformer.py run control:normalize-workflows
--allow-mutating --json`. Read `references/workflow-skill-format.md` for the shared
format and `docs/architecture/WORKFLOW_SKILLS.md` for coverage and limitations.

Standalone descriptor validation uses `scripts/validate_workflow.py` in this skill.
It requires PyYAML and jsonschema and never imports executable operation bindings.

## Portable adoption contracts

The bounded adoption pilot has one authored contract at
`references/portable-adoption.json`, with its schema alongside it. Validate
identity, bindings, operation typing and adapter compatibility through
`python3 scripts/mathformer.py ask "validate portable repository adoption" --run --json`.
Existing hook validation remains unchanged. See
`docs/migrations/portable-repository-adoption/usage.md` for invocation examples.
