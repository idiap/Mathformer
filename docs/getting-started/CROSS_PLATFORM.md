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

# Cross-Platform Notes

Mathformer is intended to run on macOS, Linux, and Windows. The Python, KB,
SymPy, benchmark, and documentation workflows are pure Python once their
optional dependencies are installed. Lean/Lake support follows the Lean
toolchain. Vampire, Rocq, and Isabelle are optional external tools and depend on
the platform packages or binaries available on your machine.

## Command Launcher Convention

Documentation examples use:

```bash
python path/to/script.py
```

Use the Python 3 launcher that is correct for your platform:

| Platform | Common launcher |
| --- | --- |
| macOS/Linux | `python3` or `python` |
| Windows PowerShell | `py -3` or `python` |
| Activated virtual environment | `python` |

The examples use forward slashes in paths. Python, Lean, Git Bash, WSL, and
modern PowerShell all accept them in ordinary file arguments.

## Install Entrypoints

The canonical installer is launched through `uv`:

```bash
uv run python scripts/install_env.py --all-extras
```

This installs Python dependencies only. Lean/mathlib setup is explicit:

```bash
uv run python scripts/install_env.py --with-lean
```

If you already have a suitable Python active, the direct form is equivalent:

```bash
python scripts/install_env.py --all-extras
```

On Unix-like shells, this wrapper remains available:

```bash
./scripts/install_uv_env.sh --all-extras
```

For VS Code + Codex, Claude Code, and OpenCode setup, see the
[agent client setup guide](AGENT_CLIENT_SETUP.md).

## Agent Skill Publishing

The canonical local skills live under `skills/`. Agent clients discover skills
from client-specific directories, so use the cross-platform publishing helper
instead of shell loops:

```bash
python scripts/link_agent_skills.py --profile all-repo --mode auto --replace
```

Then verify that Codex, Claude Code, and OpenCode discovery folders are aligned:

```bash
python tests/agent_clients/run_skill_client_discovery.py --json
```

On Windows without symlink support, use copies:

```powershell
py -3 scripts/link_agent_skills.py --profile all-repo --mode copy --replace
```

## Virtual Environment Paths

The installer creates `.venv` by default. Python itself is located at different
paths depending on the platform:

| Platform | Python inside `.venv` |
| --- | --- |
| macOS/Linux | `.venv/bin/python` |
| Windows | `.venv\Scripts\python.exe` |

Project scripts should use `sys.executable` when they need to spawn another
Python process. Documentation should prefer `python script.py` after activation
instead of hard-coding either platform-specific venv path.

Activation examples:

```bash
source .venv/bin/activate
```

```powershell
.\.venv\Scripts\Activate.ps1
```

## Optional External Tools

Lean/Lake:

- install through `elan`;
- ensure `lake --version` works in the shell you use for Mathformer;
- run `lake build` from the repository root.

Vampire:

- install a Vampire executable for your platform;
- ensure `vampire --version` works, or set `VAMPIRE_BIN` to the executable path;
- pass `--vampire-bin path/to/vampire` to `scripts/run_vampire_atp.py` for a
  one-off override.

Rocq:

- install the Rocq Prover for your platform when you want compiler validation;
- ensure `rocq --version` or `coqc --version` works;
- run `skills/rocq/rocq-execution-runner/scripts/check_rocq_file.py --path MathformerRocq`
  for structural validation plus optional compiler execution;
- pass `--compiler-bin path/to/rocq` or `--compiler-bin path/to/coqc` for a
  one-off override.

Isabelle:

- install Isabelle separately from the official distribution;
- ensure the Isabelle command-line tools are reachable before running Isabelle
  skills or tests.

## Developer Checklist

- Use `pathlib.Path` for file paths.
- Use `sys.executable` for Python subprocesses.
- Use `shutil.which()` for optional external tools.
- Avoid shell-only commands in Python scripts.
- Keep Bash wrappers as convenience wrappers, not required entrypoints.
- When adding docs, include PowerShell-friendly alternatives for commands such
  as `rm`, `cat`, `find`, and `sed`.
