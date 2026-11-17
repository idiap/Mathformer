---
name: rocq-execution-runner
description: Validate generated Rocq `.v` files structurally and type-check them with `rocq compile` or `coqc` when a compiler is available.
---

<!--
File Documentation

Motivation:
  Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

Intent:
  Tell agents how to distinguish a Rocq draft artifact from a checked or check-ready artifact.

Function:
  Documents the command that validates Rocq proof scripts and optionally invokes an installed compiler.

Maintenance Notes:
  Keep this skill synchronized with `skills/rocq/rocq-execution-runner/scripts/check_rocq_file.py`.
-->

# Rocq Execution Runner

Use this skill after `rocq-autoformalization-drafter`. The runner always checks
the local Mathformer Rocq artifact contract:

- SPDX and file documentation are present.
- A theorem/lemma/proposition is declared.
- `Proof.` and `Qed.` blocks are balanced.
- Placeholder markers such as `Admitted`, `admit`, `Axiom`, `Parameter`, and
  `Abort` are absent.
- Source-preservation comments are present.

If Rocq is installed, the runner prefers:

```bash
rocq compile path/to/file.v
```

and falls back to:

```bash
coqc path/to/file.v
```

Run the suite:

```bash
python skills/rocq/rocq-execution-runner/scripts/check_rocq_file.py \
  --path MathformerRocq \
  --report-file artifacts/rocq/wiki_level_execution.json \
  --json
```

Add `--require-compiler` when a missing compiler should fail the check instead
of being reported as a skipped external execution.
