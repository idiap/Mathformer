---
name: vampire-atp-orchestrator
description: Autoformalize small informal mathematics into TPTP first-order problems, run Vampire as an automated theorem prover, parse SZS statuses and TSTP formal proofs, produce informalized proof explanations, and package proof-discovery artifacts. Use when Codex needs a Vampire ATP proof search, a TPTP interface, an informal-to-ATP smoke test, or a first-order proof-discovery workflow that returns both formal and informal proofs.
---

<!--
File Documentation

Motivation:
  Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

Intent:
  Tell coding agents what context to load, what invariants to preserve, and how to validate their work.

Function:
  Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Vampire ATP Orchestrator

## Workflow

1. Confirm Vampire is installed with `vampire --version`, or set `VAMPIRE_BIN` / pass `--vampire-bin` to an executable path.
2. Prefer the repo interface in `backends.atp.MathformerATP.vampire` over raw subprocess calls.
3. Use explicit TPTP files when the formal problem is already known.
4. Use aggressive autoformalization only for templates supported by `aggressive_autoformalize`; unsupported statements should become explicit TPTP candidates before proof search.
5. Run proof search with a bounded `--time-limit`.
6. Treat success as an SZS proof status such as `Theorem` plus a proof object, not merely process exit code.
7. Preserve artifacts: candidate `.p`, result JSON, formal proof `.proof.tstp`, informal proof `.informal.md`, informal proof `.informal.json`, and a discovery report.
8. Apply the `vampire-proof-informalizer` standard when packaging the readable proof.
9. Report both `winning_formal_proof` and `winning_informal_proof` when proof discovery succeeds.

## Commands

Run an existing TPTP problem:

```bash
python scripts/run_vampire_atp.py --problem path/to/problem.p --time-limit 10 --json
```

Autoformalize an informal subset-transitivity statement and search:

```bash
python scripts/run_vampire_atp.py \
  --text-file tests/atp/informal_subset_transitive.md \
  --source-url https://proofwiki.org/wiki/Subset_Relation_is_Transitive \
  --artifact-root artifacts/vampire_atp/subset_transitive_web \
  --json
```

Run the representative regression:

```bash
python tests/atp/run_vampire_interface.py --json
```

## Interface

Use these Python entrypoints:

- `ATPProblem`: structured TPTP problem with informal provenance
- `ATPResult`: parsed Vampire execution result with formal and informal proof fields
- `InformalProof`: human-readable proof explanation tied to the formal result
- `VampireRunner().run_path(path, time_limit=10)`
- `VampireRunner().run_problem(problem, output_path=path)`
- `aggressive_autoformalize(text, source_url=...)`
- `discover_proof(text, artifact_root=..., source_url=...)`

## Acceptance

A completed run should report:

- `ok: true`
- `winning_status: Theorem` or another proof status
- at least one persisted TPTP candidate
- a non-empty TSTP proof when Vampire emits proof output
- a non-empty informalized proof payload
- persisted formal and informal proof paths in the report
