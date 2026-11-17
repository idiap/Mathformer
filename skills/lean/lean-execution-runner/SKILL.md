---
name: lean-execution-runner
description: Execute generated Lean4 code or `.lean` files in the local Lake project with `lake env lean`, capturing return code, stdout/stderr, diagnostics, and error-log artifacts. Use immediately after an initial Lean formalization is delivered, or whenever the task is to run Lean rather than critique or refine the result.
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

# Lean Execution Runner

## Purpose

Use this skill for the execution act: running Lean on generated code or a saved Lean file in
the project environment. It sits between initial drafting and critique/refinement.

Shared runtime owners:
- `../autoformalization-agentc/scripts/agentc.py` via `HardCritiqueAgent`
- direct CLI: `lake env lean <file>.lean`

## Workflow

1. Receive generated Lean code or a target `.lean` file.
2. Execute it in the intended Lake workdir with the local `.elan` toolchain on `PATH`.
3. Capture return code, stdout, stderr, Lean error lines, and any generated error-log file.
4. Emit reasoning-log payloads with `skill: lean-execution-runner` and the matching `hook_id`.
5. Hand diagnostics to `lean-compile-checker`, `lean-syntactic-correctness-critic`, or `lean-formal-refinement`.
6. Do not interpret a zero Lean return code as final success when the artifact still contains placeholders, mocks, legacy per-line `NL/LaTeX:` comments, noisy syntax-only comments, missing semantic declaration comments, or scaffold-only claims; run `autoformalization-result-realness-verifier` before final publication.

## Initial Formalization Hook

After `lean-autoformalization-drafter` emits `autoformalizer_initial_output`, the workflow
must run the initial Lean execution hook before deciding whether refinement is needed:

- hook id: `execute.initial`
- expected events: `lean_execution_initial_start`, `lean_execution_initial_output`
- downstream diagnostic events may also be emitted as hard-critique/compile-check events.
- final acceptance requires the later `artifact.realness_gate` hook, not merely this execution hook.

## References

- Read `references/execution.md` for command forms and expected payload fields.
