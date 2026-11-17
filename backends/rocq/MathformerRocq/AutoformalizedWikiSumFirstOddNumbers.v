(*
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
#
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# Neuro-symbolic AI Group
#
# SPDX-License-Identifier: MIT
*)

(*
File Documentation

Motivation:
  Provide a complete Rocq proof artifact for a controlled Mathformer autoformalization case.

Intent:
  Preserve the source theorem while expressing the statement and proof in Rocq vernacular.

Function:
  Defines any minimal local concepts required by the case, states the theorem, and proves it without placeholders.

Maintenance Notes:
  Regenerate with `scripts/run_rocq_autoformalization.py` after template or fixture changes.
*)

(*
Mathformer Rocq autoformalization: Sum Of The First Odd Numbers
Case id: wiki_sum_first_odd_numbers
Concepts: natural_number, finite_sum, induction, arithmetic_normalization
Related Lean target: WikiLevelGold.wiki_sum_first_odd_numbers
Source theorem: For every natural number $n$, \[ 1 + 3 + 5 + \cdots + (2n-1) = n^2. \]
Source proof idea: We prove the result by induction on $n$. For $n=0$, the sum has no terms and is $0$, which is $0^2$. Assume that the sum of the first $n$ odd numbers is $n^2$. The next odd number is $2n+1$, so the sum of the first $n+1$ odd numbers is \[ n^2 + (2n+1). \] But \[ n^2 + 2n + 1 = (n+1)^2. \] Therefore the result holds for $n+1$. By induction, it holds for every natural number $n$.
Generated note: this file is deterministic and intentionally uses only
small local definitions plus the Rocq standard library when arithmetic
automation is needed.
*)

From Stdlib Require Import Arith Lia.

Fixpoint sum_first_odds (n : nat) : nat :=
  match n with
  | 0 => 0
  | S k => sum_first_odds k + (2 * k + 1)
  end.

Theorem wiki_sum_first_odd_numbers :
  forall n : nat, sum_first_odds n = n * n.
Proof.
  intro n.
  induction n as [| n ih].
  - reflexivity.
  - simpl.
    rewrite ih.
    lia.
Qed.
