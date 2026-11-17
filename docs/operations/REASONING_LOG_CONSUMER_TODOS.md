<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make Mathformer reasoning logs useful to humans, skills, and MCP-facing
  consumer applications, not merely present as backend traces.

Intent:
  Convert the reasoning-log quality and consumption requirement into concrete,
  reviewable implementation TODOs with explicit acceptance checks.

Function:
  Defines a consumer-grade reasoning-log contract, identifies current gaps,
  and plans skill, hub, and MCP integration work.

Maintenance Notes:
  Keep this synchronized with TODO.md, skills/control/reasoning-log-schema-guardian/,
  skills/SKILL_HOOKS.yaml, scripts/mathformer.py, and docs/architecture/MCP_SERVER.md.
-->

# Reasoning Log Consumer TODOs

Goal: every Mathformer skill should have a reasoning-log path that is
self-contained, self-explanatory, concise, human understandable, and machine
processable. Consumer applications must be able to inspect those logs either
through ordinary Mathformer skills and hub actions or through the MCP service,
without direct knowledge of internal script paths.

## Current Baseline

Observed on 2026-07-08:

- `skills/control/reasoning-log-schema-guardian` owns the JSONL helper, validator,
  Markdown renderer, HTML renderer, wrapper, coverage auditor, and smoke test.
- `python skills/control/reasoning-log-schema-guardian/scripts/self_test_reasoning_logs.py --json`
  passes.
- `python skills/control/reasoning-log-schema-guardian/scripts/audit_skill_reasoning_log_coverage.py --strict --json`
  passes with 181 skills covered.
- Coverage is mostly wrapper-based: 169 skill scripts, 39 native logged scripts,
  and 130 scripts without native reasoning-log instrumentation.
- `scripts/mcp_server.py` exposes six workflow-level MCP tools and one action
  catalogue resource. This is the right boundary: do not add one MCP tool per
  skill.
- `python meta_skills/scripts/validate_mcp_boundary.py --json` passes.
- Natural-language requests such as `validate reasoning log schema`,
  `render reasoning log as html`, and `make sure skills have reasoning logs`
  currently do not resolve through `scripts/mathformer.py ask`, even though
  low-level hub actions exist.

## Design Principles

- A reasoning log is an evidence trace, not hidden chain-of-thought.
- A valid event must be parseable JSONL with stable schema fields, monotone
  event indexes, timestamps, skill identity, optional hook identity, and
  machine-readable decision evidence.
- A useful event must also be readable by a person: short intent, inputs,
  artifacts, evidence, decision, risks, next action, and human summary.
- Wrapper-based coverage is acceptable as a fallback, but high-value workflow
  scripts should emit native domain events so consumers can understand more
  than "command exited 0".
- MCP consumption should stay workflow-level. Expose reasoning-log discovery,
  validation, rendering, summarization, and retrieval through hub actions and
  stable MCP resources, not one tool per skill.
- CLI and MCP observability must stay symmetric. If hub-level reasoning-log
  capture is added, it must serve both `scripts/mathformer.py` and MCP calls.

## TODOs

### RL-001: Define The Consumer-Grade Log Contract

- [x] Extend `skills/control/reasoning-log-schema-guardian/references/schema.md` with
  a "consumer-grade" profile.
- [x] Make the profile explicit about:
  - self-contained: event has enough IDs, input summaries, artifact paths,
    hashes, and decision state to be interpreted without hidden context;
  - self-explanatory: event has a plain-language `intent` and `human_summary`;
  - concise: payloads avoid raw stdout dumps, long model output, and repeated
    full artifacts;
  - human understandable: summaries and risks explain why the event matters;
  - machine processable: sections are typed JSON objects with schema versions.
- [x] Add concrete payload size and summary length recommendations, with
  artifact references preferred over inline blobs.
- [x] Preserve the existing no-chain-of-thought and no-secret policy.

Acceptance:

```bash
python skills/control/reasoning-log-schema-guardian/scripts/self_test_reasoning_logs.py --json
```

### RL-002: Add A Reasoning-Log Quality Auditor

- [x] Add `skills/control/reasoning-log-schema-guardian/scripts/audit_reasoning_log_quality.py`.
- [x] Input: one or more JSONL logs.
- [x] Output: JSON with `ok`, `schema_version`, `log_count`, `event_count`,
  `quality_scores`, `findings`, and `consumer_readiness`.
- [x] Check the five quality dimensions separately:
  `self_contained`, `self_explanatory`, `concise`, `human_understandable`,
  and `machine_processable`.
