<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Explain how concrete Mathformer skills materialize more essential forms of
  reasoning and how several skills compose into a reasoning style.

Intent:
  Introduce an epistemic classification axis that is independent of backend,
  domain, workflow phase, and implementation mechanism.

Function:
  Documents the initial ontology and the machine-readable mapping in
  skills/REASONING_TYPES.yaml.

Maintenance Notes:
  Treat this as a revisable framework hypothesis. Keep examples grounded in
  skill contracts and preserve distinctions between proposals, evidence,
  criticism, repair, and acceptance.
-->

# Epistemic Reasoning Types

Mathformer skills are executable materializations of reasoning, but skill names
are not themselves a theory of reasoning. Many names describe a backend, domain,
workflow phase, artifact, or control role. The initial mapping therefore uses
two levels:

```text
epistemic primitive <- realized by -- skill application
        |                                  |
        +---- composed into a reasoning style ----+
```

An epistemic primitive is a small, backend-independent operation. A reasoning
style is an ordered, branching, or looping composition of skill applications.
This produces a many-to-many graph:

- one reasoning style contains one or more skills;
- one skill may participate in several styles;
- a composite skill or orchestrator may contain nested styles;
- the same skill may play a different epistemic role in a different context.

The initial machine-readable model is
[`skills/REASONING_TYPES.yaml`](../../skills/REASONING_TYPES.yaml). Its nine
style compositions remain an initial seed, while its `skill_bindings` section
classifies all 187 canonical skills.

Typed compositions are expressed in the
[Epistemic Reasoning Flow Language](REASONING_FLOW_LANGUAGE.md). ERFL keeps
operation type, relation, output semantics, skill implementation, and runtime
execution as separate layers.

The corresponding classification of what those reasoning operations produce is
documented in [epistemic output types](OUTPUT_TYPES.md) and
[`skills/OUTPUT_TYPES.yaml`](../../skills/OUTPUT_TYPES.yaml).

This complements the existing operational `reasoning_types` coordinate in
[`workflow_taxonomy.json`](../../meta_skills/taxonomy/workflow_taxonomy.json).
Labels there, such as `autoformalization`, `pathology_repair`, and
`runtime_observability`, identify workflow families. The primitives here state
which epistemic operations occur inside those families.

## Essential Primitives

| ID | Primitive | Governing question |
| --- | --- | --- |
| E1 | Source observation | What does the source explicitly contain? |
| E2 | Structural decomposition | What are the units, dependencies, binders, and internal shape? |
| E3 | Semantic modeling | What objects, meanings, assumptions, domains, and contexts are intended? |
| E4 | Retrieval | Which existing facts, APIs, declarations, or precedents may be relevant? |
| E5 | Grounding and alignment | Which retrieved object is actually applicable and meaning-preserving here? |
| E6 | Abductive completion | Which missing premise, law, bridge, or plan could complete the gap? |
| E7 | Constructive formalization | How can the intended object be synthesized in a formal representation? |
| E8 | Deduction and transformation | What follows under the declared premises and accepted rules? |
| E9 | Probing and falsification | What happens under execution, bounded samples, or adversarial probes? |
| E10 | Critical verification | Is the artifact adequate along a named independent criterion? |
| E11 | Diagnostic revision | Why did it fail, and which localized change can repair it? |
| E12 | Comparative reflection | What is learned by comparing artifacts, explanations, or trajectories? |
| E13 | Epistemic governance | Which reasoning runs next, when should it stop, and what status is warranted? |
| E14 | Inductive generalization | Which scoped pattern is provisionally supported across the observed cases? |
| E15 | Analogical transfer | Which structure can be transported through an explicit correspondence? |
| E16 | Contrastive/counterfactual reasoning | What changes under a controlled alternative or relevant contrast? |

These are epistemic functions, not mutually exclusive bins. For example,
`mathlib-candidate-verifier` primarily grounds a retrieved declaration but also
performs a scoped verification. `vampire-atp-orchestrator` spans formal
representation, deduction, execution, and proof-evidence packaging. Its use in
a style must therefore be annotated at the application level.

## Orthogonal Axes

The following properties should remain separate from the primitive type:

- **backend:** Lean, Isabelle, Rocq, Vampire, SymPy, knowledge base, or neutral;
- **domain:** mathematics, physics, or framework control;
- **inference form:** deduction, abduction, induction, analogy, contrast,
  model-based reasoning, symbolic computation, numerical sampling, or
  hermeneutic interpretation;
- **implementation:** deterministic, generative, or hybrid;
- **workflow phase:** intake, drafting, execution, critique, repair, acceptance,
  or reflection;
- **infrastructure role:** orchestrator, recorder, explainer, curator, reporter,
  or compatibility wrapper.

This prevents labels such as “Lean reasoning,” “critic reasoning,” or “final
review” from hiding the actual epistemic operation.

## Initial Style-to-Skill Mapping

The mapping below summarizes the first nine compositions in the registry. The
listed skills are representative choices at each stage, not mandatory linear
pipelines.

