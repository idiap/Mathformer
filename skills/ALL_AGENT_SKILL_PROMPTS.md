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

# Agent And Skill Prompt Index

This file indexes prompt ownership for local skills and LLM agents in this repository.
Canonical prompt bodies now live in the specialized skill `references/` files listed below.

## Scope

- Skill interface prompts from each canonical skill's `agents/openai.yaml` file
- LLM agent prompt templates formerly consolidated under `skills/autoformalization/autoformalization-agentc`
- Local prompt extensions used by systematic workflow orchestration

## Skill Specialization Status

Goal: split broad skills into smaller skills with one clear trigger each, while preserving
prompt parity, shared runtime entrypoints, artifact formats, and workflow behavior.

### Completed Skill Boundaries

- [x] `mathformer-generative-workflow-coordinator`: owns Codex-facing interpretation, decomposition, sequencing, and controlled invocation of one or more Mathformer workflows from natural-language goals.
- [x] `workflow-contract-validator`: owns executable validation of hook ids, owner skills, shared runtime paths, direct-request routing, prompt-index references, and optional reasoning-log evidence.
- [x] `skill-hook-coverage-maximizer`: owns executable auditing that non-wrapper skills are reachable and named loop contracts include required hooks and owner skills.
- [x] `reasoning-log-schema-guardian`: owns canonical reasoning-log event emission and JSONL schema validation against the hook contract.
- [x] `gate-policy-controller`: owns reusable pass/warn/fail/skip/waived gate decisions from structured checks, severities, blocking flags, and waiver records.
- [x] `autoformalization-reflective-refinement-loop`: owns full-process observation and monotonic prompt/skill improvement packets that preserve previous successful cases.
- [x] `reference-free-critic-monitor`: owns benchmark-free critic-measure snapshots, monotonic score/risk comparisons, anti-gaming checks, and improvement TODOs for Lean artifacts.
- [x] `skill-test-program-orchestrator`: owns aggressive deterministic and Codex-exec content testing across all local skills, plus self-explanatory testing TODO generation.
- [x] `paper-docling-layout-extractor`: owns docling-first paper PDF/layout extraction with fallback reporting, section blocks, theorem/proof neighborhoods, citations, and references.
- [x] `paper-main-theory-localizer`: owns localization of paper-level main theoretical results plus supporting definitions, assumptions, lemmas, proofs, references, mathlib concept hints, and intermediate expansion queues.
- [x] `paper-theory-autoformalization-orchestrator`: owns paper-level theory expansion planning before the selected main result queue enters duplicate checks, mathlib grounding, and Lean drafting.
- [x] `latex-archive-theory-extractor`: owns source-preserving extraction of theorem-like units and proofs from LaTeX textbook archives or source trees.
- [x] `textbook-theory-tex-organizer`: owns thematic chapter/section TeX bundles from extracted textbook theory units.
- [x] `textbook-autoformalization-batch-orchestrator`: owns truthful per-unit autoformalization job queues and object-by-object execution manifests from textbook bundles, with no mocked Lean completion.
- [x] `source-formalizable-unit-extractor`: owns source-page decomposition into source-linked definitions, theorem-like claims, lemmas, corollaries, proofs, examples, formulas, notation, prerequisites, dependency queues, and downstream autoformalization routes.
- [x] `autoformalization-result-realness-verifier`: owns final artifact/report checks that prevent mocks, unexecuted states, proof placeholders, or scaffold-only claims from being reported as completed autoformalizations.
- [x] `mathformerlib-accumulation-orchestrator`: owns controlled accumulation of reusable formalizations into the parallel `MathformerLib` library.
- [x] `mathformerlib-registry-manager`: owns the machine-readable Mathformerlib registry of modules, declarations, imports, provenance, and draft/candidate/accepted statuses.
- [x] `mathformerlib-promotion-gate`: owns accepted-promotion checks that block mocked, scaffolded, placeholder, or uncompiled candidates.
- [x] `result-existence-precheck-orchestrator`: owns the pre-draft duplicate-result gate across MathformerLib, local mathlib, and official-source mathlib web search.
- [x] `mathlib-result-existence-checker`: owns deterministic result-existence reports and drafting gate decisions.
- [x] `latex-prerequisite-expander`: owns `LatexExpansionAgent` prompts and pre-formalization expansion guidance.
- [x] `latex-expansion-completeness-reviewer`: owns the pre-autoformalization review for prerequisite, assumption, side-condition, and conclusion coverage in expanded LaTeX.
- [x] `latex-expansion-binding-reviewer`: owns the pre-autoformalization review for binders, quantifiers, free variables, domains, indices, arities, references, and notation in expanded LaTeX.
- [x] `latex-expansion-review-orchestrator`: owns ordered application of LaTeX expansion review hooks before initial Lean/Isabelle drafting.
- [x] `proof-expansion-difficulty-estimator`: owns proof-part segmentation, expansion-difficulty scoring, and web-search decision metadata.
- [x] `proof-expansion-web-researcher`: owns source-backed web research packets for hard or uncertain proof-expansion segments.
- [x] `proof-expansion-support-orchestrator`: owns the pre-expansion loop that estimates difficulty, invokes web support, and hands verified notes to LaTeX expansion.
- [x] `lean-autoformalization-drafter`: owns `AutoformalizationAgent` prompts, few-shot wrapping, dependency context, mathlib hints, and source-aware Natural language/LaTeX declaration comment requirements.
- [x] `lean-execution-runner`: owns execution of generated Lean code immediately after initial formalization delivery.
- [x] `rocq-autoformalization-drafter`: owns deterministic Rocq `.v` drafting for controlled Mathformer source fixtures.
- [x] `rocq-execution-runner`: owns structural Rocq artifact validation and optional `rocq compile`/`coqc` execution.
- [x] `lean-formal-refinement`: owns `FormalRefinementAgent` and `InformalRefinementAgent` prompts, refinement modes, error-category hints, and semantic-preservation guardrails.
- [x] `lean-critique-and-judging`: owns `SoftCritiqueAgent` prompts and default LLM judge aspect prompts.
- [x] `lean-syntactic-correctness-critic`: owns the Lean syntax/elaboration/typecheck critique pass.
- [x] `lean-semantic-preservation-critic`: owns the source-to-Lean meaning preservation critique pass.
- [x] `lean-logical-soundness-critic`: owns the non-vacuity/logical soundness critique pass.
- [x] `lean-mathlib-alignment-critic`: owns the mathlib-native API alignment critique pass.
- [x] `lean-critique-suite-orchestrator`: owns ordered critique-gate coordination across critique passes.
- [x] `lean-informalization-extractor`: owns reverse Lean-to-informal statement/proof packets from final Lean artifacts.
- [x] `lean-informal-proof-internal-consistency-verifier`: owns internal consistency evaluation for informalized proof packets.
- [x] `lean-informal-consistency-verifier`: owns reverse informalized proof-consistency checks before artifact acceptance.
- [x] `lean-declaration-shape-consistency-checker`: owns deterministic agreement checks between source-facing logical shape and Lean theorem signatures.
- [x] `lean-nonvacuity-consistency-checker`: owns vacuity, target-restatement, false-hypothesis, axiom, and thin-wrapper review for theorem-like Lean declarations.
- [x] `lean-cross-file-concept-consistency-indexer`: owns corpus-level concept indexing, duplicate full-name detection, divergent signature review, and MathformerLib promotion candidates.
- [x] `lean-consistency-report-orchestrator`: owns the unified reference-free Lean consistency report across compile, comments, realness, informalization, shape, proof consistency, non-vacuity, cross-file concepts, grounding, and critic monitoring.
- [x] `lean-output-denoiser`: owns `DenoisingAgent` prompts and fenced-code cleanup rules.
- [x] `lean-refinement-taxonomy`: owns `RefinementTaxonomyAgent` prompts and transition classification output rules.
- [x] `lean-line-annotation`: owns `LeanLineAnnotationAgent` prompts, line-stable annotation output rules, and generated Lean source-comment hygiene plus semantic-alignment validation.
- [x] `autoformalization-workflow-orchestrator`: owns `IterativeSelfRefinementAgentC`, `HardCritiqueAgent`, `ImportRetrievalAgent`, recursive dependencies, score-gated cycles, artifacts, reasoning logs, and statistics.
- [x] `proofnet-benchmark-runner`: owns ProofNet download/export/evaluation commands.
- [x] `autoformalization-agentc`: reduced to a compatibility wrapper for the shared runtime and legacy prompt snapshot.
- [x] `mathlib-concept-candidate-mapper`: owns concept-to-declaration/module ranking without Lean verification.
- [x] `mathlib-hierarchy-navigator`: owns broad-to-specific mathlib traversal across module prefixes, concrete modules, siblings, and query results.
- [x] `mathlib-module-tree-cartographer`: owns module-prefix parent/child/sibling cartography and leaf-count navigation.
- [x] `mathlib-declaration-neighborhood-navigator`: owns focused module imports, local declarations, declaration-name filters, and source references.
- [x] `mathlib-candidate-verifier`: owns bounded Lean `#check` verification for candidate declarations.
- [x] `mathlib-concept-coverage-reviewer`: owns verified-coverage scoring for extracted concepts and gap reporting.
- [x] `mathlib-web-search-strategist`: owns official-source web query planning when local mathlib grounding leaves gaps.
- [x] `mathlib-web-evidence-validator`: owns validation of web-sourced mathlib API claims, source provenance, and local verification status.
- [x] `mathlib-web-grounding-orchestrator`: owns the controlled loop from local gap to web search, evidence validation, and local Lean verification handoff.
- [x] `mathlib-import-set-builder`: owns planned import-block construction from verified modules, hierarchy output, fixture metadata, and existing Lean imports.
- [x] `lean-import-context-verifier`: owns checking generated Lean and expected declarations under intended import contexts instead of only under broad `import Mathlib`.
- [x] `mathlib-import-minimizer`: owns post-generation import deduplication, broad-import findings, and optional compile-checked import removal.
- [x] `mathlib-api-compatibility-planner`: owns coverage-aware drafting hints that prefer verified mathlib declarations and isolate unresolved gaps.
- [x] `mathlib-compatibility-loop-orchestrator`: owns bounded loops that widen concept discovery/verification and the outer compatibility target gate.
- [x] `mathlib-grounding-maximizer`: owns whole-artifact mathlib grounding maximization across import narrowing, native API reuse, concept/web grounding, scaffold cleanup, compatibility targets, and reference-free monotonicity.
- [x] `informal-proof-mathlib-concepts`: reduced to a compatibility wrapper for the shared mathlib lookup runtime.
- [x] `lean-compile-checker`: owns direct Lean compile/typecheck diagnostics.
- [x] `mathlib-abstraction-auditor`: owns mathlib-native alignment, abstraction-boundary, documentation, placeholder, wrapper-substance, scoring, and strict-gate guidance.
- [x] `mathlib-compatibility-auditor`: reduced to a compatibility wrapper for the shared compatibility audit runtime.

