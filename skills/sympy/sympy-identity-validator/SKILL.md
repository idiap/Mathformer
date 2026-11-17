---
name: sympy-identity-validator
description: Validate SymPy equational claims through symbolic normalization methods such as simplify, expand, polynomial normalization, and summation evaluation.
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

# SymPy Identity Validator

Use this skill when an artifact exposes `build_expressions()`. It validates the
core equality independently of the artifact's own `validate_symbolic()` wrapper.

