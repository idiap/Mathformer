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
Mathformer Rocq autoformalization: Intersection Distributes Over Union
Case id: wiki_set_inter_union_distrib
Concepts: set, intersection, union, extensionality, case_split
Related Lean target: WikiLevelGold.wiki_set_inter_union_distrib
Source theorem: Let $A$, $B$, and $C$ be subsets of a set $X$. Then \[ A \cap (B \cup C) = (A \cap B) \cup (A \cap C). \]
Source proof idea: We prove equality by showing that the two sets have the same elements. Let $x \in A \cap (B \cup C)$. Then $x \in A$ and $x \in B \cup C$. If $x \in B$, then $x \in A \cap B$, so $x \in (A \cap B) \cup (A \cap C)$. If $x \in C$, then $x \in A \cap C$, so again $x \in (A \cap B) \cup (A \cap C)$. Conversely, let $x \in (A \cap B) \cup (A \cap C)$. If $x \in A \cap B$, then $x \in A$ and $x \in B$, hence $x \in A \cap (B \cup C)$. If $x \in A \cap C$, then $x \in A$ and $x \in C$, hence $x \in A \cap (B \cup C)$. Thus the two sets are equal.
Generated note: this file is deterministic and intentionally uses only
small local definitions plus the Rocq standard library when arithmetic
automation is needed.
*)

Definition Same_set {U : Type} (X Y : U -> Prop) : Prop :=
  forall x : U, X x <-> Y x.

Theorem wiki_set_inter_union_distrib :
  forall (U : Type) (A B C : U -> Prop),
    Same_set
      (fun x => A x /\ (B x \/ C x))
      (fun x => (A x /\ B x) \/ (A x /\ C x)).
Proof.
  intros U A B C.
  unfold Same_set.
  intro x.
  split.
  - intros [ha [hb | hc]].
    + left. split; assumption.
    + right. split; assumption.
  - intros [[ha hb] | [ha hc]].
    + split; [assumption | left; assumption].
    + split; [assumption | right; assumption].
Qed.
