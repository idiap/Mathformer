<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Plan a systematic control workflow for keeping MathformerPhysicsLib coherent,
  integrated, maximally grounded in Mathlib, and free of repeated local concept
  redefinitions.

Intent:
  Define the skills, generative critics, hooks, artifacts, gates, and TODOs
  needed before MathformerPhysicsLib can be treated as a reusable physics
  foundations library rather than a collection of isolated case artifacts.

Function:
  Serves as the design and implementation backlog for MathformerPhysicsLib
  coherence and grounding audits.

Maintenance Notes:
  Keep this plan synchronized with `MATHFORMERPHYSICSLIB_FOUNDATIONS_WORKFLOW.md`,
  `skills/SKILL_HOOKS.yaml`, the hub registry, and MathformerPhysicsLib manifests.
-->

# MathformerPhysicsLib Coherence And Grounding Workflow

## Goal

Build a controlled workflow that answers this question:

> Is MathformerPhysicsLib coherent, integrated, maximally grounded on Mathlib,
> and free of scattered concept redefinitions?

The workflow must be library-level, not case-level. A single physics artifact
can compile while the library as a whole still fails because vectors, operators,
laws, units, frames, or assumptions are repeatedly redefined in incompatible
ways. This workflow treats that fragmentation as a first-class failure mode.

## Desirable Properties

Each MathformerPhysicsLib run should establish these properties:

| ID | Property | Failure mode |
| --- | --- | --- |
| P1 | Canonical ownership: every recurring physics concept has one owner module or one explicit blocker. | Same object appears under several names and modules. |
| P2 | Maximal Mathlib grounding: Mathlib carriers, operators, predicates, and theorems are reused before local surfaces. | Local wrappers duplicate `EuclideanSpace`, `LinearMap`, calculus, algebra, or matrix APIs. |
| P3 | No silent redefinition: local declarations do not shadow or restate existing Mathlib or accepted MathformerPhysicsLib objects. | A new `VectorField`, `Operator`, or `Law` is introduced for every case. |
| P4 | Integration: accepted modules are reachable through manifests, registry, docs, index imports, and object-workbench lookup. | Support exists but target workflows cannot discover it. |
| P5 | Stable abstraction boundaries: genuinely missing physics notions are named once and documented as bridges or blockers. | Broad opaque structures hide missing formal content. |
| P6 | API operability: foundations expose lemmas/projections usable by downstream theorems. | A type exists but no theorem can use it. |
| P7 | Physics semantic preservation: grounding does not erase vectors, units, regimes, frames, or laws into raw scalar algebra. | Mathlib reuse is technically valid but physically too weak. |
| P8 | Source and support labels: every assumption is source-backed, Mathlib-backed, generated-support, or blocked. | Assumptions appear without provenance. |
| P9 | Monotonic repair: proposed repairs reduce duplicate concepts and unresolved blockers without reducing verified Mathlib grounding. | A repair compiles by adding more local abstractions. |
| P10 | Evidence completeness: every acceptance claim has a machine-readable report. | Completion is asserted in prose only. |

## Canonical Artifacts

The workflow should produce:

```text
artifacts/mathformerphysicslib/coherence/inventory.json
artifacts/mathformerphysicslib/coherence/concept_graph.json
artifacts/mathformerphysicslib/coherence/mathlib_grounding.json
artifacts/mathformerphysicslib/coherence/redefinition_report.json
artifacts/mathformerphysicslib/coherence/integration_report.json
artifacts/mathformerphysicslib/coherence/generative_critic_plan.json
artifacts/mathformerphysicslib/coherence/generative_critic_report.json
artifacts/mathformerphysicslib/coherence/repair_plan.json
artifacts/mathformerphysicslib/coherence/coherence_gate.json
artifacts/mathformerphysicslib/coherence/coherence_report.md
```

The report must identify accepted support, duplicate support, missing support,
thin wrappers, blocked concepts, and candidate repairs.

## Planned Skills

### `mathformerphysicslib-coherence-inventory-builder`

Purpose: Build a normalized inventory of all MathformerPhysicsLib Lean modules,
declarations, imports, comments, manifests, registry entries, consistency
reports, and object-workbench hits.

Inputs:

