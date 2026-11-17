---
name: physics-law-concept-grounding-navigator
description: Ground physical laws and mathematical operations in physics SymPy derivations to explicit computable templates and installed SymPy APIs.
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

# Physics Law Concept Grounding Navigator

Use before drafting. It distinguishes physical-law grounding from algebraic API
grounding and records the law/API used for every transformation-critical step.

## Contract

Build a law/API grounding packet for one physics derivation case. The packet
must keep physical-law support separate from mathematical operation support.

Physical laws and constitutive relations are grounded to computable templates
when they match the catalog. Case-specific source laws that do not match the
catalog are preserved as source-backed local templates. Generated law
applications must remain marked as generated support.

The law template catalog covers:

- Newton's second law
- Hooke's law
- work-energy relation
- conservation of mechanical energy
- Ohm's law
- capacitor relation
- ideal gas law
- first-law thermodynamic sign convention

The SymPy operation catalog covers:

- `solve` and `solveset`
- `dsolve`
- `integrate` and `Integral`
- `diff` and `Derivative`
- `simplify`, `expand`, `factor`, and `cancel`
- `subs`
- vector dot/cross support
- unit conversion and dimension simplification

## Output

The default report is written to:

```text
artifacts/physics_sympy/<case_id>/law_api_grounding_packet.json
```

Completion is blocked when a law use lacks source-backed or generated-support
provenance, or when a mathematical operation has no grounded API.

## Validation

Use the Phase 8 regression check:

```bash
python tests/physics_sympy/run_phase8_law_api_grounding.py --json
```

The skill entrypoint is:

```bash
python skills/physics-common/physics-law-concept-grounding-navigator/scripts/ground_physics_laws.py --case-id rc_discharge --json
```
