import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0052`, source index 52.
Field: Quantum Mechanics.
Informal target: position expectation value from Dirac position wavefunction.

Recursive grounding:
- wavefunctions use `PositionWavefunction`;
- Born-rule integrands use `positionExpectationIntegrand`;
- position expectation uses `positionExpectationIntegral` over a Mathlib
  measure;
- the position-basis resolution identity is represented by an explicit typed
  measure-kernel witness rather than a generated nonempty placeholder.
-/


namespace Mathformer.Physics.FormalPhysics0052

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MeasureTheory

/-- Dirac-grounded position expectation wrapper. -/
theorem position_expectation_dirac_grounded
    {X : Type*} [MeasurableSpace X]
    (μ : Measure X)
    (xValue : X → ℝ)
    (psi : PositionWavefunction X)
    (expectation bornIntegral : ℝ)
    (resolution_of_identity :
      MathformerPhysicsLib.Foundations.HilbertSpace.PositionResolutionIdentityMeasureKernel X μ)
    (expectation_definition :
      expectation =
        MathformerPhysicsLib.Foundations.HilbertSpace.positionExpectationIntegral μ xValue psi)
    (born_integral_definition :
      bornIntegral = ∫ x, positionExpectationIntegrand xValue psi x ∂μ) :
    expectation = bornIntegral := by
  have _ := resolution_of_identity
  have h_integrand :
      ∀ x : X, positionExpectationIntegrand xValue psi x = xValue x * ‖psi x‖ ^ 2 :=
    fun x =>
      MathformerPhysicsLib.Foundations.HilbertSpace.positionExpectationIntegrand_apply
        xValue psi x
  have _ := h_integrand
  have h_born :
      bornIntegral =
        MathformerPhysicsLib.Foundations.HilbertSpace.positionExpectationIntegral μ xValue psi := by
    rw [born_integral_definition]
    exact
      (MathformerPhysicsLib.Foundations.HilbertSpace.positionExpectationIntegral_apply
        μ xValue psi).symm
  rw [expectation_definition, h_born]

/-- 0052 frontier bridge 1: the Born density is the squared norm of the
position wavefunction amplitude. -/
def position_born_density_from_wavefunction
    {X : Type*} (psi : PositionWavefunction X) :
    PhysicalLawWitness (∀ x : X, positionBornDensity psi x = ‖psi x‖ ^ 2) :=
  ⟨fun _ => rfl⟩

/-- 0052 frontier bridge 2: the position integrand factors through the named
Born-density surface. -/
def position_integrand_from_born_density
    {X : Type*} (xValue : X → ℝ) (psi : PositionWavefunction X) :
    PhysicalLawWitness
      (∀ x : X,
        positionExpectationIntegrand xValue psi x =
          xValue x * positionBornDensity psi x) :=
  ⟨positionExpectationIntegrand_eq_value_mul_density xValue psi⟩

/-- 0052 frontier bridge 3: a measurement-space packet unfolds to the Mathlib
integral of the Born-rule position integrand. -/
def position_expectation_from_measurement_space_frontier
    {X : Type*} [MeasurableSpace X] (S : PositionMeasurementSpaceFrontier X) :
    PhysicalLawWitness
      (positionExpectationFromMeasurementSpace S =
        ∫ x, positionExpectationIntegrand S.xValue S.psi x ∂S.μ) :=
  ⟨positionExpectationFromMeasurementSpace_apply S⟩

/-- 0052 frontier bridge 4: retrieve the measurement-space packet from the
recursive position-expectation handoff. -/
def position_measurement_space_from_recursive_frontier
    {X : Type*} [MeasurableSpace X] (R : PositionExpectationRecursiveFrontier X) :
    PositionMeasurementSpaceFrontier X :=
  R.measurement_space

/-- 0052 frontier bridge 5: expose spectral, `L²`, and integrability
obligations for the next recursive position-expectation expansion. -/
def position_expectation_recursive_frontier_handoff
    {X : Type*} [MeasurableSpace X] (R : PositionExpectationRecursiveFrontier X) :
    PhysicalLawWitness (PositionSpectralMeasureGrounding R.measurement_space) ×
      PhysicalLawWitness (PositionL2WavefunctionGrounding R.measurement_space) ×
      PhysicalLawWitness (PositionExpectationIntegrabilityGrounding R.measurement_space) :=
  (⟨R.spectral_measure_grounding⟩, ⟨R.l2_wavefunction_grounding⟩,
    ⟨R.integrability_grounding⟩)

/-- 0052 frontier bridge 6: expose the structured spectral-measure grounding
for the measured position packet. -/
def position_spectral_measure_grounding_from_recursive_frontier
    {X : Type*} [MeasurableSpace X] (R : PositionExpectationRecursiveFrontier X) :
    PhysicalLawWitness (PositionSpectralMeasureGrounding R.measurement_space) :=
  ⟨R.spectral_measure_grounding⟩

/-- 0052 frontier bridge 7: expose the structured `L²`-style wavefunction
grounding for the measured position packet. -/
def position_l2_wavefunction_grounding_from_recursive_frontier
    {X : Type*} [MeasurableSpace X] (R : PositionExpectationRecursiveFrontier X) :
    PhysicalLawWitness (PositionL2WavefunctionGrounding R.measurement_space) :=
  ⟨R.l2_wavefunction_grounding⟩

/-- 0052 frontier bridge 8: expose the structured expectation-integrability
grounding for the measured position packet. -/
def position_integrability_grounding_from_recursive_frontier
    {X : Type*} [MeasurableSpace X] (R : PositionExpectationRecursiveFrontier X) :
    PhysicalLawWitness (PositionExpectationIntegrabilityGrounding R.measurement_space) :=
  ⟨R.integrability_grounding⟩

/-- 0052 frontier bridge 9: the measurement-space packet carries Born-density
integrability as a typed Mathlib integral statement. -/
def position_born_density_integrability_from_measurement_space
    {X : Type*} [MeasurableSpace X] (S : PositionMeasurementSpaceFrontier X) :
    PhysicalLawWitness (PositionBornDensityIntegrable S.μ S.psi) :=
  ⟨S.born_density_integrable⟩

/-- 0052 frontier bridge 10: the measurement-space packet carries normalized
Born probability as a typed Mathlib integral statement. -/
def position_born_probability_normalization_from_measurement_space
    {X : Type*} [MeasurableSpace X] (S : PositionMeasurementSpaceFrontier X) :
    PhysicalLawWitness (PositionBornProbabilityNormalization S.μ S.psi) :=
  ⟨S.normalized_probability⟩

/-- 0052 frontier bridge 11: the measurement-space packet carries integrability
of the position-expectation integrand. -/
def position_expectation_integrability_from_measurement_space
    {X : Type*} [MeasurableSpace X] (S : PositionMeasurementSpaceFrontier X) :
    PhysicalLawWitness (PositionExpectationIntegrable S.μ S.xValue S.psi) :=
  ⟨S.integrable_position_observable⟩

end Mathformer.Physics.FormalPhysics0052
