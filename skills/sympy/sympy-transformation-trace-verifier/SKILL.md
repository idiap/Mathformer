---
name: sympy-transformation-trace-verifier
description: Verify that each SymPy transformation trace step has input, output, cited API or rule, and executable preservation evidence.
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

# SymPy Transformation Trace Verifier

Use this skill after execution. It inspects the artifact's `explain_trace()`
output and rejects trace steps without inputs, outputs, or API/rule citations.

