<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

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

# Source Provenance

Reference repository:
- URL: `https://github.com/lanzhang128/multi_agent_autoformalization`
- Commit: `bdd8e17b5324f5c159de257425da5760975cf552`

Prompt-bearing source files mirrored into `scripts/agentc.py`:
- `agent/autoformalization.py`
- `agent/formal_refinement.py`
- `agent/informal_refinement.py`
- `agent/soft_critique.py`
- `agent/denoising.py`
- `agent/agent_utils.py`

Orchestration behavior mirrored from:
- `evaluation_experiments/isr_gpt.py`

Non-prompt utility abstractions included for parity:
- `agent/abstract.py`
- `llm/abstract.py`
- `agent/hard_critique.py` (with optional external checker fallback)
- `agent/import_retrieval.py` (dependency-injected retriever/KB)
