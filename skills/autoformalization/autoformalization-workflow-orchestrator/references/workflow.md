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

# Autoformalization Workflow Reference

## Runtime Ownership Map

- `LatexExpansionAgent`: `latex-prerequisite-expander`
- proof expansion support loop: `proof-expansion-support-orchestrator`
- LaTeX textbook archive theory extraction: `latex-archive-theory-extractor`
- textbook theory TeX organization: `textbook-theory-tex-organizer`
- textbook per-unit autoformalization batch queue and object runner: `textbook-autoformalization-batch-orchestrator`
- proof expansion difficulty scoring: `proof-expansion-difficulty-estimator`
- proof expansion web research packets: `proof-expansion-web-researcher`
- `LatexExpansionCompletenessReviewAgent`: `latex-expansion-completeness-reviewer`
- `LatexExpansionBindingReviewAgent`: `latex-expansion-binding-reviewer`
- LaTeX expansion review suite: `latex-expansion-review-orchestrator`
- `AutoformalizationAgent`: `lean-autoformalization-drafter`
- initial generated-code Lean execution: `lean-execution-runner`
- local Isabelle/HOL and optional IsarMathLib grounding: `isarmathlib-grounding-navigator`
- initial generated Isabelle/HOL theory drafting: `isabelle-autoformalization-drafter`
- initial generated-code Isabelle execution: `isabelle-execution-runner`
- SymPy dependency probe and installed API index: `sympy-dependency-prober`, `sympy-api-docs-indexer`
- SymPy source parsing, assumptions, and API grounding: `sympy-expression-parser`, `sympy-assumption-modeler`, `sympy-concept-grounding-navigator`
- SymPy executable artifact drafting: `sympy-autoformalization-drafter`
- SymPy execution, identity validation, counterexample search, and trace verification: `sympy-execution-runner`, `sympy-identity-validator`, `sympy-counterexample-searcher`, `sympy-transformation-trace-verifier`
- SymPy reference-free consistency reporting: `sympy-consistency-report-orchestrator`
- `FormalRefinementAgent`: `lean-formal-refinement`
- `InformalRefinementAgent`: `lean-formal-refinement`
- `SoftCritiqueAgent`: `lean-critique-and-judging`
- named syntax/semantic/logical/mathlib critique passes: `lean-critique-suite-orchestrator`
- `DenoisingAgent`: `lean-output-denoiser`
- `LeanLineAnnotationAgent` and generated Lean source-comment/semantic-alignment guard: `lean-line-annotation`
- `RefinementTaxonomyAgent`: `lean-refinement-taxonomy`
- `HardCritiqueAgent`: `autoformalization-workflow-orchestrator`
- `ImportRetrievalAgent`: `autoformalization-workflow-orchestrator`
- `IterativeSelfRefinementAgentC`: `autoformalization-workflow-orchestrator`
- hook coverage and named loop-contract audit: `skill-hook-coverage-maximizer`
- result-existence precheck before drafting: `result-existence-precheck-orchestrator`
- duplicate-result search report: `mathlib-result-existence-checker`
- `map_mathlib_concepts.py` discovery mode: `mathlib-concept-candidate-mapper`
- `navigate_mathlib_hierarchy.py`: `mathlib-hierarchy-navigator`
- module-prefix cartography: `mathlib-module-tree-cartographer`
- focused declaration neighborhoods: `mathlib-declaration-neighborhood-navigator`
- `map_mathlib_concepts.py --verify-checks`: `mathlib-candidate-verifier`
- concept coverage scoring: `mathlib-concept-coverage-reviewer`
- coverage-aware API plan: `mathlib-api-compatibility-planner`
- import-set planning: `mathlib-import-set-builder`
- import-context verification: `lean-import-context-verifier`
- import minimization: `mathlib-import-minimizer`
- concept and audit compatibility loops: `mathlib-compatibility-loop-orchestrator`
- artifact-set grounding maximization loops: `mathlib-grounding-maximizer`
- raw `lake env lean` / structured `lake_check`: `lean-compile-checker`
- `check_mathlib_compat.py` heuristic audit/scoring: `mathlib-abstraction-auditor`
- final artifact/report realness check: `autoformalization-result-realness-verifier`
- benchmark-free critic-measure trend snapshots: `reference-free-critic-monitor`
- reverse Lean-to-informal proof extraction: `lean-informalization-extractor`
- internal consistency of reverse-informal proof packets: `lean-informal-proof-internal-consistency-verifier`
- reverse informal proof consistency gate: `lean-informal-consistency-verifier`
- declaration-shape consistency gate: `lean-declaration-shape-consistency-checker`
- non-vacuity consistency gate: `lean-nonvacuity-consistency-checker`
- cross-file concept consistency index: `lean-cross-file-concept-consistency-indexer`
- unified Lean consistency report: `lean-consistency-report-orchestrator`

