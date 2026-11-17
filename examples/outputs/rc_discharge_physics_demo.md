<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Preserve a compact demonstration output for the README physics example.

Intent:
  Summarize the executable SymPy validation for RC discharge without requiring
  the reader to inspect the full generated report under artifacts/.

Function:
  Records the target equation, validation status, metrics, and derivation trace
  for the RC discharge demonstration.

Maintenance Notes:
  Regenerate or revise this summary when the controlled physics SymPy suite
  changes.
-->

# RC Discharge Physics Demo

Source fixture:

- [RC discharge LaTeX source](../../tests/physics_sympy/controlled_latex/rc_discharge.tex)

Generated SymPy artifact:

- [AutoformalizedRcDischarge.py](../../backends/sympy/MathformerSympyPhysics/AutoformalizedRcDischarge.py)

Target:

```text
dV/dt = -V/(R C), V(0)=V0  ->  V(t)=V0 exp(-t/(R C))
```

Generated run:

```text
artifacts/physics_sympy/controlled_suite/rc_discharge/
```

Status:

- case: `rc_discharge`
- status: `complete`
- aggregate score: `1.000`

Selected validation criteria:

- `all_source_targets_represented`: `true`
- `all_derivation_steps_execute`: `true`
- `all_equations_dimensionally_consistent`: `true`
- `target_expression_computed_from_steps`: `true`
- `numeric_sanity_no_counterexample`: `true`

Derivation trace:

- `step_01_ode_residual`: `0` via verify ODE solution
- `step_02_initial_condition`: `V0` via apply `V(0)=V0`
- `step_03_solution`: `V0*exp(-t/(C*R))` via separable ODE solution

Generated local report files:

- `physics_consistency_report.md`
- `physics_consistency_report.json`
- `physics_consistency_report.html`
