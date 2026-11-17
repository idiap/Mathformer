<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Explain the architectural shift from script-facing usage to natural-language
  agent interaction.

Intent:
  Define how humans, VS Code agents, Codex, Claude Code, OpenCode, and local
  adapters should route ordinary-language requests into controlled Mathformer
  workflows.

Function:
  Documents the NL intent layer, its relationship to skills and the workflow
  hub, safety expectations, and examples of user-facing requests.

Maintenance Notes:
  Keep this file synchronized with the AgenticHub implementation, the HowTo,
  the AgenticHub guide, and the skill-hook contract.
-->

# Natural-Language Agent Interface

Use Mathformer by asking for the result you want, not by naming the script that
might produce it. The agent should choose the workflow, run the backend, and
return the artifact paths and validation status.

The interaction is simple:

1. A human asks an agent for an outcome in ordinary language.
2. The agent resolves the request to a Mathformer intent.
3. The agent uses the relevant skill and controlled workflow.
4. The agent explains the result in natural language and cites the produced
   artifacts.

## Good Requests

A good request names the mathematical outcome, not the script:

- "Prove the inverse-of-product theorem in group theory with Vampire."
- "Run premise selection near the Fundamental theorem of algebra."
- "Check whether the Lean formalization compiles."
- "Generate and validate Rocq proof-script candidates."
- "Verify the RC discharge derivation with assumptions and units."

The agent may call repository commands internally. That is the implementation
layer, not the user-facing contract.

## What The Agent Should Return

Every successful response should make four things visible:

1. the mathematical claim or derivation attempted;
2. the backend or KB workflow used;
3. the artifact that carries the evidence;
4. the validation status: checked, candidate, blocked, or failed.

If a backend is missing, the agent should say which one and offer the strongest
available local check.

## Relationship To Skills And The Hub

Skills are the reusable agent workflows. They describe what context to read,
what invariants to preserve, and which deterministic tools own the mechanical
part of a task.

AgenticHub is the lower-level control surface behind those skills. Use
the [AgenticHub guide](../architecture/AGENTIC_HUB.md) only when you need exact action names,
dry-runs, or CI-style reports.

## Router Entrypoint

The repository-owned router skill is
[`mathformer-workflow-router`](../../skills/control/mathformer-workflow-router/SKILL.md).
Codex, Claude Code, OpenCode, and Codex-exec/generative jobs should use it as
the top-level entrypoint when a request needs natural-language workflow
selection.

Resolve a request without running it:

```bash
python skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py \
  --request "run the compact quality gate before commit" --json
```

Audit that every registered workflow family is reachable from natural language:

```bash
python skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py \
  --audit-coverage --json
```

The same audit is available through the canonical hub:

```bash
python scripts/mathformer.py ask \
  "check that the router entrypoint covers all distinct workflows using natural language commands" \
  --run --json
```

## Safety Model

Natural language does not grant extra permission. After intent resolution, the
same workflow safety labels apply:

- read-only workflows can inspect state;
- artifact workflows can write generated outputs;
- environment workflows can update local environment state only with explicit
  permission;
- repository-writing workflows can update tracked files only when the user asks
  for that kind of change.

Agents should explain these effects before running mutating actions. If an
intent route is ambiguous, the agent should ask a short clarification or offer
the closest safe check.

## VS Code Pattern

In VS Code, the comfortable loop is:

1. Open the repository.
2. Ask the agent for the mathematical outcome.
3. Let the agent resolve the NL request to a skill and controlled workflow.
4. Review generated artifacts in the editor.
5. Ask the agent to run the relevant validation check.

Example:

> Prove that the inverse of a product in a group reverses order, using the
> premise KB if helpful, and show me the proof artifact.

The agent should route this to the Vampire ATP skill, use the controlled ATP
workflow internally, and return a short explanation plus artifact paths. It
should not require the user to name the underlying runner first.
