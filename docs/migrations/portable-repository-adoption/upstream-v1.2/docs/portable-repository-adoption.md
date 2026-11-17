# Portable repository organization: an agent execution brief

Version 1.2 · 11 September 2026

This document is the complete transfer unit. Copy it into another repository or provide it to an agentic coding environment. Execution requires the receiving repository and its normal development tools; it does not require BioAgents, its Python packages, this conversation, PRISM, a particular model provider, or a biomedical domain.

This is an adoption specification derived from BioAgents conventions. It is not a claim that its illustrative metadata is accepted unchanged by every BioAgents schema. Use the receiving project's namespace and validate the contracts it actually implements.

## 1. Instruction to the receiving agent

Organize this repository around discoverable, typed capabilities, explicit code ownership, documented workflows, and consistent public reasoning/provenance logs. Preserve its current functions and supported interfaces. Implement the bounded migration below; do not stop after proposing a directory tree.

A user-specified subset replaces the default scope below. For a review-only request, inspect and return concrete findings without implementing the migration.

First inspect the repository's own instructions, build configuration, entrypoints, tests, documentation and existing skill conventions. Record the actual starting state. Treat this document as the requested target convention, subject to the user's instructions and the receiving environment's governing rules. Do not overwrite existing agent instructions wholesale.

Default to additive adoption: describe and wrap existing implementations before considering moves. If the repository already has equivalent structures, map them explicitly instead of creating competing authorities. Use its language, package manager and test runner. Do not introduce a planner, model dependency, workflow engine or new service merely to match the example tree.

The default scope is all existing discoverable skills, plus a small representative set of currently implemented capabilities and workflows selected during inventory. Record that exact set before implementation. Ordinary helper functions do not each become a skill. Expansion to every function or every historical run is outside that initial scope.

Finish when the selected set is discoverable, correctly typed, documented and logged through the actual invocation routes, and the recorded compatibility checks pass. Report remaining limitations honestly. Do not create an endless sequence of architecture refinements or require new research to finish this migration.

## 2. What to preserve and what to adopt

| Preserve from the receiving repository | Adopt from the BioAgents organization |
|---|---|
| Existing public imports, CLI names/options, API routes and response contracts | Stable skill identities independent of their directory locations |
| Existing algorithms, provider choices and workflow ordering | Explicit capability, input/output and operation contracts |
| Existing data semantics, configuration precedence and supported platforms | Separate capability source, shared runtime, integrations and generated artifacts |
| Existing error behavior, exit codes and transactional boundaries | Consistent public decision traces linked to provenance |
| Existing output locations relied on by consumers | A documented run-artifact convention for new integrations |
| Existing domain terminology and product naming | Reader/reasoner/writer roles with domain-appropriate themes and clusters |
| Existing source lineage and historical receipts | Generated discovery/documentation from canonical authored metadata |

### Domain and host ownership

| Surface | Owner and concrete boundary |
|---|---|
| Skill instructions, typed domain operations, scientific workflows, fixtures | Domain repository; one canonical skill definition per capability |
| Scientific routing vocabulary, source bindings and request adapters | Domain package internals; an adapter directory is not an additional discoverable skill |
| Authentication, invocation identity, authorization, isolation, model access, persistence and attestations | Existing host platform; domain policies cannot grant these permissions |
| Generic planner and application | Existing host owner; retain a receiving repository's working services where they already belong |
| Exported metadata and runtime closure | Built by the domain repository; imported and selected as an immutable version by the host |
| Repository migration/maintenance instructions | Project-support scope; not automatically part of scientific domain export |

In current BioAgents, Lunar owns the application and generic planner. BioAgents retains domain code and exports it for isolated host workers; neither checkout is a runtime dependency of the other. Do not recreate `catalog/planner/` or restore the retired BioAgents application to adopt this convention. In another repository, preserve its existing planner/application and map that ownership explicitly; no Lunar installation or service split is required by this guide.

Folder names are a reference layout, not a reason to break a mature package. The stable requirements are ownership, discoverability, contracts and behavior. Record deliberate layout deviations and the discovery rules that implement them.

## 3. Reference layout and ownership

```text
AGENTS.md                         concise repository entrypoint and conventions
catalog/
  SKILLS.md                       discovery rules and navigation
  agents/<role>/<theme>/<cluster>/<skill-id>/
    SKILL.md                      purpose, use, procedure and handoffs
    skill.yaml                    typed metadata and operation bindings
    README.md                     developer usage when instructions are insufficient
    references/                   contracts, examples and supporting documentation
    scripts/                      thin launchers, when needed
    src/<package>/                skill-owned code, when appropriate
    tests/                        skill-local tests, or links to authoritative tests
    agents/                       optional host-specific discovery projections
  registry/                       discovery and descriptor generation
  schemas/                        versioned interface and log contracts
  runtime/                        genuinely shared execution/logging infrastructure
  workflows/                      reusable compositions referencing skills
  integrations/                   adapters to the existing application and hosts
project-skills/                    repository maintenance capabilities
src/ or existing application/     retained implementation in its existing owner
docs/                             architecture, skill guide, logging, migration record
tests/                            integration and compatibility tests
scripts/                          repository-level maintenance entrypoints
artifacts/runs/<workflow>/<run-id>/
                                  new per-run results, logs and manifest
artifacts/workflows/               generated reusable workflow packages, if any
```

Use one canonical authored location per skill. Its directory leaf and declared `name` agree. A stable scoped identity, such as `domain:config-validator`, resolves to that location through discovery. Themes and clusters help navigation; they must not change invocation identity. Document whether discovery scans the exact role/theme/cluster depth or uses an explicit location map.

Separate reusable domain capabilities from repository-maintenance skills through `scope`. Keep both discoverable without copying their definitions. Preserve old identifiers with explicit aliases. Detect alias cycles, ambiguous identities and duplicate canonical definitions.

Keep `catalog/agents/<role>/<theme>/<cluster>/<skill-id>/` as the domain hierarchy. Internal routing adapters, including directories carrying archived instructions, remain package internals unless explicitly admitted as canonical skills. Discover from declared roots and identities rather than recursively registering every `SKILL.md`.

An instruction-only skill need not contain empty `src/`, `scripts/` or `tests/` directories. Keep shared libraries where their existing consumers expect them. Host-specific configuration projects canonical metadata; it is not another source of skill semantics.

## 4. Skill typing: independent dimensions

Do not collapse the following into a single label such as “AI agent” or “deterministic reasoner.”

| Dimension | Meaning | Examples |
|---|---|---|
| Scope | Who owns/uses the capability | domain, project_support, planner |
| Role | Principal work performed | readers acquire/normalize; reasoners analyze/compare/decide; writers communicate/package |
| Theme and cluster | Navigation by durable capability family | configuration / validation-and-quality |
| Operation | Named action with its own I/O and execution contract | validate, retrieve, compare, render |
| Ownership/migration posture | Where authoritative implementation lives and its adoption state | application-owned adapter, skill-owned source, pinned upstream adapter, legacy implementation retained |
| Invocation mechanism | How it can actually be invoked | instructions, CLI, language callable, provider adapter, composite |
| Independence | Additional machinery required | standalone, adapter-mediated, companion-required, external-runtime-required |
| Execution character | How a particular operation produces its result | exact deterministic, stochastic estimation, semantic generation, provider opaque, non-executing orchestration |
| Generation boundary | Whether model generation belongs in that operation | prohibited, required, optional presentation, not applicable |
| Reasoning type | Declared inferential method and its mapping source | deduction, abduction, statistical inference, analogy; unassigned when undocumented |
| Availability | What is presently reachable | local implementation, configured external dependency, instructions only, unavailable |
| Output authority | What a result establishes | parsed source record, computed measurement, estimate, hypothesis, presentation |

Type operations individually. A skill may compute deterministic values and optionally use a model to explain them. Its explanation must not modify the values. A seeded simulation remains a simulation; reproducibility does not turn a model prediction into an observation. A provider call returning JSON is not necessarily deterministic. A writer need not use a model. A reasoner role does not prove a specific reasoning method was executed.

Names differ across existing metadata surfaces: BioAgents' `execution.posture` can describe ownership/migration state, while interface documentation uses invocation posture for the available mechanism. Map by meaning and source schema, not matching field names. Preserve both facts in the receiving contract.

For consequential claims such as binding, execution character, availability and reasoning mapping, retain their basis: `declared`, `derived`, `overridden` or `unknown`, with a source location where available. Derive syntactic facts from code; do not infer causal authority, reasoning methods or provider availability from a name. Unknown documentation creates a local documentation task, not a reason to disable working functions.

Record field ownership once. In the example profile, SKILL frontmatter owns name and capability description; YAML owns operation contracts and the friendly label. Its repeated capability text is a generated projection of the description, checked for equality. An existing host may use different ownership, but must document precedence and detect drift rather than choosing whichever copy it reads first.

### Minimal package example

The following is a proposed host-neutral example, not an existing BioAgents fixture. Replace the example identities and paths with inspected repository facts.

`SKILL.md`:

```markdown
---
name: config-validator
description: Check configuration values against the application's existing rules.
---
# Configuration validator

Use when a configuration needs the same validation performed by the application.
Input: a configuration object under ConfigInput@1.
Output: existing validation findings under ConfigFindings@1.

Invoke the registered validate operation. Preserve the application's messages,
ordering and error behavior. Return its findings unchanged; emit any public
execution summary as a separate trace artifact.
Do not repair configuration automatically or infer missing values.

Example: an invalid timeout produces the existing timeout finding.
Handoff: a separate configuration editor may act on findings when requested.
```

`skill.yaml`:

```yaml
schema_version: repository.skill/v1
id: domain:config-validator
name: config-validator
label: Configuration validator
capability: Check configuration values against the application's existing rules.
version: 1.0.0
scope: domain
role: reasoners
theme: configuration
cluster: validation-and-quality
invocation: language_callable
independence: adapter-mediated
implementation_owner: existing-application
operations:
  - id: validate
    binding: app.skill_adapter.invoke_validate
    implementation_ref: app.config.validate
    context_injection: emit
    inputs: ConfigInput@1
    outputs: ConfigFindings@1
    execution_character: exact_deterministic
    generation: prohibited
    reasoning_types: []
    reasoning_mapping_status: unassigned
    side_effects: []
    availability: local
    field_basis:
      binding: {basis: declared, source: app/skill_adapter.py}
      execution_character: {basis: derived, source: app/config.py}
```

This metadata describes a hypothetical verified binding. The host passes user input as `config` and injects its trace callback as `emit`; callers do not supply executable callbacks through serialized input. `implementation_ref` identifies the legacy algorithm, while `binding` identifies the route actually invoked. Here `side_effects` describes the domain operation; the injected collector may write declared trace sidecars. Do not copy `availability: local` until that binding resolves. Empty reasoning mappings are rendered “Unassigned,” not guessed as deduction. Create input/output definitions from the existing API; a schema name alone is not a type definition. The host schema must define required fields, allowed values, unknown representation and versioning. Keep optional declarations proportional to the capability.

