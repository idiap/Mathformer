<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Explain Mathformer as controlled agentic autoformalization rather than as a
  collection of scripts or backend demos.

Intent:
  State the principles that govern source-anchored generation, backend
  validation, reflective refinement, and loop-level accountability.

Function:
  Provides the conceptual contract for Mathformer users and maintainers. It
  summarizes the framework-paper model in natural language and points to the
  critical loop contracts that make the model operational.

Maintenance Notes:
  Keep this document aligned with `paper/MATHFORMER_FRAMEWORK_PAPER.tex`,
  `paper/REFERENCE_FREE_REFINEMENT_DYNAMICS.tex`, and
  `skills/SKILL_HOOKS.yaml`.
-->

# Mathformer Principles

Mathformer’s principle is controlled epistemic tightening: every loop should
leave the artifact with fewer ways to be wrong, or else produce a precise
blocker that explains why progress stopped.

The platform is deliberately reference-free in its core evaluation model: it can
measure formalization progress without a gold target by combining source
anchors, backend execution, critic agreement, non-vacuity checks, grounding
evidence, and artifact-realness signals.

Mathformer is a framework for controlled agentic autoformalization. The central
idea is not that an agent writes formal mathematics once and we trust it. The
central idea is that an agent proposes, executes, criticizes, repairs, observes,
and reflects inside a controlled loop.

The framework paper models an autoformalization run as a trajectory of states
rather than a single answer: source text, formalizable units, current formal
artifact, library grounding, critic reports, reverse informalization, obligation
ledger, metrics, and cost trace evolve together. See the
[framework paper](../../paper/MATHFORMER_FRAMEWORK_PAPER.tex) and the
[reference-free dynamics paper](../../paper/REFERENCE_FREE_REFINEMENT_DYNAMICS.tex)
for the formal model.

The short version: Mathformer is generative in proposal space, but controlled in
acceptance space.

## Core Model

An agentic formalization run is a controlled trajectory:

```text
source -> extraction -> grounding -> draft -> execution -> critique -> repair -> acceptance
```

The trajectory may use generative agents, deterministic scripts, theorem
provers, symbolic executors, web-grounded evidence, and human-readable reports.
Those components do not have the same authority. A generated draft is a
proposal. A compiler result is evidence. A critic finding is a localized risk.
A curation status controls reuse.

Every transition should answer four questions:

1. What source claim is being preserved?
2. Which agent, skill, or hook owns this step?
3. Which artifact or report records the evidence?
4. Which validation gate decides whether the step may be accepted?

## Principles

### 1. Source Anchors Come First

Autoformalization begins with a source claim: a theorem, proof sketch, paper
excerpt, physics derivation, or named mathematical fact. The source must remain
visible through the run.

Source anchors protect against statement drift. A backend can only check the
formal object it receives; a successful proof of the wrong formal object is not
a success for the original claim.

### 2. Proposals Are Cheap, Acceptance Is Expensive

Agents may generate theorem statements, definitions, helper lemmas, proof
scripts, assumptions, symbolic traces, and natural-language explanations. These
are proposals until evidence changes their status.

Acceptance requires hard gates: parser or compiler execution when relevant,
absence of placeholders, source-anchor validity, non-vacuity, dependency
grounding, consistency reports, and no unresolved blocking critic findings.

### 3. Hooks Make Agent Work Controllable

The hook contract is the control surface. A hook names a phase, trigger, owner
skill, expected reasoning-log events, output artifacts, and validation gate.

This turns an open-ended agent workflow into a partially observable controlled
process. The agent can be creative inside a phase, but the phase boundary says
what must be recorded before the workflow moves on.

### 4. Reflective Loops Must Be Monotone

Reflection is not a free rewrite. When a loop repairs a candidate, it must
preserve already-passing protected dimensions unless a source-backed theorem
shape correction forces a full rerun.

Protected dimensions include:

- source fidelity;
- backend executability;
- realness of the artifact;
- non-vacuity of the theorem or derivation;
- dependency and library grounding;
- explicit assumptions and side conditions;
- unit, dimension, frame, and regime coverage for physics.

### 5. Critics Localize Risk, They Do Not Certify Truth

Critics are useful because they point to failure surfaces: source drift, missing
hypotheses, weak theorem shape, broad custom axioms, hidden target assumptions,
unit erasure, mathlib mismatch, or vacuity.

A critic finding can block completion when it is supported by source anchors,
backend diagnostics, deterministic reports, or repeated independent probes. A
critic finding alone is not a proof.

### 6. Reverse Informalization Is A Semantic Mirror

