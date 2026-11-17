---
name: sympy-execution-runner
description: Execute generated SymPy artifacts, collect symbolic/numeric/trace outputs, and reject placeholder-only or non-runnable formalizations.
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

# SymPy Execution Runner

Use immediately after a SymPy artifact is drafted.

Run:

```bash
python skills/sympy/sympy-execution-runner/scripts/run_sympy_artifact.py \
  --artifact backends/sympy/MathformerSympy/AutoformalizedSumFirstOddNumbers.py \
  --output artifacts/sympy/wiki_sum_first_odd_numbers/execution_report.json
```

