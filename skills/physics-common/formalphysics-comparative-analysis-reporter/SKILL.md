---
name: formalphysics-comparative-analysis-reporter
description: Build systematic FormalPhysics comparison reports over Mathformer and external Lean outputs, using reference answers as non-gold comparison evidence, full MathformerPhysicsLib Foundations dependency context, deterministic Lean checks, and generative Codex-exec judges. Use when a user wants a self-contained HTML/JSON/markdown report, side-by-side Lean rendering, best-solution selection, or comparison input cleaning that removes obsolete self-generated answers from external JSON.
---

<!--
File Documentation

Motivation:
  Make comparative FormalPhysics evaluation explicit, reusable, and inspectable.

Intent:
  Guide agents through source/reference/candidate comparison without treating
  reference answers as ground truth.

Function:
  Defines the skill workflow, supporting references, and deterministic input
  preparation script for comparison reports.

Maintenance Notes:
  Keep this skill aligned with FormalPhysics first-pass source-only guards and
  MathformerPhysicsLib Foundations coherence workflows.
-->

# FormalPhysics Comparative Analysis Reporter

Use this skill for post-hoc comparison of FormalPhysics solutions from
Mathformer and external systems. The comparison target is not just the main
Lean file: for Mathformer candidates it includes the imported and available
`libraries/MathformerPhysicsLib/Lean/Foundations` dependency surface.

## Non-Gold Reference Policy

- Treat `answer` or dataset `formal_answer` fields as reference evidence, not
  gold labels.
- Do not use reference answers during first-pass source-only drafting.
- Remove obsolete prior self-output from external comparison JSON before
  judging. By default the helper script drops `mathformerphysics_output` and
  rediscovers current Mathformer artifacts from the repo.
- A solution can beat the reference if it compiles, preserves source semantics,
  keeps physical assumptions explicit, and uses a better library abstraction.

## Workflow

1. Normalize the input JSON and strip obsolete self-generated entries:

```bash
python skills/physics-common/formalphysics-comparative-analysis-reporter/scripts/prepare_comparison_inputs.py \
  --input-json inputs/selected_examples.json \
  --output-dir artifacts/formalphysics_comparative_analysis/run
```

For the full report, use:

```bash
python skills/physics-common/formalphysics-comparative-analysis-reporter/scripts/build_comparative_report.py \
  --input-json inputs/selected_examples.json \
  --output-dir artifacts/formalphysics_comparative_analysis/run \
  --json
```

Add `--execute-lean` when the report should run `lake env lean` compile gates.

2. Build a comparison packet for every case:
   - informal question and non-gold reference answer,
   - external-system Lean code, usually `formaldiscovery_output`,
   - current Mathformer Lean candidate from
     `libraries/MathformerPhysicsLib/Lean/formalphysics_XXXX/MathformerPhysics.lean`,
   - all files under `libraries/MathformerPhysicsLib/Lean/Foundations.lean` and
     `libraries/MathformerPhysicsLib/Lean/Foundations/`,
   - declaration excerpts for every detected invoked Foundation concept,
     including file path, line span, kind, name, and invocation count.

3. Run deterministic judges before generative judges:
   - Lean compilation and import health,
   - placeholder/axiom/sorry hygiene,
   - theorem-shape and non-vacuity checks,
   - Foundations dependency inventory and coherence checks,
   - source-anchor and reference-delta analysis,
   - Mathlib concept grounding evidence,
   - variable/declaration naming evidence,
   - formal-physics modeling depth versus algebraic-shell risk,
   - physics-representation completeness,
   - annotation and reviewability evidence.

4. Run deep generative judges with Codex exec only after deterministic packets
   exist. The generative panel should include a physicist judge, Lean theorem
   proving judge, Mathlib grounding judge, formal modeling/completeness judge,
   naming/reviewability judge, invoked dependency excerpt judge,
   MathformerPhysicsLib dependency judge, and adversarial semantic-preservation
   judge.

5. Build qualitative role reviews from the deterministic packets:
   - `theorem_prover_expert`: proof integrity, compile status, theorem shape,
     placeholder hygiene, import discipline, Mathlib concept grounding,
     variable/declaration naming, formal modeling depth, and dependency
     maintainability;
   - `physics_expert`: source preservation, physical object fidelity,
     assumptions, units, dimensions, operators, representation completeness,
     formal physics complexity, reviewability, and derivation coverage.

6. Aggregate results with gates first and scores second. Compilation and
   soundness hygiene are hard gates; semantic, physical, dependency, and
   maintainability metrics are ranked evidence, not oracle truth.

7. Render a self-contained HTML report with:
   - overview and leaderboard,
   - per-case best-solution rationale,
   - side-by-side Lean comparison tab,
   - Foundations dependency tab,
   - judge evidence and disagreement tab,
   - independent role-review tab,
   - cross-role strategy summary tab,
   - methodology tab documenting the non-gold reference policy.

## References

- Read `references/metrics.md` when defining or revising quality metrics.
- Read `references/judge_protocols.md` when implementing deterministic or
  Codex-exec judges.
- Read `references/qualitative_role_reviewers.md` when revising reviewer
  roles, rubrics, or strategy-synthesis criteria.
- Read `references/html_report_spec.md` when building the final HTML renderer.

## Validation Expectations

- `prepare_comparison_inputs.py --self-test` must pass.
- `build_comparative_report.py --self-test --json` must pass.
- `tests/physics_lean/run_formalphysics_comparative_report.py --json` must pass.
- The cleaned JSON must not contain `mathformerphysics_output` unless the user
  explicitly requests obsolete self-output retention.
- Every Mathformer candidate packet must include a Foundations inventory.
- Every candidate report must include an `invoked_external_dependency_excerpts`
  list so side-by-side excerpt comparison imports the concepts used from
  external dependency files.
- Every final report must expose `metric_criteria`, `critic_profiles`, and
  per-candidate `critic_evidence` for Mathlib grounding, naming,
  formality/completeness, and reviewability.
- The report must emit `theorem_prover_expert_review.md`,
  `physics_expert_review.md`, `qualitative_role_reviews.json`, and
  `strategy_comparison_summary.md`.
- Every final report must declare: `reference_answer_role =
  non_gold_reference_evidence`.
