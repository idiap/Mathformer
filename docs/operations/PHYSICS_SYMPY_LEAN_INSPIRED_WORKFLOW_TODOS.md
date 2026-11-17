<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Keep the Physics SymPy workflow review explicit after comparing it with the
  more recursive Lean physics autoformalization workflows.

Intent:
  Define concrete, self-contained TODOs for making Physics SymPy derivation
  workflows more goal-oriented, recursive, auditable, and consumer-ready without
  turning SymPy into a theorem-prover backend.

Function:
  Guides future skill, hook, router, and test changes for the executable
  equational Physics SymPy pipeline.

Maintenance Notes:
  Keep this synchronized with skills/SKILL_HOOKS.yaml, TODO.md,
  skills/physics-sympy/physics-sympy-workflow-orchestrator/,
  skills/physics-sympy/physics-sympy-review-refinement-router/, tests/physics_sympy/, and
  libraries/MathformerPhysicsLib/SymPy/formalphysics_*/MathformerPhysics.py artifacts.
-->

# Physics SymPy Lean-Inspired Workflow TODOs

## Goal

Make the Physics SymPy derivation workflow as explicit and goal-oriented as the
Lean physics recursive workflow while preserving the right backend semantics:
SymPy should produce executable equational derivation traces, not Lean-style
kernel proofs.

The useful Lean inspiration is the outer-loop discipline:

- one sample is locked until complete, blocked, or explicitly handed off;
- completeness means more than "the file runs";
- the workflow recurses through missing support objects before changing the
  final target;
- every repair has evidence, a local surface, and a stop condition;
- semantic preservation is checked as a first-class design guard.

## Current Baseline

Observed on 2026-07-08:

- `skills/physics-sympy/physics-sympy-workflow-orchestrator` already states that it converts
  a Lean-inspired physics pipeline into an equational workflow plan.
- The SymPy hook surface already includes dependency probing, source
  extraction, symbol/dimension/unit/equation/regime/frame/gap/law packets,
  installed-library grounding, equation surfaces, assumption contexts,
  execution, interpretation, unit and step verification, numeric sampling,
  deterministic critics, final equation reviews, localized refinement, and
  optional post-hoc FormalPhysics `formal_answer` reflection.
- `libraries/MathformerPhysicsLib/SymPy/formalphysics_0000/MathformerPhysics.py`
  already exposes a rich artifact contract: source task text, informal
  derivation commentary, SymPy alignment, quantity table, assumptions,
  derivation steps, equation and quantity surfaces, equation graph, law table,
  projection bridges, equivalence certificates, library grounding, assumption
  context, and validators.
- The controlled suite and phase tests give strong deterministic coverage, but
  they do not yet act as a one-case recursive goal controller for a specific
  `formalphysics_####` SymPy artifact.
- The review-refinement router is already local and monotonic, but it has no
  explicit design-guard mode for broader semantic-preservation debts.
- The workflow lacks a SymPy-native equivalent of the Lean repair expansion
  cartographer and recursive loop controller.

## Design Principles

- `complete_sympy_physics_derivation` means executable source-preserving trace,
  not merely import success or symbolic residual zero.
- A complete artifact must preserve the source statement, source assumptions,
  quantity roles, units, dimensions, frames, regimes, laws, projection bridges,
  generated support, numeric domains, and final target shape.
- SymPy library grounding should remain an API evidence requirement. Local
  placeholders are allowed only when labeled as generated support or blockers.
- FormalPhysics `formal_answer` is post-hoc and inspiration-only. First-pass
  case repair stays source-only.
- A recursive repair should touch the smallest object surface that explains the
  blocker: source packet, quantity surface, unit/dimension model, equation
  parser, assumption context, law grounding, SymPy library grounding,
  projection bridge, transformation step, numeric domain, or target
  nonleakage.
- Reasoning logs should record workflow evidence, not hidden chain-of-thought:
  goal state, stage, decision, evidence, artifacts, risks, and next action.

## TODOs

### PSY-001: Add A One-Sample Physics SymPy Goal Skill

- [x] Add a skill such as `physics-sympy-goal-sample-autoformalizer`.
- [x] Normalize the request to exactly one `formalphysics_####` case and one
  Python artifact path.
- [x] State the goal as `complete_sympy_physics_derivation` or an explicit
  blocker with evidence.
- [x] Forbid batching multiple FormalPhysics SymPy examples under one goal.
- [x] For new examples, keep the first pass source-only and avoid inspecting
  dataset `formal_answer`.
- [x] Emit a plan with sample lock, current evidence, open blockers, recursive
  workflow, commands, controller conditions, and next action.

Acceptance:

```bash
.venv/bin/python skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py \
  --case formalphysics_0000 --json
```

### PSY-002: Implement A Current-Evidence Planner

- [x] Add
  `skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py`.
- [x] Support `--case`, `--sympy-file`, `--run-gates`, and `--json`.
- [x] Report whether the artifact exists, imports, executes, and exposes the
  expected source, commentary, quantity, equation, assumption, law, projection,
  grounding, unit, numeric, and final-review surfaces.
