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

# Installation

Most users need only the Python setup. Add external provers only when a
demonstration asks for them.

## Essential Setup

Install `uv`, then run this from the repository root:

```bash
uv run python scripts/install_env.py --all-extras
```

This installs Python dependencies only. `--all-extras` includes the heavier
paper-extraction stack through Docling; for a smaller symbolic setup use:

```bash
uv run python scripts/install_env.py --with-sympy
```

The installer still creates the local `.venv`; `uv` is only the launcher and
dependency manager. If you already have a suitable Python active, this direct
form is equivalent:

```bash
python scripts/install_env.py --all-extras
```

With Codex, Claude Code, OpenCode, or another local agent, you can simply ask:

> Set up the Python Mathformer development environment.

## Optional Backends

- Lean/mathlib: install `elan`; Mathformer uses the Lean version pinned in
  `lean-toolchain`, and Lean setup is opt-in:

```bash
uv run python scripts/install_env.py --with-lean
```

For Python extras and Lean together, run:

```bash
uv run python scripts/install_env.py --all-extras --with-lean
```

- Vampire ATP: install a `vampire` executable, or set `VAMPIRE_BIN` to its path.
- Rocq: install Rocq or a compatible `coqc` only if you want compiler checks for
  generated `.v` files.
- Isabelle: install Isabelle only if you plan to work on Isabelle artifacts.

The core docs, KB, SymPy, and structural validation paths work without all of
those external tools.

### External IsarMathLib

IsarMathLib is an optional external Isabelle/ZF library. Mathformer searches its
installed theory files and proposes imports without bundling its source code.
Install the [upstream repository](https://github.com/SKolodynski/IsarMathLib)
outside the Mathformer checkout. On macOS/Linux, the default location is:

```bash
export ISARMATHLIB_HOME="$HOME/.local/share/mathformer/IsarMathLib"
git clone https://github.com/SKolodynski/IsarMathLib.git "$ISARMATHLIB_HOME"
git -C "$ISARMATHLIB_HOME" checkout d1df8f2aed2e5cee934caea4a99906cdd42ac371
```

The revision above is the reference checkout for grounding searches. For another
installation location, set `ISARMATHLIB_HOME` to the checkout root or pass
`--root` to the grounding search. On Windows, clone into a directory outside this
repository and set `$env:ISARMATHLIB_HOME` in PowerShell. The default location on
all platforms is `.local/share/mathformer/IsarMathLib` under the user home directory.

Search the external library:

```bash
python skills/isabelle/isarmathlib-grounding-navigator/scripts/search_isarmathlib.py \
  --concept injective --concept composition --json
```

Searching theory text does not require Isabelle. To check proofs, install an
Isabelle version compatible with the selected IsarMathLib revision and follow
the upstream build instructions. IsarMathLib uses the ZF logic; its theory imports
require a compatible ZF session rather than HOL `Main`. A missing external
checkout does not block examples that use only installed Isabelle/HOL theories.

## Quick Check

Ask the agent:

> Run premise selection, test semantic search, and report the generated artifacts.

For a direct terminal check:

```bash
python scripts/mathformer.py run test:docs --json
```

For VS Code, Codex, Claude Code, or OpenCode setup, see the
[agent client setup guide](AGENT_CLIENT_SETUP.md). For platform details, see
the [cross-platform notes](CROSS_PLATFORM.md). For dependency licenses, see the
[license guide](../operations/LICENSES.md).

## Pre-commit checks

Install the locked development dependencies and enable the Git hook once per
checkout:

```bash
uv sync --locked --group dev
uv run --locked --no-sync pre-commit install
```

Run all hooks across tracked files at any time:

```bash
uv run --locked --no-sync pre-commit run --all-files
```

The [pre-commit](https://pre-commit.com/) hooks check Python lint with Ruff and
formatting with Black using the versions in `uv.lock`. Commits check staged
Python files; generated artifacts, vendored snapshots, and generated libraries
are excluded. The hooks report failures without editing files. Existing lint
and formatting findings must be resolved before affected files can pass.

To apply formatting to a file, run `uv run --locked --no-sync black path/to/file.py`
and stage the result before retrying. Inspect Ruff diagnostics before applying
any suggested fixes. These fast checks complement the controlled workflow
quality gates documented in the agent guide.

## Troubleshooting

`uv: command not found`

- Install `uv` from <https://docs.astral.sh/uv/>.

`lake: command not found`

- Install `elan`, then open a new shell and retry `lake --version`.

`Vampire binary not found`

- Install Vampire and ensure `vampire` is on `PATH`, or set `VAMPIRE_BIN` to an
  executable path.

`compiler_available: false` in a Rocq report

- Install Rocq and ensure `rocq` is on `PATH`, or install/use a compatible
  `coqc`. Without a compiler, Mathformer still performs structural Rocq
  artifact validation.

Python import fails in a SymPy or benchmark script

- Re-run the installer:

```bash
uv run python scripts/install_env.py --all-extras
```

Lean build fails after a dependency update

- Run:

```bash
lake update
lake build
```

- Fix the first Lean diagnostic first; later messages are often cascades.
