<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make the framework understandable without requiring readers to inspect implementation details first.

Intent:
  Explain architecture, installation, principles, tutorials, licensing, and generated library outputs.

Function:
  Provides human-facing documentation that should stay aligned with tested behavior and code paths.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Skill Testing TODOs

Generated: 2026-06-05T16:39:06.086959+00:00

Each TODO states why it exists, what proves it done, and the command to run.

## 1. [P3] Expand adversarial content probes beyond the smoke set

- Status: todo
- Owner: `skill-test-program-orchestrator`
- Why: The current testing surface is green; the next gains come from harder ambiguity and semantic-preservation probes.
- Done when: At least one new adversarial probe family is added and executed successfully.
- Command: `python3 skills/control/skill-test-program-orchestrator/scripts/run_content_skill_codex_exec_tests.py --execute --json`
