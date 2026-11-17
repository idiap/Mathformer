---
name: project-workflow-layout-reasoner
description: Orchestrate rational positioning for Mathformer workflow graph reports by combining graph modeling, layout planning, clutter criticism, renderer updates, and validation.
---

<!--
File Documentation

Motivation:
  Workflow graph layout is an agentic reasoning task: the view should expose
  the control structure without hiding it in visual noise.

Intent:
  Provide one project-local skill for running the layout reasoning loop.

Function:
  Coordinates layout rationalization, clutter critique, deterministic layout
  plan generation, and renderer validation.

Maintenance Notes:
  Keep synchronized with scripts/render_workflow_graphs.py and
  scripts/plan_workflow_graph_layout.py.
-->

# Project Workflow Layout Reasoner

Use this skill when the user asks to make workflow graphs clearer, position
nodes rationally, reduce clutter, or reason over `workflow_graphs.json`.

## Pipeline

```text
workflow-graph-modeler -> workflow-layout-rationalizer -> workflow-layout-clutter-critic -> workflow-graph-html-reporter
```

## Deterministic Commands

Generate the graph and layout plan:

```bash
python scripts/render_workflow_graphs.py --output-dir artifacts/workflow_graphs --json
python scripts/plan_workflow_graph_layout.py --graph artifacts/workflow_graphs/workflow_graphs.json --output artifacts/workflow_graphs/workflow_layout_plan.json --json
```

## Reasoning Loop

1. Identify the question each view should answer.
2. Assign node classes to lanes or overlays.
3. Compute edge pressure by view.
4. Hide or separate semantic layers that compete visually.
5. Patch the renderer with minimal layout changes.
6. Regenerate and validate JSON, HTML, and JavaScript.

## Acceptance Criteria

- Overview is sparse and orienting.
- Sequence view preserves temporal order.
- Drill-down keeps workflow context without uncontrolled edge crossings.
- Cross-stack view shows reuse, not all skills.
- Reflection and skill overlays are opt-in unless they are the view's focus.
- Every layout choice has a short rationale.
