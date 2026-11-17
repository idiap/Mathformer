---
name: workflow-graph-modeler
description: Convert extracted Mathformer workflow contracts into a typed graph model with family, workflow, workflow_step, skill, and external_ref nodes plus containment, sequence, reuse, handoff, and reflective feedback edges.
---

<!--
File Documentation

Motivation:
  Keep graph semantics stable across HTML reports and downstream tooling.

Intent:
  Define the JSON graph model used by Mathformer workflow visualizations.

Function:
  Guides agents when constructing or reviewing workflow_graphs.json.

Maintenance Notes:
  Keep synchronized with the graph schema in scripts/render_workflow_graphs.py.
-->

# Workflow Graph Modeler

Use this skill after `workflow-contract-extractor`.

## Model Shape

Represent the project as:

```text
Workflow Family -> Workflow Stack -> Ordered Skill Hook
```

Then add reusable skill nodes and reflective edges.

## Node Types

- `family`
- `workflow`
- `workflow_step`
- `skill`
- `external_ref`

## Edge Types

- `family_contains_workflow`
- `workflow_entry`
- `workflow_sequence`
- `skill_handoff`
- `stack_uses_skill`
- `workflow_reflective_loop`
- `reflective_external_reference`

## Modeling Rules

- Keep ordered hook nodes separate from reusable skill nodes.
- Use one `workflow_step` node per ordered hook occurrence.
- Use one `skill` node per reusable capability.
- Mark critic, refiner, guard, and monitor returns as reflective edges.
- Make JSON the source of truth; HTML should render the JSON, not duplicate it.
- Prefer `scripts/render_workflow_graphs.py` for deterministic Mathformer reports.
