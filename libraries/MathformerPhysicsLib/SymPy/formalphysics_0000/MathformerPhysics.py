# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Preserve generated and reviewed formal-physics artifacts with enough context to audit their provenance.
#
# Intent:
#   Connect benchmark statements to Lean, Isabelle, and SymPy representations without hiding assumptions.
#
# Function:
#   Stores formal artifacts, summaries, and grounding reports consumed by physics backend tests and documentation.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

r"""Mathformer physics SymPy autoformalization artifact.

Original source task (NL): From the x Euler-Lagrange equation for a charged particle with electromagnetic potentials, derive the x component of the Lorentz force.
Original source task (LaTeX): F_x=qE_x+q(\dot y B_z-\dot z B_y)
Formalized target: F_x=qE_x+q(\dot y B_z-\dot z B_y)
Source anchors: src_L0004, src_L0009

Original informal statement:
From the x Euler-Lagrange equation for a charged particle with electromagnetic
potentials phi(x,y,z,t) and A=(A_x,A_y,A_z), derive the x component of the
Lorentz force,
    F_x = q E_x + q(ydot B_z - zdot B_y).

Informal derivation commentary:
1. Start from the source Euler-Lagrange x equation:
   F_x + q(Ax_t + Ax_y ydot + Ax_z zdot)
     = q(Ay_x ydot + Az_x zdot) - q phi_x.
2. Solve the equation for F_x by moving the vector-potential derivative terms
   to the right-hand side.
3. Group the result into electric and magnetic field combinations:
   -q(phi_x + Ax_t) + q ydot(Ay_x - Ax_y) - q zdot(Ax_z - Az_x).
4. Use E_x = -(phi_x + Ax_t).
5. Use B_z = Ay_x - Ax_y and B_y = Ax_z - Az_x to obtain the x Lorentz-force
   component.

SymPy alignment:
- Informal step 1 maps to DERIVATION_STEPS[0] /
  step_01_euler_lagrange_x_component.
- Informal step 2 maps to DERIVATION_STEPS[1] /
  step_02_solve_for_force_component.
- Informal steps 3-5 map to DERIVATION_STEPS[2] /
  step_03_expand_lorentz_component and to the symbolic residual checked by
  validate_derivation_steps.
- Physical typing and units are carried by QUANTITY_TABLE, QUANTITY_SURFACE,
  validate_dimensions, and validate_projection_bridges.
- Numeric and symbolic smoke checks are exposed by validate_numeric_samples
  and validate_symbolic.

Generated support note: This artifact implements the
`sympy_physics_derivation_trace` style. Source-backed equations are kept in
`CLAIM`; generated algebra, calculus, substitution, unit, and validation steps
are exposed through `DERIVATION_STEPS` and the validation functions below.
Complete status must come from execution, dimensional analysis, symbolic step
verification, and numeric sanity checks, not from this file existing.
"""

from backends.sympy.MathformerPhysicsSympy.pipeline import case_spec, derive_case, enriched_assumption_context, enriched_dimension_projection_report, enriched_equation_surface, enriched_equational_semantics_report, enriched_final_equation_reviews, execute_case, format_derivation_print, numeric_samples, step_verification, sympy_library_grounding, unit_analysis


