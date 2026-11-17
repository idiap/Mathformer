---
name: proofnet-benchmark-runner
description: Download, export, and evaluate ProofNet benchmark inputs and prediction files for Lean/Isabelle autoformalization experiments. Use when preparing ProofNet data, generating validation/test inputs, or summarizing benchmark prediction accuracy.
---
<!--
File Documentation

Motivation:
  Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

Intent:
  Tell coding agents what context to load, what invariants to preserve, and how to validate their work.

Function:
  Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# ProofNet Benchmark Runner

## Purpose

Use this skill for benchmark data and evaluation commands only. Formalization workflow
execution belongs to `autoformalization-workflow-orchestrator`.

## Commands

Download ProofNet data:

```bash
python3 benchmarks/proofnet/proofnet.py download --output data/benchmarks/proofnet
```

Export validation inputs:

```bash
python3 benchmarks/proofnet/proofnet.py export-inputs \
  --output data/benchmarks/proofnet \
  --split validation \
  --output-file data/benchmarks/proofnet/validation_inputs.jsonl \
  --formal-language Lean3
```

Evaluate predictions:

```bash
python3 benchmarks/proofnet/evaluate_predictions.py \
  --gold-dir data/benchmarks/proofnet \
  --split validation \
  --predictions-file inputs/predictions.jsonl \
  --summary-only
```

## Notes

- Keep prediction files in JSONL format expected by `evaluate_predictions.py`.
- Match `--formal-language` to the generated target language and ProofNet split.
