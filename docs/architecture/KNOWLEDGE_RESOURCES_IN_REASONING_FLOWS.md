<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make knowledge bases, search spaces, and persistent stores explicit in
  reasoning workflows without treating a resource address as epistemic
  evidence or mixing operational effects with warrant-carrying route edges.

Intent:
  Define the adopted ERFL 0.3 resource-access projection using the compact
  @KB/@SEARCH/@STORE and directional-arrow syntax supplied by the user.

Function:
  Specifies resource classes, access and persistence notation, version and
  trust rules, runtime receipts, non-coercions, examples, and migration steps.

Maintenance Notes:
  Never place credentials or secret-bearing endpoints in reasoning-flow
  source. Keep resource targets repository-scoped or externally approved.
-->

# Knowledge Resources In Reasoning Flows

## Decision

Knowledge resources are explicit dependencies of a reasoning program. ERFL
0.3 adopts the supplied compact binding notation:

```text
@KB kb0 connect(file("MathformerKB"))
@SEARCH search0 connect(file("MathformerKB"))
@STORE ledger0 connect(file("artifacts/reasoning_logs"))
```

A declaration binds a local resource alias before the `reasoning` block. It is
not evidence of availability, successful access, truth, applicability, or
warrant.

An inverted arrow is useful, but only in a separate resource-access projection:

```text
q <-query- kb0
qs <-search- search0
```

The arrow reads “occurrence `q` draws from this resource through the declared
access mode.” It must never be allowed between reasoning occurrences and must
not participate in route sequencing, handle conservation, branches, joins, or
authority propagation.

Persistence points in the opposite direction:

```text
e -persist-> kb0
```

It is a guarded operational effect, not an epistemic relation. The reasoning
route constructs and assesses the proposed content; `E` authorizes a scoped
write; an external effect commits it and emits a receipt and immutable
successor snapshot.

## Adoption Status

The compact resource plane is implemented in ERFL 0.3. The earlier explicit
snapshot pattern remains useful when a flow needs to reason about snapshot
identity, manifests, or access receipts as epistemic evidence.

### Explicit immutable snapshots

Represent an accessible KB as an observed, versioned snapshot and manifest.
`Q` consumes both explicitly. This is valid under the current parser and makes
the hidden KB dependency visible immediately.

### Compact resource projection

Use `@KB`/`@SEARCH`/`@STORE` declarations and occurrence-attached resource
arrows. The resource plane declares intended access and effects while `steps`
continues to describe epistemic dependencies.

The former `flow`/`route` spelling is intentionally rejected; imported profiles
must migrate to `reasoning`/`steps` so the framework has one canonical syntax.

## Three Planes

| Plane | Purpose | Examples |
| --- | --- | --- |
| Epistemic steps | What is inferred, retrieved, grounded, assessed, and calibrated | Query model, candidate bundle, grounding evidence, assessment, decision |
| Resource access/effect | Which logical resource is read, searched, or targeted for persistence | `q <-query- KB.premises`, `entry -append-> STORE.memory` |
| Runtime evidence | What resource version was actually resolved and what operation actually occurred | Snapshot manifest, access receipt, persistence receipt, successor digest |

The planes join through occurrence aliases, typed handles, immutable resource
versions, and receipt identities. None can substitute for another.

## Resource Classes

### `KB.*`: knowledge bases

A `KnowledgeBase<T>` is a curated, indexed, or otherwise managed collection
whose entries retain individual provenance and trust state.

Initial read modes:

- `read`: fetch a known entry or object identity;
- `lookup`: exact key, hash, or membership lookup;
- `query`: structured filtering or selection;
- `snapshot`: resolve an immutable collection version.

Membership establishes only what the named snapshot records. It does not prove
that an entry is true, applicable, grounded, accepted, or current outside that
snapshot.

### `SEARCH.*`: search spaces

A `SearchSpace<T>` is a discovery surface that may be open-world, ranked,
partial, dynamic, rate-limited, or non-repeatable. It includes web search,
documentation search, solver frontiers, and exploratory corpora.

The initial mode is `search`. A search result is a candidate. An empty result
is not evidence of absence unless the search contract establishes relevant
completeness. Unavailability, timeout, authorization failure, and an empty
result are distinct states.

Search is not a new reasoning primitive. It is commonly materialized by `Q`
when retrieving candidates, but the same resource mode may support `P` when
searching for counterexamples. Resource mode does not determine epistemic type.

### `STORE.*`: persistent stores

A `PersistentStore<T>` is a durable state substrate. Durability confers no
epistemic authority on its contents.

Initial read modes are `read` and `query`. Initial write modes should be:

- `append`: add an immutable event or entry;
- `put`: create a new named immutable object;
- `upsert`: create a successor version under an explicit predecessor check;
- `checkpoint`: persist a reproducible state snapshot;
- `invalidate`: append a tombstone or supersession relation;
- `promote`: publish an already assessed entry under a curation policy;
- `commit`: change a mutable active-version pointer after candidate validation.

Physical deletion should remain outside the initial language. Invalidation is
not falsity, and history should remain reconstructible.

## Adopted ERFL 0.3 Pattern

The earlier premise-retrieval profile left its KB implicit:

```erfl
q:Q[query_structure::Model->candidates::Bundle]
```

The canonical ERFL 0.3 profile now uses this explicit snapshot projection:

```erfl
erfl 0.3
@KB kb0 connect(file("MathformerKB"))
reasoning premise_retrieval_and_verified_reuse {
  goal "produce a verified reuse candidate or an explicit gap" -> reuse_status
  steps
    (
      s:S[request::Context->query::Model<KnowledgeQuery>]
      & o:O[
        kb0,
        kb_version::Constraint
        -> kb_snapshot::Bundle<KnowledgeBaseSnapshot>,
        kb_manifest::Evidence<SnapshotManifest>
      ]
    )
    -retrieve> q:Q[
      query::Model<KnowledgeQuery>,
      kb_snapshot::Bundle<KnowledgeBaseSnapshot>,
      kb_manifest::Evidence<SnapshotManifest>
      -> candidates::Bundle<RetrievalCandidate>,
      retrieval_receipt::Evidence<RetrievalReceipt>
    ]
  o <-query- kb0
    -ground> g:G[
      candidates::Bundle<RetrievalCandidate>,
      query::Model<KnowledgeQuery>
      -> alignment::Evidence<GroundingLink>
    ]
    -assess> r:R[
      candidates::Bundle<RetrievalCandidate>,
      alignment::Evidence<GroundingLink>
      -> assessment::Assessment
    ]
    -calibrate> e:E[
      candidates::Bundle<RetrievalCandidate>,
      assessment::Assessment,
      kb_manifest::Evidence<SnapshotManifest>,
      retrieval_receipt::Evidence<RetrievalReceipt>
      -> reuse_status::Decision
    ]
  on e.reuse_candidate => accept
  on e.explicit_gap => stop
  on e.stale_knowledge_snapshot => stop
  on e.knowledge_resource_unavailable => stop
}
```

`O` establishes which snapshot was inspected. `Q` retrieves from that exact
snapshot. `G`, `R`, and `E` remain necessary because retrieval does not establish
applicability, correctness, semantic equivalence, or permission to reuse.

Here the resource declaration exposes availability, while `O` still produces
the immutable snapshot and manifest used as evidence. This is intentionally
more explicit than consuming raw KB results directly.

## Deferred Verbose Resource Schema

The following ERFL 0.4 sketch is retained as a possible future schema-rich
form. It is not the adopted 0.3 surface syntax and is not accepted by the 0.3
validator. The compact syntax above is canonical today.

### External inputs

Every unproduced epistemic handle should be declared:

```erfl
input request::Context
input reuse_policy::Constraint
```

An input is an immutable identity within one flow execution. It is not a
resource address and cannot be silently rebound during the flow.

### Logical resources

```erfl
resource KB.local_theorems::KnowledgeBase<Claim>
  capabilities [lookup, query]
  binding snapshot_required
  trust per_entry

resource SEARCH.mathlib_docs::SearchSpace<Presentation>
  capabilities [search]
  binding observed_version
  coverage open_world
  optional

resource STORE.retrieval_ledger::PersistentStore<Decision>
  capabilities [append]
  consistency append_only
  binding versioned
```

A declaration says the flow is permitted to depend on a logical resource. It
does not prove connectivity, authorization, freshness, completeness, or
successful access.

### Access statements

```erfl
access qk <-query- KB.local_theorems@kb_snapshot
  using query
  yielding kb_candidates, kb_receipt

access qs <-search- SEARCH.mathlib_docs@search_observation
  using query
  yielding search_candidates, search_receipt
```

The occurrence alias, access verb, resource family, resource version binding,
input handles, and result handles are explicit. The declared `using` and
`yielding` handles must occur in the referenced occurrence interface.

### Persistence statements

```erfl
persist reuse_status -append-> STORE.retrieval_ledger@ledger_base
  when e.reuse_candidate
  yielding ledger_successor, persistence_receipt
```

For knowledge curation:

```erfl
persist accepted_entry -promote-> KB.local_theorems@kb_base
  when e.curated_for_scope
  yielding kb_successor, persistence_receipt
```

The guard must be a terminal `E` disposition licensed for that write mode. The
payload must already exist and retain its trust state, taints, provenance, and
obligations. The effect cannot make the payload more true or better grounded.

The successor and receipt are operational outputs. If later epistemic reasoning
depends on them, a subsequent `O` occurrence must observe them as immutable
evidence. Same-flow write-then-read should be rejected initially.