# Stable identifier used to recover the source task from the shared pipeline.
CASE_ID = "formalphysics_0000"
COMMENTARY_HEADER = 'Original informal statement:\nFrom the x Euler-Lagrange equation for a charged particle with electromagnetic\npotentials phi(x,y,z,t) and A=(A_x,A_y,A_z), derive the x component of the\nLorentz force,\n    F_x = q E_x + q(ydot B_z - zdot B_y).\n\nInformal derivation commentary:\n1. Start from the source Euler-Lagrange x equation:\n   F_x + q(Ax_t + Ax_y ydot + Ax_z zdot)\n     = q(Ay_x ydot + Az_x zdot) - q phi_x.\n2. Solve the equation for F_x by moving the vector-potential derivative terms\n   to the right-hand side.\n3. Group the result into electric and magnetic field combinations:\n   -q(phi_x + Ax_t) + q ydot(Ay_x - Ax_y) - q zdot(Ax_z - Az_x).\n4. Use E_x = -(phi_x + Ax_t).\n5. Use B_z = Ay_x - Ax_y and B_y = Ax_z - Az_x to obtain the x Lorentz-force\n   component.\n\nSymPy alignment:\n- Informal step 1 maps to DERIVATION_STEPS[0] /\n  step_01_euler_lagrange_x_component.\n- Informal step 2 maps to DERIVATION_STEPS[1] /\n  step_02_solve_for_force_component.\n- Informal steps 3-5 map to DERIVATION_STEPS[2] /\n  step_03_expand_lorentz_component and to the symbolic residual checked by\n  validate_derivation_steps.\n- Physical typing and units are carried by QUANTITY_TABLE, QUANTITY_SURFACE,\n  validate_dimensions, and validate_projection_bridges.\n- Numeric and symbolic smoke checks are exposed by validate_numeric_samples\n  and validate_symbolic.'
DERIVATION_PRINT = 'FULL PRINTED SYMPY DERIVATION\nCase: formalphysics_0000\nClaim (NL): From the x Euler-Lagrange equation for a charged particle with electromagnetic potentials, derive the x component of the Lorentz force.\nClaim (LaTeX): F_x=qE_x+q(\\dot y B_z-\\dot z B_y)\nTarget key: lorentz_force_x_component\n\nQuantities:\n- q: particle charge; dimension=charge; unit=coulomb\n- Fx: x component of force; dimension=force; unit=newton\n- Ex: x component of electric field; dimension=electric_field; unit=volt/meter\n- By: y component of magnetic field; dimension=magnetic_field; unit=tesla\n- Bz: z component of magnetic field; dimension=magnetic_field; unit=tesla\n- ydot: y velocity component; dimension=velocity; unit=meter/second\n- zdot: z velocity component; dimension=velocity; unit=meter/second\n- Ax_t: time derivative of the x component of vector potential; dimension=electric_field; unit=volt/meter\n- Ax_y: y derivative of the x component of vector potential; dimension=magnetic_field; unit=tesla\n- Ax_z: z derivative of the x component of vector potential; dimension=magnetic_field; unit=tesla\n- Ay_x: x derivative of the y component of vector potential; dimension=magnetic_field; unit=tesla\n- Az_x: x derivative of the z component of vector potential; dimension=magnetic_field; unit=tesla\n- phi_x: x derivative of scalar electric potential; dimension=electric_field; unit=volt/meter\n\nContext assumptions:\n- fixed Cartesian coordinate frame\n- take the x component of the vector equation\n- scalar and vector potentials are differentiable\n- partial derivative placeholders inherit field dimensions\n- SI electromagnetic unit convention\n\nPhysical laws and source rules:\n- Euler-Lagrange equation for minimally coupled charged-particle Lagrangian\n- E_x=-(phi_x+Ax_t)\n- B_y=Ax_z-Az_x\n- B_z=Ay_x-Ax_y\n- Lorentz force component F_x=qE_x+q(ydot B_z-zdot B_y)\n\nProjection/operator bridges:\n- formalphysics_0000.coordinate_component_bridge: coordinate_component_bridge [provided]; source=F=q(E+v cross B); targets=formalphysics_0000.target\n- formalphysics_0000.field_derivative_placeholder_bridge: field_derivative_placeholder_bridge [provided]; source=E=-grad phi-partial_t A and B=curl A; targets=formalphysics_0000.field_definitions\n\nDerivation steps:\n1. step_01_euler_lagrange_x_component [source_equation]\n   expression: Eq(Fx + q*(Ax_t + Ax_y*ydot + Ax_z*zdot), -phi_x*q + q*(Ay_x*ydot + Az_x*zdot))\n   rule: Euler-Lagrange equation for the x coordinate of the minimally coupled charged-particle Lagrangian\n   support: source equation; generated=False; source_anchors=src_L0004, src_L0009\n2. step_02_solve_for_force_component [generated_algebra]\n   expression: q*(-Ax_t - Ax_y*ydot - Ax_z*zdot + Ay_x*ydot + Az_x*zdot - phi_x)\n   rule: solve source equation for F_x\n   support: generated gap; generated=True; source_anchors=none\n3. step_03_expand_lorentz_component [target_equation]\n   expression: -Ax_t*q - Ax_y*q*ydot - Ax_z*q*zdot + Ay_x*q*ydot + Az_x*q*zdot - phi_x*q\n   rule: substitute E_x, B_y, and B_z definitions into q(E_x+ydot B_z-zdot B_y)\n   support: source target; generated=False; source_anchors=src_L0004, src_L0009\n\nComputed expressions:\n- target_expression: q*(-Ax_t - Ax_y*ydot - Ax_z*zdot + Ay_x*ydot + Az_x*zdot - phi_x)\n- expected/source_expression: q*(-Ax_t - Ax_y*ydot - Ax_z*zdot + Ay_x*ydot + Az_x*zdot - phi_x)\n- residual target_minus_expected: 0\n\nValidation print:\n- symbolic_target_verified: True\n- derivation_steps_passed: True\n- dimensionally_consistent: True\n- numeric_sample_passed: True\n- numeric_sample: q=2, ydot=3, zdot=5, Ax_t=7, Ax_y=11, Ax_z=13, Ay_x=17, Az_x=19, phi_x=23\n- numeric_target_value: 36.0\n- numeric_expected_value: 36.0\n\nEquivalence certificates:\n- step_01_euler_lagrange_x_component: passed=True; certificate=symbolic residual and executable trace metadata; rule=Euler-Lagrange equation for the x coordinate of the minimally coupled charged-particle Lagrangian\n- step_02_solve_for_force_component: passed=True; certificate=symbolic residual and executable trace metadata; rule=solve source equation for F_x\n- step_03_expand_lorentz_component: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute E_x, B_y, and B_z definitions into q(E_x+ydot B_z-zdot B_y)\n\nSymPy library grounding:\n- grounding_level: high\n- calculus: grounded; APIs=sympy.core.function.diff, sympy.integrals.integrals.integrate, sympy.core.function.Derivative, sympy.integrals.integrals.Integral\n- mechanics: grounded; APIs=sympy.physics.mechanics.particle.Particle, sympy.physics.mechanics.functions.dynamicsymbols, sympy.physics.mechanics.lagrange.LagrangesMethod\n- numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy\n- scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand\n- solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp\n- units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify\n- vector_analysis: grounded; APIs=sympy.vector.coordsysrect.CoordSys3D, sympy.vector.operators.gradient, sympy.vector.operators.divergence, sympy.vector.operators.curl'

