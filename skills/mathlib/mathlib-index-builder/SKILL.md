---
name: mathlib-index-builder
description: Build and validate a first-class Mathlib module/declaration/import index with version stamps, theorem-shape summaries, doc-comment metadata, declaration graph links, import-cost estimates, and stale-index detection. Use before Mathlib navigation, concept annotation, or controlled Lean drafting needs shared Mathlib evidence.
---


# Mathlib Index Builder

Use this skill when Mathformer needs a reusable Mathlib index instead of
rescanning source files inside each workflow.

Run:

```bash
python skills/mathlib/mathlib-index-builder/scripts/build_mathlib_index.py --json
```

For fast checks:

```bash
python skills/mathlib/mathlib-index-builder/scripts/build_mathlib_index.py --max-files 160 --json
```

The index records module metadata, declaration metadata, imports, imported-by
edges, theorem-shape summaries, doc comments, import-cost estimates, and a
lightweight declaration graph. Use `--validate-existing` to fail if the
existing index was built against a different Lean or Mathlib revision.
