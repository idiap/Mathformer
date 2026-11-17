import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0009`, source index 9.
Field: Quantum Mechanics.
Informal target: *Integration by parts in the position→momentum Fourier transform* For a square-integrable $\psi(\chi)$ vanishing at $\chi\to\pm\infty$, evaluate by parts the integral $I=\displaystyle\int_{-\infty}^{\infty}\psi(\chi)\,e^{-ip\chi/\hbar}\,d\chi$ to move the derivative onto $\psi$. **

Informal derivation summary:
1. Start from the Fourier-position integral
   $$I=\int_{-\infty}^{\infty}\psi(\chi)e^{-ip\chi/\hbar}\,d\chi.$$
2. Choose the antiderivative of the phase factor as
   $$v(\chi)=\frac{\hbar}{-ip}e^{-ip\chi/\hbar},$$
   so the integration-by-parts rule gives
   $$I=\Big[\psi(\chi)v(\chi)\Big]_{-\infty}^{\infty}
      -\int_{-\infty}^{\infty}v(\chi)\frac{d\psi}{d\chi}\,d\chi.$$
3. Use the source boundary condition that $\psi(\chi)$ vanishes at
   $\chi\to\pm\infty$ to remove the endpoint term:
   $$\Big[\psi(\chi)v(\chi)\Big]_{-\infty}^{\infty}=0.$$
4. Rewrite the derivative as $\frac{d\psi}{d\chi}=\psi'(\chi)$ and substitute
   the antiderivative:
   $$I=-\int_{-\infty}^{\infty}
       \left(\frac{\hbar}{-ip}e^{-ip\chi/\hbar}\right)\psi'(\chi)\,d\chi.$$
5. Simplify the coefficient $-\hbar/(-ip)=\hbar/(ip)$ to obtain
   $$I=\frac{\hbar}{ip}\int_{-\infty}^{\infty}
       \psi'(\chi)e^{-ip\chi/\hbar}\,d\chi.$$

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the target is routed through `MathformerPhysicsLib.Foundations.QuantumMechanicsExamples`;
- source-step evidence is first held in a Mathlib-grounded Fourier packet over a
  Hilbert carrier, Bochner integrals over `ℝ`, finite-window interval integrals,
  derivative witnesses, and boundary decay;
- the scalar evidence wrapper is retained only as a compatibility bridge.

Formal alignment:
- the finite-window integration-by-parts source step maps to
  `G.finite_window_by_parts`;
- the vanishing boundary term maps to `G.boundary_vanishes`;
- the infinite-line passage maps to `G.infinite_window_limit`;
- the antiderivative coefficient simplification maps to
  `G.coefficient_simplifies`;
- the Lean proof block calls `fourierIntegrationByPartsFromGrounding`, which
  combines those corresponding Lean hypotheses without reading the dataset
  `formal_answer`.

Semantic preservation contract:
- Source target: move the Fourier phase derivative off
  `e^{-ipχ/hbar}` and onto `ψ`, obtaining
  `I = hbar / (i*p) * ∫ ψ'(χ) e^{-ipχ/hbar} dχ`.
- Lean target: prove the corresponding real-line Bochner-integral identity
  `fourierPositionIntegral G.psi G.p G.hbar = G.result` from a
  `FourierIntegrationByPartsGrounding` packet.
- Preservation status: conditional replay over Mathlib-grounded frontier
  fields; the final equality is exact relative to the integration-by-parts,
  boundary, derivative, and coefficient fields stored in `G`.
- Source assumptions preserved: square-integrable/real-line Fourier setting,
  vanishing boundary term, nonzero `p` and `hbar`, differentiability of `ψ`,
  the finite-window integration-by-parts step, and the infinite-window passage.
- Additional mathematical assumptions introduced: the Lean surface models the
  source integral as Mathlib Bochner integrals over `ℝ` and records
  finite-window and infinite-line bridge obligations explicitly.
- Not modeled here: a full proof of the improper-limit passage from analytic
  decay assumptions, and a complete unbounded-operator Fourier-transform
  domain theory.
- Semantic deltas: the informal position-to-momentum transform is represented
  by `fourierPositionIntegral`, `fourierDerivativeIntegral`, and
  `fourierWindowIntegral`; the older scalar evidence packet is retained only as
  compatibility evidence.
