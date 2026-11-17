---
name: physics-equation-parser
description: Parse physics derivation equations into executable SymPy forms, including algebraic equations, differential equations, vector equations, conservation equations, proportionalities, and target equations.
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

# Physics Equation Parser

Use after quantities and units are known. It preserves literal LaTeX, parser
uncertainty, source anchors, and executable `Eq` or residual representations.

The implementation is centered on
`backends.sympy.MathformerPhysicsSympy.pipeline.build_physics_equation_packet()`. It combines
controlled source-equation templates, extracted source units, and the
executable derivation trace.

The parser records:

- algebraic equations,
- differential equations,
- vector or coordinate-projection equations,
- matrix, linear-system, or operator-projection equations,
- conservation equations,
- proportionality statements,
- limiting or approximation statements,
- target equations.

Every parsed record should expose raw LaTeX when available, source anchors,
parser uncertainty, a SymPy form, normalized `Eq(lhs, rhs)`, and residual
form. Target records block complete status if the source target cannot be
parsed or if the executable derivation trace does not derive the target.

The default phase command emits:

```text
artifacts/physics_sympy/<case_id>/equation_packet.json
```

Validate changes with:

```bash
.venv/bin/python tests/physics_sympy/run_phase5_equation_parser.py --json
```
