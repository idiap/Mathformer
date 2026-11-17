<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Libraries

Reusable, promotion-controlled Mathformer libraries are grouped here:

- `MathformerLib/`: reusable mathematical formalizations and SymPy solvers.
- `MathformerPhysicsLib/`: reusable Lean, Isabelle, and SymPy physics artifacts.

The Lean root modules `MathformerLib.lean` and `MathformerPhysicsLib.lean` live
beside their module directories. Lake resolves both libraries from this source
root.