The shared runtime currently remains in `../autoformalization-agentc/scripts/agentc.py`.
The mathlib lookup runtime remains in `../informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py`.
The compatibility audit runtime remains in `../mathlib-compatibility-auditor/scripts/check_mathlib_compat.py`.
Do not duplicate shared scripts into specialized skills unless a later implementation split
changes the runtime APIs.

## Systematic Workflow

`IterativeSelfRefinementAgentC.run_systematic_workflow(...)` standardizes repeated tasks:

1. normalize informal LaTeX/markdown input,
2. if the input is a LaTeX textbook archive/source tree, extract theorem-like units, organize thematic TeX bundles, and emit queued per-unit jobs before any Lean drafting claims are made,
3. estimate proof-part expansion difficulty and decide whether web support is needed,
4. run source-backed web support for flagged hard/research proof parts,
5. expand prerequisite definitions/theorems using any support packet,
6. review the expanded LaTeX for completeness and binding discipline,
7. check whether the target result already exists in MathformerLib, local mathlib, or official-source mathlib web search,
8. recursively autoformalize dependency statements,
9. branch on the selected backend: for Lean, map statements to mathlib concepts/modules, navigate relevant module hierarchy, and verify top candidates; for Isabelle/HOL, search local Isabelle sessions and optional IsarMathLib theories for grounding candidates; for SymPy, probe dependencies, build a local API index, parse expressions, model assumptions, and ground concepts into installed APIs for the selected symbolic style,
10. run the mathlib concept compatibility loop until extracted concepts are verified or bounded gaps are recorded,
11. build an intended import set from verified modules, hierarchy context, and fixture import metadata,
12. verify expected declarations under the intended import set before prompt hints rely on them,
13. run whole-artifact mathlib grounding maximization when concept/import/web evidence, scaffold cleanup, or cross-file consistency still has unresolved risk,
14. build coverage-aware alignment hints and feed dependency formalizations, verified imports, hierarchy context, plus mathlib or IsarMathLib hints into drafting/refinement prompts,
15. generate an initial formalization with source-aware module/declaration comments or source-aware executable artifact comments using the selected backend drafter,
16. run the generated Lean source-comment and semantic-alignment guard before execution,
17. execute the initial formalization with the selected backend runner,
18. run backend-specific validation: Lean compile/typecheck, Isabelle build checks, or SymPy identity validation plus bounded counterexample search and trace verification,
19. trigger iterative refinement only when needed,
20. re-run the source-comment and semantic-alignment guard after denoising or refinement,
21. minimize/deduplicate the import block and re-run import-context checks when expected declarations are known,
22. save final code to disk only after source-comment hygiene and import status are explicit,
23. run a post-save hard critique,
24. run LLM judge critiques for conceptual, formal, and semantic preservation aspects,
25. save per-round Lean snapshots,
26. classify recorded refinement states,
27. save history, structured JSON report, JSONL reasoning log, and source-comment report,
28. generate process statistics as JSON and LaTeX,
29. run mathlib grounding maximization plus mathlib abstraction/compatibility auditing and use those scores for outer-cycle gating,
30. informalize the final Lean artifact into source-preserving statement/proof packets,
31. run declaration-shape consistency on the source-preserving packet,
32. run internal consistency verification on the informalized proof packet,
33. run reverse informal proof consistency verification, optionally with `lake env lean`, before final acceptance,
34. run non-vacuity consistency to catch axioms, false hypotheses, target-restating assumptions, and undocumented exact-hypothesis wrappers,
35. run cross-file concept indexing over the touched artifact set and route repeated concepts to MathformerLib review when appropriate,
36. run the final realness gate on saved Lean/report/history artifacts,
37. run the unified Lean consistency report and persist its per-layer blockers and scores,
38. if the source-comment, import, grounding, declaration-shape, reverse-informalization, non-vacuity, cross-file, unified-report, or realness gate finds missing semantic declaration comments, broad-only imports, source-shape mismatches, internally incoherent proof packets, unsupported proof delegations, mocks, planned/unexecuted states, `sorry`/`admit`, target `axiom`s, vacuous target restatements, or scaffold-only claims, report the artifact as `draft` or `blocked` and route it back to refinement rather than counting it complete,
39. run reference-free critic monitoring and compare score/risk trends against the accepted snapshot without requiring a benchmark or gold formalization,
40. prioritize high-leverage structural fixes before cosmetic rewrites.

