<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Tests

Tests are organized by backend or responsibility. The principal themes are
`architecture`, `atp`, `control`, `e2e`, `environment`, `generative`,
`isabelle`, `kb`, `mathlib`, `mcp`, `meta_skills`, `physics_lean`,
`physics_sympy`, `reasoning_logs`, `rocq`, `sympy`, and `test_program`.

The stable aggregate entrypoints remain at `tests/run_*.py`. The
`tests/runners/` folder provides thematic symlink views of those entrypoints,
while `tests/test_program/` also exposes the canonical matrix through symlinks.
Fixtures stay beside the test families that consume them or under
`tests/fixtures/` when shared.
