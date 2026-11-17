<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Architecture

Understand components, data flow, contracts, and extension points. This section is for readers learning or using Mathformer.

```text
source → extraction and premise grounding → backend candidate
       → execution → critique and repair → accepted artifact or explicit blocker
```

Canonical skills live in `skills/`; controlled entrypoints in `scripts/`; backend
implementations in `backends/`; reusable results in `libraries/`; run outputs in
`artifacts/`. The natural-language coordinator routes goals through the deterministic
hub rather than granting generated text acceptance authority.

The [framework guide](FRAMEWORK.md) explains components and
[principles](PRINCIPLES.md) define acceptance boundaries.

## Read next

- [Framework](../architecture/FRAMEWORK.md) — Components, control flow, and backend-specific details.
- [AgenticHub](../architecture/AGENTIC_HUB.md) — Controlled operational entrypoints.
- [Reasoning-flow language](../architecture/REASONING_FLOW_LANGUAGE.md) — Typed epistemic composition.
- [Knowledge resources](../architecture/KNOWLEDGE_RESOURCES_IN_REASONING_FLOWS.md) — KB access and persistence semantics.
- [MCP server](../architecture/MCP_SERVER.md) — Service integration boundaries.

Return to the [documentation index](../README.md) or consult the
[documentation map](../reference/documentation-map.md) for the complete retained collections.
