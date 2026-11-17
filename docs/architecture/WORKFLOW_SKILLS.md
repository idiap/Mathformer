<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileCopyrightText: 2026 Idiap Research Institute
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Normalized workflow skills

Mathformer's canonical operational and reasoning registries have a generated
`workflow-skill/v1` description layer. The
[catalog](../../skills/control/workflow-contract-validator/references/normalized-workflows/catalog.json)
records explicit canonical IDs, legacy aliases, owning skills, source selectors,
source digests, descriptor locations and coverage. The
[shared schema](../../skills/control/workflow-contract-validator/references/workflow.schema.json)
and [format semantics](../../skills/control/workflow-contract-validator/references/workflow-skill-format.md)
are tracked with the existing workflow contract validator, so validation does
not depend on an ignored `.codex` directory or a neighboring checkout.

The current inventory contains **318 descriptors**:

| Canonical source | Count | Source-to-step mapping | Coverage |
| --- | ---: | --- | --- |
| `scripts/mathformer.py:build_registry` | 225 | `flow.steps.invoke` binds the unchanged native hub action; exact commands, ordered dependencies, safety, write roots, prerequisites and tool declarations remain in `mathformer.source` and `mathformer.composition`. | Native interface only |
| `scripts/mathformer.py:build_intent_routes` | 70 | `flow.steps.invoke` identifies the already selected native route; its exact action order and related skills remain in the source extension. | Native interface only |
| `skills/SKILL_HOOKS.yaml:loop_contracts` | 14 | `flow.realize_contract` remains specification-only; required/recommended hooks, triggers, owners, gates, output names and runtime accounting are retained as contract data. | Partial; no invented executable schedule |
| `skills/REASONING_TYPES.yaml:reasoning_styles` and `examples/reasoning_flows/*.rflow` | 9 | `flow.realize_contract` remains specification-only; the complete ERFL program, stages, candidate skill materializations and trust boundaries remain source data. | Partial; epistemic profiles are not operational schedules |

Counts include the normalization validation, regeneration and test actions added
with this layer. Ordinary atomic skills remain skills. Generated PRISM exports,
reports, plugin mirrors and explanatory workflow graphs are not substituted for
canonical workflow sources. Skill references within a source contract are
retained without inventing a separate independently callable workflow for each
referenced skill.

## Identity and discovery

All canonical IDs end in `_workflow` and declare `kind: workflow`. Category
prefixes distinguish `hub_`, `route_`, `loop_` and `profile_` identities. The
catalog materializes an explicit alias map and generation rejects collisions;
consumers resolve that map before applying the suffix convention. Existing
hyphenated skill directories, hub action IDs, route IDs and native loop IDs keep
their names. Each catalog entry links its owning `SKILL.md`; loop participants
and route-related skills remain in the exact source contract.

Descriptors live beneath the existing workflow-contract-validator references
directory. They are deterministic projections: edit the native registries and
implementations, then regenerate. Do not maintain their definitions separately.
Source SHA-256 digests cover complete files, so an unrelated edit to a source
module can legitimately require regeneration.

## Type and execution boundaries

The [hub interface schema](../../skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json)
formalizes the existing `RunContext`, `action_to_dict` and `run_action` /
`run_leaf_action` / `run_intent_match` result envelopes. It admits native preflight
failures, dry runs, dependency failures and child aggregation. It does not type
the scientific content embedded in subprocess stdout or replace backend artifact
schemas. Pass-through arguments appear only where the native action admits
them; sequence extra-argument rejection remains native.

Opaque native calls deliberately retain `interface_only` coverage. They preserve
existing keep-going behavior, child failure aggregation, command execution,
mutation preflight and write auditing inside the controller. Dependency metadata
is not a second execution sequence. MCP dispatches canonical hub/route IDs through
those native controls. No general workflow-skill DAG interpreter is supplied,
and native dispatch does not qualify every v1 runtime policy or scientific result.

All descriptors retain draft lifecycle and explicit gaps. The source does not
provide uniform global budgets, complete network/external-effect declarations,
mandatory receipts, or typed scientific payload ports. Normalization bounds and
qualification capability labels do not authorize runtime capabilities. For hook
loops, required membership does not imply temporal order; for ERFL profiles,
semantic dependency does not imply scheduling. Future executable adoption must
establish those contracts, independently qualify adapters, and preserve native
backend, source-fidelity, provenance, promotion and approval gates.

## Validate and regenerate

Use the repository Python environment with PyYAML and jsonschema installed:

```bash
python scripts/mathformer.py ask "validate normalized workflows" --run --json
python scripts/mathformer.py run control:normalized-workflows-tests --json
```

Regenerate the descriptions after changing canonical definitions:

```bash
python scripts/mathformer.py run control:normalize-workflows --allow-mutating --json
```

These commands operate on definitions and temporary test fixtures. They do not
run scientific workflows or regenerate proof/report artifacts. The regeneration
command writes only the normalized-workflows directory and refuses source drift
through subsequent validation. Unexpected stale descriptors are reported rather
than deleted automatically.

The check verifies exact canonical inventory coverage, deterministic generated
content, dependency references/cycles, aliases, schema/dataflow contracts, local
payload schemas and source file digests. The adversarial suite additionally
rejects stale output, forged source digests, invalid type/forward references and
duplicate YAML keys. It tests real hub dry-run/preflight envelopes and uses
stubbed child results to exercise keep-going behavior without backend execution.

Schema validity, source projection coverage, native runtime availability,
scientific validation and human approval remain separate results.

## Codex, Claude and MCP discovery

Both plugin manifests discover a flat entrypoint for every normalized workflow
alongside the existing canonical skills. The plugin
`workflow-catalog.json` maps canonical `_workflow` IDs to client-compatible
hyphenated names (long names have a stable hash suffix). Each entry contains
`SKILL.md` and the complete `workflow.yaml`; shared schemas are packaged locally.
The cached plugin can inspect and type-check contracts without a checkout;
native execution still uses the explicitly located Mathformer checkout.

MCP offers `mathformer_list_workflows`, `mathformer_show_workflow`, and
`mathformer_run_workflow`. List results are paginated and can be filtered by
category or text. Inspection accepts canonical IDs and explicit aliases. Native
hub/route dispatch preserves mutation preflight, service read-only policy,
write-root restrictions and timeout caps. Loop/profile execution returns
`specification_only`. Resources expose `mathformer://workflows`,
`mathformer://workflows/{workflow_id}` and `mathformer://workflow-schema`.

After regeneration, synchronize plugin copies with
`python scripts/sync_agent_plugins.py`; its `--check` mode rejects drift.
Reload installed/cached plugins and restart existing MCP processes to pick up
changed server code. Repository generation does not alter client settings.