Reverse informalization asks: if we translate the formal artifact back into
ordinary mathematical language, does it still look like the source claim?

This is not a substitute for proof checking. It is a semantic guardrail that
helps catch theorem-shape drift, missing assumptions, weakened conclusions, and
formal artifacts that compile for the wrong reason.

### 7. Premise Selection Retrieves Aggressively And Trusts Conservatively

Premise selection may use exact lookup, Bloom filters, semantic search,
geometric distance, curated facts, generated theorem corpora, and prior proof
artifacts. These are retrieval mechanisms, not automatic trust mechanisms.

A retrieved fact becomes usable only according to its provenance and status:
generated candidate, source-backed candidate, formal candidate, proved artifact,
reviewed premise, rejected premise, or blocked premise.

### 8. Backend Evidence Is Part Of The Argument

Lean, Rocq, Isabelle, Vampire, SymPy, and KB workflows provide different kinds
of evidence. Each backend must leave inspectable inputs, outputs, diagnostics,
and status.

The evidence is the artifact trail: formal files, TPTP problems, TSTP proofs,
compiler reports, SymPy traces, KB indexes, unit reports, consistency reports,
and blocker reports.

### 9. Completion Is A Status, Not A Mood

The paper distinguishes complete, draft, failed, and blocked states. A run is
complete only when all required hard validation gates pass. A run is blocked
when the same obstacle persists across repeated refinement attempts and no
available loop improves the protected metric vector.

This makes failure useful. A blocker report tells the next agent where the
mathematical or engineering pressure actually is.

## Critical Reflective Loops

These loop contracts are the working shape of the principles above. They are
defined operationally in `skills/SKILL_HOOKS.yaml`.

| Loop | What It Controls | Critical Gate |
| --- | --- | --- |
| `preformalization_readiness_loop` | Source extraction, theorem units, proof support, LaTeX/source anchors, and readiness before formal drafting | Do not draft when source shape, assumptions, or anchors are missing |
| `mathlib_grounding_loop` | Concept search, hierarchy navigation, candidate declaration verification, import planning, and optional official-source web grounding | Do not invent local definitions when a verified library path exists; mark unresolved gaps explicitly |
| `draft_execute_refine_loop` | Lean drafting, execution, diagnostic interpretation, critique, and localized repair | Repairs must improve diagnostics without losing source fidelity, realness, or non-vacuity |
| `artifact_acceptance_loop` | Import minimization, reverse informalization, declaration-shape review, non-vacuity checks, and unified consistency reports | Candidate status changes only after hard acceptance evidence exists |
| `lean_consistency_testing_loop` | Reference-free Lean consistency, artifact statistics, source-to-formal alignment, and report generation | A compiling file still needs consistency and shape checks before stronger claims |
| `sympy_equational_trace_loop` | Symbolic parsing, assumptions, API grounding, identity validation, counterexample search, and trace verification | Executable algebra must record assumptions, domains, and method-specific evidence |
| `sympy_physics_derivation_trace_loop` | Physics equation graphs, quantities, units, dimensions, regimes, laws, residual checks, and numeric samples | A physics derivation must preserve physical meaning, not only algebraic equality |
| `lean_physics_derivation_trace_loop` | Physics-aware Lean formalization with quantity typing, contextual assumptions, unit obligations, Lean execution, critics, and final reviewers | Complete status requires Lean evidence plus physical semantics, units, assumptions, source anchors, and non-vacuity |
| `isabelle_physics_derivation_trace_loop` | Isabelle/HOL physics artifacts with shared physics preformalization and Isabelle-specific grounding/review gates | Isabelle execution evidence must preserve the same source and physics contracts |
| `mathformerlib_accumulation_loop` | Promotion of reusable Lean artifacts into a library surface | Promotion requires stable names, documentation, validation status, and curation boundaries |
| `reflection_testing_loop` | Process reflection over prompts, skills, hooks, and tests | Improvements must be monotone over prior successful cases or explicitly marked experimental |

## The Three Feedback Loops

The paper highlights three feedback loops that explain how Mathformer improves
without hiding regressions.

| Feedback Loop | Input | Repair Target |
| --- | --- | --- |
| Prover and critic repair | Backend diagnostics and critic findings | The formal artifact or proof script |
| Reverse-informalization repair | The formal artifact translated back into readable mathematics | The theorem shape, assumptions, and source alignment |
| Process reflection | Observed run trajectory, metrics, failures, costs, and blockers | Prompts, skills, hooks, tests, and workflow structure |

The first two loops repair the artifact. The third repairs the process. The
third loop is the most dangerous and therefore the most constrained: it may not
improve a new run by invalidating previous accepted behavior.
