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

# Mathlib Abstraction Checklist

Use this checklist when refining Lean autoformalizations toward maximum mathlib alignment.

## Core Object Alignment

- Prefer existing mathlib notions over local duplicates.
- Reuse native predicates/types where available, for example Gaussian/probability APIs.
- Avoid introducing custom parallel interfaces for concepts already represented in mathlib.

## Abstraction Boundary Discipline

- Isolate only the truly missing analytic or constructional component.
- Use one clearly named abstract boundary field or predicate.
- Avoid multiple overlapping abstract routes for the same semantic property.

## Theorem Layer Shape

- Keep theorem-level equivalences behind explicit assumption packages when content is not proved.
- Do not postulate unconstrained axioms that force target conclusions.
- Ensure assumptions are strong enough for intended downstream lemmas.

## API Operability

- Add operational lemmas that turn interface assumptions into immediately usable results.
- Remove or connect floating interface propositions.

## Lean Engineering Hygiene

- Keep declaration-level doc comments (`/-- ... -/`) above each key declaration.
- Minimize broad imports when practical.
- Track and reduce `axiom` and `sorry` placeholders.
- Final artifacts with placeholders or scaffold-only claims must fail `autoformalization-result-realness-verifier`; record them as draft/blocked until repaired.
- Keep compatibility checks reproducible with `lake env lean`.

## Typical Red Flags

- Custom predicates duplicating native mathlib predicates.
- Pairing `Measure` with separate probability assertions where `ProbabilityMeasure` is better.
- Theorems stated as global equivalences over unconstrained predicates.
- Abstract field names implying concrete constructions when only properties are given.
- Modules made mostly of thin wrappers around existing declarations without source-specific bridge content.
