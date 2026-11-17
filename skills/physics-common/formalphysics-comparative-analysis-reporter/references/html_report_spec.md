<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Self-Contained HTML Report Spec

## Output Contract

Produce one portable HTML file with embedded CSS, embedded JavaScript, and no
external CDN dependencies. Pair it with the machine-readable JSON report.

## Tabs

- `Overview`: scope, dataset, compared systems, non-gold reference policy,
  hard-gate summary, and best-solution headline.
- `Leaderboard`: case-grouped coverage table, with current Mathformer and
  external Lean candidates shown side by side. It must expose hard gates, mean
  score, invoked concept excerpt counts, source/derivation/physics/depth/
  Mathlib/Foundation/reviewability coverage bars, and compact deltas.
- `Case Details`: per-case question, reference answer excerpt, candidate
  summaries, judge evidence, and recommended repair.
- `Lean Side By Side`: synchronized panes for current Mathformer Lean and
  external Lean code, with colored Lean token rendering.
- `Invoked Concepts`: per-case excerpts for every detected invoked external
  Foundation declaration, including file path, line span, kind, name, and
  invocation count.
- `Foundations`: dependency inventory for
  `libraries/MathformerPhysicsLib/Lean/Foundations.lean` and
  `libraries/MathformerPhysicsLib/Lean/Foundations/*.lean`, plus candidate concept usage
  and duplication findings.
- `Judge Evidence`: deterministic and generative judge JSON rendered as
  expandable cards.
- `Role Reviews`: independent theorem-prover-expert and physics-expert reports
  with rubric criteria, essential features, strategy tags, strengths, concerns,
  and per-case preferences.
- `Strategy Summary`: cross-role comparison that highlights agreements,
  disagreements, recurring strategies, and per-case contrasts.
- `Methodology`: metrics, judge policy, non-gold reference policy, and known
  limitations. This tab must show metric criteria and critic profiles for
  Mathlib grounding, naming/reviewability, formality depth, and physics
  representation completeness.

## Lean Rendering

Use a lightweight embedded lexer that highlights:

- comments,
- strings,
- keywords such as `theorem`, `def`, `structure`, `class`, `instance`,
  `namespace`, `by`, `have`, `calc`, `simp`, `rw`, `ring`, `linarith`,
- declarations,
- tactics,
- numerals and symbols,
- suspicious tokens: `sorry`, `admit`, and `axiom`.

Do not require network-hosted highlight libraries. Keep line numbers, wrapping,
and optional synchronized scrolling.

## Visual Design

- quiet research-dashboard style;
- strong contrast for hard gates;
- compact evidence cards;
- consistent colors for candidate systems;
- badges for `passes`, `warn`, `blocked`, `reference_only`, and
  `not_gold_reference`.

## Machine Processing

Embed a `<script type="application/json" id="comparison-data">` block with the
same report payload used to render the page. The consumer application should be
able to read this block or the sibling JSON report through MCP or local file IO.
