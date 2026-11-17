<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Give operators and agents one readable hub for the agentic control surface
  behind natural-language Mathformer requests.

Intent:
  Explain how Mathformer coordinates agents, controlled workflows,
  validation gates, and deterministic NL intent routing.

Function:
  Documents the AgenticHub: its counts, major workflow arrows, agent
  inventory, and controlled execution surface.

Maintenance Notes:
  Keep this file synchronized with `scripts/mathformer.py`, agent
  manifests, and the hook registry.
-->

# AgenticHub

AgenticHub is the control map for Mathformer agents and major
workflows. The important object is not a script catalogue, but the agentic
system that routes natural-language requests through controlled agents, hooks,
backend checks, artifacts, and validation gates.

## Counts

- Agents: `141`
- Major loop contracts: `13`
- Registered controlled actions: `89`
- Action families: `27`

## Major Workflows

Top-level agentic path:

```text
natural-language request -> intent route -> owner agent -> hook contract -> backend/tool execution -> artifact -> validation status -> explanation
```

Named loop contracts:

- `control_validation_loop`: change -> hook/schema audit -> gate policy -> reasoning-log validation -> controlled status
- `preformalization_readiness_loop`: source -> extraction -> expansion -> support evidence -> readiness gate -> formal drafting
- `textbook_theory_autoformalization_loop`: textbook source -> theory extraction -> concept organization -> theorem units -> Lean candidates
- `mathlib_grounding_loop`: concepts -> hierarchy navigation -> candidate declarations -> import plan -> verified grounding or explicit gap
- `draft_execute_refine_loop`: source packet -> draft formal artifact -> execute backend -> diagnose -> critique -> localized repair
- `artifact_acceptance_loop`: candidate artifact -> import minimization -> reverse informalization -> non-vacuity -> consistency report -> status
- `lean_consistency_testing_loop`: Lean artifact -> source-shape checks -> declaration review -> reverse informalization -> RFDE report
- `sympy_equational_trace_loop`: formula source -> parse -> assumptions -> API grounding -> symbolic validation -> counterexample search -> trace report
- `sympy_physics_derivation_trace_loop`: physics source -> quantities/units -> equation graph -> residual checks -> numeric sample -> consistency report
- `lean_physics_derivation_trace_loop`: physics derivation -> typed quantity packet -> assumptions -> Lean draft -> execution -> physics critics -> final review
- `isabelle_physics_derivation_trace_loop`: physics derivation -> Isabelle/HOL grounding -> theory draft -> build evidence -> final review
- `mathformerlib_accumulation_loop`: validated Lean artifact -> promotion gate -> registry update -> generated docs -> reusable library surface
- `reflection_testing_loop`: run evidence -> RFDE observation -> improvement candidate -> monotonicity gate -> prompt/agent/test update

## Operating The Hub

Use natural language first. Use the deterministic CLI only when an agent, operator, or CI job needs exact action names, dry-runs, or machine-readable reports.

```bash
python scripts/mathformer.py ask "run premise selection near the Fundamental theorem of algebra" --json
python scripts/mathformer.py list
python scripts/mathformer.py show quality:smoke
python scripts/mathformer.py run quality:smoke --json
python scripts/mathformer.py audit --strict --json
```

## Agents

Count: `141`

These agents are the natural-language execution surfaces for the Mathformer formal-reasoning platform.

### Control, Gates, And Observability

Count: `11`

