<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# FormalPhysics Synthesis Protocol

## Purpose

The synthesis report interprets the full comparative-report evidence across
all cases and both compared approaches. It is not a gold-label verdict. It is a
structured explanation of why each approach is strong or weak according to the
available judges and reviewers.

## Aspect Groups

- `functional_lean`: compile status, accepted/blocked status, proof integrity,
  placeholder hygiene, non-vacuity, and hard blockers.
- `source_and_derivation`: source-semantic preservation, derivation coverage,
  reference-delta quality, and missing source terms.
- `physics_completeness`: physics object fidelity, representation
  completeness, unit/dimension surfaces, context/assumption surfaces, and
  physics-complexity family coverage.
- `grounding_depth`: Mathlib concept grounding, Foundations dependency quality,
  invoked external dependency excerpts, concept-family hits, and typed
  modeling declaration counts.
- `reviewability_and_names`: variable/declaration naming, source-step
  annotations, comment surfaces, bridge/support/witness names, maintainability,
  and reportability.
- `judge_review_consensus`: theorem-prover role preferences, physics role
  preferences, Codex-exec judge results when present, and prompt-readiness
  status when results are pending.

## Codex-Exec Result Ingestion

Completed Codex-exec judge results are optional, advisory evidence. A result is
accepted only when it can be matched to a prompt by `(case_id, candidate_id,
judge_id)`.

The synthesis must report two different concepts separately:

- prompt readiness: how many judge prompts are pending, completed, or in another
  execution state;
- disagreement patterns: what completed judge results imply when compared with
  deterministic best-solution choices and deterministic metric means.

Do not infer a completed judge result from a ready prompt. When no results are
ingested, disagreement-pattern sections should say that no completed pairwise
judge evidence is available.

## Strength and Weakness Rules

Strength indicators:

- accepted hard-gate status across most cases;
- mean aspect score at least 4.0;
- clear advantage over the other approach by at least 0.75 on an aspect;
- role-review preference for most cases;
- invoked external concept excerpts with meaningful variety;
- explicit annotations linking source steps to formal declarations.

Weakness indicators:

- blocked hard gates, placeholders, vacuous targets, or failed compilation;
- mean aspect score below 3.0;
- clear deficit against the other approach by at least 0.75;
- missing invoked dependency context where the candidate depends on external
  concepts;
- source complexity flattened into a pure algebraic shell;
- pending generative judge results when a high-stakes synthesis is desired.

Action-register status values:

- `open`: repo-local work that can be acted on directly;
- `waiting_for_codex_exec_results`: blocked until the consumer application or
  MCP layer supplies completed judge-result JSON;
- `external_reference_not_repo_actionable`: evidence about the external
  reference candidate, not a local repair task.

## Narrative Policy

- Explain evidence in aspect-first language.
- Preserve disagreement between reviewers instead of averaging it away.
- Separate “accepted Lean artifact” from “physically complete formalization”.
- Mention when Codex-exec judges are only prompts and no generated result has
  been ingested.
- Emit TODOs that are self-contained and grounded in a named weakness.
