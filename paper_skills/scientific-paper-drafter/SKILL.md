---
name: scientific-paper-drafter
description: Draft and revise a LaTeX scientific paper about the Mathformer autoformalization framework from repository evidence, mechanistic models, RFDE trajectory artifacts, and claim-evidence ledgers. Use after framework cartography and mechanism abstraction.
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

# Scientific Paper Drafter

## Purpose

Use this skill to write or revise the LaTeX manuscript describing Mathformer as
a controlled, source-anchored, mathlib-grounded, reference-free observable
autoformalization framework.

## Paper Structure

Prefer this structure unless the target venue requires otherwise:

1. Abstract
2. Introduction
3. Background and Motivation
4. Framework Overview
5. Mechanistic Model
6. Workflow and Skill Architecture
7. Reference-Free Descriptive Evaluation
8. Observability and Trajectory Analysis
9. Case Studies or Demonstrations
10. Limitations
11. Related Work
12. Conclusion

## Drafting Procedure

1. Start from the claim-evidence ledger; do not invent unsupported results.
2. Describe the system as an architecture and methodology, not a solved
   correctness theorem.
3. Use formal notation only where it clarifies the mechanism:
   - state tuple;
   - transition function;
   - metric vector;
   - hard validation criteria;
   - cost-normalized progress;
   - phase-transition predicates.
4. Include tables for skill families, validation criteria, and observability surfaces.
5. When a workflow catalogue is available, describe the main workflows in the
   core paper using formal notation, then place the full catalogue in an
   appendix. Cite `artifacts/workflow_graphs/workflow_graphs.html`,
   `artifacts/workflow_graphs/workflow_graphs.json`, and
   `artifacts/paper_skills/workflow_catalog_for_paper.json` as evidence
   surfaces.
6. Include figure placeholders for:
   - pipeline diagram;
   - feedback-loop diagram;
   - RFDE trajectory timeline;
   - parallel signal plots.
7. Add limitations early enough that the paper reads as epistemically careful:
   RFDE is reference-free, not proof-free; Lean execution and source alignment
  are necessary evidence surfaces but not complete semantic validation.

## New Functionality Revision Procedure

Before revising a manuscript for a new feature, require a new-functionality
evidence packet. Route the feature to:

- architecture and workflow sections;
- observability/RFDE sections;
- demonstrations and case studies;
- limitations;
- reproducibility and agent-client setup.

Apply this paragraph pattern:

```text
capability statement -> mechanism -> evidence artifact -> limitation
```

Use this table pattern when the update spans several artifacts:

| Feature | Owner skill | Evidence | Validation gate | Paper claim |
| --- | --- | --- | --- | --- |

For workflow-catalogue updates, add two targets:

- core paper: a concise formalization of `W = {w_j}` and a table of main
  workflow classes;
- appendix: the full workflow stack catalogue with family, hook count,
  reflective status, and transition view.

The two default targets are `paper/MATHFORMER_FRAMEWORK_PAPER.tex` and
`paper/REFERENCE_FREE_REFINEMENT_DYNAMICS.tex`.

## Claim Discipline

Every substantive claim should be one of:

- repository-backed;
- artifact-backed;
- conceptual proposal;
- limitation or open problem.

Mark speculative statements as future work.

## LaTeX Style

- Use `article` unless the user specifies a venue template.
- Keep macros minimal and readable.
- Prefer tables over long prose lists for architecture maps.
- Add figure placeholders with descriptive captions rather than pretending
  generated figures already exist.
