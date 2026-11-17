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

# VS Code And Agent Skills Setup

This page is the short VS Code path. For the complete cross-client guide,
including Codex, Claude Code, and OpenCode, see
the [agent client setup guide](../getting-started/AGENT_CLIENT_SETUP.md).

## Install VS Code Extensions

Open the repository with:

```bash
code .
```

Recommended extensions:

```bash
code --install-extension leanprover.lean4
code --install-extension ms-python.python
code --install-extension tamasfe.even-better-toml
```

You can also install them from the Extensions view:
`Ctrl+Shift+X` on Windows/Linux or `Cmd+Shift+X` on macOS.

## Install Mathformer

From the VS Code integrated terminal:

```bash
uv run python scripts/install_env.py --all-extras
```

If you prefer to call Python directly:

```bash
python scripts/install_env.py --all-extras
```

Select `.venv` as the Python interpreter in VS Code after installation.

## Use Natural-Language Requests

Once the workspace and skills are available, interact with the agent by naming
the outcome you want:

- "Prove the inverse-of-product theorem in group theory with Vampire and show me
  the proof artifact."
- "Run premise selection and test semantic search."
- "Check whether the Lean formalization compiles."
- "Generate and validate Rocq proof-script candidates."
- "Review the documentation and make the HOWTO more natural."

The agent should resolve the request to a skill and a controlled workflow. The
underlying scripts are there for reproducibility and audits, not as the primary
conversation interface.

## Publish Agent Skills

The source skills live in `skills/`. Publish them into the project-local
discovery folders used by Codex, Claude Code, and OpenCode:

```bash
python scripts/link_agent_skills.py --profile all-repo --mode auto --replace
```

On Windows without symlink support:

```powershell
py -3 scripts/link_agent_skills.py --profile all-repo --mode copy --replace
```

If Codex, Claude Code, or OpenCode is already running, restart the agent client
or reload the VS Code window after publishing skills.

## Verify

Ask the agent:

> Run premise selection, test semantic search, and report the generated artifacts.

For Lean work, ask the agent to check whether the Lean formalization compiles.
For Vampire ATP, make sure `vampire` is on `PATH` or set `VAMPIRE_BIN`.
