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

# Mathformer Physics SymPy Backend

The physics SymPy backend extends Mathformer’s symbolic-algebra path from
standalone identities to executable physics derivations. The implemented style
is `sympy_physics_derivation_trace`.

The backend treats a physics derivation as a source-anchored computational
trace: source NL/LaTeX, quantity bindings, assumptions, units, dimensions,
coordinate-frame notes, implicit generated steps, physical-law grounding,
symbolic verification, numeric sanity checks, and a consistency report.

## Scope And Completion Semantics

The backend style is `sympy_physics_derivation_trace`. It is deliberately
distinct from `sympy_equational_trace`: the physics style carries source laws,
quantity meanings, units, dimensions, regimes, frames, sign conventions, and
generated-support labels in addition to executable SymPy equations.

The first supported domains are single-particle kinematics, Newtonian
point-mass dynamics, harmonic oscillator derivations, elementary energy/work
derivations, idealized circuit ODE derivations, and elementary thermodynamic
identity manipulations. Tensor calculus and general relativity, continuum
mechanics, gauge-field derivations, quantum noncommuting operator algebra, and
stochastic differential physics are deferred until the first scalar/vector
trace slice is stable.

A complete artifact must preserve the source NL/LaTeX and anchors, expose
source-backed equations as SymPy objects, expand implicit algebraic/calculus
and substitution steps, label generated support equations, declare assumptions
and conventions, perform unit and dimensional checks, derive the target from
the executable chain, and avoid unresolved placeholders or unexecuted steps.

Reports use three completion statuses:

- `complete`: all derivation steps execute and all validation criteria pass.
- `draft`: useful executable partial evidence exists, but non-blocking
  validation remains unresolved.
- `blocked`: a missing law, missing condition, inconsistent units, or
  ambiguous convention prevents a truthful complete artifact.

The executable contract lives in `backends.sympy.MathformerPhysicsSympy.pipeline` as
`physics_sympy_phase0_contract()` and
`classify_physics_sympy_completion()`. The regression check is
`tests/physics_sympy/run_phase0_contract.py`.

## Dependencies And Physics Package Grounding

The dependency prober checks the SymPy physics stack before a derivation trace
runs. Required surfaces are SymPy core, `sympy.physics.units`,
`sympy.physics.units.systems.si`, `sympy.physics.mechanics`,
`sympy.physics.vector`, and NumPy. Optional surfaces are SciPy for numeric ODE
checks, Pint for independent unit-conversion cross-checks, and
Matplotlib/Plotly for diagnostics.

Missing required dependencies block complete status. Missing optional
dependencies do not fail the dependency probe; they disable only the dependent
optional checks and are recorded in the report.

The standard report path is:

```text
artifacts/physics_sympy/<case_id>/dependency_probe.json
```

The report includes a versioned `physics_sympy_api_index_v1` shard covering
SymPy physics modules, SI/unit systems, dimension systems, mechanics/vector
APIs, and solver/calculus APIs used by derivations. The regression check is
`tests/physics_sympy/run_phase1_dependency_grounding.py`.

## Source Intake And Derivation Units

The source extractor turns a controlled physics source into typed derivation
units. It preserves the source anchors and emits units for quantity
definitions, physical laws, constitutive relations, coordinate context,
initial and boundary conditions, approximation regimes, algebraic steps,
calculus steps, substitution steps, and target equations.

Every extracted unit carries:

- source anchors,
- literal natural-language text,
- literal LaTeX when present,
- inferred symbols,
- candidate dimensions,
- candidate units,
- unresolved ambiguity notes.

The controlled fixture set covers constant-acceleration kinematics, simple
harmonic oscillator period, work-energy theorem, RC discharge, ideal gas law
manipulation, and projectile range on level ground. The executable extractor is
`extract_physics_source_units()` in `backends.sympy.MathformerPhysicsSympy.pipeline`; the
regression check is `tests/physics_sympy/run_phase2_source_extraction.py`.

## Symbol Table And Binding Discipline

The symbol-table builder converts source units into a typed binding packet. It
distinguishes scalar variables, vector quantities, functions of time,
parameters/constants, generated dummy variables, coordinate axes or basis
helpers, and unit/dimension entries.

