---
name: mathlib-concept-ontology-manager
description: Manage reviewed Mathformer concept ontology profiles for mathlib mapping, including synonyms, phrase hints, preferred declarations, domain overlays, ambiguity gates, and profile validation. Use when concept policy should be edited, validated, or shared by mathlib indexing, term annotation, and candidate mapping skills.
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

# Mathlib Concept Ontology Manager

## Purpose

Use this skill to keep informal-to-mathlib concept policy out of Python source
and in a reviewed profile. The profile records surface terms, synonyms,
preferred declarations, likely Lean objects, domain tags, and ambiguity clues.

Runtime:
- `scripts/validate_concept_ontology.py`
- shared profile: `references/core.yaml`
- hook: `mathlib.ontology.validate`

## Workflow

1. Edit `references/core.yaml` when adding or revising concept policy.
2. Keep concepts conservative: probable annotations may guide search, but only
   Lean-verified declarations may guide final drafting.
3. Add negative context clues for overloaded terms.
4. Run the validator after every profile edit.
5. Add a deterministic regression fixture when a concept fixes a real mapping
   failure.

## Commands

```bash
python3 skills/mathlib/mathlib-concept-ontology-manager/scripts/validate_concept_ontology.py \
  --json
```

```bash
python3 skills/mathlib/mathlib-concept-ontology-manager/scripts/validate_concept_ontology.py \
  --profile skills/mathlib/mathlib-concept-ontology-manager/references/core.yaml \
  --json
```

## References

- Read `references/core.yaml` for the active concept profile.
