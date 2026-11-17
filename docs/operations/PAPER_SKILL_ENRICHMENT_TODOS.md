<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Plan how the paper-writing skills should evolve so the Mathformer papers can
  be updated from new platform functionality without overclaiming or losing
  evidence discipline.

Intent:
  Record a reflective, implementation-ready TODO plan for enriching
  `paper_skills/` around reasoning-log dashboards, skill-application traces,
  reference-free monitors, controlled workflow hubs, premise selection, ATP,
  and recent autoformalization demonstrations.

Function:
  Guides future implementation passes that update paper skills first, then use
  those skills to revise the LaTeX papers and supporting figures.

Maintenance Notes:
  Keep this plan aligned with `paper_skills/`, `paper/`, `docs/architecture/REASONING_LOGS.md`,
  `docs/architecture/PRINCIPLES.md`, and the generated artifacts used as paper evidence.
-->

# Paper Skill Enrichment TODOs

## Implementation Summary

Status: implemented.

Primary evidence artifacts:

- `artifacts/paper_skills/new_functionality_evidence_packet.json`
- `artifacts/paper_skills/paper_update_plan.md`
- `artifacts/paper_skills/framework_paper_claim_audit.json`
- `artifacts/paper_skills/rfde_paper_claim_audit.json`
- `paper/figures/mathformer_observability_stack.json`
- `paper/figures/mathformer_observability_stack.pdf`
- `artifacts/workflow_hub/control_all.json`

Validation gates run:

- `python scripts/mathformer.py run control:all --json`
- `python scripts/mathformer.py run test:docs --json`
- `python scripts/mathformer.py run test:family:paper --json`
- `python scripts/mathformer.py run paper:functionality-update-suite --json --keep-going`
- `cd paper && tectonic MATHFORMER_FRAMEWORK_PAPER.tex`
- `cd paper && tectonic REFERENCE_FREE_REFINEMENT_DYNAMICS.tex`

Both claim-audit reports completed with zero findings. Both papers compile;
TeX reports only non-blocking layout warnings.

## Reflection

The current paper skills already separate repository cartography, mechanism
abstraction, RFDE evidence synthesis, paper drafting, claim auditing, and figure
generation. That is the right shape. The missing layer is a disciplined intake
path for new platform functionality.

Recent functionality changed the paper story in several concrete ways:

- reasoning logs now have a skill-application lifecycle and strict validation;
- reasoning logs can be rendered to Markdown and self-contained HTML dashboards;
- full autoformalization runs can be inspected through both workflow-level and
  skill-application-level traces;
- reference-free monitoring now has plots and statistics for formalization
  evolution;
- the controlled hub exposes workflows through stable actions;
- the README and tutorial now present the system through natural-language
  demonstrations rather than script-first usage;
- premise selection, ATP proof search, Lean/Rocq/SymPy workflows, and
  MathformerLib proof catalogs provide stronger demonstration surfaces.

The paper skills should therefore support one loop:

```text
new platform functionality
-> evidence packet
-> mechanism abstraction
-> claim-evidence audit
-> paper section patch plan
-> LaTeX update
-> figure/table update
-> compilation and claim audit
```

The critical design constraint is controlled epistemic tightening. Every paper
update should leave the manuscript with fewer unsupported claims, more explicit
evidence paths, or a precise blocker. A dashboard, monitor, or RFDE report is
evidence about observability and process control; it is not by itself evidence
that a theorem is mathematically correct.

## Phase 0: Define the New-Functionality Evidence Packet

- [x] Add `paper_skills/references/new_functionality_evidence_packet.md`.
- [x] Define the required packet fields:
  - [x] feature name;
  - [x] implementation paths;
  - [x] generated artifacts;
  - [x] validation commands and outputs;
  - [x] paper claims supported;
  - [x] claims explicitly not supported;
  - [x] target paper sections;
  - [x] figure/table implications;
  - [x] limitations and blockers.
- [x] Include a filled example for the reasoning-log HTML renderer:
  - [x] `skills/control/reasoning-log-schema-guardian/scripts/render_reasoning_log_html.py`;
  - [x] `artifacts/full_autoformalization_reasoning_log_test/reasoning.html`;
  - [x] `artifacts/full_autoformalization_reasoning_log_test/skill_application.html`;
  - [x] strict validation and dashboard inspection results.
- [x] Include a filled example for the reference-free monitor:
  - [x] monitor script path;
  - [x] CSV/JSON/SVG outputs;
  - [x] weakest-dimension and regression statistics;
  - [x] tutorial demonstration path.
- [x] Include a filled example for controlled workflow routing:
  - [x] `scripts/mathformer.py`;
  - [x] `docs/architecture/AGENTIC_HUB.md`;
  - [x] reasoning-log render action;
  - [x] control gates.

## Phase 1: Enrich Existing Paper Skills

### Framework Repository Cartographer