Each symbol receives a stable semantic ID derived from its namespace, meaning,
dimension, and unit rather than from display spelling alone. This lets later
phases compare bindings even when notation changes.

The builder reports binding diagnostics for incompatible symbol reuse, missing
binders, ambiguous constants such as `k`, `c`, `R`, `T`, and `E`, overloaded
notation such as `v`, mixed scalar/vector use, implicit functions of time, and
generated symbols that were accidentally marked source-backed. Generated dummy
variables and coordinate helpers are marked as generated support and never as
source-backed claims.

The executable builder is `build_physics_symbol_table()` in
`backends.sympy.MathformerPhysicsSympy.pipeline`; the regression check is
`tests/physics_sympy/run_phase3_symbol_table.py`.

## Dimension And Unit Modeling

The dimension modeler builds the first executable unit-and-dimension packet
after source intake and symbol binding. It records SI base dimensions for
length, mass, time, electric current, temperature, amount of substance,
luminous intensity, and dimensionless angle or pure-number quantities.

The unit grounder records common SI and derived units: meter, kilogram,
second, ampere, kelvin, mole, newton, joule, watt, pascal, coulomb, volt,
ohm, and radian. Source-specific or composite units are preserved explicitly
instead of being silently normalized away.

Where available, the packet grounds the model in SymPy unit-system objects:
`Quantity`, `Dimension`, `DimensionSystem`, `UnitSystem`, and SI from
`sympy.physics.units.systems.si`. The inference rules cover sums, products,
powers, derivatives, integrals, transcendental functions, exponentials,
logarithms, and trigonometric arguments.

The standard report path is:

```text
artifacts/physics_sympy/<case_id>/dimension_packet.json
```

The packet includes quantity-to-dimension maps, quantity-to-unit maps, inferred
step dimensions, unresolved dimensions, conflicting dimensions, and source
anchors for source-backed claims. The executable builders are
`build_physics_dimension_packet()` and `build_physics_unit_packet()` in
`backends.sympy.MathformerPhysicsSympy.pipeline`; the regression check is
`tests/physics_sympy/run_phase4_dimension_units.py`.

## Equation Parsing And Normalization

The equation parser turns source equations, curated controlled-case laws, and
executable derivation traces into a normalized equation packet. It preserves
raw LaTeX and source anchors while exposing executable SymPy forms.

The parser records these equation forms:

- algebraic equations,
- differential equations,
- vector or coordinate-projection equations,
- matrix, linear-system, or operator-projection equations,
- conservation equations,
- proportionality statements,
- limiting or approximation statements,
- target equations.

Each parsed record carries a SymPy form, normalized `Eq(lhs, rhs)`, residual
form, source-backing status, generated-support flag, parser uncertainty notes,
and source anchors. Differential and integral records preserve `Derivative`
and `Integral` forms where available. ODE solution traces are marked when the
derivation uses `dsolve`-compatible structure or explicit integration.

The standard report path is:

```text
artifacts/physics_sympy/<case_id>/equation_packet.json
```

Complete status is blocked when the source target equation cannot be parsed or
when the target is not explicitly derived from the executable intermediate
trace. The executable builder is `build_physics_equation_packet()` in
`backends.sympy.MathformerPhysicsSympy.pipeline`; the regression check is
`tests/physics_sympy/run_phase5_equation_parser.py`.

## Assumptions, Regimes, Frames, And Conditions

The regime modeler makes contextual physics assumptions explicit before gap
expansion and drafting. It records source-backed assumptions, regime
categories, side-condition hints, initial and boundary conditions, and
silent-strengthening checks.

The supported assumption catalog includes constant acceleration,
frictionless/no-damping/no-drag regimes, small-angle approximations,
nonrelativistic speed assumptions, massless spring/string assumptions, ideal
gas assumptions, lumped circuit elements, steady or quasistatic regimes, and
positivity/nonzero restrictions. A category can be supported by the catalog
even when a particular source case does not instantiate it.

The standard regime report path is:

