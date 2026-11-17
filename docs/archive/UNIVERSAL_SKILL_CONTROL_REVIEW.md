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

# Universal Skill Control Review

Review date: 2026-06-05

Scope reviewed:

- `skills/SKILL_HOOKS.yaml`
- `skills/ALL_AGENT_SKILL_PROMPTS.md`
- the [framework guide](../architecture/FRAMEWORK.md)
- `skills/autoformalization/autoformalization-agentc/scripts/agentc.py`
- `skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py`
- `skills/autoformalization/proof-expansion-difficulty-estimator/scripts/estimate_proof_expansion_difficulty.py`
- `skills/mathlib/mathlib-hierarchy-navigator/scripts/navigate_mathlib_hierarchy.py`
- `skills/mathlib/mathlib-compatibility-auditor/scripts/check_mathlib_compat.py`
- `tests/wiki_level/run_suite.py`
- `tests/latex/wiki_level/manifest.json`

Validation baseline:

- `python3 -m py_compile ...` passed for shared scripts and the controlled-suite runner.
- `ruby -e 'require "yaml"; YAML.load_file("skills/SKILL_HOOKS.yaml")'` passed.
- `lake env lean tests/lean/WikiLevelGold.lean` passed.
- `python3 tests/wiki_level/run_suite.py` passed with `cases=5`, `lean=True`, `compatibility=100`, `max_difficulty=38`.

## Findings

### High: Hook contracts are declarative, not mechanically enforced

Evidence:

- `skills/SKILL_HOOKS.yaml:12` defines required and recommended payload fields, but this is only a manifest.
- `skills/SKILL_HOOKS.yaml:26` lists hook ids, owners, expected events, and gates.
- `docs/architecture/FRAMEWORK.md:281` tells maintainers to update hook metadata and keep `skill` / `hook_id` fields aligned.
- There is no repository-level validator script for hook uniqueness, owner existence, direct-routing coverage, or reasoning-log conformance.

Risk:

Hook drift can silently accumulate: a runtime event may use an unknown `hook_id`, a renamed skill may keep stale routing, or a gate may be described but not discoverable by automation.

Universal skill opportunity:

- `workflow-contract-validator`: validate hook manifests, skill ownership, direct request routing, event names, runtime script paths, and sample reasoning logs.

### High: Gate semantics are not unified across phases

Evidence:

- `skills/SKILL_HOOKS.yaml:111`, `skills/SKILL_HOOKS.yaml:270`, `skills/SKILL_HOOKS.yaml:292`, and `skills/SKILL_HOOKS.yaml:372` define gate behavior for LaTeX review, Lean execution, compile checks, and critique suite.
- `skills/latex-textbook/latex-expansion-review-orchestrator/references/review_suite.md:28` defines review gate semantics, but `review_suite.md:36` says the default runtime records the gate result and does not abort legacy workflows.
- `skills/mathlib/mathlib-concept-coverage-reviewer/references/coverage.md:11` defines a strict concept gate, but the gate is not represented as one reusable gate decision object.

Risk:

Different phases can interpret `False`, `None`, warning, skipped, and waiver states differently. This weakens control because downstream phases cannot rely on one standard gate record.

Universal skill opportunity:

- `gate-policy-controller`: normalize phase results into a single decision shape: `pass`, `fail`, `warn`, `skip`, `waived`, with blocking reasons, waiver ids, severity, and next action.

### High: Reasoning-log schema is inconsistent across scripts

Evidence:

- `docs/architecture/FRAMEWORK.md:180` says each JSONL event includes `event_index`, timestamps, monotonic timing, `payload.skill`, `payload.hook_id`, statement hash, file prefix, step, and payload.
- `skills/autoformalization/proof-expansion-difficulty-estimator/scripts/estimate_proof_expansion_difficulty.py:240` writes only `timestamp_utc`, `step`, and `payload`.
- `skills/mathlib/mathlib-hierarchy-navigator/scripts/navigate_mathlib_hierarchy.py:243` writes the same minimal shape.
- `skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py:321` and `skills/mathlib/mathlib-compatibility-auditor/scripts/check_mathlib_compat.py:111` maintain indexed structured events.

Risk:

Statistics and audit tooling cannot reliably compute durations, event order, hook coverage, or failure provenance across all phases. The controlled suite currently emits mixed log shapes.

Universal skill opportunity:

- `reasoning-log-schema-guardian`: provide one shared append/validate module, a log validator CLI, and a migration path for scripts that currently emit minimal events.

### Medium: Controlled-suite controls are useful but case-specific

Evidence:

- `tests/wiki_level/run_suite.py:168` implements static LaTeX fixture review.
- `tests/wiki_level/run_suite.py:471` implements expected declaration `#check`s.
- `tests/wiki_level/run_suite.py:527` implements summary gate logic.
- `tests/latex/wiki_level/manifest.json:1` defines a reusable-looking manifest format, but the runner is hardwired to this suite.

Risk:

Future fixture suites will copy control logic or drift from the wiki-level runner. That makes calibration uneven across theorem families.

Universal skill opportunity:

- `controlled-formalization-suite-runner`: generalize the manifest schema and runner so any fixture suite can declare LaTeX inputs, gold Lean targets, expected imports, expected declarations, pipeline checks, and gate policies.

### Medium: Mathlib concept-control data is embedded in code

Evidence:

- `skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py:108` hardcodes `SYNONYMS`.
- `skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py:208` hardcodes `PREFERRED_DECLS`.

Risk:

Concept policy is hard to review, version, tune by mathematical area, or validate independently. Adding controlled examples can improve one suite while accidentally changing ranking behavior elsewhere.

Universal skill opportunity:

- `mathlib-concept-ontology-manager`: move synonyms, phrase hints, and preferred declarations into versioned YAML profiles with `#check` validation and per-domain overlays.
- `mathlib-index-builder`: build a versioned module/declaration/import index with hierarchical navigation metadata, theorem-shape summaries, and probable concept annotations. See the [mathlib indexing plan](../operations/MATHLIB_INDEXING_CONTROL_TODOS.md).

### Medium: Expected declaration checks use broad import context

Evidence:

- `tests/latex/wiki_level/manifest.json:48` and related case entries declare expected per-case imports.
- `tests/wiki_level/run_suite.py:490` writes scratch declaration checks with `import Mathlib`.

Risk:

A declaration may verify under broad `Mathlib` but fail under the intended minimal imports. This hides import compatibility defects that matter for generated Lean.

Universal skill opportunity:

- `lean-import-context-verifier`: verify expected declarations and generated Lean under declared import contexts, not only under `Mathlib`.

### Medium: Semantic preservation is mostly LLM-judged, not contract-checked

Evidence:

- `docs/architecture/FRAMEWORK.md:150` says alignment is enforced through doc comments, source-to-Lean hints, and optional mathlib hints.
- `skills/lean/lean-critique-suite-orchestrator/references/critique_suite.md:3` defines an expected critique report shape, but there is no universal source-to-formal contract artifact that deterministic tools can inspect.

Risk:

A Lean theorem can compile and score well on compatibility while still weakening assumptions, changing quantifier order, introducing vacuous abstractions, or missing a side condition.

Universal skill opportunity:

- `source-to-formal-contract-builder`: produce a machine-readable contract from expanded LaTeX with objects, binders, hypotheses, conclusion, side conditions, expected declarations, allowed abstraction boundaries, and blocking preservation checks.

### Medium: Proof dependency structure is implicit

Evidence:

- `docs/architecture/FRAMEWORK.md:138` describes recursive dependency behavior.
- `docs/architecture/FRAMEWORK.md:104` lists proof expansion and dependency stages, but there is no first-class proof dependency graph artifact before drafting.

Risk:

The workflow can expand and formalize dependencies, but it does not force a mathematician-style proof DAG with lemma prerequisites, theorem dependencies, proof obligations, and unresolved gaps before Lean generation.

Universal skill opportunity:

- `proof-dependency-graph-builder`: extract and validate a proof DAG before formalization, with difficulty estimates and mathlib candidates attached to each node.

### Low: Skill release hygiene is manual

Evidence:

- `skills/ALL_AGENT_SKILL_PROMPTS.md:132` lists a validation checklist.
- The current repository has many skill folders and prompt/reference surfaces, but no standalone release validator for skill folder completeness and hook/index consistency.

Risk:

New specialized skills can miss `agents/openai.yaml`, references, direct routing, or hook ownership updates without immediate failure.

Universal skill opportunity:

- `skill-pack-release-validator`: validate all skill folders, prompt indexes, hook ownership, direct routing, reference paths, and compatibility-wrapper claims.

## Persona Review

### AI Engineer

The framework has good phase decomposition and a growing calibration suite, but control is spread across YAML, docs, scripts, and LLM prompt discipline. The highest leverage universal skills are those that turn conventions into executable contracts:

- hook contract validation,
- gate normalization,
- reasoning-log schema validation,
- manifest-driven suite execution.

### Mathematician

The framework needs a stronger pre-Lean mathematical contract. LaTeX expansion reviews check completeness and binding discipline, but there is no canonical artifact for the proof objects, hypotheses, side conditions, dependency lemmas, and conclusion shape. A universal source-to-formal contract plus proof dependency graph would give semantic preservation critics something concrete to check.

### Lean Expert

The Lean-side controls should move closer to import-aware and declaration-aware verification. Compiling the gold file is necessary but not sufficient. Expected declarations should be checked under intended imports; theorem statements should be inspected for binder shape and non-vacuity; local abstractions should be compared to verified mathlib declarations before draft generation.

## TODO Backlog

### P0

- [x] Create `workflow-contract-validator` skill.
  - [x] Add `scripts/validate_skill_hooks.py`.
  - [x] Check hook id uniqueness, required fields, owner skill folders, shared runtime paths, direct request routing targets, and reference path existence.
  - [x] Validate sample reasoning logs against registered hooks.
  - [x] Add this validator to README development checks.

- [x] Create `reasoning-log-schema-guardian` skill.
  - [x] Add shared `append_reasoning_log_entry` helper for standalone scripts.
  - [x] Migrate proof difficulty estimator and mathlib hierarchy navigator to indexed/timed events.
  - [x] Add `scripts/validate_reasoning_log.py`.
  - [x] Require `payload.skill`, check hook event ids, validate monotonic ordering, and reject unknown hook ids in strict mode.

- [x] Create `gate-policy-controller` skill.
  - [x] Define universal gate decision JSON schema.
  - [x] Provide generic normalization for validator, critique, Lean check, coverage, and audit check records.
  - [x] Support explicit `waived` decisions with reason, owner, expiry, and residual risk.
  - [x] Add fail-fast and audit-only modes.
  - [ ] Wire all existing phase runtimes to emit gate decisions through this controller.

### P1

- [ ] Create `controlled-formalization-suite-runner` skill.
  - [ ] Generalize `tests/wiki_level/run_suite.py` into a manifest-driven runner.
  - [ ] Define a versioned suite manifest schema.
  - [ ] Support suite-level and case-level expected imports, declarations, Lean theorem names, difficulty bands, and required hooks.
  - [ ] Emit standard reasoning-log events through `reasoning-log-schema-guardian`.

- [x] Create `lean-import-context-verifier` skill.
  - [x] Check expected declarations under declared imports, not only `import Mathlib`.
  - [x] Check generated Lean with intended import profiles when requested.
  - [x] Report missing imports, over-broad imports, and declaration-context failures.

- [ ] Create `source-to-formal-contract-builder` skill.
  - [ ] Extract binders, objects, hypotheses, side conditions, conclusion, notation, proof obligations, and allowed abstraction boundaries from reviewed LaTeX.
  - [ ] Store contract JSON beside each generated artifact.
  - [ ] Feed the contract into semantic preservation, logical soundness, and Lean theorem-shape checks.

- [ ] Create `proof-dependency-graph-builder` skill.
  - [ ] Convert proof prose into a dependency DAG before drafting.
  - [ ] Attach difficulty score, web-support status, mathlib candidates, and unresolved gaps to each node.
  - [ ] Gate parent theorem drafting on dependency-node status.

### P2

- [ ] Create `mathlib-concept-ontology-manager` skill.
  - [ ] Move synonyms, phrase hints, and preferred declarations into YAML profiles.
  - [ ] Add profile validation with bounded `#check`s.
  - [ ] Support domain overlays such as elementary logic, set theory, order theory, finite sums, topology, probability, and functional analysis.

- [ ] Create `mathlib-index-builder` and `mathlib-term-expansion-annotator` skills.
  - [ ] Build a versioned module/declaration/import index from local mathlib.
  - [ ] Add hierarchical navigation state with depth, breadth, and verification budgets.
  - [ ] Expand informal terms into probable concept annotations with domain, proof role, confidence, evidence, and verification state.
  - [ ] Gate ambiguous mappings as explicit gaps until Lean and import-context checks pass.
  - [ ] Use the [mathlib indexing plan](../operations/MATHLIB_INDEXING_CONTROL_TODOS.md) as the detailed implementation backlog.

- [ ] Create `lean-theorem-shape-auditor` skill.
  - [ ] Inspect theorem binders, typeclass arguments, namespaces, conclusions, and proof placeholders.
  - [ ] Compare theorem shape against the source-to-formal contract.
  - [ ] Detect vacuity patterns, unused hypotheses, and over-abstract local predicates.

- [ ] Create `waiver-and-risk-register` skill.
  - [ ] Centralize explicit waivers for failed gates, missing mathlib concepts, broad imports, abstract interfaces, and web-research uncertainty.
  - [ ] Require owner, reason, expiry condition, and residual risk.
  - [ ] Include waivers in final reports and suite summaries.

- [ ] Create `skill-pack-release-validator` skill.
  - [ ] Validate every skill has `SKILL.md`, expected `agents/openai.yaml`, references, and hook/index entries where appropriate.
  - [ ] Detect orphaned skills, stale compatibility wrappers, and unreferenced prompt files.
  - [ ] Add as a fast development check.

## Suggested Implementation Order

1. Build `workflow-contract-validator`.
2. Build `reasoning-log-schema-guardian`.
3. Build `gate-policy-controller`.
4. Generalize `controlled-formalization-suite-runner`.
5. Add `lean-import-context-verifier`.
6. Add `source-to-formal-contract-builder` and `proof-dependency-graph-builder`.
7. Move concept policy into `mathlib-concept-ontology-manager`.
8. Add release and waiver controls.

This order starts with framework-level control over the current system, then moves into deeper mathematical and Lean-specific correctness.
