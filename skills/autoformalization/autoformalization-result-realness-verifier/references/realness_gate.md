<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

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

# Result Realness Gate

## Gate Rule

A final autoformalization result must be executable, report-backed, readable,
and free of mock or placeholder claims. A draft may contain unresolved
scaffold boundaries only when the artifact and report clearly say it is partial.

## Blocking In Final Artifacts

- `sorry`, `admit`, proof holes, tactic suggestions such as `exact?`, or target
  theorem proofs replaced by placeholders.
- `axiom` declarations that assert theorem content or bypass missing APIs.
- Text markers such as mock, stub, fake, simulated, placeholder, TODO, or FIXME.
- Report states indicating planned, skipped, unexecuted, mocked, simulated, or
  failed execution while the result is still reported as complete.
- Legacy per-line `NL/LaTeX:` comments, syntax-only separator comments, or
  trailing comments on purely syntactic Lean lines.
- Missing or thin declaration comments for generated Lean declarations. Final
  artifacts should preserve original-source `Natural language`/`LaTeX`
  equivalents when available, and should mark generated support declarations
  with `Generated note` or `Generated equivalent` comments.
- Interface scaffold language such as "intentionally abstract" or "abstract
  boundary" when the artifact is being published as final rather than draft.

## Allowed In Draft Artifacts

- Honest interface scaffolds that are explicitly labeled as draft or partial.
- Explicit unresolved gaps that are surfaced in the report and routed to a next
  refinement, mathlib compatibility, or research-support action.
- First-pass declarations with `sorry` only when the result is not counted as
  complete and the next required hook is refinement or final realness failure.

## Handoff

- Proof placeholders route to `lean-formal-refinement`.
- Lean execution failures route to `lean-execution-runner` and `lean-compile-checker`.
- Mocked or simulated report states route to `autoformalization-workflow-orchestrator`.
- Noisy or underspecified generated comments route to `lean-line-annotation`
  and then back through drafting/refinement.
- Mathlib abstraction placeholders route to `mathlib-abstraction-auditor` and
  `mathlib-compatibility-loop-orchestrator`.