- [autoformalization-reflective-refinement-loop](../../skills/autoformalization/autoformalization-reflective-refinement-loop/agents/openai.yaml): Find monotonic prompt and agent improvements from full workflow traces
- [autoformalization-result-realness-verifier](../../skills/autoformalization/autoformalization-result-realness-verifier/agents/openai.yaml): Block mocked final autoformalizations
- [autoformalization-workflow-orchestrator](../../skills/autoformalization/autoformalization-workflow-orchestrator/agents/openai.yaml): Run the full iterative formalization workflow
- [final-derivation-review-orchestrator](../../skills/autoformalization/final-derivation-review-orchestrator/agents/openai.yaml): Combines physics and math final reviews.
- [gate-policy-controller](../../skills/control/gate-policy-controller/agents/openai.yaml): Normalize pass, warn, fail, and waiver decisions
- [lean-refinement-taxonomy](../../skills/lean/lean-refinement-taxonomy/agents/openai.yaml): Classify refinement transitions
- [reasoning-log-schema-guardian](../../skills/control/reasoning-log-schema-guardian/agents/openai.yaml): Validate and emit structured reasoning-log events
- [reference-free-critic-monitor](../../skills/rfde/reference-free-critic-monitor/agents/openai.yaml): Track benchmark-free critic measures
- [skill-hook-coverage-maximizer](../../skills/control/skill-hook-coverage-maximizer/agents/openai.yaml): Audit agent reachability and workflow loops
- [skill-test-program-orchestrator](../../skills/control/skill-test-program-orchestrator/agents/openai.yaml): Run deterministic checks and Codex-exec content probes for all agents
- [workflow-contract-validator](../../skills/control/workflow-contract-validator/agents/openai.yaml): Check Mathformer hook ownership and routing

### Source Intake, Expansion, And Theory Extraction

Count: `16`

- [latex-archive-theory-extractor](../../skills/latex-textbook/latex-archive-theory-extractor/agents/openai.yaml): Extract theorem-like LaTeX units and proofs from archives with provenance.
- [latex-expansion-binding-reviewer](../../skills/latex-textbook/latex-expansion-binding-reviewer/agents/openai.yaml): Review expansion binder discipline
- [latex-expansion-completeness-reviewer](../../skills/latex-textbook/latex-expansion-completeness-reviewer/agents/openai.yaml): Review expansion prerequisite coverage
- [latex-expansion-review-orchestrator](../../skills/latex-textbook/latex-expansion-review-orchestrator/agents/openai.yaml): Run expansion reviews before drafting
- [latex-prerequisite-expander](../../skills/latex-textbook/latex-prerequisite-expander/agents/openai.yaml): Expand math statements before formalization
- [mathlib-result-existence-checker](../../skills/mathlib/mathlib-result-existence-checker/agents/openai.yaml): Gate drafting on existing mathlib or MathformerLib results
- [paper-docling-layout-extractor](../../skills/paper/paper-docling-layout-extractor/agents/openai.yaml): Extract paper layout with docling-first routing
- [paper-main-theory-localizer](../../skills/paper/paper-main-theory-localizer/agents/openai.yaml): Find main theory and support units
- [paper-theory-autoformalization-orchestrator](../../skills/paper/paper-theory-autoformalization-orchestrator/agents/openai.yaml): Coordinate paper-level theory formalization
- [proof-expansion-difficulty-estimator](../../skills/autoformalization/proof-expansion-difficulty-estimator/agents/openai.yaml): Score proof expansion difficulty
- [proof-expansion-support-orchestrator](../../skills/autoformalization/proof-expansion-support-orchestrator/agents/openai.yaml): Estimate and research proof expansion risk
- [proof-expansion-web-researcher](../../skills/autoformalization/proof-expansion-web-researcher/agents/openai.yaml): Research hard proof expansion steps
- [source-formalizable-unit-extractor](../../skills/autoformalization/source-formalizable-unit-extractor/agents/openai.yaml): Inventory formalizable units in math sources
- [textbook-autoformalization-batch-orchestrator](../../skills/latex-textbook/textbook-autoformalization-batch-orchestrator/agents/openai.yaml): Build truthful per-unit autoformalization job queues from textbook TeX bundles.
- [textbook-chapter-autoformalization-orchestrator](../../skills/latex-textbook/textbook-chapter-autoformalization-orchestrator/agents/openai.yaml): Extract LaTeX books and build chapter-by-chapter autoformalization queues with proofs.
- [textbook-theory-tex-organizer](../../skills/latex-textbook/textbook-theory-tex-organizer/agents/openai.yaml): Bundle extracted theorem-like units into coherent TeX files.

