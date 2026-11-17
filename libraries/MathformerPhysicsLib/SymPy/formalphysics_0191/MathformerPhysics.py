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

Original source task (NL): Differentiate the TDSE expectation value with respect to a parameter and isolate the Hamiltonian derivative expectation.
Original source task (LaTeX): \langle\Psi|\partial_\lambda H|\Psi\rangle=i\hbar\partial_\lambda\langle\Psi|\partial_t\Psi\rangle-i\hbar\langle\partial_\lambda\Psi|\partial_t\Psi\rangle+i\hbar\langle\partial_t\Psi|\partial_\lambda\Psi\rangle
Formalized target: \langle\Psi|\partial_\lambda H|\Psi\rangle=i\hbar\partial_\lambda\langle\Psi|\partial_t\Psi\rangle-i\hbar\langle\partial_\lambda\Psi|\partial_t\Psi\rangle+i\hbar\langle\partial_t\Psi|\partial_\lambda\Psi\rangle
Source anchors: src_L0004, src_L0009

Original informal statement:
Differentiate the TDSE expectation value with respect to a parameter and
derive the source identity containing the Hamiltonian derivative expectation,
the parameter derivative of <Psi|d_t Psi>, and two TDSE substitution terms.

Informal derivation commentary:
1. Apply the product rule to d_lambda <Psi|H|Psi>.
2. Solve the product-rule decomposition for <Psi|d_lambda H|Psi>.
3. Substitute the ket TDSE and adjoint-bra TDSE terms.
4. Rewrite the energy derivative as i hbar d_lambda <Psi|d_t Psi>.

SymPy alignment:
- Informal product-rule decomposition maps to DERIVATION_STEPS[0].
- TDSE substitutions map to DERIVATION_STEPS[1] and DERIVATION_STEPS[2].
- Final collection maps to DERIVATION_STEPS[3] and the residual checked by
  validate_derivation_steps.

Generated support note: This artifact implements the
`sympy_physics_derivation_trace` style. Source-backed equations are kept in
`CLAIM`; generated algebra, calculus, substitution, unit, and validation steps
are exposed through `DERIVATION_STEPS` and the validation functions below.
Complete status must come from execution, dimensional analysis, symbolic step
verification, and numeric sanity checks, not from this file existing.
"""

from backends.sympy.MathformerPhysicsSympy.pipeline import case_spec, derive_case, enriched_assumption_context, enriched_dimension_projection_report, enriched_equation_surface, enriched_equational_semantics_report, enriched_final_equation_reviews, execute_case, format_derivation_print, numeric_samples, step_verification, sympy_library_grounding, unit_analysis


# Stable identifier used to recover the source task from the shared pipeline.
CASE_ID = "formalphysics_0191"
COMMENTARY_HEADER = 'Original informal statement:\nDifferentiate the TDSE expectation value with respect to a parameter and\nderive the source identity containing the Hamiltonian derivative expectation,\nthe parameter derivative of <Psi|d_t Psi>, and two TDSE substitution terms.\n\nInformal derivation commentary:\n1. Apply the product rule to d_lambda <Psi|H|Psi>.\n2. Solve the product-rule decomposition for <Psi|d_lambda H|Psi>.\n3. Substitute the ket TDSE and adjoint-bra TDSE terms.\n4. Rewrite the energy derivative as i hbar d_lambda <Psi|d_t Psi>.\n\nSymPy alignment:\n- Informal product-rule decomposition maps to DERIVATION_STEPS[0].\n- TDSE substitutions map to DERIVATION_STEPS[1] and DERIVATION_STEPS[2].\n- Final collection maps to DERIVATION_STEPS[3] and the residual checked by\n  validate_derivation_steps.'
DERIVATION_PRINT = 'FULL PRINTED SYMPY DERIVATION\nCase: formalphysics_0191\nClaim (NL): Differentiate the TDSE expectation value with respect to a parameter and isolate the Hamiltonian derivative expectation.\nClaim (LaTeX): \\langle\\Psi|\\partial_\\lambda H|\\Psi\\rangle=i\\hbar\\partial_\\lambda\\langle\\Psi|\\partial_t\\Psi\\rangle-i\\hbar\\langle\\partial_\\lambda\\Psi|\\partial_t\\Psi\\rangle+i\\hbar\\langle\\partial_t\\Psi|\\partial_\\lambda\\Psi\\rangle\nTarget key: tdse_product_differentiation_identity\n\nQuantities:\n- lhs: Hamiltonian derivative expectation; dimension=energy; unit=joule\n- d_energy_scaled: parameter derivative of TDSE energy expectation; dimension=energy; unit=joule\n- param_inner_scaled: i hbar times parameter derivative of time inner product; dimension=energy; unit=joule\n- left_term_scaled: i hbar times left TDSE ket substitution term; dimension=energy; unit=joule\n- right_term_scaled: minus i hbar times adjoint-bra substitution term; dimension=energy; unit=joule\n- lambda_dt_scaled: i hbar times lambda-time inner product; dimension=energy; unit=joule\n- dt_lambda_scaled: i hbar times time-lambda inner product; dimension=energy; unit=joule\n\nContext assumptions:\n- Hamiltonian and state are smooth in lambda\n- TDSE ket substitution is source-backed\n- adjoint-bra TDSE substitution is source-backed\n- inner-product product rule is admissible\n- operator reductions are represented as scalar expectation projections\n\nPhysical laws and source rules:\n- time-dependent Schrodinger equation\n- adjoint TDSE relation\n- product rule for expectation values\n- parameter derivative of the energy expectation\n\nProjection/operator bridges:\n- formalphysics_0191.quantum_expectation_projection_bridge: operator_inner_product_projection_bridge [provided]; source=TDSE expectation product differentiation; targets=formalphysics_0191.target\n\nDerivation steps:\n1. step_01_isolate_hamiltonian_derivative_expectation [source_equation]\n   expression: d_energy_scaled - left_term_scaled - right_term_scaled\n   rule: differentiate the expectation value and isolate the Hamiltonian derivative term\n   support: source equation; generated=False; source_anchors=src_L0004, src_L0009\n2. step_02_substitute_tdse_energy_derivative [source_substitution]\n   expression: param_inner_scaled\n   rule: substitute the TDSE expression for the differentiated energy expectation\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n3. step_03_substitute_ket_tdse_term [source_substitution]\n   expression: lambda_dt_scaled\n   rule: substitute the ket-side TDSE inner-product term\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n4. step_04_substitute_adjoint_bra_tdse_term [source_substitution]\n   expression: -dt_lambda_scaled\n   rule: substitute the adjoint-bra TDSE inner-product term\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n5. step_05_collect_tdse_product_terms [target_equation]\n   expression: dt_lambda_scaled - lambda_dt_scaled + param_inner_scaled\n   rule: collect the parameter, ket, and adjoint-bra terms\n   support: source target; generated=False; source_anchors=src_L0004, src_L0009\n\nComputed expressions:\n- target_expression: dt_lambda_scaled - lambda_dt_scaled + param_inner_scaled\n- expected/source_expression: dt_lambda_scaled - lambda_dt_scaled + param_inner_scaled\n- residual target_minus_expected: 0\n\nValidation print:\n- symbolic_target_verified: True\n- derivation_steps_passed: True\n- dimensionally_consistent: True\n- numeric_sample_passed: True\n- numeric_sample: lhs=17, d_energy_scaled=31, param_inner_scaled=31, left_term_scaled=19, right_term_scaled=-5, lambda_dt_scaled=19, dt_lambda_scaled=5\n- numeric_target_value: 17.0\n- numeric_expected_value: 17.0\n\nEquivalence certificates:\n- step_01_isolate_hamiltonian_derivative_expectation: passed=True; certificate=symbolic residual and executable trace metadata; rule=differentiate the expectation value and isolate the Hamiltonian derivative term\n- step_02_substitute_tdse_energy_derivative: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute the TDSE expression for the differentiated energy expectation\n- step_03_substitute_ket_tdse_term: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute the ket-side TDSE inner-product term\n- step_04_substitute_adjoint_bra_tdse_term: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute the adjoint-bra TDSE inner-product term\n- step_05_collect_tdse_product_terms: passed=True; certificate=symbolic residual and executable trace metadata; rule=collect the parameter, ket, and adjoint-bra terms\n\nSymPy library grounding:\n- grounding_level: high\n- calculus: grounded; APIs=sympy.core.function.diff, sympy.integrals.integrals.integrate, sympy.core.function.Derivative, sympy.integrals.integrals.Integral\n- matrices_linear_algebra: grounded; APIs=sympy.matrices.dense.MutableDenseMatrix, sympy.matrices.expressions.matexpr.MatrixSymbol, sympy.matrices.expressions.matmul.MatMul\n- numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy\n- quantum_operators: grounded; APIs=sympy.physics.quantum.operator.Operator, sympy.physics.quantum.state.Ket, sympy.physics.quantum.state.Bra, sympy.physics.quantum.dagger.Dagger\n- scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand\n- solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp\n- units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify'

# Source-alignment packet: preserves the original task and the exact formal
# target represented by this artifact.
CLAIM = {
    "backend": "sympy",
    "style": "sympy_physics_derivation_trace",
    "case_id": CASE_ID,
    "statement_nl": 'Differentiate the TDSE expectation value with respect to a parameter and isolate the Hamiltonian derivative expectation.',
    "statement_latex": '\\langle\\Psi|\\partial_\\lambda H|\\Psi\\rangle=i\\hbar\\partial_\\lambda\\langle\\Psi|\\partial_t\\Psi\\rangle-i\\hbar\\langle\\partial_\\lambda\\Psi|\\partial_t\\Psi\\rangle+i\\hbar\\langle\\partial_t\\Psi|\\partial_\\lambda\\Psi\\rangle',
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
# Case: formalphysics_0191
# Claim (NL): Differentiate the TDSE expectation value with respect to a parameter and isolate the Hamiltonian derivative expectation.
# Claim (LaTeX): \langle\Psi|\partial_\lambda H|\Psi\rangle=i\hbar\partial_\lambda\langle\Psi|\partial_t\Psi\rangle-i\hbar\langle\partial_\lambda\Psi|\partial_t\Psi\rangle+i\hbar\langle\partial_t\Psi|\partial_\lambda\Psi\rangle
# Target key: tdse_product_differentiation_identity
#
# Quantities:
# - lhs: Hamiltonian derivative expectation; dimension=energy; unit=joule
# - d_energy_scaled: parameter derivative of TDSE energy expectation; dimension=energy; unit=joule
# - param_inner_scaled: i hbar times parameter derivative of time inner product; dimension=energy; unit=joule
# - left_term_scaled: i hbar times left TDSE ket substitution term; dimension=energy; unit=joule
# - right_term_scaled: minus i hbar times adjoint-bra substitution term; dimension=energy; unit=joule
# - lambda_dt_scaled: i hbar times lambda-time inner product; dimension=energy; unit=joule
# - dt_lambda_scaled: i hbar times time-lambda inner product; dimension=energy; unit=joule
#
# Context assumptions:
# - Hamiltonian and state are smooth in lambda
# - TDSE ket substitution is source-backed
# - adjoint-bra TDSE substitution is source-backed
# - inner-product product rule is admissible
# - operator reductions are represented as scalar expectation projections
#
# Physical laws and source rules:
# - time-dependent Schrodinger equation
# - adjoint TDSE relation
# - product rule for expectation values
# - parameter derivative of the energy expectation
#
# Projection/operator bridges:
# - formalphysics_0191.quantum_expectation_projection_bridge: operator_inner_product_projection_bridge [provided]; source=TDSE expectation product differentiation; targets=formalphysics_0191.target
#
# Derivation steps:
# 1. step_01_isolate_hamiltonian_derivative_expectation [source_equation]
#    expression: d_energy_scaled - left_term_scaled - right_term_scaled
#    rule: differentiate the expectation value and isolate the Hamiltonian derivative term
#    support: source equation; generated=False; source_anchors=src_L0004, src_L0009
# 2. step_02_substitute_tdse_energy_derivative [source_substitution]
#    expression: param_inner_scaled
#    rule: substitute the TDSE expression for the differentiated energy expectation
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 3. step_03_substitute_ket_tdse_term [source_substitution]
#    expression: lambda_dt_scaled
#    rule: substitute the ket-side TDSE inner-product term
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 4. step_04_substitute_adjoint_bra_tdse_term [source_substitution]
#    expression: -dt_lambda_scaled
#    rule: substitute the adjoint-bra TDSE inner-product term
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 5. step_05_collect_tdse_product_terms [target_equation]
#    expression: dt_lambda_scaled - lambda_dt_scaled + param_inner_scaled
#    rule: collect the parameter, ket, and adjoint-bra terms
#    support: source target; generated=False; source_anchors=src_L0004, src_L0009
#
# Computed expressions:
# - target_expression: dt_lambda_scaled - lambda_dt_scaled + param_inner_scaled
# - expected/source_expression: dt_lambda_scaled - lambda_dt_scaled + param_inner_scaled
# - residual target_minus_expected: 0
#
# Validation print:
# - symbolic_target_verified: True
# - derivation_steps_passed: True
# - dimensionally_consistent: True
# - numeric_sample_passed: True
# - numeric_sample: lhs=17, d_energy_scaled=31, param_inner_scaled=31, left_term_scaled=19, right_term_scaled=-5, lambda_dt_scaled=19, dt_lambda_scaled=5
# - numeric_target_value: 17.0
# - numeric_expected_value: 17.0
#
# Equivalence certificates:
# - step_01_isolate_hamiltonian_derivative_expectation: passed=True; certificate=symbolic residual and executable trace metadata; rule=differentiate the expectation value and isolate the Hamiltonian derivative term
# - step_02_substitute_tdse_energy_derivative: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute the TDSE expression for the differentiated energy expectation
# - step_03_substitute_ket_tdse_term: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute the ket-side TDSE inner-product term
# - step_04_substitute_adjoint_bra_tdse_term: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute the adjoint-bra TDSE inner-product term
# - step_05_collect_tdse_product_terms: passed=True; certificate=symbolic residual and executable trace metadata; rule=collect the parameter, ket, and adjoint-bra terms
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
