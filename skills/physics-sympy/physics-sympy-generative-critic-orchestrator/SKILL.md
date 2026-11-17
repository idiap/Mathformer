---
name: physics-sympy-generative-critic-orchestrator
description: Plan generative Codex-exec adversarial critiques for high-risk SymPy physics derivations. Use when deterministic SymPy physics critics disagree, a near-final artifact remains high-risk, or target leakage, hidden assumptions, scalar erasure, unit substitution, or invalid domain choices need independent adversarial probing.
---

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

# Physics SymPy Generative Critic Orchestrator

Use this skill only after deterministic reports exist. It plans, and when the
workflow permits, launches independent Codex-exec probes for adversarial
objections against a SymPy physics equation trace.

## Contract

Produce `physics_sympy_generative_critic_plan` and, when executed,
`physics_sympy_generative_critic_report`.

Prefer `scripts/build_physics_sympy_generative_critic_plan.py` for deterministic
probe planning.

## Probe Policy

Generative findings are hypotheses. They block completion only when supported by
source anchors, execution diagnostics, unit reports, deterministic critics, or
repeated independent probes with the same blocker class.

Probe for:

- source physics true or false while the equation trace still passes;
- hidden target assumptions;
- missing side conditions;
- invalid unit substitutions;
- lost frame, vector, field, law, regime, or projection structure.

