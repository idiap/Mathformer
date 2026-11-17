<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Keep the FormalScience/FormalPhysics drift taxonomy explicit inside the
  Mathformer skill layer.

Intent:
  Preserve the paper-derived pathology categories as local monitoring criteria
  for Lean physics autoformalization.

Function:
  Defines the category meanings, evidence cues, and refinement routes consumed
  by the drift-pathology monitor skill.

Maintenance Notes:
  Update this reference when the paper taxonomy or Mathformer physics gates
  change.
-->

# FormalScience Semantic Drift Taxonomy

This reference summarizes the drift taxonomy from
the locally supplied paper `2026.acl-long.1057.pdf`, section 5 and table 8, for
local Mathformer use. The paper names four alignment-drift classes:

- `notational_collapse`: domain-specific physics notation collapses to simpler
  mathematical objects. Examples include Dirac/braket quantum states, operators,
  commutators, or field/vector surfaces becoming raw scalars.
- `abstraction_elevation`: concrete symbolic operations are replaced by abstract
  properties or hypotheses. Examples include vector calculus, definite
  integrals, divergence theorem steps, or potential-energy line integrals being
  hidden behind algebraic hypotheses.
- `proof_strategy_substitution`: Lean proves the target with a different proof
  strategy than the informal derivation while preserving the target objects and
  conclusion.
- `implicit_premise_selection`: Lean exposes premises that physicists often
  leave implicit, such as positivity, nonzero denominators, differentiability,
  boundary conditions, or domain restrictions.

## Severity Policy

- `notational_collapse` is critical when the source contains quantum, operator,
  vector, tensor, field, coordinate, or dimensional structure and Lean only
  exposes raw scalar or unrelated algebraic surfaces.
- `abstraction_elevation` is critical when the physical calculation is moved
  into assumptions and the proof reduces to substitution, simplification, or a
  generic algebra lemma.
- `proof_strategy_substitution` is a warning when the target is preserved and a
  blocker only when the substituted proof avoids a required source law,
  transformation, or physical object.
- `implicit_premise_selection` is beneficial evidence when the new premise is
  labeled source-backed, mathlib-backed, or generated-support. It is a warning
  or error when assumptions are hidden, stronger than the source, or unlabeled.

## Repair Surfaces

- `quantity_typing`: restore physics-bearing type, vector, operator, field, or
  Hilbert-space surfaces.
- `unit_dimension_obligation`: add dimension, unit, or projection obligations.
- `law_grounding`: replace target-shaped or calculation-shaped assumptions with
  source-backed laws and support lemmas.
- `frame_regime`: restore coordinate, frame, basis, gauge, boundary, regime, or
  approximation context.
- `projection_bridge`: prove scalar projections preserve the source vector or
  operator claim.
- `support_dependency`: formalize the missing integral, derivative, calculus,
  operator, or algebraic bridge used by the source derivation.
- `contextual_assumption`: label implicit premises and reject hidden
  strengthening.
