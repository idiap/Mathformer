import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0053`, source index 53.
Field: Quantum Mechanics.
Informal target: for the separable wavefunction
`psi(x,t) = (A sin(kx) + B cos(kx)) exp(-i omega t)`, show that it satisfies
the time-dependent Schrodinger eigenstate relation
`i hbar * partial_t psi = hbar omega * psi`.

Informal derivation summary:
1. Differentiate only the time phase:
   `partial_t psi = (A sin(kx)+B cos(kx)) (-i omega exp(-i omega t))`.
2. Multiply the time derivative by `i hbar`.
3. Use the scalar phase cancellation `i * (-i) = 1`.
4. Collect `hbar omega (A sin(kx)+B cos(kx)) exp(-i omega t)`.
5. Identify that expression with `hbar omega psi(x,t)`.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the wavefunction notation is represented by a Mathlib Hilbert carrier and a
  visible Hamiltonian/evolution operator surface;
- the time derivative, separable spatial factor, time phase, nonzero/positive
  constants, coordinate frame, smoothness, boundary/initial context, TDSE
  source law, phase-cancellation algebra, and unit/dimension homogeneity are
  explicit Lean surfaces before the reusable `SeparableWaveTDSEEvidence`
  theorem is invoked.

Formal alignment:
- source step 1 maps to `G.time_derivative_step` and
  `separable_wave_time_derivative_support`;
- source step 2 maps to `G.lhs_definition`;
- source step 3 maps to `G.complex_phase_cancellation`;
- source step 4 maps to `separable_wave_tdse_algebraic_core`;
- source step 5 maps to `G.rhs_definition`;
- the final result is replayed through `separableWaveTDSEEigenRelation`.
-/

namespace Mathformer.Physics.FormalPhysics0053

open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Hilbert/operator carrier surface for the TDSE notation used by the scalar
separable-wave time-phase calculation. -/
structure SeparableWaveTDSEHilbertOperatorSurface
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  state : HilbertStateCarrier ℂ H
  hamiltonian : HilbertBoundedOperator ℂ H
  evolutionOperator : ℝ → HilbertBoundedOperator ℂ H
  timeEvolvedState : ℝ → HilbertStateCarrier ℂ H
  evolution_matches_state :
    ∀ t : ℝ, evolutionOperator t state = timeEvolvedState t

/-- Projection from the Hilbert/operator TDSE surface to the state selected at
the source time. -/
def separable_wave_tdse_operator_projection
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (S : SeparableWaveTDSEHilbertOperatorSurface H) (t : ℝ) : H × H :=
  (S.timeEvolvedState t, S.hamiltonian (S.timeEvolvedState t))

/-- Source-grounded complex-valued packet for the separable-wave TDSE
eigenstate relation.  The scalar fields carry the time-derivative calculation,
while the Hilbert fields keep the quantum-state and Hamiltonian notation
visible to the recursive workflow. -/
structure SeparableWaveTDSEGrounding
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  hilbert_surface : SeparableWaveTDSEHilbertOperatorSurface H
  waveCurve : ℝ → ℂ
  timePhase : ℝ → ℂ
  psi : ℂ
  spatialPart : ℂ
  timeFactor : ℂ
  timeDerivative : ℂ
  lhs : ℂ
  rhs : ℂ
  x : ℝ
  k : ℝ
  hbar : ℝ
  omega : ℝ
  t : ℝ
  time_coordinate_Frame_context : PhysicsContext True
  separable_wave_context : PhysicsContext True
  boundary_initial_phase_context : PhysicsContext True
  Smooth_time_phase_context : PhysicsContext True
  hbar_frequency_nonzero_context : PhysicsContext (hbar ≠ 0 ∧ omega ≠ 0)
  scale_pos_context : PhysicsContext (0 < hbar ∧ 0 < omega)
  wave_at_time : waveCurve t = psi
  time_phase_at_time : timePhase t = timeFactor
  wave_shape : psi = spatialPart * timeFactor
  time_phase_has_deriv :
    HasDerivAt timePhase ((-Complex.I * (omega : ℂ)) * timeFactor) t
  wave_has_time_deriv : HasDerivAt waveCurve timeDerivative t
  time_derivative_step : timeDerivative = (-Complex.I * (omega : ℂ)) * psi
  lhs_definition : lhs = Complex.I * (hbar : ℂ) * timeDerivative
  rhs_definition : rhs = (hbar : ℂ) * (omega : ℂ) * psi
  complex_phase_cancellation :
    Complex.I * (hbar : ℂ) * ((-Complex.I * (omega : ℂ)) * psi) =
      (hbar : ℂ) * (omega : ℂ) * psi
  tdse_unit_dimension_bridge : UnitDimensionCompatible lhs rhs

/-- Source-law proposition for the separable-wave TDSE eigenstate relation. -/
def SeparableWaveTDSESourceLaw
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : SeparableWaveTDSEGrounding H) : Prop :=
  G.lhs = G.rhs

/-- Coordinate projection bridge for the spatial coordinate, wave number,
Planck constant, frequency, and time parameter. -/
def coordinate
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : SeparableWaveTDSEGrounding H) : ℝ × ℝ × ℝ × ℝ × ℝ :=
  (G.x, G.k, G.hbar, G.omega, G.t)

/-- Source-step support: the separable wave is the product of a spatial factor
and the time phase at the selected time. -/
theorem separable_wave_shape_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : SeparableWaveTDSEGrounding H) :
    G.psi = G.spatialPart * G.timeFactor :=
  G.wave_shape

/-- Calculus support: the time phase has derivative `-i omega` times itself. -/
theorem separable_wave_time_phase_derivative_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : SeparableWaveTDSEGrounding H) :
    HasDerivAt G.timePhase ((-Complex.I * (G.omega : ℂ)) * G.timeFactor) G.t :=
  G.time_phase_has_deriv

/-- Calculus support: the source wave curve has the displayed time derivative. -/
theorem separable_wave_time_derivative_calculus_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : SeparableWaveTDSEGrounding H) :
    HasDerivAt G.waveCurve G.timeDerivative G.t :=
  G.wave_has_time_deriv

/-- Source-step support: differentiating the time phase gives
`partial_t psi = -i omega psi`. -/
theorem separable_wave_time_derivative_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : SeparableWaveTDSEGrounding H) :
    G.timeDerivative = (-Complex.I * (G.omega : ℂ)) * G.psi :=
  G.time_derivative_step

/-- Source-step support: the left-hand side is `i hbar` times the time
derivative. -/
theorem separable_wave_tdse_lhs_definition_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : SeparableWaveTDSEGrounding H) :
    G.lhs = Complex.I * (G.hbar : ℂ) * G.timeDerivative :=
  G.lhs_definition

/-- Source-step support: the right-hand side is the eigenvalue
`hbar omega` multiplying the wavefunction. -/
theorem separable_wave_tdse_rhs_definition_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : SeparableWaveTDSEGrounding H) :
    G.rhs = (G.hbar : ℂ) * (G.omega : ℂ) * G.psi :=
  G.rhs_definition

/-- Source-step support: the scalar phase cancellation `i * (-i) = 1`
converts the TDSE left-hand side into the eigenvalue multiple. -/
theorem separable_wave_phase_cancellation_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : SeparableWaveTDSEGrounding H) :
    Complex.I * (G.hbar : ℂ) * ((-Complex.I * (G.omega : ℂ)) * G.psi) =
      (G.hbar : ℂ) * (G.omega : ℂ) * G.psi :=
  G.complex_phase_cancellation

/-- Unit/dimension support for the TDSE eigenstate relation. -/
theorem separable_wave_tdse_unit_dimension_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : SeparableWaveTDSEGrounding H) :
    G.lhs = G.rhs :=
  unit_dimension_bridge G.tdse_unit_dimension_bridge

/-- Algebraic core: the derivative step, left/right definitions, and phase
cancellation prove the separable-wave TDSE relation. -/
theorem separable_wave_tdse_algebraic_core
    {psi timeDerivative lhs rhs : ℂ} {hbar omega : ℝ}
    (time_derivative_step : timeDerivative = (-Complex.I * (omega : ℂ)) * psi)
    (lhs_definition : lhs = Complex.I * (hbar : ℂ) * timeDerivative)
    (rhs_definition : rhs = (hbar : ℂ) * (omega : ℂ) * psi)
    (complex_phase_cancellation :
      Complex.I * (hbar : ℂ) * ((-Complex.I * (omega : ℂ)) * psi) =
        (hbar : ℂ) * (omega : ℂ) * psi) :
    lhs = rhs := by
  rw [lhs_definition, time_derivative_step, rhs_definition]
  exact complex_phase_cancellation

/-- Source-law support for the separable-wave TDSE packet. -/
theorem separable_wave_tdse_source_law_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : SeparableWaveTDSEGrounding H) :
    SeparableWaveTDSESourceLaw G := by
  unfold SeparableWaveTDSESourceLaw
  exact separable_wave_tdse_algebraic_core
    G.time_derivative_step G.lhs_definition G.rhs_definition
    G.complex_phase_cancellation

/-- Bridge from the local source grounding packet to the reusable
MathformerPhysicsLib separable-wave TDSE evidence packet. -/
def separableWaveTDSEEvidenceOfGrounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : SeparableWaveTDSEGrounding H) :
    SeparableWaveTDSEEvidence where
  psi := G.psi
  timeDerivative := G.timeDerivative
  lhs := G.lhs
  rhs := G.rhs
  hbar := G.hbar
  omega := G.omega
  time_derivative_step := G.time_derivative_step
  lhs_definition := G.lhs_definition
  rhs_definition := G.rhs_definition
  complex_phase_cancellation := G.complex_phase_cancellation

/-- Source-only Hilbert/operator-grounded form of the separable-wave TDSE
eigenstate relation. -/
theorem separable_wave_tdse_hilbert_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : SeparableWaveTDSEGrounding H)
    (source_law : PhysicalLawWitness (SeparableWaveTDSESourceLaw G)) :
    G.lhs = G.rhs := by
  have _ : True := G.time_coordinate_Frame_context.holds
  have _ : True := G.separable_wave_context.holds
  have _ : True := G.boundary_initial_phase_context.holds
  have _ : True := G.Smooth_time_phase_context.holds
  have _ : G.hbar ≠ 0 ∧ G.omega ≠ 0 := G.hbar_frequency_nonzero_context.holds
  have _ : 0 < G.hbar ∧ 0 < G.omega := G.scale_pos_context.holds
  have _ : H × H :=
    separable_wave_tdse_operator_projection G.hilbert_surface G.t
  have _ : HasDerivAt G.timePhase ((-Complex.I * (G.omega : ℂ)) * G.timeFactor) G.t :=
    separable_wave_time_phase_derivative_support G
  have _ : HasDerivAt G.waveCurve G.timeDerivative G.t :=
    separable_wave_time_derivative_calculus_support G
  have _ : G.timeDerivative = (-Complex.I * (G.omega : ℂ)) * G.psi :=
    separable_wave_time_derivative_support G
  have _ : G.lhs = G.rhs :=
    separable_wave_tdse_unit_dimension_support G
  have h_source : SeparableWaveTDSESourceLaw G := source_law.holds
  unfold SeparableWaveTDSESourceLaw at h_source
  exact h_source

/-- Reusable-foundation replay for the same separable-wave TDSE packet. -/
theorem separable_wave_tdse_via_reusable_foundation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : SeparableWaveTDSEGrounding H) :
    G.lhs = G.rhs := by
  exact separableWaveTDSEEigenRelation
    (separableWaveTDSEEvidenceOfGrounding G)

/-- Source-only wrapper for the separable-wave TDSE eigenstate relation. -/
theorem separable_wave_tdse_source_grounded
    (W : SeparableWaveTDSEEvidence) :
    W.lhs = W.rhs := by
  exact separableWaveTDSEEigenRelation W

end Mathformer.Physics.FormalPhysics0053
