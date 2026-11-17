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

# Informalization Consistency Policy

This verifier uses the final Lean file as the primary artifact and checks
whether the reverse informalization is coherent with the claimed source
alignment.

Blocking conditions:

- the extractor cannot produce a packet for a theorem-like declaration;
- a theorem-like declaration lacks a source-aware or generated-note doc comment;
- a proof contains `sorry`, `admit`, unresolved `exact?`, or a target `axiom`;
- the realness gate reports high-severity findings;
- optional Lean checks fail;
- a doc comment claims an equivalence (`iff`, `\iff`, `↔`) but the Lean
  signature has no equivalence shape;
- a doc comment claims existence but the Lean statement has no existential or
  explicit witness/result shape.

Advisory conditions:

- proof closes by exact use of a hypothesis;
- source/proof token overlap is low;
- theorem is very thin but honestly documented as a criterion, interface, or
  external-boundary assumption.

The verifier should not turn advisory findings into blockers when the artifact
openly represents an external result as a hypothesis or model field. Honesty of
the boundary is preferable to hiding it in a vacuous proof.
