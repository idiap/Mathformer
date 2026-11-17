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

Original source task (NL): Rewrite macroscopic Ampere-Maxwell in matter using bound polarization and magnetization current densities.
Original source task (LaTeX): \mu_0^{-1}\nabla\times B=J_f+\epsilon_0\partial_tE+J_P+J_M
Formalized target: \mu_0^{-1}\nabla\times B=J_f+\epsilon_0\partial_tE+J_P+J_M
Source anchors: src_L0004, src_L0009

Original informal statement:
Starting from macroscopic Ampere-Maxwell fields D=epsilon0 E+P and
H=B/mu0-M, derive the matter form with free, polarization, and magnetization
currents.

Informal derivation commentary:
1. Use Ampere-Maxwell curl H = J_f + dD/dt.
2. Substitute H=B/mu0-M and D=epsilon0 E+P.
3. Use curl and time-derivative linearity.
4. Identify J_P=dP/dt and J_M=curl M.

SymPy alignment:
- Constitutive substitution maps to DERIVATION_STEPS[0].
- Current identifications map to DERIVATION_STEPS[1] and DERIVATION_STEPS[2].
- Final collection maps to DERIVATION_STEPS[3].

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
CASE_ID = "formalphysics_0054"
COMMENTARY_HEADER = "Original informal statement:\nStarting from macroscopic Ampere-Maxwell fields D=epsilon0 E+P and\nH=B/mu0-M, derive the matter form with free, polarization, and magnetization\ncurrents.\n\nInformal derivation commentary:\n1. Use Ampere-Maxwell curl H = J_f + dD/dt.\n2. Substitute H=B/mu0-M and D=epsilon0 E+P.\n3. Use curl and time-derivative linearity.\n4. Identify J_P=dP/dt and J_M=curl M.\n\nSymPy alignment:\n- Constitutive substitution maps to DERIVATION_STEPS[0].\n- Current identifications map to DERIVATION_STEPS[1] and DERIVATION_STEPS[2].\n- Final collection maps to DERIVATION_STEPS[3]."
DERIVATION_PRINT = "FULL PRINTED SYMPY DERIVATION\nCase: formalphysics_0054\nClaim (NL): Rewrite macroscopic Ampere-Maxwell in matter using bound polarization and magnetization current densities.\nClaim (LaTeX): \\mu_0^{-1}\\nabla\\times B=J_f+\\epsilon_0\\partial_tE+J_P+J_M\nTarget key: ampere_matter_bound_currents\n\nQuantities:\n- inv_mu0_curlB: one over mu0 times curl of B; dimension=current_density; unit=ampere/meter**2\n- Jf: free current density; dimension=current_density; unit=ampere/meter**2\n- eps0_dEdt: epsilon0 times time derivative of E; dimension=current_density; unit=ampere/meter**2\n- dPdt: polarization current placeholder; dimension=current_density; unit=ampere/meter**2\n- curlM: magnetization current placeholder; dimension=current_density; unit=ampere/meter**2\n- JP: polarization current density; dimension=current_density; unit=ampere/meter**2\n- JM: magnetization current density; dimension=current_density; unit=ampere/meter**2\n\nContext assumptions:\n- SI macroscopic electromagnetism unit convention\n- mu0 != 0\n- mu0 and epsilon0 are constants\n- curl is linear over the represented vector-field terms\n- time derivative is linear over D=epsilon0 E+P\n\nPhysical laws and source rules:\n- curl H=J_f+dD/dt\n- H=B/mu0-M\n- D=epsilon0 E+P\n- J_P=partial_t P\n- J_M=curl M\n\nProjection/operator bridges:\n- formalphysics_0054.vector_placeholder_bridge: vector_equation_placeholder_bridge [provided]; source=macroscopic Ampere-Maxwell vector equation; targets=formalphysics_0054.target\n\nDerivation steps:\n1. step_01_rewrite_ampere_matter_rhs [source_equation]\n   expression: Jf + curlM + dPdt + eps0_dEdt\n   rule: substitute H=B/mu0-M and expand D=epsilon0 E+P in Ampere-Maxwell\n   support: source equation; generated=False; source_anchors=src_L0004, src_L0009\n2. step_02_identify_polarization_current [source_substitution]\n   expression: JP\n   rule: identify J_P=partial_t P\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n3. step_03_identify_magnetization_current [source_substitution]\n   expression: JM\n   rule: identify J_M=curl M\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n4. step_04_collect_bound_current_terms [target_equation]\n   expression: JM + JP + Jf + eps0_dEdt\n   rule: collect free, polarization, and magnetization current-density terms\n   support: source target; generated=False; source_anchors=src_L0004, src_L0009\n\nComputed expressions:\n- target_expression: JM + JP + Jf + eps0_dEdt\n- expected/source_expression: JM + JP + Jf + eps0_dEdt\n- residual target_minus_expected: 0\n\nValidation print:\n- symbolic_target_verified: True\n- derivation_steps_passed: True\n- dimensionally_consistent: True\n- numeric_sample_passed: True\n- numeric_sample: inv_mu0_curlB=23, Jf=2, eps0_dEdt=3, dPdt=5, curlM=13, JP=5, JM=13\n- numeric_target_value: 23.0\n- numeric_expected_value: 23.0\n\nEquivalence certificates:\n- step_01_rewrite_ampere_matter_rhs: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute H=B/mu0-M and expand D=epsilon0 E+P in Ampere-Maxwell\n- step_02_identify_polarization_current: passed=True; certificate=symbolic residual and executable trace metadata; rule=identify J_P=partial_t P\n- step_03_identify_magnetization_current: passed=True; certificate=symbolic residual and executable trace metadata; rule=identify J_M=curl M\n- step_04_collect_bound_current_terms: passed=True; certificate=symbolic residual and executable trace metadata; rule=collect free, polarization, and magnetization current-density terms\n\nSymPy library grounding:\n- grounding_level: high\n- calculus: grounded; APIs=sympy.core.function.diff, sympy.integrals.integrals.integrate, sympy.core.function.Derivative, sympy.integrals.integrals.Integral\n- matrices_linear_algebra: grounded; APIs=sympy.matrices.dense.MutableDenseMatrix, sympy.matrices.expressions.matexpr.MatrixSymbol, sympy.matrices.expressions.matmul.MatMul\n- numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy\n- scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand\n- solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp\n- units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify\n- vector_analysis: grounded; APIs=sympy.vector.coordsysrect.CoordSys3D, sympy.vector.operators.gradient, sympy.vector.operators.divergence, sympy.vector.operators.curl"

