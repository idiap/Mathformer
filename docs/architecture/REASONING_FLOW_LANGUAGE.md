<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Give Mathformer a compact language for expressing how typed epistemic
  operations compose without confusing that composition with execution order.

Intent:
  Consolidate the supplied ERFL 0.2 proposal with Mathformer's reasoning,
  output, skill, trust, and workflow-control taxonomies.

Function:
  Defines the Mathformer ERFL 0.3 profile, its semantic layers, migration rules,
  grammar, coherence invariants, examples, and validation boundary.

Maintenance Notes:
  Keep this aligned with the reasoning-flow-language skill and the reasoning
  and output registries. A valid projection is never evidence of execution or
  object-level truth.
-->

# Epistemic Reasoning Flow Language

Mathformer ERFL 0.3 describes epistemic dependency: which reasoning occurrence
consumes which epistemic handles, what it produces, and which relation licenses
the transition. It deliberately abstracts away agents, skills, tools, runtime
scheduling, and presentation. A separate resource plane may name an accessible
file-backed KB, search surface, or store, but its arrows never carry warrant.

The language occupies a fourth framework layer:

| Layer | Question |
| --- | --- |
| [Reasoning types](EPISTEMIC_REASONING_TYPES.md) | Which epistemic operation occurs? |
| [Output types](OUTPUT_TYPES.md) | Which epistemic object and workflow role result? |
| [Skill types](SKILL_TYPES.md) | How is the capability specified, executed, composed, and tested? |
| Reasoning flows | How do typed occurrences exchange warrant-bearing state? |

ERFL does not replace `skills/SKILL_HOOKS.yaml`. Hooks control operational
execution and evidence collection; ERFL states the epistemic projection that
such execution is intended to materialize.

The machine-readable semantics are in
[`erfl-0.3.json`](../../skills/control/reasoning-flow-language/references/erfl-0.3.json),
the deterministic validator is owned by the
[`reasoning-flow-language`](../../skills/control/reasoning-flow-language/SKILL.md)
skill, and the nine current reasoning-style profiles live under
[`examples/reasoning_flows`](../../examples/reasoning_flows/).
The generated [all-reasoning-flows reference](ALL_REASONING_FLOWS.md) collects
every profile's exact source and statement-by-statement epistemic
interpretation. Candidate skill materializations and affinities with controlled
repository loops live in the separate generated
[reasoning-flow materializations](REASONING_FLOW_MATERIALIZATIONS.md)
cross-reference.

## Reference Baseline and Adaptation Policy

ERFL 0.3 follows the supplied `reasoning-flow-language-markdown.zip` reference
as its upstream semantic baseline. The exact archive and the five incorporated
Markdown members are identified by SHA-256 digest in `reference_alignment` in
[`erfl-0.3.json`](../../skills/control/reasoning-flow-language/references/erfl-0.3.json).
This makes “follow the reference” testable even though the source archive lives
outside the repository.

The later user-supplied all-reasoning-flows document is the surface-syntax
reference for `reasoning`, `steps`, trailing `...`, `@KB` connections,
directional resource arrows, and generated `map` projections. Its SHA-256
digest is recorded under `surface_syntax.source_sha256` in the same registry.

The adaptation is conservative where Mathformer needs no additional
distinction and explicit where it does:

| ERFL 0.2 construct | Mathformer ERFL 0.3 treatment | Reason |
| --- | --- | --- |
| `D`, `A`, `I`, `T`, `C`, `E` | Retained | Their epistemic roles and authority boundaries already fit the framework. |
| `M` | Refined into `M` then `P` when execution is involved | Constructing a model and probing it are different epistemic acts. |
| `R` | Refined into `P` then `R` when evidence must first be produced | Search or execution evidence must remain distinct from the verdict formed from it. |
| `O`, `S`, `Q`, `G`, `F`, `X`, `L` | Mathformer extensions | Source intake, decomposition, retrieval, grounding, construction, revision, and reflective comparison must not disappear into anonymous gaps. |
| Core relations and combinators | Retained | Labelled sequence, alternatives, parallel products, optionality, bounded repetition, handlers, switches, gaps, and relational coherence remain the normative core. |
| Reference output constructors | Adapted to `handle::Root<Subject>` ports | Stable handle identity is separated from semantic kind; `Bundle` represents products, alternatives, and collections while preserving member identities. |