- [x] Fail high-severity findings for missing `payload.skill_application`,
  missing `intent`, missing `human_summary`, non-object `inputs` or
  `artifacts`, unknown hook ids, and secret-looking values.
- [x] Warn for oversized payloads, very long summaries, missing artifact
  hashes, and wrapper-only events on high-value workflows.
- [x] Register a hub action such as `control:reasoning-log-quality`.
- [x] Add a strict self-test fixture with one good log and one intentionally
  poor log.

Acceptance:

```bash
python skills/control/reasoning-log-schema-guardian/scripts/audit_reasoning_log_quality.py \
  --log-file artifacts/reasoning/self_test/good.jsonl \
  --json
python scripts/mathformer.py audit --strict --json
```

### RL-003: Add Natural-Language Routes For Reasoning Logs

- [x] Add intent routes in `scripts/mathformer.py` so these requests resolve:
  - `validate reasoning log schema`;
  - `render reasoning log as html`;
  - `make sure skills have reasoning logs`;
  - `audit reasoning log quality`;
  - `summarize reasoning log for a consumer application`.
- [x] Route to existing actions where possible:
  `control:reasoning-log-coverage`, `control:reasoning-log-smoke`,
  and `control:reasoning-log-html`.
- [x] Route new quality and summary actions once implemented.
- [x] Update `skills/control/mathformer-workflow-router` help and coverage tests.

Acceptance:

```bash
python scripts/mathformer.py ask "validate reasoning log schema" --json
python scripts/mathformer.py ask "render reasoning log as html" --json
python scripts/mathformer.py ask "make sure skills have reasoning logs" --json
python skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py --audit-coverage --json
```

### RL-004: Add A Stable Reasoning-Log Index

- [x] Add an index artifact, for example `artifacts/reasoning/index.json`.
- [x] Each entry should include `run_id`, `skill`, `hook_id`, `log_file`,
  `created_at_utc`, `status`, `event_count`, `validation_status`,
  `quality_status`, and produced report paths.
- [x] Update `run_with_reasoning_log.py` and native helpers to optionally
  append/update the index.
- [x] Add an index validator and a small fixture.
- [x] Keep the index generated and gitignored unless a specific fixture is
  needed for tests.

Acceptance:

```bash
python skills/control/reasoning-log-schema-guardian/scripts/self_test_reasoning_logs.py --json
python skills/control/reasoning-log-schema-guardian/scripts/validate_reasoning_log_index.py \
  --index artifacts/reasoning/index.json --json
```

### RL-005: Make Consumer Summaries First-Class

- [x] Add a machine-readable summary command, for example
  `summarize_reasoning_log.py`.
- [x] Summary output should include:
  `schema_version`, `ok`, `run_id`, `skills`, `hooks`, `timeline`,
  `decisions`, `risks`, `next_actions`, `artifacts`, and `validation`.
- [x] Keep the summary compact and stable enough for a UI or service client.
- [x] Reuse the existing Markdown/HTML renderers for human views, but do not
  force consumer applications to scrape rendered text.

Acceptance:

```bash
python skills/control/reasoning-log-schema-guardian/scripts/summarize_reasoning_log.py \
  --log-file artifacts/wiki_level_suite/reasoning.jsonl \
  --json
```

### RL-006: Expose Reasoning Logs Through The MCP Boundary

- [x] Preserve the six-tool MCP surface by default.
- [x] Add workflow-level hub actions for log discovery, validation, quality
  audit, summary, and rendering.
- [x] Make those actions reachable through `mathformer_ask` and
  `mathformer_run_action`.
- [x] Consider adding read-only MCP resources:
  - `mathformer://reasoning-logs` for the index;
  - `mathformer://reasoning-log-schema` for the schema/profile;
  - `mathformer://reasoning-log-quality-policy` for quality criteria.
- [x] Do not add one MCP tool per skill and do not expose arbitrary file reads.
- [x] If resource templates are added for individual logs, gate them to the
  reasoning-log index and repository-local artifact roots.

Acceptance:

```bash
python meta_skills/scripts/validate_mcp_boundary.py --json
python tests/mcp/run_mcp_server_self_test.py
```

### RL-007: Keep CLI And MCP Observability Symmetric

- [x] If hub-level reasoning-log capture is added, implement it in
  `scripts/mathformer.py` first and let MCP inherit it.
- [x] Add optional hub flags such as `--reasoning-log-file` or
  `--reasoning-log-dir` for `ask` and `run`.
- [x] Ensure MCP `mathformer_ask(run=True)` and `mathformer_run_action` can
  pass through those options only through controlled action arguments or a
  safe service-level artifact path policy.
