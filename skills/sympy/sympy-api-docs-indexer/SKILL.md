---
name: sympy-api-docs-indexer
description: Build a local, versioned SymPy API index from installed modules so symbolic autoformalization can cite concrete functions, classes, signatures, docs, and source files.
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

# SymPy API Docs Indexer

Use this skill before grounding source concepts into SymPy. It creates a compact
JSON API index from the locally installed package and records version/source
provenance.

Default output:

```bash
python skills/sympy/sympy-api-docs-indexer/scripts/index_sympy_api.py \
  --output artifacts/sympy_api/index.json
```

Self-test:

```bash
python skills/sympy/sympy-api-docs-indexer/scripts/index_sympy_api.py --self-test --json
```

