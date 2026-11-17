<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Convert the extracted Looper project into a deep but controlled Mathformer
  integration plan.

Intent:
  Define what Mathformer should import conceptually, what it should not import,
  which local surfaces should own the work, and which TODOs prove progress.

Function:
  Serves as the architectural bridge from Looper's long-horizon agentic loop to
  Mathformer's autoformalization, physics, Mathlib, MCP, and skill-control
  workflows.

Maintenance Notes:
  Keep phase names and validation commands synchronized with
  `todos/looper_integration_todos.yaml` as implementation proceeds.
-->

# Looper To Mathformer Meta-Skills Integration Plan

## Executive Decision

Integrate Looper as a Mathformer meta-skill governance layer, not as a second
runtime.

Mathformer already owns execution through:

- `scripts/mathformer.py` natural-language routing and controlled actions,
- `skills/SKILL_HOOKS.yaml` workflow contracts,
- `tests/test_program/run_comprehensive_tests.py` module families,
- repo-local skill exposure to Codex, Claude, and OpenCode,
- the independent MCP service deployment plan.

Looper contributes a missing layer above those mechanisms:

- workflow-visible task registries,
- skill quality cards,
- generated skill lifecycle control,
- runtime skill-application traces,
- workflow evolution state graphs,
- taxonomy-first skill and workflow navigation,
- evidence-backed promotion, quarantine, and rollback decisions.

## Deep Fit With Mathformer

Mathformer has a dense set of skills and controlled workflows. The pressure now
is not only "can this script run?", but "can the system explain, govern, and
evolve its own skill/workflow surface without losing formalization rigor?"

Looper is valuable because it treats agentic development itself as an artifact
domain. That matches Mathformer in five places:

1.  Autoformalization workflows are long horizon.
    A single paper, textbook chapter, or physics derivation may pass through
    extraction, expansion, grounding, drafting, execution, critique, repair,
    promotion, and documentation.

2.  Mathformer already uses explicit skills.
    Looper's quality cards and reasoning logs can strengthen the difference
    between deterministic skill contracts and generative interpretation.

3.  Mathformer now has many workflow families.
    Looper's task registry can make workflows the visible user-facing unit,
    with skills and hooks underneath.

4.  Mathformer generates new support surfaces.
    Looper's generated-skill lifecycle can prevent task-local generated skills,
    repair plans, or foundation drafts from being promoted prematurely.

5.  Mathformer has an MCP service boundary.
    Looper's "workflow-level action hub before MCP" lesson fits the existing
    Mathformer service plan and avoids per-skill MCP sprawl.

## What To Import Conceptually

### 1. Workflow-Visible Task Registry

Add a `meta_skills/registry/tasks/<task_id>/task_registry.json` contract for
high-value workflows. The first Mathformer task registries should cover:

- `mathformerphysicslib-foundations-workflow`,
- `mathformerphysicslib-coherence-grounding-loop`,
- `lean-physics-recursive-repair-loop`,
- `textbook-theory-autoformalization-loop`,
- `mcp-independent-service-deployment`.

Each registry entry should name visible workflows, composed skills, controlled
hub actions, artifacts, validators, generated local skills or support modules,
and release boundaries.

### 2. Skill Quality Cards

Add skill quality cards for meta-level and high-risk generated skills. A card
should state:

- deterministic boundary,
- generative boundary,
- epistemic risks,
- necessary conditions,
- sufficiency claim,
- representation contract,
- validation oracles,
- failure modes,
- promotion gate.

Mathformer already has tests and hook contracts. Quality cards make the
epistemic contract explicit at the skill level.

### 3. Generated Skill Lifecycle

Adopt Looper's lifecycle for generated task-local skills and support surfaces:

`draft -> task-local validated -> repeated-use candidate -> promoted -> deprecated/quarantined`

For Mathformer, "generated skill" includes:

- generated task-local agent skills,
- generated physics or math workflow support skills,
- generated MathformerPhysicsLib foundation surfaces,
- generated repair-loop probes,
- generated MCP workflow adapters.

No generated skill or support surface should be promoted only because one
workflow run passed.

### 4. Runtime Skill-Application Trace

Mathformer has reasoning-log tooling, but Looper's runtime skill-application
trace is a stronger integration object. Add a normalized trace schema under
`meta_skills/runtime/` or equivalent:

- skill application start,
- context loaded,
- input normalized,
- action taken,
- evidence recorded,
- gate evaluated,
- completion or error.

These traces should feed RFDE, skill tests, and workflow-evolution reports.

### 5. Workflow Evolution State Graph

For long workflows, add a `workflow_evolution.json` artifact that materializes
states, transitions, reflective questions, gates, and next deltas. This should
be used for recursive physics repair, MathformerPhysicsLib foundations, and
textbook autoformalization.

### 6. Taxonomy-First Navigation

Looper avoids broad search over skill prose by assigning workflows and skills
to taxonomy coordinates. Mathformer can reuse this idea with:

