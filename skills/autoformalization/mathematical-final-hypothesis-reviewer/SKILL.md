---
name: mathematical-final-hypothesis-reviewer
description: Review final formalized derivation hypotheses for mathematical soundness, theorem shape, variable binding, quantifiers, domains, side conditions, dependency structure, non-vacuity, and proof-realness before final acceptance. Use at the end of a Lean physics or mathematical formalization pipeline and route failures to localized monotonic refinement.
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

# Mathematical Final Hypothesis Reviewer

Use this reviewer after Lean execution and domain-specific critics, before a
formalized derivation is accepted as complete.

## Review Contract

Validate the final mathematical hypothesis structure:

1. All variables, parameters, functions, and structures are explicitly bound
   with appropriate domains and types.
2. Quantifiers, existence claims, uniqueness claims, equivalences, implications,
   and conclusions match the source shape.
3. Side conditions needed for algebraic, order, differential, integral, or
   limiting steps are present and not stronger than the source without labels.
4. The theorem is not vacuous, trivialized, target-as-assumption, target-as-axiom,
   or reduced to `True`.
5. Generated support lemmas do not assume the target conclusion.
6. Dependencies are acyclic and localized: support lemmas prove intermediate
   facts rather than restating the final theorem.
7. Proof placeholders, `sorry`, `admit`, unresolved tactics, mock markers, and
   scaffold-only completions are absent in complete status.
8. Refinements preserve already-correct theorem shape, source anchors, and
   passing gates.

Prefer `scripts/review_mathematical_final_hypotheses.py` for deterministic
screening.

## Common Failure Modes

- Dropped universal, existential, uniqueness, or iff structure.
- Added totality, nonzero, positivity, differentiability, or decidability
  assumptions without source support.
- Wrong implication direction.
- Unbound or under-typed variables hidden by inference.
- Theorem conclusion weakened to a projection or special case.
- Contradictory hypotheses make the theorem vacuous.
- Support lemma is equivalent to the final target.
- A repair fixes compilation by changing the statement rather than the proof.

## Refinement Handoff

Emit localized repair surfaces:

- `binder_domain`
- `quantifier_shape`
- `side_condition`
- `conclusion_shape`
- `support_dependency`
- `proof_realness`
- `nonvacuity`

Route failures to `physics-lean-review-refinement-router` or the relevant
backend refinement skill. The repair must rerun the failed reviewer and all
previously passing protected gates that could be affected by the edit.
