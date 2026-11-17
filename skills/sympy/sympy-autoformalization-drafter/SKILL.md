---
name: sympy-autoformalization-drafter
description: Generate executable SymPy autoformalization artifacts from source parse, assumption, and API-grounding packets while preserving source prose, LaTeX, and anchors.
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

# SymPy Autoformalization Drafter

Use this skill after expression parsing, assumption modeling, and API grounding.
It writes an importable Python artifact under `backends/sympy/MathformerSympy/` with the
standard contract:

- `CLAIM`
- `build_symbols()`
- `build_expressions()`
- `validate_symbolic()`
- `validate_numeric_samples()`
- `explain_trace()`

Generic controlled-case run:

```bash
python skills/sympy/sympy-autoformalization-drafter/scripts/draft_sympy_case.py \
  --parse-packet artifacts/sympy/wiki_sum_first_odd_numbers/parse_packet.json \
  --assumptions artifacts/sympy/wiki_sum_first_odd_numbers/assumptions.json \
  --grounding artifacts/sympy/wiki_sum_first_odd_numbers/api_grounding.json \
  --output backends/sympy/MathformerSympy/AutoformalizedSumFirstOddNumbers.py
```

The legacy sum-specific script remains available as `scripts/draft_sympy_wiki_case.py`
for compatibility, but new controlled examples should use `draft_sympy_case.py`.
