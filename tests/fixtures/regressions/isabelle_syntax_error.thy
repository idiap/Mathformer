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
  Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

Intent:
  Encode regression checks that catch parser breakage, semantic drift, and missing workflow evidence.

Function:
  Contains executable tests, fixtures, and manifests used for local and CI validation.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
*)

theory Isabelle_Syntax_Error
  imports Main
begin

lemma bad: "True"
  by

end
