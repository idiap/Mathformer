<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Represent changes to reasoning itself without confusing the epistemic change
  with the skills, hooks, agents, or tools that happen to implement it.

Intent:
  Define reflective refinement as a higher-order, evidence-governed transition
  between immutable reasoning specifications.

Function:
  Provides the proposed ontology, ERFL projection, authority rules, meta-skill
  boundary, runtime record contract, and implementation direction for
  reflective reasoning refinement.

Maintenance Notes:
  Keep the core semantics skill-independent. Operational materializations may
  cite skills only in a separate binding or execution-provenance layer.
-->

# Reflective Refinement

## Decision

Reflective refinement should be represented as reasoning **about a versioned
reasoning specification**, not as one skill changing another skill and not as a
new atomic `meta` operation.

The operation type says how an epistemic step reasons. The typed subject says
what the step reasons about. For example:

```text
X[..., artifact::Bundle -> repair::Plan]
```

is object-level repair, while:

```text
X[
  baseline_reasoning::Model<ReasoningSpecification>,
  reflection::Assessment
  -> proposed_delta::Delta<ReasoningSpecification>
]
```

is reflective refinement. The existing operation algebra is therefore
level-polymorphic: `L`, `X`, `F`, `P`, `C`, `R`, and `E` retain their meanings
when their subject is reasoning itself.

The governing rule is:

> Reflection may propose a successor to a reasoning process, but the proposal
> cannot authorize its own adoption.

## Why The Earlier Profile Stopped Too Early

The earlier trajectory-reflection profile had the effective shape:

```text
trajectories
  -> comparison
  -> improvement hypothesis
  -> regression evidence
  -> assessment
  -> disposition
```

This represents reflective evaluation of an improvement hypothesis. It does
not yet represent refinement because it does not name:

- the reasoning specification being changed;
- the exact reasoning surface targeted by the change;
- an explicit delta over that specification;
- a distinct, immutable candidate successor;
- evidence bound separately to the baseline and candidate;
- the fixed comparison and adoption contracts;
- the predecessor-to-successor revision relation;
- the rollback target or scope of adoption.

Likewise, a workflow-evolution record with an owner and prose `next_delta`
describes an operational next action. It is not yet a typed reasoning revision.

## Three Separate Layers

The architecture should preserve three layers that can be joined by stable
identities but never collapsed:

| Layer | Describes | May contain skill identifiers? |
| --- | --- | --- |
| Epistemic semantics | Baseline reasoning, reflection, delta, candidate, trials, comparison, assessment, and disposition | No |
| Materialization binding | Which capabilities, skills, actions, hooks, or tools may realize each occurrence | Yes |
| Execution provenance | Which binding actually ran, with environment, artifact, evidence, and digest references | Yes |

This separation means that replacing every implementation while preserving the
same reasoning specification is an implementation refinement. Conversely, a
change to the reasoning graph, relation, interface, criterion, or stopping rule
is an epistemic refinement even when the same implementation realizes it.

## Higher-Order Semantic Subjects

These subjects specialize existing ERFL root kinds; they are not new operation
codes and initially need not become new root kinds.

| Subject | Meaning |
| --- | --- |
| `ReasoningSpecification` | A skill-independent epistemic graph with typed operations, interfaces, relations, branches, iteration policy, and terminal dispositions |
| `ReasoningTrajectory` | An immutable observation of a run bound to one exact reasoning-specification identity |
| `ReasoningRevision` | The predecessor/delta/successor relation, including preservation and invalidation information |
| `RefinementContract` | Frozen cases, measures, comparison rules, thresholds, protected properties, and admissible change scope |
| `EvaluationCase` | One declared case used to evaluate baseline and candidate reasoning |
| `AdoptionPolicy` | The external authority boundary for experiment, adoption, retention, rollback, and escalation |

The existing roots already cover their epistemic roles:

```text
baseline_reasoning      :: Model<ReasoningSpecification>
baseline_evidence       :: Evidence<ReasoningTrajectory>
proposed_delta          :: Delta<ReasoningSpecification>
candidate_reasoning     :: Model<ReasoningSpecification>
revision_record         :: Relation<ReasoningRevision>
evaluation_cases        :: Bundle<EvaluationCase>
evaluation_contract     :: Constraint<RefinementContract>
trust_anchor            :: Constraint<AdoptionPolicy>
comparative_assessment  :: Assessment
refinement_status       :: Decision
```

