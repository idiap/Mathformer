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

# Mathformer Framework Documentation

This document explains the controlled workflow framework, with detailed coverage
of its Lean/mathlib formalization path, iterative critique-refinement, and process
analytics. Mathformer also includes Vampire ATP, SymPy, Rocq, Isabelle, premise-KB,
and physics workflows. Their execution and validation contracts are described in
the [backend guides](../backends/); the Lean-oriented component details below are
one specialization rather than an exhaustive backend catalog.
For a shorter conceptual map and vocabulary, start with
[main concepts](MAIN_CONCEPTS.md). For the framework principles and trust rules,
read [principles](PRINCIPLES.md). For controlled repository actions, start with
the [AgenticHub](AGENTIC_HUB.md). For the Rocq proof-script backend, read the
[Rocq backend guide](../backends/ROCQ_BACKEND.md).

## 1. Purpose

Mathformer combines:
- a Lean4 + mathlib workspace for generated formalizations,
- a Rocq proof-script backend for controlled `.v` autoformalizations,
- a natural-language agent interface backed by AgenticHub,
- reusable skills for autoformalization and mathlib concept mapping,
- an iterative orchestration loop with theorem-prover and LLM critique,
- structured logging and statistics artifacts for process analysis.

The framework is designed to produce traceable autoformalization runs, not only final Lean files.

## 2. Repository Components

## 2.0 Natural-Language Interface And AgenticHub

The user-facing entry point is a natural-language request to an agent:

> Prove the inverse-of-product theorem in group theory with Vampire and show me
> the proof artifact.

The deterministic adapter underneath that request is:

```bash
python scripts/mathformer.py ask "prove the inverse-of-product group theorem with Vampire" --json
```

The adapter resolves ordinary language to skill routes and controlled workflow
actions. The hub beneath it owns common setup, validation, backend demos,
generation workflows, and quality gates. Each action has a stable id, safety
label, exact argv command, required paths, required tools, optional tools, and
declared write locations. Actions that update tracked repository files or local
environment state require `--allow-mutating`; every action can be inspected and
dry-run before execution.

The hub audit is the top-level control check:

```bash
python scripts/mathformer.py audit --strict --json
```

It treats an entrypoint as controlled when it is registered in the hub, covered
by the comprehensive test matrix, or governed by `skills/SKILL_HOOKS.yaml`.

## 2.1 Lean Layer

Core Lean modules:
- `backends/lean/Mathformer/Basic.lean`: minimal sanity module.
- `backends/lean/Mathformer/AutoformalizedExamples.lean`: example generated outputs.
- `backends/lean/Mathformer/AutoformalizedSazonov.lean`: interface-level scaffold for Sazonov-style statements.
- `backends/lean/Mathformer/AutoformalizedHilleYosida.lean`: interface-level scaffold for Hille--Yosida-style statements.
- `libraries/MathformerLib.lean`: root module for the curated parallel Mathformerlib library.
- `libraries/MathformerLib/`: accepted reusable formalizations promoted through Mathformerlib gates.
- `backends/lean/Mathformer.lean`: root library imports.
- `backends/lean/Main.lean`: executable entrypoint.

These files are built with:
- `lakefile.toml`
- `lean-toolchain`
- `lake-manifest.json`

## 2.2 Skills Layer

### Systematic Skill Hooks
- Hook contract: `skills/SKILL_HOOKS.yaml`
- Ownership index: `skills/ALL_AGENT_SKILL_PROMPTS.md`
- Workflow orchestrator: `skills/autoformalization/autoformalization-workflow-orchestrator/`
- Hook contract validator: `skills/control/workflow-contract-validator/`
- Hook coverage maximizer: `skills/control/skill-hook-coverage-maximizer/`
- Reasoning-log schema guardian: `skills/control/reasoning-log-schema-guardian/`
- Gate policy controller: `skills/control/gate-policy-controller/`
- Reflective process improvement loop: `skills/autoformalization/autoformalization-reflective-refinement-loop/`
- Reference-free critic monitor: `skills/rfde/reference-free-critic-monitor/`
- Aggressive skill test program: `skills/control/skill-test-program-orchestrator/`
- Final result realness gate: `skills/autoformalization/autoformalization-result-realness-verifier/`

