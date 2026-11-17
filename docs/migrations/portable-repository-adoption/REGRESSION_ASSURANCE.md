<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Inference and workflow regression assurance

**No new regression was found in the tested scope.** The working tree was compared
with pre-adoption revision `427150fadefba8668f2199ec06a57277a27832bf` using independent
agent reviews and isolated before/after executions. Existing failures remain
visible; this report does not claim that every repository test is green.

## Compatibility evidence

| Boundary | Observed result |
| --- | --- |
| Existing hub actions | All 209 original descriptors unchanged; only the ten adoption actions are added. |
| Existing routes | All 66 original route definitions unchanged. 691 historical examples/terms/documented requests across 31 family settings produced 21,421 identical ranked results, scores and actions. |
| Existing tests and discovery | All 170 original matrix entries unchanged; all 188 canonical skill identities and 564 host symlinks retained. |
| Inference semantics | Hook, skill/output/reasoning taxonomies, PRISM projection specifications and active `main.prism` remain byte-identical to the baseline. |
| All PRISM workflows | 14/14 passed fake-handler execution, offline trace verification and concurrency checks, with unchanged source fingerprints. This is structural/fixture evidence. |
| Recorded inference results | Eight physics controlled-validation reports byte-identical; five symbolic-validation reports identical after removing only `/generated_at`. Equations, units, assumptions, checks and outcomes are retained. |
| Adoption runtime | All 22 tests passed through the controlled hub, including exact validator/log parity, receipt integrity, failures/cancellation, nesting/concurrency and the new binding-drift regression. |
| Entry point control | 312/312 entrypoints controlled; every broader before/after test write audit passed. |

[Routing comparison](evidence/regression-assurance/routing.json),
[all-workflow PRISM report](evidence/regression-assurance/prism-all-workflows.json),
[inference-output hashes and comparisons](evidence/regression-assurance/inference-outputs.json),
[22-test adoption gate](evidence/regression-assurance/adoption-gate.json), and
[machine-readable assurance](evidence/regression-assurance/comparison.json)
retain the evidence. The earlier [native Codex check](evidence/a08-final/prism-native.json)
remains scoped to the selected artifact-acceptance placeholder workflow; it is not
backend proof or a full 14-workflow native-provider validation.

## Broader before/after executions

Both isolated checkouts used the same existing Python environment and the same
registered fixtures. All 88 selected checks ran, with no skips and no test-matrix
or result-schema errors. Each original test retained its status and exit code.

| Family | Before | After |
| --- | --- | --- |
| ATP | 3/3 pass | 3/3 pass |
| SymPy | 14/14 pass | 14/14 pass |
| Physics SymPy | 51/54 pass | 51/54 pass |
| Source handling | 4/4 pass | 4/4 pass |
| MCP | 5/5 pass | 5/5 pass |
| Documentation | 3/4 pass | 3/4 pass |
| MathformerLib | 2/2 pass | 2/2 pass |
| Environment | 2/2 pass | 2/2 pass |
| Total | **84 pass, 4 fail** | **84 pass, 4 fail** |

[Before execution](evidence/regression-assurance/before-matrix.json) and
[after execution](evidence/regression-assurance/after-matrix.json) retain commands,
outputs and write audits. Tests wrote into disposable checkouts; existing proof
artifacts and reports in the working repository were preserved.

An independent [failure review](evidence/regression-assurance/failure-review.json)
confirmed the same causes in both runs:

- `control.reasoning_flow_catalog.synchronized`: stale materialization catalog documentation.
- `physics_sympy.phase13_consistency_report.self`: missing legacy generated-artifact paths produce `artifact_realness=0`.
- `physics_sympy.formalphysics_two_samples.e2e`: missing `01_formalphysics_0000.tex` source fixture.
- `physics_sympy.phase18_release_criteria.e2e`: the same RC-discharge artifact-realness failure; the other 12 internal release checks pass.

These remain pre-existing failures in the isolated baseline and candidate; they
were not repaired or relabeled as passing by the adoption change. No full Lean
rebuild was performed because Lean sources and interfaces were unchanged.

## Additional defect prevented

The review found that metadata could previously identify a different existing
callable while the adapter still executed its original hardcoded implementation.
The current authored metadata was correct, so this was not an observed legacy
inference failure. The six explicit adapters now reject owner/path/symbol/action
bindings that disagree with their dispatcher, before invocation or receipt
creation. A regression test covers substitutions of real callables and PRISM
entrypoints, not just nonexistent paths.

This fix changes only the new adapter and its tests. Existing inference and
workflow implementations retain their prior behavior. Free-text descriptions
still require review; the schema validates their structure and specific typed
constraints, not arbitrary natural-language truth.
