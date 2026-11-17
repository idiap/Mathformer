# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.
#
# Intent:
#   Provide lightweight formalizations that can be tested numerically, algebraically, and against source problems.
#
# Function:
#   Defines generated artifacts or pipeline code used by SymPy backend validation.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

r"""Mathformer physics SymPy autoformalization artifact.

Original source task (NL): Use the Euler-Lagrange x equation for a minimally coupled charged particle to obtain the force-balance component after cancelling the common Ax_x xdot term.
Original source task (LaTeX): F_x+q(A_{x,t}+A_{x,y}\dot y+A_{x,z}\dot z)=q(A_{y,x}\dot y+A_{z,x}\dot z)-q\phi_x
Formalized target: F_x+q(A_{x,t}+A_{x,y}\dot y+A_{x,z}\dot z)=q(A_{y,x}\dot y+A_{z,x}\dot z)-q\phi_x
Source anchors: src_L0004, src_L0009

Original informal statement:
Use the Euler-Lagrange equation for the x coordinate of a charged particle in
electromagnetic potentials to derive the x-component force balance.

Informal derivation commentary:
1. Write d/dt partial L/partial xdot and partial L/partial x.
2. Equate them by Euler-Lagrange.
3. Cancel the common Ax_x xdot term.
4. Use F_x = m xddot to obtain the force-balance component.

SymPy alignment:
- Source Euler-Lagrange rearrangement maps to DERIVATION_STEPS[0].
- Common-term cancellation maps to DERIVATION_STEPS[1].
- Force substitution maps to DERIVATION_STEPS[2].
- Component and Lagrangian context are carried by PROJECTION_BRIDGES and
  LAW_TABLE.

Generated support note: This artifact implements the
`sympy_physics_derivation_trace` style. Source-backed equations are kept in
`CLAIM`; generated algebra, calculus, substitution, unit, and validation steps
are exposed through `DERIVATION_STEPS` and the validation functions below.
Complete status must come from execution, dimensional analysis, symbolic step
verification, and numeric sanity checks, not from this file existing.
"""

from backends.sympy.MathformerPhysicsSympy.pipeline import (
    case_spec,
    derive_case,
    enriched_assumption_context,
    enriched_dimension_projection_report,
    enriched_equation_surface,
    enriched_equational_semantics_report,
    enriched_final_equation_reviews,
    execute_case,
    format_derivation_print,
    numeric_samples,
    step_verification,
    sympy_library_grounding,
    unit_analysis,
)