Breaking required I/O or semantics requires a major contract version. Optional metadata additions can use a minor version if existing consumers tolerate them. Keep content revisions separate from interface versions.

### Authored contracts versus exported discovery records

The `repository.skill/v1` example above is a local illustrative profile. It is neither BioAgents' authored `bioagents.skill-metadata/v1` contract nor Lunar's exported skill format. In BioAgents, authored metadata uses `skill_id`, an implementation with confined `source_root`, and executable operation records with `operation_id`, `module` and `callable`. Convert according to each schema; do not rename a schema version to claim compatibility.

BioAgents registration has four layers: semantic `SKILL.md`, machine `skill.yaml`, conversational `agents/openai.yaml`, and domain export followed by host import, preparation and version selection. The conversational file declares `display_name`, `short_description` and a `default_prompt` invoking `$<skill-id>`. Other hosts may use an equivalent projection; OpenAI metadata is not a universal requirement.

The current exporter constructs the following seven required fields from a scientific descriptor `row`. This describes the actual transformation in `catalog/integrations/domain_package/metadata.py`, not a proposed alternate registry:

| Exported field | Actual authored/derived origin |
|---|---|
| `id` | Descriptor `row['name']`; do not substitute the local example's scoped invocation identity |
| `name` | Descriptor name with hyphens replaced by spaces and title-cased |
| `instructions` | Canonical `SKILL.md` body, removing YAML frontmatter when present |
| `capabilities` | A one-element array containing the complete effective descriptor `row`, including projected operation metadata |
| `invocation` | The descriptor's existing `invocation` object, without inventing a different binding shape |
| `groups` | First three components below `catalog/agents`: role, theme, cluster |
| `metadata` | `source_path`, repository-relative `source_directory`, and the complete `descriptor` |

For example, a deliberately minimal instruction-only discovery record has the exported outer shape below. Empty capabilities/invocation make this a schema example, **not** an executable exporter output or a registration receipt:

```json
{
  "id": "release-note-writer",
  "name": "Release Note Writer",
  "instructions": "Draft release notes from a supplied change list.",
  "capabilities": [],
  "invocation": {},
  "groups": ["writers", "software", "release-communication"],
  "metadata": {
    "source_path": "catalog/agents/writers/software/release-communication/release-note-writer/SKILL.md",
    "source_directory": "catalog/agents/writers/software/release-communication/release-note-writer"
  }
}
```

The pinned `skills-v1.schema.json` requires all seven outer fields and forbids additional outer fields, but leaves these nested objects open. Passing that schema does not validate callable resolution or runtime closure. A real export retains the complete descriptor and invokes the package validator; actual discovery and invocation are separate host checks (example G).

## 5. Code organization without changing behavior

Map each selected skill to its actual implementation and its owner. Start with an adapter calling the existing public function or command. Do not copy the algorithm into the catalog or rerun it to generate a log.

Where skill-owned code is appropriate, use these responsibilities; separate files only when the implementation benefits:

- `api`: typed request/result boundary and validation.
- `kernel`: the actual computation or domain transformation.
- `provider`: external service/model access and response handling.
- `lifecycle`: composition, run context, public events and failure recording.
- `cli`: argument parsing and the existing process contract.

A small capability can keep these in one module. A skill wrapping an application service can own only its adapter. Shared runtime code owns common logging and contract validation rather than duplicating these in every skill. A workflow composes capabilities; it must not secretly implement a second version of their algorithms.

Only relocate code after discovering dynamic imports, package data, resource paths, plugins, serialization references, console scripts and installation behavior. Test from an installed package and a different working directory when those are supported. Keep a tested compatibility facade at an old public import when necessary. Do not depend on repository-wide `sys.path` edits as a replacement for packaging.

Domain package dependencies must have declared, packaged bytes or an explicit external-service contract. Do not add runtime imports of a sibling host checkout. Keep host service access behind the receiving environment's supported adapter/context boundary.

A phase that leaves existing application code in place can be a complete migration. Record an explicit adapter-based ownership arrangement rather than promising a later move.

## 6. Reasoning logs: public decisions and execution context

A reasoning log is a concise public decision trace. It is not a hidden chain of thought, model scratchpad, transcript of private reasoning, or reconstruction of reasons the implementation did not record.

Use the same presentation order in Markdown, HTML, CLI views and application views:

1. Friendly skill label.
2. One-sentence capability.
3. Explicitly mapped reasoning type, or “Unassigned.”
4. Operation, stage, actor and execution state.
5. Named input references, action, outcome and short recorded rationale.
6. Alternatives actually considered, outputs and performed checks.
7. Relevant assumptions, evidence limitations and operational problems.
8. Links to source artifacts and provenance.

For a component with no recorded skill, show its component label and “No skill recorded.” Multiple actual skills receive separate identities. Do not rename a workflow event to imply an unobserved skill invocation.

Example of a display from a hypothetical fixture:

```text
Configuration validator
Checks configuration values against the application's existing rules.
Reasoning type: Unassigned

Operation: validate · Stage: configuration · Execution: completed
Input: configuration fixture C17
Outcome: one invalid timeout finding returned
Recorded basis: Rationale not recorded
Checks: none recorded during this invocation
Output: findings.json
```

