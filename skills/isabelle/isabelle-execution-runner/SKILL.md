---
name: isabelle-execution-runner
description: Execute generated Isabelle/HOL `.thy` files through the local Isabelle command, usually with `isabelle build -D`, and capture return codes, diagnostics, placeholder checks, session ROOT creation guidance, and JSON reports. Use immediately after an Isabelle autoformalization draft is delivered.
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

# Isabelle Execution Runner

## Purpose

Use this skill for concrete Isabelle theorem-prover health. It is the Isabelle
counterpart of `lean-execution-runner`.

## Workflow

1. Receive a `.thy` file or a directory containing Isabelle theories.
2. Locate Isabelle using `--isabelle-bin`, `ISABELLE_BIN`, or `PATH`.
3. Ensure the checked directory has a `ROOT` session file.
4. Run `isabelle build -D <directory>`.
5. Capture return code, stdout/stderr, elapsed time, theory names, and placeholder
   indicators such as `sorry` or `oops`.
6. Route generic Isabelle failures to `isabelle-autoformalization-drafter` and
   physics failures to `physics-isabelle-derivation-drafter` or the active
   physics refinement loop.
7. Do not treat a successful process as final if placeholders remain.

## Command

```bash
python3 skills/isabelle/isabelle-execution-runner/scripts/check_isabelle_theory.py \
  --theory-file backends/isabelle/Isabelle/AutoformalizedWikiInjectiveComposition.thy \
  --session-dir Isabelle \
  --json
```
