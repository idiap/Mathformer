<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Development

Change the project and run the relevant checks. This section is for maintainers and operators.

Start with [AGENTS.md](../../AGENTS.md) and use the focused checks below.
Use the controlled hub for repository checks:

```bash
uv run python scripts/mathformer.py audit --strict --json
uv run python scripts/mathformer.py run test:docs
```

The documentation check writes test artifacts. Use a backend-specific gate when
changing formalization or execution behavior; a successful documentation check is
not a proof result.

## Read next

- [Documentation maintenance](documentation.md) — Shared structure, preservation, and review rules.

- [Agent instructions](../../AGENTS.md) — Canonical working rules and checks.
- [Hub reference](../architecture/AGENTIC_HUB.md) — Setup, validation, and action effects.
- [Cross-platform development](../getting-started/CROSS_PLATFORM.md) — Portable scripts and clients.
- [Portable adoption regression assurance](../migrations/portable-repository-adoption/REGRESSION_ASSURANCE.md) — Compatibility evidence.

Return to the [documentation index](../README.md) or consult the
[documentation map](../reference/documentation-map.md) for the complete retained collections.