If that basis was not recorded, display “Rationale not recorded.” Do not manufacture a plausible explanation. If no alternative was considered, the list may be empty. Record an unsuccessful action as unsuccessful even if later recovery succeeds.

### Required information and contract choices

Implement a versioned local contract covering the following information. These are semantic requirements, not permission to append arbitrary keys to an existing strict schema.

| Record | Required information |
|---|---|
| Run/log envelope | schema version, run/log identity, subject, overall execution status, concise summary, entries, references, assumptions/limitations, visibility/redaction declaration, digest |
| Entry | unique entry identity, sequence, stage, actor kind/identity, operation or an explicit operation reference, action, recorded rationale or missing marker, decision/outcome, input/output references, checks and local operational problems |
| Skill snapshot | canonical identity, human label, capability, mapped reasoning types, mapping basis, metadata version/digests |
| Reference | stable ID, kind, locator, optional description, content digest when available |
| Correlation | fresh invocation/attempt identity, unique event keys and parent identity for nested/concurrent work, in the log or linked provenance |
| Terminal snapshot | identity and content digest of the exact result artifact, joined to the same invocation; never a mutable “latest result” pointer |

Keep operation, correlation and timing in linked provenance if the existing log schema cannot express them compatibly. In BioAgents v1, the entry schema is strict: fields include `entry_id`, `sequence`, `stage`, `actor`, `action`, `rationale_summary`, `inputs_used`, `decision`, `outputs`, `checks`, `blockers`, plus optional `skill_metadata`. Arbitrary extra entry fields do not become v1-compatible because they are useful. A receiving project may define its own versioned schema or an explicit adapter.

Keep execution state distinct from a decision and evidence strength. A completed run may produce an uncertain estimate or a hypothesis. A rejected candidate does not mean the workflow failed. Use blocked/deferred execution only for an actual missing operational prerequisite, not merely because evidence is incomplete. Hypothesis generation can finish with qualified conclusions and no further experiment.

The host issues invocation identities in production; fixture-generated IDs demonstrate correlation only and are not host attestations. Repeating the same skill/input must still create a distinct invocation. Persist a terminal reasoning snapshot with its exact result reference and digest, and reject mismatched invocation/result joins. An optional generated description is a presentation projection; fall back to recorded summary/detail when absent. Rendering never triggers generation or execution.

A sequence defines order within a log. It does not establish causal order between concurrent branches. Record parent/attempt references, retain failed attempts and distinguish a retry from duplicate delivery. Do not wrap each invocation twice through overlapping integrations. Log at existing meaningful operation boundaries, not every function call.

### Historical integrity and provenance

Reasoning logs explain decisions; provenance records what produced what. Join them through stable run, invocation and artifact identities. Both views use the same skill metadata resolver and display preamble, but retain their separate source records and purposes.

Snapshot label, capability and mappings at execution time before computing the record digest. Preserve their source digests. An explicit mapping says how a skill is classified; it does not prove every mapped method ran. BioAgents currently obtains some mappings from PRISM annotations; another repository should use its own reviewed declarations and does not need PRISM.

Implement a small host resolver from stable skill ID to authored metadata and explicit mappings, or supply already resolved snapshots to the shared logger. Do not copy the BioAgents resolver unchanged: it assumes catalog paths, discovery depth and mapping locations. Historical snapshots must render even without a live catalog. Viewing a trace must never invoke its skill or rerun its workflow.

Never rewrite an old digest-bound record to add current labels. Produce a separate view that retains the original, its byte digest, the projection version and the new metadata's sources/digests. Mark current enrichment as current, not historical. Preserve unknown historical values. A content hash detects changed bytes; it does not prove scientific validity, execution, authenticity or a digital signature.

Specify the exact serialization used for object digests and hash raw files as raw bytes separately. BioAgents uses SHA-256 of UTF-8 JSON with sorted keys, compact separators and unescaped Unicode, excluding the top-level digest field. A different-language implementation must publish byte-level fixtures, including Unicode and numeric cases, before claiming compatibility. Use a supported canonical serialization when defining a new host contract; reject unsupported numeric values rather than letting platforms hash different encodings.

Capture only suitable public summaries and references. Do not put credentials, raw sensitive source rows, private prompts or hidden-reasoning content into logs. Validate fields and actual content; key-name filtering alone does not establish that content is suitable. HTML rendering must escape stored text and handle artifact links safely.

### Logging must not silently change existing functions

Preserve legacy stdout, return shapes, exceptions, retries and side effects. Prefer sidecar artifacts or an existing extension point when consumers reject extra result fields. Reuse existing telemetry/storage when it can meet the contract; do not install a parallel service by default.

Choose and document failure behavior. During additive adoption, an unavailable optional log sink should normally preserve the legacy operation's result and report a separate logging failure through an existing diagnostic channel. Never label the missing log complete. Preserve a pre-existing mandatory audit policy where one exists. Do not introduce a new failure-before-action requirement without treating it as a behavioral change.

Test nested operations, retries, provider failures, concurrent runs, cancelled work and sink failure where supported. Record their actual outcomes without repeating an external action to obtain better provenance.

## 7. Documentation and discovery

Maintain these surfaces, reusing existing equivalents:

- Root agent entrypoint: canonical paths, ownership, commands, compatibility rules.
- Skill guide: purpose, use conditions, typed I/O, operation bindings, one concrete example, limitations and handoffs.
- Architecture map: application, skill adapters, shared runtime, workflows and host integrations.
- Generated catalog: stable ID, label, capability, role/scope, operation types, actual availability and source links.
- Logging guide: schema, examples, public presentation order, provenance linkage, migration and failure behavior.
- Migration record: baseline, exact scope, mappings, tasks, checks, outcomes and accepted deviations.

