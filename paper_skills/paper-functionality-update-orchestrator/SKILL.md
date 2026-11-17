---
name: paper-functionality-update-orchestrator
description: Coordinate Mathformer paper updates for newly implemented platform functionality by building an evidence packet, routing claims to paper sections, planning figures/tables, and invoking claim-evidence audit discipline. Use when a new feature such as reasoning-log dashboards, reference-free monitors, workflow hubs, premise selection, ATP, or proof catalogs needs to be reflected in the papers.
---

<!--
File Documentation

Motivation:
  Prevent new platform functionality from becoming unsupported manuscript prose.

Intent:
  Provide one coordinating paper skill that moves from feature evidence to
  section patch plans while preserving claim-audit discipline.

Function:
  Orchestrates repository cartography, mechanism abstraction, RFDE synthesis,
  paper drafting, figure planning, and claim-evidence auditing.

Maintenance Notes:
  Keep this skill concise. Put reusable schemas and examples in
  `paper_skills/references/`.
-->

# Paper Functionality Update Orchestrator

## Purpose

Use this skill when a Mathformer feature has changed and the papers need to be
updated. The output is not manuscript prose first. The output is an evidence
packet, a claim delta, a section patch plan, a figure/table plan, and an audit
checklist.

## Procedure

1. Build or read a new-functionality evidence packet using
   `paper_skills/references/new_functionality_evidence_packet.md`.
2. Ask `framework-repository-cartographer` to place the feature inside the
   repository evidence map.
3. When the feature changes agentic coordination, workflow coverage, or the
   paper appendix, collect the workflow catalogue with
   `paper_skills/framework-repository-cartographer/scripts/collect_workflow_catalog_for_paper.py`.
4. Ask `workflow-mechanism-abstractor` to name the mechanism: state component,
   transition, inspection surface, monitor, validation gate, or feedback loop.
5. Ask `scientific-paper-drafter` for a section patch plan using the pattern:
   capability statement, mechanism, evidence artifact, limitation.
6. Ask `mechanistic-diagram-modeler` and `mechanistic-figure-renderer` only
   when the feature changes the visual mechanism.
7. Ask `paper-claim-evidence-auditor` to check that every new claim is backed
   by implementation, generated artifacts, validation outputs, or explicit
   conceptual framing.

For workflow-architecture updates, use multiple paper agents in this order:
cartographer -> workflow-mechanism-abstractor -> scientific-paper-drafter ->
paper-claim-evidence-auditor. The cartographer supplies the catalogue, the
abstractor supplies notation, the drafter writes the core and appendix prose,
and the auditor removes unsupported claims.

## Output Shape

- `Feature Evidence Packet`
- `Paper Claim Delta`
- `Section Patch Plan`
- `Figure/Table Plan`
- `Validation Checklist`
- `Residual Risks`

## Guardrails

- Do not bypass the claim-evidence auditor.
- Do not treat dashboards, monitor plots, or RFDE scores as proof of theorem
  correctness.
- Keep unsupported statements as limitations, conceptual proposals, or blockers.
