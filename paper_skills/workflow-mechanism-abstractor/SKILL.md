---
name: workflow-mechanism-abstractor
description: Abstract Mathformer skills, hooks, validation criteria, reasoning logs, and RFDE reports into a mechanistic and dynamical model for a scientific paper. Use after repository cartography when the paper needs formal language for trajectories, feedback loops, phase transitions, convergence, cost, and monotonic refinement.
---

<!--
File Documentation

Motivation:
  Capture the research-paper production workflow as auditable agent skills and helper scripts.

Intent:
  Separate scientific writing, evidence mapping, figure generation, and theory-evolution modeling roles.

Function:
  Provides structured guidance and automation for paper-oriented artifacts.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Workflow Mechanism Abstractor

## Purpose

Use this skill to turn the concrete Mathformer framework into a scientific
model. The output should be suitable for a methods section: entities,
transitions, validation criteria, observability surfaces, and dynamics vocabulary.

## Mechanistic Model

Represent a run as a controlled trajectory:

```text
source -> extraction -> expansion -> grounding -> drafting
       -> Lean execution -> critique -> refinement
       -> consistency -> RFDE observation -> reflection
```

Use the state tuple:

```text
S_t = (X, U, L_t, G_t, C_t, R_t, O_t, M_t, Q_t)
```

where:

- `X`: literal source and provenance;
- `U`: extracted formalizable units and line-translation packets;
- `L_t`: Lean artifact at iteration `t`;
- `G_t`: mathlib grounding and import context;
- `C_t`: critic and validation-criterion reports;
- `R_t`: reverse informalization and informal proof packets;
- `O_t`: obligation ledger;
- `M_t`: metric vector;
- `Q_t`: temporal, deterministic, and generative cost trace.

The observability component should explicitly include:

- reasoning-log event streams;
- skill-application envelopes;
- HTML dashboard projections;
- reference-free monitor trajectories;
- premise-selection neighborhoods and exact membership checks;
- ATP proof-search artifacts.
- workflow catalogue and graph reports that map stacks, hook sequences, and
  reflective edges to transition relations.

## Workflow Catalogue Formalization

When `artifacts/paper_skills/workflow_catalog_for_paper.json` is available,
formalize the collection of workflows as

```text
W = {w_j},    w_j = (id_j, family_j, sigma_j, E_j, R_j)
```

where `sigma_j = (h_1, ..., h_n)` is the ordered hook sequence, `E_j` is the
artifact and evidence surface, and `R_j` is the optional reflective edge set.
Each hook has the shape

```text
h_i = (owner_skill, role, execution_posture, output_type, validation_gate)
```

Map workflow families to the paper transition vocabulary:

- source intake and theory extraction -> `Rel_intake`, `Rel_expand`;
- mathlib and library grounding -> `Rel_ground`;
- drafting and execution -> `Rel_draft`, `Rel_execute`, `Rel_repair`;
- acceptance and consistency -> `Rel_consistency`;
- premise selection and ATP -> `Rel_premise`, `Rel_atp`;
- SymPy and physics derivations -> `Rel_symbolic`, `Rel_physics`;
- workflow graph reporting, RFDE, and reasoning logs -> `Rel_observe`,
  `Rel_reflect`;
- control and direct-route surfaces -> `Rel_control`, `Rel_support`.

## Dynamics Vocabulary

Use the following paper concepts:

- `hard validation criterion`: non-negotiable accept/reject condition such as Lean execution,
  realness, source-anchor validity, or consistency.
- `soft critic`: diagnostic signal that proposes refinement targets.
- `protected metric`: a dimension that should not regress, such as source
  fidelity, proof realness, non-vacuity, or executability.
- `phase transition`: a qualitative shift in run regime, such as failing critics
  becoming passing critics, anchor coverage crossing threshold, or an artifact
  moving from draft to complete.
- `plateau`: repeated cost without metric progress.
- `oscillation`: alternating improvement/regression over protected dimensions.
- `grounding gain`: increased mathlib compatibility without source drift.
- `semantic drift`: improved executability with worse source alignment.
- `inspection surface`: a human-readable projection of structured evidence,
  such as an HTML reasoning-log dashboard. It improves inspection; it is not a
  new proof source.
- `legacy trace compatibility`: a refinement relation between older hook-style
  logs and newer skill-application lifecycle traces.
- `evidence packet`: a structured bridge from implementation paths and
  generated artifacts to supported paper claims and explicit non-claims.

Use these loops when the feature is about observability:

```text
run -> reasoning log -> HTML dashboard -> human inspection -> skill update
run -> reference-free monitor -> weakest dimension -> targeted refinement
```

## Abstraction Procedure

1. Read the repository evidence map.
2. Map each skill family to a state component and transition type.
3. Map hook validation criteria to convergence predicates.
4. Map RFDE metrics to observability dimensions.
5. Map reports and visualizations to measurement instruments.
6. Treat dashboards as projections from logs, not proof sources.
7. Convert this into:
   - definitions;
   - equations;
   - method description;
   - limitations and non-claims.

## Guardrails

- Do not claim RFDE certifies theorem correctness.
- Do claim RFDE helps evaluate the process without a gold formalization.
- Keep the model explicitly mechanistic: name states, transitions, validation criteria,
  feedback loops, and costs.
- Preserve the distinction between generation and deterministic checking.