| Reasoning style | Primitive composition | Representative skill materializations |
| --- | --- | --- |
| Source-grounded autoformalization | E1 -> E2 -> E3 -> E6 -> E4 -> E5 -> E7 -> E9 -> E10 -> E11 -> E13 | `source-formalizable-unit-extractor`, `source-line-translation-packet-builder`, proof/LaTeX expansion skills, `mathlib-concept-candidate-mapper`, `mathlib-candidate-verifier`, backend drafter and runner skills, `lean-critique-suite-orchestrator`, `lean-formal-refinement`, `gate-policy-controller` |
| Premise retrieval and verified reuse | (E2 & E1) -> E4 -> E5 -> E10 -> E13 | `mathlib-term-expansion-annotator`, `premise-kb-indexer`, mathlib navigation skills, `mathlib-candidate-verifier`, `mathlib-result-existence-checker`, `result-existence-precheck-orchestrator` |
| Formal proof discovery | E3 -> E4 -> E7 -> E8 -> E9 -> E10 -> E12 | `vampire-atp-orchestrator`, Lean/Rocq drafters and runners, logical and non-vacuity critics, `vampire-proof-informalizer`, `lean-informalization-extractor` |
| Executable symbolic derivation | E1 -> E3 -> E5 -> E7 -> E8 -> E9 -> E10 | SymPy parser, assumption, API-grounding, drafting, identity, trace, counterexample, execution, and consistency skills |
| Physics derivation reconstruction | E1 -> E2 -> E3 -> E6 -> E5 -> E8 -> E9 -> E10 | physics source extraction, equation parsing, symbol/dimension/frame/regime modeling, gap detection, law/unit grounding, step verification, numeric probing, and final review skills |
| Adversarial validation | E9 -> E10 -> E13 | counterexample and numeric samplers, generative critics, Lean critique passes, non-vacuity and realness checks, `gate-policy-controller` |
| Critic-driven recursive repair | E10 -> E11 -> E6 -> E7 -> E13 -> loop | critique suites, execution interpreters, refinement routers, repair cartographers, generative repairers, and recursive loop controllers |
| Theory/library curation | E4 -> E5 -> E10 -> E11 -> E7 -> E13 | MathformerLib registry and promotion skills plus MathformerPhysicsLib inventory, canonicalization, grounding, coherence, repair, foundation, and gate skills |
| Trajectory reflection and process improvement | E12 -> E11 -> E7 -> E9 -> E12 -> E10 -> E13 | reference-free evaluators, comparison reporters, `autoformalization-reflective-refinement-loop`, skill tests, hook/contract validators, and gate control |

## Trust Is A Vector

A single `verified: true` flag would collapse distinctions that the framework
depends on. The mapping instead treats epistemic state as a vector whose
dimensions can change independently:

```yaml
provenance: source_linked
retrieval_status: locally_verified
executability: passed
formal_validity: proof_checked
semantic_fidelity: passed
nonvacuity: passed
domain_validity: unchecked
promotion_status: formal_candidate
```

This captures cases such as a Lean declaration that compiles but is semantically
misaligned, a SymPy identity that passes samples but lacks universal proof, or a
retrieved declaration that exists but does not match the intended source
concept.

## Important Non-Equivalences

- Retrieval rank is not declaration validity or applicability.
- Generation is not proof.
- Compilation is not semantic fidelity, non-vacuity, or physical correctness.
- Symbolic calculation is not automatically theorem proving.
- Failure to find a counterexample is not positive proof.
- Criticism localizes risk; it does not certify truth by itself.
- Repair invalidates affected checks until the revised artifact is re-run.
- A gate summarizes evidence; it does not create mathematical evidence.
- A report or informal explanation is not a substitute for its authoritative
  formal artifact.

## Exhaustive Skill Bindings

Every canonical skill, including compatibility wrappers and epistemic
infrastructure, now has exactly one primary primitive and zero or more unique
secondary primitives. The primary distribution is:

| Primary primitive | Skills |
| --- | ---: |
| Source observation | 7 |
| Structural decomposition | 9 |
| Semantic modeling | 17 |
| Retrieval | 12 |
| Grounding and alignment | 12 |
| Abductive completion | 5 |
| Constructive formalization | 9 |
| Deduction and transformation | 2 |
| Probing and falsification | 14 |
| Critical verification | 45 |
| Diagnostic revision | 11 |
| Comparative reflection | 9 |
| Epistemic governance | 35 |
| Inductive generalization | 0 |
| Analogical transfer | 0 |
| Contrastive/counterfactual reasoning | 0 |
| **Total** | **187** |

The low deductive count is deliberate. Lean, Isabelle, and Rocq drafting skills
construct proof candidates, while their execution skills probe a kernel or
compiler. They are not classified as deductive merely because their artifacts
contain proofs. `vampire-atp-orchestrator` and `sympy-identity-validator` have
deduction/transformation as their dominant output.

Each registry entry follows this binding shape:

```yaml
skill: lean-semantic-preservation-critic
kind: atomic
primary_primitive: critical_verification
supporting_primitives:
  - grounding_alignment
role: verifier
backend: lean
domain: mathematics
implementation: generative
consumes_state:
  semantic_fidelity: unchecked
produces_state:
  semantic_fidelity: passed_or_at_risk
evidence_kind: source_to_formal_alignment_report
```

Bindings are justified from each `SKILL.md`, not inferred solely from the skill
name. Coverage checks should reject unknown primitive ids, missing or extra
skill directories, duplicate secondary primitives, a primary repeated as a
secondary, invalid trust transitions, and styles with no executable
materialization.
