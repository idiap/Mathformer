---
name: autoformalization-agentc
description: Compatibility wrapper for the legacy MASA-style AgentC autoformalization runtime and prompt bundle. Use when maintaining shared runtime code in scripts/agentc.py, preserving backwards-compatible imports, or finding the specialized skill that now owns a particular autoformalization phase.
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

# Autoformalization AgentC Compatibility Wrapper

## Status

This skill is now a compatibility wrapper. New task-specific guidance lives in narrower
skills so Codex can load only the context needed for a single phase.

Shared runtime remains here:

- `scripts/agentc.py`
- `scripts/analyze_logs.py`
- `references/source.md`
- `references/prompts.md` as a legacy prompt-parity snapshot

## Use The Specialized Skills

- `autoformalization-workflow-orchestrator`: end-to-end workflow, hard critique, recursive dependencies, artifacts, score-gated cycles, logs, and statistics.
- `proof-expansion-support-orchestrator`: pre-expansion loop for proof difficulty estimation and web-backed support.
- `proof-expansion-difficulty-estimator`: proof-part expansion difficulty scoring and search-decision metadata.
- `proof-expansion-web-researcher`: source-backed web research packets for difficult expansion segments.
- `latex-prerequisite-expander`: `LatexExpansionAgent` prompt and pre-formalization expansion.
- `latex-expansion-review-orchestrator`: ordered pre-autoformalization review of expanded LaTeX.
- `latex-expansion-completeness-reviewer`: prerequisite, assumption, side-condition, and conclusion coverage review for expanded LaTeX.
- `latex-expansion-binding-reviewer`: binder, quantifier, free-variable, domain, index, arity, reference, and notation review for expanded LaTeX.
- `lean-autoformalization-drafter`: `AutoformalizationAgent` prompt, dependency context, mathlib hints, and source-aligned doc comments.
- `lean-execution-runner`: immediate Lean execution after initial formalization delivery.
- `isarmathlib-grounding-navigator`: local Isabelle/HOL and optional IsarMathLib theory search before Isabelle drafting.
- `isabelle-autoformalization-drafter`: first-pass Isabelle/HOL theory drafting, currently one style at a time via `isar_direct`.
- `isabelle-execution-runner`: immediate Isabelle execution after initial `.thy` delivery.
- `sympy-dependency-prober`: required and optional dependency probe for symbolic algebra autoformalization.
- `sympy-api-docs-indexer`: local installed SymPy API index for grounding transformations.
- `sympy-expression-parser`: NL/LaTeX-to-SymPy expression packet extraction.
- `sympy-assumption-modeler`: source-backed and generated-support assumption packets.
- `sympy-concept-grounding-navigator`: concept-to-SymPy API grounding.
- `sympy-autoformalization-drafter`: first-pass executable SymPy artifact drafting for `sympy_equational_trace`.
- `sympy-execution-runner`: immediate SymPy artifact execution after initial Python delivery.
- `sympy-identity-validator`, `sympy-counterexample-searcher`, `sympy-transformation-trace-verifier`: backend-specific validation criteria for symbolic traces.
- `sympy-consistency-report-orchestrator`: unified reference-free consistency report for SymPy artifacts.
- `lean-formal-refinement`: `FormalRefinementAgent` and `InformalRefinementAgent` prompts.
- `lean-critique-and-judging`: `SoftCritiqueAgent` prompt and final judge aspects.
- `lean-output-denoiser`: `DenoisingAgent` prompt.
- `lean-refinement-taxonomy`: `RefinementTaxonomyAgent` prompt and taxonomy output contract.
- `lean-line-annotation`: `LeanLineAnnotationAgent` prompt and annotation output contract.
- `mathlib-concept-candidate-mapper`: mathlib concept extraction plus ranked declaration/module hints.
- `mathlib-hierarchy-navigator`: broad-to-specific mathlib traversal across prefixes, modules, siblings, and query results.
- `mathlib-module-tree-cartographer`: parent/child/sibling cartography for mathlib module prefixes.
- `mathlib-declaration-neighborhood-navigator`: focused module imports, declarations, and source references.
- `mathlib-candidate-verifier`: verified mathlib declaration/module hints via Lean `#check`.
- `mathlib-concept-coverage-reviewer`: verified coverage scoring and concept gap reporting.
- `mathlib-api-compatibility-planner`: coverage-aware API hints that maximize verified mathlib reuse.
- `mathlib-compatibility-loop-orchestrator`: bounded pre-draft concept maximization and post-save compatibility target loops.
- `lean-compile-checker`: direct Lean compile/typecheck diagnostics.
- `mathlib-abstraction-auditor`: mathlib-native compatibility scoring and structural audit.
- `autoformalization-result-realness-verifier`: final gate that prevents mocks, placeholders, unexecuted states, or scaffold-only artifacts from being reported as complete autoformalizations.
- `proofnet-benchmark-runner`: ProofNet data export and prediction evaluation.

## Maintenance Rules

1. Keep `scripts/agentc.py` as the shared runtime until a separate implementation split is explicitly planned.
2. Do not add new canonical prompt text here; update the owning specialized skill's `references/` file instead.
3. Preserve fence markers (`%%%%%%%%%%`) and placeholder names when touching legacy prompt snapshots.
4. Keep backwards-compatible behavior for callers that still instantiate classes from this skill's script.
5. When changing orchestration behavior, update `autoformalization-workflow-orchestrator/references/workflow.md`.
6. Legacy callers must still route saved outputs through the result realness gate before claiming completion.

## Log Analysis

Run standalone log analysis on an existing report:

```bash
python3 skills/autoformalization/autoformalization-agentc/scripts/analyze_logs.py \
  --report-file artifacts/autoformalization/<stem>.report.json
```