# Stable identifier used to recover the source task from the shared pipeline.
CASE_ID = "formalphysics_0172"
COMMENTARY_HEADER = "Original informal statement:\nUse the Euler-Lagrange equation for the x coordinate of a charged particle in\nelectromagnetic potentials to derive the x-component force balance.\n\nInformal derivation commentary:\n1. Write d/dt partial L/partial xdot and partial L/partial x.\n2. Equate them by Euler-Lagrange.\n3. Cancel the common Ax_x xdot term.\n4. Use F_x = m xddot to obtain the force-balance component.\n\nSymPy alignment:\n- Source Euler-Lagrange rearrangement maps to DERIVATION_STEPS[0].\n- Common-term cancellation maps to DERIVATION_STEPS[1].\n- Force substitution maps to DERIVATION_STEPS[2].\n- Component and Lagrangian context are carried by PROJECTION_BRIDGES and\n  LAW_TABLE."
DERIVATION_PRINT = "FULL PRINTED SYMPY DERIVATION\nCase: formalphysics_0172\nClaim (NL): Use the Euler-Lagrange x equation for a minimally coupled charged particle to obtain the force-balance component after cancelling the common Ax_x xdot term.\nClaim (LaTeX): F_x+q(A_{x,t}+A_{x,y}\\dot y+A_{x,z}\\dot z)=q(A_{y,x}\\dot y+A_{z,x}\\dot z)-q\\phi_x\nTarget key: euler_lagrange_x_force_balance\n\nQuantities:\n- mddx: mass times x acceleration; dimension=force; unit=newton\n- Fx: x component of force; dimension=force; unit=newton\n- q_Axt: charge times time derivative of A_x; dimension=force; unit=newton\n- q_Axy_ydot: charge times A_x,y times y velocity; dimension=force; unit=newton\n- q_Axz_zdot: charge times A_x,z times z velocity; dimension=force; unit=newton\n- q_Ayx_ydot: charge times A_y,x times y velocity; dimension=force; unit=newton\n- q_Azx_zdot: charge times A_z,x times z velocity; dimension=force; unit=newton\n- q_phix: charge times scalar-potential x derivative; dimension=force; unit=newton\n\nContext assumptions:\n- fixed Cartesian coordinate frame\n- source Euler-Lagrange x equation is valid\n- F_x=m xddot\n- common A_x,x xdot terms cancel on both sides\n- potentials are differentiable\n\nPhysical laws and source rules:\n- Euler-Lagrange equation for minimally coupled charged-particle Lagrangian\n- force definition F_x=m xddot\n- coordinate component projection of the Lagrangian force balance\n\nProjection/operator bridges:\n- formalphysics_0172.coordinate_component_bridge: coordinate_component_bridge [provided]; source=Euler-Lagrange vector force balance; targets=formalphysics_0172.target\n\nDerivation steps:\n1. step_01_euler_lagrange_after_common_term_cancellation [source_equation]\n   expression: Eq(mddx + q_Axt + q_Axy_ydot + q_Axz_zdot, q_Ayx_ydot + q_Azx_zdot - q_phix)\n   rule: Euler-Lagrange x equation after cancelling the common A_x,x xdot term\n   support: source equation; generated=False; source_anchors=src_L0004, src_L0009\n2. step_02_substitute_force_definition [source_substitution]\n   expression: Eq(Fx + q_Axt + q_Axy_ydot + q_Axz_zdot, q_Ayx_ydot + q_Azx_zdot - q_phix)\n   rule: substitute F_x=m xddot\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n3. step_03_solve_force_balance_for_Fx [target_equation]\n   expression: -q_Axt - q_Axy_ydot - q_Axz_zdot + q_Ayx_ydot + q_Azx_zdot - q_phix\n   rule: solve the component force balance for F_x\n   support: source target; generated=False; source_anchors=src_L0004, src_L0009\n\nComputed expressions:\n- target_expression: -q_Axt - q_Axy_ydot - q_Axz_zdot + q_Ayx_ydot + q_Azx_zdot - q_phix\n- expected/source_expression: -q_Axt - q_Axy_ydot - q_Axz_zdot + q_Ayx_ydot + q_Azx_zdot - q_phix\n- residual target_minus_expected: 0\n\nValidation print:\n- symbolic_target_verified: True\n- derivation_steps_passed: True\n- dimensionally_consistent: True\n- numeric_sample_passed: True\n- numeric_sample: mddx=41, Fx=41, q_Axt=3, q_Axy_ydot=5, q_Axz_zdot=7, q_Ayx_ydot=23, q_Azx_zdot=31, q_phix=2\n- numeric_target_value: 37.0\n- numeric_expected_value: 37.0\n\nEquivalence certificates:\n- step_01_euler_lagrange_after_common_term_cancellation: passed=True; certificate=symbolic residual and executable trace metadata; rule=Euler-Lagrange x equation after cancelling the common A_x,x xdot term\n- step_02_substitute_force_definition: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute F_x=m xddot\n- step_03_solve_force_balance_for_Fx: passed=True; certificate=symbolic residual and executable trace metadata; rule=solve the component force balance for F_x\n\nSymPy library grounding:\n- grounding_level: high\n- calculus: grounded; APIs=sympy.core.function.diff, sympy.integrals.integrals.integrate, sympy.core.function.Derivative, sympy.integrals.integrals.Integral\n- mechanics: grounded; APIs=sympy.physics.mechanics.particle.Particle, sympy.physics.mechanics.functions.dynamicsymbols, sympy.physics.mechanics.lagrange.LagrangesMethod\n- numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy\n- scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand\n- solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp\n- units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify\n- vector_analysis: grounded; APIs=sympy.vector.coordsysrect.CoordSys3D, sympy.vector.operators.gradient, sympy.vector.operators.divergence, sympy.vector.operators.curl"

# Source-alignment packet: preserves the original task and the exact formal
# target represented by this artifact.
CLAIM = {
    "backend": "sympy",
    "style": "sympy_physics_derivation_trace",
    "case_id": CASE_ID,
    "statement_nl": "Use the Euler-Lagrange x equation for a minimally coupled charged particle to obtain the force-balance component after cancelling the common Ax_x xdot term.",
    "statement_latex": "F_x+q(A_{x,t}+A_{x,y}\\dot y+A_{x,z}\\dot z)=q(A_{y,x}\\dot y+A_{z,x}\\dot z)-q\\phi_x",
    "source_anchors": ["src_L0004", "src_L0009"],
    "commentary_header": COMMENTARY_HEADER,
}

# Structured source/task context. These are intentionally data, not comments,
# so validators and documentation generators can inspect them.
QUANTITY_TABLE = case_spec(CASE_ID)["quantities"]
DIMENSION_MODEL = {
    symbol: {"dimension_name": data[1], "unit": data[2]}
    for symbol, data in case_spec(CASE_ID)["quantities"].items()
}
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
    return {
        symbol: data[2] for symbol, data in case_spec(CASE_ID)["quantities"].items()
    }


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
    return {
        "passed": ASSUMPTION_CONTEXT["status"] == "pass",
        "packet": ASSUMPTION_CONTEXT,
    }


def validate_projection_bridges():
    """Check scalar projection bridges for vector, field, or frame reductions."""
    return {
        "passed": all(
            bridge.get("status") in {"provided", "pass", "ready", "required"}
            for bridge in PROJECTION_BRIDGES
        ),
        "projection_bridges": PROJECTION_BRIDGES,
    }


