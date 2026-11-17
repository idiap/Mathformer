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
Mathformer Rocq autoformalization: Composition Of Injective Functions
Case id: wiki_injective_composition
Concepts: function, composition, injective, type_variables
Related Lean target: WikiLevelGold.wiki_injective_comp
Source theorem: Let $A$, $B$, and $C$ be sets, and let $f : A \to B$ and $g : B \to C$ be functions. If $f$ and $g$ are injective, then the composite function $g \circ f : A \to C$ is injective.
Source proof idea: Let $x,y \in A$ and suppose that $(g \circ f)(x) = (g \circ f)(y)$. By the definition of composition, this says $g(f(x)) = g(f(y))$. Since $g$ is injective, it follows that $f(x) = f(y)$. Since $f$ is injective, it follows that $x = y$. Therefore $g \circ f$ is injective.
Generated note: this file is deterministic and intentionally uses only
small local definitions plus the Rocq standard library when arithmetic
automation is needed.
*)

Definition Injective {A B : Type} (f : A -> B) : Prop :=
  forall x y : A, f x = f y -> x = y.

Theorem wiki_injective_comp :
  forall (A B C : Type) (f : A -> B) (g : B -> C),
    Injective f -> Injective g -> Injective (fun x => g (f x)).
Proof.
  unfold Injective.
  intros A B C f g hf hg x y hxy.
  apply hf.
  apply hg.
  exact hxy.
Qed.