```text
artifacts/physics_sympy/<case_id>/regime_assumption_packet.json
```

The frame-context builder records axis orientation, origin, positive direction,
basis vectors, scalar projection from vector laws, and one-dimensional
reductions. Unstated origins are preserved as `source_unspecified` rather than
invented.

The standard frame report path is:

```text
artifacts/physics_sympy/<case_id>/frame_context_packet.json
```

The executable builders are `build_physics_regime_assumption_packet()` and
`build_physics_frame_context_packet()` in `backends.sympy.MathformerPhysicsSympy.pipeline`;
the regression check is
`tests/physics_sympy/run_phase6_assumptions_frames.py`.

## Implicit Gap Detection And Closure

The gap detector turns compressed physics derivations into explicit repair
targets. It scans the source transition list and classifies missing work as
algebra, substitution, calculus, ODE solving, law invocation, initial-condition
application, approximation justification, coordinate projection, unit
conversion, or cancellation side-condition closure.

The standard detection report path is:

```text
artifacts/physics_sympy/<case_id>/implicit_gap_packet.json
```

The gap expander then emits generated-support substeps. Each generated closure
records the source predecessor and successor anchors, the rule/API/law used,
input and output expressions, side conditions, source backing, and a local
dimension check. Generated steps are support records; they are not rewritten as
literal source statements.

The standard expansion report path is:

```text
artifacts/physics_sympy/<case_id>/gap_expansion_packet.json
```

Completion is blocked whenever an expansion packet still contains unresolved
gaps. The executable builders are `build_physics_gap_detection_packet()` and
`build_physics_gap_expansion_packet()` in `backends.sympy.MathformerPhysicsSympy.pipeline`;
the regression check is
`tests/physics_sympy/run_phase7_gap_detection_expansion.py`.

## Physics Law And API Grounding

The law/API grounder separates two kinds of support that are easy to confuse:
physical laws and constitutive relations on one side, algebraic or calculus API
operations on the other. A source law such as Hooke's law, Ohm's law, the ideal
gas law, or the work-energy relation is grounded to a computable template. A
transition rule such as substitution, simplification, integration, ODE solving,
vector projection, or unit conversion is grounded to an installed SymPy API
surface.

The global law catalog includes Newton's second law, Hooke's law, the
work-energy relation, conservation of mechanical energy, Ohm's law, the
capacitor relation, the ideal gas law, and the first-law thermodynamic sign
convention. Case-local laws that do not match a compact global template are
preserved as source-backed local templates instead of being silently discarded.

The standard law/API report path is:

```text
artifacts/physics_sympy/<case_id>/law_api_grounding_packet.json
```

Every law use records either `source_backed` or `generated_support` provenance
with an explicit justification. Completion is blocked if a law use lacks
provenance or if a required mathematical operation has no grounded API. The
executable builder is `build_physics_law_api_grounding_packet()` in
`backends.sympy.MathformerPhysicsSympy.pipeline`; the regression check is
`tests/physics_sympy/run_phase8_law_api_grounding.py`.

## Derivation Planning And Executable Artifact Contract

The derivation planner turns the prior packets into a topologically ordered
execution plan. The order is fixed: quantities, dimensions and units,
assumptions/regimes/frames, source equations, generated gap closures, target
derivation chain, and validation calls. Each job names its dependencies, its
outputs, and the packet or trace that justifies it.

The standard derivation-plan report path is:

```text
artifacts/physics_sympy/<case_id>/derivation_plan_packet.json
```

The generated Python artifact contract requires `CLAIM`, `QUANTITY_TABLE`,
`DIMENSION_MODEL`, `ASSUMPTIONS`, `DERIVATION_STEPS`, `build_symbols()`,
`build_units()`, `build_equations()`, `derive_target()`,
`validate_dimensions()`, `validate_derivation_steps()`,
`validate_numeric_samples()`, and `explain_trace()`. Final expressions must be
computed from the derivation chain rather than stored as hidden hand-computed
answers.

The executable builder is `build_physics_derivation_plan_packet()` in
`backends.sympy.MathformerPhysicsSympy.pipeline`; the artifact drafter is `write_artifact()`;
the regression check is
`tests/physics_sympy/run_phase9_derivation_plan_artifact_contract.py`.