## Hook Contract

`../SKILL_HOOKS.yaml` is the machine-readable phase contract for the split skills. Use it
as the source of truth when deciding which skill owns a phase, when a conditional skill should
run, and which reasoning-log steps prove the hook fired.

Rules:

- Every end-to-end workflow run starts with `intake.workflow_start`.
- Every phase-specific reasoning-log payload should include `skill`; when available, include `hook_id`.
- LaTeX textbook archive extraction belongs to `intake.latex_archive_theory_extract`; thematic source-preserving TeX organization belongs to `preformalization.textbook_theory_organize`; per-unit queued jobs belong to `draft.textbook_batch_autoformalize`; object-by-object execution belongs to `draft.textbook_object_autoformalization_run`.
- Hook and loop coverage belongs to `control.skill_hook_coverage`; it should pass after adding skills, hooks, direct routes, shared runtimes, or named loop contracts.
- Isabelle/IsarMathLib grounding belongs to `isabelle.grounding.search`; local theory claims must cite existing `.thy` files, and missing IsarMathLib is acceptable only when the artifact relies on installed Isabelle/HOL sessions.
- Proof expansion support belongs to `preformalization.expansion_support`, difficulty estimation belongs to `preformalization.expansion_difficulty`, and web-backed support belongs to `preformalization.expansion_web_support`.
- LaTeX expansion review belongs to `preformalization.review.suite`; its reviewer passes belong to `preformalization.review.completeness` and `preformalization.review.bindings`.
- Result-existence gating belongs to `preformalization.result_existence_precheck`; its deterministic local/mathlib web-plan search belongs to `mathlib.result_existence_search`.
- Concept mapping without `--verify-checks` belongs to `mathlib.discovery`.
- Hierarchical module navigation belongs to `mathlib.hierarchy.navigate`, `mathlib.hierarchy.module_tree`, and `mathlib.hierarchy.declaration_neighborhood`.
- Concept mapping with `--verify-checks` also fires `mathlib.verify`.
- Bounded widening of concept search/verification belongs to `mathlib.compatibility_loop`.
- Concept coverage summaries belong to `mathlib.coverage`.
- Artifact-set grounding maximization belongs to `mathlib.grounding_maximize`; it coordinates import, native API, concept coverage, web grounding, scaffold/realness, and monotonicity loops across one or more Lean files.
- Coverage-aware prompt hints belong to `mathlib.api_plan`.
- Import-set planning belongs to `mathlib.import.plan`.
- Expected declaration and generated-file import verification belong to `mathlib.import.context`.
- Import block minimization belongs to `mathlib.import.minimize`.
- Generated Lean source-comment hygiene and semantic declaration coverage belongs to `annotate.line_comment_guard`.
- Initial Isabelle/HOL drafting belongs to `draft.isabelle_initial`; initial Isabelle/HOL execution belongs to `execute.isabelle_initial`.
- SymPy equational-trace runs belong to `sympy_equational_trace_loop`; they must pass through dependency probing, local API indexing, expression parsing, assumption modeling, API grounding, executable drafting, execution, identity validation, counterexample search, trace verification, and `consistency.sympy_report`.
- The first Lean run after initial formalization belongs to `execute.initial`.
- Lean compiler events belong to `check.compile`, even when they are emitted from the compatibility-auditor script.
- Compatibility scoring and abstraction findings belong to `audit.compatibility`.
- Final checks that an artifact is not mocked, unexecuted, placeholder-based, noisy with legacy per-line or syntax-only comments, missing semantic declaration comments, or a scaffold claimed as complete belong to `artifact.realness_gate`.
- Named critique passes belong to `critique.syntax`, `critique.semantic_preservation`, `critique.logical_soundness`, `critique.mathlib_alignment`, and `critique.suite`.
- Reference-free critic-measure monitoring belongs to `critique.reference_free_monitor`; it is required before accepting prompt/skill changes when no benchmark is being used as the main evaluation surface.
- Reverse Lean-to-informal extraction belongs to `postformalization.informalize`; it produces structured source/proof packets from the final Lean file without inventing missing mathematics.
- Internal proof-packet consistency belongs to `postformalization.informal_internal_consistency`; it checks the extracted informal statement/proof/dependency packet for circularity, missing proof narratives, placeholder traces, and proof-shape incoherence before that packet is used as evidence.
- Reverse informal proof consistency belongs to `postformalization.informal_consistency`; it blocks final acceptance when extracted proof packets expose source-shape drift, hard realness failures, target axioms, or optional Lean-check failures.
- Declaration-shape consistency belongs to `consistency.declaration_shape`; it blocks final acceptance when source-advertised iff, existence, uniqueness, or conditional shapes are missing from the Lean declaration without an explicit representation boundary.
- Non-vacuity consistency belongs to `consistency.nonvacuity`; it blocks final acceptance for axioms, false-hypothesis vacuity, target-restating assumptions, and undocumented exact-hypothesis wrappers.
- Cross-file concept indexing belongs to `consistency.cross_file_concepts`; it blocks full-name collisions and records divergent/repeated concept families as promotion or review candidates.
- The unified Lean consistency report belongs to `consistency.unified_report`; it runs the complete reference-free consistency stack and persists per-layer blockers and scores.
- Every code-changing refinement should be followed by `transition.taxonomy`.
- Final artifacts and statistics should be emitted through `artifact.statistics` only after `postformalization.informal_internal_consistency`, `postformalization.informal_consistency`, `consistency.declaration_shape`, `consistency.nonvacuity`, `consistency.cross_file_concepts`, `consistency.unified_report`, and `artifact.realness_gate` have made the final/draft/blocked status explicit.

