---
name: physics-lean-dimension-critic
description: Critique unit and dimension discipline in Lean physics formalizations, including raw-scalar erasure, missing quantity types, missing dimension obligations, vector/scalar projection mistakes, and generative unit stress tests through Codex exec.
---

<!--
File Documentation

Motivation:
  Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

Intent:
  Tell coding agents what context to load, what invariants to preserve, and how to validate their work.

Function:
  Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Physics Lean Dimension Critic

Use this critic after unit analysis and before final acceptance. It is stricter
than a syntactic unit report: it asks whether the Lean artifact could still be
right for the wrong physical dimensions.

## Critic Contract

1. Check for a declared dimension policy such as `PhysDim`, `Quantity`,
   `VectorQuantity`, or an explicit project-local equivalent.
2. Check that source quantities are typed or projected with local projection
   lemmas.
3. Check that vector quantities are not silently replaced by unrelated scalars.
4. Check that unit/dimension obligations are attached to transformations, not
   only stated globally.
5. Fail raw `Real` erasure when the source claim is dimensioned and no
   projection bridge exists.

Prefer `scripts/critique_physics_lean_dimensions.py` for deterministic
screening.

## Generative Mode

This critic may use Codex exec to generate adversarial unit probes:

- Substitute two different unit systems and see whether the Lean statement would
  still express the same equation.
- Scale one base dimension independently and identify which theorem hypotheses
  should prevent invalid transformations.
- Project a vector equation to coordinates and check whether the projection
  lemma preserves the source claim.
- Search for dimensionless-only formalizations of dimensioned source claims.

Generative probes are critic evidence, not final proof evidence. Promote repeat
failures into deterministic fixtures.
