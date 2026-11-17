---
name: physics-lean-goal-sample-autoformalizer
description: Run one FormalPhysics Lean sample through a recursive, goal-oriented physics autoformalization loop. Use when Codex is asked to autoformalize, finish, ground, repair, or assess a specific libraries/MathformerPhysicsLib/Lean/formalphysics_####/MathformerPhysics.lean case one sample at a time, especially when the work must recurse through MathformerPhysicsLib objects before target theorem edits.
---


# Physics Lean Goal Sample Autoformalizer

Use this as the outer meta-skill for a single `formalphysics_####` Lean sample.
Do not batch multiple samples under one goal. Finish, block, or explicitly hand
off the current sample before moving to another one.

## One-Sample Contract

1. Normalize the requested case to one `formalphysics_####` id and Lean file.
2. State the goal as: this one sample reaches `complete_autoformalization`, or
   the loop emits an explicit blocker with evidence.
3. Run or plan the deterministic inventory first:
   - Lean file exists and imports compile;
   - current thoroughness/completeness gate status;
   - open markers such as `sorry`, `admit`, `TODO`, generated-support
     shortcuts, stale frontier language, or target-restating assumptions.
   - semantic-preservation contract coverage, including source target, Lean
     target, preservation status, semantic deltas, and trust boundary;
   - vacuity markers such as `PhysicsContext True`, reflexive
     `UnitDimensionCompatible x x`, and legacy `required_grounding_terms`
     anchors.
4. If any blocker or open marker exists, run the recursive physics loop in this
   order:
   - `physics-lean-drift-pathology-monitor`
   - `physics-math-object-detector`
   - `mathformerphysicslib-object-workbench`
   - Mathlib grounding and MathformerPhysicsLib support edits before theorem
     edits
   - Lean type-system, assumption-context, unit-analysis, physical-semantics,
     assumption, and dimension critic packets
   - pathology-specific repair plans for notational collapse, abstraction
     elevation, proof-strategy alignment, and implicit-premise normalization
   - `physics-lean-pathology-repair-orchestrator`
   - `physics-lean-generative-repair-orchestrator`
   - `physics-lean-generative-critic-orchestrator`
   - `physics-lean-repair-expansion-cartographer`
   - `physics-lean-recursive-repair-loop-controller`
   - Lean execution interpretation, consistency reporting, final hypothesis
     review, and review-refinement routing
5. Apply the next minimal repair only after the controller returns `recurse`.
6. Rerun Lean, foundation verification when foundations changed, and the
   grounded sample thoroughness gate for the current case.
7. Stop only when the current case is complete, blocked by a stable repeated
   signature, or blocked by a missing external dependency that cannot be
   reasonably resolved in the repo.

## Planner

Prefer:

```bash
python skills/physics-lean/physics-lean-goal-sample-autoformalizer/scripts/plan_goal_sample_autoformalization.py \
  --case formalphysics_0014 --json
```

Use `--run-gates` when current evidence is needed:

```bash
python skills/physics-lean/physics-lean-goal-sample-autoformalizer/scripts/plan_goal_sample_autoformalization.py \
  --case formalphysics_0014 --run-gates --json
```

The script emits `physics_lean_goal_sample_autoformalization_plan` with the
sample lock, current evidence, recursive workflow, commands, controller
conditions, and next action.

## Source-Only New Examples

For newly selected FormalPhysics examples, do not batch-generate wrappers and do
not inspect dataset `formal_answer` in the first pass. Run exactly one case at a
time through the recursive goal runner:

```bash
uv run python skills/physics-lean/physics-lean-goal-sample-autoformalizer/scripts/run_recursive_goal_case.py \
  --source-record artifacts/physics_lean/new_qm_source_only/formalphysics_0009/source_record.json \
  --json
```

The runner writes a rebuilt source record under
`artifacts/physics_lean/recursive_goal_runs/<case>/source_record.rebuilt.json`
with successful `workflow_stage_reports`. Completeness gates must use that
rebuilt record; a `skill_usage_ledger` or required-term list is not sufficient
evidence of prior workflow execution.

New source-only records should also carry semantic-preservation metadata when
available:

- `source_target`
- `lean_target_kind`
- `preservation_status`
- `source_assumptions`
- `introduced_assumptions`
- `not_modeled`
- `semantic_deltas`
- `step_alignment_expected`

If those fields are missing, the runner and reviewer should record a design
guard warning and point to
`artifacts/physics_lean/reviews/autoformalization_design_todos.md`. Do not
replace missing semantic metadata with a string-only audit anchor.

## Naming Discipline

Keep API names semantic. Do not create declarations named after loop mechanics
such as `cycle29`, `frontier_bridge_31`, or `from_frontier` unless the object is
actually a recursive evidence record whose Lean type is named `*Frontier`.
Prefer names ending in:

- `_witness` for `PhysicalLawWitness` accessors;
- `_packet` for evidence records or frontier objects;
- `_handoff` for grouped recursive obligations;
- `_target` for target propositions or target records.

## Reference

Read `references/one_sample_loop.md` when implementing or debugging the loop
itself, changing the planner script, or deciding whether a sample can be called
complete.
