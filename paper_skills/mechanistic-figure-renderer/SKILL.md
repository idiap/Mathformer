---
name: mechanistic-figure-renderer
description: Render structured Mathformer mechanistic diagram models into paper figures such as SVG and TikZ/PDF. Use after mechanistic-diagram-modeler when a scientific paper needs a concrete figure artifact.
---

<!--
File Documentation

Motivation:
  Capture the research-paper production workflow as auditable agent skills and helper scripts.

Intent:
  Separate scientific writing, evidence mapping, figure generation, and theory-evolution modeling roles.

Function:
  Provides structured guidance and automation for paper-oriented artifacts.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Mechanistic Figure Renderer

## Purpose

Use this skill after a diagram model exists. It renders the model into a figure
artifact while preserving the semantic labels of nodes and relations.

## Workflow

1. Read a diagram model JSON.
2. Render a deterministic SVG for quick inspection.
3. Optionally render a TikZ/LaTeX source and compile it with `tectonic` to PDF.
4. Add the generated figure to the paper with a caption matching the model.
5. Verify that all nodes and edges in the model appear in the rendered figure.
6. For observability figures, verify that dashboard, monitor, validation, and
   human-inspection nodes are visually distinct and readable at paper width.

## Command

```bash
python3 paper_skills/mechanistic-figure-renderer/scripts/render_mechanistic_figure.py \
  --model paper/figures/mathformer_mechanistic_diagram.json \
  --svg paper/figures/mathformer_mechanistic_diagram.svg \
  --tex paper/figures/mathformer_mechanistic_diagram.tex \
  --compile-pdf \
  --json
```

## Guardrails

- Do not render unlabeled arrows.
- Feedback edges must be visually distinguishable.
- Figures should be readable at paper column or full-page width.
- The figure is explanatory evidence, not experimental evidence.
- Captions should say whether the figure is a generated mechanism model or a
  conceptual diagram.
