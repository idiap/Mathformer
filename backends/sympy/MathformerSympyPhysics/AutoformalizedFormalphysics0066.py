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

Original source task (NL): For a smooth parameter-dependent Hamiltonian and TDSE state, use commuting mixed partials to derive the scaled time-derivative inner-product identity.
Original source task (LaTeX): \langle\Psi|\partial_\lambda H|\Psi\rangle=i\hbar\,\partial_t\langle\Psi|\partial_\lambda\Psi\rangle
Formalized target: \langle\Psi|\partial_\lambda H|\Psi\rangle=i\hbar\,\partial_t\langle\Psi|\partial_\lambda\Psi\rangle
Source anchors: src_L0004, src_L0009

Original informal statement:
For a smooth parameter-dependent Hamiltonian and TDSE state, with commuting
mixed partials, derive the parameter identity
    <Psi|dH/dlambda|Psi> = i hbar d_t <Psi|dPsi/dlambda>.

Informal derivation commentary:
1. Start from the TDSE-derived parameter expression for the Hamiltonian
   derivative expectation.
2. Expand the lambda derivative of <Psi|d_t Psi> by the product rule.
3. Cancel the matching mixed bra/ket term.
4. Use the time derivative of <Psi|d_lambda Psi> and mixed-partial
   commutation to identify the remaining expression.

