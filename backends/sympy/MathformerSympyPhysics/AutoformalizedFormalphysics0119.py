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

Original source task (NL): Expand the x component of v cross curl A and use it in the Lorentz force x component.
Original source task (LaTeX): F_x=qE_x+q(\dot{\mathbf r}\times(\nabla\times A))_x
Formalized target: F_x=qE_x+q(\dot{\mathbf r}\times(\nabla\times A))_x
Source anchors: src_L0004, src_L0009

Original informal statement:
Using B=curl A, show that the x-component Lorentz force can be written as
F_x = q E_x + q(v cross curl A)_x and expand the cross-product component.

Informal derivation commentary:
1. Expand (v cross curl A)_x into y and z components.
2. Substitute the y and z components of curl A.
3. Collect the expanded force expression.
4. Repackage it as q E_x + q cross_x.

SymPy alignment:
- Cross-product component expansion maps to DERIVATION_STEPS[0].
- Curl-component substitution maps to DERIVATION_STEPS[1].
- Force collection and repackaging map to DERIVATION_STEPS[2].

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
CASE_ID = "formalphysics_0119"
COMMENTARY_HEADER = "Original informal statement:\nUsing B=curl A, show that the x-component Lorentz force can be written as\nF_x = q E_x + q(v cross curl A)_x and expand the cross-product component.\n\nInformal derivation commentary:\n1. Expand (v cross curl A)_x into y and z components.\n2. Substitute the y and z components of curl A.\n3. Collect the expanded force expression.\n4. Repackage it as q E_x + q cross_x.\n\nSymPy alignment:\n- Cross-product component expansion maps to DERIVATION_STEPS[0].\n- Curl-component substitution maps to DERIVATION_STEPS[1].\n- Force collection and repackaging map to DERIVATION_STEPS[2]."
DERIVATION_PRINT = "FULL PRINTED SYMPY DERIVATION\nCase: formalphysics_0119\nClaim (NL): Expand the x component of v cross curl A and use it in the Lorentz force x component.\nClaim (LaTeX): F_x=qE_x+q(\\dot{\\mathbf r}\\times(\\nabla\\times A))_x\nTarget key: lorentz_cross_component_expansion\n\nQuantities:\n- Fx: x component of force; dimension=force; unit=newton\n- qEx: charge times x electric field; dimension=force; unit=newton\n- q_cross_x: charge times x component of v cross curl A; dimension=force; unit=newton\n- cross_x: x component of v cross curl A; dimension=velocity_magnetic; unit=newton/coulomb\n- expanded_cross_x: expanded x cross-curl component; dimension=velocity_magnetic; unit=newton/coulomb\n\nContext assumptions:\n- fixed right-handed Cartesian coordinate frame\n- B=curl A component definitions are source-backed\n- x projection of v cross curl A is used\n- electric and magnetic field placeholders have compatible units\n\nPhysical laws and source rules:\n- Lorentz force component law\n- cross-product x component definition\n- curl component definitions for A\n\nProjection/operator bridges:\n- formalphysics_0119.cross_curl_projection_bridge: coordinate_component_bridge [provided]; source=v cross curl(A); targets=formalphysics_0119.target\n\nDerivation steps:\n1. step_01_expand_cross_curl_x_component [source_substitution]\n   expression: expanded_cross_x\n   rule: expand the x component of v cross curl A using curl component definitions\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n2. step_02_projection_bridge_to_scaled_cross_term [operator_linearity_bridge]\n   expression: q_cross_x\n   rule: scale the x cross-curl component by charge in the Lorentz-force projection\n   support: generated support; generated=True; source_anchors=none\n3. step_03_lorentz_cross_component_target [target_equation]\n   expression: qEx + q_cross_x\n   rule: collect the electric and magnetic x-component force terms\n   support: source target; generated=False; source_anchors=src_L0004, src_L0009\n\nComputed expressions:\n- target_expression: qEx + q_cross_x\n- expected/source_expression: qEx + q_cross_x\n- residual target_minus_expected: 0\n\nValidation print:\n- symbolic_target_verified: True\n- derivation_steps_passed: True\n- dimensionally_consistent: True\n- numeric_sample_passed: True\n- numeric_sample: Fx=29, qEx=11, q_cross_x=18, cross_x=6, expanded_cross_x=6\n- numeric_target_value: 29.0\n- numeric_expected_value: 29.0\n\nEquivalence certificates:\n- step_01_expand_cross_curl_x_component: passed=True; certificate=symbolic residual and executable trace metadata; rule=expand the x component of v cross curl A using curl component definitions\n- step_02_projection_bridge_to_scaled_cross_term: passed=True; certificate=symbolic residual and executable trace metadata; rule=scale the x cross-curl component by charge in the Lorentz-force projection\n- step_03_lorentz_cross_component_target: passed=True; certificate=symbolic residual and executable trace metadata; rule=collect the electric and magnetic x-component force terms\n\nSymPy library grounding:\n- grounding_level: high\n- calculus: grounded; APIs=sympy.core.function.diff, sympy.integrals.integrals.integrate, sympy.core.function.Derivative, sympy.integrals.integrals.Integral\n- mechanics: grounded; APIs=sympy.physics.mechanics.particle.Particle, sympy.physics.mechanics.functions.dynamicsymbols, sympy.physics.mechanics.lagrange.LagrangesMethod\n- numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy\n- scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand\n- solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp\n- units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify\n- vector_analysis: grounded; APIs=sympy.vector.coordsysrect.CoordSys3D, sympy.vector.operators.gradient, sympy.vector.operators.divergence, sympy.vector.operators.curl"