## Unit And Dimensional Analysis Validation

The unit verifier checks the executable trace after planning and drafting
surfaces are available. It emits per-equation dimension checks, per-step
dimension-preservation checks, generated unit-conversion checks, and diagnostic
buckets for conflicting dimensions, missing units, and non-dimensionless
arguments to functions such as `sin`, `exp`, and `log`.

The standard unit-analysis report path is:

```text
artifacts/physics_sympy/<case_id>/unit_analysis_report.json
```

Unit or dimension inconsistency is a critical blocker for complete status and
is reported with blocker code `inconsistent_units_or_dimensions`. The verifier
also runs adversarial checks for patterns such as adding position to velocity,
exponentiating dimensional time, and taking the sine of dimensional length.

The executable builder is `build_physics_unit_analysis_packet()` in
`backends.sympy.MathformerPhysicsSympy.pipeline`; the regression check is
`tests/physics_sympy/run_phase10_unit_dimension_validation.py`.

## Step Execution, Equivalence, And ODE Validation

The step verifier checks the executable derivation trace after units,
assumptions, frames, gaps, and derivation planning have been surfaced. It
records algebraic equivalence checks, substitution checks, calculus checks,
ODE-solution checks, approximation or branch-condition checks, and
vector-to-scalar projection checks.

The standard step-execution report path is:

```text
artifacts/physics_sympy/<case_id>/step_execution_report.json
```

The verifier keeps the older `step_verification()` result inside
`legacy_step_verification`, but the public `step_verify` phase now emits the
richer Phase 11 packet. For ODE examples such as RC discharge, the packet
substitutes the candidate solution into the differential equation, verifies the
initial condition, simplifies residuals, and reuses admissible numeric samples.
For vector reductions, it requires a projection axis, a sign or coordinate
convention, and dimensional consistency for the component equation.

The executable builder is `build_physics_step_execution_packet()` in
`backends.sympy.MathformerPhysicsSympy.pipeline`; the regression check is
`tests/physics_sympy/run_phase11_step_execution_equivalence.py`.

## Numeric Sanity, Counterexamples, And Regime Sampling

The numeric sanity sampler runs after symbolic step validation. It builds a
small deterministic sampling domain from the declared physics regime: positive
mass and spring constants, positive resistance and capacitance, nonnegative
time, nonzero denominator quantities, and bounded regime variables such as the
projectile angle. It evaluates the source target and computed target under each
sample and records residuals.

The standard numeric-sanity report path is:

```text
artifacts/physics_sympy/<case_id>/numeric_sanity_report.json
```

If a sample fails, the counterexample record includes sampled values,
units/dimensions, the failed equation residual, the failed step ID, and source
anchors. Numeric sampling is supporting evidence only: complete status still
requires symbolic step validation from Phase 11.

The executable builder is `build_physics_numeric_sanity_packet()` in
`backends.sympy.MathformerPhysicsSympy.pipeline`; the regression check is
`tests/physics_sympy/run_phase12_numeric_sanity_sampling.py`.

See the [Lean-inspired SymPy enrichment plan](PHYSICS_SYMPY_LEAN_INSPIRED_ENRICHMENT_PLAN.md)
for the Lean-inspired enrichment of this backend. The implementation keeps SymPy at the
equational level while adding richer quantity surfaces, assumption-context
encoding, equation graphs, projection bridges, equational semantics critics,
final equation reviewers, and localized monotonic refinement.

## Artifact Contract

Generated artifacts live under `backends/sympy/MathformerSympyPhysics/` and expose:

- `CLAIM`
- `QUANTITY_TABLE`
- `ASSUMPTIONS`
- `DERIVATION_STEPS`
- `QUANTITY_SURFACE`
- `EQUATION_GRAPH`
- `LAW_TABLE`
- `PROJECTION_BRIDGES`
- `CONTEXT_ASSUMPTIONS`
- `SIDE_CONDITIONS`
- `EQUIVALENCE_CERTIFICATES`
- `build_symbols()`
- `build_units()`
- `build_equations()`
- `derive_target()`
- `validate_dimensions()`
- `validate_derivation_steps()`
- `validate_numeric_samples()`
- `validate_symbolic()`
- `validate_equational_semantics()`
- `validate_assumption_context()`
- `validate_projection_bridges()`
- `validate_no_hidden_target()`
- `validate_law_usage()`
- `review_final_equations()`
- `explain_trace()`
- `run_all()`

