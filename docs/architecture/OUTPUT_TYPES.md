<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Explain what Mathformer skill outputs epistemically are, independently of
  file formats, backends, workflow phases, and lifecycle statuses.

Intent:
  Define a typed output-and-warrant graph for downstream use, promotion,
  invalidation, and human interpretation.

Function:
  Documents the ontology in skills/OUTPUT_TYPES.yaml and relates it to
  reasoning primitives, trust states, hook outputs, and reasoning logs.

Maintenance Notes:
  Keep output kinds separate from containers and representations. A report,
  packet, JSON file, or Lean file receives no authority from its name alone.
-->

# Epistemic Output Types

Mathformer outputs are typed nodes in a provenance-and-warrant graph. Their
type says what epistemic function they perform. It does not say how they are
serialized, whether they are accepted, or which backend produced them.

Five dimensions must remain separate:

```text
output type       what the output epistemically is
semantic kind     claim, evidence, model, relation, assessment, decision, and so on
container role    packet, report, plan, ledger, manifest, bundle, or trace
representation    JSON, HTML, Lean, TSTP, Python, CSV, SVG, and so on
trust/lifecycle   candidate, executed, checked, blocked, accepted, superseded
```

This matters operationally. The 199 current hook contracts declare 325 output
labels, 320 distinct. Among them, 82 contain `report`, 36 contain `packet`, and
31 contain `plan`. Those suffixes describe containers, not uniform epistemic
kinds.

The machine-readable draft is
[`skills/OUTPUT_TYPES.yaml`](../../skills/OUTPUT_TYPES.yaml). It complements
[epistemic reasoning types](EPISTEMIC_REASONING_TYPES.md): reasoning types
classify operations; output types classify the nodes those operations produce.
The execution and specification form of the producing capability is classified
separately in [skill types](SKILL_TYPES.md).
Typed occurrences exchange these semantic objects through the
[Epistemic Reasoning Flow Language](REASONING_FLOW_LANGUAGE.md).

## Semantic Kinds

Output type describes workflow function; semantic kind describes the internal
epistemic object. The kinds are:

| Kind | Meaning |
| --- | --- |
| `Claim` | A proposition capable of truth or falsity |
| `Evidence` | An inspectable item bearing on a claim through a typed relation |
| `Model` | An explicit formal, symbolic, semantic, numerical, or idealized representation |
| `Relation` | A typed connection among immutable output identities |
| `Assessment` | A criterion-scoped evaluation |
| `Decision` | A calibration or operational disposition that creates no object-level evidence |
| `Obligation` | A condition remaining before a named use or promotion |
| `Plan` | Prospective bounded reasoning or action |
| `Presentation` | A communicative projection over authoritative sources |
| `Bundle` | A product, collection, alternative, context, or handoff |
| `Blocker` | A current inability to proceed, not falsity or impossibility |

For example, a `derivation_certificate` is normally a `Bundle` containing a
conditional `Claim`, proof `Evidence`, indispensable-premise `Relation`s, and
possibly open `Obligation`s. Calling the file a report does not change any of
those semantics.

## Core Warrant Path

```text
source observation / model
              |
              v
     candidate artifact
              |
              v
 atomic evidence or certificate
              |
              v
 criterion-scoped assessment
              |
              v
 policy-bound decision
```

Plans, repair specifications, explanations, indexes, traces, and blockers sit
alongside this path. They may control or clarify it, but they cannot substitute
for missing evidence nodes.

## Output Families And Types

| Family | Output types | Central boundary |
| --- | --- | --- |
| Descriptive | `source_observation_packet`, `structural_model`, `semantic_context_model` | Records or models what is present without proving truth or adequacy |
| Prospective | `retrieval_candidate_set`, `hypothesis_obligation_set`, `plan_directive`, `candidate_artifact` | Proposes candidates or future actions without establishing success |
| Evidential | `grounding_evidence_link`, `derivation_certificate`, `execution_evidence_record`, `counterexample_witness` | Bears on an exact claim under an explicit method and scope |
| Evaluative | `scoped_assessment`, `aggregate_synthesis`, `decision_record` | Assesses evidence or changes permission under a named policy |
| Revisionary | `diagnosis_repair_specification`, `revision_record` | Explains failure or records change without transferring stale validation |
| Communicative | `explanation` | Makes authoritative outputs understandable without replacing them |
| Memory | `index_registry`, `curated_knowledge_entry` | Preserves per-entry provenance and trust for later reuse |
| Operational | `provenance_trace`, `blocker_record` | Makes process lineage, failure, and recovery auditable |

Important leaf-type distinctions include:

- A source observation records what a source says, not whether it is true.
- A retrieval set claims relevance or storage presence, not applicability.
- A candidate artifact establishes only that a concrete proposal exists.
- A derivation certificate applies to the exact statement, dependencies,
  assumptions, rules, and checker recorded with it.
- Execution evidence records backend behavior, not semantic fidelity,
  non-vacuity, or domain correctness unless the backend checks those dimensions.
- One admissible aligned counterexample may refute a scoped universal claim;
  failure to find one is not proof.
- A scoped assessment cannot certify criteria it did not test.
- An aggregate cannot become more authoritative than its members.
- A decision changes workflow permission or status but creates no mathematical
  evidence.
