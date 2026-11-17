<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Keep external benchmark adapters isolated from core framework code.

Intent:
  Represent benchmark loading, evaluation, and documentation conventions clearly for repeatable experiments.

Function:
  Defines adapters and notes for benchmark families used in evaluation workflows.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# FormalScience Physics Benchmark Integration

This folder integrates the source-side physics benchmark from:

- Repository: `jmeadows17/formal-science`
- Source: <https://github.com/jmeadows17/formal-science>

The upstream repository contains generated formal artifacts. For Mathformer's
first-pass experiment, those formal answers are intentionally withheld. The
export command below emits only the informal `question` and `answer` fields from
`data/FormalPhysics.json`, plus metadata and a deterministic complexity score.

## Download And Inspect

From repository root:

```bash
python benchmarks/formal_science/formal_science.py download --output data/benchmarks/formal_science
python benchmarks/formal_science/formal_science.py stats --output data/benchmarks/formal_science
python benchmarks/formal_science/formal_science.py rank --output data/benchmarks/formal_science -n 10
```

## Export The Initial Informal Sample

```bash
python benchmarks/formal_science/formal_science.py export-informal-sample \
  --output data/benchmarks/formal_science \
  --sample-size 10 \
  --output-file data/benchmarks/formal_science/physics_top10_informal.jsonl \
  --bundle-dir data/benchmarks/formal_science/physics_top10_sources
```

The JSONL rows include:

- `id`
- `rank`
- `source_index`
- `field`
- `question`
- `answer`
- `source_text`
- `source_sha256`
- `complexity`
- `withheld_fields`

They do not include `formal_answer`.

## Complexity Ranking

The initial ranking is a deterministic source-text heuristic. It combines
character count, answer line count, LaTeX command count, inline/display math
count, and physics derivation signals such as derivatives, integrals,
Hamiltonians, Lagrangians, Fourier transforms, Poisson equations, and Maxwell
relations.

This is a selection rule, not an evaluation metric. It is meant to pick a hard
10-example sample for informal-first formalization.