Each artifact computes the target through executable SymPy steps. Source-backed
steps retain source anchors; generated gap-closure steps are marked as generated
support.

## Skill Loop

The hook contract defines `sympy_physics_derivation_trace_loop` with these
phases:

1. `physics.dependencies.probe`
2. `physics.source.extract`
3. `physics.informal.elicit`
4. `physics.informal.expand`
5. `physics.informal.review`
6. `physics.symbols.build`
7. `physics.dimensions.model`
8. `physics.units.ground`
9. `physics.equations.parse`
10. `physics.regimes.model`
11. `physics.frames.build`
12. `physics.gaps.detect`
13. `physics.gaps.expand`
14. `physics.laws.ground`
15. `physics.sympy.workflow.plan`
16. `physics.sympy.equation_surface.build`
17. `physics.sympy.assumptions.encode`
18. `draft.physics_sympy_derivation`
19. `execute.physics_sympy_derivation`
20. `execute.physics_sympy_interpret`
21. `physics.units.verify`
22. `physics.steps.verify`
23. `physics.numeric.sample`
24. `critique.physics_sympy_semantics`
25. `critique.physics_sympy_dimensions`
26. `review.physics_sympy_final_equations`
27. `review.mathematical_sympy_final_equations`
28. `refine.physics_sympy_review`
29. `consistency.physics_derivation_report`

The direct routes include requests such as “autoformalize physics derivation
with SymPy”, “derive physics result in SymPy”, “run physics unit analysis”,
“close implicit physics derivation gaps”, and “verify physics derivation trace”.

The loop also recommends `critique.reference_free_monitor` and
`evaluation.rfde_report` after the Phase 13 consistency report. Runtime payloads
should preserve `duration_ms` and `agent_usage` so RFDE trajectory reports can
show both metric evolution and cost trace evidence across refinement cycles.

The hook and loop contract is checked by
`tests/physics_sympy/run_phase14_workflow_hooks.py`.

The enriched loop includes SymPy-specific analogues of the Lean physics control
surfaces:

- `physics-sympy-workflow-orchestrator`
- `physics-sympy-equation-surface-builder`
- `physics-sympy-assumption-context-encoder`
- `physics-sympy-execution-interpreter`
- `physics-sympy-equational-semantics-critic`
- `physics-sympy-dimension-projection-critic`
- `physics-sympy-generative-critic-orchestrator`
- `physics-sympy-final-equation-reviewer`
- `mathematical-sympy-final-equation-reviewer`
- `physics-sympy-review-refinement-router`
- `physics-sympy-formal-answer-reflector`

These additions reuse the existing mathematical SymPy skills, physics
preformalization skills, web-supported derivation expansion skills, and current
physics SymPy execution/validation stack before adding backend-specific
behavior.

## Validation Criteria

A complete physics SymPy artifact requires:

- source target equations represented,
- implicit gaps expanded or explicitly blocked,
- all derivation steps executable,
- all equations and transformations dimensionally consistent,
- target expression computed from the derivation chain,
- numeric sanity checks passing on admissible samples,
- no placeholders, hidden final answers, or unresolved blockers.

The consistency report emits physics-specific reference-free metrics:

- source anchor coverage,
- equation parse coverage,
- quantity binding completeness,
- dimension consistency,
- unit grounding density,
- law grounding density,
- implicit-gap closure,
- step executability,
- assumption/regime fidelity,
- coordinate-frame explicitness,
- target derivation success,
- artifact realness.

The Phase 13 report also records a packet inventory for the source extraction,
symbol table, dimension model, unit system, regime assumptions, frame context,
equation parser, gap expansion, law/API grounding, generated artifact,
execution report, unit-analysis report, step-verification report, and
numeric-sanity report.

