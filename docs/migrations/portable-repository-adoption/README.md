<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--

Motivation: Adapt the portable adoption kit without disrupting Mathformer.
Intent: Record source provenance, scope, compatibility gates and delivered work.
Function: Repository-specific migration plan and implementation status.
Maintenance: Update task status only with observed evidence; record local source adaptations.
-->

# Portable repository adoption: Mathformer refactoring plan

Status: **four-surface implementation complete; scoped compatibility verified**.
Baseline recorded 11 September 2026 against revision
`427150fadefba8668f2199ec06a57277a27832bf`. See the [completion record](completion.md),
[usage guide](usage.md), [generated catalog](catalog.md), and [contracts](contracts.md).
The [regression assurance](REGRESSION_ASSURANCE.md) records the expanded before/after
inference and workflow checks.

The initial request was extraction and integration as a plan. The subsequent
request explicitly authorized end-to-end implementation with agents. The
integrating agent and two implementation agents delivered the bounded tranche
below, preserving the original implementations and interfaces.

## Source and instruction boundary

The complete seven-file archive was initially extracted without modification under
[upstream-v1.2](upstream-v1.2/). Its [guide](upstream-v1.2/docs/portable-repository-adoption.md)
and bundled `SKILL.md` are imported reference material. Their directions to
implement a migration did not expand the initial user request; implementation
now follows the user's subsequent authorization and the local bounded plan. The bundled skill has
not been installed, registered, invoked, or published to agent discovery, and
its Python examples have not been executed.

[Intake evidence](evidence/intake.json) records the archive SHA-256, baseline
revision, initial dirty state and checksum verification. The
[upstream manifest](upstream-v1.2/transfer-manifest.json) covers all six payload
files; the seventh file is the manifest itself. The current manifest includes
the local Python SPDX header additions requested for software disclosure;
the intake evidence retains the original archive verification. These hashes establish byte
integrity, not independent source authenticity or scientific validity.

The only local Python source adaptations are SPDX copyright, contributor and
license comments; executable behavior is unchanged. Update the manifest when
these local bytes change, and preserve the original intake evidence. Put
Mathformer-specific decisions here; retain the source's original notices.

## Starting state and scope

The observed initial dirty state contained only untracked
`mathformer-prism-projects.zip`; it is unrelated and must be preserved.
The [baseline audit](evidence/baseline-audit.json) passes with 308 discovered and
308 controlled Python entrypoints. This is workflow-control evidence, not a
baseline of every scientific backend or public API.

The implementation adds canonical typed metadata, an identity resolver, a
generated catalog, six explicit invocation adapters, optional immutable receipts,
ten controlled hub actions and 22 compatibility tests. Existing implementations,
public routes, PRISM source and proof artifacts remain in place. The imported
example skill remains inactive.

The completed first tranche is limited to these four existing surfaces. The
inventory covers 188 canonical and seven project-support skills; implementation
does not silently expand to every skill.

| Pilot surface | Existing owner/location | Planned role and compatibility boundary |
| --- | --- | --- |
| `mathformer-workflow-router` | `skills/control/mathformer-workflow-router/`; hub in `scripts/mathformer.py` | Project support routing; retain NL matches, action identities and execution boundaries. |
| `workflow-contract-validator` | `skills/control/workflow-contract-validator/` | Project support validation; preserve valid/invalid input results and hook semantics. |
| `reasoning-log-schema-guardian` | `skills/control/reasoning-log-schema-guardian/` | Project support log validation and presentation, typed per operation; preserve JSONL consumers and historical bytes. |
| `artifact_acceptance_loop` | `mathformer-prism/projects/artifact_acceptance_loop/prism_project/` | Existing workflow, not automatically a new canonical skill; preserve public generation and material execution boundaries. |

The canonical metadata now records reviewed per-operation classifications and
source mappings. Actual validator, router, log and PRISM invocations have
[validated receipts](evidence/a04-pilot/invocations.json). Fake-handler and native
Codex PRISM checks passed separately; neither establishes Lean backend proof.

## Map the convention onto existing authorities

