---
name: portable-repository-adopter
description: Adapt an existing repository to typed skills, explicit code ownership, and consistent public reasoning and provenance logs while preserving its supported functions. Use for a requested repository-organization migration or review.
---

# Portable repository adopter

This is an instruction-based repository-maintenance skill. It does not automatically execute a migration or provide a new workflow engine.

Read the [self-contained adoption guide](../../../docs/portable-repository-adoption.md) before implementation. It defines the target semantics, finite A01–A08 tasks, compatibility obligations and worked examples. The distribution preserves this relative path; copy the complete archive when transferring the skill.

## Inputs and outcome

Input is a receiving repository, the user's scope and its existing agent/development instructions. Inspect its actual entrypoints and skill mechanisms. Record a finite set of capabilities and invocation routes before editing. If scope is already specified, use it without requesting it again.

Output is an additive migration of that set, with canonical metadata, resolvable invocation bindings, suitable shared logging, documentation, observed compatibility checks and a completion record. Keep the implementation in the host's language and package structure where practical.

## Execution

1. Inventory ownership, commands, public interfaces and baseline behavior. Preserve pre-existing changes.
2. Map domain versus host ownership. Keep domain role/theme/cluster/skill hierarchy and internal request adapters distinct; do not register every adapter as a skill. Reuse the host's discovery, runtime and documentation infrastructure. Do not recreate the retired BioAgents app/planner or import a sibling host checkout at runtime. Separate role, ownership, execution character, invocation mechanism and reasoning mappings. Record unknowns explicitly.
3. Register adapters around existing implementations. Distinguish authored semantic/machine contracts from generated discovery records and conversational projections. Where an independent host imports domain packages, export, import, prepare and select the immutable version; retain another host's equivalent discovery mechanism. Test through the registered route, not only through the adapter function. Declare the injected logging context separately from user input.
4. Exercise the pilot's outputs, errors and trace joins. Use fresh invocation/event identities and bind terminal snapshots to the exact result artifact and digest; preserve recorded detail when optional generated presentation is absent. Preserve domain behavior when optional logging fails. Extend the proven pattern only to the frozen scope.
5. Generate documentation from the declared authoritative fields, check drift, and report observed verification and remaining limitations. Stop when A01–A08's agreed scope is satisfied.

## Reference code

For a runnable synthetic Python example, execute:

```sh
python3 scripts/example_runtime.py --output-dir example-run
python3 -m unittest discover -s tests -v
```

These commands are relative to this skill directory and require Python 3.10+. The v2 example profile demonstrates a registered adapter, independent invocation identities and exact-result-linked traces; it is not an automatic host instrumentation tool. Read it before adapting it. The tests do not certify a receiving repository.

For transfer packaging from the source checkout, use `python3 scripts/build_transfer.py --output adoption-kit.zip`. This builds an agent adoption kit (version 1.2), copying only the enumerated guide, skill and example/test files with a checksum manifest. It validates a temporary ZIP before same-directory hard-link publication; use a filesystem supporting hard links and a fresh destination. Existing archives are never overwritten. This kit is not a host-importable domain package; it does not collect repository data or execute the receiving application.

## Quality criteria

- Keep legacy returns, imports, commands, errors and side effects stable over the tested scope.
- Preserve signed or digest-bound historical source records; create enriched views separately.
- Record missing rationale as missing. A mapped reasoning type is not execution evidence.
- Keep computation and optional generated presentation distinct; preserve computed artifacts.
- Keep domain conclusions in the main report and execution details in linked logs.
- Keep package validation, selected-host visibility and observed invocation as separate checks. Imported versions and historical runs retain their original identities.
- Report untested routes explicitly. Do not imply installation in a host or live provider verification from package validation.

If the user requests review only, return concrete findings and repairs instead of performing a migration. Completion does not require new research, a new planner or additional speculative skills.
