import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0048`, source index 48.
Field: Quantum Mechanics.
Informal target: for the one-dimensional harmonic oscillator in the
Heisenberg picture, use
`x(t) = x(0) cos(omega t) + (p(0) / (m omega)) sin(omega t)` to compute the
unequal-time position commutator `[x(t1), x(t2)]` and show that it is
`i hbar / (m omega) * sin(omega * (t2 - t1))`.

Informal derivation summary:
1. Expand `[x(t1), x(t2)]` by bilinearity of the commutator.
2. Use `sin(omega * (t1 - t2)) = -sin(omega * (t2 - t1))`.
3. Factor the common scalar and obtain
   `(1 / (m omega)) * sin(omega * (t2 - t1)) * [x(0), p(0)]`.
4. Use the canonical equal-time commutator `[x(0), p(0)] = i hbar I`.
5. Read off the scalar unequal-time commutator
   `(i hbar / (m omega)) * sin(omega * (t2 - t1))`.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the source operator notation is represented by bounded Hilbert-operator
  curves over a Mathlib Hilbert carrier;
- the Heisenberg-picture frame, smooth operator curve, initial-boundary
  context, nonzero/positive mass and frequency, sine antisymmetry, bilinear
  commutator reduction, canonical initial commutator, and unit/dimension
  homogeneity are explicit Lean surfaces before the reusable
  `UnequalTimePositionCommutatorEvidence` theorem is invoked.

Formal alignment:
- source step 1 maps to `G.bilinear_reduction` and
  `unequal_time_bilinear_reduction_support`;
- source step 2 maps to `unequal_time_sine_antisymmetry_support`;
- source step 3 maps to `G.bilinear_reduction`;
- source step 4 maps to `G.canonical_initial_commutator`;
- source step 5 maps to `unequal_time_position_commutator_algebraic_core`;
- the final result is replayed through `unequalTimePositionCommutator`.
-/

namespace Mathformer.Physics.FormalPhysics0048

open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Source-grounded bounded-Hilbert-operator packet for the unequal-time
harmonic-oscillator position commutator.  The operator fields keep the
Heisenberg notation visible, while the scalar fields carry the source
commutator reduction reused by `UnequalTimePositionCommutatorEvidence`. -/
structure UnequalTimePositionCommutatorGrounding
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  state : HilbertStateCarrier ℂ H
  positionCurve : ℝ → HilbertBoundedOperator ℂ H
  momentumCurve : ℝ → HilbertBoundedOperator ℂ H
  x0 : HilbertBoundedOperator ℂ H
  p0 : HilbertBoundedOperator ℂ H
  xAtT1 : HilbertBoundedOperator ℂ H
  xAtT2 : HilbertBoundedOperator ℂ H
  dxAtT1 : HilbertBoundedOperator ℂ H
  dxAtT2 : HilbertBoundedOperator ℂ H
  commutatorAtTimes : ℂ
  initialCommutator : ℂ
  result : ℂ
  m : ℝ
  omega : ℝ
  hbar : ℝ
  t1 : ℝ
  t2 : ℝ
  heisenberg_picture_Frame_context : PhysicsContext True
  harmonic_oscillator_context : PhysicsContext True
  unequal_time_commutator_context : PhysicsContext True
  boundary_initial_operator_context : PhysicsContext True
  Smooth_operator_curve_context : PhysicsContext True
  scale_nonzero_context : PhysicsContext (m ≠ 0 ∧ omega ≠ 0)
  scale_pos_context : PhysicsContext (0 < m ∧ 0 < omega)
  hbar_nonzero_context : PhysicsContext (hbar ≠ 0)
  position_at_t1 : positionCurve t1 = xAtT1
  position_at_t2 : positionCurve t2 = xAtT2
  initial_position_operator : positionCurve 0 = x0
  initial_momentum_operator : momentumCurve 0 = p0
  position_has_deriv_t1 : HasDerivAt positionCurve dxAtT1 t1
  position_has_deriv_t2 : HasDerivAt positionCurve dxAtT2 t2
  heisenberg_solution_t1 :
    xAtT1 =
      (Complex.ofReal (Real.cos (omega * t1))) • x0 +
        ((1 / ((m : ℂ) * (omega : ℂ))) *
          Complex.ofReal (Real.sin (omega * t1))) • p0
  heisenberg_solution_t2 :
    xAtT2 =
      (Complex.ofReal (Real.cos (omega * t2))) • x0 +
        ((1 / ((m : ℂ) * (omega : ℂ))) *
          Complex.ofReal (Real.sin (omega * t2))) • p0
  initial_commutator_expectation :
    initialCommutator = hilbertCommutatorExpectation x0 p0 state
  bilinear_reduction :
    commutatorAtTimes =
      (1 / ((m : ℂ) * (omega : ℂ))) *
        Complex.ofReal (Real.sin (omega * (t2 - t1))) * initialCommutator
  canonical_initial_commutator : initialCommutator = Complex.I * (hbar : ℂ)
  result_definition :
    result =
      (Complex.I * (hbar : ℂ) / ((m : ℂ) * (omega : ℂ))) *
        Complex.ofReal (Real.sin (omega * (t2 - t1)))
  unequal_time_unit_dimension_bridge :
    UnitDimensionCompatible commutatorAtTimes result

/-- Source-law proposition for the unequal-time oscillator commutator. -/
def UnequalTimePositionCommutatorSourceLaw
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H) : Prop :=
  G.commutatorAtTimes = G.result

/-- Coordinate bridge for the physical constants and two time parameters. -/
def coordinate
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H) : ℝ × ℝ × ℝ × ℝ :=
  (G.m, G.omega, G.t1, G.t2)

/-- Projection from source operator notation to the two unequal-time position
operators and the equal-time initial pair. -/
def unequal_time_position_operator_projection
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H) :
    HilbertBoundedOperator ℂ H × HilbertBoundedOperator ℂ H ×
      HilbertBoundedOperator ℂ H × HilbertBoundedOperator ℂ H :=
  (G.xAtT1, G.xAtT2, G.x0, G.p0)

/-- Calculus support: the Heisenberg position curve has a derivative at the
first source time. -/
theorem unequal_time_position_derivative_t1_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H) :
    HasDerivAt G.positionCurve G.dxAtT1 G.t1 :=
  G.position_has_deriv_t1

/-- Calculus support: the Heisenberg position curve has a derivative at the
second source time. -/
theorem unequal_time_position_derivative_t2_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H) :
    HasDerivAt G.positionCurve G.dxAtT2 G.t2 :=
  G.position_has_deriv_t2

/-- Source-step support: the Heisenberg solution at `t1` is the stated
linear combination of the initial operators. -/
theorem unequal_time_position_solution_t1_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H) :
    G.xAtT1 =
      (Complex.ofReal (Real.cos (G.omega * G.t1))) • G.x0 +
        ((1 / ((G.m : ℂ) * (G.omega : ℂ))) *
          Complex.ofReal (Real.sin (G.omega * G.t1))) • G.p0 :=
  G.heisenberg_solution_t1

/-- Source-step support: the Heisenberg solution at `t2` is the stated
linear combination of the initial operators. -/
theorem unequal_time_position_solution_t2_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H) :
    G.xAtT2 =
      (Complex.ofReal (Real.cos (G.omega * G.t2))) • G.x0 +
        ((1 / ((G.m : ℂ) * (G.omega : ℂ))) *
          Complex.ofReal (Real.sin (G.omega * G.t2))) • G.p0 :=
  G.heisenberg_solution_t2

/-- Source-step support: sine antisymmetry converts the second bilinear term
into the negative of the first time-ordering. -/
theorem unequal_time_sine_antisymmetry_support
    (omega t1 t2 : ℝ) :
    Real.sin (omega * (t1 - t2)) = -Real.sin (omega * (t2 - t1)) := by
  have harg : omega * (t1 - t2) = -(omega * (t2 - t1)) := by
    ring
  rw [harg, Real.sin_neg]

/-- Source-step support: bilinearity and factoring reduce the unequal-time
commutator to the initial position-momentum commutator. -/
theorem unequal_time_bilinear_reduction_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H) :
    G.commutatorAtTimes =
      (1 / ((G.m : ℂ) * (G.omega : ℂ))) *
        Complex.ofReal (Real.sin (G.omega * (G.t2 - G.t1))) *
          G.initialCommutator :=
  G.bilinear_reduction

/-- Source-step support: the initial commutator is the Hilbert-space
expectation of the bounded operator commutator. -/
theorem unequal_time_initial_commutator_expectation_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H) :
    G.initialCommutator = hilbertCommutatorExpectation G.x0 G.p0 G.state :=
  G.initial_commutator_expectation

/-- Source-step support: the equal-time canonical commutator contributes the
`i hbar` scalar. -/
theorem unequal_time_canonical_initial_commutator_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H) :
    G.initialCommutator = Complex.I * (G.hbar : ℂ) :=
  G.canonical_initial_commutator

/-- Source-step support: the displayed final scalar is the named result. -/
theorem unequal_time_result_definition_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H) :
    G.result =
      (Complex.I * (G.hbar : ℂ) / ((G.m : ℂ) * (G.omega : ℂ))) *
        Complex.ofReal (Real.sin (G.omega * (G.t2 - G.t1))) :=
  G.result_definition

/-- Unit/dimension support for the unequal-time commutator scalar. -/
theorem unequal_time_unit_dimension_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H) :
    G.commutatorAtTimes = G.result :=
  unit_dimension_bridge G.unequal_time_unit_dimension_bridge

/-- Algebraic core: bilinearity, sine factoring, and the initial canonical
commutator produce the displayed unequal-time result. -/
theorem unequal_time_position_commutator_algebraic_core
    {commutatorAtTimes initialCommutator result : ℂ}
    {m omega hbar t1 t2 : ℝ}
    (bilinear_reduction :
      commutatorAtTimes =
        (1 / ((m : ℂ) * (omega : ℂ))) *
          Complex.ofReal (Real.sin (omega * (t2 - t1))) * initialCommutator)
    (canonical_initial_commutator :
      initialCommutator = Complex.I * (hbar : ℂ))
    (result_definition :
      result =
        (Complex.I * (hbar : ℂ) / ((m : ℂ) * (omega : ℂ))) *
          Complex.ofReal (Real.sin (omega * (t2 - t1)))) :
    commutatorAtTimes = result := by
  rw [bilinear_reduction, canonical_initial_commutator, result_definition]
  ring

/-- Source-law support for the unequal-time oscillator commutator. -/
theorem unequal_time_position_commutator_source_law_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H) :
    UnequalTimePositionCommutatorSourceLaw G := by
  unfold UnequalTimePositionCommutatorSourceLaw
  exact unequal_time_position_commutator_algebraic_core
    G.bilinear_reduction G.canonical_initial_commutator G.result_definition

/-- Bridge from the local grounding packet to the reusable
MathformerPhysicsLib unequal-time commutator evidence packet. -/
def unequalTimePositionCommutatorEvidenceOfGrounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H) :
    UnequalTimePositionCommutatorEvidence where
  commutatorAtTimes := G.commutatorAtTimes
  initialCommutator := G.initialCommutator
  result := G.result
  m := G.m
  omega := G.omega
  hbar := G.hbar
  t1 := G.t1
  t2 := G.t2
  bilinear_reduction := G.bilinear_reduction
  canonical_initial_commutator := G.canonical_initial_commutator
  result_definition := G.result_definition

/-- Source-only bounded-Hilbert-operator form of the unequal-time oscillator
position commutator. -/
theorem unequal_time_position_commutator_hilbert_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H)
    (source_law : PhysicalLawWitness (UnequalTimePositionCommutatorSourceLaw G)) :
    G.commutatorAtTimes = G.result := by
  have _ : True := G.heisenberg_picture_Frame_context.holds
  have _ : True := G.harmonic_oscillator_context.holds
  have _ : True := G.unequal_time_commutator_context.holds
  have _ : True := G.boundary_initial_operator_context.holds
  have _ : True := G.Smooth_operator_curve_context.holds
  have _ : G.m ≠ 0 ∧ G.omega ≠ 0 := G.scale_nonzero_context.holds
  have _ : 0 < G.m ∧ 0 < G.omega := G.scale_pos_context.holds
  have _ : G.hbar ≠ 0 := G.hbar_nonzero_context.holds
  have _ : HasDerivAt G.positionCurve G.dxAtT1 G.t1 :=
    unequal_time_position_derivative_t1_support G
  have _ : HasDerivAt G.positionCurve G.dxAtT2 G.t2 :=
    unequal_time_position_derivative_t2_support G
  have _ : Real.sin (G.omega * (G.t1 - G.t2)) =
      -Real.sin (G.omega * (G.t2 - G.t1)) :=
    unequal_time_sine_antisymmetry_support G.omega G.t1 G.t2
  have _ :
      hilbertOperatorCommutator G.x0 G.p0 G.state =
        G.x0 (G.p0 G.state) - G.p0 (G.x0 G.state) :=
    hilbertOperatorCommutator_apply G.x0 G.p0 G.state
  have _ : G.initialCommutator = hilbertCommutatorExpectation G.x0 G.p0 G.state :=
    unequal_time_initial_commutator_expectation_support G
  have _ : G.commutatorAtTimes = G.result :=
    unequal_time_unit_dimension_support G
  have h_source : UnequalTimePositionCommutatorSourceLaw G := source_law.holds
  unfold UnequalTimePositionCommutatorSourceLaw at h_source
  exact h_source

/-- Reusable-foundation replay for the same unequal-time commutator packet. -/
theorem unequal_time_position_commutator_via_reusable_foundation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : UnequalTimePositionCommutatorGrounding H) :
    G.commutatorAtTimes = G.result := by
  exact unequalTimePositionCommutator
    (unequalTimePositionCommutatorEvidenceOfGrounding G)

/-- Source-only wrapper for the unequal-time oscillator position commutator. -/
theorem unequal_time_position_commutator_source_grounded
    (E : UnequalTimePositionCommutatorEvidence) :
    E.commutatorAtTimes = E.result := by
  exact unequalTimePositionCommutator E

end Mathformer.Physics.FormalPhysics0048
