<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

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

# Lean + mathlib Lookup Workflow

Compatibility note: canonical user-facing guidance now lives in
`mathlib-concept-candidate-mapper` for ranked declaration/module discovery and
`mathlib-candidate-verifier` for bounded Lean `#check` verification. This file remains
as legacy detailed command material for the shared lookup runtime.

## Preconditions

- Run from the Lean project root.
- Ensure mathlib dependency is available:

```bash
lake update
lake build
```

## Fast Concept Lookup

Use the bundled script:

```bash
python3 skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py \
  --proof-file inputs/informal_proof.txt \
  --top-k 10
```

Or provide concepts directly:

```bash
python3 skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py \
  --concept commutative \
  --concept associative \
  --concept injective
```

For machine-readable output:

```bash
python3 skills/mathlib/informal-proof-mathlib-concepts/scripts/map_mathlib_concepts.py \
  --proof-file inputs/informal_proof.txt \
  --json > concept_map.json
```

## Verify Candidates in Lean

Create a scratch file and check declarations with `#check`:

```lean
import Mathlib

#check Nat.add_comm
#check Nat.add_assoc
#check Function.Injective
```

Then run:

```bash
lake env lean Scratch.lean
```

## Useful Manual Search Commands

Search declaration headers by token:

```bash
rg --glob '*.lean' --line-number '^(theorem|lemma|def|class|structure|inductive|instance)\\s+.*comm' .lake/packages/mathlib/Mathlib
```

Search by notation or symbol usage:

```bash
rg --glob '*.lean' --line-number 'dvd|\|\^|∑|Finset' .lake/packages/mathlib/Mathlib
```
