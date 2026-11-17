<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Prevent Lean-valid physics artifacts from being mistaken for complete
  autoformalizations when the target conclusion is carried by assumptions.

Intent:
  Define implementation todos for derivation-completeness gates, status
  semantics, recursive repair integration, and regression tests.

Function:
  Guides skill and workflow changes so generated Lean physics artifacts
  distinguish compilation, surface grounding, partial derivation, and complete
  autoformalization.

Maintenance Notes:
  Keep this file synchronized with physics Lean workflow scripts, final
  hypothesis reviewers, nonvacuity checks, and recursive grounding reports.
-->

# Lean Physics Derivation Completeness TODOs

## Goal

Make it impossible for a generated Lean physics artifact to be reported as a
complete autoformalization when it proves the target by unwrapping a
target-shaped hypothesis such as `PhysicalLawWitness <final conclusion>`.

The motivating failure case is
`libraries/MathformerPhysicsLib/Lean/formalphysics_0014/MathformerPhysics.lean`, which
compiles and uses MathformerPhysicsLib surfaces but does not derive the
Heisenberg bound from commutator, variance, and Cauchy-Schwarz support.

## Phase 1: Status Semantics

- [x] Replace ambiguous `level0_acceptance` language in physics Lean recursive
  reports with explicit statuses:
  - [x] `compiled_surface`
  - [x] `grounded_scaffold`
  - [x] `derivation_partial`
  - [x] `complete_autoformalization`
  - [x] `blocked_target_restating_assumption`
- [x] Enforce that `recursive_frontier_count > 0` prevents
  `complete_autoformalization`.
- [x] Update generated reports so `lean_all_ok` means only kernel/typechecking
  success.
- [x] Update user-facing report text to say whether an artifact is complete,
  partial, blocked, or only surface-grounded.

## Phase 2: Target-Restatement Detection

- [x] Add a deterministic checker that compares each theorem conclusion with
  hypotheses and support witnesses.
- [x] Flag direct target hypotheses whose proposition is syntactically or
  alpha-equivalent to the theorem conclusion.
- [x] Flag wrapper hypotheses such as:
  - [x] `PhysicalLawWitness <theorem conclusion>`
  - [x] `GeneratedSupportAssumption <theorem conclusion>`
  - [x] named law assumptions whose proposition is the theorem conclusion.
- [x] Flag proof endings that simply unwrap a target-shaped hypothesis, such as
  `exact physicalLawHolds h`.
- [x] Emit machine-readable findings with declaration name, hypothesis name,
  conclusion text, wrapper type, severity, and suggested repair route.

## Phase 3: Source-Step Obligation Ledger

- [x] Add a source-step obligation ledger for physics Lean derivations.
- [x] Extract or accept explicit obligations from source records:
  - [x] physical objects and quantities,
  - [x] definitions introduced in the source,
  - [x] intermediate equations,
  - [x] inequalities or theorem invocations,
  - [x] final target.
- [x] For each obligation, require one status:
  - [x] `proved`
  - [x] `mathlib_reused`
  - [x] `mathformerphysicslib_reused`
  - [x] `external_physical_law`
  - [x] `generated_support_labeled`
  - [x] `blocked`
- [x] Require `complete_autoformalization` to have no unresolved derivational
  obligations and no target-shaped external laws.
- [x] Store ledgers beside generated artifacts under
  `artifacts/physics_lean/<run>/<case_id>/derivation_obligations.json`.

## Phase 4: PhysicalLawWitness Policy

- [x] Introduce an explicit role field or companion metadata for
  `PhysicalLawWitness` usage:
  - [x] `source_law`
  - [x] `constitutive_assumption`
  - [x] `domain_assumption`
  - [x] `bridge_lemma`
  - [x] `generated_support`
- [x] Reject `PhysicalLawWitness` usage as complete support when its proposition
  is equivalent to the final target.
- [x] Require source anchors for `source_law` and `constitutive_assumption`
  witnesses.
- [x] Require a recursive frontier item when a witness represents a theorem
  that should eventually be derived from Mathlib or MathformerPhysicsLib.

## Phase 5: Reviewer Integration

- [x] Wire the mathematical final hypothesis reviewer into the Dirac recursive
  Lean batch after Lean compilation.
- [x] Wire the physics final hypothesis reviewer into the same batch.
- [x] Wire the Lean nonvacuity consistency checker into the same batch.
- [x] Add the new derivation-completeness checker to the same post-compile
  sequence.
- [x] Make any blocking finding from these reviewers prevent
  `complete_autoformalization`.
- [x] Preserve `compiled_surface` and `grounded_scaffold` status when compile
  and grounding pass but completeness fails.

## Phase 6: Recursive Repair Integration

- [x] Route target-restatement findings to the recursive repair controller.
- [x] For `formalphysics_0014`, generate repair frontier nodes for:
  - [x] variance definitions for fluctuation kets,
  - [x] expectation-value binding for `xMean` and `pMean`,
  - [x] commutator bridge from `[X, P] = i*hbar`,
  - [x] complex imaginary quotient to real scalar bound,
  - [x] Cauchy-Schwarz inequality over Hilbert inner products,
  - [x] nonnegativity and square-root/order step.
- [x] Require repair plans to modify foundation surfaces before changing the
  target theorem when missing objects are reusable.
- [x] Add a controlled stop condition when the missing support requires
  unbounded-operator domain theory that is outside the current bounded-operator
  abstraction.

## Phase 7: Generative Critic Probes

- [x] Add a generative probe asking whether the theorem still proves the target
  after removing all non-source `PhysicalLawWitness` hypotheses.
- [x] Add a generative probe asking which hypothesis is equivalent to the final
  conclusion.
- [x] Add a generative probe asking which source derivation step has no Lean
  proof object.
- [x] Add a generative probe asking which MathformerPhysicsLib object must be
  recursively built before the target theorem can become complete.
- [x] Require generative findings to cite deterministic evidence before they can
  block or repair an artifact.

## Phase 8: Regression Tests

- [x] Add a fixture based on `formalphysics_0014` that must compile but fail
  derivation completeness.
- [x] Add a fixture where the conclusion is directly passed as a hypothesis.
- [x] Add a fixture where `PhysicalLawWitness` wraps the target conclusion.
- [x] Add a fixture where a legitimate source law witness is not equivalent to
  the final target and should pass the target-restatement detector.
- [x] Add tests asserting that open recursive frontier prevents complete status.
- [x] Add tests asserting that `compiled_surface` remains available when
  derivation completeness fails.

## Phase 9: Router And Documentation

- [x] Add a natural-language router command such as "check whether this Lean
  physics artifact is a complete autoformalization".
- [x] Document the difference between compile validity, grounded scaffold,
  partial derivation, and complete autoformalization.
- [x] Add help text listing the new completeness gate in the router skill.
- [x] Link this TODO file from root `TODO.md` and relevant workflow docs.

## Acceptance Criteria

- [x] `formalphysics_0014` is reported as compiling but not complete.
- [x] The report names the target-restating `PhysicalLawWitness` as the blocker.
- [x] The report lists the missing Heisenberg derivation obligations.
- [x] No artifact with open recursive frontier can be labeled
  `complete_autoformalization`.
- [x] A legitimate theorem with non-target source-law assumptions can still pass
  the completeness gate.
- [x] The compact quality gate includes at least one test for target-restating
  hypothesis detection.
