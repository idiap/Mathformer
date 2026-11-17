-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib
import MathformerPhysicsLib.Lean.Foundations.HilbertSpace
import MathformerPhysicsLib.Lean.Foundations.Operators
import MathformerPhysicsLib.Lean.Foundations.PositionMomentumModels
import MathformerPhysicsLib.Lean.Foundations.Units

namespace MathformerPhysicsLib
namespace Foundations
namespace QuantumMechanicsExamples

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Operators
open MathformerPhysicsLib.Foundations.Units

/-!
Reusable MathformerPhysicsLib surfaces for new FormalPhysics quantum-mechanics
examples.  These declarations are deliberately source-step oriented: hard
physics/analysis assumptions remain visible as intermediate evidence fields,
while final wrappers prove their targets from those fields instead of restating
the target equation as one opaque hypothesis.
-/

/-- Physics role: dimensionless harmonic-oscillator ladder product evidence.
The scalar fields are the source-side symbols; `product_expansion` is the
noncommutative expansion step that a later operator-algebra layer can refine. -/
structure DimensionlessLadderNumberEvidence where
  q : ℂ
  p : ℂ
  number : ℂ
  expanded : ℂ
  product_expansion : number = expanded
  expanded_shape : expanded = p ^ 2 - Complex.I * (p * q) + Complex.I * (q * p) + q ^ 2

/-- Source-grounded ladder-number expansion from the two product steps. -/
theorem dimensionlessLadderNumberExpansion
    (E : DimensionlessLadderNumberEvidence) :
    E.number = E.p ^ 2 - Complex.I * (E.p * E.q) + Complex.I * (E.q * E.p) + E.q ^ 2 := by
  rw [E.product_expansion, E.expanded_shape]

/-- Physics role: ladder product evidence with physical constants kept as
explicit coefficients instead of erased into scalar placeholders. -/
structure PhysicalLadderProductEvidence where
  x : ℂ
  p : ℂ
  alpha : ℂ
  prefactor : ℂ
  product : ℂ
  expanded : ℂ
  alpha_eq : alpha = Complex.I / prefactor
  product_factorization : product = prefactor * ((x + alpha * p) * (x - alpha * p))
  product_expansion :
    prefactor * ((x + alpha * p) * (x - alpha * p)) =
      prefactor * (x * x - x * alpha * p + alpha * p * x - alpha * p * alpha * p)
  expanded_eq :
    expanded = prefactor * (x * x - x * alpha * p + alpha * p * x - alpha * p * alpha * p)

/-- Source-grounded product expansion for a harmonic-oscillator ladder pair. -/
theorem physicalLadderProductExpansion
    (E : PhysicalLadderProductEvidence) :
    E.product = E.expanded := by
  rw [E.product_factorization, E.product_expansion, E.expanded_eq]

/-- Physics role: the q-representation creation operator and the p/q form are
linked through the source momentum-representation step. -/
structure CreationOperatorRepresentationEvidence where
  q : ℂ
  derivative : ℂ
  momentum : ℂ
  creationQ : ℂ
  creationPQ : ℂ
  derivative_from_momentum : derivative = -Complex.I * momentum
  creation_q_definition : creationQ = (1 / (Real.sqrt 2 : ℂ)) * (-derivative + q)
  creation_pq_definition : creationPQ = (1 / (Real.sqrt 2 : ℂ)) * (Complex.I * momentum + q)
  sign_bridge : -derivative + q = Complex.I * momentum + q

/-- Source-grounded equivalence of the q-derivative and p/q creation forms. -/
theorem creationOperatorRepresentationEquivalence
    (E : CreationOperatorRepresentationEvidence) :
    E.creationQ = E.creationPQ := by
  rw [E.creation_q_definition, E.creation_pq_definition, E.sign_bridge]

