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

# Agent Client Setup

This guide keeps client setup short. In every client, the pattern is the same:

1. Open the Mathformer repository root.
2. Install the Mathformer environment.
3. Install the Mathformer plugin for Codex/Claude, or publish local skills.
4. Ask for mathematical outcomes in natural language.

Scripts remain the controlled execution layer under the agent. They are not the
normal conversation interface.

## Shared Setup

From the repository root:

```bash
uv run python scripts/install_env.py --all-extras
```

This installs the Python environment. Add Lean/mathlib only when needed:

```bash
uv run python scripts/install_env.py --with-lean
```

For Codex and Claude Code, follow the [plugin installation guide](../../plugins/README.md).
The shared plugin exposes every canonical skill and executes workflows in this
checkout. It supports client caches without copying the runtime into them.

As an alternative, and for OpenCode, publish skills to the project-local discovery folders:

```bash
python scripts/link_agent_skills.py --profile all-repo --mode auto --replace
```

This publishes the canonical flat skill directories into:

- `.agents/skills/` for Codex-style repo agents;
- `.claude/skills/` for Claude Code;
- `.opencode/skills/` for OpenCode.

Verify all three client folders see the same skill set:

```bash
python tests/agent_clients/run_skill_client_discovery.py --json
```

If symlinks are unavailable, use copies:

```powershell
py -3 scripts/link_agent_skills.py --profile all-repo --mode copy --replace
```

## VS Code + Codex

Install VS Code and Codex from their official guides:

- [VS Code setup](https://code.visualstudio.com/docs/getstarted/overview)
- [Codex quickstart](https://developers.openai.com/codex/quickstart)

Then:

1. Open the repository in VS Code.
2. Select `.venv` as the Python interpreter.
3. Open Codex, sign in, and reload the window after publishing skills.
4. Ask: "Run premise selection near the Fundamental theorem of
   algebra."

## Claude Code

Install Claude Code from the official
[Claude Code setup guide](https://code.claude.com/docs/en/getting-started).
Then run it from the repository root:

```bash
claude
```

Claude Code reads `CLAUDE.md`, so create a local `CLAUDE.md` that points to
your local `AGENTS.md` when using shared agent guidance. These files and the
agent-client configuration directories are ignored by Git. After publishing
skills, ask:

> Validate the Lean theorem fixtures and report which artifacts compiled.

## OpenCode

Install OpenCode from the official [OpenCode guide](https://opencode.ai/docs/).
Then run it from the repository root:

```bash
opencode
```

Configure a provider with `/connect` if needed. After publishing skills, ask:

> Verify the RC discharge derivation and show the SymPy validation artifact.

## Smoke Test

After installing any client, ask the agent:

> Run premise selection, test semantic search, and then prove a small theorem with
> Vampire if the ATP binary is available.

## Troubleshooting

- `python` is not found: use `python3` on macOS/Linux or `py -3` on Windows.
- VS Code `code` is not found on macOS: run
  `Shell Command: Install 'code' command in PATH` from the Command Palette.
- Plugin skills do not appear: verify the Mathformer plugin is installed and
  enabled, then restart the session. See the [plugin guide](../../plugins/README.md).
- Directly published skills do not appear: rerun `scripts/link_agent_skills.py`,
  then restart the agent client so it refreshes project discovery.
- Symlinks fail on Windows: rerun the skill publishing command with
  `--mode copy`.
- `lake` is not found: install Lean through `elan` and restart the terminal.
- `vampire` is not found: install Vampire for your platform, set `VAMPIRE_BIN`,
  or ask the agent to run a non-ATP demonstration.

## Source Notes

Install instructions in this page were checked against official VS Code,
OpenAI Codex, Anthropic Claude Code, and OpenCode documentation on 2026-06-15.
