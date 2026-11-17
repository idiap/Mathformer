---
name: workflow-layout-clutter-critic
description: Review Mathformer workflow graph JSON or HTML reports for visual clutter, edge overload, label collisions, mixed semantic layers, and weak graph-view defaults; recommend precise layout repairs.
---

<!--
File Documentation

Motivation:
  A graph can be formally correct and still unreadable.

Intent:
  Give agents a review lens for workflow graph usability.

Function:
  Diagnoses clutter and maps each issue to a concrete layout repair.

Maintenance Notes:
  Keep the checks aligned with the graph views in scripts/render_workflow_graphs.py.
-->

# Workflow Layout Clutter Critic

Use this skill after rendering `workflow_graphs.html`, or when a user says a
workflow graph is cluttered.

## Review Questions

- Does the view mix temporal order, reuse, and reflection at the same time?
- Are edge labels competing with node labels?
- Are one-off skill nodes visible in views meant to show cross-stack reuse?
- Are reflective edges crossing the main sequence lane?
- Is the default view answering one question, or several?

## Findings Format

Report findings as:

```text
View -> clutter source -> concrete repair -> expected effect
```

## Repair Menu

- Hide an edge class by default.
- Move a node class into an optional overlay.
- Increase `idealEdgeLength`, `nodeRepulsion`, or `spacingFactor`.
- Switch from force layout to lane or preset positioning.
- Split one overloaded graph into staged views.
- Preserve the JSON model; repair the rendering logic.

## Deterministic Evidence

Use `scripts/plan_workflow_graph_layout.py` to inspect edge pressure and view
defaults before suggesting changes.