/-- Physics role: Fourier integration-by-parts evidence for the
position-to-momentum transform. -/
structure FourierIntegrationByPartsEvidence where
  integral : ℂ
  boundary : ℂ
  derivativeIntegral : ℂ
  result : ℂ
  antiderivative_coefficient : ℂ
  integration_by_parts :
    integral = boundary - antiderivative_coefficient * derivativeIntegral
  boundary_vanishes : boundary = 0
  coefficient_simplifies : -antiderivative_coefficient * derivativeIntegral = result

/-- The Fourier integration-by-parts result from boundary decay and the
antiderivative coefficient. -/
theorem fourierIntegrationByPartsResult
    (E : FourierIntegrationByPartsEvidence) :
    E.integral = E.result := by
  rw [E.integration_by_parts, E.boundary_vanishes]
  simpa using E.coefficient_simplifies

/-- Mathlib grounding: the Fourier phase used for position-to-momentum
transforms.  The real position variable and physical parameters are coerced to
complex scalars before applying Mathlib's complex exponential. -/
noncomputable def fourierPhase (p hbar x : ℝ) : ℂ :=
  Complex.exp (-(Complex.I * (p : ℂ) * (x : ℂ) / (hbar : ℂ)))

/-- Mathlib grounding: the improper position-space Fourier integral is exposed
as a Bochner integral over the real line.  Integrability and boundary-decay
obligations are kept in the grounding packet rather than assumed silently. -/
noncomputable def fourierPositionIntegral (psi : ℝ → ℂ) (p hbar : ℝ) : ℂ :=
  ∫ x, psi x * fourierPhase p hbar x

/-- Mathlib grounding: the derivative-side integral after integration by parts. -/
noncomputable def fourierDerivativeIntegral (psiDerivative : ℝ → ℂ) (p hbar : ℝ) : ℂ :=
  ∫ x, psiDerivative x * fourierPhase p hbar x

/-- Mathlib grounding: a finite-window Fourier integral, used as the bridge
between interval integration by parts and the infinite-line limit. -/
noncomputable def fourierWindowIntegral (psi : ℝ → ℂ) (p hbar a b : ℝ) : ℂ :=
  ∫ x in a..b, psi x * fourierPhase p hbar x

/-- Mathlib grounding: the derivative-side finite-window integral. -/
noncomputable def fourierWindowDerivativeIntegral
    (psiDerivative : ℝ → ℂ) (p hbar a b : ℝ) : ℂ :=
  ∫ x in a..b, psiDerivative x * fourierPhase p hbar x

/-- Physics role: source-backed analytic obligations for Fourier integration
by parts on the real line.  This packet exposes the Hilbert carrier, wavefunction,
derivative, Bochner integrals, finite-window bridge, boundary decay, and
coefficient simplification separately so downstream samples cannot collapse the
calculus into one scalar equality. -/
structure FourierIntegrationByPartsGrounding
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  state : HilbertStateCarrier ℂ H
  psi : ℝ → ℂ
  psiDerivative : ℝ → ℂ
  p : ℝ
  hbar : ℝ
  p_nonzero : p ≠ 0
  hbar_nonzero : hbar ≠ 0
  psi_integrable : MeasureTheory.Integrable (fun x => psi x * fourierPhase p hbar x)
  derivative_integrable :
    MeasureTheory.Integrable (fun x => psiDerivative x * fourierPhase p hbar x)
  derivative_grounding : ∀ x : ℝ, HasDerivAt psi (psiDerivative x) x
  finite_window_by_parts :
    ∀ a b : ℝ,
      fourierWindowIntegral psi p hbar a b =
        psi b * ((hbar : ℂ) / (-(Complex.I * (p : ℂ))) * fourierPhase p hbar b) -
          psi a * ((hbar : ℂ) / (-(Complex.I * (p : ℂ))) * fourierPhase p hbar a) -
            ((hbar : ℂ) / (-(Complex.I * (p : ℂ)))) *
              fourierWindowDerivativeIntegral psiDerivative p hbar a b
  boundaryTerm : ℂ
  boundary_vanishes : boundaryTerm = 0
  infinite_window_limit :
    fourierPositionIntegral psi p hbar =
      boundaryTerm -
        ((hbar : ℂ) / (-(Complex.I * (p : ℂ)))) *
          fourierDerivativeIntegral psiDerivative p hbar
  result : ℂ
  result_eq :
    result = ((hbar : ℂ) / (Complex.I * (p : ℂ))) *
      fourierDerivativeIntegral psiDerivative p hbar
  coefficient_simplifies :
    -((hbar : ℂ) / (-(Complex.I * (p : ℂ)))) *
        fourierDerivativeIntegral psiDerivative p hbar = result

