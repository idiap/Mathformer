-- SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
-- SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
-- SPDX-License-Identifier: MIT
-- Neuro-symbolic AI Group
import Mathlib
import MathformerPhysicsLib.Lean.Foundations.UnboundedOperators

namespace MathformerPhysicsLib
namespace Foundations
namespace HilbertSpace

/-- Mathlib grounding: a physics Hilbert state carrier is a complete Mathlib
inner-product space, not a local replacement for Hilbert-space structure. -/
abbrev HilbertStateCarrier (𝕜 : Type*) (H : Type*) [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] [CompleteSpace H] := H

/-- Mathlib grounding: Hilbert-space inner products are Mathlib `inner` values. -/
def hilbertInner (𝕜 : Type*) {H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (x y : H) : 𝕜 :=
  inner 𝕜 x y

/-- Physics role: the bridge is definitional, preserving Mathlib convention and notation. -/
theorem hilbertInner_apply (𝕜 : Type*) {H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (x y : H) :
    hilbertInner 𝕜 x y = inner 𝕜 x y := rfl

/-- Mathlib grounding: bounded Hilbert operators should use continuous linear maps. -/
abbrev HilbertBoundedOperator (𝕜 : Type*) (H : Type*) [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] := H →L[𝕜] H

/-- Physics role: application of a bounded Hilbert operator is ordinary function application. -/
def applyHilbertOperator {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (T : HilbertBoundedOperator 𝕜 H) (x : H) : H :=
  T x

/-- Physics role: a Dirac transition amplitude is a Mathlib inner product. -/
def transitionAmplitude (𝕜 : Type*) {H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (bra ket : H) : 𝕜 :=
  inner 𝕜 bra ket

/-- Mathlib grounding: transition amplitudes preserve the underlying inner product. -/
theorem transitionAmplitude_apply (𝕜 : Type*) {H : Type*} [RCLike 𝕜]
    [NormedAddCommGroup H] [InnerProductSpace 𝕜 H] (bra ket : H) :
    transitionAmplitude 𝕜 bra ket = inner 𝕜 bra ket := rfl

/-- Mathlib grounding: reversing a complex Dirac transition amplitude gives the
complex conjugate. -/
theorem transitionAmplitude_conjugate_symmetry {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] (f g : H) :
    star (transitionAmplitude ℂ f g) = transitionAmplitude ℂ g f := by
  unfold transitionAmplitude
  exact inner_conj_symm g f

/-- Physics role: expectation values are inner products of a state with the
operator-applied state. -/
def hilbertExpectation {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (T : HilbertBoundedOperator 𝕜 H) (psi : H) : 𝕜 :=
  inner 𝕜 psi (T psi)

/-- Mathlib grounding: bounded Hilbert-operator commutators are continuous
linear maps built from composition, subtraction, and Mathlib operator
application. -/
def hilbertOperatorCommutator {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (X P : HilbertBoundedOperator 𝕜 H) :
    HilbertBoundedOperator 𝕜 H :=
  X.comp P - P.comp X

/-- Physics role: applying a bounded Hilbert-operator commutator expands to the
operator difference `[X, P] ψ = X(P ψ) - P(X ψ)`. -/
theorem hilbertOperatorCommutator_apply {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (X P : HilbertBoundedOperator 𝕜 H) (psi : H) :
    hilbertOperatorCommutator X P psi = X (P psi) - P (X psi) := by
  rfl

/-- Physics role: the expected commutator value in a state is an ordinary
Hilbert expectation of the bounded commutator operator. -/
def hilbertCommutatorExpectation {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (X P : HilbertBoundedOperator 𝕜 H) (psi : H) : 𝕜 :=
  hilbertExpectation (hilbertOperatorCommutator X P) psi

/-- Physics role: a parameterized expectation value keeps the operator and
state curves explicit before differentiating. -/
def parameterizedHilbertExpectation {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] (T : ℝ → HilbertBoundedOperator ℂ H) (psi : ℝ → H)
    (lambda : ℝ) : ℂ :=
  hilbertExpectation (T lambda) (psi lambda)

/-- Mathlib grounding: the parameterized expectation is definitional. -/
theorem parameterizedHilbertExpectation_apply {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] (T : ℝ → HilbertBoundedOperator ℂ H) (psi : ℝ → H)
    (lambda : ℝ) :
    parameterizedHilbertExpectation T psi lambda = hilbertExpectation (T lambda) (psi lambda) := rfl

/-- Mathlib grounding: if two scalar curves agree near a parameter and both have
derivatives there, uniqueness of `HasDerivAt` transfers the derivative value. -/
theorem derivativeEqOfEventuallyEq {energy expectation : ℝ → ℂ} {lambda : ℝ}
    {dEnergy dExpectation : ℂ} (h_eq : energy =ᶠ[nhds lambda] expectation)
    (h_energy : HasDerivAt energy dEnergy lambda)
    (h_expectation : HasDerivAt expectation dExpectation lambda) :
    dEnergy = dExpectation := by
  exact h_energy.unique (h_expectation.congr_of_eventuallyEq h_eq)

/-- Physics role: a parameterized expectation identity differentiates by the
Mathlib uniqueness theorem for derivatives, leaving the calculation of the
expectation derivative as an explicit typed premise. -/
theorem energyDerivativeEqExpectationDerivative {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] (energy : ℝ → ℂ)
    (T : ℝ → HilbertBoundedOperator ℂ H) (psi : ℝ → H) {lambda : ℝ}
    {dEnergy dExpectation : ℂ}
    (energy_eq_expectation_near :
      energy =ᶠ[nhds lambda] fun mu => parameterizedHilbertExpectation T psi mu)
    (energy_has_deriv : HasDerivAt energy dEnergy lambda)
    (expectation_has_deriv :
      HasDerivAt (fun mu => parameterizedHilbertExpectation T psi mu) dExpectation lambda) :
    dEnergy = dExpectation :=
  derivativeEqOfEventuallyEq energy_eq_expectation_near energy_has_deriv expectation_has_deriv

/-- Physics role: source-backed normalized state evidence. -/
structure NormalizedStateWitness {H : Type*} [NormedAddCommGroup H] (psi : H) : Prop where
  norm_eq_one : ‖psi‖ = 1

/-- Physics role: a parameterized Hamiltonian eigenstate equation
`H(λ) ψ(λ) = E(λ) ψ(λ)`. -/
def ParameterizedEigenstateEquation {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] (T : ℝ → HilbertBoundedOperator ℂ H) (psi : ℝ → H)
    (energy : ℝ → ℂ) (lambda : ℝ) : Prop :=
  T lambda (psi lambda) = energy lambda • psi lambda

/-- Physics role: the eigenstate/normalization source facts hold near a
parameter, which is the local form needed for differentiating the expectation
curve. -/
def EigenstateExpectationIdentityNear {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] (energy : ℝ → ℂ)
    (T : ℝ → HilbertBoundedOperator ℂ H) (psi : ℝ → H) (lambda : ℝ) : Prop :=
  ∀ᶠ mu in nhds lambda,
    ParameterizedEigenstateEquation T psi energy mu ∧ NormalizedStateWitness (psi mu)

/-- Frontier 0021-1: a normalized eigenstate has expectation equal to its
eigenvalue. -/
theorem parameterizedHilbertExpectation_eq_eigenvalue_of_eigenstate {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (energy : ℝ → ℂ) (T : ℝ → HilbertBoundedOperator ℂ H) (psi : ℝ → H)
    (lambda : ℝ)
    (eigen_eq : ParameterizedEigenstateEquation T psi energy lambda)
    (normalized : NormalizedStateWitness (psi lambda)) :
    parameterizedHilbertExpectation T psi lambda = energy lambda := by
  unfold parameterizedHilbertExpectation hilbertExpectation
  rw [eigen_eq, inner_smul_right]
  rw [inner_self_eq_norm_sq_to_K, normalized.norm_eq_one]
  norm_num

/-- Frontier 0021-2: source eigenstate and normalization facts near `λ` derive
the local energy/expectation curve identity instead of assuming it. -/
theorem energy_eq_parameterizedExpectation_near_of_eigenstate {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (energy : ℝ → ℂ) (T : ℝ → HilbertBoundedOperator ℂ H) (psi : ℝ → H)
    (lambda : ℝ)
    (near_identity : EigenstateExpectationIdentityNear energy T psi lambda) :
    energy =ᶠ[nhds lambda] fun mu => parameterizedHilbertExpectation T psi mu := by
  filter_upwards [near_identity] with mu hmu
  exact (parameterizedHilbertExpectation_eq_eigenvalue_of_eigenstate
    energy T psi mu hmu.1 hmu.2).symm

/-- Physics role: a fluctuation ket `(T - μ) ψ` is represented using a
Mathlib-backed bounded operator and scalar action. -/
def fluctuationKet {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (T : HilbertBoundedOperator 𝕜 H) (mu : 𝕜) (psi : H) : H :=
  T psi - mu • psi

/-- Physics role: the squared norm of a fluctuation ket, used as a variance
surface before taking square roots. -/
noncomputable def fluctuationNormSquared {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (T : HilbertBoundedOperator 𝕜 H) (mu : 𝕜) (psi : H) : ℝ :=
  ‖fluctuationKet T mu psi‖ ^ 2

/-- Mathlib grounding: the fluctuation norm-squared surface is definitional. -/
theorem fluctuationNormSquared_apply {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (T : HilbertBoundedOperator 𝕜 H) (mu : 𝕜) (psi : H) :
    fluctuationNormSquared T mu psi = ‖fluctuationKet T mu psi‖ ^ 2 := rfl

/-- Physics role: once the Cauchy-Schwarz/commutator work has produced an
intermediate lower bound and identified it with `hbar / 2`, the final
Heisenberg inequality is an order rewrite. -/
theorem heisenbergBoundFromLowerBound {sigmaX sigmaP hbar lowerBound : ℝ}
    (cauchy_schwarz_bound : sigmaX * sigmaP ≥ lowerBound)
    (lower_bound_eq : lowerBound = hbar / 2) :
    sigmaX * sigmaP ≥ hbar / 2 := by
  simpa [lower_bound_eq] using cauchy_schwarz_bound

/-- Mathlib grounding: the final square-root/order step of the Heisenberg
argument follows from a squared lower bound once the standard deviations and
Planck constant are known nonnegative. -/
theorem heisenbergBoundFromSquaredLowerBound {sigmaX sigmaP hbar : ℝ}
    (sigmaX_nonneg : 0 ≤ sigmaX) (sigmaP_nonneg : 0 ≤ sigmaP) (hbar_nonneg : 0 ≤ hbar)
    (squared_bound : (hbar / 2) ^ 2 ≤ (sigmaX * sigmaP) ^ 2) :
    sigmaX * sigmaP ≥ hbar / 2 := by
  have hprod_nonneg : 0 ≤ sigmaX * sigmaP := mul_nonneg sigmaX_nonneg sigmaP_nonneg
  have hhalf_nonneg : 0 ≤ hbar / 2 := by positivity
  nlinarith [sq_nonneg (sigmaX * sigmaP - hbar / 2)]

/-- Mathlib grounding: Cauchy-Schwarz as a squared norm bound for complex
Hilbert inner products. -/
theorem innerNormSquared_le_normSquared_mul_normSquared {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] (f g : H) :
    ‖inner ℂ f g‖ ^ 2 ≤ ‖f‖ ^ 2 * ‖g‖ ^ 2 := by
  have h := norm_inner_le_norm (𝕜 := ℂ) f g
  have hinner : 0 ≤ ‖inner ℂ f g‖ := norm_nonneg _
  have hprod : 0 ≤ ‖f‖ * ‖g‖ := mul_nonneg (norm_nonneg _) (norm_nonneg _)
  nlinarith [sq_nonneg (‖f‖ * ‖g‖ - ‖inner ℂ f g‖)]

/-- Physics role: Cauchy-Schwarz turns an inner-amplitude lower bound into a
variance-product lower bound for fluctuation kets. -/
theorem heisenbergVarianceProductBoundFromInnerLower {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] (X P : HilbertBoundedOperator ℂ H) (xMean pMean : ℂ)
    (psi : H) {hbar : ℝ}
    (inner_lower_bound :
      (hbar / 2) ^ 2 ≤
        ‖transitionAmplitude ℂ (fluctuationKet X xMean psi) (fluctuationKet P pMean psi)‖ ^ 2) :
    (hbar / 2) ^ 2 ≤ fluctuationNormSquared X xMean psi * fluctuationNormSquared P pMean psi := by
  exact inner_lower_bound.trans
    (innerNormSquared_le_normSquared_mul_normSquared
      (fluctuationKet X xMean psi) (fluctuationKet P pMean psi))

/-- Mathlib grounding: variance identities rewrite a variance-product bound into
the squared standard-deviation product used by the final order step. -/
theorem heisenbergSquaredBoundFromVarianceIdentities {sigmaX sigmaP hbar varianceX varianceP : ℝ}
    (sigmaX_variance : sigmaX ^ 2 = varianceX)
    (sigmaP_variance : sigmaP ^ 2 = varianceP)
    (variance_product_bound : (hbar / 2) ^ 2 ≤ varianceX * varianceP) :
    (hbar / 2) ^ 2 ≤ (sigmaX * sigmaP) ^ 2 := by
  nlinarith [sigmaX_variance, sigmaP_variance]

/-- Physics role: a probability from a complex amplitude is its squared norm. -/
noncomputable def probabilityFromAmplitude (z : ℂ) : ℝ :=
  ‖z‖ ^ 2

/-- Mathlib grounding: `probabilityFromAmplitude` is definitionally the
squared norm of the complex amplitude. -/
theorem probabilityFromAmplitude_apply (z : ℂ) :
    probabilityFromAmplitude z = ‖z‖ ^ 2 := rfl

/-- Mathlib grounding: equality of amplitudes transports through the Born-rule
probability surface. -/
theorem probabilityFromAmplitude_congr {z w : ℂ} (h : z = w) :
    probabilityFromAmplitude z = probabilityFromAmplitude w := by
  rw [h]

/-- Mathlib grounding: Hilbert bases are Mathlib `HilbertBasis` values. -/
abbrev HilbertBasisSurface (ι : Type*) (𝕜 : Type*) (H : Type*) [RCLike 𝕜]
    [NormedAddCommGroup H] [InnerProductSpace 𝕜 H] [CompleteSpace H] :=
  HilbertBasis ι 𝕜 H

/-- Physics role: source-backed conjugate symmetry for a Dirac braket pair. -/
structure DiracConjugateSymmetryWitness (fg gf : ℂ) : Prop where
  conjugate_relation : star fg = gf

/-- Physics role: the Dirac expression `(⟨f|g⟩ - ⟨g|f⟩)/(2i)` as a named
complex scalar before downstream real/imaginary projection. -/
noncomputable def diracImaginaryQuotient (fg gf : ℂ) : ℂ :=
  (fg - gf) / (2 * Complex.I)

/-- Mathlib grounding: the Dirac imaginary quotient is definitional. -/
theorem diracImaginaryQuotient_apply (fg gf : ℂ) :
    diracImaginaryQuotient fg gf = (fg - gf) / (2 * Complex.I) := rfl

/-- Physics role: under Dirac conjugate symmetry, the reversed braket can be
replaced by the complex conjugate in the imaginary-part quotient. -/
theorem diracImaginaryQuotient_eq_starQuotient {fg gf : ℂ} (h_conj : star fg = gf) :
    diracImaginaryQuotient fg gf = (fg - star fg) / (2 * Complex.I) := by
  unfold diracImaginaryQuotient
  rw [h_conj]

/-- Mathlib grounding: for a complex scalar, the Dirac imaginary quotient with
the conjugate is the scalar imaginary part embedded in `ℂ`. -/
theorem diracImaginaryQuotient_star_eq_im (z : ℂ) :
    diracImaginaryQuotient z (star z) = (z.im : ℂ) := by
  rw [diracImaginaryQuotient]
  field_simp [Complex.I_ne_zero]
  cases z
  apply Complex.ext
  · simp
  · simp
    ring

/-- Mathlib grounding: conjugate symmetry identifies the Dirac imaginary
quotient with the scalar imaginary part. -/
theorem diracImaginaryQuotient_eq_im_of_conjugate {fg gf : ℂ} (h_conj : star fg = gf) :
    diracImaginaryQuotient fg gf = (Complex.im fg : ℂ) := by
  rw [← h_conj]
  exact diracImaginaryQuotient_star_eq_im fg

/-- Mathlib grounding: the squared Dirac imaginary quotient is the squared
complex imaginary part under conjugate symmetry. -/
theorem diracImaginaryQuotient_sq_eq_im_sq_of_conjugate {fg gf : ℂ}
    (h_conj : star fg = gf) :
    (diracImaginaryQuotient fg gf) ^ 2 = (Complex.im fg : ℂ) ^ 2 := by
  exact congrArg (fun z : ℂ => z ^ 2) (diracImaginaryQuotient_eq_im_of_conjugate h_conj)

/-- Mathlib grounding: if the Dirac imaginary quotient equals `hbar / 2`, then
`(hbar / 2)^2` is bounded by the squared norm of the underlying scalar. -/
theorem diracImaginaryQuotient_star_lower_bound {z : ℂ} {hbar : ℝ}
    (h_quotient : diracImaginaryQuotient z (star z) = (hbar : ℂ) / 2) :
    (hbar / 2) ^ 2 ≤ ‖z‖ ^ 2 := by
  have hq : diracImaginaryQuotient z (star z) = (z.im : ℂ) :=
    diracImaginaryQuotient_star_eq_im z
  have him_complex : (z.im : ℂ) = (hbar : ℂ) / 2 := by
    rw [← hq]
    exact h_quotient
  have him : z.im = hbar / 2 := by
    exact_mod_cast him_complex
  rw [← him]
  have h_im_abs : |z.im| ≤ ‖z‖ := Complex.abs_im_le_norm z
  have h_abs_norm : |z.im| ≤ |‖z‖| := by
    simpa [abs_of_nonneg (norm_nonneg z)] using h_im_abs
  exact sq_le_sq.mpr h_abs_norm

/-- Physics role: combine Dirac conjugate symmetry with the complex imaginary
quotient lower-bound lemma. -/
theorem diracImaginaryQuotient_conjugate_lower_bound {fg gf : ℂ} {hbar : ℝ}
    (h_conj : star fg = gf) (h_quotient : diracImaginaryQuotient fg gf = (hbar : ℂ) / 2) :
    (hbar / 2) ^ 2 ≤ ‖fg‖ ^ 2 := by
  have h_star : diracImaginaryQuotient fg (star fg) = (hbar : ℂ) / 2 := by
    rw [h_conj]
    exact h_quotient
  exact diracImaginaryQuotient_star_lower_bound h_star

/-- Physics role: the source chain
`⟨f|g⟩ - ⟨g|f⟩ = ⟨ψ|[X,P]|ψ⟩ = iℏ` proves the Dirac imaginary quotient bridge
instead of assuming that quotient directly. -/
theorem diracImaginaryQuotient_from_commutator_expectation {fg gf comm : ℂ} {hbar : ℝ}
    (braket_difference_eq_commutator : fg - gf = comm)
    (commutator_expectation_eq_canonical : comm = Complex.I * (hbar : ℂ)) :
    diracImaginaryQuotient fg gf = (hbar : ℂ) / 2 := by
  unfold diracImaginaryQuotient
  rw [braket_difference_eq_commutator, commutator_expectation_eq_canonical]
  field_simp [Complex.I_ne_zero]

/-- Physics role: explicit witness that two state vectors are orthogonal. -/
structure HilbertOrthogonalityWitness {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (x y : H) : Prop where
  inner_eq_zero : inner 𝕜 x y = 0

/-- Frontier 0015-1: a two-level Rabi state expansion in a Hilbert carrier. -/
def TwoLevelRabiStateExpansion {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (psi excitedZero groundOne : H) (Omega t : ℝ) : Prop :=
  psi =
    (Real.cos (Omega * t / 2) : ℂ) • excitedZero +
      ((-Complex.I) * (Real.sin (Omega * t / 2) : ℂ)) • groundOne

/-- Frontier 0015-2: the expected vacuum-Rabi transition amplitude. -/
noncomputable def VacuumRabiAmplitude (Omega t : ℝ) : ℂ :=
  (-Complex.I) * (Real.sin (Omega * t / 2) : ℂ)

/-- Frontier 0015-3: under a normalized target ket and orthogonal source ket,
the Rabi state expansion gives the target transition amplitude. -/
theorem transitionAmplitude_from_twoLevelRabiStateExpansion {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (psi groundOne excitedZero : HilbertStateCarrier ℂ H) (Omega t : ℝ)
    (ground_normalized : NormalizedStateWitness groundOne)
    (orthogonality : HilbertOrthogonalityWitness (𝕜 := ℂ) groundOne excitedZero)
    (state_expansion : TwoLevelRabiStateExpansion psi excitedZero groundOne Omega t) :
    transitionAmplitude ℂ groundOne psi = VacuumRabiAmplitude Omega t := by
  have hground : inner ℂ groundOne groundOne = 1 := by
    rw [inner_self_eq_norm_sq_to_K, ground_normalized.norm_eq_one]
    norm_num
  unfold TwoLevelRabiStateExpansion at state_expansion
  unfold VacuumRabiAmplitude
  rw [state_expansion]
  unfold transitionAmplitude
  rw [inner_add_right, inner_smul_right, inner_smul_right]
  rw [orthogonality.inner_eq_zero, hground]
  simp

/-- Frontier 0015-4: the vacuum-Rabi amplitude surface unfolds to `-i sin`. -/
theorem vacuumRabiAmplitude_apply (Omega t : ℝ) :
    VacuumRabiAmplitude Omega t =
      (-Complex.I) * (Real.sin (Omega * t / 2) : ℂ) := rfl

/-- Frontier 0015-5: Mathlib's complex norm-square of `-i r` is `r²`. -/
theorem complex_normSq_neg_I_mul_real (r : ℝ) :
    Complex.normSq ((-Complex.I) * (r : ℂ)) = r ^ 2 := by
  simp [Complex.normSq_apply]
  ring

/-- Frontier 0015-6: the squared norm of `-i r` is `r²`. -/
theorem norm_neg_I_mul_real_sq (r : ℝ) :
    ‖((-Complex.I) * (r : ℂ))‖ ^ 2 = r ^ 2 := by
  rw [norm_mul, norm_neg, Complex.norm_I]
  norm_num

/-- Frontier 0015-7: the Born probability of `-i r` is `r²`. -/
theorem probabilityFromAmplitude_neg_I_mul_real (r : ℝ) :
    probabilityFromAmplitude ((-Complex.I) * (r : ℂ)) = r ^ 2 := by
  unfold probabilityFromAmplitude
  exact norm_neg_I_mul_real_sq r

/-- Frontier 0015-8: the vacuum-Rabi amplitude has Born probability
`sin²(Ωt/2)`. -/
theorem probabilityFromVacuumRabiAmplitude (Omega t : ℝ) :
    probabilityFromAmplitude (VacuumRabiAmplitude Omega t) =
      Real.sin (Omega * t / 2) ^ 2 := by
  unfold VacuumRabiAmplitude
  exact probabilityFromAmplitude_neg_I_mul_real (Real.sin (Omega * t / 2))

/-- Frontier 0015-9: a transition amplitude identified with the vacuum-Rabi
amplitude yields the source probability. -/
theorem bornProbabilityFromVacuumRabiTransitionAmplitude {z : ℂ} {Omega t : ℝ}
    (h : z = VacuumRabiAmplitude Omega t) :
    probabilityFromAmplitude z = Real.sin (Omega * t / 2) ^ 2 := by
  rw [h]
  exact probabilityFromVacuumRabiAmplitude Omega t

/-- Frontier 0015-10: if the measured probability is defined by the Born rule
from the transition amplitude, the Rabi probability follows from the state
expansion. -/
theorem vacuumRabiProbabilityFromStateExpansion {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (psi groundOne excitedZero : HilbertStateCarrier ℂ H) (Omega t Pg : ℝ)
    (ground_normalized : NormalizedStateWitness groundOne)
    (orthogonality : HilbertOrthogonalityWitness (𝕜 := ℂ) groundOne excitedZero)
    (state_expansion : TwoLevelRabiStateExpansion psi excitedZero groundOne Omega t)
    (probability_definition :
      Pg = probabilityFromAmplitude (transitionAmplitude ℂ groundOne psi)) :
    Pg = Real.sin (Omega * t / 2) ^ 2 := by
  rw [probability_definition]
  exact bornProbabilityFromVacuumRabiTransitionAmplitude
    (transitionAmplitude_from_twoLevelRabiStateExpansion
      psi groundOne excitedZero Omega t ground_normalized orthogonality state_expansion)

/-- Physics role: projection-like operators should expose idempotence and an
inner-product symmetry condition before they are used as orthogonal projections. -/
structure HilbertProjectionWitness {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (P : HilbertBoundedOperator 𝕜 H) : Prop where
  idempotent : P.comp P = P
  inner_symmetric : ∀ x y : H, inner 𝕜 (P x) y = inner 𝕜 x (P y)

/-- Physics role: a candidate adjoint must satisfy the Hilbert-space inner-product relation. -/
structure HilbertOperatorAdjointWitness {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (T Tstar : HilbertBoundedOperator 𝕜 H) : Prop where
  adjoint_relation : ∀ x y : H, inner 𝕜 (T x) y = inner 𝕜 x (Tstar y)

/-- Physics role: a self-adjoint observable is represented by the adjoint relation to itself. -/
structure SelfAdjointOperatorWitness {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (T : HilbertBoundedOperator 𝕜 H) : Prop where
  self_adjoint_relation : ∀ x y : H, inner 𝕜 (T x) y = inner 𝕜 x (T y)

/-- Physics role: source-level differentiated eigenstate equation
`H' ψ + H ψ' = E' ψ + E ψ'` at a parameter. -/
def DifferentiatedEigenstateEquation {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] (H0 dH : HilbertBoundedOperator ℂ H)
    (psi dpsi : H) (energy dEnergy : ℂ) : Prop :=
  dH psi + H0 dpsi = dEnergy • psi + energy • dpsi

/-- Frontier 0021-3: the Hellmann-Feynman derivative follows from the
differentiated eigen-equation, normalization, self-adjointness, and the
real-valued eigenvalue cancellation. -/
theorem hellmannFeynmanDerivativeFromDifferentiatedEigenEquation {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (H0 dH : HilbertBoundedOperator ℂ H) (psi dpsi : H) (energy dEnergy : ℂ)
    (normalized : NormalizedStateWitness psi)
    (self_adjoint : SelfAdjointOperatorWitness H0)
    (eigen_eq : H0 psi = energy • psi)
    (eigenvalue_real : star energy = energy)
    (differentiated_eigen_eq :
      DifferentiatedEigenstateEquation H0 dH psi dpsi energy dEnergy) :
    dEnergy = hilbertExpectation dH psi := by
  have hnorm : inner ℂ psi psi = 1 := by
    rw [inner_self_eq_norm_sq_to_K, normalized.norm_eq_one]
    norm_num
  have hH : inner ℂ psi (H0 dpsi) = energy * inner ℂ psi dpsi := by
    rw [← self_adjoint.self_adjoint_relation psi dpsi, eigen_eq, inner_smul_left]
    have hstar : (starRingEnd ℂ) energy = energy := by
      simpa using eigenvalue_real
    rw [hstar]
  unfold DifferentiatedEigenstateEquation at differentiated_eigen_eq
  have hinner := congrArg (fun v => inner ℂ psi v) differentiated_eigen_eq
  change inner ℂ psi (dH psi + H0 dpsi) =
    inner ℂ psi (dEnergy • psi + energy • dpsi) at hinner
  rw [inner_add_right, inner_add_right, inner_smul_right, inner_smul_right,
    hnorm, hH] at hinner
  have hinner' : inner ℂ psi (dH psi) + energy * inner ℂ psi dpsi =
      dEnergy + energy * inner ℂ psi dpsi := by
    simpa using hinner
  have hcalc : inner ℂ psi (dH psi) = dEnergy :=
    add_right_cancel hinner'
  unfold hilbertExpectation
  exact hcalc.symm

/-- Frontier 0021-4: a complete local parameterized-Hamiltonian packet for
Hellmann-Feynman style autoformalization.  The source curves, pointwise state,
operator derivative, state derivative, eigenstate evidence, self-adjointness,
real-eigenvalue fact, and derivative evidence stay visible. -/
structure ParameterizedHamiltonianDerivativeFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  energy : ℝ → ℂ
  hamiltonianCurve : ℝ → HilbertBoundedOperator ℂ H
  stateCurve : ℝ → HilbertStateCarrier ℂ H
  lambda : ℝ
  dHamiltonian : HilbertBoundedOperator ℂ H
  stateDerivativeAtLambda : HilbertStateCarrier ℂ H
  psi : HilbertStateCarrier ℂ H
  dE : ℂ
  normalized : NormalizedStateWitness psi
  state_at_lambda : stateCurve lambda = psi
  near_eigenstate_identity :
    EigenstateExpectationIdentityNear energy hamiltonianCurve stateCurve lambda
  eigen_eq_at_lambda :
    ParameterizedEigenstateEquation hamiltonianCurve stateCurve energy lambda
  hamiltonian_self_adjoint :
    SelfAdjointOperatorWitness (hamiltonianCurve lambda)
  eigenvalue_real_at_lambda : star (energy lambda) = energy lambda
  differentiated_eigen_eq :
    DifferentiatedEigenstateEquation (hamiltonianCurve lambda) dHamiltonian
      psi stateDerivativeAtLambda (energy lambda) dE
  energy_has_deriv : HasDerivAt energy dE lambda

/-- Frontier support: the complete local Hamiltonian packet yields the
Hellmann-Feynman expectation derivative value. -/
theorem parameterizedHamiltonianDerivativeFrontier_expectation {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : ParameterizedHamiltonianDerivativeFrontier (H := H)) :
    F.dE = hilbertExpectation F.dHamiltonian F.psi := by
  have h_eigen_psi :
      F.hamiltonianCurve F.lambda F.psi = F.energy F.lambda • F.psi := by
    have h := F.eigen_eq_at_lambda
    unfold ParameterizedEigenstateEquation at h
    rwa [F.state_at_lambda] at h
  exact hellmannFeynmanDerivativeFromDifferentiatedEigenEquation
    (F.hamiltonianCurve F.lambda) F.dHamiltonian F.psi F.stateDerivativeAtLambda
    (F.energy F.lambda) F.dE F.normalized F.hamiltonian_self_adjoint h_eigen_psi
    F.eigenvalue_real_at_lambda F.differentiated_eigen_eq

/-- Frontier 0021-5: the parameterized expectation curve induced by a
Hamiltonian and state curve. -/
noncomputable def parameterizedHamiltonianExpectationCurve {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (hamiltonianCurve : ℝ → HilbertBoundedOperator ℂ H)
    (stateCurve : ℝ → H) : ℝ → ℂ :=
  fun mu => parameterizedHilbertExpectation hamiltonianCurve stateCurve mu

/-- Frontier support: the local Hamiltonian packet also yields the derivative
of the expectation curve at the same parameter. -/
theorem parameterizedHamiltonianDerivativeFrontier_expectation_has_deriv {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : ParameterizedHamiltonianDerivativeFrontier (H := H)) :
    HasDerivAt
      (parameterizedHamiltonianExpectationCurve F.hamiltonianCurve F.stateCurve)
      (hilbertExpectation F.dHamiltonian F.psi) F.lambda := by
  have h_energy_expectation_near :
      F.energy =ᶠ[nhds F.lambda]
        (fun mu => parameterizedHilbertExpectation F.hamiltonianCurve F.stateCurve mu) :=
    energy_eq_parameterizedExpectation_near_of_eigenstate
      F.energy F.hamiltonianCurve F.stateCurve F.lambda F.near_eigenstate_identity
  have h_expectation_has_deriv_dE :
      HasDerivAt
        (fun mu => parameterizedHilbertExpectation F.hamiltonianCurve F.stateCurve mu)
        F.dE F.lambda :=
    F.energy_has_deriv.congr_of_eventuallyEq h_energy_expectation_near.symm
  simpa [parameterizedHamiltonianExpectationCurve,
    parameterizedHamiltonianDerivativeFrontier_expectation F] using
      h_expectation_has_deriv_dE

/-- Frontier 0021-7: the action curve `λ ↦ H(λ) ψ(λ)` is kept as a named
Mathlib-grounded function before differentiating the eigenstate equation. -/
noncomputable def parameterizedHamiltonianActionCurve {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (hamiltonianCurve : ℝ → HilbertBoundedOperator ℂ H)
    (stateCurve : ℝ → H) : ℝ → H :=
  fun mu => hamiltonianCurve mu (stateCurve mu)

/-- Frontier 0021-8: the eigenvalue-side curve `λ ↦ E(λ) • ψ(λ)` is explicit,
so the differentiated eigen-equation can be grounded in two differentiable
curves instead of appearing only as an opaque premise. -/
noncomputable def parameterizedEigenvalueStateCurve {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (energy : ℝ → ℂ) (stateCurve : ℝ → H) : ℝ → H :=
  fun mu => energy mu • stateCurve mu

/-- Frontier support: near-parameter eigenstate equations are exactly near
equality of the action curve and the eigenvalue-side curve. -/
theorem parameterizedActionCurve_eq_eigenvalueStateCurve_near_of_eigenstate
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (energy : ℝ → ℂ) (hamiltonianCurve : ℝ → HilbertBoundedOperator ℂ H)
    (stateCurve : ℝ → H) (lambda : ℝ)
    (near_identity :
      EigenstateExpectationIdentityNear energy hamiltonianCurve stateCurve lambda) :
    parameterizedHamiltonianActionCurve hamiltonianCurve stateCurve =ᶠ[nhds lambda]
      parameterizedEigenvalueStateCurve energy stateCurve := by
  filter_upwards [near_identity] with mu hmu
  exact hmu.1

/-- Frontier support: differentiating the near-parameter action/eigenvalue
curve equality generates the source differentiated eigenstate equation by
Mathlib derivative uniqueness. -/
theorem differentiatedEigenstateEquation_of_actionCurve_derivatives {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (energy : ℝ → ℂ) (hamiltonianCurve : ℝ → HilbertBoundedOperator ℂ H)
    (stateCurve : ℝ → H) (lambda : ℝ)
    (dHamiltonian : HilbertBoundedOperator ℂ H) (psi dpsi : H) (dE : ℂ)
    (action_eq_eigenvalue_near :
      parameterizedHamiltonianActionCurve hamiltonianCurve stateCurve =ᶠ[nhds lambda]
        parameterizedEigenvalueStateCurve energy stateCurve)
    (action_curve_has_deriv :
      HasDerivAt (parameterizedHamiltonianActionCurve hamiltonianCurve stateCurve)
        (dHamiltonian psi + hamiltonianCurve lambda dpsi) lambda)
    (eigenvalue_state_curve_has_deriv :
      HasDerivAt (parameterizedEigenvalueStateCurve energy stateCurve)
        (dE • psi + energy lambda • dpsi) lambda) :
    DifferentiatedEigenstateEquation (hamiltonianCurve lambda) dHamiltonian psi dpsi
      (energy lambda) dE := by
  have hderiv_eq :
      dHamiltonian psi + hamiltonianCurve lambda dpsi =
        dE • psi + energy lambda • dpsi :=
    action_curve_has_deriv.unique
      (eigenvalue_state_curve_has_deriv.congr_of_eventuallyEq
        action_eq_eigenvalue_near)
  exact hderiv_eq

/-- Frontier 0021-9a: generated derivative frontier for parameterized
Hamiltonians.  Unlike `ParameterizedHamiltonianDerivativeFrontier`, this packet
does not assume the differentiated eigen-equation; it derives it from
near-eigenstate curve equality and derivative uniqueness. -/
structure ParameterizedHamiltonianGeneratedDerivativeFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  energy : ℝ → ℂ
  hamiltonianCurve : ℝ → HilbertBoundedOperator ℂ H
  stateCurve : ℝ → HilbertStateCarrier ℂ H
  lambda : ℝ
  dHamiltonian : HilbertBoundedOperator ℂ H
  stateDerivativeAtLambda : HilbertStateCarrier ℂ H
  psi : HilbertStateCarrier ℂ H
  dE : ℂ
  normalized : NormalizedStateWitness psi
  state_at_lambda : stateCurve lambda = psi
  near_eigenstate_identity :
    EigenstateExpectationIdentityNear energy hamiltonianCurve stateCurve lambda
  eigen_eq_at_lambda :
    ParameterizedEigenstateEquation hamiltonianCurve stateCurve energy lambda
  hamiltonian_self_adjoint :
    SelfAdjointOperatorWitness (hamiltonianCurve lambda)
  eigenvalue_real_at_lambda : star (energy lambda) = energy lambda
  energy_has_deriv : HasDerivAt energy dE lambda
  hamiltonian_has_deriv :
    HasDerivAt hamiltonianCurve dHamiltonian lambda
  state_has_deriv :
    HasDerivAt stateCurve stateDerivativeAtLambda lambda
  action_curve_has_deriv :
    HasDerivAt
      (parameterizedHamiltonianActionCurve hamiltonianCurve stateCurve)
      (dHamiltonian psi + hamiltonianCurve lambda stateDerivativeAtLambda)
      lambda
  eigenvalue_state_curve_has_deriv :
    HasDerivAt
      (parameterizedEigenvalueStateCurve energy stateCurve)
      (dE • psi + energy lambda • stateDerivativeAtLambda)
      lambda

/-- Frontier support: generated derivative packets expose the action/eigenvalue
curve equality that drives the differentiated eigen-equation. -/
theorem parameterizedHamiltonianGeneratedDerivativeFrontier_action_eq_eigenvalue_near
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    parameterizedHamiltonianActionCurve G.hamiltonianCurve G.stateCurve =ᶠ[nhds G.lambda]
      parameterizedEigenvalueStateCurve G.energy G.stateCurve :=
  parameterizedActionCurve_eq_eigenvalueStateCurve_near_of_eigenstate
    G.energy G.hamiltonianCurve G.stateCurve G.lambda G.near_eigenstate_identity

/-- Frontier support: generated derivative packets derive the differentiated
eigenstate equation without treating it as a source assumption. -/
theorem parameterizedHamiltonianGeneratedDerivativeFrontier_differentiated_eigen_eq
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    DifferentiatedEigenstateEquation (G.hamiltonianCurve G.lambda) G.dHamiltonian
      G.psi G.stateDerivativeAtLambda (G.energy G.lambda) G.dE :=
  differentiatedEigenstateEquation_of_actionCurve_derivatives
    G.energy G.hamiltonianCurve G.stateCurve G.lambda G.dHamiltonian G.psi
    G.stateDerivativeAtLambda G.dE
    (parameterizedHamiltonianGeneratedDerivativeFrontier_action_eq_eigenvalue_near G)
    G.action_curve_has_deriv G.eigenvalue_state_curve_has_deriv

/-- Frontier support: a generated derivative packet can be projected to the
older local derivative packet, with the differentiated equation filled by the
generated theorem. -/
def ParameterizedHamiltonianGeneratedDerivativeFrontier.toDerivativeFrontier
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    ParameterizedHamiltonianDerivativeFrontier (H := H) where
  energy := G.energy
  hamiltonianCurve := G.hamiltonianCurve
  stateCurve := G.stateCurve
  lambda := G.lambda
  dHamiltonian := G.dHamiltonian
  stateDerivativeAtLambda := G.stateDerivativeAtLambda
  psi := G.psi
  dE := G.dE
  normalized := G.normalized
  state_at_lambda := G.state_at_lambda
  near_eigenstate_identity := G.near_eigenstate_identity
  eigen_eq_at_lambda := G.eigen_eq_at_lambda
  hamiltonian_self_adjoint := G.hamiltonian_self_adjoint
  eigenvalue_real_at_lambda := G.eigenvalue_real_at_lambda
  differentiated_eigen_eq :=
    parameterizedHamiltonianGeneratedDerivativeFrontier_differentiated_eigen_eq G
  energy_has_deriv := G.energy_has_deriv

/-- Frontier support: generated derivative packets prove the
Hellmann-Feynman expectation value through their generated local derivative
packet. -/
theorem parameterizedHamiltonianGeneratedDerivativeFrontier_expectation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    G.dE = hilbertExpectation G.dHamiltonian G.psi :=
  parameterizedHamiltonianDerivativeFrontier_expectation G.toDerivativeFrontier

/-- Frontier support: generated derivative packets also prove the derivative
of the parameterized expectation curve. -/
theorem parameterizedHamiltonianGeneratedDerivativeFrontier_expectation_has_deriv
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) :
    HasDerivAt
      (parameterizedHamiltonianExpectationCurve G.hamiltonianCurve G.stateCurve)
      (hilbertExpectation G.dHamiltonian G.psi) G.lambda :=
  parameterizedHamiltonianDerivativeFrontier_expectation_has_deriv
    G.toDerivativeFrontier

/-- Physics role: the normalization derivative constraint produced by a
normalized eigenstate branch. -/
def ParameterizedStateNormalizationDerivativeConstraint {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] (psi dpsi : H) : Prop :=
  inner ℂ psi dpsi + inner ℂ dpsi psi = 0

/-- Physics role: a phase gauge condition for a differentiated eigenstate
branch, written as an explicit inner-product constraint. -/
def ParameterizedEigenstatePhaseGaugeCondition {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] (psi dpsi : H) : Prop :=
  inner ℂ psi dpsi = 0

/-- Frontier 0021-12a: typed normalization and phase-gauge data for a
parameterized Hamiltonian branch. -/
structure ParameterizedHamiltonianGaugeFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) where
  normalization_near_parameter :
    ∀ᶠ mu in nhds G.lambda, NormalizedStateWitness (G.stateCurve mu)
  normalization_derivative_constraint :
    ParameterizedStateNormalizationDerivativeConstraint G.psi G.stateDerivativeAtLambda
  phase_gauge_selected :
    ParameterizedEigenstatePhaseGaugeCondition G.psi G.stateDerivativeAtLambda
  phase_gauge_derivative_constraint :
    HasDerivAt (fun mu => inner ℂ (G.stateCurve mu) G.psi) 0 G.lambda

/-- Frontier 0021-12b: typed spectral-projection branch data for a
parameterized Hamiltonian eigenbranch. -/
structure ParameterizedHamiltonianSpectralProjectionBranch {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) where
  projectionCurve : ℝ → HilbertBoundedOperator ℂ H
  dProjection : HilbertBoundedOperator ℂ H
  spectralWindow : Set ℂ
  projection_witness_near :
    ∀ᶠ mu in nhds G.lambda, HilbertProjectionWitness (projectionCurve mu)
  projection_self_adjoint_near :
    ∀ᶠ mu in nhds G.lambda, SelfAdjointOperatorWitness (projectionCurve mu)
  projection_tracks_state_near :
    ∀ᶠ mu in nhds G.lambda, projectionCurve mu (G.stateCurve mu) = G.stateCurve mu
  eigenvalue_in_spectral_window_near :
    ∀ᶠ mu in nhds G.lambda, G.energy mu ∈ spectralWindow
  simple_eigenvalue_gap_radius : ℝ
  simple_eigenvalue_gap_positive : 0 < simple_eigenvalue_gap_radius
  isolated_spectral_window_near :
    ∀ᶠ mu in nhds G.lambda,
      ∀ z : ℂ, z ∈ spectralWindow → z ≠ G.energy mu →
        simple_eigenvalue_gap_radius ≤ ‖z - G.energy mu‖
  spectral_projection_has_deriv :
    HasDerivAt projectionCurve dProjection G.lambda
  eigenvector_branch_has_deriv :
    HasDerivAt G.stateCurve G.stateDerivativeAtLambda G.lambda

/-- Frontier 0021-12c: typed unbounded-domain data for relating a
domain-bearing Hamiltonian branch to the bounded local core used in the
Hellmann-Feynman proof. -/
structure ParameterizedHamiltonianUnboundedDomainFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)) where
  unboundedHamiltonianCurve :
    ℝ → MathformerPhysicsLib.Foundations.UnboundedOperators.UnboundedHilbertOperator ℂ H
  unboundedDerivative :
    MathformerPhysicsLib.Foundations.UnboundedOperators.UnboundedHilbertOperator ℂ H
  commonCore : Submodule ℂ H
  common_core_dense : Dense ((commonCore : Set H))
  common_core_in_hamiltonian_domain_near :
    ∀ᶠ mu in nhds G.lambda, commonCore ≤ (unboundedHamiltonianCurve mu).domain
  common_core_in_derivative_domain :
    commonCore ≤ unboundedDerivative.domain
  state_branch_mem_domain_near :
    ∀ᶠ mu in nhds G.lambda,
      MathformerPhysicsLib.Foundations.UnboundedOperators.MemDomain
        (unboundedHamiltonianCurve mu) (G.stateCurve mu)
  state_derivative_mem_derivative_domain :
    MathformerPhysicsLib.Foundations.UnboundedOperators.MemDomain
      unboundedDerivative G.stateDerivativeAtLambda
  bounded_core_matches_hamiltonian_near :
    ∀ᶠ mu in nhds G.lambda,
      ∃ hcore : commonCore ≤ (unboundedHamiltonianCurve mu).domain,
        ∀ x : commonCore,
          MathformerPhysicsLib.Foundations.UnboundedOperators.apply
            (unboundedHamiltonianCurve mu) (x : H) (hcore x.property) =
              G.hamiltonianCurve mu (x : H)
  bounded_core_matches_derivative :
    ∀ x : commonCore,
      MathformerPhysicsLib.Foundations.UnboundedOperators.apply
        unboundedDerivative (x : H) (common_core_in_derivative_domain x.property) =
          G.dHamiltonian (x : H)

/-- Frontier 0021-12: a controlled recursive expansion ledger for
parameterized Hamiltonians.  The first obligations pin the generated derivative
route to Mathlib derivative and eventual-equality surfaces; the later
obligations name gauge, spectral-branch, and unbounded-domain constraints so
recursive grounding remains systematic instead of implicit. -/
structure ParameterizedHamiltonianRecursiveExpansionFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  generated : ParameterizedHamiltonianGeneratedDerivativeFrontier (H := H)
  operator_curve_derivative_grounding :
    HasDerivAt generated.hamiltonianCurve generated.dHamiltonian generated.lambda
  state_curve_derivative_grounding :
    HasDerivAt generated.stateCurve generated.stateDerivativeAtLambda generated.lambda
  energy_curve_derivative_grounding :
    HasDerivAt generated.energy generated.dE generated.lambda
  action_curve_derivative_grounding :
    HasDerivAt
      (parameterizedHamiltonianActionCurve generated.hamiltonianCurve
        generated.stateCurve)
      (generated.dHamiltonian generated.psi +
        generated.hamiltonianCurve generated.lambda generated.stateDerivativeAtLambda)
      generated.lambda
  eigenvalue_state_curve_derivative_grounding :
    HasDerivAt
      (parameterizedEigenvalueStateCurve generated.energy generated.stateCurve)
      (generated.dE • generated.psi +
        generated.energy generated.lambda • generated.stateDerivativeAtLambda)
      generated.lambda
  action_eigenvalue_near_equality :
    parameterizedHamiltonianActionCurve generated.hamiltonianCurve
      generated.stateCurve =ᶠ[nhds generated.lambda]
        parameterizedEigenvalueStateCurve generated.energy generated.stateCurve
  differentiated_equation_generated :
    DifferentiatedEigenstateEquation
      (generated.hamiltonianCurve generated.lambda) generated.dHamiltonian
      generated.psi generated.stateDerivativeAtLambda
      (generated.energy generated.lambda) generated.dE
  generated_local_packet : ParameterizedHamiltonianDerivativeFrontier (H := H)
  generated_local_packet_eq :
    generated_local_packet = generated.toDerivativeFrontier
  local_expectation_value_closed :
    generated.dE = hilbertExpectation generated.dHamiltonian generated.psi
  expectation_derivative_closed :
    HasDerivAt
      (parameterizedHamiltonianExpectationCurve generated.hamiltonianCurve
        generated.stateCurve)
      (hilbertExpectation generated.dHamiltonian generated.psi) generated.lambda
  gauge_frontier :
    ParameterizedHamiltonianGaugeFrontier generated
  self_adjointness_near_parameter :
    ∀ᶠ mu in nhds generated.lambda,
      SelfAdjointOperatorWitness (generated.hamiltonianCurve mu)
  real_eigenvalue_branch_near_parameter :
    ∀ᶠ mu in nhds generated.lambda, star (generated.energy mu) = generated.energy mu
  spectral_branch :
    ParameterizedHamiltonianSpectralProjectionBranch generated
  unbounded_domain :
    ParameterizedHamiltonianUnboundedDomainFrontier generated

/-- Frontier support for time-dependent Schrödinger parameter identities: the
connection scalar `t ↦ ⟪ψ_λ(t), ∂_λ ψ_λ(t)⟫`. -/
def schrodingerParameterConnectionCurve {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (stateCurve parameterDerivativeCurve : ℝ → H) : ℝ → ℂ :=
  fun t => inner ℂ (stateCurve t) (parameterDerivativeCurve t)

/-- Frontier 0066-1: typed evidence for differentiating the time-dependent
Schrödinger equation with respect to an external parameter.  The final identity
is reached from a differentiated-TDSE balance plus explicit mixed-partial
cancellation, not from a target-shaped placeholder. -/
structure TimeDependentSchrodingerParameterIdentityFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  time : ℝ
  hbar : ℝ
  hamiltonian : HilbertBoundedOperator ℂ H
  dHamiltonian : HilbertBoundedOperator ℂ H
  stateCurve : ℝ → HilbertStateCarrier ℂ H
  parameterDerivativeCurve : ℝ → HilbertStateCarrier ℂ H
  psi : HilbertStateCarrier ℂ H
  state_at_time : stateCurve time = psi
  normalized_state : NormalizedStateWitness psi
  hamiltonian_self_adjoint : SelfAdjointOperatorWitness hamiltonian
  timeDerivativeState : HilbertStateCarrier ℂ H
  tdse_at_time :
    hamiltonian psi = (Complex.I * (hbar : ℂ)) • timeDerivativeState
  connectionDerivative : ℂ
  connection_has_deriv :
    HasDerivAt
      (schrodingerParameterConnectionCurve stateCurve parameterDerivativeCurve)
      connectionDerivative time
  mixedPartialLeft : ℂ
  mixedPartialRight : ℂ
  mixed_partials_commute : mixedPartialLeft = mixedPartialRight
  differentiated_tdse_balance :
    hilbertExpectation dHamiltonian psi =
      Complex.I * (hbar : ℂ) * connectionDerivative +
        mixedPartialLeft - mixedPartialRight

/-- Frontier support: the time-dependent Schrödinger parameter frontier proves
the source identity after the mixed-partial correction terms cancel. -/
theorem timeDependentSchrodingerParameterIdentity_of_evidence
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerParameterIdentityFrontier (H := H)) :
    hilbertExpectation F.dHamiltonian F.psi =
      Complex.I * (F.hbar : ℂ) * F.connectionDerivative := by
  simpa [F.mixed_partials_commute] using F.differentiated_tdse_balance

/-- Frontier support for TDSE product-differentiation identities: the parameter
connection scalar `λ ↦ ⟪ψ_λ(t), ∂ₜψ_λ(t)⟫`. -/
def schrodingerParameterTimeConnectionCurve {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    (stateCurve timeDerivativeCurve : ℝ → H) : ℝ → ℂ :=
  fun lambda => inner ℂ (stateCurve lambda) (timeDerivativeCurve lambda)

/-- Algebra core for the TDSE product-differentiation identity after the
Hilbert-space product rule, ket TDSE substitution, adjoint-bra TDSE
substitution, and energy-derivative substitution have been made explicit. -/
theorem tdseProductDifferentiationIdentityCore
    (c lhs dEnergy paramInner leftTerm rightTerm lambdaDt dtLambda : ℂ)
    (hDecompose : dEnergy = leftTerm + lhs + rightTerm)
    (hEnergy : dEnergy = c * paramInner)
    (hLeft : leftTerm = c * lambdaDt)
    (hRight : rightTerm = -c * dtLambda) :
    lhs = c * paramInner - c * lambdaDt + c * dtLambda := by
  rw [hEnergy, hLeft, hRight] at hDecompose
  calc
    lhs = (c * lambdaDt + lhs + (-c * dtLambda)) - c * lambdaDt + c * dtLambda := by
      ring
    _ = c * paramInner - c * lambdaDt + c * dtLambda := by
      rw [← hDecompose]

/-- Frontier 0191-1: typed evidence for differentiating the TDSE expectation
with respect to an external parameter.  The target identity is obtained from a
visible product-rule decomposition and explicit TDSE/adjoin-TDSE substitutions,
not from a target-shaped law. -/
structure TimeDependentSchrodingerProductDifferentiationFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  lambda : ℝ
  hbar : ℝ
  hamiltonian : HilbertBoundedOperator ℂ H
  dHamiltonian : HilbertBoundedOperator ℂ H
  stateCurve : ℝ → HilbertStateCarrier ℂ H
  parameterDerivativeCurve : ℝ → HilbertStateCarrier ℂ H
  timeDerivativeCurve : ℝ → HilbertStateCarrier ℂ H
  psi : HilbertStateCarrier ℂ H
  dpsi_dt : HilbertStateCarrier ℂ H
  dpsi_dlambda : HilbertStateCarrier ℂ H
  state_at_parameter : stateCurve lambda = psi
  time_derivative_at_parameter : timeDerivativeCurve lambda = dpsi_dt
  parameter_derivative_at_parameter : parameterDerivativeCurve lambda = dpsi_dlambda
  normalized_state : NormalizedStateWitness psi
  hamiltonian_self_adjoint : SelfAdjointOperatorWitness hamiltonian
  tdse_ket_at_parameter :
    hamiltonian psi = (Complex.I * (hbar : ℂ)) • dpsi_dt
  parameterEnergyDerivative : ℂ
  parameterTimeInnerDerivative : ℂ
  lambdaTimeInner : ℂ
  timeLambdaInner : ℂ
  parameter_time_inner_has_deriv :
    HasDerivAt
      (schrodingerParameterTimeConnectionCurve stateCurve timeDerivativeCurve)
      parameterTimeInnerDerivative lambda
  lambda_time_inner_grounding :
    lambdaTimeInner = inner ℂ dpsi_dlambda dpsi_dt
  time_lambda_inner_grounding :
    timeLambdaInner = inner ℂ dpsi_dt dpsi_dlambda
  product_rule_decomposition :
    parameterEnergyDerivative =
      inner ℂ dpsi_dlambda (hamiltonian psi) +
        hilbertExpectation dHamiltonian psi +
        inner ℂ psi (hamiltonian dpsi_dlambda)
  energy_derivative_tdse_substitution :
    parameterEnergyDerivative =
      Complex.I * (hbar : ℂ) * parameterTimeInnerDerivative
  ket_tdse_inner_substitution :
    inner ℂ dpsi_dlambda (hamiltonian psi) =
      Complex.I * (hbar : ℂ) * lambdaTimeInner
  adjoint_tdse_bra_substitution :
    inner ℂ psi (hamiltonian dpsi_dlambda) =
      -(Complex.I * (hbar : ℂ)) * timeLambdaInner

/-- Frontier support: the TDSE product-differentiation frontier proves the
source identity after the explicit product-rule and TDSE substitution terms are
rewritten. -/
theorem timeDependentSchrodingerProductDifferentiation_of_evidence
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TimeDependentSchrodingerProductDifferentiationFrontier (H := H)) :
    hilbertExpectation F.dHamiltonian F.psi =
      Complex.I * (F.hbar : ℂ) * F.parameterTimeInnerDerivative -
        Complex.I * (F.hbar : ℂ) * F.lambdaTimeInner +
        Complex.I * (F.hbar : ℂ) * F.timeLambdaInner := by
  exact tdseProductDifferentiationIdentityCore
    (Complex.I * (F.hbar : ℂ))
    (hilbertExpectation F.dHamiltonian F.psi)
    F.parameterEnergyDerivative
    F.parameterTimeInnerDerivative
    (inner ℂ F.dpsi_dlambda (F.hamiltonian F.psi))
    (inner ℂ F.psi (F.hamiltonian F.dpsi_dlambda))
    F.lambdaTimeInner
    F.timeLambdaInner
    F.product_rule_decomposition
    F.energy_derivative_tdse_substitution
    F.ket_tdse_inner_substitution
    F.adjoint_tdse_bra_substitution

/-- Frontier support: the recursive expansion still carries the generated
Hellmann-Feynman value proof from its bounded local core. -/
theorem parameterizedHamiltonianRecursiveExpansionFrontier_expectation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    C.generated.dE =
      hilbertExpectation C.generated.dHamiltonian C.generated.psi :=
  parameterizedHamiltonianGeneratedDerivativeFrontier_expectation C.generated

/-- Frontier support: the recursive expansion preserves the generated
expectation-curve derivative proof. -/
theorem parameterizedHamiltonianRecursiveExpansionFrontier_expectation_has_deriv
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (C : ParameterizedHamiltonianRecursiveExpansionFrontier (H := H)) :
    HasDerivAt
      (parameterizedHamiltonianExpectationCurve C.generated.hamiltonianCurve
        C.generated.stateCurve)
      (hilbertExpectation C.generated.dHamiltonian C.generated.psi)
      C.generated.lambda :=
  parameterizedHamiltonianGeneratedDerivativeFrontier_expectation_has_deriv
    C.generated

/-- Frontier 0021-9: differentiability evidence for the operator curve, state
curve, action curve, and eigenvalue-side curve that generate the local
differentiated eigenstate equation.  Product-rule obligations remain explicit
because they are exactly where more serious recursive grounding should attach. -/
structure ParameterizedHamiltonianDifferentiabilityFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  local_derivative : ParameterizedHamiltonianDerivativeFrontier (H := H)
  hamiltonian_has_deriv :
    HasDerivAt local_derivative.hamiltonianCurve
      local_derivative.dHamiltonian local_derivative.lambda
  state_has_deriv :
    HasDerivAt local_derivative.stateCurve
      local_derivative.stateDerivativeAtLambda local_derivative.lambda
  action_curve_has_deriv :
    HasDerivAt
      (parameterizedHamiltonianActionCurve local_derivative.hamiltonianCurve
        local_derivative.stateCurve)
      (local_derivative.dHamiltonian local_derivative.psi +
        local_derivative.hamiltonianCurve local_derivative.lambda
          local_derivative.stateDerivativeAtLambda)
      local_derivative.lambda
  eigenvalue_state_curve_has_deriv :
    HasDerivAt
      (parameterizedEigenvalueStateCurve local_derivative.energy
        local_derivative.stateCurve)
      (local_derivative.dE • local_derivative.psi +
        local_derivative.energy local_derivative.lambda •
          local_derivative.stateDerivativeAtLambda)
      local_derivative.lambda
  differentiated_eigen_eq_from_derivatives :
    DifferentiatedEigenstateEquation
      (local_derivative.hamiltonianCurve local_derivative.lambda)
      local_derivative.dHamiltonian local_derivative.psi
      local_derivative.stateDerivativeAtLambda
      (local_derivative.energy local_derivative.lambda) local_derivative.dE

/-- Frontier support: the differentiability packet exposes the generated
differentiated eigenstate equation. -/
theorem parameterizedHamiltonianDifferentiabilityFrontier_differentiated_eigen_eq
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (D : ParameterizedHamiltonianDifferentiabilityFrontier (H := H)) :
    DifferentiatedEigenstateEquation
      (D.local_derivative.hamiltonianCurve D.local_derivative.lambda)
      D.local_derivative.dHamiltonian D.local_derivative.psi
      D.local_derivative.stateDerivativeAtLambda
      (D.local_derivative.energy D.local_derivative.lambda) D.local_derivative.dE :=
  D.differentiated_eigen_eq_from_derivatives

/-- Frontier support: once the differentiability packet is available, it
inherits the proved Hellmann-Feynman expectation bridge. -/
theorem parameterizedHamiltonianDifferentiabilityFrontier_expectation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (D : ParameterizedHamiltonianDifferentiabilityFrontier (H := H)) :
    D.local_derivative.dE =
      hilbertExpectation D.local_derivative.dHamiltonian D.local_derivative.psi :=
  parameterizedHamiltonianDerivativeFrontier_expectation D.local_derivative

/-- Frontier 0021-10: spectral-branch evidence for treating the eigenstate
curve as a tracked branch rather than a free algebraic symbol. -/
structure ParameterizedHamiltonianSpectralBranchFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  differentiability : ParameterizedHamiltonianDifferentiabilityFrontier (H := H)
  spectralProjection : ℝ → HilbertBoundedOperator ℂ H
  projection_witness_near :
    ∀ᶠ mu in nhds differentiability.local_derivative.lambda,
      HilbertProjectionWitness (spectralProjection mu)
  projection_self_adjoint_near :
    ∀ᶠ mu in nhds differentiability.local_derivative.lambda,
      SelfAdjointOperatorWitness (spectralProjection mu)
  projection_tracks_state :
    ∀ᶠ mu in nhds differentiability.local_derivative.lambda,
      spectralProjection mu (differentiability.local_derivative.stateCurve mu) =
        differentiability.local_derivative.stateCurve mu
  simple_eigenvalue_gap_radius : ℝ
  simple_eigenvalue_gap_positive : 0 < simple_eigenvalue_gap_radius
  phase_gauge_condition :
    ParameterizedEigenstatePhaseGaugeCondition
      differentiability.local_derivative.psi
      differentiability.local_derivative.stateDerivativeAtLambda

/-- Frontier 0021-10b: local unbounded-domain evidence for a bounded
Hellmann-Feynman core.  This keeps the domain-bearing Hamiltonian branch,
derivative operator, common core, and bounded-core comparison together instead
of hiding them behind unstructured propositions. -/
structure ParameterizedHamiltonianLocalUnboundedDomainFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : ParameterizedHamiltonianDerivativeFrontier (H := H)) where
  unboundedHamiltonianCurve :
    ℝ → MathformerPhysicsLib.Foundations.UnboundedOperators.UnboundedHilbertOperator ℂ H
  unboundedDerivative :
    MathformerPhysicsLib.Foundations.UnboundedOperators.UnboundedHilbertOperator ℂ H
  commonCore : Submodule ℂ H
  common_core_dense : Dense ((commonCore : Set H))
  common_core_in_hamiltonian_domain_near :
    ∀ᶠ mu in nhds F.lambda, commonCore ≤ (unboundedHamiltonianCurve mu).domain
  common_core_in_derivative_domain :
    commonCore ≤ unboundedDerivative.domain
  state_branch_mem_domain_near :
    ∀ᶠ mu in nhds F.lambda,
      MathformerPhysicsLib.Foundations.UnboundedOperators.MemDomain
        (unboundedHamiltonianCurve mu) (F.stateCurve mu)
  state_derivative_mem_derivative_domain :
    MathformerPhysicsLib.Foundations.UnboundedOperators.MemDomain
      unboundedDerivative F.stateDerivativeAtLambda
  bounded_core_matches_hamiltonian_near :
    ∀ᶠ mu in nhds F.lambda,
      ∃ hcore : commonCore ≤ (unboundedHamiltonianCurve mu).domain,
        ∀ x : commonCore,
          MathformerPhysicsLib.Foundations.UnboundedOperators.apply
            (unboundedHamiltonianCurve mu) (x : H) (hcore x.property) =
              F.hamiltonianCurve mu (x : H)
  bounded_core_matches_derivative :
    ∀ x : commonCore,
      MathformerPhysicsLib.Foundations.UnboundedOperators.apply
        unboundedDerivative (x : H) (common_core_in_derivative_domain x.property) =
          F.dHamiltonian (x : H)

/-- Frontier support: the spectral branch still carries the local expectation
bridge through the differentiability layer. -/
theorem parameterizedHamiltonianSpectralBranchFrontier_expectation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (S : ParameterizedHamiltonianSpectralBranchFrontier (H := H)) :
    S.differentiability.local_derivative.dE =
      hilbertExpectation S.differentiability.local_derivative.dHamiltonian
        S.differentiability.local_derivative.psi :=
  parameterizedHamiltonianDifferentiabilityFrontier_expectation S.differentiability

/-- Frontier 0021-11: fully grounded recursive packet for parameterized
Hamiltonians.  It names the remaining unbounded-operator and common-domain
obligations while preserving the bounded local theorem as checked evidence. -/
structure ParameterizedHamiltonianFullyGroundedRecursiveFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  spectral_branch : ParameterizedHamiltonianSpectralBranchFrontier (H := H)
  unbounded_domain :
    ParameterizedHamiltonianLocalUnboundedDomainFrontier
      spectral_branch.differentiability.local_derivative
  expectation_derivative_ready :
    spectral_branch.differentiability.local_derivative.dE =
      hilbertExpectation
        spectral_branch.differentiability.local_derivative.dHamiltonian
        spectral_branch.differentiability.local_derivative.psi

/-- Frontier support: the fully grounded recursive packet exposes the checked
Hellmann-Feynman expectation value at its local bounded core. -/
theorem parameterizedHamiltonianFullyGroundedRecursiveFrontier_expectation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : ParameterizedHamiltonianFullyGroundedRecursiveFrontier (H := H)) :
    F.spectral_branch.differentiability.local_derivative.dE =
      hilbertExpectation
        F.spectral_branch.differentiability.local_derivative.dHamiltonian
        F.spectral_branch.differentiability.local_derivative.psi :=
  F.expectation_derivative_ready

/-- Frontier 0021-6: recursive target packet for extending the
Hellmann-Feynman bridge beyond the local bounded-operator case. -/
structure ParameterizedHamiltonianRecursiveFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  local_derivative : ParameterizedHamiltonianDerivativeFrontier (H := H)
  operator_curve_has_deriv :
    HasDerivAt local_derivative.hamiltonianCurve
      local_derivative.dHamiltonian local_derivative.lambda
  state_curve_has_deriv :
    HasDerivAt local_derivative.stateCurve
      local_derivative.stateDerivativeAtLambda local_derivative.lambda
  spectral_branch : ParameterizedHamiltonianSpectralBranchFrontier (H := H)
  spectral_branch_local_derivative_eq :
    spectral_branch.differentiability.local_derivative = local_derivative
  unbounded_domain :
    ParameterizedHamiltonianLocalUnboundedDomainFrontier local_derivative
  local_derivative_ready :
    local_derivative.dE =
      hilbertExpectation local_derivative.dHamiltonian local_derivative.psi

/-- Physics role: a unitary evolution candidate preserves the Hilbert inner product. -/
structure UnitaryOperatorWitness {𝕜 H : Type*} [RCLike 𝕜] [NormedAddCommGroup H]
    [InnerProductSpace 𝕜 H] (U : HilbertBoundedOperator 𝕜 H) : Prop where
  preserves_inner : ∀ x y : H, inner 𝕜 (U x) (U y) = inner 𝕜 x y

/-- Frontier 0015-11: a two-level Rabi frame keeps the excited and ground
states, normalization facts, and orthogonality facts together as a reusable
Hilbert-space object. -/
structure TwoLevelRabiFrame (H : Type*) [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] [CompleteSpace H] where
  excited : HilbertStateCarrier ℂ H
  ground : HilbertStateCarrier ℂ H
  excited_normalized : NormalizedStateWitness excited
  ground_normalized : NormalizedStateWitness ground
  ground_excited_orthogonal : HilbertOrthogonalityWitness (𝕜 := ℂ) ground excited
  excited_ground_orthogonal : HilbertOrthogonalityWitness (𝕜 := ℂ) excited ground

/-- Frontier 0015-12: the Rabi state generated from a two-level frame. -/
noncomputable def twoLevelRabiStateFromFrame {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TwoLevelRabiFrame H) (Omega t : ℝ) : HilbertStateCarrier ℂ H :=
  (Real.cos (Omega * t / 2) : ℂ) • F.excited +
    VacuumRabiAmplitude Omega t • F.ground

/-- Frontier support: the frame-generated Rabi state is exactly the existing
two-level Rabi expansion surface. -/
theorem twoLevelRabiStateFromFrame_expansion {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TwoLevelRabiFrame H) (Omega t : ℝ) :
    TwoLevelRabiStateExpansion
      (twoLevelRabiStateFromFrame F Omega t) F.excited F.ground Omega t := by
  rfl

/-- Frontier support: a frame-generated Rabi state has the expected vacuum-Rabi
transition amplitude. -/
theorem transitionAmplitude_from_twoLevelRabiFrameState {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TwoLevelRabiFrame H) (Omega t : ℝ) :
    transitionAmplitude ℂ F.ground (twoLevelRabiStateFromFrame F Omega t) =
      VacuumRabiAmplitude Omega t :=
  transitionAmplitude_from_twoLevelRabiStateExpansion
    (twoLevelRabiStateFromFrame F Omega t) F.ground F.excited Omega t
    F.ground_normalized F.ground_excited_orthogonal
    (twoLevelRabiStateFromFrame_expansion F Omega t)

/-- Frontier 0015-13: Born probability induced by a projection-like bounded
operator. -/
noncomputable def projectionBornProbability {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] (P : HilbertBoundedOperator ℂ H) (psi : H) : ℝ :=
  ‖P psi‖ ^ 2

/-- Frontier 0015-14: a measurement projector for the ground-state channel,
with its Born probability connected to the Dirac transition amplitude. -/
structure TwoLevelRabiGroundMeasurementFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TwoLevelRabiFrame H) where
  groundProjector : HilbertBoundedOperator ℂ H
  projector_witness : HilbertProjectionWitness groundProjector
  fixes_ground : groundProjector F.ground = F.ground
  kills_excited : groundProjector F.excited = 0
  projection_probability_eq_transition_probability :
    ∀ psi : H,
      projectionBornProbability groundProjector psi =
        probabilityFromAmplitude (transitionAmplitude ℂ F.ground psi)

/-- Frontier 0015-15: unitary two-level dynamics whose excited initial state
evolves into the Rabi state generated by the frame. -/
structure TwoLevelRabiDynamicsFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TwoLevelRabiFrame H) (Omega : ℝ) where
  hamiltonian : HilbertBoundedOperator ℂ H
  hamiltonian_self_adjoint : SelfAdjointOperatorWitness hamiltonian
  evolution : ℝ → HilbertBoundedOperator ℂ H
  unitary_evolution : ∀ t : ℝ, UnitaryOperatorWitness (evolution t)
  initial_state : HilbertStateCarrier ℂ H
  initial_state_eq_excited : initial_state = F.excited
  evolves_excited_to_rabi_state :
    ∀ t : ℝ, evolution t F.excited = twoLevelRabiStateFromFrame F Omega t

/-- Frontier support: the projection Born probability from the dynamical Rabi
state is the expected `sin²(Ωt/2)` curve. -/
theorem projectionBornProbability_from_twoLevelRabiDynamics {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    {F : TwoLevelRabiFrame H} {Omega : ℝ}
    (D : TwoLevelRabiDynamicsFrontier F Omega)
    (M : TwoLevelRabiGroundMeasurementFrontier F) (t : ℝ) :
    projectionBornProbability M.groundProjector (D.evolution t F.excited) =
      Real.sin (Omega * t / 2) ^ 2 := by
  rw [D.evolves_excited_to_rabi_state t]
  rw [M.projection_probability_eq_transition_probability]
  exact bornProbabilityFromVacuumRabiTransitionAmplitude
    (transitionAmplitude_from_twoLevelRabiFrameState F Omega t)

/-- Frontier 0015-16: parameter calibration for the resonant Rabi model.
Detuning, coupling, and effective frequency are kept explicit so generated
physics assumptions do not silently collapse into the final `Ω`. -/
structure TwoLevelRabiParameterCalibrationFrontier (Omega : ℝ) : Type where
  coupling_frequency : ℝ
  detuning : ℝ
  effective_frequency : ℝ
  resonant_condition : detuning = 0
  effective_frequency_eq_coupling_on_resonance :
    detuning = 0 → effective_frequency = coupling_frequency
  omega_eq_effective_frequency : Omega = effective_frequency

/-- Frontier 0015-17: recursive expansion target for the open-system or
imperfect-measurement generalization of the two-level Rabi probability. -/
structure TwoLevelRabiOpenSystemFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (F : TwoLevelRabiFrame H) where
  density_state : Type
  pure_state_embedding : H → density_state
  channel : ℝ → density_state → density_state
  measurement_probability : density_state → ℝ
  pure_state_probability_agrees :
    ∀ psi : H,
      measurement_probability (pure_state_embedding psi) =
        probabilityFromAmplitude (transitionAmplitude ℂ F.ground psi)

/-- Frontier 0015-18: complete recursive handoff for moving from the scalar
vacuum-Rabi Born rule to grounded dynamics, measurement, calibration, and
open-system expansion. -/
structure VacuumRabiRecursiveFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (Omega : ℝ) where
  frame : TwoLevelRabiFrame H
  dynamics : TwoLevelRabiDynamicsFrontier frame Omega
  ground_measurement : TwoLevelRabiGroundMeasurementFrontier frame
  parameter_calibration : TwoLevelRabiParameterCalibrationFrontier Omega
  open_system_frontier : TwoLevelRabiOpenSystemFrontier frame
  probability_curve : ℝ → ℝ
  probability_curve_eq_projection :
    ∀ t : ℝ,
      probability_curve t =
        projectionBornProbability ground_measurement.groundProjector
          (dynamics.evolution t frame.excited)

/-- Frontier support: the full recursive Rabi packet yields the resonant
vacuum-Rabi probability curve. -/
theorem vacuumRabiRecursiveFrontier_probability_curve {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    {Omega : ℝ} (R : VacuumRabiRecursiveFrontier (H := H) Omega) (t : ℝ) :
    R.probability_curve t = Real.sin (Omega * t / 2) ^ 2 := by
  rw [R.probability_curve_eq_projection t]
  exact projectionBornProbability_from_twoLevelRabiDynamics
    R.dynamics R.ground_measurement t

/-- Physics role: Hilbert-Schmidt support is kept as an explicit basis-relative
summability witness until promoted through a stronger Mathlib-specific API. -/
structure HilbertSchmidtWithBasisWitness {ι 𝕜 H : Type*} [RCLike 𝕜]
    [NormedAddCommGroup H] [InnerProductSpace 𝕜 H] [CompleteSpace H]
    (b : HilbertBasisSurface ι 𝕜 H) (T : HilbertBoundedOperator 𝕜 H) : Prop where
  square_summable_images : Summable fun i : ι => ‖T (b i)‖ ^ 2

/-- Mathlib grounding: a position wavefunction is a function into complex
amplitudes until a stronger measure-theoretic API is promoted. -/
abbrev PositionWavefunction (X : Type*) := X → ℂ

/-- Physics role: the Born-rule position-expectation integrand `x |ψ x|²`. -/
noncomputable def positionExpectationIntegrand {X : Type*} (xValue : X → ℝ)
    (psi : PositionWavefunction X) (x : X) : ℝ :=
  xValue x * ‖psi x‖ ^ 2

/-- Mathlib grounding: the position-expectation integrand unfolds to the
Born-rule density weighted by the position value. -/
theorem positionExpectationIntegrand_apply {X : Type*} (xValue : X → ℝ)
    (psi : PositionWavefunction X) (x : X) :
    positionExpectationIntegrand xValue psi x = xValue x * ‖psi x‖ ^ 2 := rfl

/-- Physics role: a position-basis resolution identity is represented by an
explicit measure kernel surface before stronger delta-kernel APIs are promoted. -/
structure PositionResolutionIdentityMeasureKernel (X : Type*) [MeasurableSpace X]
    (μ : MeasureTheory.Measure X) : Prop where
  measure_space_grounded : True

/-- Physics role: the Born-rule position expectation as a Mathlib measure
integral. -/
noncomputable def positionExpectationIntegral {X : Type*} [MeasurableSpace X]
    (μ : MeasureTheory.Measure X) (xValue : X → ℝ) (psi : PositionWavefunction X) : ℝ :=
  ∫ x, positionExpectationIntegrand xValue psi x ∂μ

/-- Mathlib grounding: the position expectation integral is definitionally the
integral of the Born-rule position integrand. -/
theorem positionExpectationIntegral_apply {X : Type*} [MeasurableSpace X]
    (μ : MeasureTheory.Measure X) (xValue : X → ℝ) (psi : PositionWavefunction X) :
    positionExpectationIntegral μ xValue psi =
      ∫ x, positionExpectationIntegrand xValue psi x ∂μ := rfl

/-- Frontier 0052-1: the Born density associated with a position wavefunction. -/
noncomputable def positionBornDensity {X : Type*} (psi : PositionWavefunction X)
    (x : X) : ℝ :=
  ‖psi x‖ ^ 2

/-- Frontier support: the position expectation integrand is position value
times the Born density. -/
theorem positionExpectationIntegrand_eq_value_mul_density {X : Type*}
    (xValue : X → ℝ) (psi : PositionWavefunction X) (x : X) :
    positionExpectationIntegrand xValue psi x = xValue x * positionBornDensity psi x :=
  rfl

/-- Physics role: a position-space Born density is integrable with respect to
the selected Mathlib measure. -/
def PositionBornDensityIntegrable {X : Type*} [MeasurableSpace X]
    (μ : MeasureTheory.Measure X) (psi : PositionWavefunction X) : Prop :=
  MeasureTheory.Integrable (fun x => positionBornDensity psi x) μ

/-- Physics role: a normalized position wavefunction has total Born
probability one. -/
noncomputable def PositionBornProbabilityNormalization {X : Type*}
    [MeasurableSpace X] (μ : MeasureTheory.Measure X)
    (psi : PositionWavefunction X) : Prop :=
  ∫ x, positionBornDensity psi x ∂μ = 1

/-- Physics role: the position-expectation integrand is integrable with respect
to the selected Mathlib measure. -/
def PositionExpectationIntegrable {X : Type*} [MeasurableSpace X]
    (μ : MeasureTheory.Measure X) (xValue : X → ℝ)
    (psi : PositionWavefunction X) : Prop :=
  MeasureTheory.Integrable (fun x => positionExpectationIntegrand xValue psi x) μ

/-- Frontier 0052-2: a measured position space keeps the Mathlib measure,
coordinate map, wavefunction, and resolution-of-identity evidence together. -/
structure PositionMeasurementSpaceFrontier (X : Type*) [MeasurableSpace X] where
  μ : MeasureTheory.Measure X
  xValue : X → ℝ
  psi : PositionWavefunction X
  resolution_of_identity : PositionResolutionIdentityMeasureKernel X μ
  born_density : X → ℝ
  born_density_eq : ∀ x : X, born_density x = positionBornDensity psi x
  born_density_integrable : PositionBornDensityIntegrable μ psi
  normalized_probability : PositionBornProbabilityNormalization μ psi
  integrable_position_observable : PositionExpectationIntegrable μ xValue psi

/-- Frontier 0052-3: the expected position value generated by a measurement
space packet. -/
noncomputable def positionExpectationFromMeasurementSpace {X : Type*}
    [MeasurableSpace X] (S : PositionMeasurementSpaceFrontier X) : ℝ :=
  positionExpectationIntegral S.μ S.xValue S.psi

/-- Frontier support: the packet expectation unfolds to the Mathlib integral
of the Born-rule position integrand. -/
theorem positionExpectationFromMeasurementSpace_apply {X : Type*}
    [MeasurableSpace X] (S : PositionMeasurementSpaceFrontier X) :
    positionExpectationFromMeasurementSpace S =
      ∫ x, positionExpectationIntegrand S.xValue S.psi x ∂S.μ :=
  positionExpectationIntegral_apply S.μ S.xValue S.psi

/-- Frontier 0052-4a: spectral-measure grounding for a position measurement
space.  It keeps the position-basis resolution kernel, coordinate measurability,
and Born-density identification explicit. -/
structure PositionSpectralMeasureGrounding {X : Type*} [MeasurableSpace X]
    (S : PositionMeasurementSpaceFrontier X) : Prop where
  resolution_kernel : PositionResolutionIdentityMeasureKernel X S.μ
  coordinate_measurable : Measurable S.xValue
  born_density_grounded : ∀ x : X, S.born_density x = positionBornDensity S.psi x

/-- Frontier 0052-4b: `L²`-style wavefunction grounding for the measured
position packet.  The current surface is measure-theoretic and can later be
promoted to a stronger `Lp` carrier without losing the integral obligations. -/
structure PositionL2WavefunctionGrounding {X : Type*} [MeasurableSpace X]
    (S : PositionMeasurementSpaceFrontier X) : Prop where
  born_density_integrable : PositionBornDensityIntegrable S.μ S.psi
  normalized_probability : PositionBornProbabilityNormalization S.μ S.psi

/-- Frontier 0052-4c: integrability grounding for the position expectation
value generated by the measured position packet. -/
structure PositionExpectationIntegrabilityGrounding {X : Type*}
    [MeasurableSpace X] (S : PositionMeasurementSpaceFrontier X) : Prop where
  integrable_position_observable : PositionExpectationIntegrable S.μ S.xValue S.psi
  expectation_integral_surface :
    positionExpectationFromMeasurementSpace S =
      positionExpectationIntegral S.μ S.xValue S.psi

/-- Frontier 0052-4: recursive target packet for upgrading the position
expectation bridge toward spectral measures and `L²` wavefunctions. -/
structure PositionExpectationRecursiveFrontier (X : Type*) [MeasurableSpace X] where
  measurement_space : PositionMeasurementSpaceFrontier X
  spectral_measure_grounding : PositionSpectralMeasureGrounding measurement_space
  l2_wavefunction_grounding : PositionL2WavefunctionGrounding measurement_space
  integrability_grounding : PositionExpectationIntegrabilityGrounding measurement_space
  expectation_value :
    positionExpectationFromMeasurementSpace measurement_space =
      positionExpectationIntegral measurement_space.μ
        measurement_space.xValue measurement_space.psi

/-- Frontier 0074-1: a Dirac braket pair with both orientations kept together. -/
structure DiracBraketPair {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    [CompleteSpace H] where
  left : HilbertStateCarrier ℂ H
  right : HilbertStateCarrier ℂ H
  forward : ℂ
  reverse : ℂ
  forward_eq_transition : forward = transitionAmplitude ℂ left right
  reverse_eq_transition : reverse = transitionAmplitude ℂ right left

/-- Frontier support: the reversed braket is the conjugate of the forward
braket by Mathlib inner-product conjugate symmetry. -/
theorem diracBraketPair_conjugate_symmetry {H : Type*} [NormedAddCommGroup H]
    [InnerProductSpace ℂ H] [CompleteSpace H] (B : DiracBraketPair (H := H)) :
    star B.forward = B.reverse := by
  rw [B.forward_eq_transition, B.reverse_eq_transition]
  exact transitionAmplitude_conjugate_symmetry B.left B.right

/-- Frontier 0074-2: the imaginary quotient attached to a braket pair. -/
noncomputable def diracBraketPairImaginaryQuotient {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (B : DiracBraketPair (H := H)) : ℂ :=
  diracImaginaryQuotient B.forward B.reverse

/-- Frontier support: the braket-pair quotient equals the imaginary part of
the forward amplitude. -/
theorem diracBraketPairImaginaryQuotient_eq_im {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (B : DiracBraketPair (H := H)) :
    diracBraketPairImaginaryQuotient B = (Complex.im B.forward : ℂ) := by
  exact diracImaginaryQuotient_eq_im_of_conjugate
    (diracBraketPair_conjugate_symmetry B)

/-- Frontier support: the squared quotient identity follows from the
braket-pair conjugate symmetry packet. -/
theorem diracBraketPairImaginaryQuotient_sq_eq_im_sq {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (B : DiracBraketPair (H := H)) :
    (diracBraketPairImaginaryQuotient B) ^ 2 = (Complex.im B.forward : ℂ) ^ 2 :=
  congrArg (fun z : ℂ => z ^ 2) (diracBraketPairImaginaryQuotient_eq_im B)

/-- Frontier 0074-3a: a skew-adjoint generator witness for a Dirac braket
pair.  It keeps the generator as a Mathlib continuous linear map and records
the skew-adjoint expectation identity as an inner-product statement. -/
structure DiracSkewAdjointGeneratorGrounding {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (B : DiracBraketPair (H := H)) where
  generator : HilbertBoundedOperator ℂ H
  generator_skew_adjoint :
    ∀ x y : H, inner ℂ (generator x) y = -inner ℂ x (generator y)
  forward_as_generator_matrix_element :
    B.forward = inner ℂ B.left (generator B.right)
  reverse_as_reversed_generator_matrix_element :
    B.reverse = inner ℂ B.right (generator B.left)

/-- Frontier 0074-3b: commutator-expectation grounding for a Dirac braket
pair.  The quotient is connected to a concrete commutator expectation scalar
and a canonical `iℏ` value before any square identity is used downstream. -/
structure DiracCommutatorExpectationGrounding {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (B : DiracBraketPair (H := H)) where
  commutator_expectation : ℂ
  hbar : ℝ
  braket_difference_eq_commutator :
    B.forward - B.reverse = commutator_expectation
  commutator_expectation_eq_canonical :
    commutator_expectation = Complex.I * (hbar : ℂ)
  quotient_from_commutator :
    diracBraketPairImaginaryQuotient B = (hbar : ℂ) / 2
  imaginary_part_matches_canonical :
    (Complex.im B.forward : ℂ) = (hbar : ℂ) / 2

/-- Frontier 0074-3: recursive target packet for connecting braket-pair
imaginary quotients to skew-adjoint generators and commutator expectations. -/
structure DiracImaginaryProjectionRecursiveFrontier {H : Type*}
    [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  braket_pair : DiracBraketPair (H := H)
  conjugate_symmetry :
    star braket_pair.forward = braket_pair.reverse
  quotient_matches_imaginary_part :
    diracBraketPairImaginaryQuotient braket_pair =
      (Complex.im braket_pair.forward : ℂ)
  skew_adjoint_generator_grounding :
    DiracSkewAdjointGeneratorGrounding braket_pair
  commutator_expectation_grounding :
    DiracCommutatorExpectationGrounding braket_pair

end HilbertSpace
end Foundations
end MathformerPhysicsLib
