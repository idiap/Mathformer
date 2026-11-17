/-
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
#
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# Neuro-symbolic AI Group
#
# SPDX-License-Identifier: MIT
-/

/-
File Documentation

Motivation:
  Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

Intent:
  Encode regression checks that catch parser breakage, semantic drift, and missing workflow evidence.

Function:
  Contains executable tests, fixtures, and manifests used for local and CI validation.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-/

import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Data.Set.Basic
import Mathlib.Order.Monotone.Basic
import Mathlib.Tactic.Ring

namespace WikiLevelGold

/-- If `P` implies `Q`, then not `Q` implies not `P`. -/
theorem wiki_contrapositive {P Q : Prop} (h : P → Q) : ¬ Q → ¬ P := by
  intro hnq hp
  exact hnq (h hp)

/-- The composition of two injective functions is injective. -/
theorem wiki_injective_comp {α β γ : Type*} {f : α → β} {g : β → γ}
    (hf : Function.Injective f) (hg : Function.Injective g) :
    Function.Injective (fun x => g (f x)) := by
  intro x y hxy
  exact hf (hg hxy)

/-- The composition of two monotone functions between preorders is monotone. -/
theorem wiki_monotone_comp {α β γ : Type*} [Preorder α] [Preorder β] [Preorder γ]
    {f : α → β} {g : β → γ} (hf : Monotone f) (hg : Monotone g) :
    Monotone (fun x => g (f x)) := by
  intro x y hxy
  exact hg (hf hxy)

/-- Set intersection distributes over set union. -/
theorem wiki_set_inter_union_distrib {α : Type*} (A B C : Set α) :
    A ∩ (B ∪ C) = (A ∩ B) ∪ (A ∩ C) := by
  simpa using Set.inter_union_distrib_left A B C

/-- The sum of the first `n` odd natural numbers is `n ^ 2`. -/
theorem wiki_sum_first_odd_numbers (n : ℕ) :
    (∑ i ∈ Finset.range n, (2 * i + 1)) = n ^ 2 := by
  induction n with
  | zero =>
      simp
  | succ n ih =>
      rw [Finset.sum_range_succ, ih]
      ring

end WikiLevelGold
