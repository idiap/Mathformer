---
name: lean-informal-proof-internal-consistency-verifier
description: Evaluate the internal consistency of informalized Lean proof packets, checking that extracted informal statements, proof summaries, dependencies, proof-shape evidence, and warning signals cohere before source/Lean round-trip consistency is trusted. Use after lean-informalization-extractor and before final informal-consistency acceptance.
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

# Lean Informal Proof Internal Consistency Verifier

## Purpose

Use this skill after `lean-informalization-extractor` produces a reverse
informalization packet. It checks whether the extracted informal proof is
coherent on its own, before comparing it to the original source or to broader
semantic critics.

This is a reference-free internal audit. It does not prove the theorem; it
checks whether the informalized proof packet is self-consistent enough to use as
evidence.

## Workflow

1. Run `scripts/verify_informal_proof_internal_consistency.py`.
2. Provide either saved Lean files or an extractor JSON report.
3. For every theorem-like declaration, check statement/proof-summary presence,
   proof-shape evidence, dependency/circularity, placeholders, hidden hypothesis
   delegation, and contradiction-prone wording.
4. Treat high-severity findings as blockers for final artifact acceptance.
5. Feed blockers to `lean-informalization-extractor`,
   `lean-informal-consistency-verifier`, `lean-semantic-preservation-critic`, or
   `lean-logical-soundness-critic` depending on the failure.

## Commands

Run from Lean files:

```bash
python3 skills/lean/lean-informal-proof-internal-consistency-verifier/scripts/verify_informal_proof_internal_consistency.py \
  --lean-file backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean \
  --expect-ok \
  --json
```

Run from a saved extractor packet:

```bash
python3 skills/lean/lean-informal-proof-internal-consistency-verifier/scripts/verify_informal_proof_internal_consistency.py \
  --informalization-report artifacts/informalization/latest.json \
  --json
```

## References

- Read `references/internal_consistency_policy.md` before changing blocker
  semantics, proof-shape heuristics, or score weights.
