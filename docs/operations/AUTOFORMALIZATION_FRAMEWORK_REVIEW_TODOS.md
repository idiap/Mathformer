<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Turn a repository-wide autoformalization review into an evidence-linked improvement backlog.

Intent:
  Prioritize control, acceptance, reproducibility, and physics-semantic work without duplicating existing specialist plans.

Function:
  Records review evidence, actionable TODOs, acceptance criteria, and validation commands for future implementation slices.

Maintenance Notes:
  Re-run the cited controlled gates before closing an item, preserve the distinction between report-generation success and artifact acceptance, and link specialist work rather than copying it.
-->

# Autoformalization Framework Review TODOs

Review date: 2026-07-22.

## Scope And Method

This review covered the natural-language router and AgenticHub, the central
autoformalization runtime, skill and hook control, source and library grounding,
the comprehensive test program, backend integration, generated-artifact
boundaries, and documentation. The physics pass additionally covered the Lean,
SymPy, and Isabelle artifact trees, MathformerPhysicsLib foundations and
coherence gates, physics-specific critics, recursive repair controls, and
promotion/status semantics.

The review used the controlled routes for workflow control, the full quality
gate, and MathformerPhysicsLib coherence. It also ran the missing direct Lean
checks needed to assess the declared physics library target.

## Evidence Baseline

| Surface | Observed evidence | Review interpretation |
| --- | --- | --- |
| Workflow control | `control:all` passes all six child checks | Registration, hook ownership, and basic reasoning-log control are strong |
| Hub and skills | 189 actions, 60 intent routes, 186 canonical skills | Broad capability surface, with a growing consistency burden |
| Full quality | 146 pass, 1 fail, 2 skip out of 149 checks | Broad deterministic coverage, but not a clean or capability-complete release result |
| Failing check | All three clients publish 179 of 186 canonical skills | Seven newly canonical skills are not discoverable from client projection trees |
| Skipped checks | MCP self-test and auth adversarial test skip in the invoking Python environment | `quality:full` is dependency-conditional and does not currently mean every capability executed |
| Router calibration | 10 of 71 documented examples resolve to the wrong route or no route | Router family coverage does not prove user-facing examples work |
| Review request routing | The original full-review request has no controlled route | Cross-cutting inspection is not yet a first-class workflow family |
| Test manifest | `tests/test_matrix.json` contains zero rows; runtime silently loads 149 rows from Python | The visible manifest is not the executable source of truth |
| Test taxonomy | Built-in rows use test kinds absent from the JSON taxonomy | Matrix validation checks field presence but not declared enum membership |
| Test write isolation | Full validation rewrote tracked Isabelle and SymPy artifacts despite declaring artifact-only writes | Safety metadata and runtime effects can diverge |
| Physics family tests | All 69 Physics SymPy, Physics Lean, and MathformerPhysicsLib checks pass | Critic and regression breadth is a clear strength |
| Physics Lean compilation | All 35 `formalphysics_*` Lean files compile individually | The checked case artifacts are kernel-valid in the reviewed worktree |
| Physics library target | `lake build MathformerPhysicsLib` fails because `libraries/MathformerPhysicsLib.lean` is missing | The declared Lake library has no buildable public root |
| Physics coherence | 19 concepts, 50 modules, 15 medium findings, status `complete_with_blockers` | Coherence evidence exists, but it is not propagated consistently into release status |
| Physics status conflict | Promoted cases say `complete_high_grounding`; the backend suite says `ok: true` while its controlled case is `recurse`/`needs_expansion` | `ok` currently conflates successful inspection with accepted completion |
| Physics inventory | Filesystem cases: Lean 35, Isabelle 10, SymPy 11; manifest cases: Lean 10, Isabelle 2, SymPy 10 | Unpromoted or experimental artifacts lack a complete registry state |
| Core implementation size | `agentc.py` is 8,335 lines; `pipeline.py` is 9,335 lines; `mathformer.py` is 5,114 lines | Central runtimes are costly to change and difficult to test independently |
| Generated documentation noise | 1,889 generic “Document the responsibility” blocks across 180 Python files | Mechanical documentation obscures domain-specific contracts |

The test run temporarily changed tracked generated examples. Those exact
test-induced diffs were removed after recording the write-isolation finding;
pre-existing worktree changes were left untouched.

## What Is Working Well

