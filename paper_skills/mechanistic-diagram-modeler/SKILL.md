---
name: mechanistic-diagram-modeler
description: Build paper-ready mechanistic diagram models for Mathformer: typed nodes, layers, relations, feedback loops, validation criteria, observability surfaces, and captions. Use when a scientific paper needs a precise diagram specification before rendering a figure.
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

# Mechanistic Diagram Modeler

## Purpose

Use this skill when the paper needs a mechanistic figure. It produces a
structured diagram model rather than a hand-drawn image, so the visual claim is
auditable and reusable.

## Workflow

1. Decide the figure claim:
   - end-to-end workflow,
   - dynamical-system relations,
   - RFDE observability,
   - reasoning-log observability stack,
   - mathlib grounding loop,
   - critique/repair loop.
2. Build a model with:
   - `nodes`: id, label, layer, role, optional equation;
   - `edges`: source, target, relation, kind, label;
   - `layers`: visual grouping and semantic phase;
   - `feedback_loops`: loop name and edge ids;
   - `validation_criteria`: validation labels and attached nodes;
   - `caption`: what the figure demonstrates.
3. For the observability stack preset, use:

```text
skill execution -> reasoning log -> validation -> HTML dashboard -> RFDE monitor -> reflection
```

Include node roles for event streams, validation gates, dashboard projections,
monitor plots, human inspection, and reflective updates.
4. Keep the diagram mechanistic:
   - nodes are process or state components;
   - edges are named relations;
   - feedback edges are visibly distinct;
   - validation criteria and observations are explicit.
5. Save the model as JSON and pass it to `mechanistic-figure-renderer`.

## Command

```bash
python3 paper_skills/mechanistic-diagram-modeler/scripts/build_mechanistic_diagram_model.py \
  --preset mathformer-framework \
  --output paper/figures/mathformer_mechanistic_diagram.json
```

## Guardrails

- Do not draw a box merely because it sounds important; it must correspond to a
  state component, transition relation, validation criterion, or observation surface.
- Do not use unlabeled arrows. Every arrow should correspond to a relation.
- Keep the caption honest: the figure describes the mechanism, not a proof of
  correctness.
- Captions for dashboards and monitors should describe inspection and control,
  not proof.
