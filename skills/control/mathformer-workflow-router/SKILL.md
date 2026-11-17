---
name: mathformer-workflow-router
description: Deterministically resolve natural-language Mathformer requests to controlled workflow actions and audit route coverage. Use for route lookup, pipeline help, dry runs, and coverage checks; use the generative coordinator when Codex must interpret or compose several workflows.
---


# Mathformer Workflow Router

Use this as the deterministic routing layer for a Mathformer outcome expressed
in ordinary language. When Codex must interpret an ambiguous outcome, decompose
it, or compose several workflows, start with
`mathformer-generative-workflow-coordinator` and use this router to validate
each selected intent.

## Router Contract

Route through `scripts/mathformer.py ask` or the bundled
`scripts/route_mathformer_workflow.py`. Do not call lower-level scripts directly
until the hub has selected a controlled action.

Always preserve the hub safety model:

- use `--dry-run` when inspecting a mutating route;
- use `--allow-mutating` only when the user asked to publish, install, generate,
  or otherwise mutate repository/environment state;
- treat Codex-exec and other generative outputs as advisory until deterministic
  checks, promotion gates, or workflow-specific validators pass.

## Quick Commands

List the whole routed pipeline:

```bash
python skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py \
  --help-pipeline --json
```

Resolve a request:

```bash
python skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py \
  --request "autoformalize physics foundations with mathlib first grounding" \
  --json
```

Run the selected controlled workflow:

```bash
python skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py \
  --request "run the compact quality gate before commit" \
  --run --dry-run --json
```

Audit natural-language coverage:

```bash
python skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py \
  --audit-coverage --json
```

## Generative Or Codex-Exec Use

When a generative agent or `codex exec` job is using this skill, keep the
generative part at the intent-selection layer:

1. Paraphrase the user request into one or more candidate Mathformer intents.
2. Resolve each candidate with the router script or `scripts/mathformer.py ask`.
3. Prefer the highest-scoring route only when its `matched_terms`, `action_ids`,
   and `operator_note` support the request.
4. If the route is ambiguous, return the top routes and ask for a narrower
   outcome rather than fabricating a workflow.
5. If the route is selected, execute only through the hub with the appropriate
   safety flags.

For content-generative workflows, such as physics repair prompts or skill
content probes, the router may select the Codex-exec planning action. The
generated proposal is never final support by itself.

## Coverage Rule

Every registered workflow family in `scripts/mathformer.py list --json` must be
reachable from at least one `IntentRoute` returned by `scripts/mathformer.py ask`.
The coverage audit fails when a family has no natural-language route, when a
route points to an unknown action, or when a route lacks a runnable action id.

## Help Function

Use `--help-pipeline` when an agent or user needs orientation before choosing a
workflow. The help payload lists each routed workflow, its controlled action ids,
skill routes, examples, safety labels, and grouped workflow families.

## Portable operation discovery

Resolve the reviewed pilot contracts without execution through
`python3 scripts/mathformer.py run adoption:describe --json -- router:resolve`.
The `adoption:invoke` route offers an explicit recorded invocation; it does not
change ordinary `ask` results or execute a route selected by `router:resolve`.
See `docs/migrations/portable-repository-adoption/usage.md`.