## Canonical References

| Agent or workflow surface | Owning skill | Canonical reference |
| --- | --- | --- |
| Hook contract validation | `workflow-contract-validator` | `skills/control/workflow-contract-validator/references/contract.md` |
| Hook coverage and loop contracts | `skill-hook-coverage-maximizer` | `skills/control/skill-hook-coverage-maximizer/references/coverage_policy.md` |
| Reasoning-log schema validation | `reasoning-log-schema-guardian` | `skills/control/reasoning-log-schema-guardian/references/schema.md` |
| Universal gate decisions | `gate-policy-controller` | `skills/control/gate-policy-controller/references/gate_decision.md` |
| Reflective monotonic process improvement | `autoformalization-reflective-refinement-loop` | `skills/autoformalization/autoformalization-reflective-refinement-loop/references/refinement_loop.md` |
| Reference-free critic monitoring | `reference-free-critic-monitor` | `skills/rfde/reference-free-critic-monitor/references/reference_free_monitor.md` |
| Aggressive skill testing program | `skill-test-program-orchestrator` | `skills/control/skill-test-program-orchestrator/references/test_program.md` |
| Paper docling layout extraction | `paper-docling-layout-extractor` | `skills/paper/paper-docling-layout-extractor/references/layout_packet_schema.json` |
| Paper main theory localization | `paper-main-theory-localizer` | `skills/paper/paper-main-theory-localizer/references/theory_localization_schema.json` |
| Paper theory autoformalization orchestration | `paper-theory-autoformalization-orchestrator` | `skills/paper/paper-theory-autoformalization-orchestrator/SKILL.md` |
| LaTeX textbook theory extraction | `latex-archive-theory-extractor` | `skills/latex-textbook/latex-archive-theory-extractor/SKILL.md` |
| Textbook theory TeX organization | `textbook-theory-tex-organizer` | `skills/latex-textbook/textbook-theory-tex-organizer/SKILL.md` |
| Textbook autoformalization batch orchestration | `textbook-autoformalization-batch-orchestrator` | `skills/latex-textbook/textbook-autoformalization-batch-orchestrator/SKILL.md` |
| Source formalizable unit inventory | `source-formalizable-unit-extractor` | `skills/autoformalization/source-formalizable-unit-extractor/references/unit_inventory_schema.json` |
| Final result realness gate | `autoformalization-result-realness-verifier` | `skills/autoformalization/autoformalization-result-realness-verifier/references/realness_gate.md` |
| Mathformerlib accumulation | `mathformerlib-accumulation-orchestrator` | `skills/mathformerlib/mathformerlib-accumulation-orchestrator/SKILL.md` |
| Mathformerlib registry | `mathformerlib-registry-manager` | `skills/mathformerlib/mathformerlib-registry-manager/SKILL.md` |
| Mathformerlib promotion | `mathformerlib-promotion-gate` | `skills/mathformerlib/mathformerlib-promotion-gate/SKILL.md` |
| Result-existence precheck | `result-existence-precheck-orchestrator` | `skills/autoformalization/result-existence-precheck-orchestrator/references/precheck_loop.md` |
| Result-existence deterministic search | `mathlib-result-existence-checker` | `skills/mathlib/mathlib-result-existence-checker/references/existence_policy.md` |
| `LatexExpansionAgent` | `latex-prerequisite-expander` | `skills/latex-textbook/latex-prerequisite-expander/references/prompts.md` |
| `LatexExpansionCompletenessReviewAgent` | `latex-expansion-completeness-reviewer` | `skills/latex-textbook/latex-expansion-completeness-reviewer/references/review.md` |
| `LatexExpansionBindingReviewAgent` | `latex-expansion-binding-reviewer` | `skills/latex-textbook/latex-expansion-binding-reviewer/references/review.md` |
| LaTeX expansion review suite | `latex-expansion-review-orchestrator` | `skills/latex-textbook/latex-expansion-review-orchestrator/references/review_suite.md` |
| Proof expansion difficulty estimation | `proof-expansion-difficulty-estimator` | `skills/autoformalization/proof-expansion-difficulty-estimator/references/difficulty.md` |
| Proof expansion web research | `proof-expansion-web-researcher` | `skills/autoformalization/proof-expansion-web-researcher/references/web_research.md` |
| Proof expansion support loop | `proof-expansion-support-orchestrator` | `skills/autoformalization/proof-expansion-support-orchestrator/references/support_loop.md` |
| `AutoformalizationAgent` | `lean-autoformalization-drafter` | `skills/lean/lean-autoformalization-drafter/references/prompts.md` |
| Lean execution after initial formalization | `lean-execution-runner` | `skills/lean/lean-execution-runner/references/execution.md` |
| Rocq proof-script drafting | `rocq-autoformalization-drafter` | `skills/rocq/rocq-autoformalization-drafter/SKILL.md` |
| Rocq proof-script validation/execution | `rocq-execution-runner` | `skills/rocq/rocq-execution-runner/SKILL.md` |
| `FormalRefinementAgent` | `lean-formal-refinement` | `skills/lean/lean-formal-refinement/references/prompts.md` |
| `InformalRefinementAgent` | `lean-formal-refinement` | `skills/lean/lean-formal-refinement/references/prompts.md` |
| `SoftCritiqueAgent` | `lean-critique-and-judging` | `skills/lean/lean-critique-and-judging/references/prompts.md` |
| LLM judge aspect prompts | `lean-critique-and-judging` | `skills/lean/lean-critique-and-judging/references/prompts.md` |
| Lean syntactic correctness critique | `lean-syntactic-correctness-critic` | `skills/lean/lean-syntactic-correctness-critic/references/critique.md` |
| Lean semantic preservation critique | `lean-semantic-preservation-critic` | `skills/lean/lean-semantic-preservation-critic/references/critique.md` |
| Lean logical soundness critique | `lean-logical-soundness-critic` | `skills/lean/lean-logical-soundness-critic/references/critique.md` |
| Lean mathlib alignment critique | `lean-mathlib-alignment-critic` | `skills/lean/lean-mathlib-alignment-critic/references/critique.md` |
| Lean critique suite | `lean-critique-suite-orchestrator` | `skills/lean/lean-critique-suite-orchestrator/references/critique_suite.md` |
| Lean-to-informal proof extraction | `lean-informalization-extractor` | `skills/lean/lean-informalization-extractor/references/informalization_contract.md` |
| Informalized proof internal consistency | `lean-informal-proof-internal-consistency-verifier` | `skills/lean/lean-informal-proof-internal-consistency-verifier/references/internal_consistency_policy.md` |
| Informalized proof consistency verification | `lean-informal-consistency-verifier` | `skills/lean/lean-informal-consistency-verifier/references/consistency_policy.md` |
| Lean declaration shape consistency | `lean-declaration-shape-consistency-checker` | `skills/lean/lean-declaration-shape-consistency-checker/references/prompts.md` |
| Lean non-vacuity consistency | `lean-nonvacuity-consistency-checker` | `skills/lean/lean-nonvacuity-consistency-checker/references/prompts.md` |
| Cross-file Lean concept consistency | `lean-cross-file-concept-consistency-indexer` | `skills/lean/lean-cross-file-concept-consistency-indexer/references/prompts.md` |
| Unified Lean consistency report | `lean-consistency-report-orchestrator` | `skills/lean/lean-consistency-report-orchestrator/references/report_schema.md` |
| `DenoisingAgent` | `lean-output-denoiser` | `skills/lean/lean-output-denoiser/references/prompts.md` |
| `RefinementTaxonomyAgent` | `lean-refinement-taxonomy` | `skills/lean/lean-refinement-taxonomy/references/prompts.md` |
| `LeanLineAnnotationAgent` | `lean-line-annotation` | `skills/lean/lean-line-annotation/references/prompts.md` |
| Generated Lean source-comment and semantic-alignment guard | `lean-line-annotation` | `skills/lean/lean-line-annotation/scripts/validate_lean_line_comments.py` |
| `IterativeSelfRefinementAgentC` | `autoformalization-workflow-orchestrator` | `skills/autoformalization/autoformalization-workflow-orchestrator/references/workflow.md` |
| `HardCritiqueAgent` | `autoformalization-workflow-orchestrator` | `skills/autoformalization/autoformalization-workflow-orchestrator/references/workflow.md` |
| `ImportRetrievalAgent` | `autoformalization-workflow-orchestrator` | `skills/autoformalization/autoformalization-workflow-orchestrator/references/workflow.md` |
| ProofNet utilities | `proofnet-benchmark-runner` | `skills/benchmarks/proofnet-benchmark-runner/SKILL.md` |
| Concept/module candidate ranking | `mathlib-concept-candidate-mapper` | `skills/mathlib/mathlib-concept-candidate-mapper/SKILL.md` |
| Mathlib hierarchical navigation | `mathlib-hierarchy-navigator` | `skills/mathlib/mathlib-hierarchy-navigator/references/navigation.md` |
| Mathlib module tree cartography | `mathlib-module-tree-cartographer` | `skills/mathlib/mathlib-module-tree-cartographer/references/module_tree.md` |
| Mathlib declaration neighborhoods | `mathlib-declaration-neighborhood-navigator` | `skills/mathlib/mathlib-declaration-neighborhood-navigator/references/declaration_neighborhood.md` |
| Candidate `#check` verification | `mathlib-candidate-verifier` | `skills/mathlib/mathlib-candidate-verifier/SKILL.md` |
| Mathlib concept coverage review | `mathlib-concept-coverage-reviewer` | `skills/mathlib/mathlib-concept-coverage-reviewer/references/coverage.md` |
| Mathlib web search strategy | `mathlib-web-search-strategist` | `skills/mathlib/mathlib-web-search-strategist/references/source_policy.md` |
| Mathlib web evidence validation | `mathlib-web-evidence-validator` | `skills/mathlib/mathlib-web-evidence-validator/references/evidence_packet_schema.json` |
| Mathlib web grounding loop | `mathlib-web-grounding-orchestrator` | `skills/mathlib/mathlib-web-grounding-orchestrator/references/web_grounding_loop.md` |
| Mathlib import-set planning | `mathlib-import-set-builder` | `skills/mathlib/mathlib-import-set-builder/references/import_set_policy.md` |
| Lean import-context verification | `lean-import-context-verifier` | `skills/lean/lean-import-context-verifier/references/import_context_policy.md` |
| Mathlib import minimization | `mathlib-import-minimizer` | `skills/mathlib/mathlib-import-minimizer/references/import_minimization.md` |
| Mathlib API compatibility plan | `mathlib-api-compatibility-planner` | `skills/mathlib/mathlib-api-compatibility-planner/references/api_plan.md` |
| Mathlib compatibility loops | `mathlib-compatibility-loop-orchestrator` | `skills/mathlib/mathlib-compatibility-loop-orchestrator/references/loop.md` |
| Mathlib grounding maximization | `mathlib-grounding-maximizer` | `skills/mathlib/mathlib-grounding-maximizer/references/maximization_loop.md` |
| Lean compile diagnostics | `lean-compile-checker` | `skills/lean/lean-compile-checker/SKILL.md` |
| Mathlib abstraction and compatibility audit | `mathlib-abstraction-auditor` | `skills/mathlib/mathlib-abstraction-auditor/references/mathlib_abstraction_checklist.md` |
| Systematic hook routing | `autoformalization-workflow-orchestrator` | `skills/SKILL_HOOKS.yaml` |

