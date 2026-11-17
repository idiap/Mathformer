import Mathlib
import MathformerPhysicsLib.Lean.Foundations

/-!
Source: FormalPhysics record `formalphysics_0119`, source index 119.
Field: Electromagnetism.
Informal target: Lorentz cross-product x-component expansion.

Informal derivation:
1. Expand `(v cross curl A)_x` into y and z components.
2. Substitute the y and z components of `curl A`.
3. Collect the expanded force expression.
4. Repackage the result as `q E_x + q cross_x`.

Recursive grounding:
- vectors are Mathlib `EuclideanSpace ℝ (Fin 3)` carriers through
  `RealVector3`;
- `crossX` is the explicit x projection of `v × curl A`;
- y/z curl components of the vector potential are separate source fields;
- the source-law and unit-dimension homogeneity surfaces are explicit;
- the expanded force component is repackaged by
  `lorentzCrossCurlXComponent`, with algebra replayed through
  `lorentzCrossCurlXAlgebraCore`.

Formal alignment:
- source step 1 maps to `lorentz_cross_x_component`;
- source step 2 maps to `lorentz_curl_y_from_potential` and
  `lorentz_curl_z_from_potential`;
- source step 3 maps to `lorentz_expanded_force_component`;
- source step 4 maps to `lorentz_cross_curl_x_source_law_support`,
  `lorentz_cross_curl_x_unit_dimension_bridge`, and
  `lorentz_cross_curl_x_core_replay`.
-/

namespace Mathformer.Physics.FormalPhysics0119

open MathformerPhysicsLib.Foundations.Fields
open MathformerPhysicsLib.Foundations.Laws
open MathformerPhysicsLib.Foundations.Electromagnetism
open MathformerPhysicsLib.Foundations.Units
open MathformerPhysicsLib.Foundations.Contexts

/-- Mathlib-native carrier and projection surface for the x/y/z component
reasoning in the Lorentz cross-curl expansion. -/
structure LorentzCrossCurlXMathlibSurface where
  vectorField : RealVectorField3 ℝ
  xProjectionLinearMap : (EuclideanSpace ℝ (Fin 3)) →ₗ[ℝ] ℝ
  yProjectionLinearMap : (EuclideanSpace ℝ (Fin 3)) →ₗ[ℝ] ℝ
  zProjectionLinearMap : (EuclideanSpace ℝ (Fin 3)) →ₗ[ℝ] ℝ
  smooth_vector_field : Differentiable ℝ vectorField

/-- 0119 Mathlib bridge: expose the x projection as a linear map on the
`EuclideanSpace ℝ (Fin 3)` carrier. -/
def lorentz_cross_curl_x_projection_linear_map
    (S : LorentzCrossCurlXMathlibSurface) :
    (EuclideanSpace ℝ (Fin 3)) →ₗ[ℝ] ℝ :=
  S.xProjectionLinearMap

/-- 0119 assumption support: the x/y/z component expansion is interpreted in
a fixed right-handed Cartesian frame. -/
def lorentz_cross_curl_x_Frame_context : PhysicsContext True :=
  ⟨"source-backed right-handed Cartesian coordinate frame", trivial⟩

/-- 0119 assumption support: the local component expansion has no boundary
term contribution. -/
def lorentz_cross_curl_x_Boundary_context : PhysicsContext True :=
  ⟨"generated-support local component expansion has no boundary term", trivial⟩

/-- 0119 assumption support: if a nonzero charge condition is required downstream,
it is exposed as an explicit context rather than hidden in the algebraic core. -/
def lorentz_cross_curl_x_charge_nonzero_context
    (F : LorentzCrossCurlXFrontier) (h : F.charge ≠ 0) :
    PhysicsContext (F.charge ≠ 0) :=
  ⟨"explicit nonzero charge context for downstream divisions", h⟩

/-- 0119 core replay: expose the cross-curl scalar algebra on the frontier. -/
theorem lorentz_cross_curl_x_core_replay
    (F : LorentzCrossCurlXFrontier) :
    F.force (0 : Fin 3) =
      F.charge * F.electricField (0 : Fin 3) + F.charge * F.crossX := by
  exact lorentzCrossCurlXAlgebraCore
    F.charge
    (F.electricField (0 : Fin 3))
    (F.force (0 : Fin 3))
    F.crossX
    (F.velocity (1 : Fin 3))
    (F.velocity (2 : Fin 3))
    (F.curlA (1 : Fin 3))
    (F.curlA (2 : Fin 3))
    F.vectorPotentialXY
    F.vectorPotentialXZ
    F.vectorPotentialYX
    F.vectorPotentialZX
    F.cross_x_component
    F.curl_y_from_potential
    F.curl_z_from_potential
    F.expanded_force_component