In ERFL 0.3 the generic subject is currently documentary: the validator checks
the root `Model`, `Evidence`, or `Delta`, but not the full generic kind. Full
subject conservation is therefore a required validator refinement.

## Refinement Subjects And Meta-Depth

The target of change is an orthogonal facet, not an operation type.

| Refinement subject | Examples of change |
| --- | --- |
| `reasoning_trajectory` | Interpretation or segmentation of what happened in recorded runs |
| `reasoning_specification` | Operation composition and epistemic dependencies |
| `flow_schema` | Occurrences, relations, branches, joins, and loop structure |
| `decomposition_schema` | Problem partitioning and recombination strategy |
| `selection_policy` | Route, capability, premise, or context selection |
| `stopping_policy` | Retry bounds, progress measures, convergence, blocking, and acceptance |
| `criterion_set` | Measures, rubrics, thresholds, and protected properties |
| `representation_interface` | Handles, semantic kinds, preservation, and handoff contracts |
| `memory_policy` | Retention, retrieval, promotion, deprecation, and forgetting |
| `warrant_policy` | Claim ceilings, evidence requirements, and trust transitions |
| `governance_contract` | Evaluation independence, adoption, expiry, and rollback |
| `language_ontology` | ERFL operations, relations, semantic kinds, and invariants |

The same subject taxonomy combines with a meta-depth:

| Depth | Object being reasoned about |
| --- | --- |
| `object` (`R0`) | Mathematical, scientific, formal, or documentary objects |
| `process` (`R1`) | Reasoning specifications and their trajectories |
| `governance` (`R2`) | Evaluation contracts, trust anchors, adoption, and promotion policies |
| `language` (`R3`) | The ontology and validator that define the reasoning language |

A refinement transaction may act at one declared depth. A candidate may not
change the unchanged authority used to assess that candidate in the same
transaction.

## Reflective Refinement Lifecycle

Reflection and mutation are deliberately separated:

```text
observe/compare baseline behavior
  -> reflect and diagnose
  -> propose a typed reasoning delta
  -> construct an immutable successor specification
  -> test the candidate under a frozen contract
  -> compare baseline and candidate evidence
  -> verify protected properties and obligations
  -> calibrate a scoped disposition
  -> operational commit or rollback outside ERFL
```

The core one-step composition is:

```text
L -> X -> F -> P -> L/C -> R -> E
```

`O`, `S`, and `M` may precede it when raw logs must first be observed,
decomposed, or reconstructed into a trajectory model. They are not required
when a baseline specification and typed trajectory evidence are already
inputs.

## Canonical ERFL 0.3 Profile

The canonical trajectory-reflection profile now uses only existing ERFL 0.3
operation codes, relations, and root kinds:

```erfl
erfl 0.3
reasoning reflective_reasoning_refinement {
  goal "produce a tested disposition over an immutable reasoning revision" -> refinement_status
  steps
    l0:L[
      baseline_reasoning::Model<ReasoningSpecification>,
      baseline_evidence::Evidence<ReasoningTrajectory>,
      refinement_goal::Goal,
      evaluation_cases::Bundle<EvaluationCase>,
      evaluation_contract::Constraint<RefinementContract>,
      trust_anchor::Constraint<AdoptionPolicy>
      -> reflective_assessment::Assessment
    ]
    -revise> x:X[
      baseline_reasoning::Model<ReasoningSpecification>,
      reflective_assessment::Assessment,
      evaluation_contract::Constraint<RefinementContract>,
      trust_anchor::Constraint<AdoptionPolicy>
      -> proposed_delta::Delta<ReasoningSpecification>
    ]
    -construct> f:F[
      baseline_reasoning::Model<ReasoningSpecification>,
      proposed_delta::Delta<ReasoningSpecification>
      -> candidate_reasoning::Model<ReasoningSpecification>,
      revision_record::Relation<ReasoningRevision>
    ]
    -test> p:P[
      candidate_reasoning::Model<ReasoningSpecification>,
      evaluation_cases::Bundle<EvaluationCase>,
      evaluation_contract::Constraint<RefinementContract>
      -> candidate_evidence::Evidence<ReasoningTrajectory>
    ]
    -compare> l1:L[
      baseline_evidence::Evidence<ReasoningTrajectory>,
      candidate_evidence::Evidence<ReasoningTrajectory>,
      evaluation_contract::Constraint<RefinementContract>
      -> comparative_assessment::Assessment
    ]
    -assess> r:R[
      candidate_reasoning::Model<ReasoningSpecification>,
      revision_record::Relation<ReasoningRevision>,
      comparative_assessment::Assessment,
      trust_anchor::Constraint<AdoptionPolicy>
      -> adoption_assessment::Assessment
    ]
    -calibrate> e:E[
      baseline_reasoning::Model<ReasoningSpecification>,
      candidate_reasoning::Model<ReasoningSpecification>,
      revision_record::Relation<ReasoningRevision>,
      comparative_assessment::Assessment,
      adoption_assessment::Assessment,
      trust_anchor::Constraint<AdoptionPolicy>
      -> refinement_status::Decision
    ]
  on e.adopted_for_scope => accept
  on e.retained_as_experiment => stop
  on e.rejected => stop
  on e.blocked => stop
}
```