/-- The source Fourier integration-by-parts result over a Mathlib-grounded
Hilbert/Bochner-integral surface. -/
theorem fourierIntegrationByPartsFromGrounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : FourierIntegrationByPartsGrounding H) :
    fourierPositionIntegral G.psi G.p G.hbar = G.result := by
  rw [G.infinite_window_limit, G.boundary_vanishes]
  simpa using G.coefficient_simplifies

/-- Compatibility bridge from the richer Mathlib-grounded Fourier packet to the
older scalar evidence surface used by early source-only examples. -/
noncomputable def fourierIntegrationByPartsEvidenceOfGrounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : FourierIntegrationByPartsGrounding H) : FourierIntegrationByPartsEvidence where
  integral := fourierPositionIntegral G.psi G.p G.hbar
  boundary := G.boundaryTerm
  derivativeIntegral := fourierDerivativeIntegral G.psiDerivative G.p G.hbar
  result := G.result
  antiderivative_coefficient := (G.hbar : ℂ) / (-(Complex.I * (G.p : ℂ)))
  integration_by_parts := G.infinite_window_limit
  boundary_vanishes := G.boundary_vanishes
  coefficient_simplifies := G.coefficient_simplifies

/-- Physics role: abstract Heisenberg equation evidence for a time-independent
Hamiltonian, exposing product-rule and commutator-recognition steps. -/
structure HeisenbergEquationEvidence (A : Type*) [Ring A] [Module ℂ A] where
  hamiltonian : A
  positionAtTime : A
  derivative : A
  commutatorValue : A
  result : A
  hbar : ℂ
  hbar_nonzero : hbar ≠ 0
  product_rule_derivative : derivative = (Complex.I / hbar) • commutatorValue
  commutator_identification : commutatorValue = commutator hamiltonian positionAtTime
  result_definition : result = (Complex.I / hbar) • commutator hamiltonian positionAtTime

/-- Heisenberg equation of motion from the product-rule and commutator
identification surfaces. -/
theorem heisenbergEquationOfMotion
    {A : Type*} [Ring A] [Module ℂ A] (E : HeisenbergEquationEvidence A) :
    E.derivative = E.result := by
  rw [E.product_rule_derivative, E.commutator_identification, E.result_definition]

/-- Physics role: source evidence for position evolution and velocity in the
Heisenberg harmonic oscillator. -/
structure OscillatorVelocityEvidence (E : Type*) [NormedAddCommGroup E] [NormedSpace ℝ E] where
  x0 : E
  p0 : E
  m : ℝ
  omega : ℝ
  t : ℝ
  dx : E
  pAtTime : E
  differentiated_position :
    dx = (-(omega * Real.sin (omega * t))) • x0 + ((1 / m) * Real.cos (omega * t)) • p0
  velocity_relation : dx = (1 / m) • pAtTime
  momentum_solution :
    pAtTime = (-(m * omega) * Real.sin (omega * t)) • x0 + (Real.cos (omega * t)) • p0

/-- The momentum solution associated with a differentiated Heisenberg
oscillator position curve. -/
theorem oscillatorMomentumFromVelocity
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    (O : OscillatorVelocityEvidence E) :
    O.pAtTime = (-(O.m * O.omega) * Real.sin (O.omega * O.t)) • O.x0 +
      (Real.cos (O.omega * O.t)) • O.p0 :=
  O.momentum_solution

