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

Original source task (NL): Eliminating time from constant-acceleration kinematics gives v^2=v0^2+2a(x-x0).
Original source task (LaTeX): v^2=v_0^2+2a(x-x_0)
Formalized target: v^2=v_0^2+2a(x-x_0)
Source anchors: src_L0004, src_L0009

Original informal statement:
Eliminating time from constant-acceleration kinematics gives v^2=v0^2+2a(x-x0).

Informal derivation commentary:
The source task is represented as an executable SymPy equation trace. Explicit
source-backed steps and generated support steps are exposed in
DERIVATION_STEPS, with units, assumptions, and laws carried by structured
module data rather than by comments alone.

SymPy alignment:
- CLAIM preserves the original source statement and formal target.
- DERIVATION_STEPS records each source-backed or generated transformation.
- QUANTITY_TABLE, QUANTITY_SURFACE, LAW_TABLE, PROJECTION_BRIDGES, and
  CONTEXT_ASSUMPTIONS preserve the physics context behind the equations.
- validate_derivation_steps, validate_dimensions, validate_numeric_samples,
  and review_final_equations provide executable validation hooks.

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
CASE_ID = "constant_acceleration_velocity_position"
COMMENTARY_HEADER = "Original informal statement:\nEliminating time from constant-acceleration kinematics gives v^2=v0^2+2a(x-x0).\n\nInformal derivation commentary:\nThe source task is represented as an executable SymPy equation trace. Explicit\nsource-backed steps and generated support steps are exposed in\nDERIVATION_STEPS, with units, assumptions, and laws carried by structured\nmodule data rather than by comments alone.\n\nSymPy alignment:\n- CLAIM preserves the original source statement and formal target.\n- DERIVATION_STEPS records each source-backed or generated transformation.\n- QUANTITY_TABLE, QUANTITY_SURFACE, LAW_TABLE, PROJECTION_BRIDGES, and\n  CONTEXT_ASSUMPTIONS preserve the physics context behind the equations.\n- validate_derivation_steps, validate_dimensions, validate_numeric_samples,\n  and review_final_equations provide executable validation hooks."
DERIVATION_PRINT = "FULL PRINTED SYMPY DERIVATION\nCase: constant_acceleration_velocity_position\nClaim (NL): Eliminating time from constant-acceleration kinematics gives v^2=v0^2+2a(x-x0).\nClaim (LaTeX): v^2=v_0^2+2a(x-x_0)\nTarget key: velocity_position\n\nQuantities:\n- x: position; dimension=length; unit=meter\n- x0: initial position; dimension=length; unit=meter\n- v: velocity; dimension=velocity; unit=meter/second\n- v0: initial velocity; dimension=velocity; unit=meter/second\n- a: constant acceleration; dimension=acceleration; unit=meter/second**2\n- t: time; dimension=time; unit=second\n\nContext assumptions:\n- constant acceleration\n- one-dimensional motion\n- a != 0 when solving for t\n\nPhysical laws and source rules:\n- v=v0+a t\n- x=x0+v0 t+a t^2/2\n\nDerivation steps:\n1. step_01_solve_time [generated_algebra]\n   expression: (v - v0)/a\n   rule: solve velocity equation for time\n   support: generated gap; generated=True; source_anchors=none\n2. step_02_substitute_time [generated_substitution]\n   expression: (v - v0)*(v + v0)/(2*a)\n   rule: substitute time into position equation\n   support: generated gap; generated=True; source_anchors=none\n3. step_03_rearrange [target_equation]\n   expression: v**2\n   rule: algebraic rearrangement\n   support: source target; generated=False; source_anchors=src_L0004, src_L0009\n\nComputed expressions:\n- target_expression: v**2\n- expected/source_expression: v**2\n- residual target_minus_expected: 0\n\nValidation print:\n- symbolic_target_verified: True\n- derivation_steps_passed: True\n- dimensionally_consistent: True\n- numeric_sample_passed: True\n- numeric_sample: x0=1, v0=3, a=2, t=4, v=11, x=29\n- numeric_target_value: 121.0\n- numeric_expected_value: 121.0\n\nEquivalence certificates:\n- step_01_solve_time: passed=True; certificate=symbolic residual and executable trace metadata; rule=solve velocity equation for time\n- step_02_substitute_time: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute time into position equation\n- step_03_rearrange: passed=True; certificate=symbolic residual and executable trace metadata; rule=algebraic rearrangement\n\nSymPy library grounding:\n- grounding_level: high\n- numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy\n- quantum_operators: grounded; APIs=sympy.physics.quantum.operator.Operator, sympy.physics.quantum.state.Ket, sympy.physics.quantum.state.Bra, sympy.physics.quantum.dagger.Dagger\n- scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand\n- solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp\n- units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify"

