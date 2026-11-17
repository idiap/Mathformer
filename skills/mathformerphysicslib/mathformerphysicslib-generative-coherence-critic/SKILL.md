---
name: mathformerphysicslib-generative-coherence-critic
description: Build generative probes that stress-test MathformerPhysicsLib coherence, Mathlib grounding, and controlled repair paths.
---


# MathformerPhysicsLib Generative Coherence Critic

Use this skill when deterministic critics have run and the system needs
generative interpretation probes that try to expose hidden incoherence without
turning advisory output into accepted evidence.

## Workflow

1. Run `scripts/build_generative_coherence_critic_plan.py`.
2. Inspect the seven generated probe records:
   Mathlib maximality, redefinition/spread, integration/discoverability,
   physics semantic erasure, API usefulness, negative control, and meta-critic.
3. Execute Codex-exec or another generative reviewer only against the emitted
   probe prompts and expected schemas.
4. Treat results as advisory unless every blocking finding cites deterministic
   report evidence and names a rerun gate.
5. Feed evidence-bound failures into the coherence repair planner.

## Outputs

- `mathformerphysicslib_generative_coherence_critic_plan`
- adversarial and constructive probes
- expected probe report schemas
- pass criteria for controlled generative repair
- deterministic evidence bindings and rerun gates
