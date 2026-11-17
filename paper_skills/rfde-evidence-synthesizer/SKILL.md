---
name: rfde-evidence-synthesizer
description: Turn Reference-Free Descriptive Evaluation artifacts into paper-ready evidence, figures, tables, and narrative claims about autoformalization trajectories. Use when writing empirical or observational sections from RFDE reports, trajectory models, dashboards, or reasoning logs.
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

# RFDE Evidence Synthesizer

## Purpose

Use this skill to surface trajectory evidence from RFDE artifacts in a way that
is readable in a scientific paper. It prioritizes dynamics over terminal scores.

## Inputs

Typical inputs:

- `artifacts/rfde/<run>/rfde_report.json`
- `artifacts/rfde/<run>/rfde_report.md`
- `artifacts/rfde/<run>/trajectory_model.json`
- `artifacts/rfde/<run>/metrics_timeseries.json`
- `artifacts/rfde/<run>/trajectory_timeline.html`
- `artifacts/rfde/<run>/rfde_dashboard.html`
- `artifacts/full_autoformalization_reasoning_log_test/reasoning.html`
- `artifacts/full_autoformalization_reasoning_log_test/skill_application.html`
- `artifacts/reference_free_critic_monitor/<run>/evolution/formalization_evolution.csv`
- `artifacts/reference_free_critic_monitor/<run>/evolution/formalization_evolution.json`
- `artifacts/reference_free_critic_monitor/<run>/evolution/formalization_evolution.svg`

## Workflow

1. Identify the run and source artifact being analyzed.
2. Extract:
   - final status and hard validation criteria;
   - state, action, and transition counts;
   - phase segments and phase transitions;
   - loops and repair episodes;
   - protected metric movements;
   - warnings and limitations;
   - cost surfaces when available.
3. For reasoning logs and monitors, extract:
   - score delta;
   - risk delta;
   - weakest dimension;
   - blocker count;
   - regression count;
   - artifact paths;
   - lifecycle-stage coverage.
4. Build plot/table plans:
   - timeline of phases and validation criteria;
   - small multiples for code lines, grounded concepts, findings, blocking
     findings, anchor coverage, and pass/fail layers;
   - phase-transition table;
   - convergence narrative;
   - cost-normalized progress table.
5. Write paper text that explains what the trajectory shows and what it does
   not prove.

## Paper Claim Rules

- Good claim: "The run exhibits a transition from critic-failing to
  critic-passing after repair."
- Good claim: "The RFDE report exposes under-instrumented phases."
- Bad claim: "The theorem is correct because RFDE passed."
- Bad claim: "The method is generally superior" unless backed by a benchmark or
  controlled comparison.
- Bad claim: "The dashboard certifies the formalization."
- Bad claim: "A monitor improvement replaces backend validation."

Reasoning-log HTML dashboards are human inspection artifacts. Skill-application
JSONL logs are structured episode evidence. Reference-free monitor CSV/JSON/SVG
outputs are trajectory diagnostics.

## Output Shape

Provide:

- a short empirical vignette;
- figure captions;
- a table of trajectory episodes;
- a paper-ready trajectory diagnostics table;
- a limitations paragraph;
- exact artifact paths used as evidence.