The standard consistency report path is:

```text
artifacts/physics_sympy/<case_id>/physics_consistency_report.json
```

Complete status requires all source targets represented, all required gaps
closed or explicitly blocked, all derivation steps executable, dimensional
consistency, target derivation from prior steps, numeric sanity with no
counterexamples, and no critical blockers from downstream phase reports.

The executable builder is `consistency_report()` in
`backends.sympy.MathformerPhysicsSympy.pipeline`; the regression check is
`tests/physics_sympy/run_phase13_consistency_report.py`.

## Controlled Suite

The controlled suite covers eight cases:

- constant-acceleration position,
- constant-acceleration velocity-position relation,
- simple harmonic oscillator angular frequency,
- simple harmonic oscillator period,
- constant-force work-energy,
- RC discharge,
- ideal-gas density,
- level-ground projectile range.

Run it with:

```bash
python tests/physics_sympy/run_controlled_suite.py --json
```

Reports are written under `artifacts/physics_sympy/controlled_suite/`, including
JSON, Markdown, and HTML consistency reports for each case.

## Adversarial Suite

The adversarial suite verifies that inconsistent physics cannot be marked
complete. It covers four regression families:

- unit inconsistency: adding velocity to position, exponentiating dimensional
  time, taking sine of dimensional length, and substituting energy where force
  is expected,
- implicit-gap failures: missing initial conditions, coordinate sign
  conventions, small-angle assumptions, nonzero-denominator conditions, and
  law invocations,
- convention drift: gravity signs, spring-force signs, thermodynamic work
  signs, and current directions,
- assumption strengthening: silently making real parameters positive,
  variables constant, vector laws scalar, or damped systems undamped.

Run it with:

```bash
python tests/physics_sympy/run_adversarial_suite.py --json
```

For the full Phase 16 wrapper, including JSONL and JUnit report generation:

```bash
python tests/physics_sympy/run_phase16_adversarial_regression.py --json
```

## End-To-End Check

Run the integrated backend test family:

```bash
python tests/test_program/run_comprehensive_tests.py --module-family physics_sympy --json
```

The expected summary is all physics SymPy checks passing, including dependency
probing, every phase wrapper, artifact execution, controlled cases, and
adversarial blockers.

## Human-Readable Derivation Reports

Phase 17 renders the physics consistency packet into reports meant for human
inspection. The report shows source steps beside generated gap closures,
SymPy expressions, unit/dimension checks, and validation results. It also
includes a derivation graph, blocker-node section, target path, unit-flow
table, and RFDE trajectory plots for gap closure, dimensional consistency,
executable step count, and target residual.

Run:

```bash
python tests/physics_sympy/run_phase17_human_reports.py --json
```

Representative Markdown, HTML, and model JSON outputs are written under:

```text
artifacts/physics_sympy/phase17_human_reports/
```

## Release Gate

Phase 18 is the release gate for the first Physics SymPy slice. It checks
physics skill metadata, strict hook validation, hook coverage, dependency
grounding, unit and step verifiers, controlled cases, adversarial blockers,
clean-process generated artifact execution, RFDE metric coverage, rendered
documentation, and the rule that no complete artifact may retain unresolved
gaps.

Run:

```bash
python tests/physics_sympy/run_phase18_release_criteria.py --json
```

The release report is written under:

```text
artifacts/physics_sympy/phase18_release/
```

## MathformerLib Solver Library

Reusable physics derivations are accumulated under:

```text
libraries/MathformerLib/SympyPhysics/Solvers/<SolverType>/
```

The first entry is the Korteweg-De Vries one-soliton:

- analytic derivation:
  `libraries/MathformerLib/SympyPhysics/Solvers/AnalyticSoliton/KdVOneSoliton.py`
- simulation validation:
  `libraries/MathformerLib/SympyPhysics/Solvers/PseudoSpectralPDE/KdVOneSolitonSimulation.py`
- manifest:
  `docs/libraries/mathformerlib/sympy/physics/manifest.json`

Run:

```bash
python tests/physics_sympy/run_mathformerlib_kdv.py --json
```
