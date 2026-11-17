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

# Mathformer Library

Generated Markdown documentation for Mathformer Lean modules.

## Summary

- Generated at UTC: `2026-06-06T10:06:01.767389+00:00`
- Modules: `3`
- Declarations: `99`
- Theorem-like declarations: `63`
- Status counts: `{"candidate": 3}`

## Modules

| Module | Status | Declarations | Lean Source |
| --- | --- | ---: | --- |
| [`Mathformer.AutoformalizedCBTChapter1`](modules/Mathformer/AutoformalizedCBTChapter1.md) | `candidate` | 23 | [backends/lean/Mathformer/AutoformalizedCBTChapter1.lean](../../../backends/lean/Mathformer/AutoformalizedCBTChapter1.lean) |
| [`Mathformer.AutoformalizedCBTChapter2`](modules/Mathformer/AutoformalizedCBTChapter2.md) | `candidate` | 34 | [backends/lean/Mathformer/AutoformalizedCBTChapter2.lean](../../../backends/lean/Mathformer/AutoformalizedCBTChapter2.lean) |
| [`Mathformer.AutoformalizedCBTChapter3`](modules/Mathformer/AutoformalizedCBTChapter3.md) | `candidate` | 42 | [backends/lean/Mathformer/AutoformalizedCBTChapter3.lean](../../../backends/lean/Mathformer/AutoformalizedCBTChapter3.lean) |

## Declarations


### [`Mathformer.AutoformalizedCBTChapter1`](modules/Mathformer/AutoformalizedCBTChapter1.md)

