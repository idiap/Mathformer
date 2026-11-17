---
name: physics-derivation-consistency-report-orchestrator
description: Aggregate physics SymPy derivation packets into a reference-free consistency report with source, quantity, unit, law-grounding, gap-closure, step-execution, numeric, and artifact-realness metrics.
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

# Physics Derivation Consistency Report Orchestrator

Use after all physics SymPy phase reports exist. Complete status requires source
targets represented, all gaps closed, all steps executable, unit consistency,
target derivation success, numeric sanity, and no critical blockers.

## Contract

The orchestrator produces a Phase 13 reference-free consistency report. It
aggregates the source extraction packet, symbol table, dimension packet, unit
system packet, assumption/regime packet, frame/context packet, equation parse
packet, gap expansion packet, law/API grounding packet, generated artifact,
execution report, unit-analysis report, step-verification report, and
numeric-sanity report.

The physics RFDE metric set is:

- source anchor coverage,
- equation parse coverage,
- quantity binding completeness,
- dimension consistency,
- unit grounding density,
- law grounding density,
- implicit-gap closure,
- step executability,
- assumption/regime fidelity,
- coordinate-frame explicitness,
- target derivation success,
- artifact realness.

The standard report path is:

```text
artifacts/physics_sympy/<case_id>/physics_consistency_report.json
```

## Validation

Run the focused regression before declaring this skill healthy:

```bash
python tests/physics_sympy/run_phase13_consistency_report.py --json
```

The broader physics SymPy suite also calls this check through
`tests/test_program/run_comprehensive_tests.py`.
