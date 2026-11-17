---
name: project-workflow-graph-reporter
description: Orchestrate the full Mathformer workflow graph reporting pipeline: extract workflow contracts, build the typed graph model, render the Cytoscape HTML explorer, and validate the JSON/HTML outputs.
---

<!--
File Documentation

Motivation:
  Provide one project-local skill for generating the full workflow graph report.

Intent:
  Coordinate extraction, modeling, rendering, and validation without exposing
  users to low-level script details.

Function:
  Orchestrates the workflow graph reporting pipeline.

Maintenance Notes:
  Keep synchronized with scripts/render_workflow_graphs.py.
-->

# Project Workflow Graph Reporter

Use this skill when the user asks for an agentic workflow graph, workflow stack
map, skill reuse visualization, or reflective-loop graph report.

## Pipeline

Run the conceptual pipeline:

```text
workflow-contract-extractor -> workflow-graph-modeler -> workflow-layout-rationalizer -> workflow-graph-html-reporter
```

For deterministic project output, use:

```bash
python scripts/render_workflow_graphs.py --output-dir artifacts/workflow_graphs --json
python scripts/plan_workflow_graph_layout.py --graph artifacts/workflow_graphs/workflow_graphs.json --output artifacts/workflow_graphs/workflow_layout_plan.json --json
```

## Expected Artifacts

- `artifacts/workflow_graphs/workflow_graphs.json`
- `artifacts/workflow_graphs/workflow_graphs.html`
- `artifacts/workflow_graphs/workflow_layout_plan.json`

## Validation

Check that:

- JSON summary counts are nonzero.
- Graph contains `family`, `workflow`, `workflow_step`, `skill`, and reflective edge records.
- HTML contains Cytoscape, summary cards, graph tabs, static workflow cards, and embedded JSON.
- Reflective loops remain visible as typed edges.
- Layout plan explains view purpose, lane assignment, edge pressure, and visibility defaults.