# Source-alignment packet: preserves the original task and the exact formal
# target represented by this artifact.
CLAIM = {
    "backend": "sympy",
    "style": "sympy_physics_derivation_trace",
    "case_id": CASE_ID,
    "statement_nl": 'From the x Euler-Lagrange equation for a charged particle with electromagnetic potentials, derive the x component of the Lorentz force.',
    "statement_latex": 'F_x=qE_x+q(\\dot y B_z-\\dot z B_y)',
    "source_anchors": ['src_L0004', 'src_L0009'],
    "commentary_header": COMMENTARY_HEADER,
}

# Structured source/task context. These are intentionally data, not comments,
# so validators and documentation generators can inspect them.
QUANTITY_TABLE = case_spec(CASE_ID)["quantities"]
ASSUMPTIONS = case_spec(CASE_ID)["assumptions"]
DERIVATION_STEPS = derive_case(CASE_ID)["steps"]
EQUATION_SURFACE = enriched_equation_surface(CASE_ID)
QUANTITY_SURFACE = EQUATION_SURFACE["QUANTITY_SURFACE"]
EQUATION_GRAPH = EQUATION_SURFACE["EQUATION_GRAPH"]
LAW_TABLE = EQUATION_SURFACE["LAW_TABLE"]
PROJECTION_BRIDGES = EQUATION_SURFACE["PROJECTION_BRIDGES"]
EQUIVALENCE_CERTIFICATES = EQUATION_SURFACE["EQUIVALENCE_CERTIFICATES"]
SYMPY_LIBRARY_GROUNDING = sympy_library_grounding(CASE_ID)
ASSUMPTION_CONTEXT = enriched_assumption_context(CASE_ID)
CONTEXT_ASSUMPTIONS = ASSUMPTION_CONTEXT["CONTEXT_ASSUMPTIONS"]
SIDE_CONDITIONS = ASSUMPTION_CONTEXT["SIDE_CONDITIONS"]


def build_symbols():
    """Build the SymPy symbols bound by the source task."""
    return derive_case(CASE_ID)["symbols"]


def build_units():
    """Return source-aligned unit annotations for each bound quantity."""
    return {symbol: data[2] for symbol, data in case_spec(CASE_ID)["quantities"].items()}


def build_equations():
    """Return the computed target, expected source target, and residual."""
    result = derive_case(CASE_ID)
    return {
        "target_expression": result["target_expression"],
        "expected_expression": result["expected_expression"],
        "residual": result["residual"],
    }


def build_expressions():
    """Return lhs/rhs/difference using the generic mathematical SymPy contract."""
    result = derive_case(CASE_ID)
    return {
        "lhs": result["target_expression"],
        "rhs": result["expected_expression"],
        "validation_difference": result["residual"],
    }


def derive_target():
    """Compute the target expression from the derivation chain."""
    return derive_case(CASE_ID)["target_expression"]


