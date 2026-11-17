<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make Mathformer skill execution auditable without exposing hidden
  chain-of-thought.

Intent:
  Explain the reasoning-log contract for deterministic scripts, generative
  skills, workflow orchestrators, validators, and human-readable traces.

Function:
  Defines the standard skill-application lifecycle, required payload fields,
  privacy boundaries, rendering path, and coverage gates.

Maintenance Notes:
  Keep this page aligned with `reasoning_log.py`, `validate_reasoning_log.py`,
  `render_reasoning_log.py`, `render_reasoning_log_html.py`, and
  `audit_skill_reasoning_log_coverage.py`.
-->

# Reasoning Logs

Mathformer reasoning logs are structured epistemic traces. They explain which
skill ran, why it ran, what evidence it consumed, what artifact it produced,
which gate or decision applied, and what remains uncertain.

They are not raw chain-of-thought. A good log stores inspectable evidence,
summaries, hashes, paths, metrics, and blockers. It does not store secrets,
credentials, hidden deliberation, or long raw model outputs.

## Skill-Application Lifecycle

Every new skill application should be expressible through this lifecycle:

1. `skill_application_start`
2. `skill_application_context_loaded`
3. `skill_application_input_normalized`
4. `skill_application_action_taken`
5. `skill_application_evidence_recorded`
6. `skill_application_gate_evaluated`
7. `skill_application_complete` or `skill_application_error`

Not every skill needs every intermediate step. Every skill should have a start
and a terminal event.

## Required Payload

New skill-application events use `payload.skill_application`:

| Field | Purpose |
| --- | --- |
| `intent` | Why this skill was invoked |
| `inputs` | Source inputs, request slice, configuration, hashes, and paths |
| `artifacts` | Files or reports consumed or produced |
| `evidence` | Backend output, extracted facts, checks, scores, or observations |
| `decision` | Gate result, acceptance status, or local decision |
| `risks` | Blockers, regressions, missing assumptions, or unresolved evidence |
| `next_action` | The next recoverable action |
| `human_summary` | Short explanation for readers |

The event also carries `skill`, optional `hook_id`, optional `run_id`,
`skill_call_id`, and optional `parent_call_id` so workflow-level traces can be
stitched back together.

## Deterministic Scripts

Scripts should eventually expose `--reasoning-log-file` and use:

- `append_skill_start`
- `append_skill_progress`
- `append_skill_complete`
- `append_skill_error`

Scripts that do not yet have native support can still be run through:

```bash
python3 skills/control/reasoning-log-schema-guardian/scripts/run_with_reasoning_log.py \
  --reasoning-log-file artifacts/reasoning/example.jsonl \
  --skill example-skill \
  --intent "Run the example skill under a reasoning-log envelope." \
  -- python3 skills/example-skill/scripts/example.py --json
```

The wrapper records the execution envelope. Native instrumentation remains
preferred when the script can report richer internal evidence.

## Generative Skills

Generative skills without scripts are logged by the applying agent. The agent
should record:

- which `SKILL.md` and reference files were loaded;
- the user request slice assigned to the skill;
- the expected artifact or answer type;
- the quality criteria used;
- produced artifact paths or output summaries;
- blocker status and next action.

This gives no-script skills the same audit shape as deterministic scripts.

## Rendering

JSONL is the durable machine format. For compact review, render it to Markdown:

```bash
python3 skills/control/reasoning-log-schema-guardian/scripts/render_reasoning_log.py \
  --log-file artifacts/reasoning/example.jsonl \
  --output-file artifacts/reasoning/example.md
```

The rendered trace groups events by skill invocation and shows intent, artifacts,
evidence, risks, decision, and next action.

For a friendlier inspection surface, render the same log as a self-contained
HTML dashboard:

```bash
python3 skills/control/reasoning-log-schema-guardian/scripts/render_reasoning_log_html.py \
  --log-file artifacts/reasoning/example.jsonl \
  --output-file artifacts/reasoning/example.html
```

The HTML view adds summary cards, validation status, skill/status/step filters,
search, invocation panels, a timeline table, and expandable raw JSON evidence.
It can be opened directly in VS Code or a browser.

## Workflow Examples

Lean autoformalization logs should show the movement from source statement to
Lean surface, then compile or consistency evidence:

- intent: produce or inspect a Lean theorem candidate;
- artifacts: informal source, `.lean` file, compile report, consistency report;
- evidence: Lean return code, diagnostic count, non-vacuity score, source-anchor
  coverage;
- decision: checked, candidate-only, blocked, or needs refinement.

Vampire ATP logs should show the proof-search chain:

- intent: prove a first-order target;
- artifacts: informal statement, generated TPTP problem, TSTP proof,
  premise-selection report;
- evidence: SZS status, selected premises, helper lemma proof status;
- decision: theorem proved, counter-satisfiable, timeout, or blocked by
  translation.

Physics SymPy logs should show equation and assumption control:

- intent: validate a symbolic derivation;
- artifacts: source derivation, generated SymPy file, execution report,
  unit/dimension report;
- evidence: residuals, initial-condition checks, units, numeric sanity samples;
- decision: executable validation passed, partial validation, or blocked by
  missing assumptions.

Premise-selection logs should show retrieval quality:

- intent: find relevant facts or check exact presence;
- artifacts: KB entries, Bloom manifest, embedding index, search report;
- evidence: presence result, top semantic hits, cosine distances;
- decision: exact match found, candidates returned, or KB curation needed.

Reference-free monitor logs should show trajectory evidence:

- intent: measure whether a formalization improved without a gold reference;
- artifacts: current snapshot, ledger, evolution SVG, CSV, and JSON;
- evidence: score deltas, risk deltas, regression counts, weakest dimensions;
- decision: accept snapshot, refine weakest dimension, or block regression.

## Validation

Validate schema and hook ids:

```bash
python3 skills/control/reasoning-log-schema-guardian/scripts/validate_reasoning_log.py \
  --log-file artifacts/reasoning/example.jsonl \
  --hooks-file skills/SKILL_HOOKS.yaml \
  --strict \
  --require-instrumentation \
  --require-skill-application \
  --json
```

Audit repository coverage:

```bash
python3 skills/control/reasoning-log-schema-guardian/scripts/audit_skill_reasoning_log_coverage.py \
  --strict \
  --json
```

Coverage classes:

| Class | Meaning |
| --- | --- |
| `script-logged` | The skill has script coverage, either native or through the logged wrapper |
| `agent-logged` | The skill is applied through an agent-side skill-application packet |
| `workflow-only` | The skill is only visible through a parent workflow |
| `missing` | No acceptable logging path was found |

## Blockers

Error events should be useful. They must say:

- what stopped;
- which artifact or command was affected;
- what evidence is available;
- whether the failure is a source mismatch, missing dependency, backend limit,
  validation failure, or generated-statement drift;
- what the next recoverable action is.

## Portable adoption invocation sidecars

The [bounded adoption pilot](../migrations/portable-repository-adoption/usage.md)
adds optional immutable public-result receipts using this existing logger.
Its versioned provenance sidecar joins the unchanged JSONL schema to exact
terminal snapshots; it does not enrich or rewrite historical records in place.
