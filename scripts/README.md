<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Scripts

Top-level files in this directory are the canonical execution entrypoints used
by docs, tests, the workflow hub, and skill hooks.

One-level thematic folders such as `scripts/physics-lean/`, `scripts/control/`,
`scripts/mcp/`, and `scripts/setup/` provide symlink views for navigation. Those links are
intentionally non-canonical: keep code and workflow references pointing at the
top-level script paths unless a script is deliberately split in a separate
compatibility-preserving change. There is no separate `scripts/themes/`
intermediate folder.

Run `python scripts/organize_repository_layout.py --apply --json` after adding
a canonical root script. Run it without `--apply` after adding or moving a skill
to verify physical theme placement, managed views, and root-file classification.