The reference's semantic boundary is also normative: an ERFL graph describes
reasoning occurrences and warrant-bearing dependencies, not agents, skills,
tools, schedules, storage effects, or proof that an execution occurred. Any
Mathformer extension must declare an authority ceiling, preserve the 0.2
coherence invariants, and remain distinguishable from operational
materialization.

## Consolidated Ontology

The imported ERFL proposal and the existing Mathformer ontology classify
different granularities. ERFL 0.2 supplied eight warrant-oriented types;
Mathformer supplied thirteen workflow-independent operations. Neither can be
reduced to the other without losing information:

- induction, analogy, and counterfactual reasoning were missing as explicit
  Mathformer primitives;
- observation, decomposition, retrieval, grounding, formal construction,
  diagnosis, and reflection were absent from the compact language and appeared
  as `_` gaps;
- model construction and model-based probing were collapsed into `M`;
- evidence production and critical verdict formation were collapsed into `R`.

ERFL 0.3 therefore uses sixteen atomic occurrence codes:

| Code | Mathformer primitive | Authority ceiling |
| --- | --- | --- |
| `O` | Source observation | What the inspected source contains |
| `S` | Structural decomposition | Structure under the chosen decomposition |
| `M` | Semantic modeling | Explicit model, not model adequacy |
| `Q` | Retrieval | Candidate relevance or presence |
| `G` | Grounding and alignment | Scope-bound applicability or preservation |
| `A` | Abductive completion | Candidate explanation or premise |
| `I` | Inductive generalization | Scoped provisional generalization |
| `T` | Analogical transfer | Candidate transfer under a correspondence |
| `F` | Constructive formalization | Candidate formal or executable artifact |
| `D` | Deduction and transformation | Entailed under recorded premises and rules |
| `C` | Contrastive/counterfactual reasoning | Supported controlled contrast |
| `P` | Probing and falsification | Observed behavior or counterexample within scope |
| `R` | Critical verification | Criterion-scoped assessment or refutational verdict |
| `X` | Diagnostic revision | Diagnosis, repair proposal, or new revision |
| `L` | Comparative reflection | Scope-bound comparison or improvement hypothesis |
| `E` | Epistemic governance/calibration | Status or disposition; no substantive claim |

This preserves the imported `D`, `A`, `I`, `T`, `C`, and `E` meanings. ERFL 0.2
`M` migrates to `M -probe> P`; ERFL 0.2 `R` migrates to `P -test> R` when a
search or execution first produces evidence. `R` may stand alone only when the
evidence already exists and is named as an input.

The underscore type remains an explicit projection gap:

```text
pre:_[raw_context->candidate]
```

It preserves identity without inventing a reasoning type. A gap-bearing flow
is descriptive and cannot accept a result.

## Output Semantics

ERFL ports carry immutable epistemic handles, optionally annotated with a
semantic kind:

```text
artifact::Bundle
claim::Claim
evidence::Evidence
assessment::Assessment
status::Decision
```

The semantic kind describes the object inside an output. The output type in
`skills/OUTPUT_TYPES.yaml` describes its workflow function. The container role
and representation remain separate again:

```text
semantic kind  ×  output function  ×  container  ×  representation  ×  trust state
Claim             candidate_artifact packet       JSON              generated
Evidence          derivation_certificate report   TSTP              proof_checked
Decision          decision_record       ledger    JSON              accepted_for_scope
```

The eleven semantic kinds are `Claim`, `Evidence`, `Model`, `Relation`,
`Assessment`, `Decision`, `Obligation`, `Plan`, `Presentation`, `Bundle`, and
`Blocker`. Interface-only roots such as `Context`, `Scope`, `Constraint`,
`Delta`, `Goal`, and `Unavailable` may occur at boundaries but do not acquire
scientific authority merely by being transported.

## Syntax

A minimal reasoning program is:

```erfl
erfl 0.3
reasoning adversarial_validation {
  goal "produce a calibrated adversarial verdict" -> validation_status
  steps
    p:P[target::Claim,scope::Scope->probe_evidence::Evidence] -assess> ...
    r:R[
      target::Claim,
      probe_evidence::Evidence
      -> assessment::Assessment
    ] -calibrate> ...
    e:E[
      target::Claim,
      assessment::Assessment
      -> validation_status::Decision
    ]
  on e.refuted => stop
  on e.not_refuted_within_scope => accept
}
```

