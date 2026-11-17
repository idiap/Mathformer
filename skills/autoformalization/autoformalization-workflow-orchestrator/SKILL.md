---
name: autoformalization-workflow-orchestrator
description: Coordinate the full MASA-style autoformalization workflow across specialized skills, recursive dependencies, mathlib concept coverage loops, verified API planning, Lean hard critique, LLM judges, reverse informalization, proof-consistency verification, refinement taxonomy, compatibility scoring, multi-cycle refinement, artifacts, reasoning logs, and statistics. Use when running or implementing end-to-end iterative self-refinement rather than a single prompt agent.
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

# Autoformalization Workflow Orchestrator

## Purpose

Use this skill for the complete "estimate expansion risk -> research hard proof parts -> expand -> review expansion -> draft -> check -> critique -> refine -> audit -> save"
workflow. It owns orchestration behavior, artifact contracts, and shared runtime coordination.
Single-agent prompt details live in the specialized skills named below.

Shared runtime owner:
- `../autoformalization-agentc/scripts/agentc.py`
- classes: `IterativeSelfRefinementAgentC`, `HardCritiqueAgent`, `ImportRetrievalAgent`

## Phase Map

- Paper layout extraction: `paper-docling-layout-extractor`
- Paper main theory localization: `paper-main-theory-localizer`
- Paper theory expansion orchestration: `paper-theory-autoformalization-orchestrator`
- LaTeX textbook theory extraction: `latex-archive-theory-extractor`
- Textbook theory TeX organization: `textbook-theory-tex-organizer`
- Textbook per-unit batch queueing and object execution: `textbook-autoformalization-batch-orchestrator`
- Source unit inventory: `source-formalizable-unit-extractor`
- Line-by-line NL/LaTeX-to-Lean source anchor packets: `source-line-translation-packet-builder`
- Source-anchor drift guard: `source-formalization-drift-guard`
- Expansion: `latex-prerequisite-expander`
- Proof expansion support: `proof-expansion-support-orchestrator`
- Proof expansion difficulty estimation: `proof-expansion-difficulty-estimator`
- Proof expansion web research: `proof-expansion-web-researcher`
- Expansion review suite: `latex-expansion-review-orchestrator`
- Expansion completeness review: `latex-expansion-completeness-reviewer`
- Expansion binding review: `latex-expansion-binding-reviewer`
- Initial formal draft: `lean-autoformalization-drafter`
- Initial Lean execution: `lean-execution-runner`
- Mathlib candidate/module discovery: `mathlib-concept-candidate-mapper`
- Mathlib hierarchy navigation: `mathlib-hierarchy-navigator`
- Mathlib module tree cartography: `mathlib-module-tree-cartographer`
- Mathlib declaration neighborhoods: `mathlib-declaration-neighborhood-navigator`
- Mathlib candidate verification: `mathlib-candidate-verifier`
- Mathlib concept coverage review: `mathlib-concept-coverage-reviewer`
- Mathlib API compatibility plan: `mathlib-api-compatibility-planner`
- Mathlib import-set planning: `mathlib-import-set-builder`
- Lean import-context verification: `lean-import-context-verifier`
- Mathlib import minimization: `mathlib-import-minimizer`
- Mathlib compatibility loops: `mathlib-compatibility-loop-orchestrator`
- Mathlib grounding maximization across artifact sets: `mathlib-grounding-maximizer`
- Isabelle/IsarMathLib grounding search: `isarmathlib-grounding-navigator`
- Initial Isabelle/HOL draft: `isabelle-autoformalization-drafter`
- Initial Isabelle execution: `isabelle-execution-runner`
- SymPy dependency probe: `sympy-dependency-prober`
- SymPy API documentation index: `sympy-api-docs-indexer`
- SymPy expression parsing and assumption modeling: `sympy-expression-parser`, `sympy-assumption-modeler`
- SymPy API grounding: `sympy-concept-grounding-navigator`
- Initial SymPy executable draft: `sympy-autoformalization-drafter`
- Initial SymPy execution and validation: `sympy-execution-runner`, `sympy-identity-validator`, `sympy-counterexample-searcher`, `sympy-transformation-trace-verifier`
- Unified SymPy consistency report: `sympy-consistency-report-orchestrator`
- Theorem-prover and semantic repair: `lean-formal-refinement`
- Semantic/aspect judging: `lean-critique-and-judging`
- Critique gate suite: `lean-critique-suite-orchestrator`
- Reference-free critic monitoring: `reference-free-critic-monitor`
- Output cleanup: `lean-output-denoiser`
- Refinement transition logging: `lean-refinement-taxonomy`
- Generated Lean source-comment and semantic-alignment guard plus optional line annotations: `lean-line-annotation`
- Lean compile/typecheck diagnostics: `lean-compile-checker`
- Compatibility scoring and merge-readiness review: `mathlib-abstraction-auditor`
- Reverse informalization from final Lean: `lean-informalization-extractor`
- Internal consistency of informalized proof packets: `lean-informal-proof-internal-consistency-verifier`
- Informalized proof consistency gate: `lean-informal-consistency-verifier`
- Declaration-shape consistency gate: `lean-declaration-shape-consistency-checker`
- Non-vacuity consistency gate: `lean-nonvacuity-consistency-checker`
- Cross-file concept consistency index: `lean-cross-file-concept-consistency-indexer`
- Unified Lean consistency report: `lean-consistency-report-orchestrator`
- Final result realness gate: `autoformalization-result-realness-verifier`
- ProofNet data/evaluation commands: `proofnet-benchmark-runner`

