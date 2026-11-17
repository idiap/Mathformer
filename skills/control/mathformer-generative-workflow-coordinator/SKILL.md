---
name: mathformer-generative-workflow-coordinator
description: Generatively coordinate Mathformer workflows from natural-language goals. Use when Codex must interpret, decompose, order, explain, or invoke one or more controlled workflows and the exact workflow names are unknown or span multiple families.
---


# Mathformer Generative Workflow Coordinator

Act as the primary Codex-facing coordinator for Mathformer. Interpret the
user's desired outcome in ordinary language, compose the smallest sufficient
workflow, and keep every executable step behind the deterministic router and
workflow hub.

This is a generative orchestration skill: Codex supplies intent interpretation,
decomposition, sequencing, and adaptation. It must never invent action ids,
treat a generated plan as execution evidence, or bypass repository controls.

## Coordination Contract

1. Preserve the user's outcome, constraints, authorization, and requested
   deliverables. Do not broaden the task merely because adjacent workflows
   exist.
2. If orientation is needed, inspect the current workflow catalogue:

   ```bash
   python skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py \
     --help-pipeline --json
   ```

3. Decompose the goal only when it genuinely requires distinct workflow
   outcomes. Keep dependencies explicit and prefer an existing hub sequence
   over a newly generated sequence.
4. Resolve every candidate intent through the deterministic router:

   ```bash
   python skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py \
     --request "<natural-language outcome>" --json
   ```

5. Accept a route only when its matched terms, action ids, operator note,
   safety label, and declared writes fit the user's request. Present competing
   routes when ambiguity would materially change the result or side effects.
6. Invoke selected workflows only through the router or
   `scripts/mathformer.py`. Use dry runs for inspection and require the user's
   authorization before enabling mutating actions.
7. Carry validated artifacts between workflow stages. Generated suggestions,
   candidates, and critiques remain advisory until the selected workflow's
   deterministic checks or promotion gate accepts them.
8. Report the selected named workflows, their order, completed checks, produced
   artifacts, and any unresolved blockers in plain language.

## Codex Coordination Behavior

- Make reasonable low-risk routing assumptions and state them briefly.
- Ask a focused question only when different plausible routes would produce
  materially different outcomes or mutations.
- Re-resolve the remaining goal after a workflow changes the available state;
  do not blindly replay a stale generated plan.
- Stop a bounded retry or repair loop at its declared gate or cap.
- Never translate a user's broad request into permission for installation,
  publication, external communication, or other unrelated mutation.

## Typical Invocations

- "Set up Mathformer and run the compact validation gate."
- "Extract the theory from this paper, formalize it in Lean, and check it."
- "Find the right workflow for this physics derivation and run only safe
  checks."
- "Explain which Mathformer workflows can handle this goal before running
  anything."

Use `mathformer-workflow-router` directly when the task is only deterministic
route lookup, pipeline help, or route-coverage auditing.
