---
name: workflow-layout-rationalizer
description: Reason over Mathformer's workflow_graphs.json representation to choose rational node positions, visual lanes, default visibility, spacing, and graph-view semantics for workflow visualizations.
---

<!--
File Documentation

Motivation:
  Graph layouts should communicate the workflow's epistemic structure rather
  than merely place nodes by force simulation.

Intent:
  Give agents a compact method for deciding where graph nodes belong.

Function:
  Converts typed workflow graph semantics into layout lanes, spacing, and
  visibility choices.

Maintenance Notes:
  Keep synchronized with scripts/plan_workflow_graph_layout.py.
-->

# Workflow Layout Rationalizer

Use this skill after `workflow-graph-modeler` and before HTML rendering when a
workflow graph feels cluttered or semantically poorly positioned.

## Positioning Principle

Place nodes by reasoning role:

```text
temporal order -> capability reuse -> reflective feedback
```

## Layout Rules

- Put ordered `workflow_step` nodes on the main horizontal lane.
- Put reusable `skill` nodes on a lower optional lane.
- Put reflective feedback edges above or around the main lane; keep them opt-in.
- Keep `workflow` nodes as anchors, not as central hubs in dense drill-downs.
- Treat `family` as grouping metadata unless the user asks for taxonomy.
- Use shared-skill interaction views only for skills reused by more than one stack.

## Deterministic Helper

Prefer the project script when a concrete layout plan is needed:

```bash
python scripts/plan_workflow_graph_layout.py --graph artifacts/workflow_graphs/workflow_graphs.json --output artifacts/workflow_graphs/workflow_layout_plan.json --json
```

## Output Contract

Return:

- view purpose,
- visible node classes,
- visible edge classes,
- lane assignment,
- spacing recommendation,
- rationale for every non-obvious positioning choice.
