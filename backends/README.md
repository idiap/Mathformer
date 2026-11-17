<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Backends

Backend implementations and backend-specific generated artifacts are grouped
here while retaining their established component names:

- `atp/MathformerATP/`: TPTP generation and Vampire proof search.
- `isabelle/Isabelle/`: Isabelle/HOL theory artifacts and session metadata.
- `lean/Mathformer.lean` and `lean/Mathformer/`: Lean library root and
  autoformalization modules.
- `lean/Main.lean`: sample Lean executable entrypoint.
- `premise_kb/MathformerKB/`: premise storage, indexing, and retrieval.
- `rocq/MathformerRocq/`: Rocq proof artifacts.
- `sympy/MathformerSympy/`: general mathematical SymPy artifacts.
- `sympy/MathformerPhysicsSympy/`: reusable physics derivation pipeline.
- `sympy/MathformerSympyPhysics/`: generated executable physics artifacts.

Reusable cross-run libraries live separately under `libraries/`.