The profile distinguishes six epistemic products:

1. `reflective_assessment` explains why a change may be needed.
2. `proposed_delta` specifies a prospective intervention and carries no
   evidence that it improves anything.
3. `candidate_reasoning` is a new immutable identity; it is not an in-place
   mutation of the baseline.
4. `revision_record` relates predecessor, delta, and successor.
5. Candidate evidence and comparative assessment are bound to a frozen
   evaluation contract.
6. `refinement_status` authorizes only a scoped disposition and creates no
   substantive evidence.

`accept` means that adoption is warranted for the declared scope. It does not
change an active-version pointer. An operational commit must cite the exact
decision, candidate digest, adoption policy, and rollback target.

For a stronger paired-trial profile, `P` should execute both baseline and
candidate under the same case set and environment rather than reuse historical
baseline evidence. That variant is preferable whenever environmental drift,
model drift, or stochastic execution could confound the comparison.

## Reasoning Delta Semantics

A `Delta<ReasoningSpecification>` targets reasoning structure, never an
implementation name. Its operation vocabulary should cover:

- add, remove, replace, or retype an occurrence;
- replace or constrain an epistemic relation;
- add, remove, or retype an input or output interface;
- add or alter a branch, join, or selection policy;
- alter an iteration bound, progress measure, or stopping condition;
- alter context, retrieval, grounding, or memory policy;
- alter evidence-production or assessment criteria;
- alter calibration, terminal, or escalation policy.

Each delta should record its target selector, before and after forms, evidence
basis, expected epistemic effect, protected invariants, opened obligations,
evaluation protocol, and rollback identity.

## Static And Runtime Invariants

### Projection-level invariants

- Baseline and candidate use distinct handles and compatible full subject kinds.
- `X` produces a `Delta<ReasoningSpecification>` rather than a skill edit.
- `F` consumes the baseline and delta and produces both a successor and a
  revision relation.
- Candidate evidence is produced after the successor exists.
- Comparative assessment consumes separately bound baseline and candidate
  evidence under one evaluation contract.
- Critical assessment precedes terminal calibration.
- The adoption policy is external to and unchanged by the candidate.
- A flow cannot accept an untested, in-place, or self-authorized revision.

### Runtime invariants

- Baseline and candidate have immutable, distinct identities and digests.
- Applying the recorded delta to the recorded baseline reproduces the candidate.
- Evidence is bound to the exact specification, cases, evaluator, environment,
  backend, model, seed, and replicate identities that produced it.
- Baseline and candidate use comparable conditions or explicitly declared
  controlled differences.
- Diagnosis cases and holdout evaluation cases remain distinguishable.
- Protected per-case successes cannot be hidden by an aggregate score increase.
- Affected evidence becomes stale after a change unless preservation is shown.
- Adoption is scoped, expiring or reviewable where appropriate, and names a
  rollback target.

### Non-coercions

- Reflection is not revision authority.
- A reasoning delta is a proposal, not evidence of improvement.
- A candidate cannot weaken its own tests and use them to approve itself.
- Non-regression on a finite suite is not global monotonic improvement.
- Replaying the same specification is not a delta.
- Calibration creates a disposition, not object-level evidence.
- An implementation edit that preserves the epistemic specification is not
  automatically a reasoning refinement.

## Meta-Circularity And Trust Anchors

Self-refinement requires a stratified authority rule:

- An `R1` process may propose a revision to `R0` reasoning and test it under an
  unchanged `R2` adoption policy.
