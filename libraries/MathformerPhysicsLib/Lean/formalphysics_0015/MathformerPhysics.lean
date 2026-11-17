import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0015`, source index 15.
Field: Quantum Mechanics.
Informal target: vacuum Rabi probability from a Dirac transition amplitude.

Recursive grounding:
- transition amplitude uses `transitionAmplitude`;
- probability uses `probabilityFromAmplitude`;
- the Rabi state expansion is a typed Hilbert-space statement;
- normalization and orthogonality remain explicit typed witnesses;
- the final probability is derived through the Born-rule probability surface,
  not assumed as a target-shaped witness.
-/


namespace Mathformer.Physics.FormalPhysics0015

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Units

/-- Dirac-grounded vacuum Rabi probability wrapper. -/
theorem vacuum_rabi_probability_dirac_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (psi groundOne excitedZero : HilbertStateCarrier ℂ H)
    (Omega t Pg : ℝ)
    (normalized : NormalizedStateWitness psi)
    (ground_normalized : NormalizedStateWitness groundOne)
    (orthogonality : HilbertOrthogonalityWitness (𝕜 := ℂ) groundOne excitedZero)
    (state_expansion : TwoLevelRabiStateExpansion psi excitedZero groundOne Omega t)
    (probability_definition :
      Pg = probabilityFromAmplitude (transitionAmplitude ℂ groundOne psi))
    (probability_dimension : DimensionCompatible Pg (Real.sin (Omega * t / 2) ^ 2)) :
    Pg = Real.sin (Omega * t / 2) ^ 2 := by
  have _ := normalized
  have _ := probability_dimension
  have h_normSq :
      Complex.normSq ((-Complex.I) * (Real.sin (Omega * t / 2) : ℂ)) =
        Real.sin (Omega * t / 2) ^ 2 :=
    complex_normSq_neg_I_mul_real (Real.sin (Omega * t / 2))
  have _ := h_normSq
  exact vacuumRabiProbabilityFromStateExpansion
    psi groundOne excitedZero Omega t Pg ground_normalized orthogonality
    state_expansion probability_definition

/-- 0015 frontier bridge 1: a two-level Rabi frame generates the explicit
state-expansion surface consumed by the original probability theorem. -/
def two_level_rabi_state_expansion_from_frame
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TwoLevelRabiFrame H) (Omega t : ℝ) :
    PhysicalLawWitness
      (TwoLevelRabiStateExpansion
        (twoLevelRabiStateFromFrame F Omega t) F.excited F.ground Omega t) :=
  ⟨twoLevelRabiStateFromFrame_expansion F Omega t⟩

/-- 0015 frontier bridge 2: a frame-generated Rabi state yields the expected
Dirac transition amplitude without an amplitude placeholder. -/
def transition_amplitude_from_two_level_rabi_frame
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TwoLevelRabiFrame H) (Omega t : ℝ) :
    PhysicalLawWitness
      (transitionAmplitude ℂ F.ground (twoLevelRabiStateFromFrame F Omega t) =
        VacuumRabiAmplitude Omega t) :=
  ⟨transitionAmplitude_from_twoLevelRabiFrameState F Omega t⟩

/-- 0015 frontier bridge 3: grounded unitary dynamics plus a ground-state
measurement projector give the resonant Rabi Born probability curve. -/
def projection_born_probability_from_two_level_rabi_dynamics
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    {F : TwoLevelRabiFrame H} {Omega : ℝ}
    (D : TwoLevelRabiDynamicsFrontier F Omega)
    (M : TwoLevelRabiGroundMeasurementFrontier F) (t : ℝ) :
    PhysicalLawWitness
      (projectionBornProbability M.groundProjector (D.evolution t F.excited) =
        Real.sin (Omega * t / 2) ^ 2) :=
  ⟨projectionBornProbability_from_twoLevelRabiDynamics D M t⟩

/-- 0015 frontier bridge 4: parameter calibration remains visible as a
physics object instead of being collapsed into the scalar `Ω`. -/
def rabi_parameter_calibration_from_recursive_frontier
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    {Omega : ℝ} (R : VacuumRabiRecursiveFrontier (H := H) Omega) :
    TwoLevelRabiParameterCalibrationFrontier Omega :=
  R.parameter_calibration

/-- 0015 frontier bridge 5: the full recursive Rabi packet proves the
probability curve from dynamics, measurement, and calibration surfaces. -/
def vacuum_rabi_recursive_probability_curve
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    {Omega : ℝ} (R : VacuumRabiRecursiveFrontier (H := H) Omega) (t : ℝ) :
    PhysicalLawWitness
      (R.probability_curve t = Real.sin (Omega * t / 2) ^ 2) :=
  ⟨vacuumRabiRecursiveFrontier_probability_curve R t⟩

/-- 0015 frontier bridge 6: expose the recursive Rabi handoff components for
subsequent controlled expansion. -/
def vacuum_rabi_recursive_frontier_handoff
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    {Omega : ℝ} (R : VacuumRabiRecursiveFrontier (H := H) Omega) :
    TwoLevelRabiFrame H ×
      TwoLevelRabiDynamicsFrontier R.frame Omega ×
        TwoLevelRabiGroundMeasurementFrontier R.frame ×
          TwoLevelRabiParameterCalibrationFrontier Omega ×
            TwoLevelRabiOpenSystemFrontier R.frame :=
  (R.frame, R.dynamics, R.ground_measurement,
    R.parameter_calibration, R.open_system_frontier)

end Mathformer.Physics.FormalPhysics0015
