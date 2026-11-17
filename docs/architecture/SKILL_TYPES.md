<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Classify Mathformer skills without overloading deterministic, procedural,
  declarative, generative, orchestrator, or validator as one flat set of types.

Intent:
  Define a multi-axis skill taxonomy tied to reasoning functions, output types,
  authority boundaries, effects, and testing obligations.

Function:
  Documents the machine-readable taxonomy in skills/SKILL_TYPES.yaml and its
  relationship to the canonical skill-test inventory.

Maintenance Notes:
  Keep execution-posture counts synchronized with inventory_skills.py. A skill
  contract change may require reclassification even if its name does not change.
-->

# Skill Types

Skill type is not one hierarchy. The terms in common use answer different
questions:

```text
deterministic / generative / hybrid   how output is produced
procedural / declarative              how behavior is specified
atomic / orchestrator / router        how work is composed
script / prompt / backend adapter     how it is implemented
stateless / run-stateful / corpus     what state it depends on
proposal / evidence / decision        what authority its outputs may carry
```

The canonical classification is therefore a product of orthogonal axes. A
useful full label might be:

```text
hybrid + constraint-based + iterative-controller
+ artifact-stateful + decision-authority
```

The machine-readable taxonomy is
[`skills/SKILL_TYPES.yaml`](../../skills/SKILL_TYPES.yaml).

## 1. Execution Posture

This is the current test-program axis. The canonical inventory reports:

| Posture | Skills | Meaning |
| --- | ---: | --- |
| Deterministic | 150 | Semantic output is selected by declared code, rules, queries, or backend calls rather than open-ended model generation |
| Generative | 32 | Material semantic output depends on open-ended model or human generation |
| Hybrid | 5 | One skill boundary materially combines generative output with deterministic tools, validation, aggregation, or gates |
| Human-mediated | Reserved | A future profile for contracts requiring human authorization or judgment as a material step |

“Deterministic” is operational, not metaphysical. A deterministic skill can
still depend on backend versions, environment state, resource limits, solver
heuristics, or seeds. It also does not mean correct, source-faithful, or
proof-producing.

“Generative” does not mean unconstrained. A generative skill should have
recorded prompts and context, structural output requirements, semantic oracles,
forbidden overclaims, adversarial probes, and non-regression examples.

A hybrid skill must preserve the boundary. Deterministic evidence and
generative judgment remain separately identifiable rather than becoming one
undifferentiated `ok` result.

## 2. Specification Style

Procedural and declarative are specification styles, so either can occur within
any execution posture.

| Style | Governing question | Typical contract |
| --- | --- | --- |
| Procedural | Which ordered actions should run? | Algorithm, command sequence, control flow |
| Declarative | What state or relation should hold? | Mapping, schema, target state, invariant |
| Constraint-based | Which outputs are admissible? | Requirements, prohibitions, gates |
| Query-based | Which existing objects satisfy the need? | Search, ranking, navigation, filtering |
| Transformational | How should one representation become another? | Input-output mapping plus preservation obligations |
| Evaluative | How should an artifact be assessed? | Criteria, evidence, severity, verdict semantics |
| Compositional | How are subordinate skills coordinated? | Dependencies, branches, loops, handoffs |

A skill has one primary specification style and may have several secondary
styles. For example, `lean-execution-runner` is deterministic, procedural, and
constraint-based. `lean-autoformalization-drafter` is generative,
transformational, and constraint-based.

## 3. Composition Role

| Role | Responsibility |
| --- | --- |
| Atomic operator | One bounded transformation, query, check, or generation task |
| Sequential orchestrator | Orders subordinate skill applications |
| Branching router | Selects skills or actions from request or evidence state |
| Iterative controller | Controls repair loops, convergence, and stopping |
| Evidence aggregator | Combines typed evidence without creating atomic evidence |
| Adapter/wrapper | Preserves compatibility or translates interfaces |
| Meta-controller | Governs skills, hooks, tests, logs, taxonomies, or promotion |

An orchestrator does not inherit the authority of subordinate outputs. It may
produce a decision or aggregate, but a proof remains authoritative because of
its proof object and checker—not because an orchestrator included it.

## 4. Implementation, State, And Effects

Implementation surfaces include:

- prompt-only;
- script-only;
- prompt and script;
- backend adapter;
- registry/schema-driven;
- external-service adapter;
- documentation contract.

State models are `stateless`, `artifact_stateful`, `run_stateful`,
`corpus_stateful`, or `environment_stateful`.

Effect profiles are independent again:

- read-only;
- writes ephemeral artifacts;
- writes durable artifacts;
- mutates tracked repository files;
- mutates the environment;
- causes external side effects.

