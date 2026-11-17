<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Explain Mathformer's Looper-derived meta-skill governance layer as a real
  repository surface rather than hidden agent behavior.

Intent:
  Document implemented meta-skill workflows, generated skill promotion rules,
  runtime traces, taxonomy navigation, and MCP exposure boundaries.

Function:
  Provides the user-facing architecture reference for the `meta_skills/`
  folder and its controlled validation suite.

Maintenance Notes:
  Keep implemented surfaces synchronized with `meta_skills/README.md`,
  `scripts/mathformer.py`, and `tests/meta_skills/run_meta_skill_suite.py`.
-->

# Meta-Skills

Mathformer meta-skills govern other skills, generated agents, workflow routes,
runtime traces, and promotion decisions. They import Looper's useful
control-plane ideas without replacing Mathformer's execution substrate.

Implemented surfaces:

- `meta_skills/registry/tasks/`: visible workflow task registries.
- `meta_skills/quality_cards/`: deterministic and generative skill quality
  cards.
- `artifacts/meta_skills/runtime/`: normalized runtime skill-application
  traces.
- `meta_skills/registry/tasks/*/workflow_evolution.json`: state-transition
  graphs for long recursive workflows.
- `meta_skills/taxonomy/`: taxonomy-first workflow navigation and skill
  projections.
- `meta_skills/registry/generated_skills/`: task-local generated skill
  lifecycle records and promotion gates.
- `meta_skills/registry/workflow_actions.yaml`: MCP workflow-boundary policy.

The controlled validation entrypoint is:

```bash
python tests/meta_skills/run_meta_skill_suite.py --json
```

The natural-language route is:

```bash
python scripts/mathformer.py ask "show meta-skill workflows" --json
python scripts/mathformer.py ask "validate meta-skills" --run --json
```

## Integration Rule

Meta-skills do not execute arbitrary generated skills directly. They route
through `scripts/mathformer.py` and expose workflow-level actions to MCP clients
through the existing `mathformer_ask`, `mathformer_run_action`, and
`mathformer_help` tools.

External API keys remain a service configuration concern under `config/`; they
are not loaded from skill environment variables.

## Generated Skill Promotion

Task-local generated skills follow this lifecycle:

`draft -> task_local_validated -> repeated_use_candidate -> promoted`

They may also become `quarantined` or `deprecated`.

Promotion requires explicit evidence:

- `SKILL.md`
- quality card
- eval fixture
- evolution log
- run trace
- seeded-defect result
- repeated-use evidence before promotion
- hub or hook routing before repository-wide exposure

One successful run is not enough for promotion.
