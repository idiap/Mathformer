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

# KdV One-Soliton: Analytic SymPy Derivation

Source: <https://en.wikipedia.org/wiki/Korteweg%E2%80%93De_Vries_equation>

Solver type: `AnalyticSoliton`

Module:
`libraries/MathformerLib/SympyPhysics/Solvers/AnalyticSoliton/KdVOneSoliton.py`

## Claim

For the KdV sign convention

```latex
\phi_t+\phi_{xxx}-6\phi\phi_x=0,
```

the traveling-wave one-soliton

```latex
\phi(x,t)=-\frac{c}{2}\operatorname{sech}^2
\left(\frac{\sqrt c}{2}(x-ct-a)\right)
```

solves the equation for `c > 0`.

## Derivation Shape

1. Introduce the traveling coordinate `z = x - c t - a`.
2. Set `phi(x,t)=f(z)`.
3. Reduce the PDE to `-c f' + f''' - 6 f f' = 0`.
4. Integrate once using the decay boundary condition:
   `f'' - c f - 3 f^2 = 0`.
5. Use the localized ansatz `f(z)=-A sech(B z)^2`.
6. Matching coefficients gives `B^2=c/4` and `A=c/2`.
7. Substitution yields the target soliton.

## Validation

The module verifies:

- `phi_t + phi_xxx - 6 phi phi_x = 0`,
- `f'' - c f - 3 f^2 = 0`,
- numeric symbolic residual samples,
- generated support steps are marked as generated.

