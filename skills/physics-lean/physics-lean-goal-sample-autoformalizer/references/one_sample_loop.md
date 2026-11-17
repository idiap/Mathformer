<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# One-Sample Recursive Autoformalization Loop

## Goal State

A sample is complete only when deterministic gates report
`complete_autoformalization` for that case and no open markers remain in the
case file. Compiling Lean is necessary but not sufficient.

## Recursive Expansion Policy

Work over mathematical objects before editing the target theorem. If the sample
mentions a physics object that is missing or shallow, route it through
MathformerPhysicsLib first:

1. Search existing foundation modules and Mathlib-grounded facades.
2. Reuse a declaration when available.
3. Add or promote the smallest MathformerPhysicsLib support surface when reuse
   is not available.
4. Verify the support module independently.
5. Only then repair the sample theorem or bridge declarations.

Every iteration must re-enumerate:

- active pathology categories;
- detected physics mathematical objects;
- MathformerPhysicsLib workbench decisions;
- deterministic repair actions;
- generative repair proposals and their rerun gates;
- expansion-map nodes;
- recursive controller status.

## Completion Checklist

- The case file compiles with `lake env lean`.
- `run_grounded_sample_thoroughness.py --case <case>` returns `ok: true` and
  `status: complete_autoformalization`.
- No `sorry`, `admit`, `TODO`, `FIXME`, `GeneratedSupportAssumption`, stale
  `cycle` naming, or unnecessary `_from_frontier` helper names remain.
- Newly introduced foundation support passes the foundation verifier.
- Generative repair suggestions are represented as advisory evidence and are
  not treated as accepted until deterministic gates pass.

## Stop Conditions

- `complete`: all case gates pass and no open markers remain.
- `recurse`: outstanding nodes remain and the recursive controller signature is
  new.
- `blocked`: the signature repeats, the iteration limit is reached, the
  expansion map is not exhaustive, or a hard missing-dependency blocker exists.