### Shared Skill Runtimes
- Hook/routing validator: `skills/control/workflow-contract-validator/scripts/validate_skill_hooks.py`
- Hook/loop coverage auditor: `skills/control/skill-hook-coverage-maximizer/scripts/audit_skill_hook_coverage.py`
- Shared reasoning logger: `skills/control/reasoning-log-schema-guardian/scripts/reasoning_log.py`
- Reasoning-log validator: `skills/control/reasoning-log-schema-guardian/scripts/validate_reasoning_log.py`
- Gate decision normalizer: `skills/control/gate-policy-controller/scripts/gate_policy.py`
- Reflective process observer: `skills/autoformalization/autoformalization-reflective-refinement-loop/scripts/observe_autoformalization_process.py`
- Reference-free critic monitor: `skills/rfde/reference-free-critic-monitor/scripts/monitor_reference_free_critics.py`
- Skill inventory: `skills/control/skill-test-program-orchestrator/scripts/inventory_skills.py`
- Deterministic skill tests: `skills/control/skill-test-program-orchestrator/scripts/run_deterministic_skill_tests.py`
- Codex-exec content probes: `skills/control/skill-test-program-orchestrator/scripts/run_content_skill_codex_exec_tests.py`
- Skill testing TODO generator: `skills/control/skill-test-program-orchestrator/scripts/generate_skill_test_todos.py`
- Result realness verifier: `skills/autoformalization/autoformalization-result-realness-verifier/scripts/verify_artifact_realness.py`
- Rocq drafter: `skills/rocq/rocq-autoformalization-drafter/scripts/draft_rocq_wiki_case.py`
- Rocq execution runner: `skills/rocq/rocq-execution-runner/scripts/check_rocq_file.py`
- Result-existence checker: `skills/mathlib/mathlib-result-existence-checker/scripts/check_result_existence.py`
- Mathformerlib registry: `skills/mathformerlib/mathformerlib-registry-manager/scripts/manage_mathformerlib_registry.py`
- Mathformerlib promotion gate: `skills/mathformerlib/mathformerlib-promotion-gate/scripts/evaluate_mathformerlib_promotion.py`
- AgentC runtime: `skills/autoformalization/autoformalization-agentc/scripts/agentc.py`
- Mathlib lookup runtime: `skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py`
- Mathlib import-set builder: `skills/mathlib/mathlib-import-set-builder/scripts/build_import_set.py`
- Lean import-context verifier: `skills/lean/lean-import-context-verifier/scripts/verify_import_context.py`
- Mathlib import minimizer: `skills/mathlib/mathlib-import-minimizer/scripts/minimize_imports.py`
- Compatibility audit runtime: `skills/mathlib/mathlib-compatibility-auditor/scripts/check_mathlib_compat.py`
- Mathlib web search planner: `skills/mathlib/mathlib-web-search-strategist/scripts/plan_mathlib_web_search.py`
- Mathlib web evidence validator: `skills/mathlib/mathlib-web-evidence-validator/scripts/validate_mathlib_web_evidence.py`
- Mathlib indexing/control TODOs: [mathlib indexing plan](../operations/MATHLIB_INDEXING_CONTROL_TODOS.md)

The old broad skill folders are compatibility wrappers. Canonical phase guidance lives in
the split skills named in `skills/SKILL_HOOKS.yaml`.

## 2.3 Benchmark Layer

ProofNet tooling:
- `benchmarks/proofnet/proofnet.py`
- `benchmarks/proofnet/evaluate_predictions.py`

## 2.4 Test Inputs (LaTeX)

Reference theorem fixtures:
- `tests/latex/hille_yosida_theorem.tex`
- `tests/latex/sazonov_theorem.tex`

## 3. Agent Architecture