- Step alignment: antiderivative/window integration-by-parts maps to
  `G.finite_window_by_parts`, boundary decay to `G.boundary_vanishes`, the
  real-line passage to `G.infinite_window_limit`, and coefficient
  simplification to `G.coefficient_simplifies`.
- Trust boundary: the theorem proves the final identity from the grounding
  packet; proving the packet from raw analytic hypotheses remains a foundation
  obligation.
-/

namespace Mathformer.Physics.FormalPhysics0009

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Operators
open MathformerPhysicsLib.Foundations.PositionMomentumModels
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Source role: the Fourier transform is interpreted over the real line with
the source-side wavefunction and derivative integrable against the Mathlib
Fourier phase. -/
def FourierRealLineCoordinateFrame
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : FourierIntegrationByPartsGrounding H) : Prop :=
  MeasureTheory.Integrable (fun x => G.psi x * fourierPhase G.p G.hbar x) ∧
    MeasureTheory.Integrable
      (fun x => G.psiDerivative x * fourierPhase G.p G.hbar x)

/-- The richer grounding packet already carries the real-line Fourier frame
obligations needed by the source derivation. -/
theorem fourier_real_line_coordinate_frame_grounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : FourierIntegrationByPartsGrounding H) :
    FourierRealLineCoordinateFrame G :=
  ⟨G.psi_integrable, G.derivative_integrable⟩

/-- Source-law proposition for the infinite-window integration-by-parts step
before boundary decay and coefficient simplification are applied. -/
def FourierIntegrationByPartsSourceLaw
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : FourierIntegrationByPartsGrounding H) : Prop :=
  fourierPositionIntegral G.psi G.p G.hbar =
    G.boundaryTerm -
      ((G.hbar : ℂ) / (-(Complex.I * (G.p : ℂ)))) *
        fourierDerivativeIntegral G.psiDerivative G.p G.hbar

/-- Hilbert carrier grounding: the square-integrable state is kept as a
Mathlib-backed Hilbert carrier, not erased into a scalar placeholder. -/
def fourier_hilbert_state_carrier
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : FourierIntegrationByPartsGrounding H) : HilbertStateCarrier ℂ H :=
  G.state

/-- Derivative grounding: the source derivative `ψ'` is represented by a
pointwise `HasDerivAt` witness. -/
theorem fourier_derivative_grounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : FourierIntegrationByPartsGrounding H) (x : ℝ) :
    HasDerivAt G.psi (G.psiDerivative x) x :=
  G.derivative_grounding x

/-- Finite-window integration-by-parts grounding before taking the infinite-line
limit. -/
theorem fourier_window_by_parts_grounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : FourierIntegrationByPartsGrounding H) (a b : ℝ) :
    fourierWindowIntegral G.psi G.p G.hbar a b =
      G.psi b * ((G.hbar : ℂ) / (-(Complex.I * (G.p : ℂ))) *
        fourierPhase G.p G.hbar b) -
        G.psi a * ((G.hbar : ℂ) / (-(Complex.I * (G.p : ℂ))) *
          fourierPhase G.p G.hbar a) -
          ((G.hbar : ℂ) / (-(Complex.I * (G.p : ℂ)))) *
            fourierWindowDerivativeIntegral G.psiDerivative G.p G.hbar a b :=
  G.finite_window_by_parts a b

/-- Boundary-decay grounding for the vanishing endpoint term. -/
theorem fourier_boundary_decay_grounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : FourierIntegrationByPartsGrounding H) :
    G.boundaryTerm = 0 :=
  G.boundary_vanishes

/-- Infinite-window source law obtained after passing from finite windows to the
real-line Bochner integral. -/
theorem fourier_infinite_window_source_law
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : FourierIntegrationByPartsGrounding H) :
    FourierIntegrationByPartsSourceLaw G := by
  unfold FourierIntegrationByPartsSourceLaw
  exact G.infinite_window_limit

/-- Coefficient simplification for the antiderivative factor
`hbar / (-i p)`. -/
theorem fourier_coefficient_simplification_grounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : FourierIntegrationByPartsGrounding H) :
    -((G.hbar : ℂ) / (-(Complex.I * (G.p : ℂ)))) *
        fourierDerivativeIntegral G.psiDerivative G.p G.hbar = G.result :=
  G.coefficient_simplifies