## Deferred Multisource Example

```erfl
erfl 0.4
reasoning multisource_grounded_retrieval {
  input request::Context

  resource KB.local_theorems::KnowledgeBase<Claim>
    capabilities [query]
    binding snapshot_required
    trust per_entry

  resource SEARCH.mathlib_docs::SearchSpace<Presentation>
    capabilities [search]
    binding observed_version
    coverage open_world
    optional

  resource STORE.retrieval_ledger::PersistentStore<Decision>
    capabilities [append]
    consistency append_only
    binding versioned

  goal "produce a grounded multisource reuse disposition" -> reuse_status
  steps
    s:S[request::Context->query::Model<KnowledgeQuery>]
    -retrieve> (
      qk:Q[
        query::Model<KnowledgeQuery>
        -> kb_candidates::Bundle<RetrievalCandidate>,
        kb_receipt::Evidence<RetrievalReceipt>
      ]
      & qs:Q[
        query::Model<KnowledgeQuery>
        -> search_candidates::Bundle<RetrievalCandidate>,
        search_receipt::Evidence<SearchReceipt>
      ]
    )
    -ground> g:G[
      query::Model<KnowledgeQuery>,
      kb_candidates::Bundle<RetrievalCandidate>,
      search_candidates::Bundle<RetrievalCandidate>
      -> alignment::Evidence<GroundingLink>
    ]
    -assess> r:R[
      kb_candidates::Bundle<RetrievalCandidate>,
      search_candidates::Bundle<RetrievalCandidate>,
      alignment::Evidence<GroundingLink>
      -> assessment::Assessment
    ]
    -calibrate> e:E[
      assessment::Assessment,
      kb_receipt::Evidence<RetrievalReceipt>,
      search_receipt::Evidence<SearchReceipt>
      -> reuse_status::Decision
    ]

  access qk <-query- KB.local_theorems@kb_snapshot
    using query
    yielding kb_candidates, kb_receipt

  access qs <-search- SEARCH.mathlib_docs@search_observation
    using query
    yielding search_candidates, search_receipt

  persist reuse_status -append-> STORE.retrieval_ledger@ledger_base
    when e.reuse_candidate
    yielding ledger_successor, persistence_receipt

  on e.reuse_candidate => accept
  on e.explicit_gap => stop
  on e.search_unavailable => stop
}
```

The parallel `Q` occurrences, not the resource arrows, model the required
multi-source reasoning join. If search is optional, a complete profile must
represent an explicit alternative branch or unavailable outcome rather than
silently treating missing search results as an empty bundle.

## Adopted Compact Grammar

```text
document := "erfl 0.3" resource_binding* reasoning
resource_binding := "@" ("KB" | "SEARCH" | "STORE") ALIAS
                    "connect(file(" STRING "))"
reasoning := "reasoning" ID "{" goal steps repeat* resource_edge* handler+ "}"
steps := "steps" expression
resource_edge := ALIAS "<-" READ_MODE "-" ALIAS
               | ALIAS "-" WRITE_MODE "->" ALIAS
READ_MODE := "read" | "lookup" | "query" | "search" | "snapshot"
WRITE_MODE := "persist" | "append" | "put" | "upsert" | "checkpoint"
              | "invalidate" | "promote" | "commit"
```

A trailing `...` is removed during statement coalescing and changes no
semantics. `flow` and `route` are rejected legacy keywords.

## Deferred ERFL 0.4 Grammar Delta

```text
reasoning  := "reasoning" ID "{"
                input* resource* goal steps repeat*
                access* persist* handler+
              "}"

input      := "input" PORT

resource   := "resource" RESOURCE "::" RESOURCE_KIND
              resource_property*

access     := "access" ALIAS "<-" ACCESS_MODE "-" RESOURCE_REF
              "using" handles "yielding" handles

persist    := "persist" HANDLE "-" WRITE_MODE "->" RESOURCE_REF
              "when" predicate "yielding" handles

RESOURCE   := ("KB" | "SEARCH" | "STORE") "." ID
RESOURCE_REF := RESOURCE ["@" HANDLE]

RESOURCE_KIND :=
    "KnowledgeBase" "<" TYPE_REF ">"
  | "SearchSpace" "<" TYPE_REF ">"
  | "PersistentStore" "<" TYPE_REF ">"

ACCESS_MODE := "read" | "lookup" | "query" | "search" | "snapshot"

WRITE_MODE :=
    "append" | "put" | "upsert" | "checkpoint"
  | "invalidate" | "promote" | "commit"
```

The exact resource-property grammar should remain small and registry-driven.
At minimum it needs capabilities, required/optional status, version-binding
policy, coverage model, trust granularity, and consistency model.

## Static Invariants

