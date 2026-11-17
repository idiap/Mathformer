<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Give users a natural-language guide to the main Mathformer demonstrations.

Intent:
  Explain what to ask for, what each workflow demonstrates, what artifacts to
  expect, and how to interpret the validation status of the result.

Function:
  Serves as the practical HOWTO above the backend reference documents. It avoids
  making scripts the primary interface and points operators to AgenticHub
  when exact commands are needed.

Maintenance Notes:
  Keep examples meaningful and named. Prefer concrete demonstration theorems
  over anonymous prompt placeholders.
-->

# Mathformer HOWTO

Use Mathformer by asking for mathematical outcomes in natural language. The
agent should choose the controlled workflow, run the relevant backend, and
return the evidence with artifact paths and validation status.

## Example Requests

Example requests name the mathematical work:

- "Prove that in a group, the inverse of a product reverses order, using
  premise selection if helpful."
- "Validate the Lean wiki-level theorem fixtures and tell me which ones were
  compiler-checked."
- "Verify the RC discharge derivation and explain the assumptions, units, and
  validation result."
- "Run premise selection and search for statements near the Fundamental theorem
  of algebra."
- "Review the documentation for demonstration quality and remove tool-first
  exposition."

## Demonstration 1: Vampire ATP Proof Discovery

Use this path when the theorem can be represented in first-order logic: group
algebra, set inclusions, order relations, relational chains, or policy-style
implications.

Ask:

> Prove that in a group, `(x * y)^-1 = y^-1 * x^-1`, use premise selection, and
> summarize the Vampire proof artifact.

What Mathformer should do:

1. Keep the informal statement visible.
2. Generate a TPTP problem for Vampire.
3. Select the relevant group axioms from the local premise set.
4. Generate helper lemmas only as candidates.
5. Prove helper lemmas before promoting them.
6. Minimize the final premise set.
7. Return the TSTP proof, generated problem, reports, and informal explanation.

Evidence returned:

- A proof claim requires a successful Vampire SZS theorem status and an
  accompanying TSTP proof artifact.
- Generated helper lemmas are promoted only after their own proof obligations
  succeed.
- The informal proof explanation is a readable explanation of the formal
  evidence, not the evidence itself.

Output files to inspect:

- generated TPTP problem (generated output: `artifacts/vampire_atp/atp_function_demo/candidate_01_group_inverse_of_product_reverses_order.p`)
- Vampire TSTP proof (generated output: `artifacts/vampire_atp/atp_function_demo/candidate_01_group_inverse_of_product_reverses_order.proof.tstp`)
- informal proof explanation (generated output: `artifacts/vampire_atp/atp_function_demo/candidate_01_group_inverse_of_product_reverses_order.informal.md`)
- premise-selection report (generated output: `artifacts/vampire_atp/atp_function_demo/premise_selection_report.json`)

## Demonstration 2: Lean Formalization Candidates

Use this path when a statement should become a checked proof-assistant artifact
or a Lean candidate.

Ask:

> Validate the Lean wiki-level examples, including the sum of the first odd
> numbers, monotone composition, injective composition, and set identities.

What Mathformer should do:

1. Identify the theorem fixtures and their intended informal meanings.
2. Check Lean artifacts with the local Lean/Lake environment when available.
3. Report which artifacts are checked, which are candidates, and which are
   blocked by missing tools or diagnostics.

Evidence returned:

- Compiler-accepted Lean artifacts carry the status reported by Lean/Lake.
- Generated Lean formalizations with placeholders, admitted proofs, or missing
  imports remain drafts.

Output files to inspect:

- [Lean wiki-level fixture](../../tests/lean/WikiLevelGold.lean)
- [wiki-level case manifest](../../tests/latex/wiki_level/manifest.json)
- [sum of first odd numbers source](../../tests/latex/wiki_level/sum_first_odd_numbers.tex)

## Demonstration 3: Physics Derivation With SymPy

Use this path when a physics derivation should be checked as an executable trace
with explicit laws, quantities, units, assumptions, and residuals.

Ask:

> Verify the RC discharge derivation `dV/dt = -V/(R C)`, `V(0)=V0`, so
> `V(t)=V0 exp(-t/(R C))`, and explain what SymPy validated.

