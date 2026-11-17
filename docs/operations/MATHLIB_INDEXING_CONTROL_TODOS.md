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

# Mathlib Indexing and Controlled Navigation TODOs

Reflection date: 2026-06-05

## Goal

Mathformer should index mathlib as a navigable mathematical object, not only as a
flat declaration-name search space. The index should let the workflow move from
informal terms to probable concepts, then to module neighborhoods, verified
declarations, narrow imports, and source-to-Lean prompt hints under explicit
control gates.

The key design rule is:

- probabilistic or heuristic annotations may guide exploration;
- only Lean-verified declarations and import contexts may guide final drafting;
- unresolved ambiguity must remain visible as a gap, not be silently collapsed to
  the top lexical hit.

## Current Evidence

Existing tools already cover pieces of the process:

- `mathlib-hierarchy-navigator` exposes module parents, children, siblings,
  query results, imports, and local declarations.
- `mathlib-concept-candidate-mapper` ranks declaration and module candidates
  from concepts and informal text.
- `mathlib-candidate-verifier` checks declarations with Lean.
- `mathlib-import-set-builder`, `lean-import-context-verifier`, and
  `mathlib-import-minimizer` control import scope.
- `mathlib-concept-coverage-reviewer` separates verified coverage, candidate-only
  coverage, and gaps.

Observed weakness from local probes:

- The query `compact` can rank operator-compactness before topological
  set-compactness when the context is missing.
- The concept `finite_intersection` currently falls to irrelevant algebraic
  declarations because phrase-level concept expansion is too weak.

These are indexing problems, not only ranking problems. The system needs a
typed concept layer and a navigation state that carries domain, proof role, and
verification status.

## Target Index Layers

### 1. Module Tree Index

Deterministic fields:

- `module`: full module name, for example `Mathlib.Topology.Compactness.Compact`
- `parent`, `children`, `siblings`, `depth`, `leaf_count`
- `source_path`, `source_ref`
- direct imports and imported-by edges when available
- coarse area tags inferred from path segments, for example `topology`,
  `analysis`, `order`, `measure_theory`, `linear_algebra`

Use:

- controlled broad-to-specific navigation;
- avoiding jumps from `Topology.Compactness` to unrelated `AlgebraicGeometry`
  compactness unless context supports that domain;
- import-set planning.

### 2. Declaration Index

Deterministic fields:

- `qualified_name`, `short_name`, `namespace`, `kind`, `module`, `line`
- raw signature and source excerpt
- doc comment when locally adjacent and parseable
- attributes when easy to extract, for example `simp`, `ext`, `norm_cast`
- declaration-name tokens and namespace tokens
- theorem-shape hints from the signature: binder names, binder types, typeclass
  requirements, conclusion head symbol, proposition kind
- Lean check status under one or more import profiles

Use:

- verified candidate ranking;
- theorem-shape matching against source-to-formal contracts;
- rejecting local wrapper definitions when mathlib already has a native
  declaration.

### 3. Concept Ontology Index

Reviewed fields:

- `concept_id`: stable normalized concept key, for example
  `topology.compact_set`
- `surface_terms`: informal phrases and LaTeX forms
- `domain_tags`: mathematical areas where the concept is valid
- `lean_objects`: probable Lean predicates/classes/structures
- `preferred_modules` and `preferred_declarations`
- `negative_domains`: contexts where the term is misleading
- `required_context_clues`: words, binders, or notation needed to disambiguate
- `status`: `reviewed`, `candidate`, `deprecated`, or `gap`

Use:

- phrase expansion before declaration search;
- stable regressions for common concepts;
- domain overlays such as elementary logic, set theory, topology, measure theory,
  functional analysis, convex geometry, and finite combinatorics.

### 4. Probable Annotation Layer

Generated but controlled fields:

- `surface_term`: term found in source text
- `normalized_candidates`: one or more concept ids
- `probable_domain`: ranked domain tags with confidence
- `proof_role`: `object`, `predicate`, `hypothesis`, `conclusion`, `lemma`,
  `construction`, `tactic_hint`, or `side_condition`
- `lean_shape_guess`: likely Lean form, kept as a hint only
- `confidence`: numeric or ordinal confidence
- `evidence`: source span, neighboring words, LaTeX notation, matched ontology
  terms, and module/declaration evidence
- `verification_state`: `unverified`, `decl_checked`, `import_checked`,
  `contract_aligned`, or `gap`

Use:

- preserving uncertainty through the workflow;
- telling the drafter why a candidate was selected;
- surfacing ambiguous terms before they become wrong Lean.

### 5. Navigation State

Each exploration step should record:

- current source term or concept id;
- current module focus and ancestor path;
- candidate modules with scores and domain tags;
- candidate declarations with verification state;
- next allowed operation: `descend`, `inspect_sibling`, `query_declarations`,
  `verify_candidate`, `narrow_imports`, `mark_gap`;
- budget counters for breadth, depth, declaration checks, and fallback searches.

This state gives the system a controlled path through mathlib instead of a
single-shot lexical ranking.

## Probable Annotation Examples

These examples are intentionally probable until Lean verification confirms them.

### `compact`

- `topology.compact_set`: likely Lean object `IsCompact s`; domain clues include
  `set`, `cover`, `closed`, `open`, `intersection`, `finite subcover`.
- `topology.compact_space`: likely Lean object `CompactSpace X`; domain clues
  include whole-space statements and typeclass-style assumptions.
- `analysis.compact_operator`: likely Lean object `IsCompactOperator f`; domain
  clues include linear maps, normed spaces, balls, bounded sets, and operators.
- Gate: never choose compact-operator declarations for a set-compactness source
  unless operator clues are present.

### `finite intersection`

- `set.finite_intersection_family`: likely represented with a finite index set,
  `Finset`, or a finite subtype; domain clues include family of sets and
  intersection notation.
- `topology.finite_intersection_property`: likely connected to compactness and
  closed-set families; domain clues include every finite subfamily has nonempty
  intersection.
- `order.infimum_finite`: possible order/lattice reading; domain clues include
  semilattice notation rather than sets.
- Gate: if no set/topology/order context is present, mark the annotation
  ambiguous instead of routing to unrelated algebra declarations.

### `convex`

- `analysis.convex_set`: likely Lean object `Convex R s`; domain clues include
  vector spaces, affine combinations, segments, and sets.
- `geometry.convex_cone`: likely if cone, positive scalar, or pointed cone
  language appears.
- Gate: require the scalar field/ring and carrier set shape before generating a
  final Lean statement.

### `measurable`

- `measure_theory.measurable_function`: likely Lean object `Measurable f`;
  domain clues include functions between measurable spaces.
- `measure_theory.measurable_set`: likely Lean object `MeasurableSet s`;
  domain clues include subsets, sigma-algebras, and events.
- Gate: object-vs-set role must be explicit in the source-to-formal contract.

### `tends to` / `converges`

- `topology.filter_tendsto`: likely Lean object `Filter.Tendsto f l l'`.
- `sequence_convergence`: likely a specialized theorem over `atTop` or sequence
  filters.
- Gate: require filter endpoints, sequence/domain notation, or mark as a gap.

## Controlled Navigation Loop

1. Extract source terms and proof roles from reviewed LaTeX.
2. Expand terms with the concept ontology and probable annotation layer.
3. Choose a module-family frontier from domain tags and hierarchy evidence.
4. Descend/inspect/query under a bounded navigation state.
5. Rank declarations using concept match, theorem-shape match, module context,
   source excerpt, and import cost.
6. Verify candidate declarations with Lean `#check`.
7. Verify the intended import context.
8. Emit a coverage packet: verified concepts, ambiguous concepts, gaps, and
   recommended prompt hints.
9. Feed only verified and contract-aligned hints to drafting; keep probable
   annotations as explainable context, not proof obligations.
10. Record failures as regression probes for the ontology/index.

## TODO Backlog

### P0: Make the Index First-Class

- [x] Create a `mathlib-index-builder` skill.
  - Why: current scripts rescan source files and do not share one typed index.
  - Done when: a command builds `artifacts/mathlib_index/index.json` or
    `index.sqlite` with module, declaration, and import metadata.
  - Validation: `python3 skills/mathlib/mathlib-index-builder/scripts/build_mathlib_index.py --json`

- [x] Add a version stamp to every index artifact.
  - Why: mathlib evolves; stale rankings can silently refer to moved or removed
    declarations.
  - Done when: the index records Lean version, mathlib git revision, file count,
    declaration count, and build timestamp.
  - Validation: index validation fails when the local mathlib revision changes.

- [x] Move hardcoded concept synonyms and preferred declarations into reviewed
  YAML ontology profiles.
  - Why: concept policy is currently embedded in code and hard to audit.
  - Done when: `SYNONYMS`, `PHRASE_HINTS`, and `PREFERRED_DECLS` are loaded from
    profile files with schema validation.
  - Validation: existing concept-mapper tests remain passing.

### P1: Add Hierarchical and Probable Annotation Control