## Shared Runtime

The implementation still lives in:

- `skills/control/workflow-contract-validator/scripts/validate_skill_hooks.py`
- `skills/control/skill-hook-coverage-maximizer/scripts/audit_skill_hook_coverage.py`
- `skills/control/reasoning-log-schema-guardian/scripts/reasoning_log.py`
- `skills/control/reasoning-log-schema-guardian/scripts/validate_reasoning_log.py`
- `skills/control/gate-policy-controller/scripts/gate_policy.py`
- `skills/autoformalization/autoformalization-reflective-refinement-loop/scripts/observe_autoformalization_process.py`
- `skills/rfde/reference-free-critic-monitor/scripts/monitor_reference_free_critics.py`
- `skills/control/skill-test-program-orchestrator/scripts/inventory_skills.py`
- `skills/control/skill-test-program-orchestrator/scripts/run_deterministic_skill_tests.py`
- `skills/control/skill-test-program-orchestrator/scripts/run_content_skill_codex_exec_tests.py`
- `skills/control/skill-test-program-orchestrator/scripts/generate_skill_test_todos.py`
- `skills/paper/paper-docling-layout-extractor/scripts/extract_paper_layout.py`
- `skills/paper/paper-main-theory-localizer/scripts/localize_paper_theory.py`
- `skills/paper/paper-theory-autoformalization-orchestrator/scripts/build_paper_theory_plan.py`
- `skills/latex-textbook/latex-archive-theory-extractor/scripts/extract_latex_theory.py`
- `skills/latex-textbook/textbook-theory-tex-organizer/scripts/organize_theory_tex.py`
- `skills/latex-textbook/textbook-autoformalization-batch-orchestrator/scripts/build_textbook_autoformalization_batch.py`
- `skills/latex-textbook/textbook-autoformalization-batch-orchestrator/scripts/run_textbook_autoformalization_batch.py`
- `skills/autoformalization/source-formalizable-unit-extractor/scripts/extract_autoformalizable_units.py`
- `skills/autoformalization/autoformalization-result-realness-verifier/scripts/verify_artifact_realness.py`
- `skills/autoformalization/autoformalization-agentc/scripts/agentc.py`
- `skills/autoformalization/autoformalization-agentc/scripts/analyze_logs.py`
- `skills/autoformalization/proof-expansion-difficulty-estimator/scripts/estimate_proof_expansion_difficulty.py`
- `skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py`
- `skills/mathlib/mathlib-hierarchy-navigator/scripts/navigate_mathlib_hierarchy.py`
- `skills/mathlib/mathlib-import-set-builder/scripts/build_import_set.py`
- `skills/lean/lean-import-context-verifier/scripts/verify_import_context.py`
- `skills/mathlib/mathlib-import-minimizer/scripts/minimize_imports.py`
- `skills/rocq/rocq-autoformalization-drafter/scripts/draft_rocq_wiki_case.py`
- `skills/rocq/rocq-execution-runner/scripts/check_rocq_file.py`
- `skills/mathlib/mathlib-compatibility-auditor/scripts/check_mathlib_compat.py`
- `skills/mathlib/mathlib-result-existence-checker/scripts/check_result_existence.py`
- `skills/mathlib/mathlib-web-search-strategist/scripts/plan_mathlib_web_search.py`
- `skills/mathlib/mathlib-web-evidence-validator/scripts/validate_mathlib_web_evidence.py`
- `skills/mathformerlib/mathformerlib-registry-manager/scripts/manage_mathformerlib_registry.py`
- `skills/mathformerlib/mathformerlib-promotion-gate/scripts/evaluate_mathformerlib_promotion.py`
- `skills/mathlib/mathlib-grounding-maximizer/scripts/maximize_mathlib_grounding.py`
- `skills/lean/lean-informalization-extractor/scripts/extract_lean_informalization.py`
- `skills/lean/lean-informal-proof-internal-consistency-verifier/scripts/verify_informal_proof_internal_consistency.py`
- `skills/lean/lean-informal-consistency-verifier/scripts/verify_informal_consistency.py`
- `skills/lean/lean-declaration-shape-consistency-checker/scripts/check_declaration_shape_consistency.py`
- `skills/lean/lean-nonvacuity-consistency-checker/scripts/check_lean_nonvacuity_consistency.py`
- `skills/lean/lean-cross-file-concept-consistency-indexer/scripts/index_cross_file_concepts.py`
- `skills/lean/lean-consistency-report-orchestrator/scripts/run_lean_consistency_report.py`

