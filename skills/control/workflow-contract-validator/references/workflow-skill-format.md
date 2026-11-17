<!--
SPDX-FileCopyrightText: 2026 Idiap Research Institute
SPDX-License-Identifier: MIT
-->

# Workflow Skill v1: authoring and execution semantics

The normative structural contract is [workflow.schema.json](workflow.schema.json), JSON Schema Draft 2020-12. The helper validates descriptors and conservative dataflow semantics. This package is an authoring tool, not a workflow executor or an adapter implementation.

## Identity, sources and discovery

The canonical ID must match `^[a-z][a-z0-9_]*_workflow$`; `kind` is always `workflow`. Identity includes namespace and version. Explicit aliases map native hyphenated names, existing workflow IDs, or client-facing skill names to that identity. Keep native naming constraints intact. Classify the resolved canonical ID with the suffix rule; missing or inconsistent YAML is an error, not a fallback to an ordinary skill. Do not derive identities through punctuation replacement alone.

Use one descriptor per independently invocable workflow; multiple native operations can be declared in `operations`. A native CLI command need not be renamed when the canonical ID changes. Native workflow registries may project from the descriptor or reference it during adoption.

`provenance.sources` points to authoritative repository files, optionally with a selector and `sha256:` digest of the entire file. Paths are relative to the supplied repository root. Selectors are human-auditable source anchors; the helper does not interpret them. `coverage` is `complete`, `interface_only`, or `partial`. Incomplete coverage requires explicit gaps; complete coverage forbids gaps. Coverage is an author assertion that still requires source review. Preserve generated proofs, reports, receipts and historical run artifacts.

## Types and artifacts

`types` maps local type names to `{schema, representation?, media_type?}`. `schema` is an inline JSON Schema object/boolean or a relative local schema filename with an optional JSON Pointer fragment. Relative schema paths resolve from the descriptor directory; transitive file references resolve from the referring schema. Use `--repository-root` when schemas live elsewhere within the repository. No reference may escape that root, including through a symlink.

The helper supports Draft 2020-12, local `$ref`, and internal anchors/pointers. It never fetches remote schemas. External URI references, nested `$id`, `$dynamicRef`, inline references, and `$ref` siblings during field inspection are deliberately unsupported; report these limitations rather than weakening validation. Validity of a payload schema is checked even for unused types. JSON Schema assertion vocabularies are supported by jsonschema; `format` is annotation-only in this helper.

Type names are nominal at complete-port handoffs: two different named types are not interchangeable merely because their JSON shapes match. Use an explicit typed adapter operation for conversion. Field references require every parent schema to guarantee an object; nullable or unspecified parent types require an explicit narrowing adapter. Field references use conservative schema inspection. Arbitrary schema implication or subtyping is not claimed. Prefer named types and existing domain schemas over generic strings or unconstrained objects.

The schema describes an artifact's payload. `representation` distinguishes a value, file or directory; file paths are not substitutes for validating file payloads. A runtime adapter materializes and validates payloads and records their envelopes. Required artifact receipts should contain the type identity, representation, URI or value, content digest, producer run/step/attempt, provenance, validation receipts, scope, epistemic status, obligations and taints where relevant. Directories need a content manifest. This descriptor validator does not read scientific output payloads or attest to their existence.

Input and operation ports have `{type, required?}`; required defaults to true. Workflow and composite output ports have `{type, value}` and are required. Operation output optionality must propagate to consumers. Optional values require an `exists` guard before required consumption. Missing and null are different: null is permitted only by the payload schema.

## Operations and bindings

Operations declare inputs, outputs and `execution.mode`. A bound mode is `deterministic`, `generative`, `human`, or `mixed`; it requires a binding with `adapter`, `kind`, `target`, and `operation`, plus optional version/profile. Binding kinds are `skill`, `workflow`, `action`, or `tool`. Version pins the native target contract; a repository lockfile or environment profile should pin its implementation and dependencies. Do not execute arbitrary shell text from a descriptor. A command adapter resolves a registered target to argv through the repository's existing controller.

Use `specification_only` with a reason and no binding for missing implementations. These operations require draft lifecycle and an explicit coverage gap. Descriptor validity does not establish runtime readiness. `--require-declared-bindings` rejects such operations but cannot verify target availability, signatures, approvals or actual effects. Resolve those using repository-native tools and evidence before marking a workflow runnable. No binding adapter is supplied by this skill.

Optional `environment` references an existing repository runtime profile. Reuse Python/R locks, proof-engine toolchains, solver profiles, model manifests, and provider configuration. A Markdown dependency/license inventory is context, not an executable environment. `policy.secret_references` contains names and configuration locations only; never credential values.

## Expressions and scope

Expressions are exactly one of `{ref: path}`, `{literal: JSON}`, `{eq: [a, b]}`, `{all: [...]}`, `{any: [...]}`, `{not: expression}`, `{exists: {ref: path}}`. No Python evaluation, shell expansion, template interpolation or arbitrary code is allowed. Conditions must be boolean. Both operands of equality must be compatible. Boolean `all`/`any` operands are checked independently; do not use short-circuit evaluation to access an optional value. Use a gate or switch branch to establish presence first.

References use dot-separated identifiers, not arbitrary JSONPath. Schema fields outside this identifier vocabulary need a typed adapter. Available scopes are:

| Context | References |
| --- | --- |
| Everywhere | `inputs.<name>` and inherited visible values |
| Sequence | `steps.<earlier_id>.outputs.<port>` |
| Parallel exports | `branches.<name>.outputs.<port>` |
| Switch exports | `selected.outputs.<port>` |
| Loop body | `loop.state` |
| Loop transition, exit condition and exports | `loop.state`, `body.outputs.<port>` |
| Map body | `map.item` |
| Map exports | `items.outputs.<port>`: ordered arrays of body outputs |
| Workflow outputs | Visible root-sequence steps and `flow.outputs.<port>` |

Composite internals are lexical: a parent receives only declared child outputs. Root sequence outputs may refer directly to its completed steps. Forward references and sibling-branch dependencies are errors.

## Control nodes

Every node has `kind`, optional `id`, description and `on_failure`. Sequence children require unique IDs. Composite nodes export values through explicit typed `outputs`; call outputs come from the operation signature, and gates expose none.

- `call`: invoke the named operation with explicit typed arguments. An implementation can itself be a native workflow when its internal composition is not yet modeled; record interface-only coverage.
- `sequence`: run `steps` in order. A successful `exists` gate narrows presence for later steps. Terminal failure stops dependent execution.
- `parallel`: run named branches with positive `max_concurrency` and `join: all`. Branches cannot consume each other's outputs. Any required branch failure prevents a successful join. Race/any/quorum joins are not part of v1. Use isolated run artifacts and explicit merge operations for mutable results.
- `switch`: choose the first true case, otherwise the required default. Every body must expose identical output names, nominal types and optionality. An `exists` condition narrows presence in that case. Exports dereference `selected.outputs`.
- `map`: consume a statically typed array, validate `item_type`, execute the body with `map.item`, bound concurrency and collect each required body output in input order under `items.outputs`. Exports declare the corresponding array types. The static helper requires inspectable matching item schemas; use an explicit conversion for more complex unions.
- `loop`: validate `initial` against `state_type`; execute the body with that state at least once; evaluate `next_state` and `until` against the completed body outputs and the pre-transition `loop.state`; install the next state. Stop on true, otherwise repeat. `max_iterations` is positive and mandatory. On exhaustion use `blocked`, `budget_exhausted`, or `fail`; never silently accept the candidate. `loop.state` in exports denotes the final installed state; `body.outputs` denotes the last iteration. The helper verifies type consistency, not convergence or scientific progress.
- `gate`: evaluate a boolean condition and stop with `on_false` if false. A human approval is a distinct typed human operation/receipt, not a model-generated true value.
- `handoff`: invoke a workflow-bound operation with typed arguments and `continuation: deferred` or `automatic`. A deferred handoff yields a transfer record and suspends downstream execution until a matching external receipt supplies the declared outputs. Automatic continuation remains subject to existing invocation authority. The helper checks the declaration, not destination availability.

`on_failure` and `policy.failure.default` support `fail`, `blocked`, `quarantine`, and `needs_input`. Each terminates the current execution segment; quarantine additionally isolates affected artifacts. Runtime approval/invocation policy can impose narrower behavior. `retry.max_attempts` includes the first attempt. Extra attempts require enumerated `retryable_codes` and an adapter that establishes replay safety; absence of codes means no automatic retry. Refinement uses a loop with changed state rather than retrying an operation blindly.

## Effects, authority and receipts

Filesystem entries are logical mounts/resources resolved by the host, not unrestricted paths. Network entries and external writes name allowed services/capabilities. Empty arrays deny them. Operation-level effect and authority declarations narrow the workflow ceiling; omission inherits it. The helper checks literal containment, not runtime enforcement. The host must verify actual binding effects and isolate execution as required.

Allowed and forbidden actions are domain-specific identifiers. They must be disjoint. Workflows cannot grant themselves proof, publication, production mutation, clinical endorsement or human approval. Keep claim status, validation status, run status and approval status separate. `claim_ceiling` records a domain boundary; the helper cannot judge it scientifically.

Budgets include positive wall time and operation-call limits, optionally cost and currency. A host must also enforce cumulative child-workflow budgets and retry costs. Checkpoint resume requires matching definition and inputs; include resolved schemas, bindings, environments and relevant configuration digests in the runtime checkpoint. Receipts, artifact SHA-256 digests and provenance are mandatory; events record concise decisions and inspectable evidence, not hidden chain-of-thought.

Unknown core fields are rejected. `extensions` keys must be namespaced, for example `mathformer.backend`. Extensions hold metadata; execution semantics require a recognized host adapter/profile and must not override the core contract.

## Validation scope

Safe JSON-compatible YAML excludes duplicate/non-string keys, aliases, anchors, explicit tags, nonfinite numbers and non-JSON objects. Use lowercase `true`/`false`; YAML 1.1 words such as `on` remain strings. The CLI checks the schema against its meta-schema and checks its internal references with `--schema-only`. Descriptor validation also checks all local payload schemas/references and conservative semantic invariants. Source file existence/digests are checked when a repository root is supplied; source equivalence and source selectors still need review. The test suite exercises project-inspired compositions and malformed/adversarial descriptors. Passing it does not certify all workflows in any repository.
