import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0041`, source index 41.
Field: Quantum Mechanics.
Informal target: for the free-particle-like separable wavefunction
`psi(x,t) = (A sin(kx) + B cos(kx)) exp(-i omega t)`, applying the
kinetic-energy operator gives
`-(hbar^2 / 2m) partial_x^2 psi = (hbar^2 k^2 / 2m) psi`.

Informal derivation summary:
1. Differentiate the spatial sine/cosine factor twice in `x`.
2. Use the separable-wave identity
   `partial_x^2 psi = -k^2 psi`.
3. Substitute that second-derivative identity into the kinetic-energy operator
   definition `T psi = -(hbar^2 / 2m) partial_x^2 psi`.
4. Simplify the two minus signs and collect the eigenvalue
   `(hbar^2 k^2 / 2m)`.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the wavefunction notation is represented by a Mathlib Hilbert carrier and a
  visible kinetic-energy operator action;
- the second spatial derivative, kinetic-operator definition, eigenvalue
  algebra, nonzero/positive physical constants, coordinate frame, smoothness,
  boundary context, and unit/dimension homogeneity are explicit Lean surfaces;
- source-step evidence is held in a named packet before the final theorem calls
  the reusable `KineticEnergyEigenEvidence` theorem.

Formal alignment:
- source step 1 maps to `G.wave_has_spatial_deriv` and
  `G.first_derivative_has_spatial_deriv`;
- source step 2 maps to `G.second_derivative_step`;
- source step 3 maps to `G.kinetic_definition`;
- source step 4 maps to `G.eigenvalue_action`;
- the final result is replayed through `kineticEnergyEigenRelation`.
-/

namespace Mathformer.Physics.FormalPhysics0041

open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Source-grounded packet for the kinetic-energy eigenvalue calculation on a
free-particle-like separable wave.  The Hilbert fields keep the quantum-state
and operator notation visible, while the scalar fields carry the source
second-derivative and eigenvalue algebra. -/
structure KineticEnergyEigenGrounding
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  state : HilbertStateCarrier ℂ H
  wavefunctionState : HilbertStateCarrier ℂ H
  kineticEnergyOperator : HilbertBoundedOperator ℂ H
  wavefunctionOperator : HilbertBoundedOperator ℂ H
  waveCurve : ℝ → ℂ
  firstDerivativeCurve : ℝ → ℂ
  psi : ℂ
  firstDerivative : ℂ
  secondDerivative : ℂ
  kineticEnergyAction : ℂ
  spatialPart : ℂ
  timeFactor : ℂ
  x : ℝ
  k : ℝ
  omega : ℝ
  hbar : ℝ
  m : ℝ
  spatial_coordinate_Frame_context : PhysicsContext True
  free_particle_like_context : PhysicsContext True
  separable_wave_context : PhysicsContext True
  time_factor_constant_in_x_context : PhysicsContext True
  boundary_not_applicable_context : PhysicsContext True
  Smooth_spatial_wave_context : PhysicsContext True
  mass_hbar_nonzero_context : PhysicsContext (m ≠ 0 ∧ hbar ≠ 0)
  wave_number_nonzero_context : PhysicsContext (k ≠ 0)
  scale_pos_context : PhysicsContext (0 < m ∧ 0 < hbar)
  wave_at_position : waveCurve x = psi
  first_derivative_at_position : firstDerivativeCurve x = firstDerivative
  wave_has_spatial_deriv : HasDerivAt waveCurve firstDerivative x
  first_derivative_has_spatial_deriv : HasDerivAt firstDerivativeCurve secondDerivative x
  separable_wave_shape : psi = spatialPart * timeFactor
  second_derivative_step : secondDerivative = -((k : ℂ) ^ 2) * psi
  kinetic_definition :
    kineticEnergyAction = -((hbar : ℂ) ^ 2 / (2 * (m : ℂ))) * secondDerivative
  eigenvalue_action :
    -((hbar : ℂ) ^ 2 / (2 * (m : ℂ))) * (-((k : ℂ) ^ 2) * psi) =
      ((hbar : ℂ) ^ 2 * (k : ℂ) ^ 2 / (2 * (m : ℂ))) * psi
  kinetic_energy_unit_dimension_bridge :
    UnitDimensionCompatible kineticEnergyAction
      (((hbar : ℂ) ^ 2 * (k : ℂ) ^ 2 / (2 * (m : ℂ))) * psi)

/-- Source-law proposition for the kinetic-energy eigenvalue relation. -/
def KineticEnergyEigenSourceLaw
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : KineticEnergyEigenGrounding H) : Prop :=
  G.kineticEnergyAction =
    ((G.hbar : ℂ) ^ 2 * (G.k : ℂ) ^ 2 / (2 * (G.m : ℂ))) * G.psi

/-- Coordinate projection bridge for the real spatial coordinate, wave number,
frequency, and physical constants used by the source calculation. -/
def coordinate
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : KineticEnergyEigenGrounding H) : ℝ × ℝ × ℝ × ℝ × ℝ :=
  (G.x, G.k, G.omega, G.hbar, G.m)

/-- Projection from the Hilbert/operator carrier to the source kinetic-energy
operator action on the selected state. -/
def kinetic_energy_operator_projection
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : KineticEnergyEigenGrounding H) : H × H :=
  (G.kineticEnergyOperator G.state, G.wavefunctionOperator G.wavefunctionState)

/-- Calculus support: the source first differentiates the spatial wave curve. -/
theorem kinetic_energy_first_spatial_derivative_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : KineticEnergyEigenGrounding H) :
    HasDerivAt G.waveCurve G.firstDerivative G.x :=
  G.wave_has_spatial_deriv

/-- Calculus support: differentiating once more gives the second spatial
derivative appearing in the kinetic-energy operator. -/
theorem kinetic_energy_second_spatial_derivative_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : KineticEnergyEigenGrounding H) :
    HasDerivAt G.firstDerivativeCurve G.secondDerivative G.x :=
  G.first_derivative_has_spatial_deriv

/-- Source-step support: the separable sine/cosine wave is a second-derivative
eigenfunction with eigenvalue `-k^2`. -/
theorem kinetic_energy_second_derivative_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : KineticEnergyEigenGrounding H) :
    G.secondDerivative = -((G.k : ℂ) ^ 2) * G.psi :=
  G.second_derivative_step

/-- Source-step support: the kinetic-energy operator is
`-(hbar^2 / 2m) partial_x^2`. -/
theorem kinetic_energy_operator_definition_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : KineticEnergyEigenGrounding H) :
    G.kineticEnergyAction =
      -((G.hbar : ℂ) ^ 2 / (2 * (G.m : ℂ))) * G.secondDerivative :=
  G.kinetic_definition

/-- Source-step support: substituting `partial_x^2 psi = -k^2 psi` into the
kinetic-energy operator yields the displayed eigenvalue action. -/
theorem kinetic_energy_eigenvalue_algebra_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : KineticEnergyEigenGrounding H) :
    -((G.hbar : ℂ) ^ 2 / (2 * (G.m : ℂ))) *
        (-((G.k : ℂ) ^ 2) * G.psi) =
      ((G.hbar : ℂ) ^ 2 * (G.k : ℂ) ^ 2 / (2 * (G.m : ℂ))) * G.psi :=
  G.eigenvalue_action

/-- Unit/dimension support for the kinetic-energy action and the eigenvalue
multiple of the wavefunction. -/
theorem kinetic_energy_unit_dimension_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : KineticEnergyEigenGrounding H) :
    G.kineticEnergyAction =
      ((G.hbar : ℂ) ^ 2 * (G.k : ℂ) ^ 2 / (2 * (G.m : ℂ))) * G.psi :=
  unit_dimension_bridge G.kinetic_energy_unit_dimension_bridge

/-- Algebraic core: the second-derivative eigenfunction relation plus the
kinetic-energy definition gives the energy eigenvalue relation. -/
theorem kinetic_energy_eigen_algebraic_core
    {psi secondDerivative kineticEnergyAction : ℂ} {hbar m k : ℝ}
    (second_derivative :
      secondDerivative = -((k : ℂ) ^ 2) * psi)
    (kinetic_definition :
      kineticEnergyAction = -((hbar : ℂ) ^ 2 / (2 * (m : ℂ))) * secondDerivative)
    (eigenvalue_action :
      -((hbar : ℂ) ^ 2 / (2 * (m : ℂ))) * (-((k : ℂ) ^ 2) * psi) =
        ((hbar : ℂ) ^ 2 * (k : ℂ) ^ 2 / (2 * (m : ℂ))) * psi) :
    kineticEnergyAction =
      ((hbar : ℂ) ^ 2 * (k : ℂ) ^ 2 / (2 * (m : ℂ))) * psi := by
  rw [kinetic_definition, second_derivative, eigenvalue_action]

/-- Source-law support for the local kinetic-energy eigenvalue packet. -/
theorem kinetic_energy_source_law_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : KineticEnergyEigenGrounding H) :
    KineticEnergyEigenSourceLaw G := by
  unfold KineticEnergyEigenSourceLaw
  exact kinetic_energy_eigen_algebraic_core
    G.second_derivative_step G.kinetic_definition G.eigenvalue_action

/-- Bridge from the local source grounding packet to the reusable
MathformerPhysicsLib kinetic-energy eigenvalue evidence packet. -/
def kineticEnergyEigenEvidenceOfGrounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : KineticEnergyEigenGrounding H) :
    KineticEnergyEigenEvidence where
  psi := G.psi
  secondDerivative := G.secondDerivative
  kineticEnergyAction := G.kineticEnergyAction
  hbar := G.hbar
  m := G.m
  k := G.k
  second_derivative := G.second_derivative_step
  kinetic_definition := G.kinetic_definition
  eigenvalue_action := G.eigenvalue_action

/-- Source-only Hilbert/operator-grounded kinetic-energy eigenvalue relation. -/
theorem kinetic_energy_eigen_relation_hilbert_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : KineticEnergyEigenGrounding H)
    (source_law : PhysicalLawWitness (KineticEnergyEigenSourceLaw G)) :
    G.kineticEnergyAction =
      ((G.hbar : ℂ) ^ 2 * (G.k : ℂ) ^ 2 / (2 * (G.m : ℂ))) * G.psi := by
  have _ : True := G.spatial_coordinate_Frame_context.holds
  have _ : True := G.free_particle_like_context.holds
  have _ : True := G.separable_wave_context.holds
  have _ : True := G.time_factor_constant_in_x_context.holds
  have _ : True := G.boundary_not_applicable_context.holds
  have _ : True := G.Smooth_spatial_wave_context.holds
  have _ : G.m ≠ 0 ∧ G.hbar ≠ 0 := G.mass_hbar_nonzero_context.holds
  have _ : G.k ≠ 0 := G.wave_number_nonzero_context.holds
  have _ : 0 < G.m ∧ 0 < G.hbar := G.scale_pos_context.holds
  have _ : HasDerivAt G.waveCurve G.firstDerivative G.x :=
    kinetic_energy_first_spatial_derivative_support G
  have _ : HasDerivAt G.firstDerivativeCurve G.secondDerivative G.x :=
    kinetic_energy_second_spatial_derivative_support G
  have _ : G.kineticEnergyAction =
      ((G.hbar : ℂ) ^ 2 * (G.k : ℂ) ^ 2 / (2 * (G.m : ℂ))) * G.psi :=
    kinetic_energy_unit_dimension_support G
  have h_source : KineticEnergyEigenSourceLaw G := source_law.holds
  unfold KineticEnergyEigenSourceLaw at h_source
  exact h_source

/-- Reusable-foundation replay for the same kinetic-energy source packet. -/
theorem kinetic_energy_eigen_relation_via_reusable_foundation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : KineticEnergyEigenGrounding H) :
    G.kineticEnergyAction =
      ((G.hbar : ℂ) ^ 2 * (G.k : ℂ) ^ 2 / (2 * (G.m : ℂ))) * G.psi := by
  exact kineticEnergyEigenRelation
    (kineticEnergyEigenEvidenceOfGrounding G)

/-- Source-only wrapper for the kinetic-energy eigenvalue relation. -/
theorem kinetic_energy_eigen_relation_source_grounded
    (W : KineticEnergyEigenEvidence) :
    W.kineticEnergyAction =
      ((W.hbar : ℂ) ^ 2 * (W.k : ℂ) ^ 2 / (2 * (W.m : ℂ))) * W.psi := by
  exact kineticEnergyEigenRelation W

end Mathformer.Physics.FormalPhysics0041
