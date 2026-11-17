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

# KdV One-Soliton: Pseudo-Spectral PDE Validation

Solver type: `PseudoSpectralPDE`

Module:
`libraries/MathformerLib/SympyPhysics/Solvers/PseudoSpectralPDE/KdVOneSolitonSimulation.py`

This validation evolves the KdV equation

```latex
\phi_t+\phi_{xxx}-6\phi\phi_x=0
```

from the analytic one-soliton initial condition using Fourier pseudo-spectral
spatial derivatives and RK4 time stepping. The evolved state is compared against
the analytic soliton at the final time.

Default validation parameters:

- domain length `L = 80`,
- grid size `N = 256`,
- final time `T = 0.05`,
- time step `dt = 0.001`,
- tolerance `1e-8`.

Run:

```bash
python tests/physics_sympy/run_mathformerlib_kdv.py --json
```
