<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make the framework understandable without requiring readers to inspect implementation details first.

Intent:
  Explain architecture, installation, principles, tutorials, licensing, and generated library outputs.

Function:
  Provides human-facing documentation that should stay aligned with tested behavior and code paths.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Mathformer Main Concepts

This document gives the conceptual map of Mathformer. For the framework
principles and trust rules, see [principles](PRINCIPLES.md); for implementation
details, see the [framework guide](FRAMEWORK.md); for the machine-readable
workflow contract, see the skill-hook manifest; for observed agent use and
convergence dynamics, see the [agent dynamics report](AGENT_DYNAMICS_REPORT.md).
For the backend-independent mapping from skills to epistemic primitives and
composite reasoning styles, see [epistemic reasoning types](EPISTEMIC_REASONING_TYPES.md).
For the distinction between candidates, evidence, assessments, decisions,
explanations, and their representations, see [epistemic output types](OUTPUT_TYPES.md).
For deterministic, generative, hybrid, procedural, declarative, and
orchestration classifications, see [skill types](SKILL_TYPES.md).
For the typed language that composes epistemic occurrences while conserving
handles, authority ceilings, and calibration, see the
[Epistemic Reasoning Flow Language](REASONING_FLOW_LANGUAGE.md).
For the line-by-line semantic catalogue of every canonical profile, see [all
Mathformer reasoning flows](ALL_REASONING_FLOWS.md). For candidate skill and
controlled-loop bindings, see the separate [reasoning-flow
materializations](REASONING_FLOW_MATERIALIZATIONS.md) cross-reference.

## 1. Project Goal

Mathformer is a controlled mathematics and physics formalization workspace with
Lean/mathlib, Vampire ATP, SymPy, Rocq, and Isabelle surfaces. Its main concern is
traceable reasoning and formalization attempts with source provenance, appropriate
library or premise grounding, executable evidence, consistency checks, and honest
status labels. Backend availability and acceptance checks differ by workflow.

The detailed source-object and textbook examples below focus on the Lean/mathlib
path. Read the [backend guides](../backends/) for ATP, symbolic computation, Rocq,
and physics-specific contracts; Lean-specific examples do not define the full scope
of the framework.

For the Lean/mathlib path, autoformalization follows this pipeline:

1. extract mathematical objects from a source,
2. expand and review their informal/LaTeX meaning,
3. search for existing mathlib or MathformerLib results,
4. draft Lean using mathlib-compatible interfaces,
5. run Lean and other deterministic gates,
6. refine when gates expose problems,
7. accept only artifacts with explicit evidence.

## 2. Source Objects

A source object is a mathematical unit extracted from a paper, wiki-style page,
book, or LaTeX archive.

Important object kinds:

- `definition`: introduces a concept, structure, predicate, notation, or class of
  objects.
- `theorem`, `lemma`, `proposition`, `corollary`: theorem-like claims that should
  become Lean declarations when possible.
- `assumption`, `condition`, `criterion`, `claim`: supporting formal context.
- `proof`: a proof environment paired to a theorem-like source object.
- `remark`, `example`, `exercise`: useful context, but not autoformalization
  targets by default.

Each extracted object should preserve:

- original LaTeX,
- source file and line span,
- labels and references,
- section/chapter context,
- paired proof ids when available.

For textbook archives, these objects are stored in `theory_units.json`.

## 3. Textbook Pipeline

The textbook pipeline handles large LaTeX archives object by object.

Core skills:

- `latex-archive-theory-extractor`: unpacks a LaTeX archive and extracts
  theorem-like environments and proofs with line provenance.
- `textbook-theory-tex-organizer`: groups extracted objects into coherent
  section/chapter TeX bundles.
- `textbook-autoformalization-batch-orchestrator`: builds and runs per-object
  autoformalization jobs.

Main artifacts:

- `theory_units.json`: extracted source objects.
- `organized/organized_manifest.json`: thematic TeX bundle index.
- `autoformalization_batch/batch_manifest.json`: queued jobs for statements and
  proofs.
- `object_runs/run_manifest.json`: aggregate object execution status.
- `object_runs/runs/<job-id>/result.json`: per-object generation and gate result.
- `object_runs/runs/<job-id>/*.lean`: generated Lean for objects that reached
  drafting.

The batch runner is resumable. It never marks an object complete unless the
configured gates pass.

## 4. Skills

A skill is a local, reusable capability under `skills/<name>/`. A skill usually
contains:

- `SKILL.md`: trigger and workflow instructions,
- `agents/openai.yaml`: user-facing metadata,
- `scripts/`: deterministic helper programs,
- `references/`: detailed prompt or policy material.

Skills split the workflow into small owners. Examples:

- extraction skills identify formalizable source objects,
- mathlib skills search, navigate, and verify library candidates,
- drafting/refinement skills generate and repair Lean,
- critique skills check syntax, semantics, logic, and mathlib alignment,
- consistency skills inspect final Lean from several reference-free angles,
- control skills validate hooks, logs, gates, and tests.

The prompt and skill ownership index lives in `skills/ALL_AGENT_SKILL_PROMPTS.md`.