- reasoning types,
- backend families,
- object domains,
- formal system targets,
- safety/risk classes,
- artifact states.

The immediate target is a meta-skill router that can answer:

> Given this user request and current artifacts, which workflow should be the
> visible unit, which skills compose it, and what evidence gates must run?

## What Not To Import Directly

- Do not replace `scripts/mathformer.py`; extend it with meta-skill routes.
- Do not copy Looper's `agentic/` tree wholesale; Mathformer already has
  `skills/`, `docs/`, `tests/`, `artifacts/`, `config/`, and MCP surfaces.
- Do not expose every skill as an MCP tool; expose workflow-level actions.
- Do not put hidden reasoning in hooks; keep hooks deterministic.
- Do not treat Looper's oncology use case as a Mathformer domain feature; treat
  it as an architectural example of task-local workflow generation.

## Target Mathformer Architecture

```text
natural-language request
  -> Mathformer router
  -> meta-skill workflow registry lookup
  -> visible workflow selection
  -> composed skills and controlled actions
  -> deterministic and generative gates
  -> runtime skill-application trace
  -> workflow evolution state
  -> quality card and promotion decision
  -> optional MCP workflow endpoint
```

## Initial Meta-Skill Families

### Workflow Registry Manager

Owns task registry schemas, visible workflow entries, artifact references, and
validators.

### Skill Quality Guardian

Owns quality card schema, quality-card validation, and promotion blockers.

### Generated Skill Lifecycle Controller

Owns task-local generated skills, evaluation fixtures, seeded-defect tests,
evolution logs, and promotion state.

### Runtime Trace Interpreter

Owns skill application trace schema, trace rendering, drift extraction, and
runtime diagnosis.

### Taxonomy Navigation Planner

Owns workflow/skill taxonomy coordinates, candidate selection, reuse decisions,
and route explanations.

### Workflow Evolution Cartographer

Owns workflow evolution JSON, reflective questions, transition gates, and
next-delta reports.

## Integration Phases

### Phase 0: Planning Surface

Create `meta_skills/` with inventory, plan, and TODOs. This phase is complete
when this document and the TODO YAML validate as self-contained planning
artifacts.

### Phase 1: Registry Schema And First Registries

Create schemas and first task registries for two existing Mathformer workflows:
MathformerPhysicsLib foundations and MathformerPhysicsLib coherence. Validate
that each visible workflow lists actions, skills, artifacts, validators, and
release boundaries.

### Phase 2: Quality Cards

Create quality card schema and cards for the new meta-skill families and the
highest-risk generative skills, especially generative coherence and generative
repair. Wire cards into the comprehensive `skills` family.

### Phase 3: Runtime Tracing

Adapt existing reasoning-log tooling into a runtime skill-application trace.
Start with one route: `mathformerphysicslib.coherence`. Emit traces under
`artifacts/meta_skills/runtime/`.

### Phase 4: Workflow Evolution

Generate `workflow_evolution.json` for one recursive workflow, preferably
`lean-physics-recursive-repair-loop`, because it already has recursion,
generative repair, expansion maps, and blockers.

### Phase 5: Taxonomy Navigation

Add a taxonomy-first workflow navigation layer that can rank visible workflows
before falling back to prose search or generative interpretation. Integrate
with the existing natural-language router.

### Phase 6: Generated Skill Lifecycle

Define task-local generated skill structure and promotion gates. Use a contained
pilot: generated task-local physics critique or repair skill for one example,
not a broad promoted capability.

### Phase 7: MCP Boundary

Expose meta-skill registry and workflow selection as workflow-level MCP tools,
not per-skill tools. Ensure API keys and external dependency policy remain in
`config/`.

## Risks And Controls

| Risk | Control |
|---|---|
| Duplicating Mathformer workflow hub | Keep `scripts/mathformer.py` authoritative; meta-skills provide registry evidence and selection context. |
| Skill explosion | Require reuse decisions and task-local draft status before any promotion. |
| Prose-only meta-planning | Every TODO requires artifact paths and validators. |
| Hidden hook reasoning | Hooks only validate or log deterministic facts. |
| MCP surface sprawl | Expose workflow-level actions only. |
| Weak generated-skill evidence | Require quality cards, evals, run traces, and evolution logs before promotion. |
| Taxonomy overfitting | Validate with positive and negative route fixtures. |
| Formalization rigor dilution | Keep backend compile, Mathlib grounding, consistency, and non-vacuity gates as hard acceptance boundaries. |

## Success Criteria

The integration is successful when Mathformer can answer these questions from
repo artifacts, not chat history:

- Which visible workflow owns this request?
- Which skills compose it?
- Which deterministic and generative gates apply?
- Which generated skills or support artifacts are task-local drafts?
- Which evidence supports promotion, quarantine, or rollback?
- Which runtime traces show the workflow actually ran?
- Which workflow evolution state explains the next delta?
- Which MCP workflow endpoints expose the capability safely?
