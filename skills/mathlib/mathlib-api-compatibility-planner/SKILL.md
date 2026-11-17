---
name: mathlib-api-compatibility-planner
description: Build drafting and refinement hints that maximize use of verified mathlib declarations, imports, native predicates, typeclasses, and abstraction boundaries. Use after concept coverage review and before Lean drafting or refinement to make all concepts as mathlib-compatible as possible.
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

# Mathlib API Compatibility Planner

## Purpose

Use this skill to transform concept maps and coverage gaps into prompt-ready Lean API
guidance. The goal is maximum mathlib reuse before any local abstraction is introduced.

Shared runtime owner:
- `../autoformalization-agentc/scripts/agentc.py`
- functions: `format_mathlib_alignment_hints`, `format_mathlib_concept_coverage_hints`
- hook: `mathlib.api_plan`

## Workflow

1. Prefer verified `check_ok: true` declarations over unverified candidates.
2. Include imports, source references, and qualified names when available.
3. For unverified or unmapped concepts, name the gap and suggest closest candidate imports.
4. Instruct the drafter to keep mathlib-native notions concrete.
5. Permit local abstractions only at one explicit, documented boundary for genuinely missing concepts.
6. Use `mathlib-hierarchy-navigator` output to prefer imports from the narrowest coherent module family.
7. When an import plan is available, use the verified planned imports rather than broad `import Mathlib`.

## References

- Read `references/api_plan.md` for the planning order and anti-duplication rules.
