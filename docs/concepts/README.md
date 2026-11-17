<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Concepts

Understand the project model, terminology, and evidence boundaries. This section is for readers learning or using Mathformer.

Mathformer turns mathematical and physical language into inspectable formal and
symbolic artifacts. It connects natural-language goals to controlled workflows for
autoformalization, premise retrieval, proof search, execution, critique, and refinement.
Its backends include Lean/mathlib, Vampire ATP with TPTP/TSTP, SymPy, Rocq, and Isabelle
surfaces; their available checks and maturity differ.

- **Source-grounded formalization:** retain the original statement, assumptions, and source anchors through each transformation.
- **Controlled refinement:** draft, execute, criticize, and repair within declared workflow and hook contracts.
- **Backend-specific evidence:** a Lean compilation, ATP proof, SymPy check, and structural validation establish different things.
- **Reference-free evaluation:** assess grounding, non-vacuity, executable evidence, and artifact substance when no gold formalization exists.
- **Governed reuse:** keep theorem-memory candidates separate from accepted library results.

## Read next

- [Main concepts](../architecture/MAIN_CONCEPTS.md) — Source objects, skills, gates, memory, and evidence.
- [Principles](../architecture/PRINCIPLES.md) — Proposal and acceptance authority.
- [Reasoning types](../architecture/EPISTEMIC_REASONING_TYPES.md) — Epistemic operations independent of backends.
- [Output types](../architecture/OUTPUT_TYPES.md) — Claims, evidence, assessments, and representations.
- [Skill types](../architecture/SKILL_TYPES.md) — Deterministic, generative, and hybrid roles.

Return to the [documentation index](../README.md) or consult the
[documentation map](../reference/documentation-map.md) for the complete retained collections.
