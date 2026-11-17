<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Judge Protocols

## Deterministic Judges

Run these before any generative judge:

1. `lean_compile_judge`
   - run `lake env lean` on repo candidates;
   - compile external snippets in a temporary Lean file when safe;
   - preserve return code, errors, warnings, and command.

2. `static_hygiene_judge`
   - count imports, theorems, definitions, structures, instances, axioms,
     `sorry`, `admit`, broad `import Mathlib`, and theorem names;
   - flag empty or suspicious theorem shapes.

3. `source_anchor_judge`
   - map informal question concepts to Lean declarations and doc comments;
   - record omissions and assumption strengthening.

4. `foundations_dependency_judge`
   - inventory every file under `libraries/MathformerPhysicsLib/Lean/Foundations`;
   - record imports, declaration counts, candidate imports, duplicated concepts,
     and dependencies that make the top-level file meaningful.

5. `reference_delta_judge`
   - compare candidate, problem text, and reference answer;
   - classify deltas as agreement, stronger source preservation, weaker source
     preservation, unexplained assumption, or harmless style difference.

6. `mathlib_grounding_critic`
   - record concrete Mathlib concept families used by the candidate, including
     scalars, modules, linear maps, inner-product spaces, derivatives,
     topology/normed-space surfaces, and algebraic laws;
   - distinguish actual concept grounding from a broad `import Mathlib`;
   - record canonical Foundations declarations used by the candidate;
   - import declaration excerpts for every detected invoked Foundation concept
     so top-level excerpt comparison includes the external concepts being used.

7. `naming_reviewability_critic`
   - inspect declaration and variable names for source/domain vocabulary;
   - flag generic names that hide physical concepts;
   - count comments, source-step annotations, bridge names, and review aids.

8. `formality_depth_critic`
   - distinguish typed formal physics modeling from a pure algebraic shell;
   - reward frontiers, contexts, witnesses, units, operators, bridge lemmas, and
     reusable declarations;
   - flag single-claim solutions that erase the underlying physical
     construction;
   - use invoked dependency excerpt count and variety as evidence of grounded
     modeling depth when the snippets are semantically relevant.

9. `physics_completeness_critic`
   - check whether the formal artifact captures physical quantities, laws,
     operators, fields, states, frames, units, dimensions, domains, boundary
     assumptions, and source derivation complexity;
   - record source concepts that appear missing or underspecified.

## Generative Codex-Exec Judges

Run generative judges only on deterministic packets and code excerpts. Require
strict JSON output with:

- `judge_id`
- `case_id`
- `candidate_id`
- `scores`
- `hard_gate_findings`
- `evidence`
- `uncertainty`
- `repair_suggestions`

Recommended panel:

- `physicist_semantics_judge`: checks physical quantities, domains, laws,
  units, dimensions, operator ordering, regimes, and missing assumptions.
- `lean_tp_judge`: checks theorem shape, proof integrity, non-vacuity,
  import discipline, and maintainable Lean style.
- `mathlib_grounding_judge`: checks how well physics concepts are modeled using
  Mathlib concept families and canonical Foundations surfaces.
- `formal_modeling_completeness_judge`: checks whether the artifact captures
  the underlying physics in typed formal structure rather than algebraic
  surface equality alone.
- `naming_reviewability_judge`: checks variable/declaration naming, source-step
  annotations, clarity, and review strategy.
- `invoked_dependency_excerpt_judge`: checks whether detected invoked
  Foundation concepts have imported excerpts with path, line span, kind, name,
  and invocation count.
- `foundations_dependency_judge_llm`: checks whether the candidate depends on,
  duplicates, bypasses, or improves MathformerPhysicsLib Foundations.
- `adversarial_reference_judge`: tries to falsify both the candidate and the
  reference answer; it must not grant oracle status to either.

## Qualitative Role Reviewers

After deterministic packets exist, emit two structured role reports even when
Codex-exec judges have not yet run:

- `theorem_prover_expert`: reviews compile status, proof integrity,
  placeholder hygiene, theorem-shape non-vacuity, import discipline, Mathlib
  concept grounding, naming quality, formality depth, and dependency
  maintainability.
- `physics_expert`: reviews source-semantic preservation, physical object
  fidelity, assumptions, units, dimensions, operators, representation
  completeness, formality depth, reviewability, derivation coverage, and
  reference-answer deltas.

These reports are qualitative but not free-form: each case must include
machine-readable criteria, role scores, essential features, strategy tags,
strengths, concerns, and a per-role preferred strategy.

## Aggregation

- Hard gate failures block best-solution status.
- Independent judge agreement raises confidence.
- Judge disagreement is reported, not averaged away.
- A generative finding blocks only when supported by deterministic evidence or
  repeated independent judge agreement.
- Repairs must be localized and routed through the normal Lean physics review
  refinement workflow.