- The proposal-versus-acceptance distinction is explicit in the architecture.
- Hook validation, skill reachability, result-realness checks, source anchors,
  non-vacuity checks, and backend-specific critics are unusually comprehensive.
- Physics workflows cover units, dimensions, frames, regimes, source laws,
  projection bridges, target-restatement pathologies, and recursive repair.
- MathformerPhysicsLib now has reusable foundations and a deterministic
  coherence loop instead of relying only on case-local formalizations.
- All 35 reviewed Lean physics cases compile independently, and adversarial
  fixtures successfully trigger the intended physics critics.

## Priority Summary

| Priority | TODOs | Exit condition |
| --- | --- | --- |
| P0 | AFR-001 through AFR-006 | Validation is hermetic, the test contract is reviewable, and physics release status is backed by fresh compilation and coherent gates |
| P1 | AFR-007 through AFR-013 | Routing, evaluation, physics IRs, semantic parity, and inventory/provenance are trustworthy beyond curated cases |
| P2 | AFR-014 through AFR-016 | Core runtimes and dependency management are maintainable and reproducible |

## P0: Trust And Release Blockers

### AFR-001: Enforce Declared Write Sets For Every Controlled Action

- [x] Add a pre/post execution write-set auditor to AgenticHub.
- [x] Compare changed tracked paths, untracked paths, and artifact paths with
  the action's declared `writes` and safety label.
- [x] Make undeclared tracked-file writes a hard failure for validation,
  inspection, audit, and read-only actions.
- [x] Change `tests/isabelle/run_wiki_case.py` and
  `tests/sympy/run_wiki_case.py` to generate into temporary or artifact-only
  locations during tests.
- [x] Add adversarial fixtures for a read-only action and an artifact-only
  action that attempt an undeclared repository write.

Acceptance evidence:

- A clean-clone `quality:full` run leaves no tracked diff.
- The write-set auditor names the action id, declared roots, and unexpected
  paths when a fixture violates the contract.
- Generated examples change only under an explicit `writes_repo` action with
  `--allow-mutating`.

### AFR-002: Make The Test Matrix A Single, Typed Source Of Truth

- [x] Materialize all executable test rows in `tests/test_matrix.json`, or
  generate that file deterministically from a separate canonical manifest.
- [x] Remove the silent “empty JSON means use the Python fallback” behavior.
- [x] Validate every `module_family`, `test_kind`, `risk_level`, owner, command,
  optional dependency, timeout, expected exit, and write set against a schema.
- [x] Reject test kinds not listed in the manifest taxonomy.
- [x] Add a round-trip check proving that the reviewed manifest and loaded
  runtime matrix have identical ids and fields.

Acceptance evidence:

- The JSON manifest contains the same 149-or-later rows loaded by the runner.
- Deleting or misspelling one row or taxonomy value fails matrix validation.
- `hub:audit`, family actions, and the comprehensive runner consume the same
  canonical data rather than maintaining parallel registries.

### AFR-003: Add A Buildable MathformerPhysicsLib Public Root

- [x] Create `libraries/MathformerPhysicsLib.lean` for the public, promoted library
  surface declared in `lakefile.toml`.
- [x] Import the accepted foundations and only explicitly promoted case modules
  from that root; do not silently export experimental cases.
- [x] Add a separate all-candidate compile action for every tracked physics Lean
  case, regardless of promotion state.
- [x] Register both checks in the hub and the physics test family.

Acceptance evidence:

```bash
lake build MathformerPhysicsLib
```

- The public target succeeds from a clean build.
- The all-candidate check compiles every registered Lean physics case and
  reports per-file hashes and diagnostics.

### AFR-004: Separate Workflow Success From Artifact Acceptance

- [x] Replace overloaded `ok`/`complete` interpretation with explicit fields:
  `workflow_executed`, `checks_passed`, `artifact_status`, `library_status`, and
  `release_ok`.
- [x] Define one status lattice shared by Lean, SymPy, Isabelle, coherence,
  recursive repair, manifests, and human-readable reports.
- [x] Make `recurse`, `needs_expansion`, `repair_required`, and
  `complete_with_blockers` imply `release_ok: false`.
- [x] Keep diagnostic workflows able to exit successfully after producing a
  blocker report, while making release gates fail on that blocker.
