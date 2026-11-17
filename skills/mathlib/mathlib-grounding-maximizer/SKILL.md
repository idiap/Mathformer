---
name: mathlib-grounding-maximizer
description: Coordinate repeated loops that maximize mathlib grounding for generated Lean artifacts across narrow imports, native API reuse, concept coverage, web-backed mathlib evidence, scaffold removal, compatibility scores, and reference-free monotonicity. Use when a Lean file or set of autoformalized files should be pushed from merely compiling toward maximally mathlib-compatible formalizations.
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

# Mathlib Grounding Maximizer

## Purpose

Use this skill when "mathlib compatible" means more than "the file compiles". It coordinates
bounded refinement loops over saved Lean artifacts until the artifact is either maximally
grounded or honestly marked draft/blocked with concrete gaps.

It owns the cross-file grounding gate. Lower-level work remains owned by:

- `mathlib-compatibility-loop-orchestrator`
- `mathlib-web-grounding-orchestrator`
- `mathlib-import-minimizer`
- `lean-import-context-verifier`
- `mathlib-abstraction-auditor`
- `autoformalization-result-realness-verifier`
- `reference-free-critic-monitor`

## Workflow

1. Measure every target Lean file with `scripts/maximize_mathlib_grounding.py`.
2. Run the import loop first: remove broad `import Mathlib`, deduplicate imports, and verify the file still checks under the narrower block.
3. Run the native API loop: map custom concepts to verified mathlib declarations, inspect module/declaration neighborhoods, and replace avoidable local duplicates.
4. Run the web grounding loop only for unresolved local gaps, and accept web evidence only after official-source corroboration plus local Lean verification.
5. Run the scaffold/realness loop: remove scaffold language, mock/planned markers, weak interface-only claims, and missing semantic declaration comments before final status.
6. Run compatibility, source-comment, realness, and reference-free critic gates after each refinement round.
7. Accept a refinement only when hard risks do not increase, source-anchor/theorem surfaces do not shrink without semantic justification, and grounding measures are nondecreasing.

## Commands

Audit a set of artifacts and emit prioritized fixes:

```bash
python3 skills/mathlib/mathlib-grounding-maximizer/scripts/maximize_mathlib_grounding.py \
  --lean-file backends/lean/Mathformer/AutoformalizedSazonov.lean \
  --lean-file backends/lean/Mathformer/AutoformalizedRepresenterTheorem.lean \
  --json
```

Include local Lean checks inside compatibility audits:

```bash
python3 skills/mathlib/mathlib-grounding-maximizer/scripts/maximize_mathlib_grounding.py \
  --lean-file backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean \
  --run-lake-check \
  --expect-ok \
  --json
```

## References

- Read `references/maximization_loop.md` when interpreting loop outputs, choosing the next fix, or deciding whether a gap should remain an explicit abstraction boundary.