/-- Physics role: oscillator second-derivative evidence from the first-order
Heisenberg equations. -/
structure OscillatorPositionSecondDerivativeEvidence
    (E : Type*) [NormedAddCommGroup E] [NormedSpace ℝ E] where
  m : ℝ
  omega : ℝ
  t : ℝ
  x : E
  ddx : E
  dp : E
  second_from_velocity : ddx = (1 / m) • dp
  momentum_equation : dp = -(m * omega ^ 2) • x
  mass_cancellation : (1 / m) • (-(m * omega ^ 2) • x) = -(omega ^ 2) • x

/-- The oscillator equation for the position operator/function. -/
theorem oscillatorPositionSecondDerivative
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    (O : OscillatorPositionSecondDerivativeEvidence E) :
    O.ddx = -(O.omega ^ 2) • O.x := by
  rw [O.second_from_velocity, O.momentum_equation, O.mass_cancellation]

/-- Physics role: Hamiltonian-gradient evidence for the momentum equation of a
one-dimensional harmonic oscillator. -/
structure OscillatorHamiltonEquationEvidence
    (E : Type*) [NormedAddCommGroup E] [NormedSpace ℝ E] where
  m : ℝ
  omega : ℝ
  x : E
  dp : E
  gradient : E
  gradient_from_hamiltonian : gradient = (m * omega ^ 2) • x
  hamilton_equation : dp = -gradient

/-- Momentum equation from Hamilton's equation and the oscillator potential
gradient. -/
theorem oscillatorMomentumEquationFromHamiltonian
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    (O : OscillatorHamiltonEquationEvidence E) :
    O.dp = -(O.m * O.omega ^ 2) • O.x := by
  rw [O.hamilton_equation, O.gradient_from_hamiltonian]
  simp

/-- Physics role: second derivative of momentum obtained by differentiating
the Heisenberg momentum equation. -/
structure OscillatorMomentumSecondDerivativeEvidence
    (E : Type*) [NormedAddCommGroup E] [NormedSpace ℝ E] where
  m : ℝ
  omega : ℝ
  ddp : E
  dx : E
  differentiated_rhs : E
  differentiated_momentum_equation : ddp = differentiated_rhs
  rhs_derivative : differentiated_rhs = -(m * omega ^ 2) • dx

/-- Momentum second derivative from the differentiated oscillator equation. -/
theorem oscillatorMomentumSecondDerivative
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    (O : OscillatorMomentumSecondDerivativeEvidence E) :
    O.ddp = -(O.m * O.omega ^ 2) • O.dx := by
  rw [O.differentiated_momentum_equation, O.rhs_derivative]

/-- Physics role: source evidence for solving the harmonic oscillator initial
value problem. -/
structure OscillatorGeneralSolutionEvidence
    (E : Type*) [NormedAddCommGroup E] [NormedSpace ℝ E] where
  x0 : E
  p0 : E
  A : E
  B : E
  xAtTime : E
  m : ℝ
  omega : ℝ
  t : ℝ
  position_solution : xAtTime = (Real.cos (omega * t)) • A + (Real.sin (omega * t)) • B
  initial_position : A = x0
  initial_momentum : B = (1 / (m * omega)) • p0

/-- Heisenberg harmonic-oscillator position solution from initial data. -/
theorem oscillatorPositionSolutionFromInitialData
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    (O : OscillatorGeneralSolutionEvidence E) :
    O.xAtTime =
      (Real.cos (O.omega * O.t)) • O.x0 +
        (Real.sin (O.omega * O.t)) • ((1 / (O.m * O.omega)) • O.p0) := by
  rw [O.position_solution, O.initial_position, O.initial_momentum]

