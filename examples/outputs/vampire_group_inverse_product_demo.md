<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Preserve a compact demonstration output for the README ATP example.

Intent:
  Summarize the generated Vampire result without requiring the reader to inspect
  every local artifact under artifacts/.

Function:
  Records the status, promoted lemmas, minimized premise set, and main generated
  files for the inverse-of-product group theorem demonstration.

Maintenance Notes:
  Regenerate or revise this summary when the ATP demonstration artifacts change.
-->

# Vampire Group Inverse Product Demo

Input:

- [Group inverse product statement](../vampire_group_inverse_product_input.md)

Theorem:

```text
inv(mul(x,y)) = mul(inv(y),inv(x))
```

Generated run:

```text
artifacts/vampire_atp/atp_function_demo/
```

Status:

- `ok`: `true`
- `winning_status`: `Theorem`
- formal proof format: TPTP/TSTP

Promoted generated helper lemmas:

- `product_candidate_right_inverse`
- `product_candidate_left_inverse`
- `two_sided_inverse_unique`

Final minimized premise IDs:

- `generated_product_candidate_right_inverse`
- `generated_product_candidate_left_inverse`
- `generated_two_sided_inverse_unique`

Generated files in the local artifact root:

- `candidate_01_group_inverse_of_product_reverses_order.p`
- `candidate_01_group_inverse_of_product_reverses_order.proof.tstp`
- `candidate_01_group_inverse_of_product_reverses_order.informal.md`
- `discovery_report.json`
- `premise_selection_report.json`
- `premise_generation_report.json`
- `premise_minimization_report.json`

Informal proof sketch:

1. The candidate inverse of `mul(x,y)` is `mul(inv(y),inv(x))`.
2. Multiplying `mul(x,y)` by this candidate and reassociating reduces
   `mul(y,inv(y))` and `mul(x,inv(x))` to the identity.
3. The reverse multiplication is analogous.
4. Vampire proves the candidate-inverse and uniqueness helper lemmas separately,
   then proves the target equality from the promoted helpers.
