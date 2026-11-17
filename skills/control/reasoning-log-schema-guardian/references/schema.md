<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

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

# Reasoning Log Schema

Canonical JSONL event fields:

- `event_index`: positive integer, monotonically increasing within a log.
- `timestamp_utc`: ISO-8601 UTC timestamp.
- `timestamp_unix_ms`: Unix timestamp in milliseconds.
- `monotonic_ns`: monotonic clock value for duration reconstruction.
- `elapsed_ms_since_log_start`: milliseconds since first event in this log writer.
- `elapsed_ms_since_prev_event`: milliseconds since previous event in this log writer, or null.
- `statement_hash`: optional short hash of the informal statement.
- `file_prefix`: optional run/file prefix.
- `dependency_label`: optional dependency label.
- `step`: stable event step name.
- `payload`: JSON object.
- `payload.skill`: required skill/runtime identifier.
- `payload.hook_id`: required when the event belongs to a systematic hook.
- `payload.agent_usage`: instrumented where-used metadata for the agent or skill.
  It should include `agent_or_skill`, `step`, `hook_id`, hook phase/owner when
  known, and a `usage_site` object with file prefix, dependency label, and
  statement hash.
- `payload.convergence_criteria`: instrumented stop/pass criteria for the event.
  When `payload.hook_id` is known, this is populated from the hook `gate` field;
  otherwise it records payload-inferred evidence such as `ok`, `status`, target
  scores, correctness, or blocking finding counts.
- `payload.skill_call_id`: stable identifier for one skill invocation.
- `payload.parent_call_id`: optional identifier for the parent skill or
  workflow invocation.
- `payload.run_id`: optional workflow-level run identifier shared across skill
  invocations.
- `payload.skill_application`: required for new skill-application logs. This
  object is the self-explaining contract that lets humans audit why a skill ran,
  what it consumed, what it produced, and what remains uncertain.

Canonical skill-application steps:

- `skill_application_start`
- `skill_application_context_loaded`
- `skill_application_input_normalized`
- `skill_application_action_taken`
- `skill_application_evidence_recorded`
- `skill_application_gate_evaluated`
- `skill_application_complete`
- `skill_application_error`

Canonical `payload.skill_application` fields:

- `schema_version`: integer schema version for the skill-application payload.
- `skill`: skill or runtime identifier.
- `hook_id`: optional hook id when the invocation belongs to a hook contract.
- `run_id`: optional workflow-level run identifier.
- `skill_call_id`: stable identifier for this skill invocation.
- `parent_call_id`: optional parent invocation id.
- `status`: `running`, `complete`, `blocked`, `error`, or another explicit
  local status.
- `intent`: short natural-language statement of why the skill was invoked.
- `inputs`: object summarizing source inputs, user request slice, config, and
  relevant hashes or paths.
- `artifacts`: object listing produced or consumed artifact paths.
- `evidence`: object summarizing backend output, checks, metrics, or extracted
  observations.
- `decision`: object recording gate result, acceptance state, or local decision.
- `risks`: object recording unresolved assumptions, blockers, regressions, or
  missing evidence.
- `next_action`: short instruction for the next recoverable action.
- `human_summary`: one or two sentence explanation of the event.

Reasoning logs are structured epistemic traces, not raw chain-of-thought. They
should record inspectable evidence, decisions, and blockers. They should not
store hidden deliberation, secrets, credentials, or long raw model outputs.

## Consumer-Grade Profile

The consumer-grade profile is the stricter profile used when a log is expected
to be read by a downstream application, dashboard, review workflow, or MCP
client. It keeps the existing schema and adds quality expectations rather than
new hidden fields.

Consumer-grade logs must be:

- self-contained: every event has stable IDs, a skill name, optional hook and
  run IDs, input summaries, artifact paths, decision state, and enough evidence
  to interpret the event without private context;
- self-explanatory: every skill-application event has a short `intent` and a
  plain-language `human_summary`;
- concise: payloads point to artifacts instead of embedding raw stdout, long
  model output, full documents, or repeated complete reports;
- human understandable: summaries, risks, decisions, and next actions explain
  why the event matters and what remains uncertain;
- machine processable: `inputs`, `artifacts`, `evidence`, `decision`, and
  `risks` are typed JSON objects with a `schema_version` on
  `payload.skill_application`.

Recommended bounds:

- keep `intent` under 180 characters when possible;
- keep `human_summary` under 320 characters and at most two sentences;
- keep one event payload under about 8 KiB unless it is a deliberately bounded
  fixture;
- store large command output, rendered reports, and derivation artifacts in
  files and reference them through `artifacts` with hashes when stability
  matters;
- keep recoverable errors short and put the recovery instruction in
  `next_action`.

Security and redaction rules:

- never log bearer tokens, API keys, passwords, cookies, raw credentials, or
  private provider configuration values;
- avoid local private paths unless the path is a repository-local artifact that
  the consumer needs to retrieve;
- redact raw stdout or stderr before logging it, and prefer artifact references
  for bounded diagnostic files;
- do not store hidden chain-of-thought. Record only observable inputs,
  evidence, decisions, risks, and next actions.

Strict validation treats malformed JSON, missing `step`, missing `payload`,
missing `payload.skill`, nonmonotonic event indexes, and unknown hook ids as
blocking. Missing elapsed fields are reported as advisory compatibility findings
while older runtimes are still being migrated.
Use `--require-instrumentation` to require `payload.agent_usage` and
`payload.convergence_criteria` in new reasoning logs.
Use `--require-skill-application` to require `payload.skill_application` on
every event in a new log.