Authored instructions/contracts own meaning. Generated indexes and HTML catalogs must have a documented reproducible build command and drift check. Do not maintain hand-edited copies of full skill descriptions in several registries. Confirm discovery in the agent host actually used by the project; a valid YAML file alone does not prove a callable skill is visible.

Where the host uses imported domain packages, discovery is export → import → prepare → select that immutable version. Editing an authoring checkout cannot update a previously imported version. Package validation, selected-host visibility and an observed invocation are distinct checks; record each separately. Host-neutral local discovery remains sufficient when that is the receiving project's actual mechanism.

Keep detailed traces accessible from user-facing results. In scientific or expert reports, lead with the domain answer and selected support; put exhaustive evidence and execution histories in appendices or linked logs. Do not insert skill labels, reasoning-type taxonomy or workflow statuses into the domain argument merely because logging is now normalized.

## 8. Finite migration tasks

Create `docs/migrations/skill-organization/` or the repository's existing equivalent. Record the tasks below in its normal tracker. Each task needs: ID, scope, dependencies, implementation locations, exact verification commands, result/evidence paths and status. Use `planned`, `in_progress`, `complete` or `deferred`; explain deferrals. Do not mark a task complete on the basis of a proposed test.

| ID | Work and deliverable | Depends on | Completion evidence |
|---|---|---|---|
| A01 | Inventory existing skills, callable capabilities, workflows, code owners, public interfaces and log routes; record current revision and dirty files | — | Repository map and runnable baseline commands with observed results |
| A02 | Freeze the initial capability set and map current paths/IDs to canonical ownership, scopes, roles and aliases | A01 | Every selected capability has one owner and an explicit compatibility disposition |
| A03 | Define local versioned metadata, I/O and reasoning/provenance contracts; select existing discovery/log infrastructure to reuse | A02 | Concrete valid examples and invalid/unknown cases accepted or rejected as specified |
| A04 | Implement one representative existing workflow through adapters, metadata and shared log presentation | A03 | Old entrypoint behavior preserved; actual new invocation has resolvable identity, output and trace |
| A05 | Cover failure, retries/concurrency where applicable, sink failure and immutable historical projections | A04 | Observed outcomes, no duplicated side effects, old record digests unchanged |
| A06 | Apply the proven pattern to the rest of the frozen capability set; move code only if justified | A05 | Scope-to-implementation matrix has no silent omissions; affected integration checks pass |
| A07 | Generate the catalog and update architecture, agent instructions and user/developer examples | A06 | Discovery and links resolve; regeneration is repeatable; documented commands work |
| A08 | Run final compatibility comparison and publish a migration completion record | A07 | Baseline comparison, representative rendered logs, exact tested scope, remaining deviations and rollback instructions |

Select a pilot within the agreed scope that reflects the repository: preferably a multi-step existing workflow containing an input operation, a computation/decision and an output operation. If the selected scope includes providers, include a provider boundary; otherwise do not add one. Use recorded fixtures for repeatable tests and distinguish fixtures from live execution evidence.

A delegated team may split read-only inventory and contract review, then assign disjoint implementation files after agreeing the contracts. One integrator owns shared schemas, generators and final compatibility checks. Delegation is optional; this plan is executable by one agent.

## 9. Compatibility verification and rollback

Before changes, record exact commands and observed results for supported public imports, CLI/API examples, representative valid/invalid inputs, installation, workflows and output consumers. If the baseline fails, distinguish existing failures from migration regressions. Add focused characterization tests for untested interfaces that the migration will affect.

Compare the same fixtures before and after. Require exact results for deterministic behavior; define justified tolerances/invariants for stochastic output and timing. Check values, types, ordering, exceptions, exit codes, output paths, side effects and invocation counts as relevant. A test that merely asserts a new wrapper was called does not establish compatibility. Do not claim universal equivalence from a small test set: state the supported surfaces and cases actually checked.

New contract checks should cover duplicate IDs, unresolved aliases/bindings, mismatched I/O, inaccurate execution claims, missing metadata, digest tampering, unresolved references and cross-view consistency. If a provider is unavailable, report that live path unverified while continuing the independent local migration work.

Use small reviewable changes and preserve pre-existing edits. Revert only migration-owned changes when a compatibility comparison fails. Do not reset the whole repository. Additive adapters can be removed without touching original domain code. If paths are moved, record the reverse mapping and keep required public facades. Historical runs remain unchanged. No production database migration is implied by reorganizing skills and logs.

The final completion record must state:

1. Which skills/workflows and invocation routes were migrated.
2. Where canonical code, metadata, documentation and logs live.
3. Which public interfaces were verified and the observed results.
4. How to inspect a real example's reasoning and provenance views.
5. Any known limits, explicitly deferred surfaces and precise rollback procedure.

Conclude the agreed migration after these checks. Optional enhancements are advisory and do not reopen completed work.

## 10. Worked adoption examples

Examples A–F use a hypothetical receiving repository named `configkit`; example G shows the optional BioAgents-specific export route. These are concrete implementation targets, not receipts of an executed migration. The host-neutral examples require no BioAgents files. Adapt bindings to inspected host code and preserve the demonstrated distinctions.

### Example A: organize an existing application without moving its implementation