A deterministic installer and a deterministic validator have the same execution
posture but radically different effects and safety requirements.

## 5. Output Authority

Authority is constrained by the output typology, not inferred from posture.

| Authority profile | Typical output types |
| --- | --- |
| Proposal producer | Candidate sets, hypotheses, plans, candidate artifacts |
| Observation/evidence producer | Source observations, grounding links, certificates, execution records, counterexamples |
| Assessment producer | Scoped assessments and aggregates |
| Decision authority | Gate decisions and blocker records |
| Revision authority | Diagnoses, repair specifications, revision records, revised candidates |
| Memory/explanation producer | Explanations, indexes, curated entries, provenance traces |

Thus:

- deterministic does not imply evidence-producing;
- generative does not imply proposal-only—a generative critic may produce a
  scoped assessment, but its authority ceiling remains criterion- and
  evidence-bound;
- hybrid does not imply stronger authority than either component;
- a decision-producing skill authorizes workflow use but does not create new
  mathematical evidence.

## 6. Composite Archetypes

The axes combine into familiar working types:

| Archetype | Representative skills |
| --- | --- |
| Deterministic procedural transformer | `source-formalizable-unit-extractor`, `sympy-expression-parser` |
| Deterministic declarative validator | `workflow-contract-validator`, `lean-nonvacuity-consistency-checker` |
| Deterministic reasoning-flow validator | `reasoning-flow-language` |
| Deterministic query/retriever | `mathlib-hierarchy-navigator`, `mathlib-result-existence-checker` |
| Deterministic backend executor | Lean, Isabelle, Rocq, and SymPy execution runners |
| Deterministic evidence aggregator | Lean/SymPy consistency orchestrators, RFDE evaluator |
| Deterministic policy controller | `gate-policy-controller`, promotion and log-schema guardians |
| Generative constructor | Lean/backends/isabelle/Isabelle/Rocq drafters, prerequisite expander |
| Generative interpreter/rewriter | `lean-output-denoiser`, `proof-expansion-web-researcher` |
| Generative critic | semantic, logical, mathlib, or LaTeX completeness critics |
| Generative planner | workflow and review orchestrators |
| Generative reflector | reflective refinement and refinement-taxonomy skills |
| Hybrid generate-then-verify | `lean-line-annotation`, `physics-lean-physical-semantics-critic` |
| Hybrid tool-augmented critic | physics generative critic and FormalPhysics synthesis orchestrators |
| Hybrid critic/repair router | `physics-lean-review-refinement-router` |

These are convenience labels, not replacements for the underlying axes.

## 7. Classification Contract

Each skill classification should eventually record:

```yaml
skill: lean-semantic-preservation-critic
execution_posture: generative
primary_specification_style: evaluative
secondary_specification_styles: [constraint_based, transformational]
composition_role: atomic_operator
implementation_surfaces: [prompt_only]
state_model: artifact_stateful
effect_profile: read_only
authority_profile: assessment_producer
primary_reasoning_type: critical_verification
primary_output_types: [scoped_assessment]
testing_obligations:
  - adversarial_content_probe
  - forbidden_overclaim_check
classification_evidence:
  - skills/lean/lean-semantic-preservation-critic/SKILL.md
```

## 8. Testing Consequences

| Posture | Required testing |
| --- | --- |
| Deterministic | Compile/parse, schemas, fixed fixtures, environment capture |
| Generative | Prompt/context capture, adversarial content probes, required and forbidden claim oracles, non-regression cases |
| Hybrid | Both profiles plus handoff, provenance, authority-boundary, and stale-evidence tests |
| Human-mediated | Reviewer/scope records, decision provenance, unresolved-handoff behavior |

Specification style adds further tests. Declarative and constraint-based skills
need schema and invariant coverage. Procedural skills need branch, failure, and
idempotence tests. Query skills need relevance and false-positive fixtures.
Transformational skills need preservation checks. Compositional skills need
ordering, missing-input, and loop-termination tests.

## 9. Relation To The Other Taxonomies

The three framework layers now answer different questions:

| Layer | Question |
| --- | --- |
| [Reasoning types](EPISTEMIC_REASONING_TYPES.md) | What epistemic operation does the skill perform? |
| [Output types](OUTPUT_TYPES.md) | What epistemic object does the application produce? |
| Skill types | How is the capability specified, executed, composed, implemented, and tested? |
| [Reasoning flows](REASONING_FLOW_LANGUAGE.md) | How do typed occurrences exchange and conserve epistemic state? |

No layer can be derived safely from another. A deterministic skill may perform
retrieval, deduction, probing, verification, or governance; all may produce
different output types and authority levels.
