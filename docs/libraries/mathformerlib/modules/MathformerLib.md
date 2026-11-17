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

# `MathformerLib`

[Back to index](../INDEX.md)

## Metadata

- Source: [libraries/MathformerLib.lean](../../../../libraries/MathformerLib.lean)
- Status: `accepted`
- SHA-256: `3650f670cccec457337a259937fe43b5b51cde8aa1a3348d5272fe60e0a7e42a`
- Declarations: `0`

## Imports

```lean
import MathformerLib.Basic
```

## Module Source Notes

**Comment**

Root module for Mathformerlib, the curated Mathformer-side library of reusable formalizations accumulated from autoformalization runs. `MathformerLib` is intentionally separate from `Mathformer`: draft artifacts may live under `Mathformer`, while promoted reusable entries should be collected here only after the Mathformerlib promotion gates pass.