- Every unproduced epistemic handle is declared as an `input` or produced by a
  causally prior occurrence.
- Every resource reference resolves to exactly one logical declaration.
- A resource declaration contains no credential or secret-bearing endpoint;
  file targets must be repository-scoped or externally approved.
- The access mode is licensed for the declared resource class and capability.
- Access `using` and `yielding` handles occur in the referenced occurrence.
- `query`, `lookup`, and ordinary `search` normally bind `Q`; observation reads
  bind `O`; counterexample searches may bind `P`.
- A resource edge never satisfies route handle conservation or branch joins.
- Inverted arrows between reasoning occurrences are rejected.
- `SEARCH.*` is read-only.
- Optional-resource failure has an explicit fallback, unavailable output, or
  stopping disposition.
- Every persistence effect is guarded by a compatible terminal `E` decision.
- The persisted payload exists before calibration and preserves its authority.
- A persistence effect yields a new resource version and receipt; it never
  reproduces the base identity in place.
- Same-flow write-then-read dependencies are rejected initially.

## Runtime Records

### Access receipt

An access or retrieval record should include:

- logical resource id and resolver-binding id;
- exact snapshot, revision, or observed-time envelope;
- resource and entry schema versions;
- original and normalized query digests;
- access mode, filters, scope, ranking method, top-k, and coverage declaration;
- index, canonicalizer, embedding, or search-provider method versions;
- result identities, entry versions, per-result provenance, and trust state;
- result and receipt digests;
- status distinguishing success, empty, partial, stale, unavailable,
  unauthorized, timeout, and error.

### Persistence receipt

A persistence record should include:

- logical resource id and resolver-binding id;
- payload identity, digest, trust state, taints, and obligations;
- write mode and base snapshot digest;
- authorization decision and policy digests;
- immutable successor snapshot and content digests;
- compare-and-swap result;
- invalidated indexes, caches, assessments, and dependent evidence;
- actor, timestamp, outcome, and rollback target;
- receipt identity and digest.

A receipt establishes that an operation occurred under the recorded conditions.
It does not establish truth, applicability, successful curation, or downstream
index visibility.

## Persistence As Immutable Revision

Before an operational effect, knowledge curation should use the same immutable
revision pattern as reflective refinement:

```text
baseline snapshot + accepted entry + assessment
  -> proposed KB delta
  -> candidate successor snapshot + revision record
  -> integrity and policy tests
  -> persistence assessment
  -> E commit authorization
  -> external compare-and-swap commit
  -> persistence receipt
  -> subsequent observation of committed snapshot
```

`latest` may be a convenience pointer but never an evidence identity. Updates,
status changes, canonicalization refreshes, promotions, and invalidations should
create new entry or snapshot versions rather than erase predecessor state.

## Current MathformerKB Implications

The existing KB already distinguishes generated candidates from trusted
premises and resolves positive Bloom hits against JSONL storage. The resource
model exposes additional integrity work:

- `KBEntry` has a logical id but no immutable entry-version id or content digest;
- status updates and canonical-hash refreshes rewrite authoritative JSONL state;
- Bloom manifests do not bind themselves to a source snapshot digest or
  canonicalizer version;
- embedding metadata does not bind the index to a source snapshot or embedding
  algorithm version;
- loaded indexes are not checked for freshness against current storage;
- a stale Bloom negative can bypass the authoritative hash index;
- query packets do not identify the exact KB and index revisions used.

These are runtime consistency concerns, not reasons to give a KB stronger
epistemic authority in ERFL.

## Non-Coercions

- Declared resource access is not runtime availability or authorization.
- A resource reference is not evidence.
- KB membership is not truth, applicability, grounding, or acceptance.
- Retrieval is not grounding.
- Search ranking is not curation or proof relevance.
- No result is not absence without a completeness argument.
- Resource unavailability is not a negative scientific result.
- A stale index cannot establish presence or absence for a newer snapshot.
- Collection-level trust cannot overwrite per-entry trust.
- Persistence preserves authority; it does not upgrade it.
- A write receipt is not evidence for the persisted claim.
- Write success is not index visibility.
- Invalidation is not falsity and should not silently delete history.
- A mutable `latest` pointer is not an immutable version.
- Resource arrows do not carry epistemic warrant.

## Recommendation

Use the adopted compact bindings and directional arrows for accessible KBs,
search surfaces, and stores. Retain explicit snapshot/manifest/receipt handles
whenever version identity or access evidence matters to later reasoning:

```text
steps arrows     = epistemic dependency and warrant conservation
resource arrows  = declared access or guarded operational effect
runtime receipts = evidence that the declared interaction actually occurred
```

The self-contained implementation backlog is in
[`meta_skills/todos/knowledge_resource_todos.yaml`](../../meta_skills/todos/knowledge_resource_todos.yaml).