- [ ] Derive `MANIFEST.json` and README status tables from the authoritative
  gate result instead of manually maintained labels.

Acceptance evidence:

- The controlled Lean case cannot simultaneously be release-complete and have
  `recursive_status: recurse` or `expansion_status: needs_expansion`.
- The critical coherence release test fails while any blocking repair action is
  open, even though the report-generation action itself succeeds.
- A schema-level test rejects contradictory status combinations.

### AFR-005: Make Physics Lean Acceptance Depend On Fresh Kernel Evidence

- [x] Stop treating stored `consistency_report.json` status as current compile
  evidence without checking artifact and toolchain hashes.
- [x] Compile every promoted Lean physics module during the physics release
  gate, ideally through the public root added by AFR-003.
- [ ] Record Lean version, Mathlib revision, imports, source hash, Lean-file
  hash, command, exit code, and diagnostic digest in every consistency report.
- [x] Mark reports stale when any bound input changes.
- [x] Keep lexical depth and critic heuristics as secondary risk signals, not
  substitutes for compilation or derivation evidence.

Acceptance evidence:

- Modifying a promoted Lean file invalidates its prior report before any
  completion claim is shown.
- A compile failure cannot coexist with `complete_autoformalization` or
  `complete_high_grounding`.
- The physics backend suite executes Lean rather than only loading a prior JSON
  status.

### AFR-006: Calibrate The Physics Coherence Critic Before Repairing Findings

The current redefinition critic emits
`downstream_cases_should_import_foundation` whenever a concept occurs in more
than one downstream module and has a foundation owner. All reviewed downstream
case files already import `MathformerPhysicsLib.Lean.Foundations`, so occurrence
alone does not prove redefinition.

- [x] Classify concept occurrences as declaration, alias, wrapper, theorem use,
  hypothesis use, comment-only mention, or import-only exposure.
- [x] Report exact declaration names and source spans for suspected duplicate
  ownership.
- [x] Block only actual competing ownership, equivalent local definitions, or
  bypasses of an accepted foundation API.
- [x] Treat ordinary downstream use of a canonical concept as healthy reuse.
- [x] Re-run the 15 current findings after critic calibration, then route only
  confirmed duplicates into the existing canonical-ownership repair backlog.

Acceptance evidence:

- A positive fixture with two modules using one imported foundation concept has
  no redefinition finding.
- A negative fixture with a local duplicate declaration is blocking and names
  both owners.
- The coherence report distinguishes confirmed blockers from advisory spread
  metrics and sets `release_ok` according to AFR-004.

## P1: Coverage, Semantics, And Generalization

### AFR-007: Test Every Router Example And Add A Review/Audit Intent

- [x] Add a round-trip test for every documented route example: it must resolve
  to its owning route as the top result.
- [x] Fix the 10 current example mismatches, especially the two SymPy recursive
  goal routes that are outranked by the Lean goal route.
- [x] Add token-boundary or weighted intent features so unrelated single words
  such as `units`, `dependencies`, `mathlib`, or `codex` do not dominate.
- [x] Add an explicit cross-cutting framework-review/audit route that composes
  control, test, documentation, and selected backend inspections.
- [x] Extend coverage auditing beyond family reachability to example fidelity,
  ambiguity, and safety-compatible action selection.

Acceptance evidence:

- All route examples resolve to their documented route.
- The request represented by this review resolves to the new review route.
- Ambiguity tests cover overlapping Lean/SymPy physics goal vocabulary.

### AFR-008: Exercise The Central Autoformalization Runtime End To End

- [x] Add deterministic seeded-provider tests for
  `run_systematic_workflow(...)` and the multi-cycle/dependency paths in
  `agentc.py`.
- [ ] Cover success, compile failure, semantic-critic failure, dependency cycle,
  provider failure, timeout, source drift, and monotonic repair rejection.
- [x] Remove the central autoformalization runtime from blanket
  `generative_only` waiver treatment once deterministic seams exist.
- [ ] Execute and score a bounded subset of generative probes in a distinct
  quality profile; do not call schema validation “generative quality.”
- [x] Use independent or mutation-based oracles so the generator is not the
  sole judge of its own output.

Acceptance evidence:

- The matrix contains direct rows owned by the central runtime/orchestrator.
- At least one test follows a source object through grounding, draft, execution,
  critique, repair, and truthful terminal status.
