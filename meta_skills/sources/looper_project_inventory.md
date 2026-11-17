<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Preserve a compact but evidence-backed understanding of the extracted Looper
  project before planning Mathformer integration.

Intent:
  Identify Looper's reusable architectural surfaces without copying them
  blindly into Mathformer.

Function:
  Summarizes the archive inventory, core contracts, validators, registries,
  skills, and integration-relevant artifacts.

Maintenance Notes:
  Refresh this inventory if a newer Looper archive is extracted or if Mathformer
  starts importing Looper artifacts directly.
-->

# Looper Project Inventory

## Source

- Archive: `artifacts/external/looper/looper-repo-content-20260707-033817.zip`
- Extracted path:
  `artifacts/external/looper/looper-repo-content-20260707-033817/looper`
- Archive entry count observed during extraction: `511`
- Uncompressed size observed during extraction: `1475626` bytes

Archive and extracted paths are relative to the repository root. The source
archive is supplied locally and is not bundled.

## Core Thesis

Looper is a repo-local operating harness for long-horizon agentic development.
Its central design choice is visibility: judgment-heavy capabilities are
explicit skills, mechanically checkable behavior is scripts and schemas, and
loop state is durable artifacts.

The Looper README states five practical boundaries that matter for Mathformer:

- loop behavior lives in explicit `agents/skills/<theme>/<skill>/SKILL.md`
  files;
- deterministic behavior lives in scripts, schemas, fixtures, and registries;
- durable loop state lives under `agentic/`;
- hooks only log or enforce deterministic policy;
- every loop iteration must produce a durable delta.

## Main Folders

- `agents/skills/`: 24 explicit skills grouped into one-level themes.
- `agentic/spec/`: requirement, assumption, reasoning-log, quality, and reuse
  schemas.
- `agentic/todos/`: planning, elicitation, diagnostic, framework, dependency,
  and skill-reuse TODOs.
- `agentic/registries/`: skill, quality, dependency, deterministic mechanism,
  workflow action, workflow contract, gate policy, and drift monitor registries.
- `agentic/scripts/`: deterministic validators, generators, auditors, and report
  builders.
- `agentic/reports/`: generated compliance, drift, runtime, workflow, use-case,
  release, and skill reports.
- `registry/`: user-visible workflow registry with task-local reference skills,
  generated skills, workflow plans, reports, taxonomy, and decisions.
- `hooks/`: transparent deterministic hook configuration and scripts.
- `docs/demo/`: a live notebook and narrative demo for an oncology
  evidence-to-workflow use case.

## Explicit Skill Themes

Looper exposes 24 skills under these one-level themes:

- `orchestration`: `long-horizon-loop-runner`, `release-promoter`,
  `phase-transition-interpreter`, `gate-decision-interpreter`.
- `intake-planning`: `elicitation-gate`, `goal-quality-enricher`,
  `planning-todo-manager`, `spec-graph-compiler`.
- `diagnosis-evidence`: `abductive-diagnostician`, `compliance-assessor`,
  `drift-monitor-auditor`, `dynamic-critical-question-generator`,
  `evidence-flow-interpreter`, `frame-adequacy-gate`.
- `reuse-taxonomy`: `external-framework-reuse-gate`, `rskills-curator`,
  `skill-reuse-auditor`, `skill-taxonomy-classifier`,
  `taxonomic-skill-navigator`.
- `governance-integration`: `external-dependency-manager`,
  `hook-policy-maintainer`.
- `validation-evals`: `eval-generator`, `critique-skill-factory`,
  `reflection-essential-attribute-abstractor`.

## Deterministic Spine

`agentic/scripts/agentic_check.py` runs a large standard-library validation
suite covering:

- explicit skills and SPDX headers,
- skill registry and skill quality registry,
- reasoning logs,
- skill application logs and runtime dynamics,
- taxonomy projections and candidate navigation,
- task workflow registry,
- workflow contracts and workflow hub report,
- gate policy,
- TODOs, requirements, assumptions, state stores, drift monitor registry,
- hook contracts,
- promotion gates,
- compliance, drift, frame adequacy, external framework, and runtime reports,
- goal enrichment, generated skill refinement, workflow evolution, loop
  coherence, use-case evals, skill trigger evals, and reasoning-log reports.

This is not a single script to copy. It is a validation pattern Mathformer can
map onto existing `scripts/mathformer.py`, `skills/SKILL_HOOKS.yaml`, and
`tests/test_program/run_comprehensive_tests.py`.

## Workflow-Visible Registry

The strongest Looper idea is the task-local workflow registry. The
`registry/tasks/oncology-evidence-to-workflow/task_registry.json` artifact
exposes:

- visible workflow name and end-to-end function,
- key function,
- reasoning types,
- problem-domain types,
- task-context types,
- composed skills,
- deterministic hooks,
- workflow references,
- artifacts,
- validators,
- reference skills,
- generated task-local skills,
- reference hooks.

This is a better user-facing unit than raw skills. Mathformer should adopt this
for high-value workflows such as MathformerPhysicsLib foundations, physics Lean
repair, textbook autoformalization, premise KB construction, and MCP
deployment.

## Generated Skill Governance

Looper's oncology workflow demonstrates task-local generated skills. Each
generated skill is kept as draft until it has:

- `SKILL.md`,
- `QUALITY_CARD.yaml`,
- `EVAL.yaml`,
- `EVOLUTION_LOG.md`,
- run traces,
- seeded-defect rejection evidence,
- a promotion boundary.

Mathformer already generates many artifacts and workflows, but it does not yet
have a uniform task-local generated-skill promotion contract. This is a direct
fit for `meta_skills/`.

## Workflow Evolution

`workflow_evolution.json` materializes workflow states and transitions. Each
state has:

- id, label, representation, path, status, summary,
- reasoning types,
- reflective questions,
- next delta.

The materialization policy states that workflow evolution needs durable
representation, transition evidence, and a reflective next-delta decision.

Mathformer can use this pattern to make long formalization loops inspectable
without relying on prose-only retrospectives.

## Boundary Lessons For Mathformer

- Do not hide loop behavior in hooks. Hooks should validate and log.
- Do not expose every skill as an MCP tool. Expose workflow-level actions.
- Do not promote generated skills from one successful task-local run.
- Do not let green presence checks substitute for real evidence.
- Do not solve deterministic validation with generative prose.
- Do not use broad RAG over all skills before typed taxonomy navigation.
