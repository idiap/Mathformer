---
name: physics-isabelle-derivation-drafter
description: Draft source-aligned Isabelle/HOL physics derivation theories from informal physics sources, type packets, and assumption packets. Use for the `draft.physics_isabelle_derivation` hook, especially when adapting the Lean physics workflow to Isabelle while preserving commentary, typed/contextual physics surfaces, algebraic core lemmas, and honest blocked status for unsupported derivations.
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

# Physics Isabelle Derivation Drafter

Use after the Isabelle physics workflow plan, type-system packet, assumption
packet, source alignment commentary, and equation/law packets are available.
Generated artifacts live under `artifacts/physics_isabelle/` or `backends/isabelle/Isabelle/`
and must not write to Lean artifact paths.

## Drafting Rules

- Preserve the full informal statement and derivation commentary in a top-level
  Isabelle `text \<open>...\<close>` block.
- Add a formal alignment section that maps source equations, assumptions, unit
  notes, and generated-support algebra to the corresponding theorem assumptions,
  core lemma, wrapper theorem, or blocked reason.
- Prefer a compact algebraic core lemma plus a physics-rich wrapper theorem.
  The wrapper may call the core theorem, but must keep source context visible.
- Never assume the final target equation as a theorem assumption for complete
  status. If the script cannot derive the target from earlier source equations,
  emit a blocked scaffold and let the review gates route refinement.
- Keep generated physics surfaces minimal and valid Isabelle/HOL. Put richer
  physical typing details in commentary and packets unless executable theory
  support is ready.

## Script

Use the deterministic drafter first:

```bash
python3 skills/physics-isabelle/physics-isabelle-derivation-drafter/scripts/draft_physics_isabelle_derivation.py \
  --source-file artifacts/physics_source/formalphysics_0000/source.txt \
  --type-packet artifacts/physics_isabelle/formalphysics_0000/type_system_packet.json \
  --assumption-packet artifacts/physics_isabelle/formalphysics_0000/assumption_packet.json \
  --case-id formalphysics_0000 \
  --output-file artifacts/physics_isabelle/formalphysics_0000/MathformerPhysics.thy \
  --report-file artifacts/physics_isabelle/formalphysics_0000/physics_isabelle_draft_report.json
```

If the report status is `blocked`, keep the scaffold as evidence and route the
case through localized refinement before execution is treated as final.