- [`Mathformer.AutoformalizedCBTChapter1.FirstGenerationPrinciple`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-firstgenerationprinciple) `structure`
- [`Mathformer.AutoformalizedCBTChapter1.SecondGenerationPrinciple`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-secondgenerationprinciple) `structure`
- [`Mathformer.AutoformalizedCBTChapter1.LimitationPrinciple`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-limitationprinciple) `structure`
- [`Mathformer.AutoformalizedCBTChapter1.Denumerable`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-denumerable) `def`
- [`Mathformer.AutoformalizedCBTChapter1.Denumerable.exists_nat_surjection`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-denumerable-exists-nat-surjection) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.CantorIndexedUnion`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-cantorindexedunion) `def`
- [`Mathformer.AutoformalizedCBTChapter1.CantorPairMatrix`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-cantorpairmatrix) `def`
- [`Mathformer.AutoformalizedCBTChapter1.denumerable_union_theorem`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-denumerable-union-theorem) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.countable_union_of_countable_family`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-countable-union-of-countable-family) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.denumerable_cbt`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-denumerable-cbt) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.intermediate_subset_of_denumerable_countable`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-intermediate-subset-of-denumerable-countable) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.theorem1_nat_cannot_enumerate_powerset`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-theorem1-nat-cannot-enumerate-powerset) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.no_equiv_nat_powerset`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-no-equiv-nat-powerset) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.lemma2_nat_least_element`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-lemma2-nat-least-element) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.finite_descending_chain_bound_nat`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-finite-descending-chain-bound-nat) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.no_infinite_descending_sequence_nat`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-no-infinite-descending-sequence-nat) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.fundamental_countability_component`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-fundamental-countability-component) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.fundamental_finite_branch_countable`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-fundamental-finite-branch-countable) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.cantor_bernstein_for_II_modern`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-cantor-bernstein-for-ii-modern) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.cantor_bernstein_between_subsets`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-cantor-bernstein-between-subsets) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.union_theorem_countable_version`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-union-theorem-countable-version) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.countable_product_component`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-countable-product-component) `theorem`
- [`Mathformer.AutoformalizedCBTChapter1.nat_pair_set_countable`](modules/Mathformer/AutoformalizedCBTChapter1.md#mathformer-autoformalizedcbtchapter1-nat-pair-set-countable) `theorem`

### [`Mathformer.AutoformalizedCBTChapter2`](modules/Mathformer/AutoformalizedCBTChapter2.md)

- [`Mathformer.AutoformalizedCBTChapter2.SamePower`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-samepower) `def`
- [`Mathformer.AutoformalizedCBTChapter2.SamePower.refl`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-samepower-refl) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.SamePower.symm`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-samepower-symm) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.SamePower.trans`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-samepower-trans) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.SamePower.of_equiv`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-samepower-of-equiv) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.SamePower.comm_iff`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-samepower-comm-iff) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.SamePower.trans_of_and`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-samepower-trans-of-and) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.CantorPairMatrix`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-cantorpairmatrix) `def`
- [`Mathformer.AutoformalizedCBTChapter2.cantorPairMatrix_swap_samePower`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-cantorpairmatrix-swap-samepower) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.mem_cantorPairMatrix_swap_iff`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-mem-cantorpairmatrix-swap-iff) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.cantorPairMatrix_swap_equiv_nonempty`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-cantorpairmatrix-swap-equiv-nonempty) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.CantorScale`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-cantorscale) `structure`
- [`Mathformer.AutoformalizedCBTChapter2.HasPowerOf`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-haspowerof) `def`
- [`Mathformer.AutoformalizedCBTChapter2.FundamentalAlternative`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-fundamentalalternative) `structure`
- [`Mathformer.AutoformalizedCBTChapter2.LimitationConclusion`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-limitationconclusion) `structure`
- [`Mathformer.AutoformalizedCBTChapter2.SumLemmaConclusion`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-sumlemmaconclusion) `structure`
- [`Mathformer.AutoformalizedCBTChapter2.SequentLemmaConclusion`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-sequentlemmaconclusion) `structure`
- [`Mathformer.AutoformalizedCBTChapter2.HelicalInductionStep`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-helicalinductionstep) `structure`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_theorem1`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-theorem1) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_fundamental_theorem`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-fundamental-theorem) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_limitation_theorem`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-limitation-theorem) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_initial_segment_has_stage_power`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-initial-segment-has-stage-power) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_initial_fulfills_limitation`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-initial-fulfills-limitation) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_different_alephs_theorem`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-different-alephs-theorem) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_next_aleph_theorem`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-next-aleph-theorem) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_cantor_bernstein_theorem`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-cantor-bernstein-theorem) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_union_theorem`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-union-theorem) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_sum_lemma_mem`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-sum-lemma-mem) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_sum_lemma_power`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-sum-lemma-power) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_sequent_lemma`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-sequent-lemma) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_sequent_mem_class`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-sequent-mem-class) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_class_member_has_initial_power`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-class-member-has-initial-power) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_initial_mem_class`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-initial-mem-class) `theorem`
- [`Mathformer.AutoformalizedCBTChapter2.chapter2_scale_initial_segment_samePower_cumulative`](modules/Mathformer/AutoformalizedCBTChapter2.md#mathformer-autoformalizedcbtchapter2-chapter2-scale-initial-segment-samepower-cumulative) `theorem`

### [`Mathformer.AutoformalizedCBTChapter3`](modules/Mathformer/AutoformalizedCBTChapter3.md)

- [`Mathformer.AutoformalizedCBTChapter3.SamePower`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-samepower) `def`
- [`Mathformer.AutoformalizedCBTChapter3.SamePower.refl`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-samepower-refl) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.SamePower.symm`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-samepower-symm) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.SamePower.trans`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-samepower-trans) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.CantorWellDefinedSet`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-cantorwelldefinedset) `structure`
- [`Mathformer.AutoformalizedCBTChapter3.PowerClass`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-powerclass) `def`
- [`Mathformer.AutoformalizedCBTChapter3.mem_powerClass_iff`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-mem-powerclass-iff) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.inclusionEmbedding`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-inclusionembedding) `def`
- [`Mathformer.AutoformalizedCBTChapter3.embeddingTrans`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-embeddingtrans) `def`
- [`Mathformer.AutoformalizedCBTChapter3.samePower_of_subset_sandwich`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-samepower-of-subset-sandwich) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.PowerLE`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-powerle) `def`
- [`Mathformer.AutoformalizedCBTChapter3.powerLE_of_samePower_subset`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-powerle-of-samepower-subset) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.powerLE_refl`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-powerle-refl) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.powerLE_trans`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-powerle-trans) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.powerLE_antisymm_samePower`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-powerle-antisymm-samepower) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.PowerLT`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-powerlt) `def`
- [`Mathformer.AutoformalizedCBTChapter3.powerLT_asymm`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-powerlt-asymm) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.CantorComparability`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-cantorcomparability) `structure`
- [`Mathformer.AutoformalizedCBTChapter3.twoSetCBT_from_power_antisymmetry`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-twosetcbt-from-power-antisymmetry) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.ProperSubset`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-propersubset) `def`
- [`Mathformer.AutoformalizedCBTChapter3.CantorReflexive`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-cantorreflexive) `def`
- [`Mathformer.AutoformalizedCBTChapter3.not_powerLT_of_samePower`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-not-powerlt-of-samepower) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.ClosedUnit`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-closedunit) `def`
- [`Mathformer.AutoformalizedCBTChapter3.OpenClosedUnit`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-openclosedunit) `def`
- [`Mathformer.AutoformalizedCBTChapter3.CantorLemmaG`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-cantorlemmag) `structure`
- [`Mathformer.AutoformalizedCBTChapter3.cantorLemmaG_samePower`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-cantorlemmag-samepower) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.positiveNat`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-positivenat) `def`
- [`Mathformer.AutoformalizedCBTChapter3.natPositiveEquiv`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-natpositiveequiv) `def`
- [`Mathformer.AutoformalizedCBTChapter3.singleSetCBT_of_sandwich`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-singlesetcbt-of-sandwich) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.ContinuumComb`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-continuumcomb) `structure`
- [`Mathformer.AutoformalizedCBTChapter3.continuumComb_tooth_samePower`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-continuumcomb-tooth-samepower) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.FrameMatching`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-framematching) `structure`
- [`Mathformer.AutoformalizedCBTChapter3.sigmaFrameEquiv`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-sigmaframeequiv) `def`
- [`Mathformer.AutoformalizedCBTChapter3.frameMatching_taggedUnion_samePower`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-framematching-taggedunion-samepower) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.SingleSetFrameShift`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-singlesetframeshift) `structure`
- [`Mathformer.AutoformalizedCBTChapter3.singleSetFrameShift_samePower`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-singlesetframeshift-samepower) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.no_surjective_to_powerset`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-no-surjective-to-powerset) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.no_surjective_to_bool_functions`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-no-surjective-to-bool-functions) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.CantorComparisonProgram`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-cantorcomparisonprogram) `structure`
- [`Mathformer.AutoformalizedCBTChapter3.higher_not_samePower_continuum`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-higher-not-samepower-continuum) `theorem`
- [`Mathformer.AutoformalizedCBTChapter3.SecondNumberClassEvidence`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-secondnumberclassevidence) `structure`
- [`Mathformer.AutoformalizedCBTChapter3.secondClass_not_samePower_nat`](modules/Mathformer/AutoformalizedCBTChapter3.md#mathformer-autoformalizedcbtchapter3-secondclass-not-samepower-nat) `theorem`