- If the candidate changes the `R1` evaluator or refinement contract, an
  unchanged `R2` policy must assess that evaluator change.
- If the candidate changes `R2` itself, adoption escalates to an explicitly
  external authority, such as a human-reviewed policy transition.
- Changes to the `R3` language ontology require external governance and cannot
  be self-certified by the changed validator.

This is not an attempt to eliminate every trust assumption. It makes the trust
anchor explicit and prevents the candidate from manufacturing independence by
judging itself under rules it just changed.

## How The Existing Meta-Skill Surface Fits

The current meta-skill infrastructure largely covers operational
materialization. Its epistemic roles can be stated without making those
implementations part of the flow:

| Epistemic role | Skill-independent product | Current operational surfaces |
| --- | --- | --- |
| Observe | Trajectory evidence | Runtime application traces, reasoning logs, reference-free measurements |
| Model | Reasoning and trajectory models | Task registries, workflow-evolution graphs, ERFL profiles, taxonomies |
| Compare | Baseline/candidate or cross-run assessment | Reference-free monitoring and trajectory evaluation |
| Diagnose | Localized failure and change surface | Diagnostics, contract findings, coverage findings, reflective questions |
| Propose revision | Typed reasoning delta | Refinement packets and evolution `next_delta` records, currently mostly prose |
| Construct candidate | Immutable successor specification | Generated-candidate lifecycle templates, currently limited to generated skills |
| Test | Candidate-bound evidence | Skill test programs, meta-skill suite, seeded-defect fixtures |
| Verify | Criterion-scoped assessment | Contract, trace, quality, lifecycle, evolution, ERFL, and MCP validators |
| Govern/adopt | Scoped disposition | Gate policy, promotion lifecycle, release boundaries, and workflow hub |
| Record/learn | Versioned memory | Reasoning logs, evolution logs, quality cards, and projections |

The principal gap is between “propose revision” and “construct candidate.” The
repository can propose actions and govern generated skills, but it has no
general, skill-independent record for transforming one reasoning specification
into another.

Existing runtime traces should remain implementation-aware. They should gain
links to `reasoning_specification_id`, `reasoning_specification_digest`,
`occurrence_id`, `revision_id`, and `evaluation_contract_digest`. The core
revision record should reject `skill_id`, `owner_skill`, `hook_id`, and
`action_id`; those fields belong in the binding or provenance records joined to
it.

## Iterated Refinement

ERFL 0.3 `repeat` is bounded and calibrated, but it does not have an explicit
loop-carried state binding. Static handle reuse does not faithfully express:

```text
reasoning_0 -> reasoning_1 -> reasoning_2
```

The safe initial model is one immutable baseline-to-candidate transaction. An
orchestrator may invoke that transaction again, passing an adopted candidate as
the next baseline.

Native recursive refinement should wait for an explicit recurrence construct,
for example a future `carry` binding that connects the selected successor of
iteration `i` to the baseline of iteration `i+1`. This is an ERFL 0.4 design
candidate, not a reinterpretation of indentation or ordinary handle reuse.

## Catalogue Consequence

The conceptual catalogue and operational crosswalk should be generated as two
documents:

1. `ALL_REASONING_FLOWS.md` contains only epistemic profiles, typed subjects,
   authority ceilings, and explanations.
2. `REASONING_FLOW_MATERIALIZATIONS.md` maps occurrences to current skills,
   hooks, actions, and operational loops.

This preserves the useful one-to-many materialization map while ensuring that
the reasoning language remains meaningful if implementations are renamed,
split, merged, or replaced.

## Recommended Adoption Sequence

1. Make higher-order subjects and non-coercions normative.
2. Replace the incomplete trajectory-reflection profile with an explicit
   baseline/delta/candidate/evidence/decision profile.
3. Make generic subject types machine-checkable.
4. Add immutable revision, evaluation, and adoption records.
5. Separate semantic flow documentation from operational materializations.
6. Classify every meta-capability by subject, function, authority, independence,
   persistence, and rollback support.
7. Add meta-circularity, stale-evidence, and paired-trial adversarial tests.
8. Pilot one one-step reasoning refinement before designing recursive carry.

The self-contained backlog for this sequence is
[`meta_skills/todos/reflective_refinement_todos.yaml`](../../meta_skills/todos/reflective_refinement_todos.yaml).
