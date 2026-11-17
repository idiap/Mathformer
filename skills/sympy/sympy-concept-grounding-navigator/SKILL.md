---
name: sympy-concept-grounding-navigator
description: Map extracted mathematical concepts to concrete SymPy APIs using the local API index, with ranked candidates and explicit evidence.
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

# SymPy Concept Grounding Navigator

Use this skill after source parsing and before SymPy drafting. It maps concepts
such as finite sums, simplification, polynomial normalization, derivatives, and
matrix operations to local SymPy API candidates.

Run:

```bash
python skills/sympy/sympy-concept-grounding-navigator/scripts/ground_sympy_concepts.py \
  --concept finite_sum --concept symbolic_simplification \
  --api-index artifacts/sympy_api/index.json \
  --output artifacts/sympy/wiki_sum_first_odd_numbers/api_grounding.json
```