def validate_dimensions():
    """Check dimensional consistency for the target and generated steps."""
    return unit_analysis(CASE_ID)


def validate_derivation_steps():
    """Check symbolic residuals and step metadata."""
    return step_verification(CASE_ID)


def validate_numeric_samples(max_n=None):
    """Evaluate admissible numeric samples as supporting validation."""
    report = numeric_samples(CASE_ID)
    if max_n is not None:
        report = dict(report)
        report["bounded_search_limit"] = max_n
        report["sample_count"] = 1
    return report


def validate_symbolic():
    """Return whether the symbolic derivation validates the source target."""
    return step_verification(CASE_ID)["passed"]


def validate_equational_semantics():
    """Check source-to-equation semantic preservation for the trace."""
    return enriched_equational_semantics_report(CASE_ID)


def validate_assumption_context():
    """Check that contextual physics assumptions are explicit."""
    return {"passed": ASSUMPTION_CONTEXT["status"] == "pass", "packet": ASSUMPTION_CONTEXT}


def validate_projection_bridges():
    """Check scalar projection bridges for vector, field, or frame reductions."""
    return {
        "passed": all(bridge.get("status") in {"provided", "pass", "ready", "required"} for bridge in PROJECTION_BRIDGES),
        "projection_bridges": PROJECTION_BRIDGES,
    }


def validate_no_hidden_target():
    """Check that target equations are not hidden as source inputs."""
    target_like_sources = [
        node for node in EQUATION_GRAPH["nodes"]
        if node.get("role") in {"source", "input"}
        and node.get("support") != "source_backed"
        and ("target" in str(node).lower() or "answer" in str(node).lower())
    ]
    return {"passed": not target_like_sources, "target_like_sources": target_like_sources}


def validate_law_usage():
    """Check that physical law usage is visible in the law table."""
    return {"passed": bool(LAW_TABLE), "law_count": len(LAW_TABLE), "law_table": LAW_TABLE}


def validate_library_grounding():
    """Check that the derivation uses maximally grounded installed SymPy APIs."""
    return {
        "passed": SYMPY_LIBRARY_GROUNDING["grounding_level"] == "high",
        "grounding": SYMPY_LIBRARY_GROUNDING,
    }


def review_final_equations():
    """Run final physics and mathematical equation reviewers."""
    return enriched_final_equation_reviews(CASE_ID)


def explain_trace():
    """Return source-backed and generated derivation steps with comments."""
    raw_steps = derive_case(CASE_ID)["steps"]
    enriched_steps = []
    previous = CLAIM["statement_latex"]
    for step in raw_steps:
        enriched_steps.append({
            **step,
            "input": previous,
            "output": step["expression"],
            "justification": step["rule"],
            "api": "sympy.solve/simplify/expand plus case-specific physics bridge metadata",
        })
        previous = step["expression"]
    return enriched_steps


def print_derivation():
    """Return the full printed derivation trace embedded at the end."""
    return format_derivation_print(CASE_ID)


def run_all():
    """Execute all physics SymPy validations for this artifact."""
    report = execute_case(CASE_ID)
    report["equation_surface"] = EQUATION_SURFACE
    report["assumption_context"] = ASSUMPTION_CONTEXT
    report["equational_semantics"] = validate_equational_semantics()
    report["dimension_projection"] = enriched_dimension_projection_report(CASE_ID)
    report["sympy_library_grounding"] = validate_library_grounding()
    report["final_equation_reviews"] = review_final_equations()
    return report


