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
Mathformer Rocq autoformalization: Contrapositive
Case id: wiki_contrapositive
Concepts: proposition, implication, negation, contradiction
Related Lean target: WikiLevelGold.wiki_contrapositive
Source theorem: Let $P$ and $Q$ be propositions. If $P$ implies $Q$, then not $Q$ implies not $P$.
Source proof idea: Assume first that $h : P \to Q$. To prove the desired implication, assume $\neg Q$ and suppose, for contradiction, that $P$ holds. Applying $h$ to the proof of $P$ gives a proof of $Q$, contradicting $\neg Q$. Therefore $P$ is impossible, so $\neg P$ holds. Hence $\neg Q \to \neg P$.
Generated note: this file is deterministic and intentionally uses only
small local definitions plus the Rocq standard library when arithmetic
automation is needed.
*)

Theorem wiki_contrapositive :
  forall P Q : Prop, (P -> Q) -> ~ Q -> ~ P.
Proof.
  intros P Q hpq hnq hp.
  apply hnq.
  apply hpq.
  exact hp.
Qed.