- [x] Detect open markers such as `TODO`, placeholder equations, missing
  `SymPy alignment`, empty equation graphs, stale target leakage suppressions,
  scalar-only collapses, and missing generated-support labels.
- [x] Return `next_action` as one of `complete`, `recurse`, `blocked`, or
  `needs_initial_draft`.

Acceptance:

```bash
.venv/bin/python skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py \
  --case formalphysics_0000 --run-gates --json
```

### PSY-003: Add A SymPy Recursive Expansion Cartographer

- [x] Add a deterministic cartographer for open SymPy physics repair objects.
- [x] Classify frontier objects by surface:
  `source_anchor`, `quantity`, `dimension`, `unit`, `frame`, `regime`,
  `equation_node`, `law_grounding`, `sympy_api_grounding`,
  `projection_bridge`, `transformation_step`, `numeric_domain`,
  `target_nonleakage`, `trace_realness`, and `consumer_reasoning_log`.
- [x] For each frontier item, record evidence, owner skill, artifact path,
  minimal repair surface, affected validators, and stop condition.
- [x] Distinguish missing physics content from missing executable SymPy support.
- [x] Preserve the existing review-refinement surfaces instead of introducing
  broad rewrite instructions.

Acceptance:

```bash
.venv/bin/python skills/physics-sympy/physics-sympy-repair-expansion-cartographer/scripts/map_physics_sympy_repair_expansion.py \
  --case formalphysics_0000 --json
```

### PSY-004: Add A SymPy Recursive Loop Controller

- [x] Add a controller that consumes the expansion map and decides `complete`,
  `recurse`, or `blocked`.
- [x] Require monotonic evidence before applying a repair.
- [x] Stop as blocked when the same unresolved blocker recurs across repeated
  iterations with no new local repair surface.
- [x] Block completion when any high-severity frontier remains open.
- [x] Record controller decisions in a machine-readable reasoning-log event.

Acceptance:

```bash
.venv/bin/python skills/physics-sympy/physics-sympy-recursive-repair-loop-controller/scripts/control_physics_sympy_recursive_repair.py \
  --expansion-map artifacts/physics_sympy/recursive_goal_runs/formalphysics_0000/repair_expansion.json \
  --json
```

### PSY-005: Add A SymPy Design-Guard Review Mode

- [x] Extend `physics-sympy-review-refinement-router` with a
  `design_guard_review` mode.
- [x] Detect semantic-preservation debts that are broader than one failed final
  equation review.
- [x] Flag missing or stale source commentary, informal-to-SymPy alignment,
  target nonleakage evidence, assumption provenance, projection bridges,
  generated-support labeling, installed-library grounding, and consumer-ready
  reasoning-log events.
- [x] Route findings back to local repair surfaces rather than whole-artifact
  rewrites.

Acceptance:

```bash
.venv/bin/python skills/physics-sympy/physics-sympy-review-refinement-router/scripts/plan_physics_sympy_review_refinement.py \
  --mode design_guard_review --json
```

### PSY-006: Add A Grounded Sample Thoroughness Gate

- [x] Add `tests/physics_sympy/run_grounded_sample_thoroughness.py`.
- [x] Gate one specific `formalphysics_####` artifact rather than only the
  controlled demonstration suite.
- [x] Require source commentary, equation-surface depth, high library
  grounding, unit/dimension checks, numeric sanity checks, final reviews,
  target nonleakage, trace realness, and no high-severity design-guard
  findings.
- [x] Report `compiled_or_executed`, `grounded_scaffold`,
  `derivation_partial`, `complete_sympy_physics_derivation`, or `blocked`.

Acceptance:

```bash
.venv/bin/python tests/physics_sympy/run_grounded_sample_thoroughness.py \
  --case formalphysics_0000 --json
```

### PSY-007: Add A Source-Only FormalPhysics SymPy Runner

- [x] Add a runner for new FormalPhysics SymPy source records.
- [x] Rebuild one source record at a time under
  `artifacts/physics_sympy/recursive_goal_runs/<case>/`.
- [x] Include workflow-stage reports, semantic-preservation metadata,
  source-only trust boundary, and any blockers.
- [x] Do not use a string-only audit anchor as evidence that a workflow stage
  actually ran.

Acceptance:

```bash
.venv/bin/python skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/run_recursive_goal_case.py \
  --source-record artifacts/physics_sympy/source_only/formalphysics_0000/source_record.json \
  --json
```

### PSY-008: Make Post-Hoc Formal-Answer Reflection Auditable

- [x] Keep `physics-sympy-formal-answer-reflector` optional and post-hoc.
- [x] Require a pre-reflection ledger proving that the candidate, blocker, or
  final consistency report existed before `formal_answer` inspection.
- [x] Reject any reflection-suggested change that bypasses localized monotonic
  review refinement.
- [x] Record whether each accepted change came from source evidence, execution
  evidence, deterministic critics, or post-hoc inspiration.

