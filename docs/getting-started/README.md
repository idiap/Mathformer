<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Getting started

Install the environment and complete a first example. This section is for readers learning or using Mathformer.

Use Python 3.11–3.13 and `uv`. From the repository root:

```bash
uv run python scripts/install_env.py --all-extras
uv run python scripts/mathformer.py --help
```

`--all-extras` installs Python extras, including the heavier document-extraction stack.
Use `--with-sympy` for a smaller symbolic setup. External provers are optional and
installed separately; the [installation guide](INSTALL.md)
explains Lean, Vampire, Rocq, and Isabelle requirements.

With an agent, ask: “Set up the Python Mathformer development environment.”

## Read next

- [Install](../getting-started/INSTALL.md) — Python profiles and optional backends.
- [Agent client setup](../getting-started/AGENT_CLIENT_SETUP.md) — Expose skills to supported clients.
- [Natural-language interface](../getting-started/NL_AGENT_INTERFACE.md) — Translate a goal into a controlled workflow.
- [Tutorial](../getting-started/TUTORIAL.md) — Read complex artifacts and validation evidence.
- [Cross-platform setup](../getting-started/CROSS_PLATFORM.md) — Platform-specific setup and launch forms.

Return to the [documentation index](../README.md) or consult the
[documentation map](../reference/documentation-map.md) for the complete retained collections.