- [x] Keep `artifacts/mcp_server/calls.jsonl` as a service call audit log,
  not a replacement for reasoning logs.

Acceptance:

```bash
python scripts/mathformer.py ask "run the compact quality gate before commit" \
  --run --dry-run --json
python tests/mcp/run_mcp_server_self_test.py
```

### RL-008: Prioritize Native Logging For High-Value Scripts

- [x] Keep wrapper logging as a baseline.
- [x] Migrate native lifecycle logging first for scripts that drive review,
  routing, recursive repair, final acceptance, and MCP/service boundaries.
- [x] Initial priority list:
  - `skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py`;
  - `skills/autoformalization/final-derivation-review-orchestrator/scripts/run_final_derivation_review.py`;
  - `skills/physics-lean/physics-lean-goal-sample-autoformalizer/scripts/run_recursive_goal_case.py`;
  - `skills/physics-lean/physics-lean-goal-sample-autoformalizer/scripts/plan_goal_sample_autoformalization.py`;
  - `skills/physics-common/physics-final-hypothesis-reviewer/scripts/review_physics_final_hypotheses.py`;
  - `skills/physics-lean/physics-lean-review-refinement-router/scripts/plan_review_refinement.py`;
  - `scripts/load_mcp_service_config.py`;
  - `scripts/mathformer_mcp_service.py`.
- [x] Add `--reasoning-log-file` to each migrated script.
- [x] Emit domain-specific evidence in `payload.skill_application.evidence`,
  not only command return codes.

Acceptance:

```bash
python skills/control/reasoning-log-schema-guardian/scripts/audit_skill_reasoning_log_coverage.py \
  --require-native-script-logging --json
```

Note: strict all-script native migration remains a progress metric; this slice
keeps wrapper logging as the baseline and adds native consumer-grade events to
the hub, workflow router, final review aggregation, review refinement, and the
Physics SymPy recursive workflow scripts.

### RL-009: Add Consumer Application Fixtures

- [x] Add fixture logs that represent:
  - a successful single-skill run;
  - a multi-skill physics Lean recursive repair run;
  - a failing or blocked workflow with recoverable next actions;
  - a wrapper-only fallback event.
- [x] Add tests that parse those fixtures as a consumer application would.
- [x] Assert no consumer needs to parse prose to recover `status`, `skill`,
  `run_id`, `artifacts`, `risks`, or `next_actions`.

Acceptance:

```bash
python tests/reasoning_logs/run_consumer_contract_suite.py
```

### RL-010: Add Security And Redaction Gates

- [x] Add secret-pattern checks for environment variable names, bearer tokens,
  API keys, local private paths when they are not needed, and raw credential
  values.
- [x] Apply the checks to reasoning logs, rendered Markdown, rendered HTML,
  summaries, and MCP resource payloads.
- [x] Keep raw stdout/stderr out of logs unless explicitly bounded and
  redacted.
- [x] Document the redaction policy in the schema reference and MCP docs.

Acceptance:

```bash
python skills/control/reasoning-log-schema-guardian/scripts/audit_reasoning_log_quality.py \
  --log-file artifacts/reasoning/redaction_fixture.jsonl --json
python tests/mcp/run_mcp_auth_adversarial_test.py
```

### RL-011: Integrate Reasoning Logs Into Review Workflows

- [x] Teach review/refinement workflows to attach reasoning-log summaries to
  final review artifacts.
- [x] For Lean physics reviews, record source alignment, semantic-preservation
  contract status, unit/dimension status, non-vacuity status, and next repair
  action as structured evidence.
- [x] Make review TODO generation consume structured summaries instead of
  relying only on saved JSON reports.
- [x] Ensure review logs are short enough for humans to inspect and structured
  enough for a dashboard.

Acceptance:

```bash
python skills/autoformalization/final-derivation-review-orchestrator/scripts/run_final_derivation_review.py --self-test
python skills/physics-lean/physics-lean-review-refinement-router/scripts/plan_review_refinement.py --self-test
```

## Release Gate For This Workstream

The workstream is complete when:

- reasoning-log schema self-test passes;
- coverage audit passes;
- quality audit passes on consumer fixtures;
- natural-language reasoning-log routes resolve;
- MCP boundary test still passes without per-skill tools;
- MCP self-test proves a consumer can discover or run reasoning-log workflows;
- docs explain the CLI, skill, and MCP consumption paths;
- no logs, summaries, rendered dashboards, or MCP resources leak secrets or
  hidden chain-of-thought.