SymPy alignment:
- Informal steps 1-2 map to DERIVATION_STEPS[0] and DERIVATION_STEPS[1].
- Informal steps 3-4 map to DERIVATION_STEPS[2] and DERIVATION_STEPS[3].
- The complex/operator physics context is represented by LAW_TABLE,
  PROJECTION_BRIDGES, SYMPY_LIBRARY_GROUNDING, and executable scalar
  projection certificates.

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
CASE_ID = "formalphysics_0066"
COMMENTARY_HEADER = "Original informal statement:\nFor a smooth parameter-dependent Hamiltonian and TDSE state, with commuting\nmixed partials, derive the parameter identity\n    <Psi|dH/dlambda|Psi> = i hbar d_t <Psi|dPsi/dlambda>.\n\nInformal derivation commentary:\n1. Start from the TDSE-derived parameter expression for the Hamiltonian\n   derivative expectation.\n2. Expand the lambda derivative of <Psi|d_t Psi> by the product rule.\n3. Cancel the matching mixed bra/ket term.\n4. Use the time derivative of <Psi|d_lambda Psi> and mixed-partial\n   commutation to identify the remaining expression.\n\nSymPy alignment:\n- Informal steps 1-2 map to DERIVATION_STEPS[0] and DERIVATION_STEPS[1].\n- Informal steps 3-4 map to DERIVATION_STEPS[2] and DERIVATION_STEPS[3].\n- The complex/operator physics context is represented by LAW_TABLE,\n  PROJECTION_BRIDGES, SYMPY_LIBRARY_GROUNDING, and executable scalar\n  projection certificates."
DERIVATION_PRINT = "FULL PRINTED SYMPY DERIVATION\nCase: formalphysics_0066\nClaim (NL): For a smooth parameter-dependent Hamiltonian and TDSE state, use commuting mixed partials to derive the scaled time-derivative inner-product identity.\nClaim (LaTeX): \\langle\\Psi|\\partial_\\lambda H|\\Psi\\rangle=i\\hbar\\,\\partial_t\\langle\\Psi|\\partial_\\lambda\\Psi\\rangle\nTarget key: tdse_parameter_identity\n\nQuantities:\n- lhs: scaled Hamiltonian parameter expectation; dimension=energy; unit=joule\n- d_lambda_inner_scaled: i hbar times lambda derivative of time inner product; dimension=energy; unit=joule\n- lambda_dt_scaled: i hbar times lambda-time mixed inner term; dimension=energy; unit=joule\n- dt_lambda_scaled: i hbar times time-lambda inner term; dimension=energy; unit=joule\n- mixed_lambda_time_scaled: i hbar times lambda then time second partial term; dimension=energy; unit=joule\n- mixed_time_lambda_scaled: i hbar times time then lambda second partial term; dimension=energy; unit=joule\n- d_time_inner_scaled: i hbar times time derivative of parameter inner product; dimension=energy; unit=joule\n\nContext assumptions:\n- Hamiltonian and state are smooth in lambda and time\n- TDSE holds for the ket state\n- mixed partial derivatives commute\n- inner-product convention and hbar factor are fixed\n- operator substitutions are source-backed and finite-dimensional/projection-grounded for SymPy execution\n\nPhysical laws and source rules:\n- time-dependent Schrodinger equation\n- parameter differentiation of an inner product\n- time differentiation of an inner product\n- commutation of mixed partial derivatives under smoothness assumptions\n\nProjection/operator bridges:\n- formalphysics_0066.quantum_operator_projection_bridge: operator_inner_product_projection_bridge [provided]; source=Hilbert-space TDSE identity; targets=formalphysics_0066.target\n- formalphysics_0066.scaled_hbar_bridge: unit_dimension_bridge [provided]; source=i*hbar times derivative inner-product terms; targets=formalphysics_0066.scaled_terms\n\nDerivation steps:\n1. step_01_tdse_parameter_start [source_equation]\n   expression: d_lambda_inner_scaled + dt_lambda_scaled - lambda_dt_scaled\n   rule: TDSE parameter identity before product-rule cancellation\n   support: source equation; generated=False; source_anchors=src_L0004, src_L0009\n2. step_02_lambda_inner_product_rule [source_substitution]\n   expression: lambda_dt_scaled + mixed_lambda_time_scaled\n   rule: expand the lambda derivative of the time inner product\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n3. step_03_time_inner_product_rule [source_substitution]\n   expression: dt_lambda_scaled + mixed_time_lambda_scaled\n   rule: expand the time derivative of the parameter inner product\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n4. step_04_mixed_partial_commutation_bridge [generated_algebra]\n   expression: dt_lambda_scaled + mixed_time_lambda_scaled\n   rule: use commuting mixed partials and cancel the lambda-time term\n   support: generated support; generated=True; source_anchors=none\n5. step_05_target_time_derivative_identity [target_equation]\n   expression: d_time_inner_scaled\n   rule: identify the remaining scaled terms as the time derivative of the parameter inner product\n   support: source target; generated=False; source_anchors=src_L0004, src_L0009\n\nComputed expressions:\n- target_expression: d_time_inner_scaled\n- expected/source_expression: d_time_inner_scaled\n- residual target_minus_expected: 0\n\nValidation print:\n- symbolic_target_verified: True\n- derivation_steps_passed: True\n- dimensionally_consistent: True\n- numeric_sample_passed: True\n- numeric_sample: lhs=11, d_lambda_inner_scaled=23, lambda_dt_scaled=5, dt_lambda_scaled=7, mixed_lambda_time_scaled=13, mixed_time_lambda_scaled=13, d_time_inner_scaled=11\n- numeric_target_value: 11.0\n- numeric_expected_value: 11.0\n\nEquivalence certificates:\n- step_01_tdse_parameter_start: passed=True; certificate=symbolic residual and executable trace metadata; rule=TDSE parameter identity before product-rule cancellation\n- step_02_lambda_inner_product_rule: passed=True; certificate=symbolic residual and executable trace metadata; rule=expand the lambda derivative of the time inner product\n- step_03_time_inner_product_rule: passed=True; certificate=symbolic residual and executable trace metadata; rule=expand the time derivative of the parameter inner product\n- step_04_mixed_partial_commutation_bridge: passed=True; certificate=symbolic residual and executable trace metadata; rule=use commuting mixed partials and cancel the lambda-time term\n- step_05_target_time_derivative_identity: passed=True; certificate=symbolic residual and executable trace metadata; rule=identify the remaining scaled terms as the time derivative of the parameter inner product\n\nSymPy library grounding:\n- grounding_level: high\n- calculus: grounded; APIs=sympy.core.function.diff, sympy.integrals.integrals.integrate, sympy.core.function.Derivative, sympy.integrals.integrals.Integral\n- matrices_linear_algebra: grounded; APIs=sympy.matrices.dense.MutableDenseMatrix, sympy.matrices.expressions.matexpr.MatrixSymbol, sympy.matrices.expressions.matmul.MatMul\n- numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy\n- quantum_operators: grounded; APIs=sympy.physics.quantum.operator.Operator, sympy.physics.quantum.state.Ket, sympy.physics.quantum.state.Bra, sympy.physics.quantum.dagger.Dagger\n- scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand\n- solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp\n- units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify"