/-- Physics role: separable-wave derivative evidence. -/
structure SeparableWaveSpatialDerivativeEvidence where
  psi : ℂ
  firstDerivative : ℂ
  secondDerivative : ℂ
  spatialPart : ℂ
  timeFactor : ℂ
  k : ℝ
  first_derivative_step : firstDerivative = (k : ℂ) * spatialPart * timeFactor
  second_derivative_step : secondDerivative = -((k : ℂ) ^ 2) * psi

/-- The second spatial derivative of a separable sine/cosine wave. -/
theorem separableWaveSecondSpatialDerivative
    (W : SeparableWaveSpatialDerivativeEvidence) :
    W.secondDerivative = -((W.k : ℂ) ^ 2) * W.psi :=
  W.second_derivative_step

/-- Physics role: kinetic-energy action evidence on a separable wavefunction. -/
structure KineticEnergyEigenEvidence where
  psi : ℂ
  secondDerivative : ℂ
  kineticEnergyAction : ℂ
  hbar : ℝ
  m : ℝ
  k : ℝ
  second_derivative : secondDerivative = -((k : ℂ) ^ 2) * psi
  kinetic_definition : kineticEnergyAction = -((hbar : ℂ) ^ 2 / (2 * (m : ℂ))) * secondDerivative
  eigenvalue_action :
    -((hbar : ℂ) ^ 2 / (2 * (m : ℂ))) * (-((k : ℂ) ^ 2) * psi) =
      ((hbar : ℂ) ^ 2 * (k : ℂ) ^ 2 / (2 * (m : ℂ))) * psi

/-- Kinetic-energy eigenvalue relation for the separable spatial wave. -/
theorem kineticEnergyEigenRelation
    (W : KineticEnergyEigenEvidence) :
    W.kineticEnergyAction =
      ((W.hbar : ℂ) ^ 2 * (W.k : ℂ) ^ 2 / (2 * (W.m : ℂ))) * W.psi := by
  rw [W.kinetic_definition, W.second_derivative, W.eigenvalue_action]

/-- Physics role: time-dependent Schrödinger separable phase evidence. -/
structure SeparableWaveTDSEEvidence where
  psi : ℂ
  timeDerivative : ℂ
  lhs : ℂ
  rhs : ℂ
  hbar : ℝ
  omega : ℝ
  time_derivative_step : timeDerivative = (-Complex.I * (omega : ℂ)) * psi
  lhs_definition : lhs = Complex.I * (hbar : ℂ) * timeDerivative
  rhs_definition : rhs = (hbar : ℂ) * (omega : ℂ) * psi
  complex_phase_cancellation :
    Complex.I * (hbar : ℂ) * ((-Complex.I * (omega : ℂ)) * psi) =
      (hbar : ℂ) * (omega : ℂ) * psi

/-- Time-dependent Schrödinger eigenstate relation for a separable phase. -/
theorem separableWaveTDSEEigenRelation
    (W : SeparableWaveTDSEEvidence) :
    W.lhs = W.rhs := by
  rw [W.lhs_definition, W.time_derivative_step, W.rhs_definition]
  exact W.complex_phase_cancellation

/-- Physics role: Born-rule variance evidence for position. -/
structure PositionVarianceBornEvidence where
  sigmaSq : ℝ
  secondMoment : ℝ
  mean : ℝ
  densityIntegral : ℝ
  variance_definition : sigmaSq = secondMoment - mean ^ 2
  mean_from_born_density : mean = densityIntegral

/-- Position variance in Born-rule moment form. -/
theorem positionVarianceBornFormula
    (V : PositionVarianceBornEvidence) :
    V.sigmaSq = V.secondMoment - V.densityIntegral ^ 2 := by
  rw [V.variance_definition, V.mean_from_born_density]

/-- Physics role: the pointwise integrand defining the first commutator
calculation in the position representation. -/
structure PositionMomentumInnerDifferenceEvidence where
  fg : ℂ
  gf : ℂ
  integralForm : ℂ
  braket_difference : fg - gf = integralForm

