---
name: framework-repository-cartographer
description: Map the Mathformer repository into paper-ready evidence: skill families, workflow hooks, Lean artifacts, reports, scripts, logs, and validation surfaces. Use before writing or revising a scientific paper about the Mathformer framework so claims are grounded in concrete repository artifacts.
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

# Framework Repository Cartographer

## Purpose

Use this skill at the start of a paper-writing pass. It turns the repository
into a compact evidence map for the paper: what exists, which part of the
framework it supports, and what claims it can safely justify.

This skill is descriptive. It should not overclaim novelty or correctness; it
should identify evidence surfaces and missing evidence.

## Workflow

1. Inventory the repository:
   - Lean modules under `backends/lean/Mathformer/` and `libraries/MathformerLib/`;
   - workflow skills under `skills/`;
   - hook contract `skills/SKILL_HOOKS.yaml`;
   - framework docs under `docs/`;
   - RFDE artifacts under `artifacts/rfde/`;
   - workflow graph and catalogue artifacts under
     `artifacts/workflow_graphs/` and `artifacts/paper_skills/`;
   - reasoning logs, skill-application logs, HTML dashboards, and consistency
     reports under `artifacts/`;
   - controlled hub actions in `scripts/mathformer.py`;
   - proof catalogs under `docs/libraries/mathformerlib/` and library artifacts under
     `libraries/MathformerLib/` and `libraries/MathformerPhysicsLib/`.
2. Group skills into mechanism families:
   - source extraction and line anchoring;
   - prerequisite expansion and binding review;
   - mathlib grounding and duplicate-result checks;
   - Lean drafting, execution, critique, and refinement;
   - reverse informalization and consistency validation criteria;
   - realness, non-vacuity, and artifact acceptance;
   - RFDE trajectory observability and reference-free monitor plots;
   - ATP proof search and premise selection;
   - reflective skill improvement and testing.
3. For each family, record:
   - representative skill paths;
   - main scripts or deterministic checks;
   - hook ids or workflow phases;
   - inputs and outputs;
   - convergence and validation criteria;
   - generated evidence surfaces such as JSONL traces, HTML dashboards, TPTP
     problems, Vampire TSTP proofs, Bloom-filter membership reports, embedding
     search neighborhoods, and geometric distance reports;
   - paper claim supported by this evidence.
4. For workflow-architecture paper updates, run:

```bash
python3 paper_skills/framework-repository-cartographer/scripts/collect_workflow_catalog_for_paper.py --json
```

Use the resulting `artifacts/paper_skills/workflow_catalog_for_paper.json` as
the source of workflow counts, hook counts, family names, reflective-loop
status, and appendix table material.
5. Separate implemented evidence from conceptual design:
   - implemented: backed by local files, scripts, reports, or generated artifacts;
   - partially implemented: present but sparse or mostly historical;
   - proposed: described in docs but not yet operationally evidenced.
6. Produce a paper-ready mechanism map table, workflow catalogue summary, and
   claim-evidence ledger.

## Output Shape

Return or write a concise map with these sections:

- `Repository Evidence Map`
- `Skill Family Table`
- `Workflow Hook/Validation-Criterion Summary`
- `Workflow Catalogue Summary`
- `Observed Artifact Evidence`
- `New Functionality Evidence`
- `Paper Update Targets`
- `Claim-Evidence Ledger`
- `Gaps and Limitations`

## Guardrails

- Do not infer that a method is validated merely because a skill exists.
- Distinguish source-grounding evidence from Lean-correctness evidence.
- Distinguish deterministic scripts from generative prompts.
- Treat RFDE as descriptive observability, not a proof of correctness.
- Keep path references exact enough that a reader can inspect them.
