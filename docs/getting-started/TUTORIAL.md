<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Teach Mathformer through concrete demonstrations rather than script listings.

Intent:
  Walk readers through meaningful mathematical workflows, the evidence each
  workflow produces, and the validation status attached to each result.

Function:
  Provides a narrative tutorial for users working through an agent interface.
  Exact command reproduction is delegated to AgenticHub and backend guides.

Maintenance Notes:
  Keep this tutorial demonstration-centered. When adding a new example, name the
  real mathematical claim and explain why the produced artifacts matter.
-->

# Mathformer Tutorial

This tutorial is the deeper companion to the [HowTo](HOWTO.md). It focuses on
complex, realistic autoformalization artifacts already present in the
repository:

1. Hille-Yosida semigroup theory in Lean;
2. Choquet theory and mathlib grounding in Lean;
3. transformer scaling laws from a modern theory paper;
4. FormalPhysics-style multi-backend physics artifacts;
5. reference-free monitoring of formalization evolution.

The intended interface is natural language. Ask the agent for the outcome, then
inspect the source-linked formal surfaces and reports that come back. For setup,
see the [install guide](INSTALL.md).

## Mental Model

Complex autoformalization rarely starts as "prove this one-line theorem." It
usually starts from a paper paragraph, a named theorem, a scientific derivation,
or a source theorem whose full background is larger than the current backend
library.

Mathformer handles this by making the boundary explicit:

- source assumptions are represented as named structures or packets;
- available library facts are used where they exist;
- missing background theory is isolated behind clear hypotheses;
- generated conclusions are checked only as far as the backend can check them;
- reports record whether the artifact is a checked result, a candidate, or a
  blocked draft.
- reference-free monitors track whether each refinement step improves grounding,
  non-vacuity, prover health, and artifact substance when no gold
  formalization exists.

The examples below are useful because they show this boundary instead of hiding
it. A complex formalization can still be valuable when it states exactly what is
formalized, what is assumed, and which part is backend-checked.

## Demo 1: Hille-Yosida Semigroup Theory In Lean

Ask:

> Inspect the Hille-Yosida Lean autoformalization, explain what is actually
> formalized, and identify the analytic boundary that remains external.

The artifact is [AutoformalizedHilleYosida.lean](../../backends/lean/Mathformer/AutoformalizedHilleYosida.lean).
It models a `C0Semigroup`, continuity at zero, growth bounds, generator
difference quotients, and resolvent/generator interfaces.

What should happen:

1. The agent reads the Lean file as a source-linked formal surface.
2. It identifies the main mathematical objects: semigroups, continuity,
   generators, resolvents, and growth bounds.
3. It separates Lean-native definitions from theorem-level assumption packages.
4. It reports which statements are proved accessors or consequences, and which
   parts are intentionally represented as hypotheses.

What to notice:

- Hille-Yosida theory involves unbounded operators and semigroup generators.
- Those concepts do not collapse cleanly to a short elementary theorem.
- The Lean file therefore formalizes an interface and its consequences without
  pretending that all analytic infrastructure has been rebuilt locally.

Output files to inspect:

- [Hille-Yosida Lean surface](../../backends/lean/Mathformer/AutoformalizedHilleYosida.lean)
- [Lean project file](../../lakefile.toml)
- [pinned Lean toolchain](../../lean-toolchain)

## Demo 2: Choquet Theory And Mathlib Grounding

Ask:

> Inspect the Choquet theory Lean artifact and explain how it uses available
> mathlib facts while keeping the representation theorem boundary explicit.

The artifact is [AutoformalizedChoquetTheory.lean](../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean).
It connects compact convex sets, extreme points, probability-measure surfaces,
continuous affine tests, and the available Krein-Milman theorem.

What should happen:

1. The agent identifies the bundled `ChoquetSet` structure.
2. It traces the available mathlib grounding for extreme points and
   Krein-Milman.
3. It distinguishes mathlib-proved support lemmas from explicit Choquet
   representation hypotheses.
4. It explains how the artifact represents a theorem whose full named
   statement is not already available as a single imported mathlib result.

What to notice:

- Choquet theory mixes topology, convexity, measure, and affine functions.
- The useful formalization work is not only proving a final theorem; it is
  finding the right interface between available library material and missing
  representation infrastructure.
- The file shows how Mathformer keeps that interface inspectable.

Output files to inspect:

- [Choquet Lean surface](../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean)
- [Mathformer library documentation index](../libraries/mathformerlib/INDEX.md)
- [aligned HTML documentation index](../libraries/mathformerlib/aligned/INDEX.html)

## Demo 3: Transformer Scaling Laws From A Theory Paper

Ask:

> Inspect the transformer scaling-laws Lean artifact and explain how the paper's
> assumptions, rates, and exponent consequences are represented.

The artifact is
[AutoformalizedTransformerScalingLaws.lean](../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean).
It turns paper-level statements about transformer approximation and statistical
rates on low-dimensional data into explicit Lean structures and rate lemmas.

What should happen:

1. The agent identifies the source theorem families and their assumptions.
2. It explains the role of `ManifoldAssumptions`,
   `TargetFunctionAssumptions`, and `TransformerNetworkClass`.
3. It distinguishes paper-level hypothesis packages from Lean-proved algebraic
   consequences about exponents.
4. It reports which aspects are source-linked claims and which aspects are
   checked Lean derivations from those claims.

What to notice:

- Modern ML theory uses asymptotic rates, manifold assumptions, approximation
  classes, and generalization bounds.
- Autoformalizing such a paper requires preserving the mathematical shape of
  the theorem even when the entire proof appendix is not formalized.
- The resulting artifact is a useful formal contract for future refinement:
  assumptions, rates, and consequences are named rather than buried in prose.

Output files to inspect:

- [transformer scaling-laws Lean surface](../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean)
- transformer scaling revisit note (generated output: `artifacts/transformer_scaling_laws_revisit_2026-06-06.md`)

## Demo 4: FormalPhysics Multi-Backend Artifacts

Ask:

> Inspect a FormalPhysics-derived case across Lean and SymPy, explain the
> assumptions, units, equations, and validation reports, and identify what each
> backend contributes.

Start with the [Mathformer Physics Library](../../libraries/MathformerPhysicsLib/README.md).
The library stores related artifacts by backend. A representative case is
`formalphysics_0172`, which has both Lean and SymPy forms.

What should happen:

1. The agent reads the backend-separated library layout.
2. It inspects the Lean candidate and the consistency report.
3. It inspects the SymPy executable derivation and the summary report.
4. It compares the roles of proof-assistant structure and executable symbolic
   checking.
5. It reports assumptions, units, dimensions, equations, and validation status
   without flattening them into a single scalar calculation.

What to notice:

- Physics autoformalization must preserve quantities, units, regimes,
  assumptions, and laws.
- Lean, Isabelle, and SymPy provide different kinds of evidence.
- Mathformer keeps those backend artifacts next to reports so a user can audit
  what was formalized and what was merely checked computationally.

Output files to inspect:

- [physics library overview](../../libraries/MathformerPhysicsLib/README.md)
- [FormalPhysics 0172 Lean artifact](../../libraries/MathformerPhysicsLib/Lean/formalphysics_0172/MathformerPhysics.lean)
- [FormalPhysics 0172 Lean report](../../libraries/MathformerPhysicsLib/Lean/formalphysics_0172/consistency_report.json)
- [FormalPhysics 0172 SymPy artifact](../../libraries/MathformerPhysicsLib/SymPy/formalphysics_0172/MathformerPhysics.py)
- [FormalPhysics 0172 SymPy summary](../../libraries/MathformerPhysicsLib/SymPy/formalphysics_0172/summary.json)
- from-scratch Lean candidate (generated output: `artifacts/physics_lean/from_scratch_lean/formalphysics_0172/mathformer_typed_candidate.lean`)
- unit-analysis report (generated output: `artifacts/physics_lean/from_scratch_lean/formalphysics_0172/unit_report.json`)
- physics consistency report (generated output: `artifacts/physics_sympy/controlled_suite/formalphysics_0172/physics_consistency_report.md`)

## Demo 5: Reference-Free Formalization Monitor

Ask:

> Monitor the evolution of a Lean formalization without using a gold reference,
> then explain the plot, the trend statistics, and the next refinement target.

This demo is for the moment after an agent has produced one or more
formalization candidates. In ordinary benchmark evaluation, a system is scored
against a reference answer. Complex mathematics and physics rarely have that
luxury: there may be no single gold Lean file for a theorem from a paper, no
complete reference formalization for a physics derivation, and no canonical
choice of assumptions.

