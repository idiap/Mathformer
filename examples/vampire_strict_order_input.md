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

Let r be a binary relation. Assume r is transitive: whenever r(x,y) and r(y,z), r(x,z).
Assume r is irreflexive: r(x,x) never holds.
Prove that r is asymmetric: if r(x,y), then not r(y,x).
