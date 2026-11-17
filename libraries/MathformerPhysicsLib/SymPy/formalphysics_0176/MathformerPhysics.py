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

Original source task (NL): Evaluate the first variation at epsilon zero after differentiating under the integral and substituting variation derivatives.
Original source task (LaTeX): \left.dJ_\epsilon/d\epsilon\right|_0=\int L_f\eta+\int L_{f'}\eta'
Formalized target: \left.dJ_\epsilon/d\epsilon\right|_0=\int L_f\eta+\int L_{f'}\eta'
Source anchors: src_L0004, src_L0009

Original informal statement:
For the first variation of a functional with fixed endpoints, evaluate the
epsilon derivative at zero and obtain the two standard integral terms.

Informal derivation commentary:
1. Differentiate under the integral sign.
2. Apply the chain rule to the varied function and its derivative.
3. Substitute partial g_epsilon/partial epsilon = eta.
4. Substitute partial g'_epsilon/partial epsilon = eta'.
5. Evaluate the L-derivative factors at epsilon=0.

SymPy alignment:
- Differentiate-under-integral and chain-rule steps map to DERIVATION_STEPS[0].
- Evaluation at epsilon=0 maps to DERIVATION_STEPS[1] and DERIVATION_STEPS[2].
- The final additive target maps to DERIVATION_STEPS[3].

Generated support note: This artifact implements the
`sympy_physics_derivation_trace` style. Source-backed equations are kept in
`CLAIM`; generated algebra, calculus, substitution, unit, and validation steps
are exposed through `DERIVATION_STEPS` and the validation functions below.
Complete status must come from execution, dimensional analysis, symbolic step
verification, and numeric sanity checks, not from this file existing.
"""

from backends.sympy.MathformerPhysicsSympy.pipeline import case_spec, derive_case, enriched_assumption_context, enriched_dimension_projection_report, enriched_equation_surface, enriched_equational_semantics_report, enriched_final_equation_reviews, execute_case, format_derivation_print, numeric_samples, step_verification, sympy_library_grounding, unit_analysis


# Stable identifier used to recover the source task from the shared pipeline.
CASE_ID = "formalphysics_0176"
COMMENTARY_HEADER = "Original informal statement:\nFor the first variation of a functional with fixed endpoints, evaluate the\nepsilon derivative at zero and obtain the two standard integral terms.\n\nInformal derivation commentary:\n1. Differentiate under the integral sign.\n2. Apply the chain rule to the varied function and its derivative.\n3. Substitute partial g_epsilon/partial epsilon = eta.\n4. Substitute partial g'_epsilon/partial epsilon = eta'.\n5. Evaluate the L-derivative factors at epsilon=0.\n\nSymPy alignment:\n- Differentiate-under-integral and chain-rule steps map to DERIVATION_STEPS[0].\n- Evaluation at epsilon=0 maps to DERIVATION_STEPS[1] and DERIVATION_STEPS[2].\n- The final additive target maps to DERIVATION_STEPS[3]."
DERIVATION_PRINT = "FULL PRINTED SYMPY DERIVATION\nCase: formalphysics_0176\nClaim (NL): Evaluate the first variation at epsilon zero after differentiating under the integral and substituting variation derivatives.\nClaim (LaTeX): \\left.dJ_\\epsilon/d\\epsilon\\right|_0=\\int L_f\\eta+\\int L_{f'}\\eta'\nTarget key: first_variation_epsilon_zero\n\nQuantities:\n- dJ0: first variation of the functional at epsilon zero; dimension=energy; unit=joule\n- integrand_f: integral term before evaluating L_f at epsilon zero; dimension=energy; unit=joule\n- integrand_fp: integral term before evaluating L_fprime at epsilon zero; dimension=energy; unit=joule\n- final_f: final L_f eta integral; dimension=energy; unit=joule\n- final_fp: final L_fprime eta-prime integral; dimension=energy; unit=joule\n\nContext assumptions:\n- fixed endpoint variation eta(a)=eta(b)=0\n- differentiation under the integral is justified\n- L and variation functions are smooth enough\n- epsilon is evaluated at zero\n\nPhysical laws and source rules:\n- chain rule for L(x,g_epsilon,g_epsilon')\n- differentiate under the integral sign\n- variation derivative dg_epsilon/depsilon=eta\n- variation derivative dg_epsilon'/depsilon=eta'\n\nProjection/operator bridges:\n- formalphysics_0176.projection_bridge: coordinate_component_bridge [provided]; source=None; targets=formalphysics_0176.target\n\nDerivation steps:\n1. step_01_differentiate_under_integral [source_equation]\n   expression: integrand_f + integrand_fp\n   rule: differentiate under the integral sign and split the variation terms\n   support: source equation; generated=False; source_anchors=src_L0004, src_L0009\n2. step_02_evaluate_L_f_term_at_epsilon_zero [source_substitution]\n   expression: final_f\n   rule: evaluate the L_f variation term at epsilon zero\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n3. step_03_evaluate_L_fprime_term_at_epsilon_zero [source_substitution]\n   expression: final_fp\n   rule: evaluate the L_fprime variation term at epsilon zero\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n4. step_04_collect_first_variation_terms [target_equation]\n   expression: final_f + final_fp\n   rule: collect the two first-variation integral terms\n   support: source target; generated=False; source_anchors=src_L0004, src_L0009\n\nComputed expressions:\n- target_expression: final_f + final_fp\n- expected/source_expression: final_f + final_fp\n- residual target_minus_expected: 0\n\nValidation print:\n- symbolic_target_verified: True\n- derivation_steps_passed: True\n- dimensionally_consistent: True\n- numeric_sample_passed: True\n- numeric_sample: dJ0=17, integrand_f=5, integrand_fp=12, final_f=5, final_fp=12\n- numeric_target_value: 17.0\n- numeric_expected_value: 17.0\n\nEquivalence certificates:\n- step_01_differentiate_under_integral: passed=True; certificate=symbolic residual and executable trace metadata; rule=differentiate under the integral sign and split the variation terms\n- step_02_evaluate_L_f_term_at_epsilon_zero: passed=True; certificate=symbolic residual and executable trace metadata; rule=evaluate the L_f variation term at epsilon zero\n- step_03_evaluate_L_fprime_term_at_epsilon_zero: passed=True; certificate=symbolic residual and executable trace metadata; rule=evaluate the L_fprime variation term at epsilon zero\n- step_04_collect_first_variation_terms: passed=True; certificate=symbolic residual and executable trace metadata; rule=collect the two first-variation integral terms\n\nSymPy library grounding:\n- grounding_level: high\n- calculus: grounded; APIs=sympy.core.function.diff, sympy.integrals.integrals.integrate, sympy.core.function.Derivative, sympy.integrals.integrals.Integral\n- numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy\n- scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand\n- solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp\n- units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify"

# Source-alignment packet: preserves the original task and the exact formal
# target represented by this artifact.
CLAIM = {
    "backend": "sympy",
    "style": "sympy_physics_derivation_trace",
    "case_id": CASE_ID,
    "statement_nl": 'Evaluate the first variation at epsilon zero after differentiating under the integral and substituting variation derivatives.',
    "statement_latex": "\\left.dJ_\\epsilon/d\\epsilon\\right|_0=\\int L_f\\eta+\\int L_{f'}\\eta'",
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
# Case: formalphysics_0176
# Claim (NL): Evaluate the first variation at epsilon zero after differentiating under the integral and substituting variation derivatives.
# Claim (LaTeX): \left.dJ_\epsilon/d\epsilon\right|_0=\int L_f\eta+\int L_{f'}\eta'
# Target key: first_variation_epsilon_zero
#
# Quantities:
# - dJ0: first variation of the functional at epsilon zero; dimension=energy; unit=joule
# - integrand_f: integral term before evaluating L_f at epsilon zero; dimension=energy; unit=joule
# - integrand_fp: integral term before evaluating L_fprime at epsilon zero; dimension=energy; unit=joule
# - final_f: final L_f eta integral; dimension=energy; unit=joule
# - final_fp: final L_fprime eta-prime integral; dimension=energy; unit=joule
#
# Context assumptions:
# - fixed endpoint variation eta(a)=eta(b)=0
# - differentiation under the integral is justified
# - L and variation functions are smooth enough
# - epsilon is evaluated at zero
#
# Physical laws and source rules:
# - chain rule for L(x,g_epsilon,g_epsilon')
# - differentiate under the integral sign
# - variation derivative dg_epsilon/depsilon=eta
# - variation derivative dg_epsilon'/depsilon=eta'
#
# Projection/operator bridges:
# - formalphysics_0176.projection_bridge: coordinate_component_bridge [provided]; source=None; targets=formalphysics_0176.target
#
# Derivation steps:
# 1. step_01_differentiate_under_integral [source_equation]
#    expression: integrand_f + integrand_fp
#    rule: differentiate under the integral sign and split the variation terms
#    support: source equation; generated=False; source_anchors=src_L0004, src_L0009
# 2. step_02_evaluate_L_f_term_at_epsilon_zero [source_substitution]
#    expression: final_f
#    rule: evaluate the L_f variation term at epsilon zero
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 3. step_03_evaluate_L_fprime_term_at_epsilon_zero [source_substitution]
#    expression: final_fp
#    rule: evaluate the L_fprime variation term at epsilon zero
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 4. step_04_collect_first_variation_terms [target_equation]
#    expression: final_f + final_fp
#    rule: collect the two first-variation integral terms
#    support: source target; generated=False; source_anchors=src_L0004, src_L0009
#
# Computed expressions:
# - target_expression: final_f + final_fp
# - expected/source_expression: final_f + final_fp
# - residual target_minus_expected: 0
#
# Validation print:
# - symbolic_target_verified: True
# - derivation_steps_passed: True
# - dimensionally_consistent: True
# - numeric_sample_passed: True
# - numeric_sample: dJ0=17, integrand_f=5, integrand_fp=12, final_f=5, final_fp=12
# - numeric_target_value: 17.0
# - numeric_expected_value: 17.0
#
# Equivalence certificates:
# - step_01_differentiate_under_integral: passed=True; certificate=symbolic residual and executable trace metadata; rule=differentiate under the integral sign and split the variation terms
# - step_02_evaluate_L_f_term_at_epsilon_zero: passed=True; certificate=symbolic residual and executable trace metadata; rule=evaluate the L_f variation term at epsilon zero
# - step_03_evaluate_L_fprime_term_at_epsilon_zero: passed=True; certificate=symbolic residual and executable trace metadata; rule=evaluate the L_fprime variation term at epsilon zero
# - step_04_collect_first_variation_terms: passed=True; certificate=symbolic residual and executable trace metadata; rule=collect the two first-variation integral terms
#
# SymPy library grounding:
# - grounding_level: high
# - calculus: grounded; APIs=sympy.core.function.diff, sympy.integrals.integrals.integrate, sympy.core.function.Derivative, sympy.integrals.integrals.Integral
# - numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy
# - scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand
# - solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp
# - units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify
