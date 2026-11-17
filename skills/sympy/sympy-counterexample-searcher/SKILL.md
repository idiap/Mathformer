---
name: sympy-counterexample-searcher
description: Search admissible bounded domains for counterexamples to generated SymPy claims and report concrete witnesses rather than hiding failed samples.
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

# SymPy Counterexample Searcher

Use this skill after symbolic validation. It searches a source-backed bounded
domain and writes any counterexamples as first-class report entries.

