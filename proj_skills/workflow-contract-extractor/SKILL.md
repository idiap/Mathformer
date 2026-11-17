---
name: workflow-contract-extractor
description: Extract Mathformer workflow families, workflow stacks, triggers, artifact entrypoints, handoffs, ordered hooks, and reflective-loop hints from AGENTS.md, docs/architecture/AGENTIC_HUB.md, and local skill manifests. Use before modeling or rendering agentic workflow graph reports.
---

<!--
File Documentation

Motivation:
  Make workflow extraction consistent before graph modeling.

Intent:
  Tell agents how to identify workflow contracts without confusing script
  catalogues with ordered agentic loops.

Function:
  Provides project-local extraction rules for the workflow graph reporter.

Maintenance Notes:
  Keep synchronized with docs/architecture/AGENTIC_HUB.md and scripts/render_workflow_graphs.py.
-->

# Workflow Contract Extractor

Use this skill when building or updating Mathformer's agentic workflow graph model.

## Sources

Read only the needed local sources:

- `AGENTS.md` for repository-wide operating contracts.
- `docs/architecture/AGENTIC_HUB.md` for named loop contracts, families, and agent inventory.
- `skills/*/*/SKILL.md` for skill names and descriptions.

## Extraction Contract

Extract:

- workflow family
- workflow stack name
- trigger
- artifact entrypoints
- ordered hook skills
- hook role: `extractor`, `critic`, `planner`, `refiner`, `guard`, `orchestrator`, `writer`, or `workflow-skill`
- execution posture: `deterministic`, `generative`, or `both`
- output type: `workflow_context`, `evidence_packet`, `finding`, `plan_or_todo`, `gate_decision`, `workflow_update`, or `report_artifact`
- reflective feedback edges

## Rules

- Preserve order when a loop is written with `->`.
- Do not flatten reflective loops into ordinary sequence edges.
- Prefer existing skill names from `skills/` when mapping hook text to a skill.
- If a reflective target is outside the local workflow, mark it as an external reference.
- Use `scripts/render_workflow_graphs.py` when the user wants the deterministic project report.