- [x] Add reasoning-log dashboards as first-class evidence surfaces.
- [x] Add skill-application logs and strict validation reports to the inventory.
- [x] Add controlled hub actions as evidence of reproducible workflow routing.
- [x] Add proof catalog and MathformerLib proof surfaces to the map.
- [x] Add premise-selection evidence:
  - [x] exact presence checks;
  - [x] Bloom-filter membership;
  - [x] embedding search;
  - [x] geometric distance reports.
- [x] Add ATP evidence:
  - [x] generated TPTP problems;
  - [x] Vampire SZS statuses;
  - [x] TSTP proof artifacts;
  - [x] premise-guided proof reports.
- [x] Add a section in the output shape named `New Functionality Evidence`.
- [x] Add a section in the output shape named `Paper Update Targets`.

### Workflow Mechanism Abstractor

- [x] Extend the state model with explicit observability artifacts:
  - [x] reasoning-log event stream;
  - [x] skill-application envelopes;
  - [x] HTML dashboard projection;
  - [x] reference-free monitor trajectory.
- [x] Define the dashboard as a projection, not a new proof source.
- [x] Define the skill-application lifecycle as a trace refinement over older
  hook-style logs.
- [x] Add a mechanism term for `inspection surface`.
- [x] Add a mechanism term for `legacy trace compatibility`.
- [x] Add a mechanism term for `evidence packet`.
- [x] Add a loop:
  ```text
  run -> reasoning log -> HTML dashboard -> human inspection -> skill update
  ```
- [x] Add a loop:
  ```text
  run -> reference-free monitor -> weakest dimension -> targeted refinement
  ```

### RFDE Evidence Synthesizer

- [x] Accept reasoning-log HTML dashboards as human inspection artifacts.
- [x] Accept skill-application JSONL logs as structured episode evidence.
- [x] Accept reference-free monitor CSV/JSON/SVG outputs.
- [x] Produce a paper-ready table of trajectory diagnostics:
  - [x] score delta;
  - [x] risk delta;
  - [x] weakest dimension;
  - [x] blocker count;
  - [x] regression count;
  - [x] artifact paths.
- [x] Produce a short observational vignette from the full autoformalization run.
- [x] Add explicit non-claim rules:
  - [x] dashboard visibility does not prove correctness;
  - [x] RFDE improvement does not replace backend validation;
  - [x] reference-free monitoring should be paired with source and execution
    evidence.

### Scientific Paper Drafter

- [x] Add a `New Functionality Revision Procedure`.
- [x] Require a new-functionality evidence packet before revising claims.
- [x] Add section-target routing:
  - [x] architecture and workflow sections;
  - [x] observability/RFDE sections;
  - [x] demonstrations/case studies;
  - [x] limitations;
  - [x] reproducibility and agent-client setup.
- [x] Add update instructions for both paper sources:
  - [x] `paper/MATHFORMER_FRAMEWORK_PAPER.tex`;
  - [x] `paper/REFERENCE_FREE_REFINEMENT_DYNAMICS.tex`.
- [x] Add a preferred paragraph pattern:
  - [x] capability statement;
  - [x] mechanism;
  - [x] evidence artifact;
  - [x] limitation.
- [x] Add a table pattern for new functionality:
  - [x] feature;
  - [x] owner skill;
  - [x] evidence;
  - [x] validation gate;
  - [x] paper claim.

### Paper Claim Evidence Auditor

- [x] Add claim categories for:
  - [x] observability claims;
  - [x] dashboard/interface claims;
  - [x] workflow-control claims;
  - [x] reasoning-log schema claims;
  - [x] reference-free monitor claims.
- [x] Add checks for missing artifact paths in paper claims.
- [x] Add checks for unsupported correctness claims from dashboards or RFDE.
- [x] Add checks that every new paper figure/table has a generating path or an
  explicit conceptual status.
- [x] Add checks that paper claims distinguish:
  - [x] generated artifact;
  - [x] validated artifact;
  - [x] inspected artifact;
  - [x] conceptual proposal.

### Mechanistic Diagram Modeler And Figure Renderer

- [x] Add a preset for the observability stack:
  ```text
  skill execution -> reasoning log -> validation -> HTML dashboard -> RFDE monitor -> reflection
  ```
- [x] Add visual node types for:
  - [x] event stream;
  - [x] validation gate;
  - [x] dashboard projection;
  - [x] monitor plot;
  - [x] human inspection;
  - [x] reflective update.
- [x] Add captions that describe inspection and control, not proof.
- [x] Verify generated SVG/TikZ stays readable at paper width.

### Theory Evolution Modeler And Simulator

- [x] Treat reference-free monitor outputs as empirical calibration candidates.
- [x] Add parameters for instrumentation density and dashboard inspection rate.
- [x] Add a scenario in which observability improves without immediate theorem
  success.
- [x] Add a scenario in which dashboard inspection detects legacy trace gaps.
- [x] Mark these as simulated or observational depending on evidence source.

## Phase 2: Consider One New Coordinating Paper Skill

- [x] Create `paper-functionality-update-orchestrator` only if existing skills
  become awkward to coordinate.
- [x] Its trigger should be: use when a new Mathformer feature needs to be
  converted into paper updates across evidence mapping, mechanism abstraction,
  drafting, figures, and claim audit.
