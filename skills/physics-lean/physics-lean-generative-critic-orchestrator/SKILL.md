---
name: physics-lean-generative-critic-orchestrator
description: Orchestrate explicit generative critics for Lean physics formalizations using deterministic critic packets plus Codex-exec adversarial probes over physical semantics, assumptions, unit/dimension discipline, FormalScience drift pathologies, non-vacuity, and source fidelity.
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

# Physics Lean Generative Critic Orchestrator

Use after Lean execution, unit analysis, and first-pass deterministic critic
reports are available, or when a physics formalization looks plausible but may
be empty, over-strengthened, dimensionally erased, or physically misread.

## Critic Panel

Run these critics independently before refinement:

1. `physics-lean-physical-semantics-critic`
2. `physics-lean-assumption-critic`
3. `physics-lean-dimension-critic`
4. `physics-lean-drift-pathology-monitor`
5. Generic Lean critics: syntactic correctness, semantic preservation, logical
   soundness, mathlib alignment, realness, declaration shape, and non-vacuity.

Then run a generative panel with Codex exec when the artifact is high-risk,
near-final, or critic disagreement remains.

## Codex Exec Use

Use the existing content runner:

```bash
python3 skills/control/skill-test-program-orchestrator/scripts/run_content_skill_codex_exec_tests.py \
  --execute \
  --skill physics-lean-generative-critic-orchestrator \
  --json
```

For a dry run of planned probes, omit `--execute`.

## Reflection Policy

Treat critics as adversarial instruments, not authorities. A critic is useful
when it localizes a possible physics failure and proposes evidence that could
confirm or falsify it. A critic is harmful when it pushes the workflow toward a
more elaborate empty formalism or adds assumptions only to make Lean easier.

Require at least one of these before blocking final status:

- a source-anchor mismatch,
- a Lean theorem-shape or non-vacuity finding,
- a unit/dimension inconsistency,
- an unlabeled assumption-strengthening finding,
- repeated independent Codex-exec probes with the same blocker class.

Prefer `scripts/build_physics_lean_generative_critic_plan.py` to create the
critic plan and Codex-exec probe prompts.