Do not duplicate runtime code across specialized skills unless a future implementation split
also updates imports, tests, and artifact compatibility.

## Hook Contract

`skills/SKILL_HOOKS.yaml` defines the systematic phase routing for the split skills. Each
hook has an owner skill, trigger condition, expected reasoning-log steps, and gates/outputs.
When adding or renaming a skill, update this hook manifest and the orchestrator workflow
reference in the same change, then run `workflow-contract-validator`.

Control hooks:

- `control.workflow_contract`: validates hook ownership, shared runtime paths, direct routing, and prompt-index references.
- `control.skill_hook_coverage`: validates non-wrapper skill reachability and named loop-contract completeness.
- `control.reasoning_log_schema`: validates JSONL event shape, event ordering, payload fields, and hook ids.
- `control.gate_policy`: normalizes phase outputs into pass, warn, fail, skip, or waived decisions.
- `reflection.process_refinement`: observes workflow artifacts and emits monotonic prompt/skill improvement opportunities.
- `critique.reference_free_monitor`: records benchmark-free critic-measure snapshots and monotonic score/risk comparisons after critique or artifact checks.
- `test.skill_program`: inventories skills, runs deterministic tests, runs Codex-exec content probes, and emits testing TODOs.
- `intake.latex_archive_theory_extract`: extracts theorem-like units and proofs from LaTeX textbook archives with source provenance and proof-pairing status.
- `preformalization.textbook_theory_organize`: groups extracted textbook theory units into source-preserving chapter/section TeX bundles.
- `draft.textbook_batch_autoformalize`: emits queued per-unit textbook autoformalization jobs that must pass the standard workflow gates before completion.
- `draft.textbook_object_autoformalization_run`: processes textbook jobs object by object and records provider, Lean, realness, and consistency evidence before any completion status.
- `artifact.realness_gate`: rejects final artifacts/reports that still contain mocks, unexecuted/planned states, proof placeholders, target axioms, or scaffold-only completion claims.
- `mathformerlib.accumulate`: coordinates controlled accumulation into `MathformerLib`.
- `mathformerlib.registry`: builds the Mathformerlib module/declaration/status registry.
- `mathformerlib.promotion_gate`: blocks accepted promotion unless realness and requested compile checks pass.
- `preformalization.result_existence_precheck`: blocks first-pass drafting until duplicate-result risk is resolved.
- `mathlib.result_existence_search`: searches local mathlib, MathformerLib, and planned official-source web surfaces for existing results.
- `mathlib.web_strategy`: plans official-source web searches from unresolved local mathlib gaps.
- `mathlib.web_evidence`: validates web-sourced mathlib claims before they influence Lean.
- `mathlib.web_grounding_loop`: coordinates local gap evidence, web search, evidence validation, and Lean verification handoffs.
- `mathlib.import.plan`: builds planned import blocks from verified module evidence.
- `mathlib.import.context`: checks expected declarations and generated Lean under intended imports.
- `mathlib.import.minimize`: deduplicates and narrows saved Lean import blocks before final claims.
- `mathlib.grounding_maximize`: coordinates cross-file import, native API, concept coverage, web grounding, scaffold/realness, compatibility, and reference-free monotonicity loops.
- `postformalization.informalize`: extracts conservative informal statements and proof narratives from final Lean declarations.
- `postformalization.informal_internal_consistency`: checks informalized proof packets for internal coherence before source/Lean round-trip consistency.
- `postformalization.informal_consistency`: verifies reverse-informalized proof consistency against source comments, realness checks, and optional Lean checks.
- `consistency.declaration_shape`: checks that source-advertised iff/existence/uniqueness/conditional shapes remain visible in Lean signatures or explicit representation-boundary notes.
- `consistency.nonvacuity`: checks theorem-like declarations for axioms, false hypotheses, target-restating assumptions, trivial conclusions, and undocumented exact-hypothesis wrappers.
- `consistency.cross_file_concepts`: indexes repeated concepts across Lean files, blocks full-name collisions, and emits MathformerLib-promotion review candidates.
- `consistency.unified_report`: runs the complete reference-free Lean consistency report and records per-layer blockers and scores.