- `libraries/MathformerPhysicsLib/Lean/**/*.lean`
- `libraries/MathformerPhysicsLib/MANIFEST.json`
- `libraries/MathformerPhysicsLib/MATHLIB_GROUNDING_AUDIT.json`
- `artifacts/mathformerphysicslib/foundations/**`

Outputs:

- `mathformerphysicslib_inventory`
- `concept_occurrence_index`
- `module_import_index`

Key checks:

- every accepted module is reachable from an index or manifest;
- every declaration has a concept label or is ignored with a reason;
- every recurring label has an owner candidate.

### `mathformerphysicslib-concept-canonicalizer`

Purpose: Turn repeated concept occurrences into canonical concept records.

Inputs:

- inventory output;
- detector object classes;
- Mathlib concept ontology hints;
- existing foundation backlog.

Outputs:

- `mathformerphysicslib_concept_graph`
- canonical concept IDs such as `vector_field.real.euclidean3`,
  `linear_operator.field`, `unit_dimension.compatible`, and
  `physical_law.witness`.

Key checks:

- aliases point to one canonical concept;
- case-local concepts are distinguished from reusable concepts;
- ambiguous concepts become blockers, not silent merges.

### `mathformerphysicslib-mathlib-grounding-auditor`

Purpose: Score each canonical concept against verified Mathlib grounding.

Inputs:

- concept graph;
- `mathlib-concept-candidate-mapper` output;
- `mathlib-candidate-verifier` output;
- `mathlib-import-set-builder` output;
- `mathlib-grounding-maximizer` output.

Outputs:

- `mathformerphysicslib_mathlib_grounding_report`
- grounding levels: `direct_mathlib`, `mathlib_bridge`, `local_blocker`,
  `unverified_local`, `out_of_scope`.

Key checks:

- no local object is accepted when a verified Mathlib object suffices;
- broad `import Mathlib` is either minimized or justified;
- grounding scores are nondecreasing across repairs.

### `mathformerphysicslib-redefinition-critic`

Purpose: Detect concept spread, duplicate local wrappers, near-synonym surfaces,
and case-local redeclarations of accepted foundations.

Inputs:

- concept graph;
- Lean declarations and comments;
- Mathlib grounding report.

Outputs:

- `mathformerphysicslib_redefinition_report`
- severity-ranked findings.

Critic questions:

- Is this declaration merely renaming a Mathlib object?
- Is the same physics concept defined in another MathformerPhysicsLib module?
- Does this wrapper add a useful theorem/API or only a new name?
- Could downstream cases import an existing foundation instead?

### `mathformerphysicslib-integration-critic`

Purpose: Ensure accepted support is actually integrated into the library and
discoverable by workflows.

Inputs:

- manifests;
- index imports;
- docs;
- object-workbench plans;
- foundation reports.

Outputs:

- `mathformerphysicslib_integration_report`
- missing manifest/index/doc/workbench links.

Critic questions:

- Is every accepted module reachable from `Foundations.lean`, a manifest, or a
  documented import path?
- Does the object workbench return `mathformer_reused` for promoted support?
- Do downstream cases import accepted support rather than duplicating it?
- Are generated artifacts and accepted support separated?

### `mathformerphysicslib-api-operability-critic`

Purpose: Check that foundations expose usable theorem-facing APIs, not just
opaque structures.

Outputs:

- `mathformerphysicslib_api_operability_report`
- examples of downstream usage or explicit missing-API blockers.

Critic questions:

- Can a target theorem project components, apply operators, or use law
  witnesses without unfolding private implementation details?
- Are bridge lemmas narrower than final target theorems?
- Are assumptions composable across cases?

### `mathformerphysicslib-generative-coherence-critic`

Purpose: Run an adversarial generative panel over the deterministic reports.
This is the main generative skill for the workflow.

Inputs:

- inventory;
- concept graph;
- grounding report;
- redefinition report;
- integration report;
- API operability report;
- selected Lean snippets.

Outputs:

- `mathformerphysicslib_generative_critic_plan`
- `mathformerphysicslib_generative_critic_report`

Generative critic panel:

1. **Mathlib maximality critic**: find places where the library could use a
   stronger Mathlib-native surface.
2. **Redefinition critic**: search for concepts spread across modules under
   different names.
3. **Integration critic**: find accepted concepts missing from index, manifest,
   docs, registry, workbench, or downstream imports.
4. **Physics semantics critic**: detect scalar erasure, missing units, missing
   frames, missing laws, and over-general assumptions.