Suppose the repository starts with:

```text
pyproject.toml                     installs configkit and its console command
src/configkit/config.py           validate(config) -> list[str]
src/configkit/cli.py               configkit check FILE
tests/test_config.py
```

Its existing implementation is:

```python
def validate(config):
    timeout = config["timeout"]
    return [] if timeout > 0 else ["timeout must be positive"]
```

The current contract accepts numeric `timeout` values, returns ordered strings, and raises `KeyError` for a missing timeout. The CLI prints findings and exits 1 for an invalid configuration. These behaviors belong to the application, including the exception; this organization change does not silently improve them.

Add the following ownership map:

| Existing surface | Canonical addition | Disposition |
|---|---|---|
| `configkit.config.validate` | `catalog/agents/reasoners/configuration/validation-and-quality/config-validator/SKILL.md` and `skill.yaml` | Keep implementation and public import as `implementation_ref`; invoke through the adapter binding |
| `configkit check FILE` | Document it as the existing CLI invocation | Keep command, output and exit codes |
| No agent invocation adapter | `src/configkit/skill_adapter.py` | Own only invocation correlation and optional trace emission |
| Existing tests | `tests/test_skill_adapter.py` | Add parity cases; retain old tests |
| No run-output convention | `artifacts/runs/config-check/<run-id>/` | Use for new agent invocations, leaving CLI output unchanged |

Instantiate section 4's metadata with `binding: configkit.skill_adapter.invoke_validate`, `implementation_ref: configkit.config.validate` and `context_injection: emit`. Define `ConfigInput@1` as an object with a required numeric `timeout` and additional keys allowed; define `ConfigFindings@1` as an ordered array of strings. The adapter delegates to the legacy function rather than adding schema rejection that would change its errors. A separate new typed invocation endpoint may validate these schemas if its distinct error contract is documented.

For an application where optional logging uses standard Python logging, a small illustrative adapter is:

```python
import logging
from configkit.config import validate

logger = logging.getLogger(__name__)


def invoke_validate(config, emit):
    # emit accepts a native event; the shared collector creates the full envelope.
    def record(event):
        try:
            emit(event)
        except Exception:
            try:
                logger.warning("Optional skill trace could not be written")
            except Exception:
                pass  # Optional diagnostics must not replace the domain outcome.

    try:
        findings = validate(config)
    except Exception as exc:
        record({"operation": "validate", "execution_status": "failed",
                "error_type": type(exc).__name__})
        raise
    record({"operation": "validate", "execution_status": "completed",
            "finding_count": len(findings)})
    return findings
```

This adapter does not change the CLI route or claim that the legacy CLI is now instrumented. Its selected coverage is the new agent invocation route. If the migration scope includes the CLI, connect that route separately and test stdout/stderr explicitly. The collector owns run identity, metadata snapshots, references and digesting; the native event is not a complete reasoning log. The adapter deliberately avoids logging configuration bodies or exception messages.

Concrete parity tests for this example:

```python
import pytest
from configkit.config import validate
from configkit.skill_adapter import invoke_validate


@pytest.mark.parametrize("config, expected", [
    ({"timeout": 10}, []),
    ({"timeout": 0}, ["timeout must be positive"]),
    ({"timeout": -1, "extra": "retained"}, ["timeout must be positive"]),
])
def test_adapter_preserves_findings(config, expected):
    events = []
    assert validate(config) == expected
    assert invoke_validate(config, events.append) == expected
    assert len(events) == 1
    assert events[0]["execution_status"] == "completed"


def test_missing_timeout_preserves_exception():
    events = []
    with pytest.raises(KeyError) as error:
        invoke_validate({}, events.append)
    assert error.value.args == ("timeout",)
    assert events[0]["execution_status"] == "failed"


def test_optional_sink_failure_preserves_result():
    def unavailable(event):
        raise OSError("fixture sink unavailable")
    assert invoke_validate({"timeout": 0}, unavailable) == [
        "timeout must be positive"
    ]
```

Run the host's existing test command plus `python -m pytest tests/test_skill_adapter.py`. Also call the unchanged console command with valid and invalid fixtures and compare its stdout and exit code to the baseline. Only report these checks as passed after executing them in the receiving repository.

Test the registered route too: resolve `domain:config-validator` through a fixed mapping to `invoke_validate`, inject `events.append`, and assert one event and the expected findings. Calling the legacy function directly cannot establish logging coverage. For sink-failure tests also make the diagnostic handler raise and verify both successful return values and original exceptions survive. Never import arbitrary callable names supplied by untrusted invocation input.

### Example B: independent invocations, linked reasoning and provenance views

For the invalid-timeout fixture above, the collector knows that `run-C17`, invocation `validate-1`, called `domain:config-validator`. The original validator returned one finding. It did not provide a rationale, so the trace must not invent one.

The following JSON is an illustrative linked-record excerpt, not a full BioAgents v1 envelope. A host adds its schema version, visibility declaration and real content digests when serializing complete records; the runnable v2 fixture demonstrates that serialization. Identity strings here are readable placeholders, not production identity-generation instructions.

