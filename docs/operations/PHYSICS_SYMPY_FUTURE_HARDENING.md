<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

#
#

# Physics SymPy Future Hardening Ledger

This ledger keeps the broad future-hardening themes for the Physics SymPy
backend explicit without leaving them as an unchecked umbrella TODO in the
top-level project plan.

## Controlled Expansion Themes

| Theme | Current Control Surface | Expansion Policy |
| --- | --- | --- |
| Richer vector mechanics | `physics_sympy` controlled suite and dimension/unit adversaries | Add cases only with explicit frames, basis conventions, component-vs-vector semantics, and executable SymPy checks. |
| Approximation-regime adversaries | regime assumption modeling and adversarial unit/dimension suite | Add small-parameter, asymptotic, and dropped-term cases only when the approximation order and validity domain are represented in the artifact. |
| Plotted RFDE trajectories | RFDE evaluation family and artifact reporting | Add plots as derived evidence only after the symbolic/numeric trace is reproducible and the plot script is checked. |
| Broader paper/textbook physics extraction | paper/textbook source extraction workflows plus physics symbol/gap expansion | Promote new extracted derivations only when source anchors, implicit-gap expansion, unit/dimension checks, and execution interpretation pass. |

## Promotion Rule

New hardening cases should enter through the relevant controlled family
(`physics_sympy`, `rfde`, `paper`, or `textbook`) and must expose deterministic
validation evidence before they are treated as backend capability rather than a
research candidate.
