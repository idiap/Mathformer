import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0074`, source index 74.
Field: Quantum Mechanics.
Informal target: imaginary-part identity for a Dirac braket.

Recursive grounding:
- braket values use `transitionAmplitude`;
- conjugate symmetry is explicit;
- the quotient `(⟨f|g⟩ - ⟨g|f⟩)/(2i)` uses `diracImaginaryQuotient`;
- the square identity is proved through the `Complex.im` projection bridge
  rather than by quotient and square witnesses.
-/


namespace Mathformer.Physics.FormalPhysics0074

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws

/-- Dirac-grounded imaginary-part square identity bridge. -/
theorem dirac_imaginary_part_identity_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (f g : HilbertStateCarrier ℂ H)
    (conjugate_symmetry :
      DiracConjugateSymmetryWitness
        (transitionAmplitude ℂ f g) (transitionAmplitude ℂ g f)) :
    (diracImaginaryQuotient (transitionAmplitude ℂ f g) (transitionAmplitude ℂ g f)) ^ 2 =
      (Complex.im (transitionAmplitude ℂ f g) : ℂ) ^ 2 := by
  have h_im :
      diracImaginaryQuotient (transitionAmplitude ℂ f g) (transitionAmplitude ℂ g f) =
        (Complex.im (transitionAmplitude ℂ f g) : ℂ) :=
    MathformerPhysicsLib.Foundations.HilbertSpace.diracImaginaryQuotient_eq_im_of_conjugate
      conjugate_symmetry.conjugate_relation
  have h_square :
      (diracImaginaryQuotient (transitionAmplitude ℂ f g) (transitionAmplitude ℂ g f)) ^ 2 =
        (Complex.im (transitionAmplitude ℂ f g) : ℂ) ^ 2 :=
    congrArg (fun z : ℂ => z ^ 2) h_im
  exact h_square

/-- 0074 frontier bridge 1: a braket-pair packet derives conjugate symmetry
from Mathlib transition-amplitude symmetry. -/
def dirac_braket_pair_conjugate_symmetry
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (B : DiracBraketPair (H := H)) :
    PhysicalLawWitness (star B.forward = B.reverse) :=
  ⟨diracBraketPair_conjugate_symmetry B⟩

/-- 0074 frontier bridge 2: the braket-pair imaginary quotient is the
imaginary part of the forward amplitude. -/
def dirac_braket_pair_imaginary_quotient
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (B : DiracBraketPair (H := H)) :
    PhysicalLawWitness
      (diracBraketPairImaginaryQuotient B = (Complex.im B.forward : ℂ)) :=
  ⟨diracBraketPairImaginaryQuotient_eq_im B⟩

/-- 0074 frontier bridge 3: the braket-pair quotient square identity follows
without quotient or square placeholders. -/
def dirac_braket_pair_imaginary_square
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (B : DiracBraketPair (H := H)) :
    PhysicalLawWitness
      ((diracBraketPairImaginaryQuotient B) ^ 2 =
        (Complex.im B.forward : ℂ) ^ 2) :=
  ⟨diracBraketPairImaginaryQuotient_sq_eq_im_sq B⟩

/-- 0074 frontier bridge 4: retrieve the braket pair from the recursive
imaginary-projection handoff. -/
def dirac_braket_pair_from_recursive_frontier
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (R : DiracImaginaryProjectionRecursiveFrontier (H := H)) :
    DiracBraketPair (H := H) :=
  R.braket_pair

/-- 0074 frontier bridge 5: expose the skew-adjoint-generator and commutator
expectation obligations for the next recursive expansion. -/
def dirac_imaginary_projection_recursive_frontier_handoff
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (R : DiracImaginaryProjectionRecursiveFrontier (H := H)) :
    DiracSkewAdjointGeneratorGrounding R.braket_pair ×
      DiracCommutatorExpectationGrounding R.braket_pair :=
  (R.skew_adjoint_generator_grounding, R.commutator_expectation_grounding)

/-- 0074 frontier bridge 6: expose the typed skew-adjoint-generator grounding
for the recursive Dirac imaginary-projection packet. -/
def dirac_skew_adjoint_generator_grounding_from_recursive_frontier
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (R : DiracImaginaryProjectionRecursiveFrontier (H := H)) :
    DiracSkewAdjointGeneratorGrounding R.braket_pair :=
  R.skew_adjoint_generator_grounding

/-- 0074 frontier bridge 7: expose the typed commutator-expectation grounding
for the recursive Dirac imaginary-projection packet. -/
def dirac_commutator_expectation_grounding_from_recursive_frontier
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (R : DiracImaginaryProjectionRecursiveFrontier (H := H)) :
    DiracCommutatorExpectationGrounding R.braket_pair :=
  R.commutator_expectation_grounding

/-- 0074 frontier bridge 8: the recursive packet keeps the quotient-to-imaginary
projection equality explicit. -/
def dirac_imaginary_projection_quotient_matches_im_from_recursive_frontier
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (R : DiracImaginaryProjectionRecursiveFrontier (H := H)) :
    PhysicalLawWitness
      (diracBraketPairImaginaryQuotient R.braket_pair =
        (Complex.im R.braket_pair.forward : ℂ)) :=
  ⟨R.quotient_matches_imaginary_part⟩

/-- 0074 frontier bridge 9: the recursive packet keeps conjugate symmetry
explicit before applying the imaginary-projection theorem. -/
def dirac_imaginary_projection_conjugate_symmetry_from_recursive_frontier
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (R : DiracImaginaryProjectionRecursiveFrontier (H := H)) :
    PhysicalLawWitness (star R.braket_pair.forward = R.braket_pair.reverse) :=
  ⟨R.conjugate_symmetry⟩

end Mathformer.Physics.FormalPhysics0074
