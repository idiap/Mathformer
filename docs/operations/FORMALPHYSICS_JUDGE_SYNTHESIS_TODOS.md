<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# FormalPhysics Judge Synthesis TODOs

## Scope

Create a synthesis workflow that consumes
`formalphysics-comparative-analysis-reporter` outputs and interprets all cases,
both compared Lean approaches, deterministic judges, Codex-exec judge
statuses/results, and theorem-prover/physics role reviews.

## TODOs

- [x] FPS-001: Create a repo-local synthesis skill.
  - Skill: `skills/physics-common/formalphysics-judge-synthesis-reporter/`.
  - Trigger: comparative-report interpretation, judge/reviewer synthesis,
    strengths/weaknesses analysis, follow-up TODO generation.

- [x] FPS-002: Define aspect-level synthesis criteria.
  - Functional Lean.
  - Source and derivation coverage.
  - Physics completeness.
  - Grounding depth.
  - Reviewability and naming.
  - Judge/reviewer consensus.

- [x] FPS-003: Implement a deterministic synthesis builder.
  - Input: `comparative_report.json`.
  - Outputs: `synthesis_report.json`, `synthesis_report.md`,
    `synthesis_report.html`, and `synthesis_todos.md`.
  - Preserve non-gold reference policy.

- [x] FPS-004: Interpret both approaches across all cases.
  - Aggregate hard gates, accepted/blocked counts, role preferences, best
    solution counts, metric means, critic evidence, and judge prompt/result
    statuses.
  - Produce coherent strengths and weaknesses for each approach.

- [x] FPS-005: Generate follow-up TODOs from synthesis weaknesses.
  - Hard-gate repair TODOs.
  - Pending Codex-exec judge TODOs.
  - Dependency-context TODOs.
  - Aspect-specific improvement TODOs.

- [x] FPS-006: Validate the skill.
  - Run `build_synthesis_report.py --self-test --json`.
  - Run the builder on the live selected-examples comparative report.
  - Validate the skill folder with the system skill validator.

- [x] FPS-007: Add controlled workflow-hub actions.
  - `physics-lean:formalphysics-judge-synthesis-report`.
  - `physics-lean:formalphysics-judge-synthesis-report-self-test`.
  - Natural-language route:
    `report.formalphysics.judge_synthesis`.

- [x] FPS-008: Add a compact test under `tests/physics_lean/`.
  - Test: `tests/physics_lean/run_formalphysics_judge_synthesis_report.py`.
  - Checks JSON, Markdown, HTML, TODO artifacts, reference policy, approach
    strengths/weaknesses, and aspect comparisons.

- [x] FPS-009: Ingest completed Codex-exec judge JSON and summarize
  disagreement patterns separately from prompt-readiness status.
  - CLI flags: `--codex-results-json` and `--codex-results-dir`.
  - Matches completed results by `(case_id, candidate_id, judge_id)`.
  - Reports prompt readiness separately from completed-result disagreements.
  - Classifies generated follow-up items by status and actionability so
    external-reference weaknesses do not appear as local repair tasks.

- [x] FPS-010: Add a high-cost optional runner that executes selected
  Codex-exec judge prompts and writes result JSON for later ingestion.
  - Runner: `skills/physics-common/formalphysics-judge-synthesis-reporter/scripts/run_codex_exec_judges.py`.
  - Dry-run by default; requires explicit `--execute` before invoking Codex.
  - Supports resumable long runs with `--resume` and bounded concurrency with
    `--workers`.
  - Writes `selected_codex_exec_judge_prompts.json`,
    `codex_exec_judge_results.json`, and
    `codex_exec_judge_run_manifest.json`.
  - Hub actions:
    `physics-lean:formalphysics-codex-exec-judge-runner` and
    `physics-lean:formalphysics-codex-exec-judge-runner-self-test`.
