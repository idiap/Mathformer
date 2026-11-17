<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Preserve generated and reviewed formal-physics artifacts with enough context to audit their provenance.

Intent:
  Connect benchmark statements to Lean, Isabelle, and SymPy representations without hiding assumptions.

Function:
  Stores formal artifacts, summaries, and grounding reports consumed by physics backend tests and documentation.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Mathlib Grounding Audit

Conclusion: all current Lean physics library entries are high-grounded complete candidates. A Lean physics artifact may remain complete only when the theorem surface is Mathlib-native and the consistency report carries physics-final-review grounding evidence.

| Case | Level | Complete allowed | Main gap |
|---|---:|---:|---|
| `formalphysics_0000` | high | yes | residual unit/dimension bridges remain shallow but theorem surface is Mathlib-native |
| `formalphysics_0020` | high | yes | residual unit/dimension bridges remain shallow but theorem surface is Mathlib-native |
| `formalphysics_0026` | high | yes | residual unit/dimension bridges remain shallow but theorem surface is Mathlib-native |
| `formalphysics_0054` | high | yes | residual unit/dimension bridges remain shallow but theorem surface is Mathlib-native |
| `formalphysics_0059` | high | yes | residual unit/dimension bridges remain shallow but theorem surface is Mathlib-native |
| `formalphysics_0066` | high | yes | residual unit/dimension bridges remain shallow but theorem surface is Mathlib-native |
| `formalphysics_0119` | high | yes | residual unit/dimension bridges remain shallow but theorem surface is Mathlib-native |
| `formalphysics_0172` | high | yes | residual unit/dimension bridges remain shallow but theorem surface is Mathlib-native |
| `formalphysics_0176` | high | yes | residual unit/dimension bridges remain shallow but theorem surface is Mathlib-native |
| `formalphysics_0191` | high | yes | residual unit/dimension bridges remain shallow but theorem surface is Mathlib-native |

## Gate Policy

- `high`: may be reported complete when Lean execution, source anchors, unit checks, background dependencies, critics, and final reviews also pass.
- `medium` or `low`: must remain draft/blocked until a physics final review records high Mathlib grounding or an explicit waiver/blocker is added.
- Missing physics final review or missing background dependency plan blocks complete status even if the Lean file compiles.
