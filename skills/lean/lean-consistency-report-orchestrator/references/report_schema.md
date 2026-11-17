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

# Lean Consistency Report Schema

The report is intentionally layer-oriented so future critics can be inserted
without invalidating previous successful cases.

Required top-level fields:

- `generated_at_utc`
- `skill`
- `hook_id`
- `ok`
- `summary`
- `layers`
- `blocking_layers`
- `output_files`

Each layer has:

- `id`
- `ok`
- `required`
- `skipped`
- `duration_ms`
- `summary`
- `finding_count`
- `blocking_finding_count`
- `score_candidates`
- `cmd`

The orchestrator should only make gates stricter by adding new layers or
warnings. Existing successful cases remain valid unless a new layer finds a
real blocker that was previously unobserved.