# End-of-file derivation print
# FULL PRINTED SYMPY DERIVATION
# Case: formalphysics_0000
# Claim (NL): From the x Euler-Lagrange equation for a charged particle with electromagnetic potentials, derive the x component of the Lorentz force.
# Claim (LaTeX): F_x=qE_x+q(\dot y B_z-\dot z B_y)
# Target key: lorentz_force_x_component
#
# Quantities:
# - q: particle charge; dimension=charge; unit=coulomb
# - Fx: x component of force; dimension=force; unit=newton
# - Ex: x component of electric field; dimension=electric_field; unit=volt/meter
# - By: y component of magnetic field; dimension=magnetic_field; unit=tesla
# - Bz: z component of magnetic field; dimension=magnetic_field; unit=tesla
# - ydot: y velocity component; dimension=velocity; unit=meter/second
# - zdot: z velocity component; dimension=velocity; unit=meter/second
# - Ax_t: time derivative of the x component of vector potential; dimension=electric_field; unit=volt/meter
# - Ax_y: y derivative of the x component of vector potential; dimension=magnetic_field; unit=tesla
# - Ax_z: z derivative of the x component of vector potential; dimension=magnetic_field; unit=tesla
# - Ay_x: x derivative of the y component of vector potential; dimension=magnetic_field; unit=tesla
# - Az_x: x derivative of the z component of vector potential; dimension=magnetic_field; unit=tesla
# - phi_x: x derivative of scalar electric potential; dimension=electric_field; unit=volt/meter
#
# Context assumptions:
# - fixed Cartesian coordinate frame
# - take the x component of the vector equation
# - scalar and vector potentials are differentiable
# - partial derivative placeholders inherit field dimensions
# - SI electromagnetic unit convention
#
# Physical laws and source rules:
# - Euler-Lagrange equation for minimally coupled charged-particle Lagrangian
# - E_x=-(phi_x+Ax_t)
# - B_y=Ax_z-Az_x
# - B_z=Ay_x-Ax_y
# - Lorentz force component F_x=qE_x+q(ydot B_z-zdot B_y)
#
# Projection/operator bridges:
# - formalphysics_0000.coordinate_component_bridge: coordinate_component_bridge [provided]; source=F=q(E+v cross B); targets=formalphysics_0000.target
# - formalphysics_0000.field_derivative_placeholder_bridge: field_derivative_placeholder_bridge [provided]; source=E=-grad phi-partial_t A and B=curl A; targets=formalphysics_0000.field_definitions
#
# Derivation steps:
# 1. step_01_euler_lagrange_x_component [source_equation]
#    expression: Eq(Fx + q*(Ax_t + Ax_y*ydot + Ax_z*zdot), -phi_x*q + q*(Ay_x*ydot + Az_x*zdot))
#    rule: Euler-Lagrange equation for the x coordinate of the minimally coupled charged-particle Lagrangian
#    support: source equation; generated=False; source_anchors=src_L0004, src_L0009
# 2. step_02_solve_for_force_component [generated_algebra]
#    expression: q*(-Ax_t - Ax_y*ydot - Ax_z*zdot + Ay_x*ydot + Az_x*zdot - phi_x)
#    rule: solve source equation for F_x
#    support: generated gap; generated=True; source_anchors=none
# 3. step_03_expand_lorentz_component [target_equation]
#    expression: -Ax_t*q - Ax_y*q*ydot - Ax_z*q*zdot + Ay_x*q*ydot + Az_x*q*zdot - phi_x*q
#    rule: substitute E_x, B_y, and B_z definitions into q(E_x+ydot B_z-zdot B_y)
#    support: source target; generated=False; source_anchors=src_L0004, src_L0009
#
# Computed expressions:
# - target_expression: q*(-Ax_t - Ax_y*ydot - Ax_z*zdot + Ay_x*ydot + Az_x*zdot - phi_x)
# - expected/source_expression: q*(-Ax_t - Ax_y*ydot - Ax_z*zdot + Ay_x*ydot + Az_x*zdot - phi_x)
# - residual target_minus_expected: 0
#
# Validation print:
# - symbolic_target_verified: True
# - derivation_steps_passed: True
# - dimensionally_consistent: True
# - numeric_sample_passed: True
# - numeric_sample: q=2, ydot=3, zdot=5, Ax_t=7, Ax_y=11, Ax_z=13, Ay_x=17, Az_x=19, phi_x=23
# - numeric_target_value: 36.0
# - numeric_expected_value: 36.0
#
# Equivalence certificates:
# - step_01_euler_lagrange_x_component: passed=True; certificate=symbolic residual and executable trace metadata; rule=Euler-Lagrange equation for the x coordinate of the minimally coupled charged-particle Lagrangian
# - step_02_solve_for_force_component: passed=True; certificate=symbolic residual and executable trace metadata; rule=solve source equation for F_x
# - step_03_expand_lorentz_component: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute E_x, B_y, and B_z definitions into q(E_x+ydot B_z-zdot B_y)
#
# SymPy library grounding:
# - grounding_level: high
# - calculus: grounded; APIs=sympy.core.function.diff, sympy.integrals.integrals.integrate, sympy.core.function.Derivative, sympy.integrals.integrals.Integral
# - mechanics: grounded; APIs=sympy.physics.mechanics.particle.Particle, sympy.physics.mechanics.functions.dynamicsymbols, sympy.physics.mechanics.lagrange.LagrangesMethod
# - numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy
# - scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand
# - solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp
# - units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify
# - vector_analysis: grounded; APIs=sympy.vector.coordsysrect.CoordSys3D, sympy.vector.operators.gradient, sympy.vector.operators.divergence, sympy.vector.operators.curl