- Probe-definition validation and actual probe execution have separate ids and
  reported coverage.

### AFR-009: Make `quality:full` Capability-Explicit And Strict When Requested

- [x] Emit a capability ledger listing executed, skipped, unavailable, and
  untested backends and provider-dependent probes.
- [x] Add a strict profile that fails when any declared release capability is
  skipped or unavailable.
- [x] Include Vampire, Rocq, MCP/httpx, Java, provider availability, and exact
  Python package versions in the dependency snapshot.
- [x] Keep a workstation-friendly profile, but label it clearly as conditional
  rather than fully executed.
- [x] Ensure full quality also builds declared Lean library targets.

Acceptance evidence:

- A result cannot say “full” without showing which capabilities actually ran.
- The strict profile fails in the reviewed environment until the two skipped
  MCP checks can execute or are explicitly excluded by profile.
- Dependency snapshots are sufficient to reproduce backend selection.

### AFR-010: Introduce A Typed, Backend-Neutral Physics Derivation IR

The SymPy physics runtime currently combines case registry, source metadata,
derivation construction, units, critics, rendering, and CLI behavior in one
9,335-line module. `case_spec(...)` and `derive_case(...)` encode curated cases
directly, so many tests exercise the same templates that generated the result.

- [x] Define a versioned physics IR for quantities, domains, units, dimensions,
  coordinate frames, regimes, source laws, equation graph, derivation
  obligations, projection bridges, and target claims.
- [x] Parse source records into that IR before selecting a backend.
- [x] Make Lean, SymPy, and Isabelle adapters consume the same obligation ids
  and source anchors.
- [ ] Separate curated case fixtures from production parsing and derivation
  code.
- [x] Add held-out FormalPhysics cases that are not named in a production
  `if/elif` branch.

Acceptance evidence:

- A new source case can reach a truthful draft or blocker without editing the
  central pipeline registry.
- Backend artifacts cite the same source digest and obligation identifiers.
- Held-out and metamorphic tests detect target leakage and template
  overfitting.

### AFR-011: Upgrade Unit And Dimension Checks From Metadata To Semantics

- [x] For SymPy, evaluate a unitful form of each derivation or a formally
  related dimension expression, not only a parallel custom dimension map.
- [x] For Lean, promote reusable typed quantity/unit surfaces where feasible and
  retain explicit projection theorems when reducing to scalar algebra.
- [x] Require dimensionless arguments for exponentials and trigonometric
  functions and compatible dimensions across sums/equalities.
- [x] Add adversarial mutations that alter only a unit exponent, conversion,
  coordinate component, or regime assumption.
- [x] Record which validation is structural, symbolic, numeric, or theorem
  proved.

Acceptance evidence:

- Removing or corrupting metadata cannot make a dimensionally invalid equation
  pass through an unrelated residual check.
- Each promoted physics artifact exposes an executable or proved unit-flow
  witness tied to the equations it validates.

### AFR-012: Make Cross-Backend Physics Parity A First-Class Gate

- [x] Build on the existing cross-backend semantic-packet work rather than
  comparing backend syntax.
- [x] Compare source digest, assumptions, quantity roles, projection policy,
  equation/obligation graph, and terminal trust state across Lean, SymPy, and
  Isabelle.
- [x] Declare intentional backend projections explicitly, especially scalar or
  component backends/isabelle/Isabelle/SymPy reductions of vector/operator source claims.
- [x] Add a coverage matrix showing which cases are promoted, candidate-only,
  blocked, or absent in each backend.
- [x] Prevent a backend-specific complete claim from being presented as
  cross-backend confirmation when the semantic packet is incomplete.

Acceptance evidence:

- Parity checks operate on shared obligation ids from AFR-010.
- A hidden assumption added to only one backend is detected.
- Coverage and semantic parity are reported separately.

### AFR-013: Register Every Physics Artifact And Bind Reports To Provenance

- [x] Include every tracked physics case in `MANIFEST.json`, with explicit
  `experimental`, `draft`, `candidate`, `promoted`, `blocked`, or `archived`
  status.
- [x] Distinguish public-root imports from candidate-only compile coverage.
- [ ] Record source location/digest, generator/action id, generator revision,
  artifact hash, environment/tool versions, and decisive report hashes.
- [x] Generate README coverage tables from this registry.
- [x] Fail integration checks on unregistered case directories or reports whose
  hashes do not match their artifacts.