Implemented in `agentc.py`:
- `workflow-contract-validator`: validates hook ids, owner skills, shared runtime paths, direct request routes, prompt-index references, and optional reasoning-log evidence.
- `skill-hook-coverage-maximizer`: audits that non-wrapper skills are reachable through hooks or direct routes and that named loop contracts contain required hooks and owner skills.
- `reasoning-log-schema-guardian`: emits and validates canonical reasoning-log JSONL events.
- `gate-policy-controller`: normalizes heterogeneous phase results into stable gate decisions with waiver records.
- `autoformalization-reflective-refinement-loop`: observes full workflow artifacts and proposes prompt/skill improvements guarded by monotonic non-regression gates.
- `reference-free-critic-monitor`: records benchmark-free measures across prover health, placeholder freedom, logical non-vacuity, semantic anchors, mathlib grounding, critic agreement, and artifact substance.
- `skill-test-program-orchestrator`: inventories all skills, runs deterministic tests, runs Codex-exec content probes, and generates self-explanatory testing TODOs.
- `autoformalization-result-realness-verifier`: blocks final reports that still contain mocks, unexecuted states, `sorry`/`admit`, target `axiom`s, or scaffold-only complete claims.
- `mathformerlib-accumulation-orchestrator`: coordinates movement of reusable results into the parallel `MathformerLib` library.
- `mathformerlib-registry-manager`: catalogs Mathformerlib modules, declarations, imports, and draft/candidate/accepted statuses.
- `mathformerlib-promotion-gate`: requires realness and requested compile checks before accepted promotion.
- `result-existence-precheck-orchestrator`: blocks first-pass drafting until existing mathlib or MathformerLib results are ruled out.
- `mathlib-result-existence-checker`: ranks duplicate candidates from local mathlib search, MathformerLib, and official-source web-search plans.
- `proof-expansion-support-orchestrator`: coordinates pre-expansion difficulty scoring and web-backed support packets.
- `proof-expansion-difficulty-estimator`: scores proof segments and decides where external support is needed.
- `proof-expansion-web-researcher`: collects source-backed statements, hypotheses, and uncertainty notes for hard proof segments.
- `LatexExpansionAgent`: expands prerequisites/implicit assumptions in LaTeX form.
- `LatexExpansionCompletenessReviewAgent`: checks expanded LaTeX for prerequisite, assumption, side-condition, and conclusion coverage before drafting.
- `LatexExpansionBindingReviewAgent`: checks expanded LaTeX for binders, quantifiers, free variables, domains, indices, arities, references, and notation before drafting.
- `mathlib-hierarchy-navigator`: navigates mathlib from broad prefixes to concrete modules, siblings, and query results.
- `mathlib-module-tree-cartographer`: maps parent/child/sibling module structure and leaf counts.
- `mathlib-declaration-neighborhood-navigator`: inspects focused module imports, declarations, and source references.
- `mathlib-compatibility-loop-orchestrator`: widens concept discovery and verification until extracted concepts have verified mathlib coverage or explicit gaps.
- `mathlib-concept-coverage-reviewer`: reports verified candidate coverage, candidate-only coverage, and gaps for each extracted concept.
- `mathlib-web-search-strategist`: plans official-source web searches for unresolved local mathlib gaps.
- `mathlib-web-evidence-validator`: validates web-sourced API claims, source provenance, and local verification status.
- `mathlib-web-grounding-orchestrator`: coordinates local gap evidence, official-source web search, evidence validation, and Lean verification handoff.
- `mathlib-import-set-builder`: turns verified modules, hierarchy results, fixture metadata, and existing imports into a narrow planned import block.
- `lean-import-context-verifier`: checks expected declarations and generated Lean under intended imports instead of only under broad `import Mathlib`.
- `mathlib-import-minimizer`: deduplicates and, when requested, compile-checks removal of unnecessary imports after Lean generation.
- `mathlib-api-compatibility-planner`: turns verified declarations/imports and residual gaps into drafting/refinement hints.
- `AutoformalizationAgent`: generates initial Lean/Isabelle formalization.
- `rocq-autoformalization-drafter`: generates controlled Rocq `.v` proof scripts from source fixtures.
- `rocq-execution-runner`: validates Rocq proof artifacts structurally and invokes `rocq compile` or `coqc` when available.
- `lean-execution-runner`: executes the initial generated Lean artifact before refinement decisions.
- `HardCritiqueAgent`: runs theorem-prover checks (Lean uses `lake env lean` backend option).
- `SoftCritiqueAgent`: semantic/aspect critique with binary judgement + explanation.
- Named critique-pass skills cover Lean syntactic correctness, semantic preservation, logical soundness, mathlib alignment, and critique-suite orchestration.
- `FormalRefinementAgent`: Lean-error-driven repair/refinement.
- `InformalRefinementAgent`: semantic-preservation/alignment-driven refinement.
- `DenoisingAgent`: output cleaning helper.
- `LeanLineAnnotationAgent`: line-by-line natural-language annotation of Lean files and generated Lean source-comment/semantic-alignment guarding.
- `RefinementTaxonomyAgent`: per-transition classification over refinement trigger, reasoning mode, syntactic edits, semantic edits, artifact effects, and preservation risk.
- `IterativeSelfRefinementAgentC`: orchestrates end-to-end and multi-cycle workflows.

