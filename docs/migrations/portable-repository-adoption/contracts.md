<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--

Motivation: Make additive metadata and public evidence contracts reviewable.
Intent: Define serialization, API boundaries and supported evidence claims.
Function: A03 contract reference for the frozen portable adoption tranche.
Maintenance: Update alongside versioned schema, adapter and provenance tests.
-->

# Portable metadata and provenance contracts, version 1

The existing callable and hub interfaces remain authoritative. The new adapter
provides six explicitly implemented invocation routes and describes eight
operations. It does not dispatch arbitrary metadata to arbitrary code. The
[scope map](scope-map.md) identifies each owner and compatibility boundary.

## Metadata

The canonical record is
[portable-adoption.json](../../../skills/control/workflow-contract-validator/references/portable-adoption.json),
governed by the strict
[JSON Schema](../../../skills/control/workflow-contract-validator/references/portable-adoption.schema.json).
Both use metadata version 1. The schema is Draft 2020-12; runtime validation
interprets the finite schema vocabulary used here with Python's standard library.
It does not require a JSON Schema or YAML package. Extending that vocabulary
requires extending and testing the validator.

| Record | Required fields and meaning |
| --- | --- |
| Root | `schema_version`, exact `canonical_roots`, canonical `taxonomy_sources`, nonempty `surfaces`. |
| Surface | Existing `id`, `kind`, `owner`, `scope`, nonempty `operations`. Skill owners must resolve to their existing canonical skill directory. |
| Operation | Unique `id`, unique `aliases`, `binding`, `typing`, `inputs`, `outputs`, `availability`, nonempty `evidence_limits`, and independent `role`. |
| Binding | `kind`, repository-relative real `path`, existing `symbol`; `hub_action` additionally requires a real `action_id` whose current command names that path. |
| Typing | Independent execution posture, specification styles, composition role, effects, authority profile, output type, reasoning method, invocation mechanism, generation boundary, output authority, source references and mapping basis. |
| Input | `type` names the existing argument representation; `description` states its native contract. This is not a universal runtime argument schema. |
| Output | `type` names the existing representation; `description`, `authority` and explicit `writes` state its boundary. Semantic output type remains a separate taxonomy field. |
| Availability | `requires` lists declared prerequisites; it does not attest to current provider availability. |

Unknown fields are rejected at every metadata object level, including bindings,
I/O and source mappings. Empty required text, unsupported versions, unknown
taxonomy/I/O values, duplicate IDs/aliases, missing owners or symbols, escaping
paths and mismatched binding mechanisms are invalid. The six explicit adapters
also require the exact owner/path/symbol/action binding implemented by their
dispatcher, so metadata cannot describe a different existing callable while
recording execution of the original one. Aliases point directly to
canonical operation IDs; alias chains and cycles are forbidden. The current
schema intentionally describes this pilot's finite I/O representations.

Taxonomy references retain their existing authoritative files. Skill reasoning
source fragments are checked against actual `skill_bindings` entries in
`skills/REASONING_TYPES.yaml`; workflow interpretations cite actual primitive IDs
and state their mapping basis. Sources establish declared classification, not
observed execution. Native PRISM entrypoint signatures constrain output types.
Generated outputs must retain proposal authority and their generation effect;
the current material fixture must retain its explicit
`not_executed_by_structural_fixture` limitation. These mechanical checks detect
specific contradictions; they are not a natural-language truth checker for all
descriptive text.

## Adapter API

The implementation is
[portable_adoption.py](../../../skills/control/workflow-contract-validator/scripts/portable_adoption.py).
`load_contract(path)` returns metadata and its validated identity index;
`resolve(identity, data=None)` returns `(surface, operation)` for an existing ID
or alias; `catalog_text(data)` creates deterministic documentation without invoking
an operation. `invoke(identity, inputs, output_dir=None)` uses this explicit map:

| Operation | Adapter inputs | Adapter result |
| --- | --- | --- |
| `router:resolve` | `request`; optional `limit` and `family` | JSON projection of the native ordered `IntentMatch` records. The native Python API still returns its original records. |
| `control:workflow-contract` | Empty object | Existing hub `run_action` result, including its command result and exit information. |
| `control:reasoning-log-summary` | `log_file` path string | Native consumer summary dictionary with current schema and quality checks. |
| `reasoning-log:validate` | `log_file` path string | Native validation dictionary with existing default options. |
| `artifact_acceptance_loop:public` | Empty object | Fake-handler fixture result with explicit `fixture`, `handler`, `backend_verified: false`, authority and native PRISM result. |
| `artifact_acceptance_loop:material` | Empty object | Corresponding material fixture result with the same explicit evidence limits. |

