---
name: vampire-proof-informalizer
description: Turn Vampire SZS/TSTP proof results into concise informal proof explanations while preserving the formal proof as the authoritative artifact. Use when a workflow must return both a formal Vampire proof and a readable mathematical proof sketch.
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

# Vampire Proof Informalizer

## Workflow

1. Keep the raw TSTP proof unchanged as the formal proof artifact.
2. Build the informal proof from the generated TPTP problem, the SZS status, and the TSTP proof result.
3. State the original informal problem when available.
4. Explain the proof at the level of the mathematical predicates, not Vampire's low-level clausification steps.
5. Mention the formal connection: Vampire proves the conjecture by refuting its negation and deriving a contradiction.
6. Persist the informal proof in both Markdown and structured JSON when the surrounding workflow writes artifacts.

## Interface

Prefer the repo implementation in `backends.atp.MathformerATP.vampire`:

- `InformalProof`: structured informal proof payload
- `informalize_proof(result, problem=..., problem_path=...)`: render a result into `InformalProof`
- `ATPResult.formal_proof`: raw TSTP proof text
- `ATPResult.informal_proof`: informalized proof object
- `discover_proof(...)`: returns `winning_formal_proof` and `winning_informal_proof`

## Quality Bar

An acceptable informalization should include:

- theorem statement or source statement
- proof status and formal proof step count
- readable numbered proof steps
- a clear link back to the TSTP proof as the authoritative object
- no claim stronger than the encoded TPTP problem proves

For the subset-transitivity template, the proof should explain the arbitrary-element argument:
assume `member(x,r)`, use `subset(r,s)` to get `member(x,s)`, use `subset(s,t)` to get
`member(x,t)`, then conclude `subset(r,t)`.