```json
{
  "run_id": "run-C17",
  "reasoning_entry": {
    "entry_id": "entry-1",
    "event_key": "run-C17/validate-1/terminal",
    "invocation_id": "validate-1",
    "skill_id": "domain:config-validator",
    "label": "Configuration validator",
    "capability": "Check configuration values against the application's existing rules.",
    "reasoning_types": [],
    "mapping_status": "unassigned",
    "operation": "validate",
    "execution_status": "completed",
    "outcome": "One configuration finding returned.",
    "rationale_summary": "Rationale not recorded.",
    "inputs_used": ["fixture-C17"],
    "outputs": ["findings-C17"],
    "checks": [],
    "alternatives_considered": []
  },
  "provenance_activity": {
    "id": "validate-1",
    "actor": "domain:config-validator",
    "implementation": "configkit.config.validate",
    "used": ["fixture-C17"],
    "generated": ["findings-C17"],
    "execution_status": "completed"
  },
  "artifacts": [
    {"id": "fixture-C17", "locator": "fixtures/invalid-timeout.json"},
    {"id": "findings-C17", "locator": "artifacts/runs/config-check/run-C17/findings.json"}
  ]
}
```

The matching visible entry is:

```text
Configuration validator
Check configuration values against the application's existing rules.
Reasoning type: Unassigned

validate · completed · run-C17 / validate-1
One configuration finding returned.
Rationale not recorded.
Input: fixture-C17 · Output: findings-C17
```

For two executions of the same skill and input, record two independent invocations:

| Fact | First invocation | Second invocation |
|---|---|---|
| Stable skill identity | `domain:config-validator` | `domain:config-validator` |
| Run / invocation | `run-C17` / `validate-1` | `run-C18` / `validate-2` |
| Terminal event key | `run-C17/validate-1/terminal` | `run-C18/validate-2/terminal` |
| Result artifact | `findings-C17` | `findings-C18` |
| Terminal result digest | SHA-256 of first serialized findings artifact | SHA-256 of second serialized findings artifact |

The runnable fixture serializes findings as `{run_id, invocation_id, findings}` while preserving the validator's original list return. Thus even identical finding lists have independently bound result bytes. Its terminal snapshot references the artifact's identity and actual hash. Substituting the second run's findings file into the first run must fail verification; a matching skill label or finding count is insufficient. Fresh IDs in this synthetic example stand in for host-issued identities and assert no host attestation.

The run completed even though the configuration was invalid. No parity test appears under `checks`: those tests belong to migration validation, not this runtime invocation. If a workflow later edits the configuration, record a new activity and artifact, not a corrected history for this invocation.

For an old `legacy-log.json`, compute and retain its original byte hash, then write `legacy-log.normalized.json` and `.html` as separate artifacts. Record the source locator/hash, record pointer (for example `/entries/0`), projection version and metadata snapshot hashes in the view. Verify the original byte hash is unchanged after rendering. If its actor cannot be resolved, display “No skill recorded”; do not borrow the current workflow's skill list.

### Example C: a skill with computation and optional generated explanation

Suppose an existing `forecast-reviewer` skill computes forecast residuals and can explain the result with a configured model. Its two operations have different contracts:

| Field | `compute-residuals` | `explain-residuals` |
|---|---|---|
| Input | observed `[10, 12]`, predicted `[9, 14]` | computed residual artifact `[-1, 2]`, with convention predicted minus observed |
| Output | residuals `[-1, 2]` and mean absolute error `1.5` | prose such as “The forecast undershoots the first observation and overshoots the second.” |
| Execution character | exact deterministic | semantic generative |
| Generation when invoked | prohibited | required |
| Inclusion in workflow | required for this workflow | optional presentation step |
| Authority | computed metric | explanation of the supplied metric |
| Reasoning mapping | unassigned unless explicitly documented | unassigned unless explicitly documented |
| Provider unavailable | computation still completes | explanation unavailable; retain the computed result |

Do not classify both operations as generative because they share a package. Do not fabricate provider execution when the displayed explanation is a fixture. Test that any generated explanation leaves the residual artifact and its digest unchanged. An explanation claiming mean absolute error `2.0` fails fidelity review; it does not authorize modifying the computed result to match its prose.

### Example D: an instruction-only writer remains instruction-only

An existing `release-note-writer/SKILL.md` tells an agent to summarize supplied changes. Register it as a writer with instruction-based invocation and advisory output. Its catalog entry can say “Draft release notes from a supplied change list.” It must not advertise a local `run` command or a callable merely because catalog metadata exists. If an agent actually invokes those instructions, the host records that invocation; discovery alone produces no executed activity.

### Example E: a task with an observable finish

Instantiate A04 for the configuration adapter as follows:

```yaml
id: A04
status: planned
scope:
  - domain:config-validator through the new agent adapter
dependencies: [A03]
implementation_locations:
  - src/configkit/skill_adapter.py
  - tests/test_skill_adapter.py
verification_commands:
  - python -m pytest tests/test_config.py tests/test_skill_adapter.py
expected_results:
  - valid and invalid configuration outputs match the legacy function
  - missing timeout retains KeyError with the original argument
  - optional sink failure preserves the returned findings
  - each adapter call invokes validation once
  - rendered entries resolve to the same invocation and artifacts as provenance
observed_results: []
evidence_paths: []
```

The commands cover the example unit tests; add collector/integration tests for invocation count and rendered-record joins before closing the final two criteria. Populate observed results and evidence paths from actual runs. Finish this task when those criteria hold; adding an optimizer, a new model or a new workflow engine is not part of its completion condition.

### Example F: transfer the adoption instructions and fixture

