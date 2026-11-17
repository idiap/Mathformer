---
name: textbook-autoformalization-batch-orchestrator
description: Build an honest per-unit autoformalization job queue from organized textbook theory bundles, preserving source TeX, paired proofs, thematic context, mathlib/realness/consistency gate requirements, and preventing mocked completed Lean results.
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

# Textbook Autoformalization Batch Orchestrator

Use this skill after textbook theory units have been extracted and organized. It creates
one job packet per formalizable target and prompt files that route each job through the
standard autoformalization workflow.

## Workflow

1. Load `theory_units.json` and `organized_manifest.json`.
2. Build queued jobs for definitions, theorem-like results, assumptions, claims, notation,
   and criteria. Attach paired proofs when present.
3. Attach a `line_translation_packet` to each job so the generated Lean can cite
   literal `src_L####` anchors from the statement/proof text.
4. Emit a separate queued proof-obligation job for every paired proof environment so
   proof work is tracked explicitly.
5. Feed each job to `autoformalization-workflow-orchestrator`.
6. Mark a job `complete` only after Lean execution, source-anchor drift, realness, grounding, and consistency
   gates pass. Queued jobs are not completed formalizations.
7. To execute jobs object by object, run `scripts/run_textbook_autoformalization_batch.py`.
   Prefer `--provider codex-cli` when the Codex CLI is authenticated. Use `--max-jobs`
   and `--start-at` for shards; the run manifest is resumable.

## Command

```bash
python3 skills/latex-textbook/textbook-autoformalization-batch-orchestrator/scripts/build_textbook_autoformalization_batch.py \
  --theory-units-json artifacts/textbook_theory/example/theory_units.json \
  --organized-manifest artifacts/textbook_theory/example/organized/organized_manifest.json \
  --output-dir artifacts/textbook_theory/example/autoformalization_batch \
  --json
```

```bash
python3 skills/latex-textbook/textbook-autoformalization-batch-orchestrator/scripts/run_textbook_autoformalization_batch.py \
  --batch-manifest artifacts/textbook_theory/example/autoformalization_batch/batch_manifest.json \
  --output-dir artifacts/textbook_theory/example/object_runs \
  --provider codex-cli \
  --max-jobs 1 \
  --json
```

## Contract

- Do not write Lean placeholders, mock proofs, `sorry`, `admit`, or target axioms.
- Emit `queued_autoformalization` and `queued_proof_autoformalization` jobs with required gate metadata.
- Preserve original statement TeX and paired proof TeX separately.
- Preserve `line_translation_packet.lean_prompt_context` and require source-backed declarations to cite `Source anchors: ...`.
- Keep unsupported standalone proofs as `support_only`; do not autoformalize them as claims.
- The runner must write one `result.json` per job and a top-level `run_manifest.json`.
  Status is `complete` only when the generated Lean passes the configured gates; otherwise
  use `draft_failed_gates`, `blocked_generation`, or `blocked_no_generative_provider`.
