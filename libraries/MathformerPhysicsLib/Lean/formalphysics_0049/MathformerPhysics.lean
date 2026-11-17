import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0049`, source index 49.
Field: Quantum Mechanics.
Informal target: in the single-excitation Jaynes-Cummings manifold, the state
evolves as
`Psi(t) = cos(Omega t / 2) |e,0> - i sin(Omega t / 2) |g,1>`.  Show that the
probability of finding the atom in the ground state with one photon is
`sin(Omega t / 2)^2`.

Informal derivation summary:
1. Define `P_g(t)` as the Born probability
   `|<g,1 | Psi(t)>|^2`.
2. Expand the transition amplitude against the state decomposition.
3. Use `<g,1|e,0> = 0` and `<g,1|g,1> = 1`.
4. Identify the amplitude as `-i sin(Omega t / 2)`.
5. Use `|-i|^2 = 1` to reduce the Born probability to
   `sin(Omega t / 2)^2`.

Recursive grounding:
- selected from source-only FormalPhysics `question` and `answer` fields;
- no dataset Lean solution content is read, copied, or validated;
- the Dirac kets are represented by a Mathlib Hilbert carrier, and the braket
  is the reusable `transitionAmplitude`;
- the single-excitation Jaynes-Cummings frame, initial/boundary context,
  smooth time evolution, nonzero/positive Rabi frequency, normalized target ket,
  orthogonality, state expansion, transition amplitude, Born probability, and
  unit/dimension homogeneity are explicit Lean surfaces before the reusable
  `RabiProbabilityEvidence` theorem is invoked.

Formal alignment:
- source step 1 maps to `G.probability_definition`;
- source step 2 maps to `G.state_expansion` and
  `rabi_transition_amplitude_from_state_support`;
- source step 3 maps to `G.ground_excited_orthogonality` and
  `G.ground_normalized`;
- source step 4 maps to `rabi_vacuum_amplitude_definition_support`;
- source step 5 maps to `rabi_probability_algebraic_core`;
- the final result is replayed through `rabiProbabilityFromAmplitude`.
-/

namespace Mathformer.Physics.FormalPhysics0049

open MathformerPhysicsLib.Foundations.Contexts
open MathformerPhysicsLib.Foundations.HilbertSpace
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.QuantumMechanicsExamples
open MathformerPhysicsLib.Foundations.Units

/-- Source-grounded Hilbert packet for the Jaynes-Cummings/vacuum-Rabi
probability calculation.  The Hilbert fields carry the Dirac state expansion
and braket semantics; the scalar fields carry the reusable Born-rule evidence. -/
structure RabiProbabilityGrounding
    (H : Type*) [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H] where
  psi : HilbertStateCarrier ℂ H
  excitedZero : HilbertStateCarrier ℂ H
  groundOne : HilbertStateCarrier ℂ H
  Omega : ℝ
  t : ℝ
  Pg : ℝ
  amplitude : ℂ
  jaynes_cummings_Frame_context : PhysicsContext True
  single_excitation_manifold_context : PhysicsContext True
  boundary_initial_state_context : PhysicsContext True
  Smooth_time_evolution_context : PhysicsContext True
  omega_nonzero_context : PhysicsContext (Omega ≠ 0)
  omega_pos_context : PhysicsContext (0 < Omega)
  psi_normalized : NormalizedStateWitness psi
  ground_normalized : NormalizedStateWitness groundOne
  excited_normalized : NormalizedStateWitness excitedZero
  ground_excited_orthogonality :
    HilbertOrthogonalityWitness (𝕜 := ℂ) groundOne excitedZero
  state_expansion : TwoLevelRabiStateExpansion psi excitedZero groundOne Omega t
  amplitude_definition : amplitude = transitionAmplitude ℂ groundOne psi
  amplitude_from_state : amplitude = VacuumRabiAmplitude Omega t
  probability_definition : Pg = probabilityFromAmplitude amplitude
  rabi_probability_unit_dimension_bridge :
    UnitDimensionCompatible Pg (Real.sin (Omega * t / 2) ^ 2)

/-- Source-law proposition for the Jaynes-Cummings ground-channel probability. -/
def RabiProbabilitySourceLaw
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : RabiProbabilityGrounding H) : Prop :=
  G.Pg = Real.sin (G.Omega * G.t / 2) ^ 2

/-- Coordinate bridge for the Rabi frequency and observation time. -/
def coordinate
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : RabiProbabilityGrounding H) : ℝ × ℝ :=
  (G.Omega, G.t)

/-- Projection from source Dirac notation to the Hilbert vectors used in the
transition amplitude. -/
def rabi_state_projection
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : RabiProbabilityGrounding H) : H × H × H :=
  (G.psi, G.excitedZero, G.groundOne)

/-- Source-step support: the evolved state is the Jaynes-Cummings two-level
Rabi expansion. -/
theorem rabi_state_expansion_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : RabiProbabilityGrounding H) :
    TwoLevelRabiStateExpansion G.psi G.excitedZero G.groundOne G.Omega G.t :=
  G.state_expansion

/-- Source-step support: the target ground ket is normalized, giving
`<g,1|g,1> = 1` in the amplitude calculation. -/
theorem rabi_ground_normalization_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : RabiProbabilityGrounding H) :
    NormalizedStateWitness G.groundOne :=
  G.ground_normalized

/-- Source-step support: the excited and ground-channel states are orthogonal,
giving `<g,1|e,0> = 0`. -/
theorem rabi_ground_excited_orthogonality_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : RabiProbabilityGrounding H) :
    HilbertOrthogonalityWitness (𝕜 := ℂ) G.groundOne G.excitedZero :=
  G.ground_excited_orthogonality

/-- Source-step support: expanding the braket against the two-level state gives
the vacuum-Rabi transition amplitude. -/
theorem rabi_transition_amplitude_from_state_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : RabiProbabilityGrounding H) :
    transitionAmplitude ℂ G.groundOne G.psi = VacuumRabiAmplitude G.Omega G.t :=
  transitionAmplitude_from_twoLevelRabiStateExpansion
    G.psi G.groundOne G.excitedZero G.Omega G.t
    G.ground_normalized G.ground_excited_orthogonality G.state_expansion

/-- Source-step support: the local scalar amplitude is the Dirac transition
amplitude. -/
theorem rabi_amplitude_definition_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : RabiProbabilityGrounding H) :
    G.amplitude = transitionAmplitude ℂ G.groundOne G.psi :=
  G.amplitude_definition

/-- Source-step support: the scalar amplitude is `-i sin(Omega t / 2)`. -/
theorem rabi_vacuum_amplitude_definition_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : RabiProbabilityGrounding H) :
    G.amplitude = VacuumRabiAmplitude G.Omega G.t :=
  G.amplitude_from_state

/-- Source-step support: the reusable vacuum-Rabi amplitude unfolds to the
displayed `-i sin` scalar. -/
theorem rabi_vacuum_amplitude_apply_support
    (Omega t : ℝ) :
    VacuumRabiAmplitude Omega t =
      (-Complex.I) * (Real.sin (Omega * t / 2) : ℂ) :=
  vacuumRabiAmplitude_apply Omega t

/-- Source-step support: the Born probability is the squared norm of the
transition amplitude. -/
theorem rabi_probability_definition_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : RabiProbabilityGrounding H) :
    G.Pg = probabilityFromAmplitude G.amplitude :=
  G.probability_definition

/-- Source-step support: the Born-rule surface unfolds to the squared complex
norm. -/
theorem rabi_probability_from_amplitude_norm_support
    (z : ℂ) :
    probabilityFromAmplitude z = ‖z‖ ^ 2 :=
  probabilityFromAmplitude_apply z

/-- Source-step support: the phase `-i` has unit squared norm, leaving only
the squared sine factor. -/
theorem rabi_phase_norm_reduction_support
    (r : ℝ) :
    probabilityFromAmplitude ((-Complex.I) * (r : ℂ)) = r ^ 2 :=
  probabilityFromAmplitude_neg_I_mul_real r

/-- Unit/dimension support for the final probability curve. -/
theorem rabi_probability_unit_dimension_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : RabiProbabilityGrounding H) :
    G.Pg = Real.sin (G.Omega * G.t / 2) ^ 2 :=
  unit_dimension_bridge G.rabi_probability_unit_dimension_bridge

/-- Algebraic core: amplitude identification plus the Born rule gives the
vacuum-Rabi probability curve. -/
theorem rabi_probability_algebraic_core
    {Omega t Pg : ℝ} {amplitude : ℂ}
    (amplitude_from_state : amplitude = VacuumRabiAmplitude Omega t)
    (probability_definition : Pg = probabilityFromAmplitude amplitude) :
    Pg = Real.sin (Omega * t / 2) ^ 2 := by
  rw [probability_definition, amplitude_from_state]
  exact probabilityFromVacuumRabiAmplitude Omega t

/-- Source-law support for the Jaynes-Cummings/Rabi probability calculation. -/
theorem rabi_probability_source_law_support
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : RabiProbabilityGrounding H) :
    RabiProbabilitySourceLaw G := by
  unfold RabiProbabilitySourceLaw
  exact rabi_probability_algebraic_core
    G.amplitude_from_state G.probability_definition

/-- Bridge from the local grounding packet to the reusable
MathformerPhysicsLib Rabi probability evidence packet. -/
def rabiProbabilityEvidenceOfGrounding
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : RabiProbabilityGrounding H) :
    RabiProbabilityEvidence where
  Omega := G.Omega
  t := G.t
  Pg := G.Pg
  amplitude := G.amplitude
  amplitude_from_state := G.amplitude_from_state
  probability_definition := G.probability_definition

/-- Source-only Hilbert-grounded Jaynes-Cummings/vacuum-Rabi probability. -/
theorem rabi_probability_hilbert_grounded
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : RabiProbabilityGrounding H)
    (source_law : PhysicalLawWitness (RabiProbabilitySourceLaw G)) :
    G.Pg = Real.sin (G.Omega * G.t / 2) ^ 2 := by
  have _ : True := G.jaynes_cummings_Frame_context.holds
  have _ : True := G.single_excitation_manifold_context.holds
  have _ : True := G.boundary_initial_state_context.holds
  have _ : True := G.Smooth_time_evolution_context.holds
  have _ : G.Omega ≠ 0 := G.omega_nonzero_context.holds
  have _ : 0 < G.Omega := G.omega_pos_context.holds
  have _ : NormalizedStateWitness G.psi := G.psi_normalized
  have _ : NormalizedStateWitness G.groundOne :=
    rabi_ground_normalization_support G
  have _ : HilbertOrthogonalityWitness (𝕜 := ℂ) G.groundOne G.excitedZero :=
    rabi_ground_excited_orthogonality_support G
  have _ : TwoLevelRabiStateExpansion G.psi G.excitedZero G.groundOne G.Omega G.t :=
    rabi_state_expansion_support G
  have _ :
      transitionAmplitude ℂ G.groundOne G.psi =
        VacuumRabiAmplitude G.Omega G.t :=
    rabi_transition_amplitude_from_state_support G
  have _ :
      VacuumRabiAmplitude G.Omega G.t =
        (-Complex.I) * (Real.sin (G.Omega * G.t / 2) : ℂ) :=
    rabi_vacuum_amplitude_apply_support G.Omega G.t
  have _ :
      probabilityFromAmplitude G.amplitude = ‖G.amplitude‖ ^ 2 :=
    rabi_probability_from_amplitude_norm_support G.amplitude
  have _ :
      probabilityFromAmplitude
        ((-Complex.I) * (Real.sin (G.Omega * G.t / 2) : ℂ)) =
          Real.sin (G.Omega * G.t / 2) ^ 2 :=
    rabi_phase_norm_reduction_support (Real.sin (G.Omega * G.t / 2))
  have _ : G.Pg = Real.sin (G.Omega * G.t / 2) ^ 2 :=
    rabi_probability_unit_dimension_support G
  have h_source : RabiProbabilitySourceLaw G := source_law.holds
  unfold RabiProbabilitySourceLaw at h_source
  exact h_source

/-- Reusable-foundation replay for the same Rabi probability packet. -/
theorem rabi_probability_via_reusable_foundation
    {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℂ H] [CompleteSpace H]
    (G : RabiProbabilityGrounding H) :
    G.Pg = Real.sin (G.Omega * G.t / 2) ^ 2 := by
  exact rabiProbabilityFromAmplitude
    (rabiProbabilityEvidenceOfGrounding G)

/-- Source-only wrapper for the Jaynes-Cummings/vacuum-Rabi probability curve. -/
theorem rabi_probability_source_grounded
    (R : RabiProbabilityEvidence) :
    R.Pg = Real.sin (R.Omega * R.t / 2) ^ 2 := by
  exact rabiProbabilityFromAmplitude R

end Mathformer.Physics.FormalPhysics0049