An adoption kit contains `docs/portable-repository-adoption.md`, the maintenance skill's `SKILL.md`, `scripts/example_runtime.py`, `scripts/build_transfer.py`, the example/packager tests and a checksum manifest. Its manifest identifies an `agent-adoption-kit`, kit version `1.2`, and the guide entrypoint. Give the archive to a coding agent and run the commands in section 11. This ZIP does not register scientific capabilities and is not a Lunar domain package. Its maintenance skill coordinates repository work; it is not automatically exported with domain skills.

### Example G: export executable domain content to an independent host

This optional example applies to a BioAgents authoring checkout with its declared development environment. It is not a command to run inside the adoption kit. From that checkout root, the documented explicit-root export is:

```sh
uv run --group framework python scripts/repository/export_domain_package.py \
  --repository-root "$PWD" --catalog-root "$PWD/catalog" \
  --data-root "$PWD/data" --output bioagents.zip
```

Use a fresh output path. The exporter packages domain skill records, workflow registrations, declared runtime/dependency material, fixtures and referenced local dataset bytes. It checks complete referenced content before atomic publication. Remote descriptors remain references. The database-free command includes no saved reports; report export is a separate authoring operation. The host receives the ZIP, prepares the declared environment and runs domain code in isolated workers; it does not import a sibling BioAgents checkout into its application.

An example version transition is concrete: a host currently selects imported version `V1`. Editing a skill's instructions in the authoring repository leaves `V1` and its historical runs unchanged. Export to a new filename, import as a new owned version `V2`, prepare it and select `V2` for a subsequent invocation. Keep old runs bound to `V1`; do not relabel their skill snapshots using `V2` metadata.

| Check | Observable evidence | What it does not establish |
|---|---|---|
| Package validation | Declared schema, manifest and required byte closure pass the package validator | Host import, visibility or execution |
| Host visibility | Imported version is prepared/selected and the host exposes the intended descriptor and operation | That the operation ran |
| Observed invocation | Host-issued invocation identity, terminal event and exact result digest agree for that selected version | Correctness of every other capability or live provider mode |

A different host uses its own import/discovery mechanism and equivalent checks. Adoption-kit validation does not stand in for any of these host checks. Building, uploading or executing a real domain package is outside this kit's own release verification.

## 11. Optional executable transfer kit

The document remains usable alone. For runnable reference code, copy the complete transfer archive preserving its directory structure. The kit contains this guide and `project-skills/repository-adoption/portable-repository-adopter/`, with an instruction-based adoption skill, a standard-library Python example and its tests. No provider credentials or BioAgents imports are needed. Do not install only the skill directory while discarding its referenced guide.

From the extracted archive root, using Python 3.10 or newer:

```sh
python3 -m unittest discover -s project-skills/repository-adoption/portable-repository-adopter/tests -v
python3 project-skills/repository-adoption/portable-repository-adopter/scripts/example_runtime.py --output-dir example-run
```

The example creates a new output directory and demonstrates a fixed synthetic configuration fixture, a registered adapter, linked reasoning/provenance and an HTML view. It does not inspect, instrument or certify the receiving application. Its versioned envelope is `repository-adoption.example/v2`, distinct from BioAgents v1 and domain package format v1; the fixture rejects unsupported profile versions. Tests establish the reference example's behavior; migration checks must still exercise the host's actual entrypoints. Adapt the collector boundary, not its synthetic validator, to the host.

The reference collector handles synchronous invocations, creates fresh identities for each, and validates their specific artifact/identity/result-digest joins; it is not a general schema validator or concurrent event collector. The host must retain its own concurrency, retry, cancellation and persistence contracts when adopting the pattern.

To rebuild the kit, run `python3 project-skills/repository-adoption/portable-repository-adopter/scripts/build_transfer.py --output adoption-kit-copy.zip` from the extracted root. Publication requires a filesystem supporting same-directory hard links: the builder validates a temporary archive and links it into place without overwriting an existing destination. Unsupported publication fails without a final archive; choose a supporting filesystem rather than weakening the no-overwrite guarantee.

Use the adoption skill when carrying out A01–A08. No new model-powered reasoning skills are needed for migration. Existing host capabilities may perform inventory, writing and testing; the added skill coordinates their use and defines completion.

## 12. BioAgents source conventions consulted

These repository-relative references document the origin of this specification. They are optional background, not execution dependencies for the receiving agent:

- `AGENTS.md` and `catalog/SKILLS.md`: canonical roots, role/theme/cluster layout, identity and artifact placement.
- `docs/skill-universalization-model.md`: additive interfaces, field origins, invocation/independence distinctions and compatibility; its historical local-planner description is superseded by root ownership instructions.
- `docs/reference/skill-operation-profiles.md`: operation-level execution and generation boundaries.
- `docs/reasoning-logs.md` and `catalog/schemas/reasoning-log-v1.schema.json`: public trace fields and metadata preamble.
- `catalog/runtime/reasoning_log.py`: validation, object digests and Markdown projection.
- `project-skills/skill-governance/planner-skill-registration/SKILL.md`: authored contracts, conversational interface and independent-host registration.
- `docs/migrations/generic-platform/README.md`: completed application/planner transfer and explicit-root export command.
- `catalog/integrations/domain_package/metadata.py` and `format/skills-v1.schema.json`: actual exported record construction and pinned schema.
- `catalog/integrations/domain_package/README.md`: runtime closure and host authority; its temporary source-app compatibility sentence is superseded by the completed migration.
- `docs/application-data-provenance-contracts.md`: invocation and terminal-result correlation.

Reuse these conventions rather than BioAgents-specific counts, absolute paths, domain taxonomies, environment registrations or release machinery. The receiving repository keeps its own name and working application.