- [x] Keep `SKILL.md` concise; move detailed templates into references.
- [x] Output shape:
  - [x] feature evidence packet;
  - [x] paper claim delta;
  - [x] section patch plan;
  - [x] figure/table plan;
  - [x] validation checklist.
- [x] Do not let this skill bypass the claim-evidence auditor.

## Phase 3: Add Deterministic Paper-Support Scripts

- [x] Add `paper_skills/framework-repository-cartographer/scripts/build_paper_evidence_packet.py`.
- [x] Add `paper_skills/paper-claim-evidence-auditor/scripts/audit_paper_claims.py`.
- [x] Add `paper_skills/scientific-paper-drafter/scripts/plan_paper_update.py`.
- [x] Add optional JSON outputs for these scripts so they can feed the paper
  drafter without manual prose scraping.
- [x] Register the scripts in the controlled hub if they become top-level
  workflows.
- [x] Add reasoning-log support or wrapper support for each script.

## Phase 4: Update the Paper Mechanism Map

- [x] Update `paper_skills/references/mathformer_mechanism_map.md` with:
  - [x] reasoning-log schema guardian;
  - [x] HTML reasoning-log renderer;
  - [x] skill-application lifecycle;
  - [x] reference-free critic monitor;
  - [x] workflow hub and controlled actions;
  - [x] proof catalog;
  - [x] premise selection;
  - [x] ATP/Vampire proof artifacts.
- [x] Add an `Observability Surfaces` table.
- [x] Add an `Inspection Artifacts` table.
- [x] Add a `New Functionality Intake` mini-workflow.
- [x] Update non-claims to include dashboards and monitors.

## Phase 5: Prepare Manuscript Updates

### `MATHFORMER_FRAMEWORK_PAPER.tex`

- [x] Update the abstract with the current observability stack.
- [x] Update the introduction contribution list:
  - [x] controlled skill-application traces;
  - [x] reasoning-log HTML dashboards;
  - [x] reference-free monitor plots/statistics;
  - [x] premise selection and ATP proof-search demonstrations;
  - [x] natural-language controlled workflow front door.
- [x] Add a subsection on reasoning-log dashboards as inspection surfaces.
- [x] Add a subsection or paragraph on full autoformalization trace inspection.
- [x] Update the skill-family table with:
  - [x] reasoning-log schema guardian;
  - [x] reference-free critic monitor;
  - [x] premise selection;
  - [x] proof catalog.
- [x] Add a demonstration table linking:
  - [x] Lean full autoformalization trace;
  - [x] Vampire ATP proof demo;
  - [x] premise-selection search demo;
  - [x] physics SymPy demonstration;
  - [x] reference-free monitor evolution demo.
- [x] Add a limitation that HTML dashboards improve inspectability but do not
  certify mathematical correctness.

### `REFERENCE_FREE_REFINEMENT_DYNAMICS.tex`

- [x] Add the HTML reasoning-log dashboard as a measurement projection.
- [x] Add the reference-free monitor plots/statistics as concrete trajectory
  artifacts.
- [x] Add a short definition of an inspection projection from event logs to
  human-readable dashboards.
- [x] Add a diagnostic role for legacy trace compatibility.
- [x] Add examples of weakest-dimension targeting from monitor output.
- [x] Add a limitation on visual analytics: plots support diagnosis, not proof.

## Phase 6: Figures And Tables

- [x] Generate an observability-stack figure.
- [x] Generate or reference a dashboard screenshot only if a reproducible
  screenshot path exists.
- [x] Add a table of reasoning-log event lifecycle stages.
- [x] Add a table of paper-update evidence packets.
- [x] Add a table comparing:
  - [x] backend validation;
  - [x] reasoning-log validation;
  - [x] RFDE monitoring;
  - [x] human inspection;
  - [x] claim audit.

## Phase 7: Validation Gates

- [x] Run `python scripts/mathformer.py run control:all --json`.
- [x] Run `python scripts/mathformer.py run test:docs --json`.
- [x] Run paper-skill tests in the comprehensive matrix.
- [x] Compile `paper/MATHFORMER_FRAMEWORK_PAPER.tex`.
- [x] Compile `paper/REFERENCE_FREE_REFINEMENT_DYNAMICS.tex`.
- [x] Run the paper claim-evidence auditor after manuscript edits.
- [x] Verify that every new figure/table source path exists.
- [x] Verify that every new artifact path either exists or is explicitly marked
  as an example path.

## Phase 8: Acceptance Criteria

- [x] Paper skills can take a new feature and produce a structured evidence
  packet.
- [x] Paper skills can map the feature to paper sections and claim types.
- [x] Paper skills can distinguish implemented evidence from conceptual framing.
- [x] The framework paper can be updated without unsupported correctness claims.
- [x] The RFDE paper can describe dashboards and monitors as observability
  instruments.
- [x] All generated paper figures/tables have reproducible sources.
- [x] Control, docs, paper compilation, and claim-audit gates pass.
