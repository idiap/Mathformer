<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Mathformer detailed project guide

This guide preserves the detailed capabilities, examples, workflow descriptions,
integration instructions, and repository notes formerly on the root README.
Start with the [project README](../../README.md) for the concise introduction
and the [documentation index](../README.md) for the common reading structure.

Mathformer is a research workspace for turning mathematical language into formal artifacts (supporting Lean, Isabelle, TPTP/TSTP, Rocq) and symbolic algebra (SymPy). It connects natural-language agent requests to controlled workflows for ATP proof search, premise retrieval,autoformalization, and executable symbolic checks.

Its evaluation focus is reference-free: when no gold formalization exists,
Mathformer judges progress through source anchors, backend execution, critic
signals, non-vacuity, grounding, and artifact realness.

The repository includes real-world complex autoformalization targets in both
mathematics and physics. Mathematical examples include source-linked Lean
surfaces for [Hille-Yosida semigroup theory](../../backends/lean/Mathformer/AutoformalizedHilleYosida.lean),
[Choquet theory](../../backends/lean/Mathformer/AutoformalizedChoquetTheory.lean), and
[transformer scaling laws](../../backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean).
Physics examples include the backend-separated
[Mathformer Physics Library](../../libraries/MathformerPhysicsLib/README.md), with
[Lean](../../libraries/MathformerPhysicsLib/Lean/formalphysics_0172/MathformerPhysics.lean)
and [SymPy](../../libraries/MathformerPhysicsLib/SymPy/formalphysics_0172/MathformerPhysics.py)
FormalPhysics-derived artifacts that preserve assumptions, units, equations,
and executable validation traces.

## Key Concepts

Mathformer is an agentic control layer for formal reasoning in mathematics and
physics. The reusable workflow catalog is maintained in `skills/`.

- Natural-language requests are routed to controlled reasoning workflows.
- Specialized agents own narrow responsibilities: premise selection, Lean
  drafting, Vampire ATP, SymPy execution, Rocq/Isabelle drafting, physics unit
  and dimension checks, critique, refinement, and final review.
- Hook phases define the coordination: each phase has an owner,
  trigger, expected reasoning-log events, validation gate, and output artifact.
- Reflective loops run draft, execute, critique, and refine cycles while
  preserving source anchors, theorem shape, non-vacuity, mathlib/API grounding,
  and backend evidence.
- Physics workflows add units, dimensions, regimes, reference
  frames, law grounding, numeric sanity checks, and reviewer loops.
- The output is inspectable evidence: Lean/Rocq files, TPTP/TSTP proofs, SymPy
  traces, theorem-memory indexes, consistency reports, or blocker reports.

## Install

Install `uv`, then run this from the repository root:

```bash
uv run python scripts/install_env.py --all-extras
```

This installs the Python environment and all Python extras. For a lighter setup,
replace `--all-extras` with only the profile you need, such as `--with-sympy`.

With an agent, ask: "Set up the Python Mathformer development environment."

Optional backends can be added only when needed: Lean uses `elan`/`lake`,
Vampire ATP uses `vampire`, and Rocq/Isabelle use their own installers. Details
are in the [install guide](../getting-started/INSTALL.md) and
[agent client setup guide](../getting-started/AGENT_CLIENT_SETUP.md).

For Codex and Claude Code, install the [Mathformer plugin](../../plugins/README.md).
It exposes the canonical skills through both clients' plugin marketplaces and
uses this checkout for workflow execution.

## Demonstrations

### Autoformalization

Ask the agent:

> Autoformalize the theorem that the sum of the first `n` odd numbers is `n^2`,
> then validate the Lean candidate and explain which evidence was obtained.

This starts from a familiar informal theorem:

```text
1 + 3 + 5 + ... + (2n - 1) = n^2
```

Mathformer keeps the informal statement visible, drafts a Lean formal surface,
checks what the local Lean/Lake environment can validate, and reports whether
the artifact is accepted, candidate-only, or blocked by missing tooling.

Files: [informal source](../../tests/latex/wiki_level/sum_first_odd_numbers.tex),
[Lean theorem fixture](../../tests/lean/WikiLevelGold.lean).

### ATP Proof Discovery

Ask the agent:

> Prove that in a group, the inverse of a product reverses order, use premise
> selection if helpful, and explain the Vampire proof artifact.

This is the standard theorem `(x * y)^-1 = y^-1 * x^-1`. Mathformer translates
the informal statement into a TPTP problem, selects the relevant group axioms,
generates and proves any helper lemmas before reusing them, asks Vampire for a
proof, and writes both machine-readable proof evidence and a human-readable
explanation.

Typical artifacts live under `artifacts/vampire_atp/` and include the generated
TPTP problem, the Vampire TSTP proof, premise-selection reports, and an informal
proof explanation.

Files: [input](../../examples/vampire_group_inverse_product_input.md), [output
summary](../../examples/outputs/vampire_group_inverse_product_demo.md).

### Checked Formalization Candidates

Ask the agent:

> Validate the Lean and Rocq theorem fixtures for the wiki-level examples, and
> report which artifacts are compiler-checked versus structurally validated.