## Legacy Snapshot

`skills/autoformalization/autoformalization-agentc/references/prompts.md` remains as a compatibility prompt-parity
snapshot. New canonical prompt edits should happen in the owning specialized skill first.
`informal-proof-mathlib-concepts` and `mathlib-compatibility-auditor` also remain as
compatibility wrappers around shared scripts.

## Validation Checklist

- [x] Each new skill has a required `SKILL.md`.
- [x] Each new user-facing skill has `agents/openai.yaml`.
- [x] Prompt-owning skills keep exact prompt bodies in one-level `references/prompts.md` files.
- [x] The old broad skills point to specialized skills and preserve shared runtimes.
- [x] ProofNet benchmark commands are no longer owned by `autoformalization-agentc`.
- [x] Mathlib lookup is split into candidate mapping and candidate verification.
- [x] Mathlib hierarchy navigation is split into module-tree cartography, declaration-neighborhood inspection, and orchestration.
- [x] Mathlib compatibility has a pre-draft concept-coverage loop and coverage-aware API planning hook.
- [x] Mathlib grounding has a web-search complement that prefers official sources and routes claims back to local Lean verification.
- [x] Mathlib import management is split into import-set building, import-context verification, and import minimization hooks.
- [x] Compatibility review is split into Lean compile checking and abstraction auditing.
- [x] Systematic skill application is defined in `skills/SKILL_HOOKS.yaml`.
- [x] Systematic skill application has a validator in `workflow-contract-validator`.
- [x] Systematic skill application has hook coverage and loop-contract auditing in `skill-hook-coverage-maximizer`.
- [x] Reasoning-log schema has a shared append helper and validator in `reasoning-log-schema-guardian`.
- [x] Gate semantics have a reusable decision controller in `gate-policy-controller`.
- [x] Full-process reflection has a monotonic improvement loop in `autoformalization-reflective-refinement-loop`.
- [x] Skill validation has an aggressive deterministic and Codex-exec content testing program in `skill-test-program-orchestrator`.
- [x] LaTeX textbook archives have extraction, thematic TeX organization, and truthful queued batch autoformalization skills.
- [x] Final autoformalization outputs have a deterministic realness gate in `autoformalization-result-realness-verifier`.
- [x] Final Lean artifacts have reverse informalization, informal-proof internal consistency, proof-consistency, declaration-shape, non-vacuity, cross-file concept, and unified consistency gates in the `lean-*consistency*` skill stack.
- [x] Reusable accumulated formalizations have Mathformerlib registry and promotion gates.
- [x] Duplicate-result prevention has a pre-draft gate over MathformerLib, local mathlib, and official-source mathlib web search.
- [x] Proof expansion support now estimates per-segment difficulty and routes hard segments to web-backed research before expansion.
- [x] Pre-autoformalization LaTeX expansion review is split into completeness, binding, and suite orchestration skills.
- [x] Critique passes are split into syntax, semantic preservation, logical soundness, mathlib alignment, and suite orchestration.
- [x] Repository validation after the latest runtime split passed on 2026-07-08 via `python scripts/mathformer.py ask "make sure every workflow is controlled" --run --json` and `python scripts/mathformer.py ask "run the compact quality gate before commit" --run --json`, covering prompt-index/hook parity, reasoning-log smoke checks, and a smoke workflow.