5. **API usefulness critic**: ask whether a downstream theorem can actually use
   the foundation.
6. **Negative-control critic**: intentionally tries to produce a compiling but
   incoherent repair and records the gate that should reject it.
7. **Meta-critic**: checks whether the previous critics disagree, overreach, or
   lack evidence.

Generative outputs are advisory. They become blockers only after deterministic
evidence is attached: a duplicate declaration, missing import/index path, failed
Mathlib candidate check, failed downstream usage probe, or verified semantic
erasure.

### `mathformerphysicslib-coherence-repair-planner`

Purpose: Convert deterministic and generative critic reports into a monotonic
repair plan.

Outputs:

- `mathformerphysicslib_coherence_repair_plan`
- ordered repairs grouped by:
  - reuse Mathlib directly;
  - promote existing local support;
  - consolidate duplicate local definitions;
  - add bridge theorem/API;
  - update manifest/index/docs/workbench;
  - block a concept with explicit reason.

Gate:

- a repair plan must reduce either duplicate count, missing integration count,
  ungrounded concept count, or unresolved blocker count without reducing verified
  Mathlib grounding.

### `mathformerphysicslib-coherence-gate`

Purpose: Aggregate reports into a library-level status.

Statuses:

- `complete`: all P1-P10 pass;
- `complete_with_blockers`: blockers are explicit and not hidden by target
  theorems;
- `needs_repair`: deterministic findings remain;
- `needs_generative_review`: deterministic reports disagree or are incomplete;
- `failed`: accepted support contains placeholders, duplicate abstractions, or
  hidden semantic erasure.

## Planned Hooks

Add these hooks to `skills/SKILL_HOOKS.yaml` once scripts exist:

| Hook ID | Owner skill | Trigger | Gate |
| --- | --- | --- | --- |
| `library.physics.coherence.inventory` | `mathformerphysicslib-coherence-inventory-builder` | after MathformerPhysicsLib files, manifests, reports, or foundations change | inventory must cover every accepted Lean module |
| `library.physics.coherence.canonicalize` | `mathformerphysicslib-concept-canonicalizer` | after inventory | every recurring concept has one canonical ID or blocker |
| `library.physics.coherence.mathlib_grounding` | `mathformerphysicslib-mathlib-grounding-auditor` | after concept graph | accepted concepts must be Mathlib-direct, bridge-justified, or blocked |
| `library.physics.coherence.redefinition_critic` | `mathformerphysicslib-redefinition-critic` | after grounding report | no high-severity duplicate local definitions |
| `library.physics.coherence.integration_critic` | `mathformerphysicslib-integration-critic` | after registry/docs/index/workbench changes | accepted support must be reachable by manifest, index, docs, and workbench |
| `library.physics.coherence.api_critic` | `mathformerphysicslib-api-operability-critic` | before promotion or downstream reuse | accepted foundations need usable downstream APIs or blockers |
| `library.physics.coherence.generative_critic` | `mathformerphysicslib-generative-coherence-critic` | near-final, disagreement, or high-risk repair | generative findings need deterministic evidence before blocking |
| `library.physics.coherence.repair_plan` | `mathformerphysicslib-coherence-repair-planner` | after any failed critic | repairs must be monotonic and library-first |
| `library.physics.coherence.gate` | `mathformerphysicslib-coherence-gate` | before reporting library complete | P1-P10 are complete, explicit blockers, or failed |

Named loop:

```yaml
mathformerphysicslib_coherence_grounding_loop:
  required_hooks:
    - library.physics.coherence.inventory
    - library.physics.coherence.canonicalize
    - library.physics.coherence.mathlib_grounding
    - library.physics.coherence.redefinition_critic
    - library.physics.coherence.integration_critic
    - library.physics.coherence.api_critic
    - library.physics.coherence.generative_critic
    - library.physics.coherence.repair_plan
    - library.physics.coherence.gate
```

## Hub Routes

Planned controlled hub actions:

- `physics-lib:coherence-inventory`
- `physics-lib:concept-canonicalize`
- `physics-lib:mathlib-grounding-audit`
- `physics-lib:redefinition-critic`
- `physics-lib:integration-critic`
- `physics-lib:api-operability-critic`
- `physics-lib:generative-coherence-critic`
- `physics-lib:coherence-repair-plan`
- `physics-lib:coherence-gate`
- `physics-lib:coherence-loop`