### Lean, Mathlib, And MathformerLib

Count: `43`

- [informal-proof-mathlib-concepts](../../skills/mathlib/informal-proof-mathlib-concepts/agents/openai.yaml): Legacy wrapper for mathlib lookup runtime
- [lean-autoformalization-drafter](../../skills/lean/lean-autoformalization-drafter/agents/openai.yaml): Draft first-pass formal Lean or Isabelle code
- [lean-compile-checker](../../skills/lean/lean-compile-checker/agents/openai.yaml): Run lake env lean and capture errors
- [lean-consistency-report-orchestrator](../../skills/lean/lean-consistency-report-orchestrator/agents/openai.yaml): Runs the full reference-free consistency stack for Lean autoformalization files.
- [lean-critique-and-judging](../../skills/lean/lean-critique-and-judging/agents/openai.yaml): Judge formalizations against explicit aspects
- [lean-critique-suite-orchestrator](../../skills/lean/lean-critique-suite-orchestrator/agents/openai.yaml): Run ordered Lean critique passes
- [lean-cross-file-concept-consistency-indexer](../../skills/lean/lean-cross-file-concept-consistency-indexer/agents/openai.yaml): Builds a controlled cross-file index of Lean declarations and repeated concepts.
- [lean-declaration-shape-consistency-checker](../../skills/lean/lean-declaration-shape-consistency-checker/agents/openai.yaml): Deterministic critic for agreement between source claim shape and Lean signature shape.
- [lean-execution-runner](../../skills/lean/lean-execution-runner/agents/openai.yaml): Run generated Lean in Lake
- [lean-formal-refinement](../../skills/lean/lean-formal-refinement/agents/openai.yaml): Repair formal code from prover or semantic feedback
- [lean-import-context-verifier](../../skills/lean/lean-import-context-verifier/agents/openai.yaml): Verify Lean under intended imports
- [lean-informal-consistency-verifier](../../skills/lean/lean-informal-consistency-verifier/agents/openai.yaml): Check reverse informal proof consistency
- [lean-informal-proof-internal-consistency-verifier](../../skills/lean/lean-informal-proof-internal-consistency-verifier/agents/openai.yaml): Check informalized proof coherence
- [lean-informalization-extractor](../../skills/lean/lean-informalization-extractor/agents/openai.yaml): Extract informal proof packets from Lean
- [lean-line-annotation](../../skills/lean/lean-line-annotation/agents/openai.yaml): Annotate Lean files line by line
- [lean-logical-soundness-critic](../../skills/lean/lean-logical-soundness-critic/agents/openai.yaml): Critique non-vacuity and logical soundness
- [lean-mathlib-alignment-critic](../../skills/lean/lean-mathlib-alignment-critic/agents/openai.yaml): Critique mathlib-native alignment
- [lean-nonvacuity-consistency-checker](../../skills/lean/lean-nonvacuity-consistency-checker/agents/openai.yaml): Deterministic critic for vacuous, trivial, or target-restating Lean theorem shapes.
- [lean-output-denoiser](../../skills/lean/lean-output-denoiser/agents/openai.yaml): Extract clean formal code from noisy output
- [lean-semantic-preservation-critic](../../skills/lean/lean-semantic-preservation-critic/agents/openai.yaml): Critique source-to-Lean meaning preservation
- [lean-syntactic-correctness-critic](../../skills/lean/lean-syntactic-correctness-critic/agents/openai.yaml): Critique Lean parse and typecheck health
- [mathematical-final-hypothesis-reviewer](../../skills/autoformalization/mathematical-final-hypothesis-reviewer/agents/openai.yaml): Reviews formal hypothesis shape and math soundness.
- [mathformer-library-docs-generator](../../skills/mathformerlib/mathformer-library-docs-generator/agents/openai.yaml): Publish Mathformer Lean modules as browsable Markdown.
- [mathformerlib-accumulation-orchestrator](../../skills/mathformerlib/mathformerlib-accumulation-orchestrator/agents/openai.yaml): Coordinate promotion into Mathformerlib
- [mathformerlib-promotion-gate](../../skills/mathformerlib/mathformerlib-promotion-gate/agents/openai.yaml): Gate accepted Mathformerlib entries
- [mathformerlib-registry-manager](../../skills/mathformerlib/mathformerlib-registry-manager/agents/openai.yaml): Build the Mathformerlib registry
- [mathlib-abstraction-auditor](../../skills/mathlib/mathlib-abstraction-auditor/agents/openai.yaml): Audit Lean files for mathlib alignment
- [mathlib-api-compatibility-planner](../../skills/mathlib/mathlib-api-compatibility-planner/agents/openai.yaml): Plan verified mathlib API usage
- [mathlib-candidate-verifier](../../skills/mathlib/mathlib-candidate-verifier/agents/openai.yaml): Verify mathlib candidates with Lean #check
- [mathlib-compatibility-auditor](../../skills/mathlib/mathlib-compatibility-auditor/agents/openai.yaml): Legacy wrapper for compatibility audit runtime
- [mathlib-compatibility-loop-orchestrator](../../skills/mathlib/mathlib-compatibility-loop-orchestrator/agents/openai.yaml): Maximize concept-to-mathlib coverage
- [mathlib-concept-candidate-mapper](../../skills/mathlib/mathlib-concept-candidate-mapper/agents/openai.yaml): Rank mathlib declarations and modules
- [mathlib-concept-coverage-reviewer](../../skills/mathlib/mathlib-concept-coverage-reviewer/agents/openai.yaml): Check verified concept coverage
- [mathlib-concept-ontology-manager](../../skills/mathlib/mathlib-concept-ontology-manager/agents/openai.yaml): Validate reviewed concept policy
- [mathlib-declaration-neighborhood-navigator](../../skills/mathlib/mathlib-declaration-neighborhood-navigator/agents/openai.yaml): Inspect module declaration neighborhoods
- [mathlib-grounding-maximizer](../../skills/mathlib/mathlib-grounding-maximizer/agents/openai.yaml): Maximize Lean artifacts against mathlib
- [mathlib-hierarchy-navigator](../../skills/mathlib/mathlib-hierarchy-navigator/agents/openai.yaml): Navigate mathlib by module tree
- [mathlib-import-minimizer](../../skills/mathlib/mathlib-import-minimizer/agents/openai.yaml): Minimize generated Lean imports
- [mathlib-import-set-builder](../../skills/mathlib/mathlib-import-set-builder/agents/openai.yaml): Build narrow mathlib import profiles
- [mathlib-module-tree-cartographer](../../skills/mathlib/mathlib-module-tree-cartographer/agents/openai.yaml): Map module prefixes and siblings
- [mathlib-web-evidence-validator](../../skills/mathlib/mathlib-web-evidence-validator/agents/openai.yaml): Validate source-backed mathlib web claims
- [mathlib-web-grounding-orchestrator](../../skills/mathlib/mathlib-web-grounding-orchestrator/agents/openai.yaml): Coordinate web-assisted mathlib grounding
- [mathlib-web-search-strategist](../../skills/mathlib/mathlib-web-search-strategist/agents/openai.yaml): Plan official-source mathlib web searches

