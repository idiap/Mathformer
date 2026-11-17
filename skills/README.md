<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Skills

Canonical executable skills are physically nested by theme, for example
`skills/lean/lean-execution-runner/SKILL.md`. Workflow contracts, the test
matrix, documentation, and agent-client publishing all resolve these nested
canonical paths. Theme folders are organizational containers and do not contain
their own `SKILL.md`; agent clients still publish a flat set of unique skill
names. Thematic metadata also remains available in `skills/SKILL_HOOKS.yaml`,
`meta_skills/taxonomy/workflow_taxonomy.json`, quality cards, workflow
registries, and this README.

Codex and Claude Code can also discover these skills through the
[Mathformer plugin](../plugins/README.md). Its generated flat entrypoints load
the canonical instructions from a runtime checkout. After updating skill
discovery metadata, run `python scripts/sync_agent_plugins.py` and commit the
generated plugin files with the source changes.

`skills/REASONING_TYPES.yaml` adds a complementary epistemic axis: it maps
backend-independent reasoning primitives to representative skill compositions
and contains primary/secondary bindings for every canonical skill. Its
primitives should not be confused with the operational workflow-family labels
named `reasoning_types` in `workflow_taxonomy.json`.

`skills/OUTPUT_TYPES.yaml` classifies the epistemic kinds of outputs produced by
those reasoning operations and keeps output kind separate from container role,
file format, backend, lifecycle state, and trust state.

`skills/SKILL_TYPES.yaml` defines the orthogonal execution-posture,
specification-style, composition, implementation, state, effect, authority, and
testing axes used to classify the skills themselves.

`skills/control/reasoning-flow-language/` owns ERFL 0.3, which composes those reasoning
operations through typed, relation-labelled epistemic handles. Its validated
profiles live in `examples/reasoning_flows/`; they are conceptual projections,
not substitutes for hook execution or evidence logs. The generated
`docs/architecture/ALL_REASONING_FLOWS.md` reference explains every profile and
keeps its semantics independent of implementation. The generated
`docs/architecture/REASONING_FLOW_MATERIALIZATIONS.md` cross-references
candidate skill bindings and controlled operational loop contracts separately.

Current themes:

- `atp`: Vampire and proof-informalization workflows.
- `autoformalization`: source extraction, proof expansion, result checks, and
  cross-backend review surfaces.
- `benchmarks`: benchmark-specific runners.
- `control`: generative natural-language workflow coordination, deterministic
  routing, hooks, gates, reasoning logs, reasoning flows, inventory, and
  workflow validation. Start with
  `mathformer-generative-workflow-coordinator` when the desired outcome spans
  workflows or their exact names are unknown.
- `isabelle`: Isabelle and IsarMathLib workflows.
- `latex-textbook`: LaTeX and textbook expansion workflows.
- `lean`: Lean execution, refinement, critique, and consistency workflows.
- `mathformerlib`: MathformerLib registry, promotion, accumulation, and docs.
- `mathformerphysicslib`: MathformerPhysicsLib coherence, grounding, and
  foundations workflows.
- `mathlib`: Mathlib lookup, grounding, compatibility, import, and abstraction
  workflows.
- `paper`: paper theory extraction and localization workflows.
- `physics-common`: backend-neutral physics parsing, grounding, assumptions, and
  derivation planning.
- `physics-isabelle`: physics-to-Isabelle workflows.
- `physics-lean`: physics-to-Lean workflows and recursive repair loops.
- `physics-sympy`: physics-to-SymPy workflows.
- `premise-kb`: premise knowledge-base indexing and seed generation.
- `rfde`: reference-free critique and descriptive evaluation.
- `rocq`: Rocq drafting and execution workflows.
- `sympy`: general SymPy autoformalization, execution, and validation.
