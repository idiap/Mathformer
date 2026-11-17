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

# Skill Hook Coverage Policy

## Coverage Rule

Every non-wrapper skill should be reachable by at least one of:

- an owner hook in `skills/SKILL_HOOKS.yaml`,
- a direct request route in `direct_request_routing`.

Compatibility wrappers may be exempt, but the exemption must be explicit and reviewed.

## Loop Rule

Named loops should declare:

- `required_hooks`: the minimum hooks that make the loop real,
- `recommended_hooks`: optional hooks that improve control,
- `required_owner_skills`: owner skills that must appear among required hooks.

The audit blocks missing required hooks and missing required owner skills. It reports
missing recommended hooks as nonblocking unless a future policy makes them required.

## Canonical Loop Families

- control and validation
- preformalization expansion and result precheck
- mathlib grounding and compatibility
- drafting, execution, critique, and refinement
- artifact acceptance and statistics
- MathformerLib accumulation
- reflective testing and monotonic improvement
