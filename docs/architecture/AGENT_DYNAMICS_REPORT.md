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

# Agent Dynamics Report

Generated: 2026-06-06

This report analyses the current Mathformer agentic framework from two views:

- the designed dynamics encoded in `skills/SKILL_HOOKS.yaml`,
- the observed dynamics in available reasoning logs and object-run artifacts.

The goal is to make visible which agents are being used, where convergence is
being judged, and where the workflow still needs tighter runtime evidence.

## 1. Executive Summary

Mathformer now has a broad hook-based control architecture: 72 workflow hooks
cover intake, preformalization, mathlib alignment, drafting, critique,
execution, consistency, reflection, testing, and library accumulation. Of these
hooks, 56 define explicit gates, so most systematic agent transitions have a
declared convergence condition.

The observed logs show a different, useful picture: most recorded activity is
from the testing and refinement infrastructure, not from full production
autoformalization runs. Across the available reasoning logs there are 1,939
events, dominated by `skill-test-program-orchestrator`, with smaller but
meaningful traces from reflection, mathlib verification, LaTeX expansion review,
AgentC, and the unified Lean consistency layer.

The framework is moving in the right direction: new reasoning-log events can now
carry `agent_usage` and `convergence_criteria`, and deterministic tests enforce
that instrumentation for new shared-log and AgentC workflow events. The main
remaining gap is historical and operational: older logs and existing textbook
object-run results were produced before this instrumentation, so they cannot yet
support complete agent-dynamics analysis without reruns.

## 2. Designed Agent Dynamics

The hook contract defines the intended control surface:

| Phase | Hook Count | Interpretation |
| --- | ---: | --- |
| `mathlib_alignment` | 16 | Largest control region; grounding is deliberately multi-agent and iterative. |
| `preformalization` | 10 | Strong front-loading before Lean generation: source units, expansion, bindings, dependencies. |
| `critique` | 7 | Multiple orthogonal critics rather than one monolithic reviewer. |
| `intake` | 5 | Source and archive ingestion are first-class workflow stages. |
| `control` | 4 | Contract, coverage, schema, and gate policy govern the system itself. |
| `drafting` | 4 | Drafting includes seed, initial formalization, and object-level textbook runs. |
| `consistency` | 4 | Post-Lean consistency is decomposed into shape, non-vacuity, cross-file, and unified reports. |
| Other phases | 22 | Library, postformalization, refinement, cleanup, artifacts, annotation, execution, verification, logging, audit, reflection, testing, benchmark. |

The architecture is intentionally control-heavy around mathlib. This is
appropriate for autoformalization: the most expensive failures are often not
syntax failures but semantic drift, invented APIs, under-specified concepts, and
proofs that compile only because they prove a weaker or vacuous statement.

## 3. Observed Agent Dynamics

Observed reasoning logs:

- `artifacts/skill_test_program/reasoning.jsonl`: 1,646 events.
- `artifacts/wiki_level_suite/reasoning.jsonl`: 145 events.
- `artifacts/reflection/reasoning.jsonl`: 99 events.
- `artifacts/workflow_consistency_smoke/workflow_consistency_smoke.reasoning.jsonl`: 48 events.
- `artifacts/reasoning_log_instrumentation_smoke/reasoning.jsonl`: 1 event.

Top observed skills/agents:

| Agent or Skill | Events | Reading |
| --- | ---: | --- |
| `skill-test-program-orchestrator` | 1,417 | Testing dominates the current evidence base. |
| `autoformalization-reflective-refinement-loop` | 108 | Reflection is active and repeatedly logged. |
| `mathlib-candidate-verifier/map_mathlib_concepts.py` | 103 | Mathlib verification is a recurring bottleneck/control point. |
| `latex-expansion-review-orchestrator` | 15 | Source expansion review is present but small in current logs. |
| `autoformalization-workflow-orchestrator` | 13 | End-to-end workflow traces are present but not yet the dominant corpus. |
| `lean-consistency-report-orchestrator` | 13 | Unified consistency is exercised, mainly in smoke/workflow checks. |
| `autoformalization-agentc` | 10 | AgentC appears in the integrated consistency smoke path. |

The event distribution says the framework is currently best instrumented as a
test-and-control system. Full production autoformalization dynamics are only
partly represented in the available logs.

## 4. Convergence Dynamics

The hook contract gives convergence criteria through gate text. The strongest
gated regions are:

- control gates: hook validation, coverage, reasoning-log schema, gate policy,
- preformalization gates: source unit inventory, LaTeX expansion completeness,
  binding checks, dependency expansion,
- mathlib gates: result existence, hierarchy navigation, candidate verification,
  import planning, web corroboration, compatibility loops,
- artifact gates: realness, compile/execute checks, denoising, line annotation,
- consistency gates: informalization, declaration shape, internal proof
  consistency, non-vacuity, cross-file concepts, unified consistency report,
- reflection/testing gates: monotonic improvement and regression control.

Observed convergence evidence is still sparse because many logs predate the new
instrumentation. In the newly instrumented path, events can now carry:

- `agent_usage`: where the agent was used, including hook phase and usage site,
- `convergence_criteria`: the gate or inferred criterion,
- `current_evidence`: local evidence such as `ok`, `status`,
  `compatibility_score`, `consistency_target_met`, or blocking finding counts.