The core grammar is:

```text
document   := "erfl 0.3" resource_binding* reasoning
reasoning  := "reasoning" ID "{" goal steps repeat* resource_edge* handler+ "}"
goal       := "goal" STRING "->" HANDLE
steps      := "steps" expression
repeat     := "repeat" INT ".." INT "[" expression "]"
              "until" predicate "measure" ID
resource_binding := "@" RESOURCE_CLASS ALIAS
                    "connect(file(" STRING "))"
resource_edge := ALIAS "<-" READ_MODE "-" ALIAS
               | ALIAS "-" WRITE_MODE "->" ALIAS
handler    := "on" predicate "=>" ("stop" | "accept" | "switch @" ID)
expression := sequence
sequence   := choice (RELATION choice)*
choice     := parallel ("|" parallel)*
parallel   := atom ("&" atom)*
atom       := [ALIAS ":"] TYPE "[" ports "->" ports "]" ["?"]
            | "(" expression ")"
port       := HANDLE ["::" SEMANTIC_KIND]
predicate  := (ALIAS | "reasoning") "." STATUS
RESOURCE_CLASS := "KB" | "SEARCH" | "STORE"
READ_MODE  := "read" | "lookup" | "query" | "search" | "snapshot"
WRITE_MODE := "persist" | "append" | "put" | "upsert" | "checkpoint"
              | "invalidate" | "promote" | "commit"
map        := "map" ID "{" map_entry* "}"
map_entry  := "reasoning::" ID "-" relation_list ">"
              "output::" ID "." HANDLE output_transition*
```

`map` is a derived whole-system projection, not an executable reasoning
program. It collapses a program to its relation signature and named output.
Cross-program transitions may be shown only when an explicit semantic handoff
is registered; shared skills, similarly named handles, or operational-loop
overlap are insufficient.

### Multiline layout

Each top-level `goal`, `steps`, `repeat`, resource edge, and `on` statement begins on a new
physical line. Within that logical statement, further line breaks and all
indentation are presentation only: the parser coalesces the physical lines
before applying the grammar. Delimiters, relation labels, branch operators,
ports, and predicates remain semantic; indentation never creates a sequence,
branch, scope, or warrant relation.

A trailing `...` says that the same logical statement continues on the next
physical line. It has no epistemic meaning. This makes long chains readable
without assigning semantics to indentation.

The preferred layout for a long chain is:

- put `steps` on its own line;
- put the initial occurrence on the next line;
- end each continued segment with its relation and `...`, such as
  `artifact -test> ...`, then put the next occurrence on the following line;
- indent the members of `(...)` and prefix later branches with `&` or `|`;
- when an occurrence interface is long, open `TYPE[` on one line, list input
  ports below it, and place `-> output` on its own line;
- align `]` or `)` with the construct that opened it;
- keep the repeat predicate and progress measure on the closing `]` line when
  they fit.

For example, the bounded repair chain is written as:

```erfl
repeat 1..4 [
  x:X[artifact::Bundle,assessment::Assessment->repair::Plan] -revise> ...
  f:F[
    artifact::Bundle,
    repair::Plan
    -> revised_artifact::Bundle
  ] -test> ...
  p:P[revised_artifact::Bundle->revised_evidence::Evidence] -assess> ...
  r2:R[
    revised_artifact::Bundle,
    revised_evidence::Evidence
    -> revised_assessment::Assessment
  ] -calibrate> ...
  e2:E[
    revised_artifact::Bundle,
    revised_assessment::Assessment
    -> iteration_status::Decision
  ]
] until e2.accepted measure unresolved_findings
```

The compact single-line spelling remains valid and has exactly the same
meaning. Tokens such as `alias:TYPE`, `-relation>`, and `handle::Kind` should
not themselves be split across lines.

### Knowledge, search, and persistence

The attached reference syntax is adopted directly for accessible resources:

```erfl
erfl 0.3
@KB kb0 connect(file("MathformerKB"))
reasoning kb_grounded_route {
  goal "calibrate a KB-grounded route" -> reviewed
  steps
    o:O[kb0,source::Context->ground::Evidence] -constrain> ...
    a:A[ground::Evidence->candidate::Claim] -test> ...
    r:R[candidate::Claim->verdict::Assessment] -calibrate> ...
    e:E[candidate::Claim,verdict::Assessment->reviewed::Decision]
  o <-query- kb0
  e -persist-> kb0
  on e.reviewed => accept
}
```

`@KB`, `@SEARCH`, and `@STORE` bind resource aliases before the reasoning
block. An inverted arrow declares consumption by an occurrence; a forward
write arrow declares a possible externally executed effect. Neither arrow is a
reasoning relation, participates in step sequencing, or supplies warrant.
Reads must name the resource alias in the occurrence inputs. Writes must be
authorized by an `E` occurrence. Actual access and persistence remain subject
to versioned receipts, immutable successor identities, and external policy.
File targets must be repository-relative: absolute paths, parent traversal,
and network endpoints are rejected.

`A | B` is a tagged alternative and both branches must expose the same output
interface. `A & B` is a product: both epistemic contributions are required.
Optional occurrences use `?`. Iteration is finite and requires an observable
measure; replaying the same output does not count as epistemic progress.

## Relations

Relations say why the output of one occurrence may enter another. The core set
is:

- support and transport: `requires`, `preserve`;
- intake and representation: `observe`, `decompose`, `model`;
- knowledge use: `retrieve`, `ground`, `assume`;
- inference and construction: `generalize`, `transfer`, `construct`, `derive`;
- inquiry and evaluation: `compare`, `probe`, `test`, `assess`, `calibrate`;
- control and change: `constrain`, `revise`.

`requires` supplies no warrant. The legacy unlabelled `>` edge is rejected
because dependency alone cannot say whether a candidate was assumed, tested,
grounded, or merely transported.

## Relational Coherence

The validator enforces the properties that can be checked from a projection:

1. Every transition names a registered relation and conserves at least one
   handle.
2. Reused handles preserve their declared semantic kind.
3. Relations target compatible operation types.
4. Alternative branches expose an identical output interface; every branch of
   a parallel product contributes at least one conserved handle to its join.
5. The goal handle is produced by the steps expression's terminal `E` occurrence.
6. Every steps expression and repeat body terminates in `E`.
7. Acceptance and workflow switches are guarded by `E`; a reasoning-level predicate
   may only stop.
8. Iteration is bounded, calibrated, and carries a named progress measure.
9. A flow containing `_` cannot accept.
10. Every resource alias resolves uniquely; inverted reads are consumed
    explicitly, `SEARCH` is read-only, and persistence is authorized by `E`.

Runtime projections must additionally conserve exact output identities,
digests, scope, provenance, taints, claim ceilings, and open obligations. Those
properties belong in bound output records and reasoning logs, not merely in
port names.

## Epistemic Non-Coercions

- Deduction from an abductive candidate remains conditional on that candidate.
- A retrieved result is not grounded merely because it exists.
- A constructed artifact is not executed or verified merely because it parses.
- A model is not a probe, and a successful model run is not automatically
  evidence about the target system.
- Failure to find a counterexample is bounded nonrefutation, never proof.
- An assessment cannot certify criteria it did not inspect.
- Calibration may promote or block under policy but creates no object-level
  evidence.
- A valid ERFL profile proves neither that the projection is complete nor that
  its occurrences ran.

## Integration Boundary

The nineteen flows in the supplied ERFL reference were not copied into the
Mathformer workflow catalog. They refer to foreign workflow registries, and
several intentionally contain unresolved `_` regions. Their language semantics
were consolidated; their operational identities were not. Mathformer instead
ships one validated conceptual profile for each of its nine existing reasoning
styles.

Knowledge bases, search spaces, and persistence use an additional distinction
between epistemic steps and resource access. The implemented
[knowledge-resource extension](KNOWLEDGE_RESOURCES_IN_REASONING_FLOWS.md)
adopts `@KB`/`@SEARCH`/`@STORE`, inverted access arrows, and calibrated forward
persistence arrows in ERFL 0.3 without treating them as warrant-carrying step
edges.

Validate them with:

```bash
python skills/control/reasoning-flow-language/scripts/validate_reasoning_flow.py \
  examples/reasoning_flows/*.rflow \
  --strict --check-registries --json
```
