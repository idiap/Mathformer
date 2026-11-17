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

# Aggressive Skill Test Program

## Scope

The program covers every local skill under `skills/*/*/SKILL.md`.

Skill test profiles:

- `deterministic`: scripts, validators, Lean checks, hook contracts, JSON
  schemas, suite runners, and benchmark utilities.
- `generative`: prompt-owned skills whose behavior is judged by content quality,
  mathematical fidelity, critique usefulness, or planning discipline.
- `hybrid`: skills with deterministic scripts plus generative orchestration or
  content-facing behavior.

## Deterministic Matrix

Required gates:

- Python compile all skill scripts and test runners.
- Parse `skills/SKILL_HOOKS.yaml`.
- Run strict workflow-contract validation.
- Run strict reasoning-log validation for suite and reflection logs when present.
- Run gate-policy smoke tests.
- Run import-management smoke tests for planned imports, broad-import detection,
  and duplicate import minimization.
- Run `lake env lean tests/lean/WikiLevelGold.lean`.
- Run `tests/wiki_level/run_suite.py` for controlled regression.
- Run reflective observer against the current suite report.

Aggressive mode also adds:

- `--help` smoke for every executable script.
- Codex-exec dry-run planning for every generative or hybrid skill.
- Failure-to-TODO conversion.

## Generative Matrix

Generative probes must use `codex exec`. A probe passes only when the saved final
message satisfies its oracle:

- names the target skill,
- addresses the concrete adversarial scenario,
- includes required terms,
- avoids forbidden overclaiming,
- returns the requested structured shape.

Probe families:

- LaTeX expansion and review: missing assumptions, dangling binders, quantifier
  drift, notation ambiguity.
- Lean drafting and refinement: source-to-Lean preservation, no `sorry`, no
  vacuous theorem weakening, mathlib-native declarations preferred.
- Critique skills: syntactic correctness, semantic preservation, logical
  soundness, and mathlib alignment with explicit pass/fail evidence.
- Mathlib planning: verified declarations are preferred; unresolved gaps are
  isolated.
- Orchestration/control skills: hook order, gate policy, non-regression, and
  reasoning-log evidence.
- Annotation/taxonomy skills: stable line references and allowed labels.

## Codex Exec Protocol

Each content probe writes:

- prompt file,
- Codex stdout/stderr,
- final message from `--output-last-message`,
- oracle result,
- pass/fail status.

Use read-only sandboxing by default. The content test runner must not let a
probe edit repository files.
After editing only probe oracles, use `--reuse-existing` to re-score saved final
messages without rerunning Codex. Do not use reused results as evidence that a
new or changed prompt was freshly executed.

## Failure Conversion

Every failure becomes one of:

- deterministic regression command,
- reusable Codex-exec content probe,
- skill prompt TODO,
- fixture/suite expansion TODO,
- explicit waived risk with owner and expiry.

## Exit Criteria

The program is considered green only when:

- deterministic report has zero blocking failures,
- every generative or hybrid skill has at least one content probe planned,
- required content smoke probes pass,
- generated TODOs have no unexplained item,
- monotonic baseline cases remain passing.