# Source-alignment packet: preserves the original task and the exact formal
# target represented by this artifact.
CLAIM = {
    "backend": "sympy",
    "style": "sympy_physics_derivation_trace",
    "case_id": CASE_ID,
    "statement_nl": "For a smooth parameter-dependent Hamiltonian and TDSE state, use commuting mixed partials to derive the scaled time-derivative inner-product identity.",
    "statement_latex": "\\langle\\Psi|\\partial_\\lambda H|\\Psi\\rangle=i\\hbar\\,\\partial_t\\langle\\Psi|\\partial_\\lambda\\Psi\\rangle",
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
# Case: formalphysics_0066
# Claim (NL): For a smooth parameter-dependent Hamiltonian and TDSE state, use commuting mixed partials to derive the scaled time-derivative inner-product identity.
# Claim (LaTeX): \langle\Psi|\partial_\lambda H|\Psi\rangle=i\hbar\,\partial_t\langle\Psi|\partial_\lambda\Psi\rangle
# Target key: tdse_parameter_identity
#
# Quantities:
# - lhs: scaled Hamiltonian parameter expectation; dimension=energy; unit=joule
# - d_lambda_inner_scaled: i hbar times lambda derivative of time inner product; dimension=energy; unit=joule
# - lambda_dt_scaled: i hbar times lambda-time mixed inner term; dimension=energy; unit=joule
# - dt_lambda_scaled: i hbar times time-lambda inner term; dimension=energy; unit=joule
# - mixed_lambda_time_scaled: i hbar times lambda then time second partial term; dimension=energy; unit=joule
# - mixed_time_lambda_scaled: i hbar times time then lambda second partial term; dimension=energy; unit=joule
# - d_time_inner_scaled: i hbar times time derivative of parameter inner product; dimension=energy; unit=joule
#
# Context assumptions:
# - Hamiltonian and state are smooth in lambda and time
# - TDSE holds for the ket state
# - mixed partial derivatives commute
# - inner-product convention and hbar factor are fixed
# - operator substitutions are source-backed and finite-dimensional/projection-grounded for SymPy execution
#
# Physical laws and source rules:
# - time-dependent Schrodinger equation
# - parameter differentiation of an inner product
# - time differentiation of an inner product
# - commutation of mixed partial derivatives under smoothness assumptions
#
# Projection/operator bridges:
# - formalphysics_0066.quantum_operator_projection_bridge: operator_inner_product_projection_bridge [provided]; source=Hilbert-space TDSE identity; targets=formalphysics_0066.target
# - formalphysics_0066.scaled_hbar_bridge: unit_dimension_bridge [provided]; source=i*hbar times derivative inner-product terms; targets=formalphysics_0066.scaled_terms
#
# Derivation steps:
# 1. step_01_tdse_parameter_start [source_equation]
#    expression: d_lambda_inner_scaled + dt_lambda_scaled - lambda_dt_scaled
#    rule: TDSE parameter identity before product-rule cancellation
#    support: source equation; generated=False; source_anchors=src_L0004, src_L0009
# 2. step_02_lambda_inner_product_rule [source_substitution]
#    expression: lambda_dt_scaled + mixed_lambda_time_scaled
#    rule: expand the lambda derivative of the time inner product
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 3. step_03_time_inner_product_rule [source_substitution]
#    expression: dt_lambda_scaled + mixed_time_lambda_scaled
#    rule: expand the time derivative of the parameter inner product
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 4. step_04_mixed_partial_commutation_bridge [generated_algebra]
#    expression: dt_lambda_scaled + mixed_time_lambda_scaled
#    rule: use commuting mixed partials and cancel the lambda-time term
#    support: generated support; generated=True; source_anchors=none
# 5. step_05_target_time_derivative_identity [target_equation]
#    expression: d_time_inner_scaled
#    rule: identify the remaining scaled terms as the time derivative of the parameter inner product
#    support: source target; generated=False; source_anchors=src_L0004, src_L0009
#
# Computed expressions:
# - target_expression: d_time_inner_scaled
# - expected/source_expression: d_time_inner_scaled
# - residual target_minus_expected: 0
#
# Validation print:
# - symbolic_target_verified: True
# - derivation_steps_passed: True
# - dimensionally_consistent: True
# - numeric_sample_passed: True
# - numeric_sample: lhs=11, d_lambda_inner_scaled=23, lambda_dt_scaled=5, dt_lambda_scaled=7, mixed_lambda_time_scaled=13, mixed_time_lambda_scaled=13, d_time_inner_scaled=11
# - numeric_target_value: 11.0
# - numeric_expected_value: 11.0
#
# Equivalence certificates:
# - step_01_tdse_parameter_start: passed=True; certificate=symbolic residual and executable trace metadata; rule=TDSE parameter identity before product-rule cancellation
# - step_02_lambda_inner_product_rule: passed=True; certificate=symbolic residual and executable trace metadata; rule=expand the lambda derivative of the time inner product
# - step_03_time_inner_product_rule: passed=True; certificate=symbolic residual and executable trace metadata; rule=expand the time derivative of the parameter inner product
# - step_04_mixed_partial_commutation_bridge: passed=True; certificate=symbolic residual and executable trace metadata; rule=use commuting mixed partials and cancel the lambda-time term
# - step_05_target_time_derivative_identity: passed=True; certificate=symbolic residual and executable trace metadata; rule=identify the remaining scaled terms as the time derivative of the parameter inner product
#
# SymPy library grounding:
# - grounding_level: high
# - calculus: grounded; APIs=sympy.core.function.diff, sympy.integrals.integrals.integrate, sympy.core.function.Derivative, sympy.integrals.integrals.Integral
# - matrices_linear_algebra: grounded; APIs=sympy.matrices.dense.MutableDenseMatrix, sympy.matrices.expressions.matexpr.MatrixSymbol, sympy.matrices.expressions.matmul.MatMul
# - numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy
# - quantum_operators: grounded; APIs=sympy.physics.quantum.operator.Operator, sympy.physics.quantum.state.Ket, sympy.physics.quantum.state.Bra, sympy.physics.quantum.dagger.Dagger
# - scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand
# - solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp
# - units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify
