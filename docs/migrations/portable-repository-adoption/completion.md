<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Portable adoption completion record

The frozen four-surface tranche is implemented. Canonical locations and legacy
routes are retained. There are eight typed operations, six explicit adapters,
ten new controlled hub actions and 22 passing compatibility tests.
The [follow-up regression assurance](REGRESSION_ASSURANCE.md) expands verification
to all historical route examples, all 14 PRISM workflows, and 88 before/after
checks; it records four unchanged baseline failures and the binding-drift fix.

## Implementation and ownership

- Canonical metadata and strict schema: `skills/control/workflow-contract-validator/references/portable-adoption.json` and `portable-adoption.schema.json`.
- Resolver, generated catalog and explicit adapters: the same skill's `scripts/portable_adoption.py`.
- Optional synchronous recorder and offline validator/renderer: `skills/control/reasoning-log-schema-guardian/scripts/adoption_provenance.py`, using the existing JSONL logger.
- Hub and NL routes: `scripts/mathformer.py`; tests: `tests/control/test_portable_adoption.py` and `test_adoption_provenance.py`, registered in `tests/test_matrix.json`.
- Existing hooks `control.workflow_contract` and `control.reasoning_log_schema` retain ownership. Their source registry and the meta-skill-only MCP mapping need no parallel entries or new schema. Registering the new actions/tests supplies Python entrypoint coverage without changing PRISM's semantic source fingerprint.

[Scope mapping](scope-map.md), [contracts](contracts.md), [catalog](catalog.md) and
[usage](usage.md) describe each binding. The three canonical skill sources remain
visible through their existing host projections; PRISM stays an existing workflow
rather than becoming a copied skill. The imported kit remains reference-only.

## Observed verification

| Check | Result and evidence |
| --- | --- |
| Initial controlled pilot gate | PASS: 10 adapter/contract tests and 11 provenance tests; metadata and catalog checks; no unexpected writes. [Receipt](evidence/a08-final/pilot-gate.json). |
| Python workflow control | PASS: 312/312 entrypoints controlled, up from 308/308 by the two new modules and two tests. [Audit](evidence/a08-final/audit.json). |
| Legacy routing and host publication | PASS: baseline and final stdout byte-identical for the recorded request and dry-run discovery. [Router](evidence/a08-final/router.json), [discovery](evidence/a08-final/discovery.json). |
| Legacy validator and log consumers | PASS: exact captured validator command/exit/stdout/stderr parity; summary/validation result parity and historical bytes unchanged. Included in pilot tests; [consumer suite](evidence/a08-final/consumer.json). |
| PRISM fake handler | PASS: selected public/material fixture execution and offline verification. [Baseline fixture](evidence/a01-baseline/prism-fixture.json), pilot tests and saved receipts. |
| PRISM native Codex handler | PASS: selected artifact acceptance workflow, public/material native effects, offline verification and conservative fixture non-promotion oracle. [Native report](evidence/a08-final/prism-native.json), [command](evidence/a08-final/prism-native-command.json). |
| Compact repository gate | Existing failure reproduced exactly before/after in an isolated checkout: `control:reasoning-flow-catalog` reports stale materialization documentation. No new failure before that stop. [Baseline](evidence/a01-baseline/compact.json), [final](evidence/a08-final/compact.json). |
| Layout, links, source preservation and archive integrity | Results in [final verification](evidence/a08-final/verification.json). |

The native command used the repository's existing `.venv/bin/python` because the
system Python lacks PyYAML, narrowed `--workflow artifact_acceptance_loop`, set
`--jobs 1`, and wrote a new evidence report. It did not regenerate existing PRISM
artifacts. No overlap/concurrency claim is made for that single-workflow run.
The full 14-workflow native suite is outside the four-surface tranche.

## Inspect an actual invocation

The validator was invoked through `adoption:invoke`, which called the existing
controlled hub leaf. Its invocation ID is `8f48b028072c42e6b6b43de7645339c8`.

- [Exact terminal result](evidence/a04-pilot/receipts/8f48b028072c42e6b6b43de7645339c8/result.json)
- [Original reasoning JSONL](evidence/a04-pilot/receipts/8f48b028072c42e6b6b43de7645339c8/reasoning.jsonl)
- [Linked provenance and metadata snapshot](evidence/a04-pilot/receipts/8f48b028072c42e6b6b43de7645339c8/provenance.json)
- [Offline HTML view](evidence/a04-pilot/receipts/8f48b028072c42e6b6b43de7645339c8/receipt.html)

[All six invocation receipts](evidence/a04-pilot/invocations.json) cover validator,
router, log summary/validation, and PRISM public/material fixture adapters.
Copies in this evidence directory preserve the original three receipt files;
the HTML file is a separately rendered view. Runtime copies remain under
`artifacts/adoption/`.

## Limits and rollback

Native handler evidence remains a placeholder-fixture safety check, not proof of
a Lean artifact or full semantic equivalence. No scientific artifact is promoted.
The compact gate stops at the known baseline failure; downstream checks after
that stop are not claimed as verified. Optional receipts support public strict
JSON and synchronous callables; async execution and automatic cross-process
parent propagation are outside this contract. Callers own retries and public-data
selection. Hashes establish consistency, not authentication.

Changes are uncommitted. To roll back, remove only the new adoption action blocks
and NL route from `scripts/mathformer.py`, the two new matrix entries, the two new
modules, the two metadata/schema files, the two test files, and this tranche's
documentation additions. Restore only the appended adoption sections in the three
skill guides, `AGENTS.md`, and `docs/architecture/REASONING_LOGS.md`. Keep the earlier
extracted reference kit and initial intake evidence if retaining the plan. Inspect
later edits before removing any file; do not reset the checkout. No original
implementation, public alias or generated proof needs restoration. Preserve the
unrelated `mathformer-prism-projects.zip` and historical records. New receipts may
be retained as immutable history even when the adapters are removed.
