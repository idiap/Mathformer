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

# Mathformer SymPy Backend

The SymPy backend extends Mathformer from theorem-prover autoformalization into
executable symbolic algebra autoformalization. It follows the same reference-free
principles used elsewhere in the project: preserve source anchors, ground
concepts in a local library/API, execute the artifact, search for counterexamples,
verify the transformation trace, and report explicit validation criteria.

## Supported Style

The first supported style is `sympy_equational_trace`.

It targets:

- algebraic identities,
- finite sums,
- simplification claims,
- polynomial equalities,
- elementary derivative identities,
- simple matrix-expression identities.

The following styles are explicitly deferred until the equational-trace style
has stable deterministic tests:

- `sympy_solver_certificate`,
- `sympy_rewrite_trace`,
- `sympy_limit_calculus_trace`,
- `sympy_matrix_trace`,
- `sympy_combinatorics_trace`.

A second implemented style, `sympy_physics_derivation_trace`, handles
source-anchored physics derivations with explicit quantity binding, unit and
dimension analysis, implicit gap closure, physical-law grounding, generated
Python artifacts, and consistency reports. See the
[physics SymPy backend guide](PHYSICS_SYMPY_BACKEND.md).

## Artifact Contract

A complete SymPy run produces:

- source claim packet,
- parsed expression packet,
- assumption packet,
- SymPy API-grounding packet,
- generated Python artifact under `backends/sympy/MathformerSympy/`,
- executable transformation trace,
- symbolic validation report,
- bounded counterexample report,
- reference-free consistency report in JSON, Markdown, and optionally HTML.

Generated artifacts expose:

- `CLAIM`,
- `build_symbols()`,
- `build_expressions()`,
- `validate_symbolic()`,
- `validate_numeric_samples()`,
- `explain_trace()`.

Source-backed claims preserve original prose, original LaTeX, and source anchors.
Generated support assumptions, such as summation index variables, are represented
separately from literal source assumptions.

## Pipeline

1. `sympy-dependency-prober` checks required and optional packages.
2. `sympy-api-docs-indexer` builds a versioned local SymPy API index.
3. `sympy-expression-parser` extracts source-backed formulas and concepts.
4. `sympy-assumption-modeler` records domains and side conditions.
5. `sympy-concept-grounding-navigator` maps concepts to installed APIs.
6. `sympy-autoformalization-drafter` writes an executable Python artifact.
7. `sympy-execution-runner` imports and executes the artifact.
8. `sympy-identity-validator` independently validates symbolic equivalence.
9. `sympy-counterexample-searcher` searches bounded admissible domains.
10. `sympy-transformation-trace-verifier` checks trace evidence.
11. `sympy-consistency-report-orchestrator` merges metrics and status.

## Validation Criteria

A complete artifact satisfies:

- every formalized source formula is parsed or explicitly unresolved,
- assumptions are source-backed or marked generated,
- API-grounding evidence exists for transformation-critical concepts,
- symbolic validation passes for the selected method,
- numeric sampling finds no violations when meaningful,
- counterexample search finds no witness in the configured domain,
- every trace step cites an API or explicit rule,
- reverse-informal consistency is visible through source NL/LaTeX in `CLAIM`,
- the artifact is placeholder-free.

## API Index

The API index is written to `artifacts/sympy_api/index.json`, with per-module
shards under `artifacts/sympy_api/modules/`.

Each indexed object records:

- qualified name,
- module path,
- object kind,
- signature when inspectable,
- docstring summary,
- docstring examples when visible,
- assumption hints when visible,
- related method hints,
- source file path,
- source hash,
- docs search URL,
- SymPy version and freshness key.

## Controlled Examples

The controlled suite currently covers:

- `wiki_sum_first_odd_numbers`: `\sum_{i=0}^{n-1}(2i+1)=n^2`,
- `sympy_binomial_square`: `(a+b)^2=a^2+2ab+b^2`,
- `sympy_finite_geometric_sum`: `\sum_{k=0}^{n}r^k=(1-r^{n+1})/(1-r)`, with `r \ne 1`,
- `sympy_product_rule_derivative`: `d/dx(x^2\sin x)=2x\sin x+x^2\cos x`,
- `sympy_matrix_distributivity`: `A(B+C)=AB+AC`.

Run the suite:

```bash
python tests/sympy/run_controlled_suite.py --json
```

The suite writes reports under `artifacts/sympy/controlled_suite/` and an HTML
index at `artifacts/sympy/controlled_suite/index.html`.