## Workflow

1. Normalize the informal input. When the input is a LaTeX textbook archive/source tree,
   extract theorem-like units with `latex-archive-theory-extractor`, organize coherent
   TeX bundles with `textbook-theory-tex-organizer`, and create truthful queued jobs with
   `textbook-autoformalization-batch-orchestrator`.
2. When the input is a paper PDF/URL, extract layout with
   `paper-docling-layout-extractor`, localize main theory with `paper-main-theory-localizer`,
   and build the intermediate/reference expansion plan with
   `paper-theory-autoformalization-orchestrator`.
3. Extract a source-linked inventory of formalizable units when the input is a URL, article,
   paper excerpt, or wiki-style source.
4. Estimate which proof parts are hard to expand.
5. Run web-backed support for hard, research-level, cited, or uncertain proof segments.
6. Expand prerequisite definitions/theorems using the support packet and source-unit inventory.
7. Review the expanded LaTeX for completeness and binding discipline before drafting.
8. Build a line-by-line translation packet from literal NL/LaTeX to Lean-facing
   obligations with `source-line-translation-packet-builder`; inject its
   `lean_prompt_context` into the drafter as core statement annotations.
9. Recursively formalize dependency statements before parent statements when dependency context is provided.
10. Branch on the selected backend. For Lean, map informal statements to mathlib concepts/modules, navigate relevant module hierarchy, and verify top candidates. For Isabelle/HOL, run `isarmathlib-grounding-navigator` over local Isabelle sessions and optional IsarMathLib theory trees. For SymPy, first run `sympy-dependency-prober`, `sympy-api-docs-indexer`, `sympy-expression-parser`, `sympy-assumption-modeler`, and `sympy-concept-grounding-navigator` for the selected symbolic style.
11. Run the mathlib concept compatibility loop until every extracted concept is verified or the round cap is reached.
12. Build a narrow intended import set from verified modules, hierarchy context, and fixture expected-import metadata.
13. Verify expected declarations under the intended imports; do not rely only on broad `import Mathlib`.
14. Run `mathlib-grounding-maximizer` when several files or high-risk concepts need whole-artifact grounding controls before prompt hints become authoritative.
15. Build a coverage-aware API plan that injects confirmed declarations/modules, verified imports, hierarchy context, explicit gaps, and source-anchor obligations as hints.
16. Generate an initial formalization with source-aware comments, `Source anchors: ...` references for source-backed declarations or artifacts, and normal blank-line structure. Use `lean-autoformalization-drafter` for Lean4, `isabelle-autoformalization-drafter` for Isabelle/HOL, and `sympy-autoformalization-drafter` for executable symbolic algebra traces.
17. Run `lean-line-annotation`'s source-comment hygiene guard with semantic-comment coverage; reject or repair drafts with legacy per-line comments, syntax-only comments, or missing declaration alignment before execution.
18. Execute the initial formal artifact through the matching execution runner: `lean-execution-runner` for Lean4, `isabelle-execution-runner` for Isabelle/HOL, or `sympy-execution-runner` for SymPy.
19. Run a backend-specific validation pass: `lake env lean` when targeting Lean4, `isabelle build -D` when targeting Isabelle/HOL, or the SymPy identity, counterexample, trace, and consistency validators for `sympy_equational_trace`.
20. Run `source-formalization-drift-guard` whenever a line translation packet exists; route missing or orphan anchors back to semantic refinement before acceptance.
21. Run refinement only when hard or soft critique indicates a problem, preserving original-source NL/LaTeX comments, generated support notes, and `Source anchors` while removing noisy legacy comments.
22. Re-run the source-comment hygiene guard and source-anchor drift guard after denoising or refinement and before saving final artifacts.
23. Minimize/deduplicate the Lean import block and re-check the intended import context when expected declarations are known.
24. Classify each refinement transition and save per-round Lean snapshots.
25. Run post-save Lean checks, LLM judges, mathlib grounding maximization, and mathlib compatibility auditing.
26. Informalize final Lean declarations with `lean-informalization-extractor`, preserving original-source, generated-note, and source-anchor fields separately from the extracted proof narrative.
27. Run `lean-declaration-shape-consistency-checker` on the extracted packet; route blockers to semantic refinement or representation-boundary notes when source-advertised iff, existence, uniqueness, or conditional shape is not visible in Lean.
28. Run `lean-informal-proof-internal-consistency-verifier` on the extracted proof packet; route blockers to proof-packet extraction, semantic refinement, or logical-soundness review when the informalized proof is internally incoherent.
29. Run `lean-informal-consistency-verifier` before final acceptance; route blockers to semantic/logical refinement when the reverse informalization exposes a source-shape mismatch, unsupported proof delegation, placeholder, target axiom, realness failure, or optional Lean-check failure.
30. Run `lean-nonvacuity-consistency-checker`; route blockers to statement/proof strengthening or explicit interface-boundary documentation when the theorem is vacuous, target-restating, axiomatic, or an undocumented exact-hypothesis wrapper.
31. Run `lean-cross-file-concept-consistency-indexer` across the touched artifact set; route full-name collisions to repair and repeated concept families to MathformerLib promotion review.
32. Run `autoformalization-result-realness-verifier` before publishing final artifacts; if placeholders, mocks, unexecuted reports, noisy legacy comments, missing semantic declaration comments, or scaffold-only claims remain, label the artifact draft/blocked and route it back to refinement instead of counting it complete.
33. Run `lean-consistency-report-orchestrator` to persist the full reference-free consistency report and expose any failing layer before final status is claimed.
34. Run `reference-free-critic-monitor` to snapshot benchmark-free critic measures and compare them against the accepted baseline before prompt/skill reflection.
35. Continue score-gated outer cycles until the compatibility target, realness gate, source-comment hygiene gate, source-anchor drift guard, declaration-shape gate, reverse-informalization internal-consistency gate, reverse-informalization consistency gate, non-vacuity gate, cross-file concept gate, unified consistency report, mathlib grounding maximizer, reference-free monitor, or cycle cap is reached.
36. Emit `.lean`, `.history.json`, `.report.json`, reasoning-log JSONL, source-comment hygiene reports, source-anchor drift reports, reverse-informalization reports, consistency reports, stats JSON/TeX, and cycle manifests only after final status is truthful: `complete`, `draft`, or `blocked`.

## References

- Read `references/workflow.md` for class ownership, artifact details, and multi-cycle behavior.
- Read `../SKILL_HOOKS.yaml` before changing phase routing, trigger conditions, or reasoning-log event ownership.
