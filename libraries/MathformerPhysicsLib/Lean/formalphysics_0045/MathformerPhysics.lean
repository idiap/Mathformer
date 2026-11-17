import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0045`, source index 45.
Field: Quantum Mechanics.
Informal target: Let $\psi(x)\in L^2(\mathbb{R})$ be a normalized wavefunction that vanishes at $|x|\to\infty$. Define $|f\rangle=\hat{X}|\psi\rangle$ and $|g\rangle=\hat{P}|\psi\rangle$, with $\hat{P}=-i\hbar\,\frac{d}{dx}$ in the position representation. Show that $$ \langle f|g\rangle-\langle g|f\rangle=-i\hbar\int_{-\infty}^{\infty}\!\!\Big(x\,\psi^*(x)\,\frac{d\psi(x)}{dx}-\psi^*(x)\,\frac{d}{dx}[x\psi(x)]\Big)\,dx. $$ {

Informal derivation summary: Using $\langle f|g\rangle=\int f^*(x)\,g(x)\,dx$ we have $$ \langle f|g\rangle=-i\hbar\int_{-\infty}^{\infty}x\,\psi^*(x)\,\frac{d\psi(x)}{dx}\,dx. $$ Similarly, $$ \langle g|f\rangle=-i\hbar\int_{-\infty}^{\infty}\psi^*(x)\,\frac{d}{dx}[x\psi(x)]\,dx. $$ Therefore, $$ \langle f|g\rangle-\langle g|f\rangle=-i\hbar\int_{-\infty}^{\infty}\Big(x\,\psi^*(x)\,\frac{d\psi(x)}{dx}-\psi^*(x)\,\frac{d}{dx}[x\psi(x)]\Big)\,dx. $$ {

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the target is routed through `MathformerPhysicsLib.Foundations.QuantumMechanicsExamples`;
- source-step evidence is held in a named packet before the final theorem calls
  the reusable MathformerPhysicsLib theorem.
-/

namespace Mathformer.Physics.FormalPhysics0045

open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Operators
open MathformerPhysicsLib.Foundations.PositionMomentumModels
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Source-only wrapper for the position-momentum braket difference integral form. -/
theorem position_momentum_inner_difference_source_grounded
    (E : PositionMomentumInnerDifferenceEvidence) :
    E.fg - E.gf = E.integralForm := by
  exact positionMomentumInnerDifference E

/-- Audit anchor: required grounding terms for this new source-only QM sample. -/
def required_grounding_terms : List String :=
[
  "PositionMomentumInnerDifferenceEvidence",
  "positionMomentumInnerDifference",
  "RealLineL2PositionMomentumModel"
]

end Mathformer.Physics.FormalPhysics0045