Core report dataclasses:
- `IterativeRefinementState`
- `LLMJudgeCritique`
- `SystematicAutoformalizationReport`

## 4. Workflow Model

`run_systematic_workflow(...)` is the main entry point.

Pipeline stages:
0. Validate control contracts when hooks, routing, shared runtimes, or reasoning logs are part of the run.
1. Normalize informal input (LaTeX/markdown cleanup).
2. Optional proof expansion difficulty estimation and web-backed support for hard segments.
3. Optional LaTeX expansion (prerequisite surfacing).
4. Optional LaTeX expansion review for completeness and binding discipline before drafting.
5. Result-existence precheck against MathformerLib, local mathlib, and official-source mathlib web search.
6. Recursive dependency autoformalization (same pipeline per dependency).
7. Optional concept-to-mathlib mapping, hierarchy navigation, and Lean `#check` verification.
8. Mathlib concept compatibility loop and coverage review.
9. Optional web-assisted mathlib grounding for unresolved local gaps, followed by evidence validation and local Lean verification handoff.
10. Import-set planning and import-context verification for expected declarations.
11. Coverage-aware mathlib API and hierarchy hint synthesis.
12. Extract core statement alignment annotations from source text.
13. Generate initial formalization (or use seeded formalization).
14. Run hard critique (Lean check).
15. Run soft critique.
16. Iterate formal/informal refiners until stop condition or max iterations.
17. Minimize/deduplicate generated imports when the artifact is saved.
18. Save final Lean file.
19. Re-run final hard critique on saved file.
20. Optionally run LLM judges:
   - conceptual/mathematical consistency
   - formal consistency
   - semantic preservation
21. Run reference-free critic monitoring to snapshot benchmark-free internal correctness proxies and compare them with the accepted baseline.
22. Save round-by-round Lean snapshots.
23. Classify each recorded refinement state with a stable taxonomy and attach per-round timings.
24. Save history/report/reasoning logs.
25. Save statistics artifacts (JSON + LaTeX report).
26. Optionally run reflective process observation to produce monotonic prompt/skill improvement packets.
27. Run aggressive skill tests before accepting prompt or skill changes.

## 4.1 Default Multi-Cycle Behavior

Top-level first formalizations default to 3 outer cycles:
- configurable via `default_first_formalization_cycles`,
- implemented through `run_multi_cycle_systematic_workflow(...)`,
- cycles can carry forward previous final code as seed.

Cycle outputs are tracked with a cycle manifest.

## 4.2 Recursive Dependencies

Dependency input supports:
- raw strings,
- dict schema (`informal_statement`, optional `label`, nested `dependencies`),
- `RecursiveDependencyInput`.

Behavior:
- recursive calls use the same systematic workflow,
- dependency cache avoids duplicate formalization,
- cycle detection prevents recursive loops on repeated normalized statements.

## 5. Alignment and Prompt Guarantees

