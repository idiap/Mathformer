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

# ProofNet Benchmark Integration

This folder integrates the benchmark dataset:

- Dataset: `hoskinson-center/proofnet`
- Source: <https://huggingface.co/datasets/hoskinson-center/proofnet>

## Notes

- ProofNet formal statements are in Lean 3.
- This repository is configured for Lean 4 + mathlib.
- If you benchmark autoformalization here, treat outputs as Lean 3 targets unless you add a Lean3->Lean4 translation stage.

## Download

From repository root:

```bash
python benchmarks/proofnet/proofnet.py download --output data/benchmarks/proofnet
```

By default, Hugging Face cache files are written inside `data/benchmarks/proofnet/.hf_cache`.

## Inspect Stats / Samples

```bash
python benchmarks/proofnet/proofnet.py stats --output data/benchmarks/proofnet
python benchmarks/proofnet/proofnet.py sample --output data/benchmarks/proofnet --split validation -n 2
```

## Export Model Inputs

```bash
python benchmarks/proofnet/proofnet.py export-inputs \
  --output data/benchmarks/proofnet \
  --split validation \
  --output-file data/benchmarks/proofnet/validation_inputs.jsonl \
  --formal-language Lean3
```

The exported file contains one JSON record per problem with:

- `id`
- `split`
- `nl_statement`
- `prompt`

## Evaluate Predictions

Prediction JSONL format (one row per predicted item):

```json
{"id": "...", "pred_formal_statement": "..."}
```

Evaluation command:

```bash
python benchmarks/proofnet/evaluate_predictions.py \
  --gold-dir data/benchmarks/proofnet \
  --split validation \
  --predictions-file inputs/predictions.jsonl \
  --summary-only
```

Metrics include coverage, exact match, and whitespace-normalized exact match.
