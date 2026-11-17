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

# `MathformerLib.Basic`

[Back to index](../../INDEX.md)

## Metadata

- Source: [libraries/MathformerLib/Basic.lean](../../../../../libraries/MathformerLib/Basic.lean)
- Status: `accepted`
- SHA-256: `e8fc3d8171ed6a06c3aff369dab8bd8aa79bfc51abdedf8c87673d9e5afc3e20`
- Declarations: `1`

## Imports

```lean
import Mathlib
```

## Module Source Notes

**Comment**

Basic namespace and seed declarations for Mathformerlib. This file is deliberately small. Generated formalizations should be promoted into topic-specific `MathformerLib.*` modules after registry and promotion checks.

## Declarations

- [`MathformerLib.true_intro`](#mathformerlib-true-intro) (theorem, line 15)

<a id="mathformerlib-true-intro"></a>

## `MathformerLib.true_intro`

- Kind: `theorem`
- Source line: [libraries/MathformerLib/Basic.lean:15](../../../../../libraries/MathformerLib/Basic.lean#L15)

**Generated Notes**

Smoke theorem proving that the Mathformerlib root builds.

**Generated LaTeX**

```latex
`\top`.
```

$$
\top
$$

**Lean**

```lean
theorem true_intro : True := by
  trivial

end MathformerLib
```