The framework enforces:
- source-aware module/declaration comments in generation/refinement prompts, preserving original natural-language/LaTeX equivalents and generated support notes, with blank lines allowed and legacy per-line `NL/LaTeX:` comments rejected,
- source-to-Lean alignment hints from extracted core LaTeX theorem statements,
- optional mathlib alignment hints from concept mapping.

Skill ownership and hook inventory:
- `skills/ALL_AGENT_SKILL_PROMPTS.md`
- `skills/SKILL_HOOKS.yaml`

## 6. Artifacts and Naming

Default outputs are generated under:
- `artifacts/autoformalization/`

Default naming uses:
- statement slug + short hash
- e.g. `<slug>_<hash>.lean`

Typical artifact set:
- final Lean file: `*.lean`
- iterative history: `*.history.json`
- workflow report: `*.report.json`
- reasoning log: `*.reasoning.jsonl`
- statistics JSON: `*.stats.json`
- statistics LaTeX: `*.stats.tex`
- round snapshots: `*.versions/*.round_XX.lean`
- multi-cycle manifest: `*.cycles.manifest.json`

## 7. Reasoning Log Schema

Each JSONL event includes:
- `event_index`
- `timestamp_utc`
- `timestamp_unix_ms`
- `monotonic_ns`
- `elapsed_ms_since_log_start`
- `elapsed_ms_since_prev_event`
- `payload.skill`
- `payload.hook_id` when the event belongs to a systematic hook
- `statement_hash`
- `file_prefix`
- `dependency_label`
- `step`
- `payload`

This enables per-step timing and process-duration reconstruction.

Lean diagnostics are also captured in hard-critique events when available:
- `lean_error_log_file`
- `lean_error_log`

## 8. Statistics Pipeline

Implemented in:
- `build_autoformalization_statistics(...)`
- `save_autoformalization_statistics(...)`
- standalone CLI: `skills/autoformalization/autoformalization-agentc/scripts/analyze_logs.py`

Computed metrics include:
- cycle and dependency counts,
- reasoning event and process duration stats,
- skill event counts and per-skill durations,
- hard critique pass/fail counts,
- Lean error categories and top error lines,
- refinement-dynamics counts by trigger family, primary refinement type, reasoning mode, syntactic edit type, semantic edit type, artifact effect, and preservation risk,
- per-round refinement timing summaries and round-by-round taxonomy annotations,
- Lean file evolution across round snapshots,
- declaration/doc-comment/sorry counts.

## 9. How To Run

## 9.1 Build Lean Project

```bash
lake update
lake build
```

## 9.2 Run Concept Mapper

```bash
python3 skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py \
  --proof-file tests/latex/sazonov_theorem.tex \
  --top-k 10 \
  --top-modules 12 \
  --json
```

## 9.3 Plan Web-Assisted Mathlib Grounding

```bash
python3 skills/mathlib/mathlib-web-search-strategist/scripts/plan_mathlib_web_search.py \
  --concept monotone \
  --concept compactness \
  --json

python3 skills/mathlib/mathlib-web-evidence-validator/scripts/validate_mathlib_web_evidence.py \
  --self-test \
  --json
```

## 9.4 Analyze Existing Autoformalization Report

```bash
python3 skills/autoformalization/autoformalization-agentc/scripts/analyze_logs.py \
  --report-file artifacts/autoformalization/<run>.report.json
```

## 9.5 Run Controlled Wikipedia-Level Suite

```bash
python3 tests/wiki_level/run_suite.py
```

This deterministic calibration pass runs static LaTeX checks, proof-expansion
difficulty scoring, verified concept-to-mathlib mapping, hierarchy navigation,
expected declaration `#check`s, Lean execution, and compatibility auditing over
the controlled cases in `tests/latex/wiki_level/`.

## 9.5 Run Control Validators

```bash
python3 skills/control/workflow-contract-validator/scripts/validate_skill_hooks.py \
  --hooks-file skills/SKILL_HOOKS.yaml \
  --skills-dir skills \
  --strict \
  --json
```

```bash
python3 skills/control/reasoning-log-schema-guardian/scripts/validate_reasoning_log.py \
  --log-file artifacts/wiki_level_suite/reasoning.jsonl \
  --hooks-file skills/SKILL_HOOKS.yaml \
  --strict \
  --json
```

