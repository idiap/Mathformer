<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

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

# Lean Execution Reference

## Direct File Execution

```bash
lake env lean backends/lean/Mathformer/AutoformalizedExample.lean
```

## Generated-Code Execution In AgentC

`HardCritiqueAgent` writes generated Lean code to a temporary or configured file and runs
the selected Lean backend. For Lean4 project execution, prefer:

- `lean_backend="lake_env"`
- `lean_workdir="."`

## Reasoning Payload Fields

The execution hook should preserve:

- `skill`: `lean-execution-runner`
- `hook_id`: `execute.initial`, `execute.saved_output`, or another execution hook id
- `file_prefix` or target file path
- `correctness`
- `details`
- `hard_feedback`
- `duration_ms`
- `lean_error_log_file`
- `lean_error_log`
- `result_realness_required`: true for saved/final artifacts
- `result_realness_report` when the final gate has already run

## Boundaries

- Use `lean-execution-runner` for running Lean.
- Use `lean-compile-checker` for structured compiler-health diagnostics.
- Use `lean-syntactic-correctness-critic` for the critique judgement over those diagnostics.
- Use `lean-formal-refinement` to change the Lean code.
- Use `autoformalization-result-realness-verifier` to decide whether a compiling artifact is complete or still a draft/blocked scaffold, including noisy legacy per-line source comments and syntax-only comments.