What Mathformer should do:

1. Identify the voltage `V`, initial voltage `V0`, resistance `R`,
   capacitance `C`, and time `t`.
2. Record assumptions such as ideal resistor, ideal capacitor, `R > 0`,
   `C > 0`, and `t >= 0`.
3. Encode the candidate solution `V0 exp(-t/(R C))`.
4. Check the ODE residual, the initial condition, dimensional consistency, and
   a numeric sample.
5. Report which source-backed and generated steps were validated.

Evidence returned:

- The computation is scoped to the stated assumptions.
- Missing domain conditions, nonzero constraints, or unit assumptions block
  strong claims.
- Executable symbolic support is separate from proof-assistant acceptance.

Output files to inspect:

- [SymPy RC-discharge artifact](../../backends/sympy/MathformerSympyPhysics/AutoformalizedRcDischarge.py)
- [physics consistency report](../../artifacts/physics_sympy/controlled_suite/rc_discharge/physics_consistency_report.md)
- [machine-readable consistency report](../../artifacts/physics_sympy/controlled_suite/rc_discharge/physics_consistency_report.json)
- [demonstration summary](../../examples/outputs/rc_discharge_physics_demo.md)

## Demonstration 4: Premise Selection

Use this path when you want the system to retrieve and rank mathematical facts
before proof search.

Ask:

> Index the famous theorem and axiom corpus, then test exact presence, semantic
> search, and geometric distance for the Fundamental theorem of algebra.

What Mathformer should do:

1. Load structured theorem and axiom entries into the KB.
2. Normalize names, informal statements, LaTeX surfaces, and optional formal
   surfaces.
3. Build exact lookup data and Bloom filters for fast presence checks.
4. Build embeddings for semantic proximity.
5. Report whether the target theorem is exactly present.
6. Return nearby facts and distances in the embedding space.

Evidence returned:

- Exact presence means a probable Bloom-filter hit resolved to a concrete KB
  entry.
- Semantic hits are nearby suggestions, not proof premises.
- Generated corpus entries remain retrieval candidates until curation or proof
  evidence promotes them.

Output files to inspect:

- [search demonstration summary](../../examples/outputs/fundamental_theorem_algebra_search_demo.md)
- KB entries (generated output: `artifacts/kb/premise_kb/entries.jsonl`)
- Bloom-filter manifest (generated output: `artifacts/kb/premise_kb/bloom/manifest.json`)
- embedding index (generated output: `artifacts/kb/premise_kb/embeddings/index.json`)

## Choosing The Right Path

Use this map when deciding what to ask:

| Goal | Best first path |
| --- | --- |
| Prove a first-order theorem | Vampire ATP |
| Retrieve nearby mathematical facts | Premise selection |
| Produce compiler-checked mathlib work | Lean |
| Generate or validate `.v` proof scripts | Rocq |
| Check physics derivations or symbolic formulas | SymPy |
| Maintain reproducible agent behavior | Skills and AgenticHub |
| Run benchmark-style evaluations | Benchmark workflows |

In normal agent use, ask for the outcome. If you are operating the repository
directly, use [AgenticHub](../architecture/AGENTIC_HUB.md) to inspect the exact action,
dry-run it, or run it with the appropriate safety label.

## Where To Go Next

- [Tutorial](TUTORIAL.md): a demonstration-centered walkthrough.
- [Natural-language agent interface](NL_AGENT_INTERFACE.md): how agents route
  user requests.
- [Install guide](INSTALL.md): essential setup and optional backend notes.
- [Premise KB guide](../backends/PREMISE_KB.md): KB schema, indexing, and curation states.
- [Vampire ATP guide](../backends/VAMPIRE_ATP.md): TPTP/Vampire details.
- [Rocq backend guide](../backends/ROCQ_BACKEND.md): Rocq generation and validation.

## Generated output availability

Source and library links identify retained artifacts. Paths labeled “generated output”
are optional run products and may be absent in a fresh checkout; their absence is not
proof evidence. Ask the agent to run the associated demonstration through the controlled
hub, then inspect the returned artifact paths and validation status. Consult the
[hub reference](../architecture/AGENTIC_HUB.md) for exact actions and write effects.
Do not substitute a different run's report or infer a checked result from the path alone.
