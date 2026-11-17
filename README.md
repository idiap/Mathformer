<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Mathformer

## Overview

Mathformer turns mathematical and physical language into inspectable formal and
symbolic artifacts. It connects natural-language goals to controlled workflows for
autoformalization, premise retrieval, proof search, execution, critique, and refinement.
Its backends include Lean/mathlib, Vampire ATP with TPTP/TSTP, SymPy, Rocq, and Isabelle
surfaces; their available checks and maturity differ.

## Key concepts

- **Source-grounded formalization:** retain the original statement, assumptions, and source anchors through each transformation.
- **Controlled refinement:** draft, execute, criticize, and repair within declared workflow and hook contracts.
- **Backend-specific evidence:** a Lean compilation, ATP proof, SymPy check, and structural validation establish different things.
- **Reference-free evaluation:** assess grounding, non-vacuity, executable evidence, and artifact substance when no gold formalization exists.
- **Governed reuse:** keep theorem-memory candidates separate from accepted library results.

## Getting started

Use Python 3.11–3.13 and `uv`. From the repository root:

```bash
uv run python scripts/install_env.py --all-extras
uv run python scripts/mathformer.py --help
```

`--all-extras` installs Python extras, including the heavier document-extraction stack.
Use `--with-sympy` for a smaller symbolic setup. External provers are optional and
installed separately; the [installation guide](docs/getting-started/INSTALL.md)
explains Lean, Vampire, Rocq, and Isabelle requirements.

With an agent, ask: “Set up the Python Mathformer development environment.”

## Examples

Ask the agent to:

- Autoformalize `1 + 3 + … + (2n - 1) = n²` and distinguish compiler evidence from candidate status.
- Prove that a group product's inverse reverses order using Vampire and explain the proof artifact.
- Verify the RC discharge equation with SymPy, including its assumptions and units.

The [detailed project guide](docs/guides/project-guide.md#demonstrations) preserves
these demonstrations and source links. The [tutorial](docs/getting-started/TUTORIAL.md)
explains larger mathematics and physics artifacts and how to interpret their limits.

## Architecture

```text
source → extraction and premise grounding → backend candidate
       → execution → critique and repair → accepted artifact or explicit blocker
```

Canonical skills live in `skills/`; controlled entrypoints in `scripts/`; backend
implementations in `backends/`; reusable results in `libraries/`; run outputs in
`artifacts/`. The natural-language coordinator routes goals through the deterministic
hub rather than granting generated text acceptance authority.

Read the [architecture overview](docs/architecture/README.md) and
[principles](docs/architecture/PRINCIPLES.md).

## Documentation

<a id="autoformalization"></a>
<a id="atp-proof-discovery"></a>
<a id="checked-formalization-candidates"></a>
<a id="physics-derivation-rc-discharge"></a>
<a id="premise-selection"></a>
<a id="install"></a>
<a id="demonstrations"></a>
<a id="how-it-runs"></a>
<a id="start-here"></a>
<a id="repository-shape"></a>
<a id="license"></a>
<a id="disclaimer"></a>

Start with the [documentation index](docs/README.md). All project documentation
uses the same reading areas; specialist collections retain their stable paths.

- [Getting started](docs/getting-started/README.md) — Install the environment and complete a first example.
- [Concepts](docs/concepts/README.md) — Understand the project model, terminology, and evidence boundaries.
- [Guides](docs/guides/README.md) — Carry out tasks and interpret their outputs.
- [Architecture](docs/architecture/README.md) — Understand components, data flow, contracts, and extension points.
- [Reference](docs/reference/README.md) — Look up commands, skills, workflows, and documentation sources.
- [Development](docs/development/README.md) — Change the project and run the relevant checks.
- [Operations](docs/operations/README.md) — Configure, run, observe, and release maintained workflows.
- [Governance](docs/governance/README.md) — Check licensing, provenance, review, and publication requirements.
- [Archive](docs/archive/README.md) — Find historical material and distinguish plans from current behavior.

## Development and validation

Start with [AGENTS.md](AGENTS.md) and the [development guide](docs/development/README.md).
Use the controlled hub for repository checks:

```bash
uv run python scripts/mathformer.py audit --strict --json
uv run python scripts/mathformer.py run test:docs
```

The documentation check writes test artifacts. Use a backend-specific gate when
changing formalization or execution behavior; a successful documentation check is
not a proof result.

## Limitations and status

This is experimental research software. Backend checks have different claim ceilings;
a compiled interface or theorem with explicit assumptions does not establish the
entire source theory. Generated candidates, retrieved premises, critic assessments,
and proved artifacts remain distinct. Some report paths exist only after their
producing workflow runs. Plans and archived material do not describe guaranteed
current capabilities.

## Dependencies and license

Source and documentation are MIT licensed; see [LICENSE](LICENSE).
[DEPENDENCIES.md](DEPENDENCIES.md), the [license guide](docs/operations/LICENSES.md),
and the [environment license inventory](docs/operations/PYTHON_DEPENDENCY_LICENSES.md)
describe dependencies, vendored sources, and datasets under their respective terms.

Neuro-symbolic AI Group, Idiap Research Institute.