Acceptance evidence:

- The filesystem and manifest case sets match for Lean, Isabelle, and SymPy.
- Experimental cases remain discoverable without being presented as promoted.
- Regeneration or manual edits invalidate prior summaries deterministically.

## P2: Maintainability And Reproducibility

### AFR-014: Split The Core Runtimes Behind Stable Typed Interfaces

- [ ] Decompose `agentc.py`, `backends/sympy/MathformerPhysicsSympy/pipeline.py`, and the hub
  registry into focused packages with explicit public APIs.
- [x] Move report/status models into shared versioned schema modules.
- [x] Keep backward-compatible facades while migrating skills and tests.
- [x] Add import-cycle checks and unit tests for each extracted subsystem.
- [ ] Replace generic generated docstrings with short, domain-specific
  invariants where they add maintenance value.

Acceptance evidence:

- Source intake, grounding, execution, status aggregation, report rendering,
  and backend adapters can be tested independently.
- Public callers do not depend on internal case tables or report dictionary
  shape by convention alone.
- Documentation quality checks reward useful contracts rather than boilerplate
  count.

### AFR-015: Lock Python Dependency Profiles

- [x] Add a committed lock for core, physics, MCP, document, and provider
  profiles while retaining concise human-authored dependency declarations.
- [ ] Test the minimum supported and locked reference environments separately.
- [x] Record the resolved package set and Python ABI in run manifests.
- [x] Add a scheduled dependency-refresh workflow with backend regressions.

Acceptance evidence:

- A clean machine can reproduce the reviewed reference environment without
  resolving broad version ranges differently.
- Dependency drift is visible as a reviewed lock change plus test evidence.

### AFR-016: Add Independent Evaluation And Calibration Dashboards

- [ ] Track performance separately on curated regression cases, held-out source
  cases, adversarial mutations, and genuine new formalization tasks.
- [ ] Calibrate heuristic scores such as proof-step depth, bridge count, critic
  agreement, and grounding score against independently reviewed outcomes.
- [x] Report false-positive and false-negative rates for source drift,
  target-restatement, duplicate ownership, unit mismatch, and completion gates.
- [x] Track cost, retries, wall time, and convergence without exposing hidden
  chain-of-thought.

Acceptance evidence:

- A dashboard can answer whether a gate is accurate, not merely whether it ran.
- Metric improvements cannot be claimed solely from the same fixtures used to
  design the metric.

## Existing Specialist Backlogs To Reuse

Do not duplicate these workstreams when implementing the items above:

- Formal-science object intake, canonical ownership, Mathlib grounding, and
  replacement of trivial bridges:
  [FORMAL_SCIENCE_GROUNDING_RECURSION_TODOS.md](../libraries/FORMAL_SCIENCE_GROUNDING_RECURSION_TODOS.md)
- Lean physics derivation-completeness semantics and target-restatement policy:
  [LEAN_PHYSICS_DERIVATION_COMPLETENESS_TODOS.md](LEAN_PHYSICS_DERIVATION_COMPLETENESS_TODOS.md)
- MathformerPhysicsLib coherence workflow implementation:
  [MATHFORMERPHYSICSLIB_COHERENCE_GROUNDING_WORKFLOW.md](../libraries/MATHFORMERPHYSICSLIB_COHERENCE_GROUNDING_WORKFLOW.md)
- Physics SymPy recursive workflow and cross-backend packet work:
  [PHYSICS_SYMPY_LEAN_INSPIRED_WORKFLOW_TODOS.md](PHYSICS_SYMPY_LEAN_INSPIRED_WORKFLOW_TODOS.md)
- Reasoning-log consumer readiness:
  [REASONING_LOG_CONSUMER_TODOS.md](REASONING_LOG_CONSUMER_TODOS.md)

## Recommended Execution Order

1. AFR-001 and AFR-002 make subsequent validation trustworthy and reviewable.
2. AFR-003 through AFR-006 establish truthful PhysicsLib build and release
   semantics before more artifacts are promoted.
3. AFR-007 through AFR-009 close control-plane and test-profile gaps.
4. AFR-010 through AFR-013 improve physics generalization, semantic depth, and
   backend parity.
5. AFR-014 through AFR-016 reduce maintenance cost and improve reproducibility
   and scientific evaluation.