Natural-language route:

> Check whether MathformerPhysicsLib is coherent, integrated, maximally grounded
> on Mathlib, and not redefining concepts across modules.

## TODOs

Implementation evidence, 2026-07-08:

- Controlled route: `mathformerphysicslib.coherence`.
- Hub actions: `physics-lib:coherence-suite` and
  `physics-lib:coherence-loop-report`.
- Current report: `artifacts/mathformerphysicslib/coherence/coherence_report.md`.
- Current gate status: `complete_with_blockers`; recursive repair work is now
  driven by the generated repair plan rather than this implementation checklist.

### Phase 1: Deterministic Inventory

- [x] Create `mathformerphysicslib-coherence-inventory-builder` skill.
- [x] Implement inventory script over Lean files, manifests, docs, reports, and
  object-workbench outputs.
- [x] Emit concept occurrence, import, module, and manifest indexes.
- [x] Add self-test fixture with two modules sharing one concept label.

### Phase 2: Canonical Concept Graph

- [x] Create `mathformerphysicslib-concept-canonicalizer` skill.
- [x] Normalize recurring physics concepts into stable IDs.
- [x] Add ambiguity blockers for concepts that cannot be safely merged.
- [x] Link concept IDs to foundation backlog IDs.

### Phase 3: Mathlib Grounding Audit

- [x] Create `mathformerphysicslib-mathlib-grounding-auditor` skill.
- [x] Reuse existing Mathlib mapping, verification, import planning, and
  grounding maximization scripts.
- [x] Record failed Mathlib candidates to avoid repeated searches.
- [x] Add monotonic grounding comparison across runs.

### Phase 4: Redefinition And Spread Critics

- [x] Create `mathformerphysicslib-redefinition-critic` skill.
- [x] Flag local wrappers that duplicate Mathlib or accepted foundations.
- [x] Detect concept spread by name, comments, Mathlib targets, and downstream
  roles.
- [x] Add severity rules for duplicate carriers, duplicate operators, duplicate
  law witnesses, and duplicate unit/dimension surfaces.

### Phase 5: Integration Critics

- [x] Create `mathformerphysicslib-integration-critic` skill.
- [x] Check `Foundations.lean`, manifests, docs, object-workbench lookup, and
  downstream imports.
- [x] Add missing-link blockers for accepted support that workflows cannot find.
- [x] Add stale-generated-artifact detection so draft support is not treated as
  accepted.

### Phase 6: API Operability Critics

- [x] Create `mathformerphysicslib-api-operability-critic` skill.
- [x] Require at least one downstream usage pattern or explicit missing-API
  blocker for accepted foundations.
- [x] Detect opaque structures with no usable projections or bridge lemmas.
- [x] Add negative fixtures where a type exists but cannot support a theorem.

### Phase 7: Generative Critic Panel

- [x] Create `mathformerphysicslib-generative-coherence-critic` skill.
- [x] Build a Codex-exec prompt plan for maximality, redefinition,
  integration, semantics, API usefulness, negative control, and meta-critique.
- [x] Require deterministic evidence before a generative finding blocks status.
- [x] Add disagreement handling when critics conflict.

### Phase 8: Repair Planning And Gate

- [x] Create `mathformerphysicslib-coherence-repair-planner` skill.
- [x] Create `mathformerphysicslib-coherence-gate` skill.
- [x] Emit monotonic repairs that reduce duplicate, missing integration,
  ungrounded, or unresolved blocker counts.
- [x] Block repairs that compile only by adding new ungrounded abstractions.

### Phase 9: Hooks, Hub, And Tests

- [x] Add planned hooks to `skills/SKILL_HOOKS.yaml`.
- [x] Add `mathformerphysicslib_coherence_grounding_loop`.
- [x] Add hub actions and a natural-language route.
- [x] Add `tests/physics_lean/run_mathformerphysicslib_coherence_loop.py`.
- [x] Add test-matrix entries under `physics_lean` and control checks.

### Phase 10: First Controlled Run

- [x] Run the coherence loop over existing Lean top-10 cases.
- [x] Generate `coherence_report.md`.
- [x] Convert high-severity findings into foundation or repair-loop TODOs.
- [x] Require the report before declaring MathformerPhysicsLib complete.