/-- Position-momentum braket difference from the source integral form. -/
theorem positionMomentumInnerDifference
    (E : PositionMomentumInnerDifferenceEvidence) :
    E.fg - E.gf = E.integralForm :=
  E.braket_difference

/-- Physics role: canonical commutator expectation from the product rule and
normalization in the position representation. -/
structure PositionMomentumCanonicalExpectationEvidence where
  commutatorExpectation : ℂ
  integralNorm : ℂ
  hbar : ℝ
  product_rule_reduction :
    commutatorExpectation = Complex.I * (hbar : ℂ) * integralNorm
  normalization : integralNorm = 1

/-- Canonical commutator expectation from product rule plus normalization. -/
theorem positionMomentumCanonicalExpectation
    (E : PositionMomentumCanonicalExpectationEvidence) :
    E.commutatorExpectation = Complex.I * (E.hbar : ℂ) := by
  rw [E.product_rule_reduction, E.normalization]
  simp

/-- Physics role: unequal-time oscillator commutator evidence. -/
structure UnequalTimePositionCommutatorEvidence where
  commutatorAtTimes : ℂ
  initialCommutator : ℂ
  result : ℂ
  m : ℝ
  omega : ℝ
  hbar : ℝ
  t1 : ℝ
  t2 : ℝ
  bilinear_reduction :
    commutatorAtTimes =
      (1 / ((m : ℂ) * (omega : ℂ))) *
        Complex.ofReal (Real.sin (omega * (t2 - t1))) * initialCommutator
  canonical_initial_commutator : initialCommutator = Complex.I * (hbar : ℂ)
  result_definition :
    result =
      (Complex.I * (hbar : ℂ) / ((m : ℂ) * (omega : ℂ))) *
        Complex.ofReal (Real.sin (omega * (t2 - t1)))

/-- Unequal-time position commutator from bilinearity and the initial
canonical commutator. -/
theorem unequalTimePositionCommutator
    (E : UnequalTimePositionCommutatorEvidence) :
    E.commutatorAtTimes = E.result := by
  rw [E.bilinear_reduction, E.canonical_initial_commutator, E.result_definition]
  ring

/-- Physics role: Cauchy-Schwarz intermediate evidence in the Heisenberg route. -/
structure HeisenbergCauchySchwarzIntermediateEvidence where
  fg : ℂ
  gf : ℂ
  quotient : ℂ
  sigmaProductLowerBound : ℂ
  quotient_definition : quotient = (fg - gf) / (2 * Complex.I)
  cauchy_schwarz_bound : sigmaProductLowerBound = quotient ^ 2

/-- The Cauchy-Schwarz intermediate bound in quotient form. -/
theorem heisenbergCauchySchwarzIntermediate
    (E : HeisenbergCauchySchwarzIntermediateEvidence) :
    E.sigmaProductLowerBound = ((E.fg - E.gf) / (2 * Complex.I)) ^ 2 := by
  rw [E.cauchy_schwarz_bound, E.quotient_definition]

/-- Physics role: Jaynes-Cummings/Rabi probability evidence grounded through
the reusable Hilbert-space Rabi state expansion and Born-rule probability. -/
structure RabiProbabilityEvidence where
  Omega : ℝ
  t : ℝ
  Pg : ℝ
  amplitude : ℂ
  amplitude_from_state : amplitude = VacuumRabiAmplitude Omega t
  probability_definition : Pg = probabilityFromAmplitude amplitude

/-- Vacuum Rabi/Jaynes-Cummings probability from transition amplitude and the
Born-rule norm square. -/
theorem rabiProbabilityFromAmplitude
    (R : RabiProbabilityEvidence) :
    R.Pg = Real.sin (R.Omega * R.t / 2) ^ 2 := by
  rw [R.probability_definition, R.amplitude_from_state]
  exact probabilityFromVacuumRabiAmplitude R.Omega R.t

end QuantumMechanicsExamples
end Foundations
end MathformerPhysicsLib
