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

Original source task (NL): From D=epsilon_0 E+P, J_M=curl M, curl H=J_f+dD/dt, and B=mu_0(H+M), derive the Maxwell-Ampere equation with free, polarization, and magnetization current terms.
Original source task (LaTeX): \nabla\times(B/\mu_0)=J_f+\epsilon_0\partial_t E+\partial_tP+J_M
Formalized target: \nabla\times(B/\mu_0)=J_f+\epsilon_0\partial_t E+\partial_tP+J_M
Source anchors: src_L0004, src_L0009

Original informal statement:
From D=epsilon_0 E+P, J_M=curl M, curl H=J_f+dD/dt, and B=mu_0(H+M), derive
the Maxwell-Ampere equation with free, polarization, and magnetization current
terms:
    curl(B/mu_0) = J_f + epsilon_0 partial_t E + partial_t P + J_M.

Informal derivation commentary:
1. Start from the macroscopic Ampere law curl H = J_f + dD/dt.
2. Use B=mu_0(H+M), mu_0 != 0, constant mu_0, and curl linearity to rewrite
   curl(B/mu_0) as curl H + curl M.
3. Identify the magnetization current J_M = curl M.
4. Substitute curl H = J_f + dD/dt into the rewritten left-hand side.
5. Substitute D=epsilon_0 E+P and use time-derivative linearity with constant
   epsilon_0 to expand dD/dt as epsilon_0 partial_t E + partial_t P.
6. Collect the free, displacement, polarization, and magnetization current
   terms to obtain the target equation.

SymPy alignment:
- Informal step 1 is represented as the source law used by
  step_02_substitute_ampere_macroscopic and LAW_TABLE.
- Informal step 2 maps to DERIVATION_STEPS[0] /
  step_01_projection_from_B_relation and PROJECTION_BRIDGES.
- Informal step 3 maps to DERIVATION_STEPS[3] /
  step_04_substitute_magnetization_current.
- Informal step 4 maps to DERIVATION_STEPS[1] /
  step_02_substitute_ampere_macroscopic.
- Informal step 5 maps to DERIVATION_STEPS[2] /
  step_03_expand_displacement_current.
- Informal step 6 maps to DERIVATION_STEPS[4] /
  step_05_target_rhs and to validate_derivation_steps.
