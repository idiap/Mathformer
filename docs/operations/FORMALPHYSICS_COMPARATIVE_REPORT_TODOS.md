<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# FormalPhysics Comparative Report TODOs

## Scope

Build a comparative analysis workflow that evaluates current Mathformer
FormalPhysics artifacts against external-system Lean outputs from an external
JSON file. The informal `answer` is a reference answer, not a gold standard.
Obsolete prior `mathformerphysics_output` JSON fields must be removed from the
comparison bundle and current Mathformer outputs must be loaded from the repo.

## TODOs

- [x] FPC-001: Normalize external JSON into comparison records.
  - Inputs: `FS_index`, `question`, `answer`, `formaldiscovery_output`.
  - Exclude `mathformerphysics_output` by default.
  - Emit `selected_examples.cleaned.json` and `comparison_manifest.json`.

- [x] FPC-002: Rediscover current Mathformer artifacts from the repo.
  - Lean: `libraries/MathformerPhysicsLib/Lean/formalphysics_XXXX/MathformerPhysics.lean`.
  - Never score stale self-output from the external JSON.

- [x] FPC-003: Include the full Foundations dependency surface.
  - Inventory `libraries/MathformerPhysicsLib/Lean/Foundations.lean`.
  - Inventory every `libraries/MathformerPhysicsLib/Lean/Foundations/*.lean` file.
  - Score dependency use, duplication, bypasses, import health, and concept
    ownership.

- [x] FPC-004: Implement deterministic Lean judges.
  - Compile each top-level Lean candidate with `lake env lean`.
  - Compile safe external snippets in temporary files.
  - Record errors, warnings, imports, declarations, placeholders, axioms,
    theorem shapes, and broad import use.

- [x] FPC-005: Implement source and reference delta judges.
  - Compare problem text to candidate theorem statements and declarations.
  - Compare reference answer as non-gold evidence.
  - Classify candidate-reference deltas as agreement, stronger preservation,
    weaker preservation, missing assumption, or style-only difference.

- [x] FPC-006: Implement deep Codex-exec judges.
  - Physicist semantics judge.
  - Lean theorem-proving judge.
  - Mathlib grounding judge.
  - Formal modeling and completeness judge.
  - Naming and reviewability judge.
  - Invoked dependency excerpt judge.
  - Foundations dependency judge.
  - Adversarial reference judge.
  - Require JSON outputs with evidence, uncertainty, and repair suggestions.

- [x] FPC-007: Build the hard-gate and score aggregator.
  - Hard gates: compilation, no placeholders, no unreviewed axioms, non-vacuity,
    reference-policy compliance.
  - Scores: source preservation, physics fidelity, Foundations quality,
    mathlib grounding, Mathlib concept grounding, variable naming quality,
    formality depth, physics-representation completeness, assumption
    transparency, proof integrity, derivation coverage, reviewability clarity,
    reference-delta quality, maintainability, reportability.

- [x] FPC-008: Render an attractive self-contained HTML report.
  - Tabs: overview, leaderboard, case details, Lean side-by-side, Foundations,
    judge evidence, role reviews, strategy summary, methodology.
  - Embed JSON in the HTML for MCP or consumer-app processing.
  - Use embedded CSS/JS only.

- [x] FPC-009: Add colored Lean code rendering.
  - Highlight comments, strings, keywords, declaration names, tactics,
    suspicious tokens, imports, and source anchors.
  - Support synchronized side-by-side scrolling.

- [x] FPC-010: Validate on the attached selected examples.
  - Confirm obsolete self-generation is absent from cleaned JSON.
  - Confirm every Mathformer case includes Foundations dependency evidence.
  - Confirm the best-solution summary never treats `answer` as gold.

- [x] FPC-011: Add workflow routing only after the report builder is stable.
  - Add a hub action for preparing comparison inputs.
  - Add a hub action for rendering HTML.
  - Add skill hook coverage and compact tests.

- [x] FPC-012: Add qualitative role reviewers.
  - Emit an independent theorem-prover-expert report for every case.
  - Emit an independent physics-expert report for every case.
  - Include role-specific criteria, primary metrics, essential features,
    strategy tags, strengths, concerns, and preferences.

- [x] FPC-013: Add cross-role strategy synthesis.
  - Compare theorem-prover and physics preferences case by case.
  - Report agreement/disagreement counts and recurring strategy contrasts.
  - Emit standalone Markdown/JSON plus HTML tabs for consumer applications.

- [x] FPC-014: Add enriched critic criteria.
  - Expose `metric_criteria` and `critic_profiles` in JSON and HTML.
  - Add Mathlib concept grounding, variable/declaration naming, formal modeling
    depth, physics-representation completeness, and reviewability clarity.
  - Emit per-candidate `critic_evidence` for human and machine review.

- [x] FPC-015: Import invoked external dependency concepts into excerpt
  comparison.
  - Add declaration excerpts, line spans, and invocation counts to Foundations
    inventory records.
  - Attach `invoked_external_dependency_excerpts` to every candidate report.
  - Add the HTML `Invoked Concepts` tab and aggregate invoked-excerpt counts.

- [x] FPC-016: Replace alternating leaderboard rows with case-grouped coverage
  comparison.
  - Show current Mathformer and external Lean candidates side by side per case.
  - Add coverage bars for source, derivation, physics completeness, formal
    depth, Mathlib grounding, Foundations grounding, and reviewability.
  - Add compact deltas so coverage differences can be scanned visually.

## Implemented Artifacts

- Skill: `skills/physics-common/formalphysics-comparative-analysis-reporter/`.
- Input preparation:
  `skills/physics-common/formalphysics-comparative-analysis-reporter/scripts/prepare_comparison_inputs.py`.
- Report builder:
  `skills/physics-common/formalphysics-comparative-analysis-reporter/scripts/build_comparative_report.py`.
- Compact test:
  `tests/physics_lean/run_formalphysics_comparative_report.py`.
- Role-review outputs:
  `theorem_prover_expert_review.md`, `physics_expert_review.md`,
  `qualitative_role_reviews.json`, and `strategy_comparison_summary.md`.
- Hub actions:
  `physics-lean:formalphysics-comparative-report` and
  `physics-lean:formalphysics-comparative-report-self-test`.
- Hook:
  `report.formalphysics_comparative_analysis`.
