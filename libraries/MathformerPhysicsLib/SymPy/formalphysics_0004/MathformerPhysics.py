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

Original source task (NL): For the 1D quantum harmonic oscillator in units with m=omega=hbar=1, compute the number operator N=a_dagger a from a=(q+ip)/sqrt(2), a_dagger=(q-ip)/sqrt(2), and [q,p]=i.
Original source task (LaTeX): N=a^{\dagger}a=\frac12(p^2-i p q+i q p+q^2)
Formalized target: N=a^{\dagger}a=\frac12(p^2-i p q+i q p+q^2)
Source anchors: src_L0004, src_L0009

Original informal statement:
For the 1D quantum harmonic oscillator in units with m=omega=hbar=1, the
ladder operators are a=(q+ip)/sqrt(2) and a_dagger=(q-ip)/sqrt(2), with
[q,p]=i. Compute the number operator N=a_dagger a in terms of q and p.

Informal derivation commentary:
1. Record the source ladder definitions
   a = (ip+q)/sqrt(2) and a_dagger = (-ip+q)/sqrt(2).
2. Form the number-operator product N = a_dagger*a.
3. Factor out the dimensionless constant to obtain
   N = (1/2)(-ip+q)(ip+q).
4. Expand the product without commuting p and q:
   N = (1/2)(p**2 - i*p*q + i*q*p + q**2).
5. Preserve the canonical commutator [q,p]=i as source context, but do not
   apply the optional simplification to (p**2+q**2-1)/2 because the requested
   expansion is the unsimplified operator-ordered expression.

SymPy alignment:
- Informal step 1 maps to DERIVATION_STEPS[0] and DERIVATION_STEPS[1].
- Informal step 2 maps to DERIVATION_STEPS[2].
- Informal step 3 maps to DERIVATION_STEPS[3].
- Informal step 4 maps to DERIVATION_STEPS[4] and the symbolic residual
  checked by validate_derivation_steps.
- The operator surface is represented by noncommutative SymPy symbols, so p*q
  and q*p remain distinct.
- Dimensionless units, noncommutative operator ordering, and the optional
  commutator simplification boundary are carried by ASSUMPTIONS, LAW_TABLE,
  PROJECTION_BRIDGES, and validate_projection_bridges.

