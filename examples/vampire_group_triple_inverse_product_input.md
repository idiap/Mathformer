<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Give users concrete starting points for running Mathformer workflows on small theorem tasks.

Intent:
  Show how informal inputs, ATP candidates, premise selection, and proof artifacts connect in practice.

Function:
  Contains runnable or readable examples that double as smoke-test material for documentation.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

Let G be a group with multiplication mul, identity element e, and inverse operation inv.
Prove that for all three elements x, y, and z of G, the inverse of the triple
product mul(mul(x,y),z) is the product of the inverses in reverse order:
inv(mul(mul(x,y),z)) = mul(inv(z),mul(inv(y),inv(x))).