## 5. Hooks and Loops

Hooks are the project's systematic control layer. They define which skill owns a
workflow phase, which reasoning-log events prove that phase ran, and which gate
condition must hold before downstream stages can trust the output.

The hook contract lives in `skills/SKILL_HOOKS.yaml`.

Important loop contracts:

- `preformalization_readiness_loop`: source extraction, proof support, LaTeX
  expansion review, and duplicate-result checks.
- `textbook_theory_autoformalization_loop`: textbook extraction, organization,
  job queueing, object execution, and standard Lean gates.
- `mathlib_grounding_loop`: concept search, hierarchy navigation, candidate
  verification, web evidence, import planning, and API hinting.
- `draft_execute_refine_loop`: generation, Lean execution, critiques, refinement,
  denoising, and transition taxonomy.
- `artifact_acceptance_loop`: import minimization, reverse informalization,
  non-vacuity, cross-file consistency, realness, unified report, and statistics.
- `reflection_testing_loop`: monotonic skill improvement plus regression tests.

Hook validators make sure new skills do not become unreachable side paths.

## 6. Gates and Statuses

Gates turn heterogeneous checks into explicit pass/fail evidence. A gate can pass,
warn, fail, skip, or be waived with justification, depending on the phase.

Common gates:

- Lean execution and compile checks,
- source-comment hygiene,
- realness checks against mocks, placeholders, `sorry`, `admit`, target `axiom`,
  and scaffold-only completion claims,
- mathlib grounding and import-context checks,
- reverse informalization consistency,
- declaration-shape consistency,
- proof internal consistency,
- non-vacuity checks,
- cross-file concept consistency,
- unified Lean consistency report.

Important artifact statuses:

- `queued_autoformalization`: a statement/definition job is ready but not run.
- `queued_proof_autoformalization`: a paired proof job is ready but not run.
- `complete`: generated Lean passed the configured gates.
- `draft_failed_gates`: Lean was generated but at least one configured gate failed.
- `blocked_generation`: generation did not produce usable Lean, timed out, or
  refused for a substantive reason.
- `blocked_no_generative_provider`: no usable LLM/Codex provider was available.
- `support_only`: source material is useful context but not a standalone target.

The status vocabulary is deliberately conservative. A failed gate is progress:
it localizes the next refinement target without pretending success.

## 7. Mathlib Grounding

Mathformer tries to maximize use of existing mathlib rather than creating
parallel abstractions.

Grounding includes:

- extracting informal concepts from the source,
- ranking candidate mathlib declarations and modules,
- using Lean `#check` to verify candidates,
- navigating module hierarchies and declaration neighborhoods,
- planning narrow imports,
- validating web-sourced mathlib claims against official docs/source,
- re-checking generated Lean under intended imports,
- minimizing broad or duplicate imports after generation.

When mathlib lacks a source concept, the preferred pattern is to isolate the gap
behind one explicit abstraction boundary, document that boundary, and keep the
rest of the artifact mathlib-native.

## 8. MathformerLib

`MathformerLib` is the curated parallel library for reusable formalizations that
are not yet in mathlib or that serve as local project support.

Promotion into MathformerLib requires:

- realness checks,
- compile checks when requested,
- registry updates,
- no placeholder or scaffold markers for accepted entries.

The registry tracks modules, declarations, imports, provenance, and statuses
such as `draft`, `candidate`, and `accepted`.

## 9. Reference-Free Consistency

Many generated Lean files do not have a gold benchmark formalization. Mathformer
therefore uses reference-free signals:

- does the Lean compile?
- are source comments present and semantically meaningful?
- does reverse informalization match the source shape?
- are theorem statements non-vacuous?
- are repeated concepts named and shaped consistently across files?
- is mathlib grounding improving or at least non-regressing?
- do critic measures identify unresolved risk?

These measures do not prove mathematical correctness by themselves. They provide
a monotonic control signal for refinement and prevent obvious false positives.

## 10. Reasoning Logs and Reports

Workflow runs should leave machine-readable evidence.

Common evidence files:

- reasoning logs: JSONL events with hook ids, timestamps, and payloads,
- agent usage instrumentation: each new event records which agent/skill was used,
  where it was used, and the hook or payload criteria used to judge convergence,
- history files: refinement states and transition taxonomy,
- report files: final workflow and gate outcomes,
- consistency reports: per-layer blockers and scores,
- statistics files: run timing and summary metrics,
- object run results: one `result.json` per textbook object.

This makes the process auditable: users can inspect not only the final Lean file
but also why it was accepted, drafted, or blocked.

## 11. Development Checks

Use these checks after changing skills, hooks, or workflow scripts:

```bash
python3 skills/control/workflow-contract-validator/scripts/validate_skill_hooks.py --strict --json
python3 skills/control/skill-hook-coverage-maximizer/scripts/audit_skill_hook_coverage.py --expect-ok --json
python3 skills/control/skill-test-program-orchestrator/scripts/run_deterministic_skill_tests.py --json
git diff --check
```

Use `lake build Mathformer` or narrower `lake env lean <file>` checks when Lean
source files change.
