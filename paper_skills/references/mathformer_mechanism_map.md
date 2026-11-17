<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Capture the research-paper production workflow as auditable agent skills and helper scripts.

Intent:
  Separate scientific writing, evidence mapping, figure generation, and theory-evolution modeling roles.

Function:
  Provides structured guidance and automation for paper-oriented artifacts.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Mathformer Paper Mechanism Map

This reference is a compact map for paper-writing skills. It should be updated
when the framework architecture changes.

## Core Mechanism

Mathformer treats autoformalization as a controlled trajectory rather than a
single generation event. A run starts from source mathematics and passes through
extraction, expansion, mathlib grounding, Lean drafting, execution, critique,
refinement, reverse informalization, consistency checking, RFDE observability,
and reflective skill improvement.

## Skill Families

| Family | Representative paths | Mechanistic role |
| --- | --- | --- |
| Workflow orchestration | `skills/autoformalization/autoformalization-workflow-orchestrator/`, `skills/SKILL_HOOKS.yaml` | Defines phase ownership, hook routing, validation criteria, and end-to-end loops. |
| Source extraction | `skills/autoformalization/source-formalizable-unit-extractor/`, `skills/latex-textbook/latex-archive-theory-extractor/`, `skills/paper/paper-docling-layout-extractor/` | Converts raw source into formalizable units with provenance. |
| Source anchoring | `skills/autoformalization/source-line-translation-packet-builder/`, `skills/autoformalization/source-formalization-drift-guard/`, `skills/lean/lean-line-annotation/` | Maintains literal reference points between NL/LaTeX and Lean declarations. |
| Informal expansion | `skills/latex-textbook/latex-prerequisite-expander/`, `skills/latex-textbook/latex-expansion-review-orchestrator/`, `skills/latex-textbook/latex-expansion-binding-reviewer/` | Surfaces implicit definitions, assumptions, bindings, and proof obligations. |
| Mathlib grounding | `skills/mathlib/mathlib-grounding-maximizer/`, `skills/mathlib/mathlib-hierarchy-navigator/`, `skills/mathlib/mathlib-import-set-builder/`, `skills/mathlib/mathlib-result-existence-checker/` | Maximizes reuse of mathlib APIs and prevents duplicate or invented abstractions. |
| Draft/execute/refine | `skills/lean/lean-autoformalization-drafter/`, `skills/lean/lean-execution-runner/`, `skills/lean/lean-formal-refinement/`, `skills/lean/lean-compile-checker/` | Generates Lean and repairs syntax/type/proof failures under prover feedback. |
| Critique stack | `skills/lean/lean-critique-suite-orchestrator/`, `skills/lean/lean-syntactic-correctness-critic/`, `skills/lean/lean-semantic-preservation-critic/`, `skills/lean/lean-logical-soundness-critic/` | Provides orthogonal diagnostic pressure before acceptance. |
| Consistency stack | `skills/lean/lean-consistency-report-orchestrator/`, `skills/lean/lean-informalization-extractor/`, `skills/lean/lean-informal-consistency-verifier/`, `skills/lean/lean-nonvacuity-consistency-checker/` | Tests reverse-informal consistency, declaration shape, non-vacuity, and proof coherence. |
| Artifact realness | `skills/autoformalization/autoformalization-result-realness-verifier/`, `skills/control/gate-policy-controller/` | Enforces validation criteria that block mocks, placeholders, unexecuted claims, and scaffold-only success. |
| Library accumulation | `skills/mathformerlib/mathformerlib-accumulation-orchestrator/`, `skills/mathformerlib/mathformerlib-promotion-gate/`, `libraries/MathformerLib/` | Promotes reusable formalizations into a controlled parallel library. |
| Reasoning logs | `skills/control/reasoning-log-schema-guardian/`, `artifacts/full_autoformalization_reasoning_log_test/` | Records workflow-level and skill-application-level traces with schema validation and Markdown/HTML inspection projections. |
| Observability | `skills/rfde/reference-free-descriptive-evaluator/`, `skills/rfde/reference-free-critic-monitor/`, `paper/REFERENCE_FREE_REFINEMENT_DYNAMICS.tex` | Describes trajectory quality without a gold Lean reference and emits monitor statistics, plots, and weakest-dimension diagnostics. |
| Premise selection | `backends/premise_kb/MathformerKB/`, `skills/premise-kb/premise-kb-indexer/`, `examples/outputs/fundamental_theorem_algebra_search_demo.md` | Separates exact KB presence checks from embedding-neighborhood search and geometric-distance reports. |
| ATP proof artifacts | `backends/atp/MathformerATP/`, `skills/atp/vampire-atp-orchestrator/`, `artifacts/vampire_atp/` | Emits generated TPTP problems, Vampire SZS statuses, TSTP proofs, and premise-guided proof reports. |
| Controlled workflow hub | `scripts/mathformer.py`, `docs/architecture/AGENTIC_HUB.md` | Registers discoverable actions with family, safety, required-path, command, write-target, and dependency metadata. |
| Proof catalog | `docs/libraries/PROOF_CATALOG.md`, `docs/libraries/mathformerlib/` | Links reusable formal artifacts and generated proof descriptions for MathformerLib and MathformerPhysicsLib surfaces. |
| Reflection/testing | `skills/autoformalization/autoformalization-reflective-refinement-loop/`, `skills/control/skill-test-program-orchestrator/` | Converts observed failures into monotone skill/prompt improvements. |

