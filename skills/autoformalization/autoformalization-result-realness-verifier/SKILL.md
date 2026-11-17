---
name: autoformalization-result-realness-verifier
description: Verify that saved autoformalization artifacts and reports are real final results rather than mocks, stubs, planned outputs, unexecuted drafts, `sorry`/`axiom` placeholders, legacy per-line NL/LaTeX comment spam, missing semantic declaration comments, or interface scaffolds presented as completed theorem proofs. Use before final artifact statistics, reports, release gates, or any claim that an autoformalization result is complete.
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

# Autoformalization Result Realness Verifier

## Purpose

Use this skill as the final realness gate for Mathformer autoformalization outputs.
It prevents provisional artifacts from becoming reported successes when they still
contain mocked results, unexecuted states, `sorry`/`admit`, target `axiom`s, fake
declarations, legacy per-line `NL/LaTeX:` comments, missing source-aware declaration
comments, or interface scaffolds that are not explicitly labeled as draft.

This skill does not forbid honest scaffolding during exploration. It forbids
claiming scaffolded or mocked content as a completed autoformalization result.

## Workflow

1. Run after initial execution, each saved Lean artifact, post-save critique, and
   before final statistics/report publication.
2. Scan the `.lean` file and any `.report.json`/`.history.json` artifacts.
3. Treat placeholders, mock markers, legacy per-line `NL/LaTeX:` comments, comments on purely syntactic Lean lines, and missing semantic declaration comments as blocking for `--artifact-status final`.
4. If an artifact is intentionally partial, mark it `--artifact-status draft` and
   report it as blocked/partial, not complete.
5. Route blocking findings to `lean-formal-refinement`, `lean-compile-checker`,
   `mathlib-abstraction-auditor`, or the workflow orchestrator depending on the
   finding.

## Commands

Final gate for a Lean artifact:

```bash
python3 skills/autoformalization/autoformalization-result-realness-verifier/scripts/verify_artifact_realness.py \
  --lean-file backends/lean/Mathformer/AutoformalizedSazonov.lean \
  --artifact-status final \
  --json
```

Report-aware gate:

```bash
python3 skills/autoformalization/autoformalization-result-realness-verifier/scripts/verify_artifact_realness.py \
  --lean-file backends/lean/Mathformer/AutoformalizedSazonov.lean \
  --report-file artifacts/autoformalization/sazonov.report.json \
  --history-file artifacts/autoformalization/sazonov.history.json \
  --artifact-status final \
  --json
```

Expected-failure regression check:

```bash
python3 skills/autoformalization/autoformalization-result-realness-verifier/scripts/verify_artifact_realness.py \
  --text "theorem t : True := by sorry" \
  --name mocked_sorry \
  --expect-blocking \
  --json
```

## References

- Read `references/realness_gate.md` when deciding whether a partial result is an
  honest draft, a blocked artifact, or a completed result.