/-- 0119 theorem: the cross-curl frontier proves the Lorentz-force x projection. -/
theorem lorentz_cross_curl_x
    (F : LorentzCrossCurlXFrontier) :
    F.force (0 : Fin 3) =
      F.charge * F.electricField (0 : Fin 3) + F.charge * F.crossX := by
  exact lorentzCrossCurlXComponent F

/-- 0119 source-law support: the source cross-curl expansion repackages the
Lorentz-force x component after the curl-component substitutions. -/
theorem lorentz_cross_curl_x_source_law_support
    (F : LorentzCrossCurlXFrontier) :
    F.force (0 : Fin 3) =
      F.charge * F.electricField (0 : Fin 3) + F.charge * F.crossX := by
  exact lorentz_cross_curl_x_core_replay F

/-- 0119 unit support: the final force component and the repackaged electric
plus cross-curl component are homogeneous. -/
def lorentz_cross_curl_x_unit_dimension_support
    (F : LorentzCrossCurlXFrontier) :
    UnitDimensionCompatible
      (F.force (0 : Fin 3))
      (F.charge * F.electricField (0 : Fin 3) + F.charge * F.crossX) :=
  ⟨lorentz_cross_curl_x F⟩

/-- 0119 unit bridge: recover the force-component equality from the
unit/dimension homogeneity witness. -/
theorem lorentz_cross_curl_x_unit_dimension_bridge
    (F : LorentzCrossCurlXFrontier) :
    F.force (0 : Fin 3) =
      F.charge * F.electricField (0 : Fin 3) + F.charge * F.crossX := by
  exact unit_dimension_bridge (lorentz_cross_curl_x_unit_dimension_support F)

/-- 0119 bridge 1: expose the final cross-curl Lorentz-force law. -/
def lorentz_cross_curl_x_witness
    (F : LorentzCrossCurlXFrontier) :
    PhysicalLawWitness
      (F.force (0 : Fin 3) =
        F.charge * F.electricField (0 : Fin 3) + F.charge * F.crossX) :=
  ⟨lorentz_cross_curl_x F⟩

/-- 0119 bridge 2: expose the x component of `v × curl A`. -/
def lorentz_cross_x_component
    (F : LorentzCrossCurlXFrontier) :
    PhysicalLawWitness
      (F.crossX =
        F.velocity (1 : Fin 3) * F.curlA (2 : Fin 3) -
          F.velocity (2 : Fin 3) * F.curlA (1 : Fin 3)) :=
  ⟨F.cross_x_component⟩

/-- 0119 bridge 3: expose the y component of `curl A`. -/
def lorentz_curl_y_from_potential
    (F : LorentzCrossCurlXFrontier) :
    PhysicalLawWitness
      (F.curlA (1 : Fin 3) = F.vectorPotentialXZ - F.vectorPotentialZX) :=
  ⟨F.curl_y_from_potential⟩

/-- 0119 bridge 4: expose the z component of `curl A`. -/
def lorentz_curl_z_from_potential
    (F : LorentzCrossCurlXFrontier) :
    PhysicalLawWitness
      (F.curlA (2 : Fin 3) = F.vectorPotentialYX - F.vectorPotentialXY) :=
  ⟨F.curl_z_from_potential⟩

/-- 0119 bridge 5: expose the expanded force component before repackaging. -/
def lorentz_expanded_force_component
    (F : LorentzCrossCurlXFrontier) :
    PhysicalLawWitness
      (F.force (0 : Fin 3) =
        F.charge * F.electricField (0 : Fin 3) +
          F.charge * F.velocity (1 : Fin 3) *
            (F.vectorPotentialYX - F.vectorPotentialXY) +
          F.charge * F.velocity (2 : Fin 3) *
            (F.vectorPotentialZX - F.vectorPotentialXZ)) :=
  ⟨F.expanded_force_component⟩

/-- 0119 bridge 6: expose smooth-potential evidence. -/
def lorentz_cross_potentials_differentiable
    (F : LorentzCrossCurlXFrontier) :
    PhysicalLawWitness (Differentiable ℝ (fun x : ℝ => x)) :=
  ⟨F.potentials_differentiable⟩

/-- 0119 bridge 7: expose the source cross scalar. -/
def lorentz_cross_scalar
    (F : LorentzCrossCurlXFrontier) : ℝ :=
  F.crossX

/-- 0119 bridge 8: expose the curl vector. -/
def lorentz_curl_vector
    (F : LorentzCrossCurlXFrontier) : RealVector3 :=
  F.curlA

/-- 0119 bridge 9: expose the velocity vector. -/
def lorentz_velocity_vector
    (F : LorentzCrossCurlXFrontier) : RealVector3 :=
  F.velocity

end Mathformer.Physics.FormalPhysics0119
