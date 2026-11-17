---
name: sympy-assumption-modeler
description: Extract and validate SymPy assumptions from source text and parse packets, including natural-number, integer, real, positivity, nonzero, and bounded sampling domains.
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

# SymPy Assumption Modeler

Use this skill after expression parsing. It produces a source-backed assumption
packet and flags any generated assumptions that are not literal source claims.

Run:

```bash
python skills/sympy/sympy-assumption-modeler/scripts/model_sympy_assumptions.py \
  --parse-packet artifacts/sympy/wiki_sum_first_odd_numbers/parse_packet.json \
  --output artifacts/sympy/wiki_sum_first_odd_numbers/assumptions.json
```