## Recursive Dependencies

`run_systematic_workflow(...)` accepts nested dependency inputs:

- `str`
- `{"informal_statement": "...", "label": "...", "dependencies": [...]}`
- `RecursiveDependencyInput(...)`

Each dependency runs through the same systematic workflow and the resulting formalizations
are reused as parent prompt context.

## Multi-Cycle Refinement

`run_multi_cycle_systematic_workflow(...)` runs outer refinement cycles:

- cycle 1 runs the standard systematic workflow,
- cycle `k > 1` can seed from cycle `k-1` final Lean code,
- each cycle writes separate `.lean`, `.history.json`, and `.report.json` artifacts,
- each cycle records compatibility-audit results and Lean correctness,
- a cycle manifest JSON tracks all versions.

By default, first/top-level `run_systematic_workflow(...)` calls are score-gated:

- stop when compatibility score reaches `100`, or
- stop when the outer-cycle cap reaches `20`.

Override with constructor or call arguments such as `default_first_formalization_cycles`,
`default_target_compatibility_score`, `default_max_score_gated_cycles`,
`compatibility_target_score`, `enable_compatibility_audit=False`, or
`enable_default_multi_cycle=False`.

## Artifacts

When output paths are omitted, workflow artifacts are created under
`artifacts/autoformalization/` with a deterministic `<statement-slug>_<hash>` stem.

Expected artifact families:

- final `.lean`
- `.history.json`
- `.report.json`
- reasoning-log `.jsonl`
- per-round `.round_XX.lean`
- per-cycle `.cycle_XX.*` files when applicable
- `.stats.json`
- `.stats.tex`
- cycle manifest JSON for multi-cycle runs

Final reports must record whether each artifact is `complete`, `draft`, or `blocked`.
Do not describe an artifact as complete when the realness gate still reports blocking
findings. Honest interface scaffolds may be saved as drafts, but they must not be
counted as completed theorem-level autoformalizations.

Reasoning-log events include timing fields:

- `event_index`
- `timestamp_utc`
- `timestamp_unix_ms`
- `elapsed_ms_since_log_start`
- `elapsed_ms_since_prev_event`

Hard-critique events include Lean error log path/content when available:

- `lean_error_log_file`
- `lean_error_log`