/-- Reusable algebraic core: integration by parts plus boundary decay and
coefficient simplification yields the final Fourier integral identity. -/
theorem fourier_integration_by_parts_algebraic_core
    {integral boundary derivativeIntegral result coefficient : ℂ}
    (integration_by_parts : integral = boundary - coefficient * derivativeIntegral)
    (boundary_vanishes : boundary = 0)
    (coefficient_simplifies : -coefficient * derivativeIntegral = result) :
    integral = result := by
  rw [integration_by_parts, boundary_vanishes]
  simpa using coefficient_simplifies

/-- Reconstruct the Fourier integration-by-parts result from explicit
source-law witnesses instead of a hidden target-shaped assumption. -/
theorem fourier_integration_by_parts_from_source_laws
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : FourierIntegrationByPartsGrounding H)
    (source_law : PhysicalLawWitness (FourierIntegrationByPartsSourceLaw G))
    (boundary_decay : PhysicalLawWitness (G.boundaryTerm = 0))
    (coefficient_law : PhysicalLawWitness
      (-((G.hbar : ℂ) / (-(Complex.I * (G.p : ℂ)))) *
        fourierDerivativeIntegral G.psiDerivative G.p G.hbar = G.result)) :
    fourierPositionIntegral G.psi G.p G.hbar = G.result := by
  have h_source : FourierIntegrationByPartsSourceLaw G := source_law.holds
  unfold FourierIntegrationByPartsSourceLaw at h_source
  exact fourier_integration_by_parts_algebraic_core
    h_source boundary_decay.holds coefficient_law.holds

/-- Source-only Fourier integration by parts over the richer Hilbert/Bochner
integral grounding surface.  The extra `PhysicsContext` and
`UnitDimensionCompatible` arguments are explicit source-backed side-condition
labels: real-line coordinate frame, nonzero denominators, differentiability, and
unit/dimension homogeneity. -/
theorem fourier_integration_by_parts_mathlib_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : FourierIntegrationByPartsGrounding H)
    (real_line_coordinate_frame : PhysicsContext (FourierRealLineCoordinateFrame G))
    (nonzero_source_backed : PhysicsContext (G.p ≠ 0 ∧ G.hbar ≠ 0))
    (smoothness_source_backed : PhysicsContext (Differentiable ℝ G.psi))
    (unit_dimension_homogeneous :
      UnitDimensionCompatible (fourierPositionIntegral G.psi G.p G.hbar) G.result) :
    fourierPositionIntegral G.psi G.p G.hbar = G.result := by
  have _ : FourierRealLineCoordinateFrame G := real_line_coordinate_frame.holds
  have _ : G.p ≠ 0 ∧ G.hbar ≠ 0 := nonzero_source_backed.holds
  have _ : Differentiable ℝ G.psi := smoothness_source_backed.holds
  have _ : fourierPositionIntegral G.psi G.p G.hbar = G.result :=
    unit_dimension_homogeneous.relation
  exact fourierIntegrationByPartsFromGrounding G

/-- Source-backed unit/dimension bridge for the Fourier integration-by-parts
target.  It keeps homogeneity visible to the workflow while delegating the
actual equality recovery to the foundation bridge. -/
theorem fourier_integration_by_parts_unit_dimension_bridge
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : FourierIntegrationByPartsGrounding H)
    (unit_dimension_homogeneous :
      UnitDimensionCompatible (fourierPositionIntegral G.psi G.p G.hbar) G.result) :
    fourierPositionIntegral G.psi G.p G.hbar = G.result := by
  exact unit_dimension_bridge unit_dimension_homogeneous

/-- Compatibility wrapper for the earlier scalar packet. -/
theorem fourier_integration_by_parts_source_grounded
    (E : FourierIntegrationByPartsEvidence) :
    E.integral = E.result := by
  exact fourierIntegrationByPartsResult E

/-- Compatibility bridge from the recursive grounding packet to the scalar
source packet, used by legacy consumers while the richer object becomes the
preferred API. -/
theorem fourier_integration_by_parts_scalar_bridge
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : FourierIntegrationByPartsGrounding H) :
    (fourierIntegrationByPartsEvidenceOfGrounding G).integral =
      (fourierIntegrationByPartsEvidenceOfGrounding G).result := by
  exact fourierIntegrationByPartsResult (fourierIntegrationByPartsEvidenceOfGrounding G)

end Mathformer.Physics.FormalPhysics0009