```bash
python3 skills/control/gate-policy-controller/scripts/gate_policy.py \
  --gate-id wiki-level-suite \
  --check lean=true:high:true:"Lean gold file compiles" \
  --json
```

## 9.6 Run Reflective Process Observation

```bash
python3 skills/autoformalization/autoformalization-reflective-refinement-loop/scripts/observe_autoformalization_process.py \
  --report-file artifacts/wiki_level_suite/report.json \
  --reasoning-log-file artifacts/wiki_level_suite/reasoning.jsonl \
  --hooks-file skills/SKILL_HOOKS.yaml \
  --output-file artifacts/reflection/wiki_level_refinement_packet.json \
  --json
```

Every emitted opportunity includes the regression commands that must pass before
a prompt or skill refinement is accepted.

## 9.7 Run Aggressive Skill Tests

```bash
python3 skills/control/skill-test-program-orchestrator/scripts/inventory_skills.py \
  --output-file artifacts/skill_test_program/inventory.json \
  --json
```

```bash
python3 skills/control/skill-test-program-orchestrator/scripts/run_deterministic_skill_tests.py \
  --include-slow \
  --json
```

```bash
python3 skills/control/skill-test-program-orchestrator/scripts/run_content_skill_codex_exec_tests.py \
  --execute \
  --json
```

```bash
python3 skills/control/skill-test-program-orchestrator/scripts/generate_skill_test_todos.py
```

The content lane uses `codex exec` under a read-only sandbox and records prompts,
stdout/stderr, final messages, and oracle results under
`artifacts/skill_test_program/content/`.
When only content oracles change, re-score saved outputs with
`run_content_skill_codex_exec_tests.py --reuse-existing --json`; fresh prompt or
skill changes still require `--execute`.

## 10. Current Boundary and Limitations

The generated Lean theorem files may still be interface scaffolds when full mathlib formalization is not available locally. In those cases:
- unresolved analytic content is intentionally isolated behind explicit abstract interfaces,
- refinement prompts are configured to avoid vacuous or unconstrained theorem postulation,
- generated Lean uses source-aware declaration comments rather than legacy per-line `NL/LaTeX:` comments,
- reports and judge critiques document semantic/formal gaps,
- `autoformalization-result-realness-verifier` must mark the artifact `draft` or `blocked`; the scaffold must not be counted as a completed theorem-level autoformalization.

## 11. Extension Guide

For a new theorem family:
1. Add LaTeX/input fixture under `tests/latex/` (optional but recommended).
2. Run systematic workflow to generate initial Lean scaffold.
3. Keep recursive dependencies enabled when prerequisites exist.
4. Use concept mapping to bias toward existing mathlib declarations.
5. Build and verify the intended import set before drafting relies on expected declarations.
6. Use web-assisted mathlib grounding only for unresolved local gaps, and return every API claim to Lean verification.
7. Run multi-cycle refinement.
8. Minimize imports and re-check import context after saving Lean.
9. Run the realness gate on Lean/report/history artifacts.
10. Review `*.report.json`, `*.reasoning.jsonl`, and `*.stats.*`.
11. Promote final Lean file into `backends/lean/Mathformer/` only when final status is complete rather than draft/blocked.

For prompt behavior changes:
1. Update prompt templates in `agentc.py`.
2. Update the owning specialized skill reference under `skills/*/references/`.
3. Run `autoformalization-reflective-refinement-loop` and use its monotonicity contract.
4. Run `skill-test-program-orchestrator` deterministic and Codex-exec content checks.
5. Update `skills/ALL_AGENT_SKILL_PROMPTS.md`.

For phase-routing or skill-trigger changes:
1. Update `skills/SKILL_HOOKS.yaml`.
2. Update `skills/autoformalization/autoformalization-workflow-orchestrator/references/workflow.md`.
3. Ensure reasoning-log payloads still include the correct `skill` and `hook_id`.
4. Run `workflow-contract-validator` in strict mode.
