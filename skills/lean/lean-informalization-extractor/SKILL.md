---
name: lean-informalization-extractor
description: Extract structured informal statements and proof narratives from final Lean4 files, preserving source-aware comments, theorem signatures, proof bodies, tactic summaries, dependencies, and unresolved-risk signals. Use after Lean artifacts compile and before consistency verification or human review.
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

# Lean Informalization Extractor

## Purpose

Use this skill to read final Lean files in the reverse direction: Lean source to
structured informal statement/proof packets. The output should say what the
artifact actually proves or defines, based on signatures, source-aware doc
comments, proof terms/tactics, imports, and local dependencies.

This skill does not certify mathematical correctness by itself. It creates the
evidence packet consumed by `lean-informal-consistency-verifier`.

## Workflow

1. Run `scripts/extract_lean_informalization.py` on each final Lean file.
2. Preserve original-source natural-language and LaTeX comments separately from
   generated notes.
3. For each declaration, extract the Lean kind, name, line, signature, local doc
   comment, proof segment, tactic keywords, and probable dependencies.
4. Produce a concise informal statement and proof summary that is faithful to
   the Lean artifact. Do not fill missing proof ideas with external knowledge.
5. Mark missing doc comments, placeholders, target axioms, and proof bodies that
   only delegate to a hypothesis as explicit findings.
6. Send the packet to `lean-informal-consistency-verifier` before accepting the
   artifact as semantically stable.

## Command

```bash
python3 skills/lean/lean-informalization-extractor/scripts/extract_lean_informalization.py \
  --lean-file backends/lean/Mathformer/AutoformalizedTransformerScalingLaws.lean \
  --json
```

## References

- Read `references/informalization_contract.md` before changing extraction
  fields, proof-summary categories, or downstream consistency semantics.
