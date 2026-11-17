<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--

Motivation: Freeze additive adoption ownership and compatibility scope.
Intent: Describe the exact existing surfaces represented by local metadata.
Function: A02 operation map and A01 inventory interpretation.
Maintenance: Keep operation IDs synchronized with canonical metadata.
-->

# Frozen portable-adoption scope

The tranche contains three existing control skills and one existing PRISM
workflow. The [inventory](evidence/a01-baseline/inventory.json) records 188
canonical skills and seven project-support skills, including each manifest's
digest, declared Python callables and referring hub actions. Discovery remains
`skills/*/*/SKILL.md` and `proj_skills/*/SKILL.md`; imported documentation and host
projections are not additional canonical roots. Inventory establishes declared
interfaces, not execution coverage. Gate receipts are separate evidence.

Canonical operation metadata lives in
[portable-adoption.json](../../../skills/control/workflow-contract-validator/references/portable-adoption.json).
The existing hub remains authoritative for action execution and safety. Scoped
aliases resolve to the IDs below; they do not replace old IDs or create a second
implementation. Alias resolution must reject duplicates, cycles and unresolved
targets. PRISM bindings identify typed entrypoints, not dynamically callable
Python functions.

| Surface and owner | Operation ID | Existing binding and role | Compatibility boundary |
| --- | --- | --- | --- |
| `mathformer-workflow-router`, `skills/control/mathformer-workflow-router/` | `router:resolve` | `scripts/mathformer.py::resolve_intent`; reader/branching router | Preserve ordered `List[IntentMatch]`, empty matches, request scoring and family filtering; execution still passes through the hub. |
| `workflow-contract-validator`, `skills/control/workflow-contract-validator/` | `control:workflow-contract` | Existing hub action to `scripts/validate_skill_hooks.py::main` under this owner; reasoner/validator | Preserve JSON report fields, stdout, strict invalid exit 3, valid exit 0, and existing hooks. |
| `reasoning-log-schema-guardian`, `skills/control/reasoning-log-schema-guardian/` | `control:reasoning-log-summary` | Existing hub action to `scripts/summarize_reasoning_log.py::main`; reader | Preserve consumer schema version 1, ordered timeline, validation and quality fields. |
| Same log owner | `control:reasoning-log-html` | Existing hub action to `scripts/render_reasoning_log_html.py::main`; writer | Preserve selected output path and input JSONL bytes; rendering does not execute a workflow. |
| Same log owner | `reasoning-log:validate` | `scripts/validate_reasoning_log.py::validate_reasoning_log`; reasoner/validator | Preserve strict and instrumentation options, findings and malformed-input behavior. |
| Same log owner | `reasoning-log:append` | `scripts/reasoning_log.py::append_reasoning_log_entry`; writer | Preserve canonical append helper, public payload contract, returned `Path`, and legacy mandatory logging policy. |
| `artifact_acceptance_loop`, `mathformer-prism/projects/artifact_acceptance_loop/prism_project/` | `artifact_acceptance_loop:public` | `main.prism::main`; reasoner | Preserve `Result[Generated[ArtifactDisposition], ModelFailure]`, `AI.Generate` and `Context.Disclose` effects and fixture inputs. |
| Same PRISM owner | `artifact_acceptance_loop:material` | `material_main.prism::main`; reasoner | Preserve `Computed[LeanArtifactAcceptanceDecision]` and fixed structural material records, including `not_executed_by_structural_fixture`. |

Every script path in the table is relative to its stated skill owner unless
explicitly rooted at `scripts/mathformer.py`. Metadata contains full
repository-relative binding paths and exact aliases. Python callables remain
native APIs; registration does not promise a universal argument-marshalling
adapter. HTML rendering and appending retain their native interfaces.

## Sources and independent classifications

`skills/SKILL_TYPES.yaml` supplies execution posture, specification style,
composition role, effects and authority vocabulary. `skills/REASONING_TYPES.yaml`
explicitly assigns `epistemic_governance` as primary to all three selected skills;
per-operation metadata records that declared source and its mapping basis. The
PRISM governance classification is an operation-level interpretation of its
authored contract, not an invented canonical skill assignment.
`skills/OUTPUT_TYPES.yaml` supplies output semantics. Role (`reader`, `reasoner`,
`writer`), invocation mechanism, generation boundary and output authority remain
separate fields. No classification proves that reasoning or a backend ran.

The material fixture's deterministic label follows inspected bindings in
`materialization.prism`: they construct fixed typed records and call `compute`.
It is not inferred from the `Computed` wrapper. Those bindings explicitly report
that linked native implementations did not execute and carry empty evidence
references. The public entrypoint instead exposes an explicit generated result.
`runtime.json` selects the fake handler. Fixture traces can therefore establish
topology and output shape only; they do not establish Lean compilation, proof,
source fidelity, nonvacuity or real artifact acceptance.

## Consumers, dependencies and preservation

All three skills depend on the current hooks and skill directories. The router
depends on the existing hub registry and intent routes; log validation and
summarization depend on existing JSONL schema, instrumentation and hook checks.
The guardian owns shared logger, schema validator, Markdown/HTML renderers and
consumer summary implementations. Optional provenance belongs in a versioned
sidecar or projection, preserving historical JSONL bytes and existing consumers.

PRISM conversion metadata remains under the existing sibling `conversion/`
directory. `generated/` artifacts retain their current ownership; this migration
does not regenerate them. Required hooks and skill dependencies for the
acceptance workflow remain defined by `skills/SKILL_HOOKS.yaml`'s
`artifact_acceptance_loop` entry. New fixture adapters must use the existing
runtime and state their handler explicitly. Live provider/backend checks require
their own evidence and available prerequisites.

No source move or public API removal is needed. Rollback removes the additive
metadata, adapter exposure and generated documentation after checking dependents;
existing entrypoints, IDs, proofs, logs and authored PRISM sources stay usable.