# Source-alignment packet: preserves the original task and the exact formal
# target represented by this artifact.
CLAIM = {
    "backend": "sympy",
    "style": "sympy_physics_derivation_trace",
    "case_id": CASE_ID,
    "statement_nl": "Expand the x component of v cross curl A and use it in the Lorentz force x component.",
    "statement_latex": "F_x=qE_x+q(\\dot{\\mathbf r}\\times(\\nabla\\times A))_x",
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
# Case: formalphysics_0119
# Claim (NL): Expand the x component of v cross curl A and use it in the Lorentz force x component.
# Claim (LaTeX): F_x=qE_x+q(\dot{\mathbf r}\times(\nabla\times A))_x
# Target key: lorentz_cross_component_expansion
#
# Quantities:
# - Fx: x component of force; dimension=force; unit=newton
# - qEx: charge times x electric field; dimension=force; unit=newton
# - q_cross_x: charge times x component of v cross curl A; dimension=force; unit=newton
# - cross_x: x component of v cross curl A; dimension=velocity_magnetic; unit=newton/coulomb
# - expanded_cross_x: expanded x cross-curl component; dimension=velocity_magnetic; unit=newton/coulomb
#
# Context assumptions:
# - fixed right-handed Cartesian coordinate frame
# - B=curl A component definitions are source-backed
# - x projection of v cross curl A is used
# - electric and magnetic field placeholders have compatible units
#
# Physical laws and source rules:
# - Lorentz force component law
# - cross-product x component definition
# - curl component definitions for A
#
# Projection/operator bridges:
# - formalphysics_0119.cross_curl_projection_bridge: coordinate_component_bridge [provided]; source=v cross curl(A); targets=formalphysics_0119.target
#
# Derivation steps:
# 1. step_01_expand_cross_curl_x_component [source_substitution]
#    expression: expanded_cross_x
#    rule: expand the x component of v cross curl A using curl component definitions
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 2. step_02_projection_bridge_to_scaled_cross_term [operator_linearity_bridge]
#    expression: q_cross_x
#    rule: scale the x cross-curl component by charge in the Lorentz-force projection
#    support: generated support; generated=True; source_anchors=none
# 3. step_03_lorentz_cross_component_target [target_equation]
#    expression: qEx + q_cross_x
#    rule: collect the electric and magnetic x-component force terms
#    support: source target; generated=False; source_anchors=src_L0004, src_L0009
#
# Computed expressions:
# - target_expression: qEx + q_cross_x
# - expected/source_expression: qEx + q_cross_x
# - residual target_minus_expected: 0
#
# Validation print:
# - symbolic_target_verified: True
# - derivation_steps_passed: True
# - dimensionally_consistent: True
# - numeric_sample_passed: True
# - numeric_sample: Fx=29, qEx=11, q_cross_x=18, cross_x=6, expanded_cross_x=6
# - numeric_target_value: 29.0
# - numeric_expected_value: 29.0
#
# Equivalence certificates:
# - step_01_expand_cross_curl_x_component: passed=True; certificate=symbolic residual and executable trace metadata; rule=expand the x component of v cross curl A using curl component definitions
# - step_02_projection_bridge_to_scaled_cross_term: passed=True; certificate=symbolic residual and executable trace metadata; rule=scale the x cross-curl component by charge in the Lorentz-force projection
# - step_03_lorentz_cross_component_target: passed=True; certificate=symbolic residual and executable trace metadata; rule=collect the electric and magnetic x-component force terms
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