- [x] Create a `mathlib-term-expansion-annotator` skill.
  - Why: informal terms need domain, role, and ambiguity annotations before
    declaration search.
  - Done when: source text becomes a JSON list of probable annotations with
    `surface_term`, `concept_id`, `domain_tags`, `proof_role`, `confidence`,
    `evidence`, and `verification_state`.
  - Validation: controlled fixtures produce stable annotations for `compact`,
    `convex`, `finite intersection`, `measurable`, and `tendsto`.

- [x] Add domain-disambiguation gates.
  - Why: terms like `compact`, `normal`, `regular`, `complete`, `closed`, and
    `finite` are overloaded across mathlib.
  - Done when: ambiguous terms require explicit context clues before a single
    domain-specific declaration can be promoted.
  - Validation: `compact` in a set/topology fixture does not rank compact
    operator declarations first.

- [x] Add phrase-level expansion for multiword concepts.
  - Why: flat token ranking fails on phrases such as `finite intersection`.
  - Done when: phrase matches can route to concept ids before token splitting.
  - Validation: `finite intersection property` routes to set/topology/order
    candidates or an explicit ambiguity gap, not unrelated algebra lemmas.

- [x] Add proof-role annotations to mapping.
  - Why: the same word can indicate an object, hypothesis, conclusion, theorem
    pattern, or tactic.
  - Done when: mapper output separates object candidates from theorem lemmas and
    tactic hints.
  - Validation: drafting prompts receive role-specific hints.

### P1: Control Navigation as a Stateful Process

- [x] Add a `mathlib-navigation-state-planner` skill.
  - Why: exploration should be bounded and auditable rather than one-shot search.
  - Done when: each navigation run records current focus, candidate frontier,
    allowed next operation, depth/breadth budgets, and stop reason.
  - Validation: reasoning logs show `descend`, `inspect_sibling`,
    `query_declarations`, `verify_candidate`, and `mark_gap` transitions.

- [x] Integrate declaration-neighborhood evidence into candidate scores.
  - Why: local imports, sibling modules, and nearby lemmas often reveal the right
    API family.
  - Done when: candidates include neighborhood features and explanation fields.
  - Validation: candidate reports explain why each top declaration is selected.

- [x] Add import-cost scoring.
  - Why: broad imports hide mapping mistakes and make generated Lean less
    reusable.
  - Done when: candidates carry estimated import cost and intended import set.
  - Validation: `lean-import-context-verifier` checks top candidates under the
    proposed imports.

### P2: Improve Declaration Semantics

- [x] Extract theorem-shape summaries from declaration signatures.
  - Why: name overlap is insufficient; the mapper needs binder and conclusion
    shape.
  - Done when: declarations include normalized head symbols, binder type heads,
    typeclass requirements, and conclusion form.
  - Validation: theorem-shape matching improves ranking on controlled fixtures.

- [x] Add doc-comment and namespace embeddings as optional rerankers.
  - Why: comments and namespaces carry mathematical semantics not always visible
    in names.
  - Done when: embeddings are cached separately from deterministic metadata and
    never override failed Lean verification.
  - Validation: reranking is monotonic on baseline cases or gated behind a
    comparison report.

- [x] Build a lightweight declaration graph.
  - Why: declarations are connected by namespace, imports, theorem families,
    attributes, and local source neighborhoods.
  - Done when: index queries can return related lemmas, constructors,
    introduction/elimination lemmas, and rewrite lemmas for a chosen declaration.
  - Validation: neighborhood reports help refinement choose supporting lemmas.

### P2: Regression and Evaluation

- [x] Add indexing regression fixtures.
  - Why: common overloaded terms should not regress silently.
  - Done when: fixtures cover compactness, finite intersections, convexity,
    measurability, tendsto, monotonicity, closure, boundedness, and filters.
  - Validation: deterministic report includes index-ranking and ambiguity-gate
    checks.

- [x] Add a gap ledger for unmapped concepts.
  - Why: missing mathlib coverage should become reusable data, not a forgotten
    prompt note.
  - Done when: every unmapped concept has a stable id, source span, attempted
    domains, failed candidates, and next action.
  - Validation: coverage reports include open gaps and resolved-gap history.

- [x] Add monotonic index-refinement checks.
  - Why: improving one term expansion can degrade previous successful mappings.
  - Done when: ontology/index changes must pass old controlled cases before they
    can become default.
  - Validation: reflective refinement reports show no baseline regressions.

## Exit Criteria

The mathlib indexing layer is mature when:

- common proof terms become stable probable annotations with visible ambiguity;
- navigation can be replayed from reasoning logs;
- top mapping hints are Lean-verified under intended imports;
- ambiguous or missing concepts are blocked as gaps, not guessed;
- index and ontology changes are monotonic over controlled fixtures.