`control:reasoning-log-html` and `reasoning-log:append` are discoverable native
bindings; calling them through this new adapter is rejected. Their existing
entrypoints are unchanged. Unknown adapter inputs are rejected. PRISM invokes
the existing project wrapper and adjacent runtime, then runs offline trace
verification; it does not replace fake handlers with providers or execute Lean.

Controlled commands retain hub preflight and write auditing:

```bash
python3 scripts/mathformer.py run adoption:validate --json
python3 scripts/mathformer.py run adoption:describe --json -- router:resolve
python3 scripts/mathformer.py run adoption:invoke --json -- router:resolve --inputs '{"request":"make sure every workflow is controlled"}'
python3 scripts/mathformer.py run adoption:catalog-check --json
python3 scripts/mathformer.py run adoption:check --json
```

`adoption:catalog` regenerates the declared documentation path and requires the
hub's existing mutation authorization flag. The invocation CLI writes only under
`artifacts/adoption/`; the Python API accepts an explicit caller-selected receipt
directory or `None` to disable optional recording.

## Public provenance and serialization

[adoption_provenance.py](../../../skills/control/reasoning-log-schema-guardian/scripts/adoption_provenance.py)
provides `invoke_recorded(operation, metadata, output_dir,
parent_invocation_id=None)`. It calls a synchronous zero-argument callable exactly
once and preserves the exact return object or original `BaseException`. Nested
synchronous calls inherit a context-local parent identity. Each invocation has
a fresh UUID directory and serves as a unique attempt; retry decisions and
attempt numbering belong to the caller.

With recording enabled, each complete receipt directory contains:

| Artifact | Contents and identity |
| --- | --- |
| `result.json` | Version 1 terminal record with invocation ID, parent ID, status and public JSON result. Failures record only exception class; cancellation has a separate terminal status. |
| `reasoning.jsonl` | Existing canonical logger's start and terminal lifecycle events, sharing invocation/parent identities and metadata/result digests. |
| `provenance.json` | Version 1 identity, terminal status, frozen metadata snapshot and metadata/result/reasoning digests. |

Terminal states are `complete`, `failed`, and `cancelled`. Existing mandatory
logging behavior remains separate from this optional recorder. A sink, metadata
serialization or result serialization failure produces a generic diagnostic,
preserves the operation result or exception, and never repeats the operation.
Incomplete receipt directories remain incomplete and fail offline validation.

Canonical JSON is UTF-8 with sorted string keys, compact separators and
`ensure_ascii=False`; nonfinite numbers and non-JSON Python objects are rejected.
Terminal files have a final newline. Result and metadata hashes cover their
canonical JSON values, while `reasoning_digest` covers exact JSONL bytes and
`source_digest` covers exact metadata-file bytes. The metadata snapshot also
captures its canonical contract digest, capability fields, reasoning mapping and
taxonomy source digests. Hashes establish consistency, not authenticated origin:
someone replacing every related artifact and digest can manufacture a
self-consistent record.

`validate_invocation(directory)` checks the result, metadata and exact log digests
and all cross-view identity, parent, lifecycle and evidence joins. It rejects
incomplete receipts and malformed JSON, including duplicate keys and nonfinite
values. `render_summary(directory)` validates first and returns escaped static
HTML without a model or workflow call. CLI equivalents are controlled
`adoption:receipt-validate` and `adoption:receipt-render`, followed after `--` by
the receipt directory. Rendering emits HTML to stdout and preserves source bytes.

## Limits

The wrapper supports synchronous calls, caller-owned retries, synchronous
nesting, independent concurrent receipt directories and synchronous cancellation
exceptions. It does not await coroutines, wrap asynchronous generators, guarantee
cross-process parent propagation or forcibly cancel external tools. Independent
receipt files do not make arbitrary shared legacy JSONL appends concurrent-safe.
Historical enrichment is a separate projection; historical digest-bound logs
must not be rewritten.

Only public results and the metadata allowlist belong in receipts. The recorder
does not automatically redact arbitrary secrets from allowed strings or result
objects. Callers must select public summaries; hidden reasoning, credentials,
private prompts and raw sensitive payloads must not be supplied. Failure
diagnostics and exception receipts omit exception messages. Schema validation,
fake-handler trace checks and rendering provide no new scientific proof,
source-fidelity guarantee or live-provider evidence.