## Observability Surfaces

| Surface | Representative path | What it supports | What it does not support |
| --- | --- | --- | --- |
| Reasoning-log JSONL | `artifacts/full_autoformalization_reasoning_log_test/reasoning.jsonl` | Event ordering, lifecycle coverage, blockers, and validation traceability. | Theorem correctness by itself. |
| Skill-application JSONL | `artifacts/full_autoformalization_reasoning_log_test/skill_application.jsonl` | Per-skill intent, inputs, outputs, status, and blocker structure. | Backend execution success unless linked to execution artifacts. |
| HTML dashboard | `artifacts/full_autoformalization_reasoning_log_test/reasoning.html` | Human inspection of structured traces. | A new proof source. |
| Reference-free monitor | `artifacts/reference_free_critic_monitor/platform_refinement_test/evolution/formalization_evolution.json` | Score deltas, risk deltas, weakest dimensions, blocker counts, and regressions. | Replacement for Lean/Rocq/SymPy/ATP validation. |
| Premise-selection report | `examples/outputs/fundamental_theorem_algebra_search_demo.md` | Exact presence and semantic-neighborhood evidence for theorem memory. | Proof that selected premises are sufficient. |
| ATP proof report | `artifacts/vampire_atp/atp_function_demo/` | TPTP problem generation, SZS status, and inspectable TSTP proof artifacts. | Semantic equivalence to every informal source unless separately checked. |

## Inspection Artifacts

| Artifact class | Typical extension | Reader task |
| --- | --- | --- |
| Backend validation | `.json`, `.tstp`, `.lean`, `.v` | Confirm what a prover or checker accepted, rejected, or blocked. |
| Trace validation | `.jsonl`, `.json` | Inspect lifecycle coverage, missing stages, and blockers. |
| Projection | `.html`, `.md` | Navigate evidence in human-readable form. |
| Plot/statistics | `.csv`, `.json`, `.svg` | Compare trajectory movement, regressions, and weakest dimensions. |
| Paper plan | `.md`, `.json` | Route feature evidence to manuscript claims, sections, figures, and limitations. |

## New Functionality Intake

Use this mini-workflow for paper updates:

```text
new platform functionality
-> evidence packet
-> mechanism abstraction
-> paper claim delta
-> section patch plan
-> figure/table plan
-> claim-evidence audit
```

The evidence packet should name implementation paths, generated artifacts,
validation commands, supported claims, explicit non-claims, target paper
sections, figure/table implications, and limitations.

## State Components

Use this model in paper drafts:

```text
S_t = (X, U, L_t, G_t, C_t, R_t, O_t, M_t, Q_t)
```

- `X`: literal source;
- `U`: source units and line-translation packets;
- `L_t`: current Lean artifact;
- `G_t`: mathlib grounding packet;
- `C_t`: critic and validation-criterion report stack;
- `R_t`: reverse informalization packet;
- `O_t`: dependency and obligation ledger;
- `M_t`: metric vector;
- `Q_t`: temporal, deterministic, and generative cost trace.

## Core Non-Claims

- RFDE does not prove theorem correctness.
- Reasoning-log dashboards improve inspection but do not certify theorem
  correctness.
- Reference-free monitor plots support diagnosis but do not replace backend
  validation.
- Passing consistency validation criteria does not replace mathematical review.
- The framework is primarily an observability and control architecture for
  autoformalization, with Lean and mathlib as central deterministic constraints.
