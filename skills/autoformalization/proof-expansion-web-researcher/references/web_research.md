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

# Proof Expansion Web Research

## Query Strategy

- Search exact theorem names first.
- Add key hypotheses and domain terms when names are ambiguous.
- Search definitions separately from proof techniques.
- Prefer source queries such as `site:arxiv.org`, publisher pages, official docs, or theorem/library documentation when available.
- Stop once the needed statement, assumptions, and expansion-relevant definitions are verified.

## Packet Format

For each researched segment:

- `segment_index`
- `question`
- `sources`: URL, source type, and date accessed if useful
- `verified_statement_or_definition`
- `hypotheses_to_preserve`
- `expansion_notes`
- `uncertainties`

## Guardrails

- Do not over-expand beyond what the original proof uses.
- Do not import unsupported assumptions from a nearby but different theorem.
- Mark uncertain facts explicitly instead of smoothing them into the expansion.
