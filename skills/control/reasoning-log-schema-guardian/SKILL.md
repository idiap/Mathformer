---
name: reasoning-log-schema-guardian
description: Validate, normalize, and emit structured Mathformer reasoning-log JSONL events. Use when a skill writes reasoning logs, when a workflow needs log schema enforcement, or when hook events must be checked for event indexes, timestamps, payload.skill, hook_id validity, and parseable JSONL structure.
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

# Reasoning Log Schema Guardian

## Purpose

Use this skill to make reasoning logs uniform across Mathformer skills. It owns
the JSONL event shape, schema validation, and hook-id checks against
`skills/SKILL_HOOKS.yaml`.

Runtime:
- `scripts/reasoning_log.py`: shared append helper for JSONL events.
- `scripts/validate_reasoning_log.py`: deterministic schema validator.
- `scripts/render_reasoning_log.py`: human-readable Markdown renderer.
- `scripts/render_reasoning_log_html.py`: self-contained HTML dashboard
  renderer for filtering and inspecting reasoning traces.
- `scripts/run_with_reasoning_log.py`: wrapper for scripts that do not yet
  expose native reasoning-log flags.
- `scripts/audit_skill_reasoning_log_coverage.py`: repository-wide coverage
  auditor for skill logging status.
- `scripts/audit_reasoning_log_quality.py`: consumer-grade quality and
  redaction auditor.
- `scripts/summarize_reasoning_log.py`: compact JSON summary for consumer
  applications.
- `scripts/index_reasoning_logs.py`: stable index builder for discoverable
  reasoning-log artifacts.
- `scripts/validate_reasoning_log_index.py`: validator for the stable index.
- `scripts/self_test_reasoning_logs.py`: deterministic smoke test for helpers,
  validation, rendering, and coverage.
- hook: `control.reasoning_log_schema`

## Workflow

1. Use `append_reasoning_log_entry(...)` from `scripts/reasoning_log.py` when a
   runtime writes events.
2. Include `payload.skill` on every event.
3. Include `payload.hook_id` when the event belongs to a hook in
   `skills/SKILL_HOOKS.yaml`.
4. Validate logs before using them for process statistics, gates, or release
   claims.
5. Treat invalid JSON, missing `step`, missing `payload`, missing `payload.skill`,
   and unknown hook ids as blocking in strict mode.
6. For new skill applications, use the skill lifecycle helpers:
   `append_skill_start`, `append_skill_progress`, `append_skill_complete`, and
   `append_skill_error`.
7. Keep payloads self-explaining. Record intent, inputs, artifacts, evidence,
   decision, risks, next action, and a human summary; do not log hidden
   chain-of-thought or secrets.

## Commands

```bash
python3 skills/control/reasoning-log-schema-guardian/scripts/validate_reasoning_log.py \
  --log-file artifacts/wiki_level_suite/reasoning.jsonl \
  --hooks-file skills/SKILL_HOOKS.yaml \
  --strict \
  --require-instrumentation \
  --json
```

Render a log for human inspection:

```bash
python3 skills/control/reasoning-log-schema-guardian/scripts/render_reasoning_log.py \
  --log-file artifacts/wiki_level_suite/reasoning.jsonl \
  --output-file artifacts/wiki_level_suite/reasoning.md
```

Render the same log as a browser-friendly dashboard:

```bash
python3 skills/control/reasoning-log-schema-guardian/scripts/render_reasoning_log_html.py \
  --log-file artifacts/wiki_level_suite/reasoning.jsonl \
  --output-file artifacts/wiki_level_suite/reasoning.html
```

Audit repository-wide coverage:

```bash
python3 skills/control/reasoning-log-schema-guardian/scripts/audit_skill_reasoning_log_coverage.py \
  --strict \
  --json
```

Audit consumer-grade quality and create fixtures:

```bash
python3 skills/control/reasoning-log-schema-guardian/scripts/audit_reasoning_log_quality.py \
  --self-test \
  --json
```

Summarize and index logs for consumer applications:

```bash
python3 skills/control/reasoning-log-schema-guardian/scripts/summarize_reasoning_log.py \
  --log-file artifacts/reasoning/self_test/good.jsonl \
  --json

python3 skills/control/reasoning-log-schema-guardian/scripts/index_reasoning_logs.py \
  --ensure-fixtures \
  --json
```

Run the contract smoke test:

```bash
python3 skills/control/reasoning-log-schema-guardian/scripts/self_test_reasoning_logs.py \
  --json
```

## References

- Read `references/schema.md` when changing the event schema or adding a new
  event-producing runtime.

## Optional adoption provenance

`adoption_provenance.py` records public strict-JSON results in fresh invocation
directories through the existing skill start/terminal log helpers. Its optional
sink cannot replace a return value or exception, retry an action, or rewrite
historical logs. Offline `adoption:receipt-validate` and
`adoption:receipt-render` operate on existing receipts only. See
`docs/migrations/portable-repository-adoption/contracts.md` for the local versioned
contract, digest rules and supported execution boundaries.