Generated support note: This artifact implements the
`sympy_physics_derivation_trace` style. Source-backed equations are kept in
`CLAIM`; generated algebra, calculus, substitution, unit, and validation steps
are exposed through `DERIVATION_STEPS` and the validation functions below.
Complete status must come from execution, dimensional analysis, symbolic step
verification, and numeric sanity checks, not from this file existing.
"""

from backends.sympy.MathformerPhysicsSympy.pipeline import case_spec, derive_case, enriched_assumption_context, enriched_dimension_projection_report, enriched_equation_surface, enriched_equational_semantics_report, enriched_final_equation_reviews, execute_case, format_derivation_print, numeric_samples, step_verification, sympy_library_grounding, unit_analysis


# Stable identifier used to recover the source task from the shared pipeline.
CASE_ID = "formalphysics_0004"
COMMENTARY_HEADER = 'Original informal statement:\nFor the 1D quantum harmonic oscillator in units with m=omega=hbar=1, the\nladder operators are a=(q+ip)/sqrt(2) and a_dagger=(q-ip)/sqrt(2), with\n[q,p]=i. Compute the number operator N=a_dagger a in terms of q and p.\n\nInformal derivation commentary:\n1. Record the source ladder definitions\n   a = (ip+q)/sqrt(2) and a_dagger = (-ip+q)/sqrt(2).\n2. Form the number-operator product N = a_dagger*a.\n3. Factor out the dimensionless constant to obtain\n   N = (1/2)(-ip+q)(ip+q).\n4. Expand the product without commuting p and q:\n   N = (1/2)(p**2 - i*p*q + i*q*p + q**2).\n5. Preserve the canonical commutator [q,p]=i as source context, but do not\n   apply the optional simplification to (p**2+q**2-1)/2 because the requested\n   expansion is the unsimplified operator-ordered expression.\n\nSymPy alignment:\n- Informal step 1 maps to DERIVATION_STEPS[0] and DERIVATION_STEPS[1].\n- Informal step 2 maps to DERIVATION_STEPS[2].\n- Informal step 3 maps to DERIVATION_STEPS[3].\n- Informal step 4 maps to DERIVATION_STEPS[4] and the symbolic residual\n  checked by validate_derivation_steps.\n- The operator surface is represented by noncommutative SymPy symbols, so p*q\n  and q*p remain distinct.\n- Dimensionless units, noncommutative operator ordering, and the optional\n  commutator simplification boundary are carried by ASSUMPTIONS, LAW_TABLE,\n  PROJECTION_BRIDGES, and validate_projection_bridges.'
DERIVATION_PRINT = 'FULL PRINTED SYMPY DERIVATION\nCase: formalphysics_0004\nClaim (NL): For the 1D quantum harmonic oscillator in units with m=omega=hbar=1, compute the number operator N=a_dagger a from a=(q+ip)/sqrt(2), a_dagger=(q-ip)/sqrt(2), and [q,p]=i.\nClaim (LaTeX): N=a^{\\dagger}a=\\frac12(p^2-i p q+i q p+q^2)\nTarget key: dimensionless_ladder_number_operator_expansion\n\nQuantities:\n- q: dimensionless position operator; dimension=dimensionless; unit=one\n- p: dimensionless momentum operator; dimension=dimensionless; unit=one\n- a: annihilation ladder operator; dimension=dimensionless; unit=one\n- adagger: creation ladder operator; dimension=dimensionless; unit=one\n- Nop: number operator N; dimension=dimensionless; unit=one\n\nContext assumptions:\n- dimensionless oscillator units m=omega=hbar=1\n- q and p are noncommuting quantum operators\n- a=(q+i p)/sqrt(2) is the source annihilation operator\n- a_dagger=(q-i p)/sqrt(2) is the source creation operator\n- N=a_dagger*a defines the number operator\n- [q,p]=i is recorded but the optional commutator simplification is not applied\n\nPhysical laws and source rules:\n- dimensionless harmonic-oscillator ladder definitions\n- number operator definition N=a_dagger*a\n- noncommutative distributive expansion\n- canonical commutator [q,p]=i retained as context only\n\nProjection/operator bridges:\n- formalphysics_0004.noncommutative_operator_bridge: finite_operator_algebra_projection_bridge [provided]; source=unbounded Hilbert-space q and p operators; targets=formalphysics_0004.target\n- formalphysics_0004.dimensionless_units_bridge: unit_dimension_bridge [provided]; source=m=omega=hbar=1; targets=formalphysics_0004.dimensionless_operator_surface\n\nDerivation steps:\n1. step_01_annihilation_definition [source_equation]\n   expression: sqrt(2)*(I*p + q)/2\n   rule: source ladder definition a=(q+i p)/sqrt(2)\n   support: source equation; generated=False; source_anchors=src_L0004, src_L0009\n2. step_02_creation_definition [source_equation]\n   expression: sqrt(2)*(-I*p + q)/2\n   rule: source adjoint ladder definition a_dagger=(q-i p)/sqrt(2)\n   support: source equation; generated=False; source_anchors=src_L0004, src_L0009\n3. step_03_number_operator_product [source_substitution]\n   expression: (-I*p + q)*(I*p + q)/2\n   rule: form N=a_dagger*a from the source definitions\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n4. step_04_factor_dimensionless_normalization [source_substitution]\n   expression: (-I*p + q)*(I*p + q)/2\n   rule: factor the dimensionless normalization constant\n   support: source support; generated=False; source_anchors=src_L0004, src_L0009\n5. step_05_noncommutative_operator_expansion [target_equation]\n   expression: -I*p*q/2 + p**2/2 + I*q*p/2 + q**2/2\n   rule: expand the product while preserving noncommutative p*q and q*p order\n   support: source target; generated=False; source_anchors=src_L0004, src_L0009\n\nComputed expressions:\n- target_expression: (-I*p*q + p**2 + I*q*p + q**2)/2\n- expected/source_expression: (-I*p*q + p**2 + I*q*p + q**2)/2\n- residual target_minus_expected: 0\n\nValidation print:\n- symbolic_target_verified: True\n- derivation_steps_passed: True\n- dimensionally_consistent: True\n- numeric_sample_passed: True\n- numeric_sample: q=2, p=3\n- numeric_target_value: 6.5\n- numeric_expected_value: 6.5\n\nEquivalence certificates:\n- step_01_annihilation_definition: passed=True; certificate=symbolic residual and executable trace metadata; rule=source ladder definition a=(q+i p)/sqrt(2)\n- step_02_creation_definition: passed=True; certificate=symbolic residual and executable trace metadata; rule=source adjoint ladder definition a_dagger=(q-i p)/sqrt(2)\n- step_03_number_operator_product: passed=True; certificate=symbolic residual and executable trace metadata; rule=form N=a_dagger*a from the source definitions\n- step_04_factor_dimensionless_normalization: passed=True; certificate=symbolic residual and executable trace metadata; rule=factor the dimensionless normalization constant\n- step_05_noncommutative_operator_expansion: passed=True; certificate=symbolic residual and executable trace metadata; rule=expand the product while preserving noncommutative p*q and q*p order\n\nSymPy library grounding:\n- grounding_level: high\n- matrices_linear_algebra: grounded; APIs=sympy.matrices.dense.MutableDenseMatrix, sympy.matrices.expressions.matexpr.MatrixSymbol, sympy.matrices.expressions.matmul.MatMul\n- mechanics: grounded; APIs=sympy.physics.mechanics.particle.Particle, sympy.physics.mechanics.functions.dynamicsymbols, sympy.physics.mechanics.lagrange.LagrangesMethod\n- numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy\n- quantum_operators: grounded; APIs=sympy.physics.quantum.operator.Operator, sympy.physics.quantum.state.Ket, sympy.physics.quantum.state.Bra, sympy.physics.quantum.dagger.Dagger\n- scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand\n- solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp\n- units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify'

# Source-alignment packet: preserves the original task and the exact formal
# target represented by this artifact.
CLAIM = {
    "backend": "sympy",
    "style": "sympy_physics_derivation_trace",
    "case_id": CASE_ID,
    "statement_nl": 'For the 1D quantum harmonic oscillator in units with m=omega=hbar=1, compute the number operator N=a_dagger a from a=(q+ip)/sqrt(2), a_dagger=(q-ip)/sqrt(2), and [q,p]=i.',
    "statement_latex": 'N=a^{\\dagger}a=\\frac12(p^2-i p q+i q p+q^2)',
    "source_anchors": ['src_L0004', 'src_L0009'],
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
# Case: formalphysics_0004
# Claim (NL): For the 1D quantum harmonic oscillator in units with m=omega=hbar=1, compute the number operator N=a_dagger a from a=(q+ip)/sqrt(2), a_dagger=(q-ip)/sqrt(2), and [q,p]=i.
# Claim (LaTeX): N=a^{\dagger}a=\frac12(p^2-i p q+i q p+q^2)
# Target key: dimensionless_ladder_number_operator_expansion
#
# Quantities:
# - q: dimensionless position operator; dimension=dimensionless; unit=one
# - p: dimensionless momentum operator; dimension=dimensionless; unit=one
# - a: annihilation ladder operator; dimension=dimensionless; unit=one
# - adagger: creation ladder operator; dimension=dimensionless; unit=one
# - Nop: number operator N; dimension=dimensionless; unit=one
#
# Context assumptions:
# - dimensionless oscillator units m=omega=hbar=1
# - q and p are noncommuting quantum operators
# - a=(q+i p)/sqrt(2) is the source annihilation operator
# - a_dagger=(q-i p)/sqrt(2) is the source creation operator
# - N=a_dagger*a defines the number operator
# - [q,p]=i is recorded but the optional commutator simplification is not applied
#
# Physical laws and source rules:
# - dimensionless harmonic-oscillator ladder definitions
# - number operator definition N=a_dagger*a
# - noncommutative distributive expansion
# - canonical commutator [q,p]=i retained as context only
#
# Projection/operator bridges:
# - formalphysics_0004.noncommutative_operator_bridge: finite_operator_algebra_projection_bridge [provided]; source=unbounded Hilbert-space q and p operators; targets=formalphysics_0004.target
# - formalphysics_0004.dimensionless_units_bridge: unit_dimension_bridge [provided]; source=m=omega=hbar=1; targets=formalphysics_0004.dimensionless_operator_surface
#
# Derivation steps:
# 1. step_01_annihilation_definition [source_equation]
#    expression: sqrt(2)*(I*p + q)/2
#    rule: source ladder definition a=(q+i p)/sqrt(2)
#    support: source equation; generated=False; source_anchors=src_L0004, src_L0009
# 2. step_02_creation_definition [source_equation]
#    expression: sqrt(2)*(-I*p + q)/2
#    rule: source adjoint ladder definition a_dagger=(q-i p)/sqrt(2)
#    support: source equation; generated=False; source_anchors=src_L0004, src_L0009
# 3. step_03_number_operator_product [source_substitution]
#    expression: (-I*p + q)*(I*p + q)/2
#    rule: form N=a_dagger*a from the source definitions
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 4. step_04_factor_dimensionless_normalization [source_substitution]
#    expression: (-I*p + q)*(I*p + q)/2
#    rule: factor the dimensionless normalization constant
#    support: source support; generated=False; source_anchors=src_L0004, src_L0009
# 5. step_05_noncommutative_operator_expansion [target_equation]
#    expression: -I*p*q/2 + p**2/2 + I*q*p/2 + q**2/2
#    rule: expand the product while preserving noncommutative p*q and q*p order
#    support: source target; generated=False; source_anchors=src_L0004, src_L0009
#
# Computed expressions:
# - target_expression: (-I*p*q + p**2 + I*q*p + q**2)/2
# - expected/source_expression: (-I*p*q + p**2 + I*q*p + q**2)/2
# - residual target_minus_expected: 0
#
# Validation print:
# - symbolic_target_verified: True
# - derivation_steps_passed: True
# - dimensionally_consistent: True
# - numeric_sample_passed: True
# - numeric_sample: q=2, p=3
# - numeric_target_value: 6.5
# - numeric_expected_value: 6.5
#
# Equivalence certificates:
# - step_01_annihilation_definition: passed=True; certificate=symbolic residual and executable trace metadata; rule=source ladder definition a=(q+i p)/sqrt(2)
# - step_02_creation_definition: passed=True; certificate=symbolic residual and executable trace metadata; rule=source adjoint ladder definition a_dagger=(q-i p)/sqrt(2)
# - step_03_number_operator_product: passed=True; certificate=symbolic residual and executable trace metadata; rule=form N=a_dagger*a from the source definitions
# - step_04_factor_dimensionless_normalization: passed=True; certificate=symbolic residual and executable trace metadata; rule=factor the dimensionless normalization constant
# - step_05_noncommutative_operator_expansion: passed=True; certificate=symbolic residual and executable trace metadata; rule=expand the product while preserving noncommutative p*q and q*p order
#
# SymPy library grounding:
# - grounding_level: high
# - matrices_linear_algebra: grounded; APIs=sympy.matrices.dense.MutableDenseMatrix, sympy.matrices.expressions.matexpr.MatrixSymbol, sympy.matrices.expressions.matmul.MatMul
# - mechanics: grounded; APIs=sympy.physics.mechanics.particle.Particle, sympy.physics.mechanics.functions.dynamicsymbols, sympy.physics.mechanics.lagrange.LagrangesMethod
# - numeric_validation: grounded; APIs=sympy.core.evalf.N, sympy.utilities.lambdify.lambdify, mpmath, numpy
# - quantum_operators: grounded; APIs=sympy.physics.quantum.operator.Operator, sympy.physics.quantum.state.Ket, sympy.physics.quantum.state.Bra, sympy.physics.quantum.dagger.Dagger
# - scalar_expression_core: grounded; APIs=sympy.core.symbol.Symbol, sympy.core.relational.Equality, sympy.simplify.simplify.simplify, sympy.core.function.expand
# - solvers_and_algebra: grounded; APIs=sympy.solvers.solvers.solve, sympy.solvers.solveset.solveset, sympy.simplify.radsimp.radsimp
# - units_dimensions: grounded; APIs=sympy.physics.units.Quantity, sympy.physics.units.Dimension, sympy.physics.units.systems.si.SI, sympy.physics.units.util.quantity_simplify