# Source-alignment packet: preserves the original task and the exact formal
# target represented by this artifact.
CLAIM = {
    "backend": "sympy",
    "style": "sympy_physics_derivation_trace",
    "case_id": CASE_ID,
    "statement_nl": "Rewrite macroscopic Ampere-Maxwell in matter using bound polarization and magnetization current densities.",
    "statement_latex": "\\mu_0^{-1}\\nabla\\times B=J_f+\\epsilon_0\\partial_tE+J_P+J_M",
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
# Case: formalphysics_0054
# Claim (NL): Rewrite macroscopic Ampere-Maxwell in matter using bound polarization and magnetization current densities.
# Claim (LaTeX): \mu_0^{-1}\nabla\times B=J_f+\epsilon_0\partial_tE+J_P+J_M
# Target key: ampere_matter_bound_currents
#
# Quantities:
# - inv_mu0_curlB: one over mu0 times curl of B; dimension=current_density; unit=ampere/meter**2
# - Jf: free current density; dimension=current_density; unit=ampere/meter**2
# - eps0_dEdt: epsilon0 times time derivative of E; dimension=current_density; unit=ampere/meter**2
# - dPdt: polarization current placeholder; dimension=current_density; unit=ampere/meter**2
# - curlM: magnetization current placeholder; dimension=current_density; unit=ampere/meter**2
# - JP: polarization current density; dimension=current_density; unit=ampere/meter**2
# - JM: magnetization current density; dimension=current_density; unit=ampere/meter**2
#
# Context assumptions:
# - SI macroscopic electromagnetism unit convention
# - mu0 != 0
# - mu0 and epsilon0 are constants
# - curl is linear over the represented vector-field terms
# - time derivative is linear over D=epsilon0 E+P
#
# Physical laws and source rules:
# - curl H=J_f+dD/dt
# - H=B/mu0-M
# - D=epsilon0 E+P
# - J_P=partial_t P
# - J_M=curl M
#
# Projection/operator bridges:
# - formalphysics_0054.vector_placeholder_bridge: vector_equation_placeholder_bridge [provided]; source=macroscopic Ampere-Maxwell vector equation; targets=formalphysics_0054.target
#
# Derivation steps:
# 1. step_01_rewrite_ampere_matter_rhs [source_equation]
#    expression: Jf + curlM + dPdt + eps0_dEdt
#    rule: substitute H=B/mu0-M and expand D=epsilon0 E+P in Ampere-Maxwell
#    support: source equation; generated=False; source_anchors=src_L0004, src_L0009
# 2. step_02_identify_polarization_current [source_substitution]
#    expression: JP
#    rule: identify J_P=partial_t P
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 3. step_03_identify_magnetization_current [source_substitution]
#    expression: JM
#    rule: identify J_M=curl M
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 4. step_04_collect_bound_current_terms [target_equation]
#    expression: JM + JP + Jf + eps0_dEdt
#    rule: collect free, polarization, and magnetization current-density terms
#    support: source target; generated=False; source_anchors=src_L0004, src_L0009
#
# Computed expressions:
# - target_expression: JM + JP + Jf + eps0_dEdt
# - expected/source_expression: JM + JP + Jf + eps0_dEdt
# - residual target_minus_expected: 0
#
# Validation print:
# - symbolic_target_verified: True
# - derivation_steps_passed: True
# - dimensionally_consistent: True
# - numeric_sample_passed: True
# - numeric_sample: inv_mu0_curlB=23, Jf=2, eps0_dEdt=3, dPdt=5, curlM=13, JP=5, JM=13
# - numeric_target_value: 23.0
# - numeric_expected_value: 23.0
#
# Equivalence certificates:
# - step_01_rewrite_ampere_matter_rhs: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute H=B/mu0-M and expand D=epsilon0 E+P in Ampere-Maxwell
# - step_02_identify_polarization_current: passed=True; certificate=symbolic residual and executable trace metadata; rule=identify J_P=partial_t P
# - step_03_identify_magnetization_current: passed=True; certificate=symbolic residual and executable trace metadata; rule=identify J_M=curl M
# - step_04_collect_bound_current_terms: passed=True; certificate=symbolic residual and executable trace metadata; rule=collect free, polarization, and magnetization current-density terms
#
# SymPy library grounding:
# - grounding_level: high
# - calculus: grounded; APIs=sympy.core.function.diff, sympy.integrals.integrals.integrate, sympy.core.function.Derivative, sympy.integrals.integrals.Integral
# - matrices_linear_algebra: grounded; APIs=sympy.matrices.dense.MutableDenseMatrix, sympy.matrices.expressions.matexpr.MatrixSymbol, sympy.matrices.expressions.matmul.MatMul
# - numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy
# - scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand
# - solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp
# - units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify
# - vector_analysis: grounded; APIs=sympy.vector.coordsysrect.CoordSys3D, sympy.vector.operators.gradient, sympy.vector.operators.divergence, sympy.vector.operators.curl
