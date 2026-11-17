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

# Informalized Proof Internal Consistency Policy

This gate evaluates the reverse-informalized proof packet against itself. It is
not a source-preservation check and not a Lean compiler check.

Blocking conditions:

- theorem-like declaration has no informal statement;
- theorem-like declaration has no proof summary;
- proof features include unresolved placeholders;
- declaration is an axiom in a final proof packet;
- extracted dependencies include the declaration itself;
- proof body is absent for a theorem-like declaration that is not an explicit
  axiom marker already blocked elsewhere.

Advisory conditions:

- an equivalence statement has no bidirectional proof evidence such as
  `constructor`, `cases`, or exact use of an explicit equivalence hypothesis;
- an existential statement has no witness/dependency evidence;
- proof is delegated to a hypothesis that is not visible in the signature or
  described as an explicit boundary;
- proof summary is generic and gives no useful proof-shape information;
- statement and proof summary have very low vocabulary overlap and no explicit
  dependency handoff.

The gate should prefer honest warnings to false blockers. A proof can be
internally coherent when it delegates to a named hypothesis, model component, or
external criterion, provided that delegation is visible in the packet.