### Isabelle And Rocq

Count: `5`

- [isabelle-autoformalization-drafter](../../skills/isabelle/isabelle-autoformalization-drafter/agents/openai.yaml): Draft source-aware Isabelle/HOL theory files from NL or LaTeX.
- [isabelle-execution-runner](../../skills/isabelle/isabelle-execution-runner/agents/openai.yaml): Run Isabelle/HOL theory checks and emit structured diagnostics.
- [isarmathlib-grounding-navigator](../../skills/isabelle/isarmathlib-grounding-navigator/agents/openai.yaml): Search Isabelle/HOL and IsarMathLib theories for grounding candidates.
- [rocq-autoformalization-drafter](../../skills/rocq/rocq-autoformalization-drafter/agents/openai.yaml): Agent manifest for this capability.
- [rocq-execution-runner](../../skills/rocq/rocq-execution-runner/agents/openai.yaml): Agent manifest for this capability.

### ATP And Premise Selection

Count: `5`

- [premise-kb-indexer](../../skills/premise-kb/premise-kb-indexer/agents/openai.yaml): Index theorem facts into MathformerKB
- [premise-kb-theorem-seed-generator](../../skills/premise-kb/premise-kb-theorem-seed-generator/agents/openai.yaml): Generate theorem and axiom KB seeds
- [proofnet-benchmark-runner](../../skills/benchmarks/proofnet-benchmark-runner/agents/openai.yaml): Prepare and evaluate ProofNet runs
- [vampire-atp-orchestrator](../../skills/atp/vampire-atp-orchestrator/agents/openai.yaml): Run TPTP proof search with Vampire
- [vampire-proof-informalizer](../../skills/atp/vampire-proof-informalizer/agents/openai.yaml): Explain Vampire formal proofs

