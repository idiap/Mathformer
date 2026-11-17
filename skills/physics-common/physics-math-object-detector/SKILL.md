---
name: physics-math-object-detector
description: Detect the concrete physics mathematical objects that must be recovered before repairing Lean physics drift pathologies, including quantum states, operators, commutators, vector fields, coordinate frames, calculus bridges, physical laws, dimensions, units, and implicit premises.
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

# Physics Math Object Detector

Use immediately after `physics-lean-drift-pathology-monitor` reports a warning
or failure. This skill identifies which physics-bearing object must be worked
on before the target Lean theorem is edited.

## Contract

Emit a `physics_math_object_detection_packet` containing object candidates such
as:

- `quantum_state`
- `quantum_operator`
- `commutator`
- `hilbert_space_inner_product`
- `vector_field`
- `coordinate_frame`
- `basis_projection`
- `gradient_divergence_curl`
- `integral_or_limit`
- `dimensioned_quantity`
- `unit_bridge`
- `physical_law`
- `boundary_or_regime_assumption`

Each object candidate must include source cues, Lean cues, required
Mathlib/MathformerPhysicsLib surfaces, repair surfaces, and blocked-until gates.

Prefer `scripts/detect_physics_math_objects.py` for deterministic first-pass
object detection.