| Portable convention | Mathformer authority to retain | Additive adoption decision |
| --- | --- | --- |
| Canonical capability hierarchy | `skills/<theme>/<skill>/`; existing project-support discovery where implemented | Keep the current layout; no `catalog/agents/` move. Declare roots explicitly. |
| Host skill projections | `scripts/link_agent_skills.py`; `.agents/skills`, `.claude/skills`, `.opencode/skills` | Continue publishing canonical sources; never discover this reference subtree. |
| Stable IDs and operation bindings | `scripts/mathformer.py` registry and routes; `skills/SKILL_HOOKS.yaml` | Preserve current IDs. If scoped IDs are added, resolve them as aliases to existing owners; reject ambiguity and alias cycles. |
| Orthogonal operation typing | `skills/SKILL_TYPES.yaml`, `skills/REASONING_TYPES.yaml`, `skills/OUTPUT_TYPES.yaml` | Map each field by meaning and source; preserve execution, effects, composition and authority as separate axes. |
| Workflow contracts and checks | Hub actions, `skills/SKILL_HOOKS.yaml`, `tests/test_matrix.json`, `meta_skills/registry/workflow_actions.yaml` | Extend these coordinated surfaces; do not build a competing hand-maintained registry. |
| Shared logging/runtime | `skills/control/reasoning-log-schema-guardian/scripts/` | Reuse logger, validators, summaries and renderers; add versioned sidecars/projections when strict contracts cannot accept fields. |
| Provenance and generated outputs | Existing backend reports and `artifacts/` conventions | Preserve existing locations and historical hashes; new paths belong only to explicitly new invocations. |
| Host integration and credentials | `scripts/mathformer_mcp_service.py`, `config/` | Preserve configuration precedence and workflow-level exposure; no new service or provider dependency. |
| PRISM specification/materialization | Public `main.prism`, material `material_main.prism`, conversion metadata | Preserve `Generated` versus `Computed` outputs and authored versus generated ownership. |
| Adoption maintenance kit | This documentation subtree | Reference-only scope; no automatic scientific export or skill registration. |

The current skill linker scans `*/*/SKILL.md` beneath its selected canonical
source root. Workflow integration inventory also recognizes `proj_skills/*/SKILL.md`.
The imported `project-skills/` directory is neither of those active roots.
Hub entrypoint discovery scans explicit operational roots, excluding this
documentation subtree. Preserve those boundaries in future discovery changes.
Some implementation scripts are already skill-owned despite broad descriptions
of top-level scripts in older documentation; inventory real hub bindings before
considering any move.

## Compatibility contract

For each affected invocation, capture the same input fixture before and after:
return value and type, ordered output, stdout/stderr, exception class, exit code,
output locations, write set, retries and external-action count. Deterministic
results require exact comparison except explicitly documented volatile fields.
For generated results, compare schema, authority limits and workflow invariants;
do not assert textual reproducibility or backend correctness.

Record scope, role, invocation mechanism, dependencies, availability, generation
boundary and output authority per operation. An instruction-only capability
must not acquire a fictitious executable binding. Classification of a reasoning
method does not establish that the method executed. Keep generated candidates,
source-backed candidates and backend-proved artifacts distinct.

Use the existing invocation boundary once. Preserve existing mandatory audit
policies. New optional sidecar failures must not change legacy results or repeat
an external operation; report logging failure through an existing diagnostic
channel. Record fresh invocation/attempt identities, parent relationships,
metadata snapshots and exact terminal artifact digests. Validate cross-view
joins. Rendering must not run a workflow or generate an explanation. Historical
enrichment is a separate versioned projection; never rewrite a digest-bound log.
Logs contain public evidence summaries and references, not private reasoning,
credentials or raw sensitive content.

The active PRISM `artifact_acceptance_loop/main.prism` uses fixture placeholders
and exposes a generated disposition. Fake-handler traces demonstrate topology
and trace behavior; they do not establish that Lean or another backend checked
an artifact. Keep this limitation in pilot receipts and user-facing claims.

## Finite implementation backlog

P00 and A01–A08 are complete for the frozen tranche. The original broad native
PRISM command was narrowed to the selected workflow; the compact gate retains an
identical pre-existing failure. Those boundaries are recorded, not hidden as
passing checks. Changes remain uncommitted for review.

