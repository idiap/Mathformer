---
name: mathformerphysicslib-mathlib-grounding-auditor
description: Audit whether MathformerPhysicsLib concepts reuse Mathlib surfaces before introducing local physics support definitions.
---


# MathformerPhysicsLib Mathlib Grounding Auditor

Use this skill whenever a MathformerPhysicsLib concept might be definable by
Mathlib objects, or when a candidate definition needs a grounding check.

## Workflow

1. Run `scripts/audit_mathlib_grounding.py` on the concept graph.
2. Record grounded, partial, and missing concepts separately.
3. Block promotion when a Mathlib-grounded concept is redefined locally without
   provenance.

## Outputs

- `mathformerphysicslib_mathlib_grounding_audit`
- concept-level grounding status
- desirable properties checked by the grounding critic
