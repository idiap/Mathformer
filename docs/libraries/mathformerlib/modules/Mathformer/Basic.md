<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make the framework understandable without requiring readers to inspect implementation details first.

Intent:
  Explain architecture, installation, principles, tutorials, licensing, and generated library outputs.

Function:
  Provides human-facing documentation that should stay aligned with tested behavior and code paths.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# `Mathformer.Basic`

[Back to index](../../INDEX.md)

## Metadata

- Source: [backends/lean/Mathformer/Basic.lean](../../../../../backends/lean/Mathformer/Basic.lean)
- Status: `candidate`
- SHA-256: `c9902e82c349ef0bc4ae3afb8d93170f00c919d75d6c17743274eea3729f36de`
- Declarations: `1`

## Imports

```lean
import Mathlib
```

## Declarations

- [`hello`](#hello) (def, line 8)

## `hello`

- Kind: `def`
- Source line: [backends/lean/Mathformer/Basic.lean:8](../../../../../backends/lean/Mathformer/Basic.lean#L8)

**Generated Notes**

Minimal project seed definition used by the default Lean template.

**Generated LaTeX**

```latex
this declaration has no mathematical content.
```

**Lean**

```lean
def hello := "world"

/--
Generated note (NL): Basic arithmetic smoke example for commutativity of natural
number addition.
Generated equivalent (LaTeX): `a+b=b+a`.
-/
example (a b : Nat) : a + b = b + a := by
  simpa using Nat.add_comm a b
```