The demonstration suite includes familiar mathematical claims such as the sum
of the first odd numbers, monotone function composition, injective composition,
and elementary set identities. Mathformer can draft or inspect formal artifacts
and then route them through the strongest checker available in the local
environment.

Files: [case manifest](../../tests/latex/wiki_level/manifest.json), [Lean
fixture](../../tests/lean/WikiLevelGold.lean), [Rocq generated odd-sum
file](../../backends/rocq/MathformerRocq/AutoformalizedWikiSumFirstOddNumbers.v).

### Physics Derivation: RC Discharge

Ask the agent:

> Verify the RC discharge derivation `dV/dt = -V/(R C)`, `V(0)=V0`, so
> `V(t)=V0 exp(-t/(R C))`, and explain the assumptions, units, and executable
> validation result.

Mathformer represents the discharge law as an executable SymPy physics trace.
It checks that the proposed voltage curve satisfies the differential equation,
matches the initial condition, preserves the voltage/time/resistance/capacitance
quantity structure, and passes a concrete numeric sample.

Files: [source fixture](../../tests/physics_sympy/controlled_latex/rc_discharge.tex),
[SymPy artifact](../../backends/sympy/MathformerSympyPhysics/AutoformalizedRcDischarge.py),
[output summary](../../examples/outputs/rc_discharge_physics_demo.md).

### Premise Selection

Ask the agent:

> Run premise selection over the famous theorem and axiom corpus, then search
> for facts near the Fundamental theorem of algebra.

Mathformer indexes the local theorem corpus, checks whether the target theorem
is already present, returns nearby facts by semantic search, and reports
geometric distance in the embedding space.

Files: [search output
summary](../../examples/outputs/fundamental_theorem_algebra_search_demo.md).

## How It Runs

1. You ask for a mathematical outcome in natural language.
2. The generative workflow coordinator interprets the goal, decomposes it when
   needed, and validates each selected intent through the deterministic router.
3. The relevant backend runs locally: Vampire, Lean, Rocq, SymPy, or the premise
   KB.
4. The result is reported with artifacts and validation status.

Automation and regression paths still exist underneath, but the intended front
door is the natural-language agent interface provided by
`mathformer-generative-workflow-coordinator`.

The [PRISM project](../../mathformer-prism/README.md) represents the repository's
named hook-loop contracts as typed workflow programs. Its generated
[workflow catalog](../../mathformer-prism/workflow_catalog.md) records
the ordered hooks, owner skills, optional extensions, and linked native helper
resources; individual skills remain reusable components rather than entrypoints.

## Start Here

- [Install guide](../getting-started/INSTALL.md): the short local setup path and optional
  backend notes.
- [HowTo](../getting-started/HOWTO.md): natural-language overview of the main workflows.
- [Tutorial](../getting-started/TUTORIAL.md): guided demonstrations with expected artifacts.
- [Proof Catalog](../libraries/PROOF_CATALOG.md): descriptions and links for the
  proof-oriented MathformerLib and Mathformer library modules.
- [Principles](../architecture/PRINCIPLES.md): design principles for formal evidence.
- [Reasoning logs](../architecture/REASONING_LOGS.md): structured skill traces,
  Markdown/HTML rendering, and coverage checks.
- Workflow graph report (`artifacts/workflow_graphs/workflow_graphs.html`, generated by
  `uv run python scripts/mathformer.py run docs:workflow-graph-render`):
  click drill-down view of the agentic workflow stacks and reflective loops.
- [Natural-language agent interface](../getting-started/NL_AGENT_INTERFACE.md): how VS Code,
  Codex, Claude Code, and OpenCode handle ordinary-language requests.
- [MCP server](../architecture/MCP_SERVER.md): expose the controlled workflow hub to
  Claude Desktop, Claude Code, and other MCP clients, locally or remotely.
- [Independent MCP service TODOs](../operations/INDEPENDENT_MCP_SERVICE_TODOS.md):
  whole-pipeline service deployment with dependencies and config-based API keys.
- [AgenticHub](../architecture/AGENTIC_HUB.md): advanced reference for agents, skills, and exact controlled
  actions.
- [Dependency index](../operations/DEPENDENCIES.md): framework, package, license, and URL inventory.
- [License guide](../operations/LICENSES.md): project, dependency, and dataset licensing.

## Repository Shape

```text
mathformer/
├── backends/                ATP, Isabelle, Lean libraries/executables, premise-KB, Rocq, and SymPy
├── libraries/               reusable Mathformer and physics libraries
├── paper/                   LaTeX papers, PDFs, and paper figures
├── skills/                  reusable agent workflows
├── docs/                    guides, tutorials, and backend notes
├── examples/                small demonstration inputs
├── tests/                   regression and validation fixtures
└── artifacts/               generated proofs, reports, indexes, and traces
```

## License

Mathformer source and documentation are MIT licensed. See [LICENSE](../../LICENSE)
for the project license and the [license guide](../operations/LICENSES.md) for dependency,
vendored-source, and dataset licensing notes. A generated inventory of the
current Python environment is kept in
[Python dependency license inventory](../operations/PYTHON_DEPENDENCY_LICENSES.md).


## Disclaimer

This is experimental research software under continuous development.

Neuro-symbolic AI Lab - IDIAP Research Institute