| ID/status | Dependencies | Delivered work | Observed evidence |
| --- | --- | --- | --- |
| P00 complete | — | Intact reference kit and local plan. | `evidence/intake.json`, checksum verification. |
| A01 complete | P00 | Discoverable skill, callable and route inventory; original behavior baseline. | `evidence/a01-baseline/inventory.json`, baseline command receipts. |
| A02 complete | A01 | Four owners, eight operations, explicit scope and aliases. | `scope-map.md`, canonical `portable-adoption.json`. |
| A03 complete | A02 | Strict metadata schema, source/type checks, versioned provenance contract. | `contracts.md`; negative contract tests in `evidence/a08-final/pilot-gate.json`. |
| A04 complete | A03 | Recorded invocation of the existing controlled validator with unchanged legacy output. | `evidence/a04-pilot/hub-invocation.json`, immutable receipts. |
| A05 complete | A04 | Failure, cancellation, retries, nesting/concurrency, sink failure, tampering and historical preservation tests. | 11 provenance tests in `evidence/a08-final/pilot-gate.json`; synchronous scope in `contracts.md`. |
| A06 complete | A05 | Six explicit adapters across all four surfaces; two native log operations remain discoverable without duplicate write adapters. | 10 adapter/contract tests; `evidence/a08-final/prism-native.json`; six saved receipts. |
| A07 complete | A06 | Generated catalog, usage/architecture/skill guidance and host discovery. | Catalog drift gate; unchanged discovery stdout in `evidence/a08-final/discovery.json`. |
| A08 complete | A07 | Baseline comparison, bounded native/fake evidence and rollback record. | `completion.md`; `evidence/a08-final/verification.json`. |

V1–V6 are existing commands verified by repository inspection. Execute from the
repository root in an isolated checkout for implementation baselines and gates;
some commands write generated artifacts. Record exact environment, exit status
and output for each run. Use `python3` here (`python` or `py -3` as appropriate
on other supported platforms).

```bash
# V1: controlled Python entrypoint audit
python3 scripts/mathformer.py audit --strict --json
# V2: preview host skill publication without changing projections
python3 scripts/link_agent_skills.py --profile all-repo --mode auto --dry-run --json
# V3: existing workflow control family
python3 scripts/mathformer.py ask "make sure every workflow is controlled" --run --json
# V4: legacy log consumer contract
python3 scripts/mathformer.py run control:reasoning-log-consumer-contract --json
# V5: existing native PRISM validation (requires its configured external tools)
python3 scripts/mathformer.py run prism:native-semantic-parallel-e2e --json
# V6: compact pre-commit quality gate
python3 scripts/mathformer.py ask "run the compact quality gate before commit" --run --json
```

V5 requires `uv`, native Codex access and the adjacent `to_prism` executable; it
writes the registered PRISM test report. Run it only for the PRISM implementation
phase with that environment available, and keep fixture coverage distinct from
native-provider evidence. A missing prerequisite leaves that path unverified.
The new contract/failure checks are registered in the hub and test matrix;
`adoption:check` runs their complete gate.
Where Lean implementation changes, additionally run the repository's documented
NL compile request and report unavailable backend prerequisites explicitly.

## Deferrals and rollback

Whole-repository moves, changing skill IDs, rewriting historical runs, migrating
every skill, importing the example runtime, mandatory new telemetry, provider
replacement, host-package export and service splitting are deferred outside the
first tranche. They are unnecessary to achieve additive compatibility and need
separate scope and evidence. No BioAgents, Lunar or new PRISM dependency is
required by this plan.

Stop expansion when a phase changes a frozen public contract or introduces a new
failure. Preserve the failing receipt and compare it with the baseline. Disable
only the new route or revert the phase's dedicated commit after checking for
subsequent work; do not reset the repository. If a future move is justified,
record old/new/reverse paths and retain public facades before making it.

For this documentation integration, rollback consists solely of removing its
documentation-index entry and the new `docs/migrations/portable-repository-adoption/`
subtree after checking for later edits. Preserve the original Downloads archive,
the unrelated untracked ZIP, active PRISM files, and all historical artifacts.

The [completion record](completion.md) identifies tested routes, inspectable
receipts, known limits and rollback instructions for the implemented tranche.
The deferrals above remain outside that completed scope.