Acceptance:

```bash
.venv/bin/python tests/physics_sympy/run_formal_answer_reflection_policy.py --json
```

### PSY-009: Add Native Reasoning Logs To High-Value SymPy Scripts

- [x] Add domain-specific reasoning-log events to the workflow orchestrator,
  review-refinement router, future goal planner, future expansion cartographer,
  future controller, and grounded thoroughness gate.
- [x] Each event should include goal id, case id, stage, evidence, artifacts,
  decision, risks, and next action.
- [x] Keep logs concise and machine-readable for consumer applications and MCP
  workflow resources.
- [x] Reuse the consumer-grade reasoning-log contract rather than adding a
  separate SymPy-specific log schema.

Acceptance:

```bash
python skills/control/reasoning-log-schema-guardian/scripts/audit_skill_reasoning_log_coverage.py \
  --strict --json
```

### PSY-010: Add Natural-Language Routes For Recursive SymPy Cases

- [x] Route requests such as `same for SymPy formalphysics_0000`,
  `recursive goal oriented physics SymPy example 0000`, and
  `review the SymPy physics derivation workflow for one case`.
- [x] Expose matched skill routes, action ids, safety labels, and writes.
- [x] Preserve the one-sample lock in router output.

Acceptance:

```bash
python scripts/mathformer.py ask "recursive goal oriented physics SymPy example 0000" --json
python scripts/mathformer.py ask "same for SymPy formalphysics_0000" --json
```

### PSY-011: Make Dependency Failures Friendly And Controlled

- [x] Ensure SymPy physics validations run through the repo environment or emit
  a clear dependency failure when `sympy` is unavailable.
- [x] Prefer `.venv/bin/python` in low-level acceptance commands and controlled
  hub actions for user-facing workflows.
- [x] Add a test that missing SymPy is reported as a dependency blocker, not a
  generic Python traceback.

Acceptance:

```bash
.venv/bin/python tests/physics_sympy/run_phase1_dependency_grounding.py --json
.venv/bin/python tests/physics_sympy/run_controlled_suite.py --json
```

### PSY-012: Add Cross-Backend Semantic Comparison Packets

- [x] Compare Lean and SymPy artifacts for the same source only as alignment
  evidence, never as gold labels for each other.
- [x] Report source target, backend target, assumptions, not-modeled content,
  semantic deltas, unit/dimension treatment, projection bridges, and support
  object status.
- [x] Allow comparison packets to feed reviews while preserving backend-native
  completion criteria.

Acceptance:

```bash
.venv/bin/python tests/physics_sympy/run_cross_backend_semantic_packet.py \
  --case formalphysics_0000 --json
```

### PSY-013: Add Recursive Run Reports

- [x] Store per-case reports under
  `artifacts/physics_sympy/recursive_goal_runs/<case>/`.
- [x] Emit `source_record.rebuilt.json`, `current_evidence.json`,
  `repair_expansion.json`, `controller_decision.json`, `thoroughness.json`,
  `reasoning.jsonl`, and a concise Markdown summary.
- [x] Include statuses for source preservation, executable trace, grounding,
  critics, final reviews, recursive frontier, and formal-answer reflection
  boundary.

Acceptance:

```bash
.venv/bin/python skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/run_recursive_goal_case.py \
  --case formalphysics_0000 --json
```

### PSY-014: Add Adversarial Design-Guard Fixtures

- [x] Add fixtures for scalar erasure, target leakage, missing frame or regime,
  placeholder library grounding, missing projection bridge, numeric domain
  holes, silent assumption strengthening, and undocumented generated support.
- [x] Ensure each fixture fails the design-guard review or grounded sample
  thoroughness gate with a precise local repair route.

Acceptance:

```bash
.venv/bin/python tests/physics_sympy/run_adversarial_design_guard_suite.py --json
```

## Existing Validation Commands

Use these commands to check the current baseline while the TODOs above are
implemented:

```bash
.venv/bin/python skills/physics-sympy/physics-sympy-workflow-orchestrator/scripts/build_physics_sympy_workflow_plan.py \
  --self-test --json
.venv/bin/python tests/physics_sympy/run_controlled_suite.py --json
.venv/bin/python tests/physics_sympy/run_phase14_workflow_hooks.py --json
.venv/bin/python tests/physics_sympy/run_phase18_release_criteria.py --json
python scripts/mathformer.py audit --strict --json
```

## Done Criteria

- A user can request one FormalPhysics SymPy physics case in natural language
  and receive a one-sample locked plan.
- The plan can recurse through missing source, object, grounding, equation,
  assumption, projection, numeric, and trace support before final-target edits.
- Complete status is reserved for source-preserving, executable,
  unit/dimension-checked, critic-reviewed, and target-nonleaking derivations.
- All high-value SymPy workflow decisions produce concise machine-readable
  reasoning-log events.
- MCP consumers can access summaries through workflow-level Mathformer actions
  without learning internal script paths.
