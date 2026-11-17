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
  Keep Isabelle examples available alongside Lean and ATP artifacts for cross-system comparison.

Intent:
  Represent formalization experiments in a theorem-prover format with clear session boundaries.

Function:
  Defines Isabelle theories and ROOT sessions used by execution and alignment tests.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
*)

theory AutoformalizedWikiInjectiveComposition
  imports Main
begin

text \<open>
Original source (NL): Let $A$, $B$, and $C$ be sets, and let $f : A \to B$ and $g : B \to C$ be functions. If $f$ and $g$ are injective, then the composite function $g \circ f : A \to C$ is injective.

Original source (LaTeX): Let $A$, $B$, and $C$ be sets, and let $f : A \to B$ and $g : B \to C$ be functions. If $f$ and $g$ are injective, then the composite function $g \circ f : A \to C$ is injective.

Original proof idea (NL): Let $x,y \in A$ and suppose that $(g \circ f)(x) = (g \circ f)(y)$. By the definition of composition, this says $g(f(x)) = g(f(y))$. Since $g$ is injective, it follows that $f(x) = f(y)$. Since $f$ is injective, it follows that $x = y$. Therefore $g \circ f$ is injective.

Original proof idea (LaTeX): Let $x,y \in A$ and suppose that $(g \circ f)(x) = (g \circ f)(y)$. By the definition of composition, this says $g(f(x)) = g(f(y))$. Since $g$ is injective, it follows that $f(x) = f(y)$. Since $f$ is injective, it follows that $x = y$. Therefore $g \circ f$ is injective.

Formalized target (Isabelle/HOL): inj f \<Longrightarrow> inj g \<Longrightarrow> inj (g \<circ> f)

Generated note: This Isabelle/HOL formalization uses arbitrary types instead of
set-coded domains, matching the controlled target for the Wikipedia-level case.
Source anchors: synthetic_wiki_injective_composition
\<close>

text \<open>
Source-backed theorem: composition preserves injectivity.  The following proof
follows the original proof flow: expand composition, use injectivity of g, then
use injectivity of f.
\<close>

theorem wiki_injective_comp:
  fixes f :: "'a \<Rightarrow> 'b"
    and g :: "'b \<Rightarrow> 'c"
  assumes hf: "inj f"
    and hg: "inj g"
  shows "inj (g \<circ> f)"
proof (rule injI)
  fix x y
  assume hxy: "(g \<circ> f) x = (g \<circ> f) y"
  have "g (f x) = g (f y)"
    using hxy by simp
  then have "f x = f y"
    using hg unfolding inj_def by blast
  then show "x = y"
    using hf unfolding inj_def by blast
qed

end