def validate_no_hidden_target():
    """Check that target equations are not hidden as source inputs."""
    target_like_sources = [
        node
        for node in EQUATION_GRAPH["nodes"]
        if node.get("role") in {"source", "input"}
        and node.get("support") != "source_backed"
        and ("target" in str(node).lower() or "answer" in str(node).lower())
    ]
    return {
        "passed": not target_like_sources,
        "target_like_sources": target_like_sources,
    }


def validate_law_usage():
    """Check that physical law usage is visible in the law table."""
    return {
        "passed": bool(LAW_TABLE),
        "law_count": len(LAW_TABLE),
        "law_table": LAW_TABLE,
    }


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
        enriched_steps.append(
            {
                **step,
                "input": previous,
                "output": step["expression"],
                "justification": step["rule"],
                "api": "sympy.solve/simplify/expand plus case-specific physics bridge metadata",
            }
        )
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
# Case: formalphysics_0172
# Claim (NL): Use the Euler-Lagrange x equation for a minimally coupled charged particle to obtain the force-balance component after cancelling the common Ax_x xdot term.
# Claim (LaTeX): F_x+q(A_{x,t}+A_{x,y}\dot y+A_{x,z}\dot z)=q(A_{y,x}\dot y+A_{z,x}\dot z)-q\phi_x
# Target key: euler_lagrange_x_force_balance
#
# Quantities:
# - mddx: mass times x acceleration; dimension=force; unit=newton
# - Fx: x component of force; dimension=force; unit=newton
# - q_Axt: charge times time derivative of A_x; dimension=force; unit=newton
# - q_Axy_ydot: charge times A_x,y times y velocity; dimension=force; unit=newton
# - q_Axz_zdot: charge times A_x,z times z velocity; dimension=force; unit=newton
# - q_Ayx_ydot: charge times A_y,x times y velocity; dimension=force; unit=newton
# - q_Azx_zdot: charge times A_z,x times z velocity; dimension=force; unit=newton
# - q_phix: charge times scalar-potential x derivative; dimension=force; unit=newton
#
# Context assumptions:
# - fixed Cartesian coordinate frame
# - source Euler-Lagrange x equation is valid
# - F_x=m xddot
# - common A_x,x xdot terms cancel on both sides
# - potentials are differentiable
#
# Physical laws and source rules:
# - Euler-Lagrange equation for minimally coupled charged-particle Lagrangian
# - force definition F_x=m xddot
# - coordinate component projection of the Lagrangian force balance
#
# Projection/operator bridges:
# - formalphysics_0172.coordinate_component_bridge: coordinate_component_bridge [provided]; source=Euler-Lagrange vector force balance; targets=formalphysics_0172.target
#
# Derivation steps:
# 1. step_01_euler_lagrange_after_common_term_cancellation [source_equation]
#    expression: Eq(mddx + q_Axt + q_Axy_ydot + q_Axz_zdot, q_Ayx_ydot + q_Azx_zdot - q_phix)
#    rule: Euler-Lagrange x equation after cancelling the common A_x,x xdot term
#    support: source equation; generated=False; source_anchors=src_L0004, src_L0009
# 2. step_02_substitute_force_definition [source_substitution]
#    expression: Eq(Fx + q_Axt + q_Axy_ydot + q_Axz_zdot, q_Ayx_ydot + q_Azx_zdot - q_phix)
#    rule: substitute F_x=m xddot
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 3. step_03_solve_force_balance_for_Fx [target_equation]
#    expression: -q_Axt - q_Axy_ydot - q_Axz_zdot + q_Ayx_ydot + q_Azx_zdot - q_phix
#    rule: solve the component force balance for F_x
#    support: source target; generated=False; source_anchors=src_L0004, src_L0009
#
# Computed expressions:
# - target_expression: -q_Axt - q_Axy_ydot - q_Axz_zdot + q_Ayx_ydot + q_Azx_zdot - q_phix
# - expected/source_expression: -q_Axt - q_Axy_ydot - q_Axz_zdot + q_Ayx_ydot + q_Azx_zdot - q_phix
# - residual target_minus_expected: 0
#
# Validation print:
# - symbolic_target_verified: True
# - derivation_steps_passed: True
# - dimensionally_consistent: True
# - numeric_sample_passed: True
# - numeric_sample: mddx=41, Fx=41, q_Axt=3, q_Axy_ydot=5, q_Axz_zdot=7, q_Ayx_ydot=23, q_Azx_zdot=31, q_phix=2
# - numeric_target_value: 37.0
# - numeric_expected_value: 37.0
#
# Equivalence certificates:
# - step_01_euler_lagrange_after_common_term_cancellation: passed=True; certificate=symbolic residual and executable trace metadata; rule=Euler-Lagrange x equation after cancelling the common A_x,x xdot term
# - step_02_substitute_force_definition: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute F_x=m xddot
# - step_03_solve_force_balance_for_Fx: passed=True; certificate=symbolic residual and executable trace metadata; rule=solve the component force balance for F_x
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
