---
name: mathlib-web-search-strategist
description: Plan targeted web searches for mathlib grounding when local concept mapping, hierarchy navigation, or Lean verification leaves unresolved candidates. Use to generate official-source query strings, source-priority strategy, and local verification handoff tasks that complement local mathlib search without replacing it.
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

# Mathlib Web Search Strategist

## Purpose

Use this skill when local mathlib search is inconclusive and a targeted web pass may
identify canonical declarations, modules, notation, or API conventions.

Hook:
- `mathlib.web_strategy`

This skill plans searches; it does not treat web hits as verified Lean facts.

## Workflow

1. Start from local evidence: concept map, hierarchy output, failed `#check`, import-context
   failure, coverage gap, or explicit concepts.
2. Run `scripts/plan_mathlib_web_search.py` to create a bounded search plan.
3. Search official sources first:
   - mathlib HTML documentation
   - `leanprover-community/mathlib4` source
   - Lean/mathlib official documentation when API conventions are needed
4. Use retrieval aids only to discover candidates, never as final evidence:
   - Loogle
   - LeanSearch
5. For every web-sourced API claim, create a local handoff:
   - `#check` expected declarations with `mathlib-candidate-verifier`
   - verify intended imports with `lean-import-context-verifier`
   - update import plans with `mathlib-import-set-builder`
6. Hand any gathered source packet to `mathlib-web-evidence-validator`.

## Commands

Plan from explicit concepts:

```bash
python3 skills/mathlib/mathlib-web-search-strategist/scripts/plan_mathlib_web_search.py \
  --concept monotone \
  --concept compactness \
  --json
```

Plan from a local concept-map or coverage report:

```bash
python3 skills/mathlib/mathlib-web-search-strategist/scripts/plan_mathlib_web_search.py \
  --local-map-json artifacts/mathlib/concept-map.json \
  --json
```

## References

- Read `references/source_policy.md` before doing actual web research or judging
  whether a web result is acceptable.