### SymPy Symbolic Backend

Count: `12`

- [mathematical-sympy-final-equation-reviewer](../../skills/sympy/mathematical-sympy-final-equation-reviewer/agents/openai.yaml): Reviews final SymPy equation traces.
- [sympy-api-docs-indexer](../../skills/sympy/sympy-api-docs-indexer/agents/openai.yaml): Agent manifest for this capability.
- [sympy-assumption-modeler](../../skills/sympy/sympy-assumption-modeler/agents/openai.yaml): Agent manifest for this capability.
- [sympy-autoformalization-drafter](../../skills/sympy/sympy-autoformalization-drafter/agents/openai.yaml): Agent manifest for this capability.
- [sympy-concept-grounding-navigator](../../skills/sympy/sympy-concept-grounding-navigator/agents/openai.yaml): Agent manifest for this capability.
- [sympy-consistency-report-orchestrator](../../skills/sympy/sympy-consistency-report-orchestrator/agents/openai.yaml): Agent manifest for this capability.
- [sympy-counterexample-searcher](../../skills/sympy/sympy-counterexample-searcher/agents/openai.yaml): Agent manifest for this capability.
- [sympy-dependency-prober](../../skills/sympy/sympy-dependency-prober/agents/openai.yaml): Agent manifest for this capability.
- [sympy-execution-runner](../../skills/sympy/sympy-execution-runner/agents/openai.yaml): Agent manifest for this capability.
- [sympy-expression-parser](../../skills/sympy/sympy-expression-parser/agents/openai.yaml): Agent manifest for this capability.
- [sympy-identity-validator](../../skills/sympy/sympy-identity-validator/agents/openai.yaml): Agent manifest for this capability.
- [sympy-transformation-trace-verifier](../../skills/sympy/sympy-transformation-trace-verifier/agents/openai.yaml): Agent manifest for this capability.

### Physics Derivation Backends

Count: `47`

