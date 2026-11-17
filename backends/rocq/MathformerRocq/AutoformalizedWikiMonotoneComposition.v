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
Mathformer Rocq autoformalization: Composition Of Monotone Functions
Case id: wiki_monotone_composition
Concepts: preorder, monotone, composition, order_relation
Related Lean target: WikiLevelGold.wiki_monotone_comp
Source theorem: Let $A$, $B$, and $C$ be preordered sets. Let $f : A \to B$ and $g : B \to C$ be monotone functions. Then $g \circ f : A \to C$ is monotone.
Source proof idea: Let $x,y \in A$ and assume $x \le y$. Since $f$ is monotone, we have $f(x) \le f(y)$. Since $g$ is monotone, applying $g$ to this inequality gives $g(f(x)) \le g(f(y))$. This is exactly the statement that $g \circ f$ is monotone.
Generated note: this file is deterministic and intentionally uses only
small local definitions plus the Rocq standard library when arithmetic
automation is needed.
*)

Definition Monotone {A B : Type}
    (leA : A -> A -> Prop) (leB : B -> B -> Prop)
    (f : A -> B) : Prop :=
  forall x y : A, leA x y -> leB (f x) (f y).

Theorem wiki_monotone_comp :
  forall (A B C : Type)
    (leA : A -> A -> Prop) (leB : B -> B -> Prop) (leC : C -> C -> Prop)
    (f : A -> B) (g : B -> C),
    Monotone leA leB f -> Monotone leB leC g ->
    Monotone leA leC (fun x => g (f x)).
Proof.
  unfold Monotone.
  intros A B C leA leB leC f g hf hg x y hxy.
  apply hg.
  apply hf.
  exact hxy.
Qed.
