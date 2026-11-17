---
name: formalphysics-judge-synthesis-reporter
description: Build an interpretive synthesis from FormalPhysics comparative report JSON. Use when Codex must combine all cases, both compared Lean approaches, deterministic judges, metric criteria, critic evidence, Codex-exec judge results or prompt statuses, and theorem-prover/physics role reviews into a strengths-and-weaknesses synthesis report with clear aspect-level criteria and follow-up TODOs.
---


# FormalPhysics Judge Synthesis Reporter

Use this skill after `formalphysics-comparative-analysis-reporter` has produced
`comparative_report.json`. The synthesis is not another leaderboard. It turns
judge and reviewer outcomes into a coherent interpretation of the approaches.

## Inputs

- Required: `comparative_report.json`.
- Optional: a directory for synthesis outputs.
- Optional: one or more Codex-exec result JSON/JSONL files or directories.
  Result records are matched by `(case_id, candidate_id, judge_id)`.

## Workflow

1. Read `references/synthesis_protocol.md` when changing criteria, aspect
   grouping, or narrative policy.
2. Run the synthesis builder:

```bash
python skills/physics-common/formalphysics-judge-synthesis-reporter/scripts/build_synthesis_report.py \
  --comparative-report artifacts/formalphysics_comparative_analysis/hub_selected_examples_report/comparative_report.json \
  --output-dir artifacts/formalphysics_judge_synthesis/hub_selected_examples \
  --json
```

To ingest completed Codex-exec judge results at synthesis time, add either:

```bash
--codex-results-json path/to/judge_results.json
--codex-results-dir path/to/result_directory
```

Accepted result containers are a JSON list, a JSON object with `results`,
`judge_results`, `codex_exec_results`, or `codex_exec_judge_results`, or JSONL
with one result wrapper per line.

To prepare or explicitly execute Codex-exec judge prompts, use the dry-run-first
runner:

```bash
python skills/physics-common/formalphysics-judge-synthesis-reporter/scripts/run_codex_exec_judges.py \
  --prompts-json artifacts/formalphysics_comparative_analysis/hub_selected_examples_report/codex_exec_judge_prompts.json \
  --output-dir artifacts/formalphysics_judge_synthesis/codex_exec_judges/hub_selected_examples \
  --candidate-id current_mathformer_lean \
  --judge-id lean_tp_judge \
  --limit 1 \
  --resume \
  --workers 1 \
  --json
```

Add `--execute` only when the user explicitly wants to run Codex-exec. The
runner writes `codex_exec_judge_results.json`, which can be passed back to the
synthesis builder with `--codex-results-json`. Use `--resume` for long runs so
existing final-message files are reused, and increase `--workers` only when the
consumer can tolerate concurrent Codex-exec subprocesses.

3. Interpret both compared approaches across all cases:
   - functional Lean status and hard-gate failures,
   - source and derivation coverage,
   - physics representation completeness,
   - Mathlib and Foundations grounding,
   - invoked external dependency excerpts,
   - proof/modeling depth versus algebraic-shell risk,
   - variable naming and reviewability,
   - theorem-prover and physics role-review preferences,
   - Codex-exec judge results when present, otherwise prompt readiness.

4. Emit:
   - `synthesis_report.json`: machine-readable synthesis;
   - `synthesis_report.md`: concise human report;
   - `synthesis_report.html`: self-contained visual report;
   - `synthesis_todos.md`: follow-up TODOs grounded in weaknesses and missing
     judge evidence.

## Interpretation Rules

- Treat reference answers as non-gold evidence.
- Do not average away disagreements: expose them as interpretation points.
- Separate compile/proof soundness from semantic richness.
- A candidate can compile and still be shallow if it lacks grounding,
  representation completeness, or reviewability evidence.
- A candidate can have rich modeling context and still require repair if hard
  gates fail.
- If Codex-exec judges are pending, state that the synthesis is based on
  deterministic judges and role reviewers, with generative judge prompts ready.
- Keep prompt readiness separate from completed-result disagreements:
  readiness asks what has run, while disagreements ask whether completed
  generative judges conflict with deterministic best-solution choices or
  deterministic metric scores.
- Classify generated follow-up items by `status` and `actionability`.
  External-reference candidate weaknesses are evidence items, not repo-local
  repair tasks.

## Validation

- `build_synthesis_report.py --self-test --json` must pass.
- Generated JSON must include per-approach strengths, weaknesses, aspect
  summaries, role-review synthesis, judge-outcome synthesis, and TODOs.
- Generated HTML must include approach comparison, aspect synthesis, judge
  outcome, and TODO sections.
- The smoke test must cover completed Codex-exec result ingestion and
  disagreement-pattern summaries.
- `run_codex_exec_judges.py --self-test --json` must pass without invoking
  Codex.
- Result ingestion must normalize known judge-id version suffixes such as
  `adversarial_reference_judge_v1` back to their prompt judge id.
