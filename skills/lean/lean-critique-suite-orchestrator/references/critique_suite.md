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

# Lean Critique Suite

## Expected Report Shape

```json
{
  "suite_judgement": "pass|fail|pass_with_warnings",
  "passes": [
    {
      "id": "syntax",
      "skill": "lean-syntactic-correctness-critic",
      "judgement": "True|False",
      "blocking": true,
      "evidence": []
    },
    {
      "id": "semantic_preservation",
      "skill": "lean-semantic-preservation-critic",
      "judgement": "True|False",
      "blocking": true,
      "evidence": []
    },
    {
      "id": "logical_soundness",
      "skill": "lean-logical-soundness-critic",
      "judgement": "True|False",
      "blocking": true,
      "evidence": []
    },
    {
      "id": "mathlib_alignment",
      "skill": "lean-mathlib-alignment-critic",
      "judgement": "True|False|Warning",
      "blocking": false,
      "evidence": []
    },
    {
      "id": "result_realness",
      "skill": "autoformalization-result-realness-verifier",
      "judgement": "True|False",
      "blocking": true,
      "evidence": []
    },
    {
      "id": "reference_free_monitor",
      "skill": "reference-free-critic-monitor",
      "judgement": "pass|warn|fail",
      "blocking": true,
      "evidence": []
    }
  ],
  "required_refinement": [],
  "waivers": []
}
```

## Hook Mapping

- `critique.syntax`: `lean-syntactic-correctness-critic`
- `critique.semantic_preservation`: `lean-semantic-preservation-critic`
- `critique.logical_soundness`: `lean-logical-soundness-critic`
- `critique.mathlib_alignment`: `lean-mathlib-alignment-critic`
- `artifact.realness_gate`: `autoformalization-result-realness-verifier`
- `critique.reference_free_monitor`: `reference-free-critic-monitor`
- `critique.suite`: `lean-critique-suite-orchestrator`

## Handoff Rules

- Syntax failures include raw Lean diagnostics for `lean-formal-refinement`.
- Semantic failures include source/Lean mismatch pairs.
- Logical failures include the exact theorem/axiom/interface that makes the artifact vacuous or unsound.
- Mathlib alignment failures include candidate declarations/imports or auditor findings when available.
- Realness failures include the exact path/line/report field containing mocks, placeholders, unexecuted states, or scaffold-only final claims.
- Reference-free monitor failures include the regressed score, increased risk count, or theorem/source-anchor shrinkage that blocks monotonic prompt or skill acceptance.