This changes the dynamics analysis from narrative reconstruction to measurable
state transitions.

## 5. Transition Dynamics

The intended workflow is a loop, not a line:

1. Intake identifies source units and artifacts.
2. Preformalization expands source text, bindings, prerequisites, and difficulty.
3. Mathlib alignment searches, maps, verifies, and grounds the target concepts.
4. Drafting produces Lean candidates.
5. Execution and critique expose syntax, semantic, logical, and grounding
   failures.
6. Refinement updates the candidate without weakening previous successes.
7. Consistency checks reverse-informalize, test non-vacuity, and compare shapes.
8. Artifact gates decide whether the result is final, draft, blocked, or
   promotable to MathformerLib.
9. Reflection and testing convert failures into monotonic prompt/skill
   improvements.

Observed transitions are currently dominated by self-loops inside testing and
legacy uninstrumented phases. This is expected because the deterministic suite
produces a large event volume. The next stage should increase the ratio of
production workflow events with fully populated hook phase metadata.

## 6. Textbook Object-Run Dynamics

The current textbook object-run manifest records 5 processed jobs from the
arXiv textbook archive batch:

| Status | Count | Meaning |
| --- | ---: | --- |
| `complete` | 3 | Generation plus configured gates passed. |
| `blocked_generation` | 1 | The generator did not produce acceptable Lean. |
| `draft_failed_gates` | 1 | Lean was generated but failed at least one gate. |

This is a valuable microcosm of the desired object-by-object dynamics: not every
unit should advance, and blocked/draft states are informative. However, those
specific result files were generated before per-object `agent_usage` and
`convergence_criteria` fields were added, so they should be rerun if the
textbook batch is used for quantitative agent-dynamics analysis.

## 7. Dynamics Risks

### R1. Test-Dominant Observability

The largest observed agent is the test orchestrator. This is good for regression
control, but it can hide production bottlenecks unless production runs are logged
with the same rigor.

Todo:

- Run representative end-to-end autoformalization workflows after the new
  instrumentation and archive their reasoning logs separately from test logs.

### R2. Legacy Log Blind Spots

Older logs often lack `agent_usage` and `convergence_criteria`. They remain
useful for sequence and event-count analysis, but not for precise convergence
analysis.

Todo:

- Treat pre-instrumentation logs as historical baselines only.
- Add a report field that distinguishes `instrumented_event_count` from
  `legacy_event_count`.

### R3. Mathlib Alignment Is Broad But Hard To Attribute

The hook contract has 16 mathlib-alignment hooks. This is appropriate, but
without per-agent convergence evidence it is hard to tell whether failures come
from concept mapping, result-existence checks, import context, hierarchy
navigation, web grounding, or compatibility loops.

Todo:

- Require every mathlib-alignment agent to emit `current_evidence` fields for
  candidate count, verified count, unresolved concept count, import delta, and
  blocker count.

### R4. Object-Level Runs Need Native Reasoning Logs

Textbook per-object result JSON now records usage and convergence, but the
object runner should also append reasoning-log events for each object lifecycle.

Todo:

- Add JSONL events for object job start, provider block, generation complete,
  gates complete, and final status.

### R5. Convergence Criteria Are Present But Not Yet Normalized

Gate text is human-readable and useful, but some analyses need structured
criteria.

Todo:

- Add optional normalized fields such as `target_status`,
  `required_gate_ids`, `minimum_scores`, `monotonicity_policy`, and
  `blocking_failure_policy`.

## 8. Recommended Agent-Dynamics Metrics

Track these metrics per run and over time:

- event count by skill, hook, and phase,
- instrumented event ratio,
- convergence source ratio: hook contract vs payload inference vs missing,
- phase transition matrix,
- blocker count by owner skill,
- mean retries per drafting target,
- mathlib candidate verification ratio,
- generated Lean acceptance ratio,
- draft-to-final conversion ratio,
- monotonic critic score deltas,
- number of improvements accepted without invalidating previous successful
  cases.

These metrics are reference-free: they do not require a benchmark theorem corpus.
They evaluate internal process health, consistency, and convergence discipline.

## 9. Immediate Implementation Todos

- Generate `artifacts/agent_dynamics/agent_dynamics_report.json` from all
  reasoning logs and object-run manifests.
- Add a deterministic test that fails if a new reasoning log has less than 95%
  instrumented events, while allowing explicitly marked legacy logs.
- Extend the textbook object runner to write lifecycle reasoning-log events.
- Add per-hook structured convergence schemas for the high-traffic phases:
  `mathlib_alignment`, `drafting`, `critique`, and `consistency`.
- Add an aggregate dashboard table to the main workflow report:
  `agent`, `hook`, `phase`, `calls`, `passes`, `blocks`, `criteria_source`,
  `last_evidence`.
- Rerun the active textbook object batch with `--force` for a small controlled
  slice after instrumentation, then compare old vs new observability.

## 10. Bottom Line

The framework has the right agentic shape: many specialized agents, systematic
hooks, explicit gates, and a growing reflection/testing layer. The main next
step is not to add more agents; it is to make every agent invocation produce
structured convergence evidence. Once production autoformalization runs are
logged with the new instrumentation, Mathformer can analyse agent dynamics as a
measurable control system rather than as a sequence of opaque prompt calls.
