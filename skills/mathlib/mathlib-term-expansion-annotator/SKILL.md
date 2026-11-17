---
name: mathlib-term-expansion-annotator
description: Expand informal mathematical terms into probable Mathlib concept annotations with domain disambiguation, phrase-level matching, proof-role labels, evidence spans, ambiguity gates, and explicit gap states. Use before declaration search or drafting prompts rely on informal Mathlib concepts.
---


# Mathlib Term Expansion Annotator

Use this skill after source text is available and before declaration search.

Run:

```bash
python skills/mathlib/mathlib-term-expansion-annotator/scripts/annotate_mathlib_terms.py \
  --text "A compact set with the finite intersection property is nonempty." \
  --json
```

Self-test:

```bash
python skills/mathlib/mathlib-term-expansion-annotator/scripts/annotate_mathlib_terms.py --self-test --json
```

The output is advisory until Lean verification and import checks succeed. If
domain clues are missing or conflicting, the annotation remains ambiguous or a
gap instead of collapsing to the top lexical declaration.
