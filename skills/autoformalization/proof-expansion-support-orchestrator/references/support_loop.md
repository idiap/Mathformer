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

# Proof Expansion Support Loop

## Hook Order

1. `preformalization.expansion_support`
2. `preformalization.expansion_difficulty`
3. `preformalization.expansion_web_support` for flagged segments
4. `preformalization.expand`
5. `preformalization.review.suite`

## Handoff Packet

The packet should include:

- `difficulty_report`
- `web_research_packets`
- `safe_to_expand_without_search`
- `segments_requiring_human_or_web_followup`
- `expansion_constraints`

## Decision Rule

If a flagged segment lacks verified source support, do not silently expand it as if it
were known. Preserve an explicit uncertainty for the expander and later reviewers.
