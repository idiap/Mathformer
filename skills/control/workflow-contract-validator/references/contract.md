<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

Intent:
  Tell coding agents what context to load, what invariants to preserve, and how to validate their work.

Function:
  Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Hook Contract

`skills/SKILL_HOOKS.yaml` is the canonical contract for systematic skill
application.

Required hook fields:

- `id`: stable dotted hook id.
- `phase`: workflow phase.
- `trigger`: when the hook applies.
- `owner_skill`: skill directory that owns the hook.
- `reasoning_log_steps`: expected event step names. Empty is allowed only for
  hooks that are pure capability routing with no current runtime.

Runtime contract fields:

- `orchestrator_skill`: canonical end-to-end owner.
- `reasoning_log_required_payload_fields`: currently includes `skill`.
- `recommended_payload_fields`: currently includes `hook_id` and `duration_ms`.
- `shared_runtime_scripts`: repo-relative runtime paths that must exist.

Direct routing maps user-facing intents to owner skill directories. Every target
must exist and contain `SKILL.md`.
