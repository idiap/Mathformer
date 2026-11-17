---
name: lean-informal-consistency-verifier
description: Verify proof consistency by informalizing final Lean files, comparing the reverse informalization against source-aware comments, proof bodies, placeholder/non-vacuity signals, realness checks, and optional Lean compilation. Use as a post-formalization acceptance gate after Lean files compile.
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

# Lean Informal Consistency Verifier

## Purpose

Use this skill after final Lean files have been saved. It runs a reverse pass:

1. informalize the Lean artifact with `lean-informalization-extractor`;
2. require `lean-informal-proof-internal-consistency-verifier` to pass or
   provide nonblocking advisory findings only;
3. compare that extracted statement/proof packet with source comments and proof
   features;
4. combine the result with realness and optional compiler checks;
5. block final acceptance when the reverse pass exposes an unsupported proof,
   missing source alignment, placeholder, target axiom, or obvious statement drift.

The verifier is reference-free: it does not require a gold formalization. It is
also conservative: a pass means no configured inconsistency was found, not that
the mathematical theorem has been independently proved outside Lean.

## Workflow

1. Run `scripts/verify_informal_consistency.py` on the target Lean files.
2. Require an informalization packet for every theorem-like declaration.
3. Check that source comments and generated notes align with the Lean signature.
4. Flag theorem proofs that only delegate to a hypothesis, especially when the
   delegation is not described as an explicit criterion, model component, or
   external theorem boundary.
5. Run the realness gate and, when requested, `lake env lean` on each file.
6. Route blocking findings to `lean-formal-refinement`,
   `lean-semantic-preservation-critic`, or `lean-logical-soundness-critic`.

## Command

```bash
python3 skills/lean/lean-informal-consistency-verifier/scripts/verify_informal_consistency.py \
  --lean-file backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean \
  --run-lean-check \
  --expect-ok \
  --json
```

## References

- Read `references/consistency_policy.md` before changing blocking criteria or
  round-trip semantic checks.