- [physics-coordinate-frame-context-builder](../../skills/physics-common/physics-coordinate-frame-context-builder/agents/openai.yaml): Agent manifest for this capability.
- [physics-derivation-consistency-report-orchestrator](../../skills/physics-common/physics-derivation-consistency-report-orchestrator/agents/openai.yaml): Agent manifest for this capability.
- [physics-derivation-gap-expander](../../skills/physics-common/physics-derivation-gap-expander/agents/openai.yaml): Agent manifest for this capability.
- [physics-derivation-plan-builder](../../skills/physics-common/physics-derivation-plan-builder/agents/openai.yaml): Agent manifest for this capability.
- [physics-derivation-source-extractor](../../skills/physics-common/physics-derivation-source-extractor/agents/openai.yaml): Agent manifest for this capability.
- [physics-derivation-step-verifier](../../skills/physics-common/physics-derivation-step-verifier/agents/openai.yaml): Agent manifest for this capability.
- [physics-dimension-modeler](../../skills/physics-common/physics-dimension-modeler/agents/openai.yaml): Agent manifest for this capability.
- [physics-equation-parser](../../skills/physics-common/physics-equation-parser/agents/openai.yaml): Agent manifest for this capability.
- [physics-final-hypothesis-reviewer](../../skills/physics-common/physics-final-hypothesis-reviewer/agents/openai.yaml): Reviews final physics hypotheses and context.
- [physics-formal-answer-comparison-reflector](../../skills/physics-common/physics-formal-answer-comparison-reflector/agents/openai.yaml): Compare withheld dataset formalizations
- [physics-implicit-gap-detector](../../skills/physics-common/physics-implicit-gap-detector/agents/openai.yaml): Agent manifest for this capability.
- [physics-informal-derivation-elicitor](../../skills/physics-common/physics-informal-derivation-elicitor/agents/openai.yaml): Elicit missing physics context before formalization
- [physics-informal-derivation-expander](../../skills/physics-common/physics-informal-derivation-expander/agents/openai.yaml): Expand informal physics steps before formalization
- [physics-informal-derivation-readiness-reviewer](../../skills/physics-common/physics-informal-derivation-readiness-reviewer/agents/openai.yaml): Review expanded physics derivations before drafting
- [physics-isabelle-derivation-drafter](../../skills/physics-isabelle/physics-isabelle-derivation-drafter/agents/openai.yaml): Draft source-aligned Isabelle/HOL physics derivation theories.
- [physics-law-concept-grounding-navigator](../../skills/physics-common/physics-law-concept-grounding-navigator/agents/openai.yaml): Agent manifest for this capability.
- [physics-lean-assumption-context-encoder](../../skills/physics-lean/physics-lean-assumption-context-encoder/agents/openai.yaml): Encode physics context for Lean
- [physics-lean-assumption-critic](../../skills/physics-lean/physics-lean-assumption-critic/agents/openai.yaml): Finds hidden physics assumption drift in Lean.
- [physics-lean-consistency-report-orchestrator](../../skills/physics-lean/physics-lean-consistency-report-orchestrator/agents/openai.yaml): Aggregate Lean physics gates
- [physics-lean-derivation-drafter](../../skills/physics-lean/physics-lean-derivation-drafter/agents/openai.yaml): Draft typed Lean physics derivations
- [physics-lean-dimension-critic](../../skills/physics-lean/physics-lean-dimension-critic/agents/openai.yaml): Generates unit and dimension stress checks.
- [physics-lean-execution-interpreter](../../skills/physics-lean/physics-lean-execution-interpreter/agents/openai.yaml): Classify Lean physics failures
- [physics-lean-generative-critic-orchestrator](../../skills/physics-lean/physics-lean-generative-critic-orchestrator/agents/openai.yaml): Runs generative Codex-exec physics critics.
- [physics-lean-physical-semantics-critic](../../skills/physics-lean/physics-lean-physical-semantics-critic/agents/openai.yaml): Critiques whether Lean preserves physics meaning.
- [physics-lean-refinement-loop](../../skills/physics-lean/physics-lean-refinement-loop/agents/openai.yaml): Refine Lean physics artifacts
- [physics-lean-review-refinement-router](../../skills/physics-lean/physics-lean-review-refinement-router/agents/openai.yaml): Routes failed final reviews to local repairs.
- [physics-lean-type-system-builder](../../skills/physics-lean/physics-lean-type-system-builder/agents/openai.yaml): Build typed physics surfaces for Lean
- [physics-lean-unit-analysis-verifier](../../skills/physics-lean/physics-lean-unit-analysis-verifier/agents/openai.yaml): Verify Lean unit discipline
- [physics-lean-workflow-orchestrator](../../skills/physics-lean/physics-lean-workflow-orchestrator/agents/openai.yaml): Orchestrate Lean physics formalization
- [physics-numeric-sanity-sampler](../../skills/physics-common/physics-numeric-sanity-sampler/agents/openai.yaml): Agent manifest for this capability.
- [physics-regime-assumption-modeler](../../skills/physics-common/physics-regime-assumption-modeler/agents/openai.yaml): Agent manifest for this capability.
- [physics-symbol-table-builder](../../skills/physics-common/physics-symbol-table-builder/agents/openai.yaml): Agent manifest for this capability.
- [physics-sympy-assumption-context-encoder](../../skills/physics-sympy/physics-sympy-assumption-context-encoder/agents/openai.yaml): Encodes SymPy physics assumptions.
- [physics-sympy-dependency-prober](../../skills/physics-sympy/physics-sympy-dependency-prober/agents/openai.yaml): Agent manifest for this capability.
- [physics-sympy-derivation-drafter](../../skills/physics-sympy/physics-sympy-derivation-drafter/agents/openai.yaml): Agent manifest for this capability.
- [physics-sympy-dimension-projection-critic](../../skills/physics-sympy/physics-sympy-dimension-projection-critic/agents/openai.yaml): Stress-tests dimensions and projections.
- [physics-sympy-equation-surface-builder](../../skills/physics-sympy/physics-sympy-equation-surface-builder/agents/openai.yaml): Builds physics equation surfaces.
- [physics-sympy-equational-semantics-critic](../../skills/physics-sympy/physics-sympy-equational-semantics-critic/agents/openai.yaml): Critiques SymPy physics semantics.
- [physics-sympy-execution-interpreter](../../skills/physics-sympy/physics-sympy-execution-interpreter/agents/openai.yaml): Classifies SymPy physics diagnostics.
- [physics-sympy-execution-runner](../../skills/physics-sympy/physics-sympy-execution-runner/agents/openai.yaml): Agent manifest for this capability.
- [physics-sympy-final-equation-reviewer](../../skills/physics-sympy/physics-sympy-final-equation-reviewer/agents/openai.yaml): Reviews final physics equations.
- [physics-sympy-formal-answer-reflector](../../skills/physics-sympy/physics-sympy-formal-answer-reflector/agents/openai.yaml): Reflects on FormalPhysics answers.
- [physics-sympy-generative-critic-orchestrator](../../skills/physics-sympy/physics-sympy-generative-critic-orchestrator/agents/openai.yaml): Plans generative SymPy physics critiques.
- [physics-sympy-review-refinement-router](../../skills/physics-sympy/physics-sympy-review-refinement-router/agents/openai.yaml): Routes SymPy review repairs.
- [physics-sympy-workflow-orchestrator](../../skills/physics-sympy/physics-sympy-workflow-orchestrator/agents/openai.yaml): Plans controlled SymPy physics workflows.
- [physics-unit-analysis-verifier](../../skills/physics-common/physics-unit-analysis-verifier/agents/openai.yaml): Agent manifest for this capability.
- [physics-unit-system-grounder](../../skills/physics-common/physics-unit-system-grounder/agents/openai.yaml): Agent manifest for this capability.

### Runtime Compatibility And Integration

Count: `2`

- [autoformalization-agentc](../../skills/autoformalization/autoformalization-agentc/agents/openai.yaml): Legacy wrapper for shared AgentC runtime
- [result-existence-precheck-orchestrator](../../skills/autoformalization/result-existence-precheck-orchestrator/agents/openai.yaml): Prevent duplicate autoformalization before drafting

## Controlled Action Families

```text
agentc
atp
benchmark
control
docs
e2e
environment
generative
isabelle
kb
lean
licenses
mathformerlib
mathlib
paper
physics_isabelle
physics_lean
physics_sympy
quality
rfde
rocq
setup
skills
source
sympy
test
textbook
```
