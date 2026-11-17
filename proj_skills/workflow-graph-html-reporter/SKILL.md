---
name: workflow-graph-html-reporter
description: Render a workflow graph JSON model into a self-contained HTML explorer with summary cards, Cytoscape.js views, click drill-down, static fallback workflow cards, and embedded JSON.
---

<!--
File Documentation

Motivation:
  Make agentic workflow structure easy to inspect visually.

Intent:
  Guide rendering of Mathformer's workflow_graphs.html report.

Function:
  Defines the report surfaces expected from workflow graph visualization.

Maintenance Notes:
  Keep synchronized with scripts/render_workflow_graphs.py.
-->

# Workflow Graph HTML Reporter

Use this skill after `workflow-graph-modeler`.

## Required Report Surfaces

The HTML report should include:

- summary cards
- graph-design notes or explanatory text
- tabbed graph explorer
- workflow overview view
- sequence and hierarchy view
- cross-stack interaction view
- click drill-down view with bottom details panel
- collapsible workflow-stack cards
- embedded JSON payload
- static fallback content for non-JavaScript readers

## Rendering Rules

- Use Cytoscape.js for the dynamic graph layer.
- Keep sequence views ordered; do not rely only on force layout.
- Use force layout only for cross-stack skill reuse.
- Keep visual style utilitarian and readable.
- JSON remains the source of truth.
- Prefer `scripts/render_workflow_graphs.py` for deterministic rendering.
