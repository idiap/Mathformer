---
name: sympy-consistency-report-orchestrator
description: Build a reference-free consistency report for SymPy artifacts by merging parse, assumption, grounding, execution, identity, counterexample, and trace reports into backend-specific metrics.
---

<!--
File Documentation

Motivation:
  Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

Intent:
  Tell coding agents what context to load, what invariants to preserve, and how to validate their work.

Function:
  Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# SymPy Consistency Report Orchestrator

Use this skill at the end of a SymPy backend run. It surfaces reference-free
metrics for symbolic algebra autoformalization:

- parse coverage
- assumption fidelity
- API-grounding density
- symbolic equivalence
- numeric robustness
- counterexample absence
- transformation trace executability
- source-anchor coverage
- artifact realness