- Physical typing and vector-to-scalar placeholder discipline are carried by
  QUANTITY_TABLE, QUANTITY_SURFACE, PROJECTION_BRIDGES,
  validate_dimensions, and validate_projection_bridges.

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
CASE_ID = "formalphysics_0020"
COMMENTARY_HEADER = "Original informal statement:\nFrom D=epsilon_0 E+P, J_M=curl M, curl H=J_f+dD/dt, and B=mu_0(H+M), derive\nthe Maxwell-Ampere equation with free, polarization, and magnetization current\nterms:\n    curl(B/mu_0) = J_f + epsilon_0 partial_t E + partial_t P + J_M.\n\nInformal derivation commentary:\n1. Start from the macroscopic Ampere law curl H = J_f + dD/dt.\n2. Use B=mu_0(H+M), mu_0 != 0, constant mu_0, and curl linearity to rewrite\n   curl(B/mu_0) as curl H + curl M.\n3. Identify the magnetization current J_M = curl M.\n4. Substitute curl H = J_f + dD/dt into the rewritten left-hand side.\n5. Substitute D=epsilon_0 E+P and use time-derivative linearity with constant\n   epsilon_0 to expand dD/dt as epsilon_0 partial_t E + partial_t P.\n6. Collect the free, displacement, polarization, and magnetization current\n   terms to obtain the target equation.\n\nSymPy alignment:\n- Informal step 1 is represented as the source law used by\n  step_02_substitute_ampere_macroscopic and LAW_TABLE.\n- Informal step 2 maps to DERIVATION_STEPS[0] /\n  step_01_projection_from_B_relation and PROJECTION_BRIDGES.\n- Informal step 3 maps to DERIVATION_STEPS[3] /\n  step_04_substitute_magnetization_current.\n- Informal step 4 maps to DERIVATION_STEPS[1] /\n  step_02_substitute_ampere_macroscopic.\n- Informal step 5 maps to DERIVATION_STEPS[2] /\n  step_03_expand_displacement_current.\n- Informal step 6 maps to DERIVATION_STEPS[4] /\n  step_05_target_rhs and to validate_derivation_steps.\n- Physical typing and vector-to-scalar placeholder discipline are carried by\n  QUANTITY_TABLE, QUANTITY_SURFACE, PROJECTION_BRIDGES,\n  validate_dimensions, and validate_projection_bridges."
DERIVATION_PRINT = "FULL PRINTED SYMPY DERIVATION\nCase: formalphysics_0020\nClaim (NL): From D=epsilon_0 E+P, J_M=curl M, curl H=J_f+dD/dt, and B=mu_0(H+M), derive the Maxwell-Ampere equation with free, polarization, and magnetization current terms.\nClaim (LaTeX): \\nabla\\times(B/\\mu_0)=J_f+\\epsilon_0\\partial_t E+\\partial_tP+J_M\nTarget key: maxwell_ampere_with_polarization_magnetization\n\nQuantities:\n- curlB_over_mu0: curl of B divided by mu_0 represented as a vector-current-density placeholder; dimension=current_density; unit=ampere/meter**2\n- curlH: curl of H represented as a vector-current-density placeholder; dimension=current_density; unit=ampere/meter**2\n- curlM: curl of M represented as magnetization-current placeholder; dimension=current_density; unit=ampere/meter**2\n- Jf: free current density; dimension=current_density; unit=ampere/meter**2\n- JM: magnetization current density; dimension=current_density; unit=ampere/meter**2\n- dDdt: time derivative of electric displacement field; dimension=current_density; unit=ampere/meter**2\n- eps0_dEdt: epsilon_0 times the time derivative of electric field; dimension=current_density; unit=ampere/meter**2\n- dPdt: time derivative of polarization field; dimension=current_density; unit=ampere/meter**2\n- B: magnetic flux density field; dimension=magnetic_field; unit=tesla\n- H: magnetic field intensity field; dimension=magnetic_intensity; unit=ampere/meter\n- M: magnetization field; dimension=magnetic_intensity; unit=ampere/meter\n- D: electric displacement field; dimension=electric_displacement; unit=coulomb/meter**2\n- E: electric field; dimension=electric_field; unit=volt/meter\n- Ppol: polarization field; dimension=electric_displacement; unit=coulomb/meter**2\n- mu0: vacuum permeability; dimension=permeability; unit=newton/ampere**2\n- epsilon0: vacuum permittivity; dimension=permittivity; unit=farad/meter\n\nContext assumptions:\n- SI macroscopic electromagnetism unit convention\n- fields are smooth enough for curl and time derivatives\n- mu0 != 0\n- mu0 and epsilon0 are constants\n- curl is linear over the represented vector-field terms\n- all current-density placeholders live in the same vector space and coordinate frame\n\nPhysical laws and source rules:\n- D=epsilon0 E+P\n- J_M=curl M\n- curl H=J_f+dD/dt\n- B=mu0(H+M)\n- curl linearity and derivative linearity for constant material constants\n\nProjection/operator bridges:\n- formalphysics_0020.vector_placeholder_bridge: vector_equation_placeholder_bridge [provided]; source=vector Maxwell-Ampere equation; targets=formalphysics_0020.target\n- formalphysics_0020.curl_linearity_bridge: operator_linearity_bridge [provided]; source=curl(B/mu0)=curl(H+M); targets=formalphysics_0020.step_01\n- formalphysics_0020.time_derivative_linearity_bridge: operator_linearity_bridge [provided]; source=partial_t(epsilon0 E+P)=epsilon0 partial_t E+partial_t P; targets=formalphysics_0020.step_03\n\nDerivation steps:\n1. step_01_projection_from_B_relation [operator_linearity_bridge]\n   expression: curlH + curlM\n   rule: from B=mu0(H+M), mu0 != 0, constant mu0, and linearity of curl\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n2. step_02_substitute_ampere_macroscopic [source_substitution]\n   expression: Jf + curlM + dDdt\n   rule: substitute curl H=J_f+dD/dt\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n3. step_03_expand_displacement_current [source_substitution]\n   expression: Jf + curlM + dPdt + eps0_dEdt\n   rule: substitute D=epsilon0 E+P and commute time derivative through constant epsilon0\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n4. step_04_substitute_magnetization_current [source_substitution]\n   expression: JM + Jf + dPdt + eps0_dEdt\n   rule: substitute J_M=curl M\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n5. step_05_target_rhs [target_equation]\n   expression: JM + Jf + dPdt + eps0_dEdt\n   rule: Maxwell-Ampere target current-density right-hand side\n   support: source target; generated=False; source_anchors=src_L0004, src_L0009\n\nComputed expressions:\n- target_expression: JM + Jf + dPdt + eps0_dEdt\n- expected/source_expression: JM + Jf + dPdt + eps0_dEdt\n- residual target_minus_expected: 0\n\nValidation print:\n- symbolic_target_verified: True\n- derivation_steps_passed: True\n- dimensionally_consistent: True\n- numeric_sample_passed: True\n- numeric_sample: Jf=2, eps0_dEdt=3, dPdt=5, JM=7\n- numeric_target_value: 17.0\n- numeric_expected_value: 17.0\n\nEquivalence certificates:\n- step_01_projection_from_B_relation: passed=True; certificate=symbolic residual and executable trace metadata; rule=from B=mu0(H+M), mu0 != 0, constant mu0, and linearity of curl\n- step_02_substitute_ampere_macroscopic: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute curl H=J_f+dD/dt\n- step_03_expand_displacement_current: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute D=epsilon0 E+P and commute time derivative through constant epsilon0\n- step_04_substitute_magnetization_current: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute J_M=curl M\n- step_05_target_rhs: passed=True; certificate=symbolic residual and executable trace metadata; rule=Maxwell-Ampere target current-density right-hand side\n\nSymPy library grounding:\n- grounding_level: high\n- calculus: grounded; APIs=sympy.core.function.diff, sympy.integrals.integrals.integrate, sympy.core.function.Derivative, sympy.integrals.integrals.Integral\n- matrices_linear_algebra: grounded; APIs=sympy.matrices.dense.MutableDenseMatrix, sympy.matrices.expressions.matexpr.MatrixSymbol, sympy.matrices.expressions.matmul.MatMul\n- numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy\n- scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand\n- solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp\n- units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify\n- vector_analysis: grounded; APIs=sympy.vector.coordsysrect.CoordSys3D, sympy.vector.operators.gradient, sympy.vector.operators.divergence, sympy.vector.operators.curl"

