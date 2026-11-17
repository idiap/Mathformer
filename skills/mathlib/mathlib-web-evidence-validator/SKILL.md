---
name: mathlib-web-evidence-validator
description: Validate web-sourced mathlib grounding packets before they influence Lean drafting, imports, or Mathformerlib accumulation. Use to enforce official-source evidence, retrieval-aid limits, query provenance, uncertainty preservation, and local Lean verification handoffs for declarations, modules, imports, notation, and theorem-shape claims.
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

# Mathlib Web Evidence Validator

## Purpose

Use this skill after web search produces candidate mathlib facts. It decides whether
the packet can be used as grounding evidence, needs local verification, or must be
blocked.

Hook:
- `mathlib.web_evidence`

## Workflow

1. Collect web findings into the packet shape described in `references/evidence_packet_schema.json`.
2. Run `scripts/validate_mathlib_web_evidence.py`.
3. Treat source status as follows:
   - `grounded`: official source plus local Lean verification are present.
   - `needs_local_verification`: official source is present but local Lean checks are missing.
   - `blocked`: source is unsupported, retrieval-only, or contradicts local verification.
   - retrieval-aid discovery can become `grounded` only when the packet also has an
     official mathlib docs/source corroboration URL and local verification.
4. Send accepted declarations to `mathlib-candidate-verifier` and accepted imports to
   `lean-import-context-verifier` whenever verification is not already recorded.
5. Do not inject candidate-only web claims into drafting prompts as established facts.

## Commands

Validate a packet:

```bash
python3 skills/mathlib/mathlib-web-evidence-validator/scripts/validate_mathlib_web_evidence.py \
  --packet artifacts/mathlib/web-grounding-packet.json \
  --json
```

Self-test:

```bash
python3 skills/mathlib/mathlib-web-evidence-validator/scripts/validate_mathlib_web_evidence.py \
  --self-test \
  --json
```