Mathformer therefore measures progress by asking whether the artifact has fewer
ways to be wrong than before. The monitor compares the current snapshot with an
accepted baseline and any prior snapshots in the ledger. It turns that sequence
into an evolution view: scores should rise, hard risks should not rise, and any
regression should become a concrete refinement task.

What should happen:

1. The agent identifies the artifact or family of artifacts to monitor.
2. It extracts reference-free signals: prover health, placeholder freedom,
   logical non-vacuity, semantic anchor coverage, library grounding, critic
   agreement, and artifact substance.
3. It counts risks such as unresolved proofs, target axioms, placeholder
   markers, trivial theorem shapes, and low-scoring dimensions.
4. It compares the current snapshot against the baseline and ledger history.
5. It writes a plot, a CSV timeline, and a JSON evolution model.
6. It explains the next refinement step in terms of the weakest measured
   dimension, not as a generic request to "try again."

What to notice:

- The plot is not a proof certificate. It is a progress instrument.
- A rising confidence curve means the artifact is becoming more constrained,
  better grounded, or less risky according to local evidence.
- A flat line can be useful: it says the latest change did not improve the
  measured formalization state.
- A regression is a blocker candidate: the next loop should explain why a score
  fell or why a hard risk increased.

Output files to inspect:

- [monitor demonstration summary](../../examples/outputs/reference_free_monitor_evolution_demo.md)
- [reference-free monitor skill](../../skills/rfde/reference-free-critic-monitor/SKILL.md)
- [monitor reference guide](../../skills/rfde/reference-free-critic-monitor/references/reference_free_monitor.md)

Generated local runs also write:

- `artifacts/reference_free_critic_monitor/evolution/formalization_evolution.svg`
- `artifacts/reference_free_critic_monitor/evolution/formalization_evolution.csv`
- `artifacts/reference_free_critic_monitor/evolution/formalization_evolution.json`
- `artifacts/reference_free_critic_monitor/latest.json`

## Reading Complex Artifacts

Read these examples as evidence packets rather than single-status badges. Look
for the shape of the evidence:

| Artifact kind | What it tells you |
| --- | --- |
| Lean surface | Which definitions, hypotheses, and theorem statements are explicit |
| Consistency report | Which formal or structural checks ran |
| Assumption packet | Which physical or mathematical assumptions were modeled |
| Unit or dimension report | Whether quantities were checked against the intended physical dimensions |
| SymPy artifact | Which symbolic equation or derivation was executed |
| Evolution plot | Whether reference-free scores improved and hard risks stayed controlled |
| Evolution statistics | Which dimensions improved, regressed, or remained flat across snapshots |
| Summary JSON | Machine-readable status and diagnostics |

The most important question is whether the artifact states its boundary clearly.
For complex material, a precise candidate is often more useful than an
overconfident proof-shaped file.

## If A Complex Example Fails

Complex examples fail in more interesting ways than toy theorems. Common
failure modes include:

- a library concept exists under a different name or with different hypotheses;
- a source theorem uses background theory not yet modeled locally;
- a physical derivation omits a nonzero, positivity, frame, or regime
  assumption;
- a symbolic backend validates the equation but not the full physical meaning;
- a proof-assistant surface is syntactically valid but too weak, too strong, or
  not aligned with the source statement.

Ask the agent to localize the failure: source mismatch, missing dependency,
missing assumption, backend limitation, or generated statement drift. That
classification is usually more useful than another blind generation attempt.

## Next Steps

- Use the [HowTo](HOWTO.md) for the short demonstration list.
- Use the [physics library overview](../../libraries/MathformerPhysicsLib/README.md) for
  multi-backend physics artifacts.
- Use the [premise KB guide](../backends/PREMISE_KB.md) when complex theorem search needs
  retrieval or curation.
- Use the [Vampire ATP guide](../backends/VAMPIRE_ATP.md) when a complex problem has a
  first-order fragment suitable for ATP proof search.

## Generated output availability

Source and library links identify retained artifacts. Paths labeled “generated output”
are optional run products and may be absent in a fresh checkout; their absence is not
proof evidence. Ask the agent to run the associated demonstration through the controlled
hub, then inspect the returned artifact paths and validation status. Consult the
[hub reference](../architecture/AGENTIC_HUB.md) for exact actions and write effects.
Do not substitute a different run's report or infer a checked result from the path alone.
