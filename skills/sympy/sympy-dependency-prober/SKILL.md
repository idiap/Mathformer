---
name: sympy-dependency-prober
description: Probe the local Python environment for the SymPy backend dependencies and emit a versioned availability report before symbolic autoformalization runs.
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

# SymPy Dependency Prober

Use this skill before a SymPy backend run. It checks required and optional
packages, reports versions, and distinguishes blocking missing packages from
optional accelerators.

Required packages for the first backend style:
- `sympy`
- `mpmath`
- `numpy`
- `pydantic`
- `pylatexenc`

Recommended packages:
- `hypothesis`
- `pytest`
- `lark`
- `latex2sympy2_extended`
- `beautifulsoup4`
- `requests`
- `sphinx`
- `sphinx_autodoc_typehints`
- `networkx`
- `pandas`
- `plotly`
- `z3`

Run:

```bash
python skills/sympy/sympy-dependency-prober/scripts/probe_sympy_dependencies.py --json
```