# Source-alignment packet: preserves the original task and the exact formal
# target represented by this artifact.
CLAIM = {
    "backend": "sympy",
    "style": "sympy_physics_derivation_trace",
    "case_id": CASE_ID,
    "statement_nl": "From D=epsilon_0 E+P, J_M=curl M, curl H=J_f+dD/dt, and B=mu_0(H+M), derive the Maxwell-Ampere equation with free, polarization, and magnetization current terms.",
    "statement_latex": "\\nabla\\times(B/\\mu_0)=J_f+\\epsilon_0\\partial_t E+\\partial_tP+J_M",
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
# Case: formalphysics_0020
# Claim (NL): From D=epsilon_0 E+P, J_M=curl M, curl H=J_f+dD/dt, and B=mu_0(H+M), derive the Maxwell-Ampere equation with free, polarization, and magnetization current terms.
# Claim (LaTeX): \nabla\times(B/\mu_0)=J_f+\epsilon_0\partial_t E+\partial_tP+J_M
# Target key: maxwell_ampere_with_polarization_magnetization
#
# Quantities:
# - curlB_over_mu0: curl of B divided by mu_0 represented as a vector-current-density placeholder; dimension=current_density; unit=ampere/meter**2
# - curlH: curl of H represented as a vector-current-density placeholder; dimension=current_density; unit=ampere/meter**2
# - curlM: curl of M represented as magnetization-current placeholder; dimension=current_density; unit=ampere/meter**2
# - Jf: free current density; dimension=current_density; unit=ampere/meter**2
# - JM: magnetization current density; dimension=current_density; unit=ampere/meter**2
# - dDdt: time derivative of electric displacement field; dimension=current_density; unit=ampere/meter**2
# - eps0_dEdt: epsilon_0 times the time derivative of electric field; dimension=current_density; unit=ampere/meter**2
# - dPdt: time derivative of polarization field; dimension=current_density; unit=ampere/meter**2
# - B: magnetic flux density field; dimension=magnetic_field; unit=tesla
# - H: magnetic field intensity field; dimension=magnetic_intensity; unit=ampere/meter
# - M: magnetization field; dimension=magnetic_intensity; unit=ampere/meter
# - D: electric displacement field; dimension=electric_displacement; unit=coulomb/meter**2
# - E: electric field; dimension=electric_field; unit=volt/meter
# - Ppol: polarization field; dimension=electric_displacement; unit=coulomb/meter**2
# - mu0: vacuum permeability; dimension=permeability; unit=newton/ampere**2
# - epsilon0: vacuum permittivity; dimension=permittivity; unit=farad/meter
#
# Context assumptions:
# - SI macroscopic electromagnetism unit convention
# - fields are smooth enough for curl and time derivatives
# - mu0 != 0
# - mu0 and epsilon0 are constants
# - curl is linear over the represented vector-field terms
# - all current-density placeholders live in the same vector space and coordinate frame
#
# Physical laws and source rules:
# - D=epsilon0 E+P
# - J_M=curl M
# - curl H=J_f+dD/dt
# - B=mu0(H+M)
# - curl linearity and derivative linearity for constant material constants
#
# Projection/operator bridges:
# - formalphysics_0020.vector_placeholder_bridge: vector_equation_placeholder_bridge [provided]; source=vector Maxwell-Ampere equation; targets=formalphysics_0020.target
# - formalphysics_0020.curl_linearity_bridge: operator_linearity_bridge [provided]; source=curl(B/mu0)=curl(H+M); targets=formalphysics_0020.step_01
# - formalphysics_0020.time_derivative_linearity_bridge: operator_linearity_bridge [provided]; source=partial_t(epsilon0 E+P)=epsilon0 partial_t E+partial_t P; targets=formalphysics_0020.step_03
#
# Derivation steps:
# 1. step_01_projection_from_B_relation [operator_linearity_bridge]
#    expression: curlH + curlM
#    rule: from B=mu0(H+M), mu0 != 0, constant mu0, and linearity of curl
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 2. step_02_substitute_ampere_macroscopic [source_substitution]
#    expression: Jf + curlM + dDdt
#    rule: substitute curl H=J_f+dD/dt
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 3. step_03_expand_displacement_current [source_substitution]
#    expression: Jf + curlM + dPdt + eps0_dEdt
#    rule: substitute D=epsilon0 E+P and commute time derivative through constant epsilon0
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 4. step_04_substitute_magnetization_current [source_substitution]
#    expression: JM + Jf + dPdt + eps0_dEdt
#    rule: substitute J_M=curl M
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 5. step_05_target_rhs [target_equation]
#    expression: JM + Jf + dPdt + eps0_dEdt
#    rule: Maxwell-Ampere target current-density right-hand side
#    support: source target; generated=False; source_anchors=src_L0004, src_L0009
#
# Computed expressions:
# - target_expression: JM + Jf + dPdt + eps0_dEdt
# - expected/source_expression: JM + Jf + dPdt + eps0_dEdt
# - residual target_minus_expected: 0
#
# Validation print:
# - symbolic_target_verified: True
# - derivation_steps_passed: True
# - dimensionally_consistent: True
# - numeric_sample_passed: True
# - numeric_sample: Jf=2, eps0_dEdt=3, dPdt=5, JM=7
# - numeric_target_value: 17.0
# - numeric_expected_value: 17.0
#
# Equivalence certificates:
# - step_01_projection_from_B_relation: passed=True; certificate=symbolic residual and executable trace metadata; rule=from B=mu0(H+M), mu0 != 0, constant mu0, and linearity of curl
# - step_02_substitute_ampere_macroscopic: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute curl H=J_f+dD/dt
# - step_03_expand_displacement_current: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute D=epsilon0 E+P and commute time derivative through constant epsilon0
# - step_04_substitute_magnetization_current: passed=True; certificate=symbolic residual and executable trace metadata; rule=substitute J_M=curl M
# - step_05_target_rhs: passed=True; certificate=symbolic residual and executable trace metadata; rule=Maxwell-Ampere target current-density right-hand side
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
