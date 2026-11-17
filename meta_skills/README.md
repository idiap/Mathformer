<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make Mathformer's meta-skill integration planning visible, durable, and
  checkable instead of leaving it in chat history.

Intent:
  Hold source analysis, architectural plans, and self-contained TODOs for
  importing Looper-style long-horizon skill governance into Mathformer.

Function:
  Provides the local planning surface for meta-skills: workflow-visible
  registries, skill quality cards, runtime traces, taxonomy navigation, and
  promotion controls.

Maintenance Notes:
  Keep this folder aligned with `skills/SKILL_HOOKS.yaml`, `scripts/mathformer.py`,
  `tests/test_program/run_comprehensive_tests.py`, and MCP service docs when
  TODOs are implemented.
-->

# Meta Skills

`meta_skills/` is the planning and control surface for Mathformer capabilities
that reason about skills, workflows, generated agents, routing, evidence,
promotion, and long-horizon improvement.

The current seed is the Looper project archive:

- Source zip:
  `artifacts/external/looper/looper-repo-content-20260707-033817.zip`
- Extracted analysis copy:
  `artifacts/external/looper/looper-repo-content-20260707-033817/looper`

These paths are relative to the repository root. Supply the source archive
locally at the indicated path before extracting it; it is not bundled.

## Contents

- [sources/looper_project_inventory.md](sources/looper_project_inventory.md):
  what the Looper archive contains and which artifacts matter for Mathformer.
- [looper_mathformer_integration_plan.md](looper_mathformer_integration_plan.md):
  deep integration strategy, boundary decisions, risks, and target Mathformer
  surfaces.
- [todos/looper_integration_todos.yaml](todos/looper_integration_todos.yaml):
  self-contained implementation TODOs with acceptance evidence and validation
  commands.
- [../docs/architecture/META_SKILLS.md](../docs/architecture/META_SKILLS.md):
  user-facing architecture guide for the implemented meta-skill layer.
- [../docs/architecture/REFLECTIVE_REFINEMENT.md](../docs/architecture/REFLECTIVE_REFINEMENT.md):
  proposed skill-independent semantics for changing reasoning itself through
  immutable specifications, typed deltas, comparative evidence, and governed
  adoption.
- [todos/reflective_refinement_todos.yaml](todos/reflective_refinement_todos.yaml):
  self-contained implementation backlog for the reflective-refinement model,
  meta-capability classification, provenance boundary, and controlled pilot.
- [../docs/architecture/KNOWLEDGE_RESOURCES_IN_REASONING_FLOWS.md](../docs/architecture/KNOWLEDGE_RESOURCES_IN_REASONING_FLOWS.md):
  proposed skill-independent semantics for logical KB, search, and persistent
  store dependencies in reasoning flows.
- [todos/knowledge_resource_todos.yaml](todos/knowledge_resource_todos.yaml):
  self-contained implementation backlog for resource syntax, bindings,
  receipts, immutable KB versions, index coherence, and migration.

## Integration Rule

Looper should not replace Mathformer's existing execution substrate. Mathformer
already has:

- natural-language routing in `scripts/mathformer.py`,
- controlled workflow hooks in `skills/SKILL_HOOKS.yaml`,
- a comprehensive test matrix in `tests/test_program/run_comprehensive_tests.py`,
- repo-local skill publication for Codex, Claude, and OpenCode,
- an independent MCP service plan.

Looper should be integrated as a meta-skill governance layer over those
surfaces: workflow-visible registries, quality cards, generated skill
promotion gates, runtime trace interpretation, taxonomy-first navigation, and
workflow evolution evidence.