- A blocker records current inability to proceed, not falsity or impossibility.

## Essential Properties

Every output needs an identity and exact subject. Evidence about a path becomes
unsafe if the file later changes, so evidence-bearing outputs bind to a content
digest rather than only a mutable path.

The common envelope records:

- output type and schema version;
- primary semantic kind and typed member identities;
- producing skill, hook, run, and skill-call identity;
- exact subject and subject digest;
- source anchors, input-output relations, and artifact hashes;
- epistemic scope and dimensions explicitly not checked;
- production method and logical force;
- checker, backend, environment, dependencies, and assumptions;
- polarity: supporting, refuting, mixed, or neutral;
- independence and reproducibility;
- namespaced process, validation, claim, decision, and promotion statuses;
- lifecycle, mutability, canonicality, and invalidation conditions;
- representations, risks, limitations, and next recoverable action.

The typology avoids a single confidence scalar. Named trust dimensions show
what is actually known:

```yaml
provenance: source_verified
retrieval_status: locally_verified
executability: passed
formal_validity: proof_checked
semantic_fidelity: unchecked
nonvacuity: unchecked
domain_validity: unchecked
promotion_status: formal_candidate
```

## Typed Relations

```text
observation_packet  --observes--> source
semantic_model      --represents--> domain or artifact
candidate_artifact  --proposes--> obligation
evidence_record     --supports/challenges--> claim
derivation_certificate --proves--> exact formal claim
counterexample      --refutes--> scoped claim
assessment          --assesses--> artifact or evidence
decision            --authorizes/rejects/routes--> transition
blocker             --blocks--> transition
repair_specification --repairs--> finding or artifact
explanation         --explains--> authoritative output
index_registry      --indexes/contains--> output
revision_record     --supersedes/invalidates--> prior output
```

An observation becomes evidence only after a relation names the target claim,
polarity, scope, and inference by which the observation bears on it.

## Reasoning-To-Output Defaults

| Reasoning primitive | Typical primary output |
| --- | --- |
| Source observation | `source_observation_packet` |
| Structural decomposition | `structural_model` |
| Semantic modeling | `semantic_context_model` |
| Retrieval | `retrieval_candidate_set` |
| Grounding and alignment | `grounding_evidence_link` |
| Abductive completion | `hypothesis_obligation_set` |
| Constructive formalization | `candidate_artifact` |
| Deduction and transformation | `derivation_certificate` |
| Probing and falsification | `execution_evidence_record`, possibly `counterexample_witness` |
| Critical verification | `scoped_assessment` |
| Diagnostic revision | `diagnosis_repair_specification` or `revision_record` |
| Comparative reflection | `aggregate_synthesis` or `explanation` |
| Epistemic governance | `decision_record`, `plan_directive`, or `blocker_record` |
| Inductive generalization | `candidate_artifact`, `execution_evidence_record`, and boundary obligations |
| Analogical transfer | `candidate_artifact`, `grounding_evidence_link`, and preservation obligations |
| Contrastive/counterfactual reasoning | `execution_evidence_record`, `scoped_assessment`, and boundary obligations |

This is a default mapping, not a fixed skill signature. One skill application
may emit several typed outputs, and a bundle preserves each member's type and
authority separately.

## Status And Authority Rules

1. Generic top-level `ok` or `status` is insufficient. Use independent process,
   validation, claim, decision, and promotion statuses.
2. `complete` means complete under a named gate profile and version for an exact
   subject digest, never globally complete.
3. Generated candidates and hypotheses remain advisory until named evidence and
   gates change their state.
4. Critics may raise risk or block under policy but cannot manufacture
   proof-checked validity.
5. A waiver changes permission, not the failed check, truth, or residual risk.
6. Aggregates cite atomic members by digest, preserve disagreements, distinguish
   required from advisory inputs, and inherit limitations.
7. A changed subject digest makes dependent evidence, assessments, and decisions
   stale until revalidated.
8. Human renderings and embedded copies name an immutable authoritative source.
   A mutable `latest` path is a pointer, not evidence identity.
9. Indexes and registries preserve trust per entry; storage cannot promote an
   output.
10. A blocker may be a successful governance output while the requested
    mathematical outcome remains incomplete.

## Concrete Acceptance Hazard

The typology exposes a current class of bug that surface names obscure: a
generative critic **plan** and a completed critic **report** are not
interchangeable. A plan is prospective control output; a completed report is a
scoped assessment. A consistency gate that treats plan presence as completed
critic evidence can reach `complete` without the critic having run.

The current physics-Lean consistency orchestrator demonstrates this hazard: its
required generative-critic styles admit either
`physics_lean_generative_critic_plan` or
`physics_lean_generative_critic_report`, a statusless plan becomes `present`,
and the self-test reaches `complete` with the plan alone. See
`skills/physics-lean/physics-lean-consistency-report-orchestrator/scripts/run_physics_lean_consistency_report.py`.

This document does not change those workflow implementations. It establishes
the invariant future validators should enforce: plans, prompts, queues, and
repair proposals cannot satisfy requirements for executed evidence or completed
assessment outputs.

## Next Refinement

The next layer is an exhaustive binding from every declared hook output label
to one primary output type, optional secondary types, container role,
materializations, trust dimensions affected, authoritative source, downstream
consumers, and freshness/invalidation rules.
