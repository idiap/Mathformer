<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make the framework understandable without requiring readers to inspect implementation details first.

Intent:
  Explain architecture, installation, principles, tutorials, licensing, and generated library outputs.

Function:
  Provides human-facing documentation that should stay aligned with tested behavior and code paths.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# MathformerLib SymPy Physics

This directory indexes executable physics derivations accumulated into
MathformerLib. Entries are organized by solver type under:

```text
libraries/MathformerLib/SympyPhysics/Solvers/
```

Each entry should expose a formal SymPy derivation, validation criteria, and
when applicable a numerical simulation or instantiation that checks the derived
result in an executable setting.

## Solver Types

- `AnalyticSoliton`: closed-form soliton/traveling-wave derivations.
- `PseudoSpectralPDE`: Fourier pseudo-spectral PDE validation runs.

## Entries

### Korteweg-De Vries One-Soliton

- Source: <https://en.wikipedia.org/wiki/Korteweg%E2%80%93De_Vries_equation>
- Analytic derivation:
  `libraries/MathformerLib/SympyPhysics/Solvers/AnalyticSoliton/KdVOneSoliton.py`
- Simulation validation:
  `libraries/MathformerLib/SympyPhysics/Solvers/PseudoSpectralPDE/KdVOneSolitonSimulation.py`
- Test:
  `tests/physics_sympy/run_mathformerlib_kdv.py`

The entry uses the sign convention:

```latex
\phi_t+\phi_{xxx}-6\phi\phi_x=0.
```

The verified one-soliton is:

```latex
\phi(x,t)=-\frac{c}{2}\operatorname{sech}^2
\left(\frac{\sqrt c}{2}(x-ct-a)\right),\quad c>0.
```

Validation includes:

- direct symbolic PDE residual check in SymPy,
- traveling-wave reduced ODE residual check,
- parameter-condition derivation for the `sech^2` ansatz,
- numeric symbolic residual samples,
- pseudo-spectral RK4 simulation against the analytic soliton.

Run:

```bash
python tests/physics_sympy/run_mathformerlib_kdv.py --json
```

## Human-Readable Physics Reports

Physics SymPy artifacts also render a human-facing derivation report. The
Phase 17 report is designed for inspection rather than only machine checking:
it places the source step, generated gap-closure substeps, SymPy expression,
unit/dimension check, and validation status side by side.

The same report renders:

- source equation nodes, generated support nodes, law/API/rule edges, blocker
  nodes, and the target derivation path,
- a unit-flow table showing dimension preservation through each step,
- RFDE trajectory tables and plots for gap closure, dimensional consistency,
  executable step count, and target-derivation residual.

Run:

```bash
python tests/physics_sympy/run_phase17_human_reports.py --json
```

Representative outputs are written under:

```text
artifacts/physics_sympy/phase17_human_reports/
```