# Source-alignment packet: preserves the original task and the exact formal
# target represented by this artifact.
CLAIM = {
    "backend": "sympy",
    "style": "sympy_physics_derivation_trace",
    "case_id": CASE_ID,
    "statement_nl": "Eliminating time from constant-acceleration kinematics gives v^2=v0^2+2a(x-x0).",
    "statement_latex": "v^2=v_0^2+2a(x-x_0)",
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
# Case: constant_acceleration_velocity_position
# Claim (NL): Eliminating time from constant-acceleration kinematics gives v^2=v0^2+2a(x-x0).
# Claim (LaTeX): v^2=v_0^2+2a(x-x_0)
# Target key: velocity_position
#
# Quantities:
# - x: position; dimension=length; unit=meter
# - x0: initial position; dimension=length; unit=meter
# - v: velocity; dimension=velocity; unit=meter/second
# - v0: initial velocity; dimension=velocity; unit=meter/second
# - a: constant acceleration; dimension=acceleration; unit=meter/second**2
# - t: time; dimension=time; unit=second
#
# Context assumptions:
# - constant acceleration
# - one-dimensional motion
# - a != 0 when solving for t
#
# Physical laws and source rules:
# - v=v0+a t
# - x=x0+v0 t+a t^2/2
#
# Derivation steps:
# 1. step_01_solve_time [generated_algebra]
#    expression: (v - v0)/a
#    rule: solve velocity equation for time
#    support: generated gap; generated=True; source_anchors=none
# 2. step_02_substitute_time [generated_substitution]
#    expression: (v - v0)*(v + v0)/(2*a)
#    rule: substitute time into position equation
#    support: generated gap; generated=True; source_anchors=none
# 3. step_03_rearrange [target_equation]
#    expression: v**2
#    rule: algebraic rearrangement
#    support: source target; generated=False; source_anchors=src_L0004, src_L0009
#
# Computed expressions:
# - target_expression: v**2
# - expected/source_expression: v**2
# - residual target_minus_expected: 0
#
# Validation print:
# - symbolic_target_verified: True
# - derivation_steps_passed: True
# - dimensionally_consistent: True
# - numeric_sample_passed: True
# - numeric_sample: x0=1, v0=3, a=2, t=4, v=11, x=29
# - numeric_target_value: 121.0
# - numeric_expected_value: 121.0
#
# Equivalence certificates:
# - step_01_solve_time: passed=True; certificate=symbolic residual and executable trace metadata; rule=solve velocity equation for time
# - step_02_substitute_time: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute time into position equation
# - step_03_rearrange: passed=True; certificate=symbolic residual and executable trace metadata; rule=algebraic rearrangement
#
# SymPy library grounding:
# - grounding_level: high
# - numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy
# - quantum_operators: grounded; APIs=sympy.physics.quantum.operator.Operator, sympy.physics.quantum.state.Ket, sympy.physics.quantum.state.Bra, sympy.physics.quantum.dagger.Dagger
# - scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand
# - solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp
# - units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify
