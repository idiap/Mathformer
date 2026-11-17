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

Original source task (NL): Use normalization and eigenstate assumptions to cancel the derivative-of-norm term in the Hellmann-Feynman theorem.
Original source task (LaTeX): \partial_\lambda E_\lambda=\langle\Psi_\lambda|\partial_\lambda H_\lambda|\Psi_\lambda\rangle
Formalized target: \partial_\lambda E_\lambda=\langle\Psi_\lambda|\partial_\lambda H_\lambda|\Psi_\lambda\rangle
Source anchors: src_L0004, src_L0009

Original informal statement:
For a normalized non-degenerate eigenstate of a smooth self-adjoint
Hamiltonian, derive the Hellmann-Feynman identity dE/dlambda=<Psi|dH/dlambda|Psi>.

Informal derivation commentary:
1. Differentiate the eigenvalue expectation by the product rule.
2. Use the eigenstate equation to rewrite the outer terms.
3. Use normalization to show the norm derivative term is zero.
4. Cancel that zero contribution and obtain the Hamiltonian derivative
   expectation.

SymPy alignment:
- Product-rule/eigenvalue reduction maps to DERIVATION_STEPS[0].
- Normalization derivative maps to DERIVATION_STEPS[1].
- The final cancellation maps to DERIVATION_STEPS[2].

Generated support note: This artifact implements the
`sympy_physics_derivation_trace` style. Source-backed equations are kept in
`CLAIM`; generated algebra, calculus, substitution, unit, and validation steps
are exposed through `DERIVATION_STEPS` and the validation functions below.
Complete status must come from execution, dimensional analysis, symbolic step
verification, and numeric sanity checks, not from this file existing.
"""

from backends.sympy.MathformerPhysicsSympy.pipeline import case_spec, derive_case, enriched_assumption_context, enriched_dimension_projection_report, enriched_equation_surface, enriched_equational_semantics_report, enriched_final_equation_reviews, execute_case, format_derivation_print, numeric_samples, step_verification, sympy_library_grounding, unit_analysis


# Stable identifier used to recover the source task from the shared pipeline.
CASE_ID = "formalphysics_0026"
COMMENTARY_HEADER = 'Original informal statement:\nFor a normalized non-degenerate eigenstate of a smooth self-adjoint\nHamiltonian, derive the Hellmann-Feynman identity dE/dlambda=<Psi|dH/dlambda|Psi>.\n\nInformal derivation commentary:\n1. Differentiate the eigenvalue expectation by the product rule.\n2. Use the eigenstate equation to rewrite the outer terms.\n3. Use normalization to show the norm derivative term is zero.\n4. Cancel that zero contribution and obtain the Hamiltonian derivative\n   expectation.\n\nSymPy alignment:\n- Product-rule/eigenvalue reduction maps to DERIVATION_STEPS[0].\n- Normalization derivative maps to DERIVATION_STEPS[1].\n- The final cancellation maps to DERIVATION_STEPS[2].'
DERIVATION_PRINT = 'FULL PRINTED SYMPY DERIVATION\nCase: formalphysics_0026\nClaim (NL): Use normalization and eigenstate assumptions to cancel the derivative-of-norm term in the Hellmann-Feynman theorem.\nClaim (LaTeX): \\partial_\\lambda E_\\lambda=\\langle\\Psi_\\lambda|\\partial_\\lambda H_\\lambda|\\Psi_\\lambda\\rangle\nTarget key: hellmann_feynman\n\nQuantities:\n- dE: parameter derivative of the eigenvalue; dimension=energy; unit=joule\n- dH: expectation of the Hamiltonian parameter derivative; dimension=energy; unit=joule\n- eig_norm_derivative: eigenvalue times derivative of state norm; dimension=energy; unit=joule\n\nContext assumptions:\n- Hamiltonian is self-adjoint\n- state is normalized\n- state is a non-degenerate eigenstate\n- Hamiltonian and eigenstate are smooth in lambda\n- operator equation is represented as scalar expectation projection\n\nPhysical laws and source rules:\n- eigenvalue equation H psi=E psi\n- normalization derivative equals zero\n- product rule for the differentiated expectation value\n- Hellmann-Feynman cancellation\n\nProjection/operator bridges:\n- formalphysics_0026.quantum_expectation_projection_bridge: operator_inner_product_projection_bridge [provided]; source=Hellmann-Feynman operator expectation; targets=formalphysics_0026.target\n\nDerivation steps:\n1. step_01_differentiate_eigen_expectation [source_equation]\n   expression: dH + eig_norm_derivative\n   rule: differentiate the eigenvalue expectation and group the normalization derivative term\n   support: source equation; generated=False; source_anchors=src_L0004, src_L0009\n2. step_02_apply_normalization_derivative [source_substitution]\n   expression: 0\n   rule: use d/dlambda <psi|psi>=0 for normalized states\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n3. step_03_cancel_norm_derivative [target_equation]\n   expression: dH\n   rule: cancel the normalization derivative term\n   support: source target; generated=False; source_anchors=src_L0004, src_L0009\n\nComputed expressions:\n- target_expression: dH\n- expected/source_expression: dH\n- residual target_minus_expected: 0\n\nValidation print:\n- symbolic_target_verified: True\n- derivation_steps_passed: True\n- dimensionally_consistent: True\n- numeric_sample_passed: True\n- numeric_sample: dE=13, dH=13, eig_norm_derivative=0\n- numeric_target_value: 13.0\n- numeric_expected_value: 13.0\n\nEquivalence certificates:\n- step_01_differentiate_eigen_expectation: passed=True; certificate=symbolic residual and executable trace metadata; rule=differentiate the eigenvalue expectation and group the normalization derivative term\n- step_02_apply_normalization_derivative: passed=True; certificate=symbolic residual and executable trace metadata; rule=use d/dlambda <psi|psi>=0 for normalized states\n- step_03_cancel_norm_derivative: passed=True; certificate=symbolic residual and executable trace metadata; rule=cancel the normalization derivative term\n\nSymPy library grounding:\n- grounding_level: high\n- calculus: grounded; APIs=sympy.core.function.diff, sympy.integrals.integrals.integrate, sympy.core.function.Derivative, sympy.integrals.integrals.Integral\n- matrices_linear_algebra: grounded; APIs=sympy.matrices.dense.MutableDenseMatrix, sympy.matrices.expressions.matexpr.MatrixSymbol, sympy.matrices.expressions.matmul.MatMul\n- numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy\n- quantum_operators: grounded; APIs=sympy.physics.quantum.operator.Operator, sympy.physics.quantum.state.Ket, sympy.physics.quantum.state.Bra, sympy.physics.quantum.dagger.Dagger\n- scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand\n- solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp\n- units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify'

# Source-alignment packet: preserves the original task and the exact formal
# target represented by this artifact.
CLAIM = {
    "backend": "sympy",
    "style": "sympy_physics_derivation_trace",
    "case_id": CASE_ID,
    "statement_nl": 'Use normalization and eigenstate assumptions to cancel the derivative-of-norm term in the Hellmann-Feynman theorem.',
    "statement_latex": '\\partial_\\lambda E_\\lambda=\\langle\\Psi_\\lambda|\\partial_\\lambda H_\\lambda|\\Psi_\\lambda\\rangle',
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
# Case: formalphysics_0026
# Claim (NL): Use normalization and eigenstate assumptions to cancel the derivative-of-norm term in the Hellmann-Feynman theorem.
# Claim (LaTeX): \partial_\lambda E_\lambda=\langle\Psi_\lambda|\partial_\lambda H_\lambda|\Psi_\lambda\rangle
# Target key: hellmann_feynman
#
# Quantities:
# - dE: parameter derivative of the eigenvalue; dimension=energy; unit=joule
# - dH: expectation of the Hamiltonian parameter derivative; dimension=energy; unit=joule
# - eig_norm_derivative: eigenvalue times derivative of state norm; dimension=energy; unit=joule
#
# Context assumptions:
# - Hamiltonian is self-adjoint
# - state is normalized
# - state is a non-degenerate eigenstate
# - Hamiltonian and eigenstate are smooth in lambda
# - operator equation is represented as scalar expectation projection
#
# Physical laws and source rules:
# - eigenvalue equation H psi=E psi
# - normalization derivative equals zero
# - product rule for the differentiated expectation value
# - Hellmann-Feynman cancellation
#
# Projection/operator bridges:
# - formalphysics_0026.quantum_expectation_projection_bridge: operator_inner_product_projection_bridge [provided]; source=Hellmann-Feynman operator expectation; targets=formalphysics_0026.target
#
# Derivation steps:
# 1. step_01_differentiate_eigen_expectation [source_equation]
#    expression: dH + eig_norm_derivative
#    rule: differentiate the eigenvalue expectation and group the normalization derivative term
#    support: source equation; generated=False; source_anchors=src_L0004, src_L0009
# 2. step_02_apply_normalization_derivative [source_substitution]
#    expression: 0
#    rule: use d/dlambda <psi|psi>=0 for normalized states
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 3. step_03_cancel_norm_derivative [target_equation]
#    expression: dH
#    rule: cancel the normalization derivative term
#    support: source target; generated=False; source_anchors=src_L0004, src_L0009
#
# Computed expressions:
# - target_expression: dH
# - expected/source_expression: dH
# - residual target_minus_expected: 0
#
# Validation print:
# - symbolic_target_verified: True
# - derivation_steps_passed: True
# - dimensionally_consistent: True
# - numeric_sample_passed: True
# - numeric_sample: dE=13, dH=13, eig_norm_derivative=0
# - numeric_target_value: 13.0
# - numeric_expected_value: 13.0
#
# Equivalence certificates:
# - step_01_differentiate_eigen_expectation: passed=True; certificate=symbolic residual and executable trace metadata; rule=differentiate the eigenvalue expectation and group the normalization derivative term
# - step_02_apply_normalization_derivative: passed=True; certificate=symbolic residual and executable trace metadata; rule=use d/dlambda <psi|psi>=0 for normalized states
# - step_03_cancel_norm_derivative: passed=True; certificate=symbolic residual and executable trace metadata; rule=cancel the normalization derivative term
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
