<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make the Rocq backend understandable to users who know Mathformer but have not inspected the implementation.

Intent:
  Explain how Mathformer generates, validates, and optionally compiles Rocq proof scripts.

Function:
  Documents commands, artifact layout, trust states, and extension points for the Rocq autoformalization path.

Maintenance Notes:
  Keep this page aligned with `backends/rocq/MathformerRocq/autoformalize.py`, the Rocq skills, and `tests/rocq/run_wiki_suite.py`.
-->

# Rocq Backend

The Rocq backend adds a proof-script target to Mathformer's multi-backend
autoformalization workbench. It starts from the controlled wiki-level LaTeX
theorem suite and emits complete `.v` files under `backends/rocq/MathformerRocq/`.

Rocq is the renamed Coq proof assistant. Modern Rocq documentation describes
batch compilation with `rocq compile file.v`; Mathformer also supports `coqc`
as a compatibility fallback when that is the executable available on a machine.

## What The Backend Provides

| Component | Purpose |
| --- | --- |
| `backends/rocq/MathformerRocq/autoformalize.py` | Core templates, source parsing, structural validation, optional compiler execution |
| `backends/rocq/MathformerRocq/*.v` | Committed Rocq proof-script examples for the controlled theorem suite |
| `scripts/run_rocq_autoformalization.py` | Repository-level CLI wrapper |
| `skills/rocq/rocq-autoformalization-drafter/` | Agent skill for generating Rocq artifacts |
| `skills/rocq/rocq-execution-runner/` | Agent skill for structural validation and optional compiler checking |
| `tests/rocq/run_wiki_suite.py` | End-to-end smoke suite |

## Generate The Full Suite

```bash
python scripts/run_rocq_autoformalization.py \
  --manifest-file tests/latex/wiki_level/manifest.json \
  --output-dir MathformerRocq \
  --report-file artifacts/rocq/wiki_level_draft.json \
  --json
```

This generates five controlled examples:

- `AutoformalizedWikiContrapositive.v`
- `AutoformalizedWikiInjectiveComposition.v`
- `AutoformalizedWikiMonotoneComposition.v`
- `AutoformalizedWikiSetInterUnionDistrib.v`
- `AutoformalizedWikiSumFirstOddNumbers.v`

Each file contains:

- an SPDX and file-documentation header;
- source theorem/proof comments;
- minimal local definitions when needed;
- one complete theorem proof ending in `Qed.`;
- no `Admitted`, `admit`, `Axiom`, `Parameter`, or `Abort` placeholders.

## Generate One Case

```bash
python scripts/run_rocq_autoformalization.py \
  --latex-file tests/latex/wiki_level/injective_composition.tex \
  --case-id wiki_injective_composition \
  --output-file backends/rocq/MathformerRocq/AutoformalizedWikiInjectiveComposition.v \
  --report-file artifacts/rocq/wiki_injective_composition_draft.json \
  --json
```

Supported case ids are:

- `wiki_contrapositive`
- `wiki_injective_composition`
- `wiki_monotone_composition`
- `wiki_set_inter_union_distrib`
- `wiki_sum_first_odd_numbers`

## Validate Or Compile

Run validation over the committed Rocq corpus:

```bash
python skills/rocq/rocq-execution-runner/scripts/check_rocq_file.py \
  --path MathformerRocq \
  --report-file artifacts/rocq/wiki_level_execution.json \
  --json
```

The execution runner always performs structural proof-artifact checks. If Rocq
is installed, it prefers:

```bash
rocq compile backends/rocq/MathformerRocq/AutoformalizedWikiContrapositive.v
```

If only a legacy-compatible command is present, it falls back to:

```bash
coqc backends/rocq/MathformerRocq/AutoformalizedWikiContrapositive.v
```

Use `--require-compiler` when a missing compiler should fail:

```bash
python skills/rocq/rocq-execution-runner/scripts/check_rocq_file.py \
  --path MathformerRocq \
  --require-compiler \
  --json
```

## Test The Backend

```bash
python tests/rocq/run_wiki_suite.py --json
python tests/test_program/run_comprehensive_tests.py --module-family rocq --json
```

On machines without Rocq installed, these tests still pass if structural
validation succeeds. External execution is marked as skipped in the JSON report.

## Trust Model

The Rocq backend has two validation levels:

| Level | Meaning |
| --- | --- |
| Structural validation | The generated file has the expected theorem/proof shape, source comments, and no placeholder markers |
| Compiler validation | `rocq compile` or `coqc` accepts the `.v` file |

Structural validation is useful for local development and CI environments that
do not install every proof assistant. Compiler validation is stronger and should
be required before treating a Rocq artifact as externally checked.

## Extension Notes

Add new deterministic cases by extending `CASE_TEMPLATES` in
`backends/rocq/MathformerRocq/autoformalize.py`. Each new case should provide:

- a stable case id;
- a valid Rocq filename;
- the theorem name;
- required `From Stdlib Require Import ...` lines;
- local definitions, if any;
- a theorem statement;
- a complete proof;
- concept tags and source summary.

Then update `tests/rocq/run_wiki_suite.py` with the expected file and theorem
name, and rerun the Rocq smoke suite.
