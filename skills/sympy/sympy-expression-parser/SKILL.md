---
name: sympy-expression-parser
description: Extract source-backed mathematical expressions from NL/LaTeX into a structured SymPy parse packet with uncertainty and source anchors.
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

# SymPy Expression Parser

Use this skill after source intake for SymPy runs. It extracts formula spans,
stable source-line anchors, source concepts, and candidate SymPy expression
surfaces. Unresolved or ambiguous expressions must be explicit.

Run:

```bash
python skills/sympy/sympy-expression-parser/scripts/parse_sympy_expressions.py \
  --source tests/latex/wiki_level/sum_first_odd_numbers.tex \
  --output artifacts/sympy/wiki_sum_first_odd_numbers/parse_packet.json
```

