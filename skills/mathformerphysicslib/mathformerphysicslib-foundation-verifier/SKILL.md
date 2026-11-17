---
name: mathformerphysicslib-foundation-verifier
description: Verify MathformerPhysicsLib Lean foundation candidates for realness, non-vacuity, Mathlib grounding comments, import policy, semantic scaffolding risks, and promotion readiness.
---

# MathformerPhysicsLib Foundation Verifier

Use after `mathformerphysicslib-foundation-drafter`, and before registry or
promotion claims. This skill verifies both the structural shape of foundation
modules and the accepted Lean index import path.

Prefer `scripts/verify_foundation_modules.py`.

## Contract

- Reject `sorry`, `admit`, generated axioms, and scaffold-only `Prop := True`.
- Require Mathlib grounding comments in accepted modules.
- Report broad `import Mathlib` as justified, warning, or blocking.
- Compile `MathformerPhysicsLib.Lean.Foundations` unless
  `--skip-index-compile` is explicitly supplied.
- Emit promotion readiness and explicit blockers for each module.
