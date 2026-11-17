---
name: lean-semantic-preservation-critic
description: Critique whether a Lean4 formalization preserves the mathematical meaning of the original informal statement or proof. Use when comparing source assumptions, definitions, quantifiers, domains, conclusions, dependency context, and source-aligned doc comments against generated Lean code.
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

# Lean Semantic Preservation Critic

## Purpose

Use this skill for source-to-formalization meaning preservation. It is a semantic critique,
not a compile check and not a proof-completion check.

Shared runtime owner:
- `../autoformalization-agentc/scripts/agentc.py`
- class: `SoftCritiqueAgent`

## Workflow

1. Compare the informal source statement/proof to the Lean theorem statements and definitions.
2. Check quantifiers, domains, hypotheses, conclusions, equivalences/implications, constants, and hidden assumptions.
3. Use source-aligned doc comments and dependency context as evidence, not as a substitute for Lean statements.
4. Mark failures when the Lean statement is materially weaker, stronger, vacuous, scoped to the wrong objects, or omits a core conclusion.
5. Send failures to `lean-formal-refinement` as semantic realignment feedback.

## References

- Read `references/critique.md` for the pass prompt and preservation checklist.
