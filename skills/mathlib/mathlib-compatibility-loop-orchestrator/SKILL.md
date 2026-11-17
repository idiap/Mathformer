---
name: mathlib-compatibility-loop-orchestrator
description: Coordinate loops that maximize mathlib compatibility across concept discovery, candidate verification, coverage review, API planning, drafting/refinement, and post-save compatibility auditing. Use when all concepts should be pushed toward verified mathlib declarations and compatibility-score targets.
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

# Mathlib Compatibility Loop Orchestrator

## Purpose

Use this skill when mathlib compatibility is a gate, not a suggestion. It coordinates the
pre-draft concept loop and the post-save compatibility audit loop.

Shared runtime owner:
- `../autoformalization-agentc/scripts/agentc.py`
- function: `run_mathlib_concept_compatibility_loop`
- hooks: `mathlib.compatibility_loop`, `audit.compatibility`

## Workflow

1. Run concept discovery and verification.
2. Review coverage with `mathlib-concept-coverage-reviewer`.
3. If not all concepts are verified, widen candidate and verification breadth for bounded rounds.
4. Build and verify a narrow import plan with `mathlib-import-set-builder` and `lean-import-context-verifier`.
5. Build coverage-aware drafting hints with `mathlib-api-compatibility-planner`.
6. After Lean output is saved, run `mathlib-import-minimizer` and `mathlib-abstraction-auditor`.
7. Continue outer compatibility cycles until the target score is met or the cycle cap is reached.

## References

- Read `references/loop.md` for loop events, stopping conditions, and failure handling.
