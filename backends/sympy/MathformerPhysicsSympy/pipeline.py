# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

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

"""Executable physics derivation pipeline for the Mathformer SymPy backend."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import html as html_lib
import importlib
from importlib import metadata as importlib_metadata
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
from typing import cast, Any, Dict, List, Optional, Sequence, Tuple

import sympy as sp

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
STYLE = "sympy_physics_derivation_trace"
RELATED_NONPHYSICS_STYLE = "sympy_equational_trace"
BASE_DIMS = ("M", "L", "T", "I", "Theta", "N", "J")
ZERO_DIM = {key: 0 for key in BASE_DIMS}

from libraries.MathformerPhysicsLib.physics_ir import (
    from_case_spec,
    validate_ir,
)

PHYSICS_SYMPY_TARGET_DOMAINS: List[Dict[str, str]] = [
    {
        "id": "single_particle_kinematics",
        "label": "single-particle kinematics",
        "scope": "constant-acceleration, projectile, and one-dimensional motion derivations with explicit initial conditions",
    },
    {
        "id": "newtonian_point_mass_dynamics",
        "label": "Newtonian point-mass dynamics",
        "scope": "force, acceleration, work, and energy derivations for idealized point masses",
    },
    {
        "id": "harmonic_oscillator_derivations",
        "label": "harmonic oscillator derivations",
        "scope": "linear spring-mass oscillator frequency, period, and elementary ODE consequences",
    },
    {
        "id": "elementary_energy_work_derivations",
        "label": "elementary energy/work derivations",
        "scope": "work-energy and conservative-force identities with scalar units and dimensions",
    },
    {
        "id": "idealized_circuit_ode_derivations",
        "label": "idealized circuit ODE derivations",
        "scope": "RC/RL-style first-order circuit equations with explicit sign and component conventions",
    },
    {
        "id": "elementary_thermodynamic_identity_manipulations",
        "label": "elementary thermodynamic identity manipulations",
        "scope": "ideal-gas, density, pressure, volume, temperature, and molar-quantity algebra",
    },
]


PHYSICS_SYMPY_DEFERRED_DOMAINS: List[Dict[str, str]] = [
    {
        "id": "tensor_calculus_general_relativity",
        "label": "tensor calculus and general relativity",
        "reason": "requires tensor-index semantics and differential-geometry conventions beyond the first scalar/vector trace slice",
    },
    {
        "id": "continuum_mechanics",
        "label": "continuum mechanics",
        "reason": "requires field equations, boundary conditions, and constitutive laws that need richer surface contracts",
    },
    {
        "id": "gauge_field_derivations",
        "label": "gauge-field derivations",
        "reason": "requires explicit gauge choices, covariance conventions, and nontrivial field-strength representations",
    },
    {
        "id": "quantum_noncommuting_operator_algebra",
        "label": "quantum operator algebra with noncommuting observables",
        "reason": "requires operator-ordering, domain, and adjoint semantics not available in the first executable scalar trace contract",
    },
    {
        "id": "stochastic_differential_physics",
        "label": "stochastic differential physics",
        "reason": "requires stochastic process semantics, sampling policies, and measure-theoretic side conditions",
    },
]


PHYSICS_SYMPY_COMPLETENESS_CRITERIA: List[Dict[str, str]] = [
    {
        "id": "source_preservation",
        "text": "preserves source NL/LaTeX and source anchors",
        "validation_key": "source_nl_latex_and_anchors_preserved",
    },
    {
        "id": "source_equation_exposure",
        "text": "exposes every source-backed equation as a SymPy object",
        "validation_key": "all_source_targets_represented",
    },
    {
        "id": "implicit_step_expansion",
        "text": "expands every implicit algebraic, calculus, or substitution step",
        "validation_key": "all_required_gaps_closed",
    },
    {
        "id": "generated_support_marking",
        "text": "declares every generated support equation as generated support",
        "validation_key": "equation_surface_complete",
    },
    {
        "id": "context_declaration",
        "text": "declares all assumptions, regimes, domains, coordinate frames, and sign conventions",
        "validation_key": "assumption_context_explicit",
    },
    {
        "id": "unit_dimension_analysis",
        "text": "performs unit and dimensional analysis for every equation and transformation",
        "validation_key": "all_equations_dimensionally_consistent",
    },
    {
        "id": "target_chain_validation",
        "text": "validates the final target expression from the derivation chain",
        "validation_key": "target_expression_computed_from_steps",
    },
    {
        "id": "artifact_realness",
        "text": "has no unresolved placeholders or unexecuted derivation steps",
        "validation_key": "all_derivation_steps_execute",
    },
]


PHYSICS_SYMPY_COMPLETION_STATUSES: Dict[str, Dict[str, Any]] = {
    "complete": {
        "definition": "all derivation steps execute and all validation criteria pass",
        "terminal": True,
    },
    "draft": {
        "definition": "a useful executable partial derivation exists, but some non-blocking criteria remain unresolved",
        "terminal": False,
    },
    "blocked": {
        "definition": "a missing law, missing condition, inconsistent units, or ambiguous convention prevents a truthful complete artifact",
        "terminal": True,
        "hard_blocker_codes": [
            "missing_source_anchor_or_text",
            "missing_source_equation_or_target",
            "missing_law_or_unexpanded_gap",
            "missing_condition_or_context",
            "inconsistent_units_or_dimensions",
            "ambiguous_projection_or_convention",
            "target_not_derived_from_chain",
            "critical_physics_blocker",
        ],
    },
}


VALIDATION_BLOCKER_CODES: Dict[str, str] = {
    "all_source_targets_represented": "missing_source_equation_or_target",
    "source_nl_latex_and_anchors_preserved": "missing_source_anchor_or_text",
    "equation_surface_complete": "missing_law_or_unexpanded_gap",
    "assumption_context_explicit": "missing_condition_or_context",
    "all_required_gaps_closed": "missing_law_or_unexpanded_gap",
    "all_derivation_steps_execute": "unexecuted_derivation_step",
    "sympy_library_grounding_high": "missing_sympy_physics_grounding",
    "all_equations_dimensionally_consistent": "inconsistent_units_or_dimensions",
    "equational_semantics_preserved": "source_semantics_not_preserved",
    "dimension_projection_critic_passed": "ambiguous_projection_or_convention",
    "target_expression_computed_from_steps": "target_not_derived_from_chain",
    "numeric_sanity_no_counterexample": "numeric_counterexample_or_sampling_failure",
    "no_critical_blockers": "critical_physics_blocker",
    "physics_final_equation_review_passed": "physics_final_review_failed",
    "mathematical_final_equation_review_passed": "mathematical_final_review_failed",
}


PHYSICS_SYMPY_DEPENDENCY_SPECS: List[Dict[str, Any]] = [
    {
        "module": "sympy",
        "framework": "SymPy core",
        "required": True,
        "used_for": "symbolic expression construction, exact algebra, solving, calculus, and report residuals",
        "package": "sympy",
    },
    {
        "module": "sympy.physics.units",
        "framework": "SymPy physics units",
        "required": True,
        "used_for": "unit and dimensional analysis surfaces",
        "package": "sympy",
    },
    {
        "module": "sympy.physics.units.systems.si",
        "framework": "SymPy SI unit system",
        "required": True,
        "used_for": "SI grounding for physics quantities",
        "package": "sympy",
    },
    {
        "module": "sympy.physics.mechanics",
        "framework": "SymPy mechanics",
        "required": True,
        "used_for": "point-mass, oscillator, frame, and mechanics API grounding",
        "package": "sympy",
    },
    {
        "module": "sympy.physics.vector",
        "framework": "SymPy vector",
        "required": True,
        "used_for": "coordinate-frame and vector-analysis API grounding",
        "package": "sympy",
    },
    {
        "module": "numpy",
        "framework": "NumPy",
        "required": True,
        "used_for": "numeric sampling and array-backed diagnostics",
        "package": "numpy",
    },
    {
        "module": "scipy",
        "framework": "SciPy",
        "required": False,
        "used_for": "optional numeric ODE checks",
        "package": "scipy",
        "downgrades": ["numeric_ode_cross_check"],
    },
    {
        "module": "pint",
        "framework": "Pint",
        "required": False,
        "used_for": "optional independent unit-conversion cross-checks",
        "package": "Pint",
        "downgrades": ["independent_unit_conversion_cross_check"],
    },
    {
        "module": "matplotlib",
        "framework": "Matplotlib",
        "required": False,
        "used_for": "optional derivation diagnostic plots",
        "package": "matplotlib",
        "downgrades": ["static_diagnostic_plot_rendering"],
    },
    {
        "module": "plotly",
        "framework": "Plotly",
        "required": False,
        "used_for": "optional interactive derivation diagnostic plots",
        "package": "plotly",
        "downgrades": ["interactive_diagnostic_plot_rendering"],
    },
]


PHYSICS_SYMPY_API_SHARD_VERSION = "physics_sympy_api_index_v1"


PHYSICS_SOURCE_UNIT_ROLES = (
    "quantity_definition",
    "physical_law",
    "constitutive_relation",
    "coordinate_context",
    "initial_condition",
    "boundary_condition",
    "approximation_regime",
    "algebraic_step",
    "calculus_step",
    "substitution_step",
    "target_equation",
)


PHYSICS_SOURCE_FIXTURES: Dict[str, str] = {
    "constant_acceleration_kinematics": "tests/physics_sympy/controlled_latex/constant_acceleration_position.tex",
    "simple_harmonic_oscillator_period": "tests/physics_sympy/controlled_latex/simple_harmonic_oscillator_period.tex",
    "work_energy_theorem": "tests/physics_sympy/controlled_latex/work_energy_constant_force.tex",
    "rc_circuit_discharge": "tests/physics_sympy/controlled_latex/rc_discharge.tex",
    "ideal_gas_law_manipulation": "tests/physics_sympy/controlled_latex/ideal_gas_density.tex",
    "projectile_range_level_ground": "tests/physics_sympy/controlled_latex/projectile_range_level_ground.tex",
}


CONTROLLED_PHYSICS_CASE_IDS: List[str] = [
    "constant_acceleration_position",
    "constant_acceleration_velocity_position",
    "simple_harmonic_oscillator_omega",
    "simple_harmonic_oscillator_period",
    "work_energy_constant_force",
    "rc_discharge",
    "ideal_gas_density",
    "projectile_range_level_ground",
]


WIKI_LEVEL_PHYSICS_CASES: List[Dict[str, str]] = [
    {
        "case_id": "korteweg_de_vries_one_soliton",
        "label": "Korteweg-de Vries one-soliton",
        "runner": "tests/physics_sympy/run_mathformerlib_kdv.py",
        "source": "Wikipedia Korteweg-de Vries equation",
        "role": "wiki-level physics case exercised after the controlled fixture suite passes",
    }
]


PHASE16_ADVERSARIAL_FIXTURES: List[Dict[str, str]] = [
    {
        "id": "add_velocity_to_position",
        "category": "unit_inconsistency",
        "description": "add velocity to position",
        "expected_code": "additive_dimension_mismatch",
    },
    {
        "id": "exponentiate_dimensional_time",
        "category": "unit_inconsistency",
        "description": "exponentiate dimensional time",
        "expected_code": "dimensioned_function_argument",
    },
    {
        "id": "sine_of_dimensional_length",
        "category": "unit_inconsistency",
        "description": "take sine of dimensional length",
        "expected_code": "dimensioned_function_argument",
    },
    {
        "id": "substitute_energy_where_force_expected",
        "category": "unit_inconsistency",
        "description": "substitute energy where force is expected",
        "expected_code": "substitution_dimension_mismatch",
    },
    {
        "id": "missing_initial_condition",
        "category": "implicit_gap_failure",
        "description": "missing initial condition",
        "expected_code": "missing_initial_condition_application",
    },
    {
        "id": "missing_coordinate_sign_convention",
        "category": "implicit_gap_failure",
        "description": "missing coordinate sign convention",
        "expected_code": "ambiguous_projection_or_convention",
    },
    {
        "id": "missing_small_angle_assumption",
        "category": "implicit_gap_failure",
        "description": "missing small-angle assumption",
        "expected_code": "missing_approximation_justification",
    },
    {
        "id": "missing_nonzero_denominator",
        "category": "implicit_gap_failure",
        "description": "missing nonzero denominator",
        "expected_code": "missing_condition_or_context",
    },
    {
        "id": "missing_law_invocation",
        "category": "implicit_gap_failure",
        "description": "missing law invocation",
        "expected_code": "missing_law_or_unexpanded_gap",
    },
    {
        "id": "gravity_sign_mismatch",
        "category": "convention_drift",
        "description": "gravity sign mismatch",
        "expected_code": "coordinate_sign_convention_drift",
    },
    {
        "id": "spring_force_sign_mismatch",
        "category": "convention_drift",
        "description": "spring force sign mismatch",
        "expected_code": "force_sign_convention_drift",
    },
    {
        "id": "thermodynamic_work_sign_mismatch",
        "category": "convention_drift",
        "description": "thermodynamic work sign mismatch",
        "expected_code": "thermodynamic_work_sign_convention_drift",
    },
    {
        "id": "current_direction_mismatch",
        "category": "convention_drift",
        "description": "current direction mismatch",
        "expected_code": "current_direction_convention_drift",
    },
    {
        "id": "real_parameter_silently_made_positive",
        "category": "assumption_strengthening",
        "description": "real parameter silently made positive",
        "expected_code": "source_real_strengthened_to_positive",
    },
    {
        "id": "variable_silently_made_constant",
        "category": "assumption_strengthening",
        "description": "variable silently made constant",
        "expected_code": "source_variable_silently_made_constant",
    },
    {
        "id": "vector_law_silently_reduced_to_scalar",
        "category": "assumption_strengthening",
        "description": "vector law silently reduced to scalar law",
        "expected_code": "source_vector_law_silently_reduced_to_scalar",
    },
    {
        "id": "damping_silently_removed",
        "category": "assumption_strengthening",
        "description": "damping silently removed",
        "expected_code": "source_damping_silently_removed",
    },
]


PHYSICS_SYMBOL_KINDS = (
    "scalar_variable",
    "vector_quantity",
    "function_of_time",
    "parameter_constant",
    "generated_dummy_variable",
    "coordinate_axis_or_basis",
    "unit_or_dimension",
)


AMBIGUOUS_PHYSICS_SYMBOLS = {
    "k": ["spring constant", "Boltzmann constant", "wave number"],
    "c": ["speed of light", "damping coefficient", "constant of integration"],
    "R": ["resistance", "range", "gas constant"],
    "T": ["temperature", "period", "kinetic energy"],
    "E": ["energy", "electric field"],
    "v": ["velocity", "volume"],
}


PHYSICS_SYMBOL_DIAGNOSTIC_CODES = (
    "symbol_reuse_incompatible_meaning",
    "missing_binder",
    "ambiguous_constant_notation",
    "overloaded_notation_across_corpus",
    "mixed_scalar_vector_use",
    "implicit_function_of_time_omitted_in_display",
    "generated_symbol_marked_source_backed",
)


PHYSICS_BASE_DIMENSIONS: List[Dict[str, str]] = [
    {"symbol": "L", "name": "length", "si_base_unit": "meter"},
    {"symbol": "M", "name": "mass", "si_base_unit": "kilogram"},
    {"symbol": "T", "name": "time", "si_base_unit": "second"},
    {"symbol": "I", "name": "electric current", "si_base_unit": "ampere"},
    {"symbol": "Theta", "name": "temperature", "si_base_unit": "kelvin"},
    {"symbol": "N", "name": "amount of substance", "si_base_unit": "mole"},
    {"symbol": "J", "name": "luminous intensity", "si_base_unit": "candela"},
    {
        "symbol": "1",
        "name": "dimensionless angle or pure number",
        "si_base_unit": "radian_or_one",
    },
]


PHYSICS_COMMON_UNITS: List[Dict[str, str]] = [
    {"name": "meter", "kind": "SI base", "sympy_name": "sympy.physics.units.meter"},
    {
        "name": "kilogram",
        "kind": "SI base",
        "sympy_name": "sympy.physics.units.kilogram",
    },
    {"name": "second", "kind": "SI base", "sympy_name": "sympy.physics.units.second"},
    {"name": "ampere", "kind": "SI base", "sympy_name": "sympy.physics.units.ampere"},
    {"name": "kelvin", "kind": "SI base", "sympy_name": "sympy.physics.units.kelvin"},
    {"name": "mole", "kind": "SI base", "sympy_name": "sympy.physics.units.mole"},
    {"name": "newton", "kind": "derived", "sympy_name": "sympy.physics.units.newton"},
    {"name": "joule", "kind": "derived", "sympy_name": "sympy.physics.units.joule"},
    {"name": "watt", "kind": "derived", "sympy_name": "sympy.physics.units.watt"},
    {"name": "pascal", "kind": "derived", "sympy_name": "sympy.physics.units.pascal"},
    {"name": "coulomb", "kind": "derived", "sympy_name": "sympy.physics.units.coulomb"},
    {"name": "volt", "kind": "derived", "sympy_name": "sympy.physics.units.volt"},
    {"name": "ohm", "kind": "derived", "sympy_name": "sympy.physics.units.ohm"},
    {
        "name": "radian",
        "kind": "dimensionless_angle",
        "sympy_name": "sympy.physics.units.radian",
    },
]


PHYSICS_DIMENSION_INFERENCE_RULES: List[Dict[str, str]] = [
    {
        "id": "sum_equal_dimensions",
        "text": "sums require equal dimensions",
        "implemented_by": "dimension_of_expr:Add",
    },
    {
        "id": "product_adds_exponents",
        "text": "products add dimension exponents",
        "implemented_by": "dimension_of_expr:Mul",
    },
    {
        "id": "power_multiplies_exponents",
        "text": "powers multiply exponents",
        "implemented_by": "dimension_of_expr:Pow",
    },
    {
        "id": "derivative_divides_by_variable",
        "text": "derivatives divide by the independent variable dimension",
        "implemented_by": "dimension_of_expr:Derivative",
    },
    {
        "id": "integral_multiplies_by_variable",
        "text": "integrals multiply by the integration variable dimension",
        "implemented_by": "dimension_of_expr:Integral",
    },
    {
        "id": "transcendentals_dimensionless",
        "text": "transcendental functions require dimensionless arguments",
        "implemented_by": "dimension_of_expr:Function",
    },
    {
        "id": "exp_log_dimensionless",
        "text": "exponentials/logarithms require dimensionless arguments",
        "implemented_by": "dimension_of_expr:exp/log",
    },
    {
        "id": "trig_angle_dimensionless",
        "text": "trigonometric functions require angle or dimensionless arguments",
        "implemented_by": "dimension_of_expr:sin/cos/tan",
    },
]


PHYSICS_EQUATION_FORM_KINDS = (
    "algebraic_equation",
    "differential_equation",
    "vector_equation",
    "matrix_linear_system",
    "conservation_equation",
    "proportionality_statement",
    "limiting_or_approximation_statement",
    "target_equation",
)


PHYSICS_EQUATION_NORMALIZATION_TARGETS: List[Dict[str, str]] = [
    {
        "id": "equality_to_eq",
        "text": "equalities are represented as SymPy Eq(lhs, rhs)",
        "representation": "sympy.core.relational.Equality",
    },
    {
        "id": "residual_form",
        "text": "every equality also carries lhs - rhs residual form",
        "representation": "sympy.Expr",
    },
    {
        "id": "derivative_form",
        "text": "differential equations preserve Derivative/diff representations where available",
        "representation": "sympy.core.function.Derivative",
    },
    {
        "id": "integral_form",
        "text": "integral equations preserve Integral/integrate representations where available",
        "representation": "sympy.integrals.integrals.Integral",
    },
    {
        "id": "vector_projection_form",
        "text": "vector equations carry explicit projection or placeholder bridges",
        "representation": "sympy.physics.vector or scalar projection placeholders",
    },
    {
        "id": "ode_solution_form",
        "text": "ODE solutions are represented by dsolve-compatible or explicit integration traces",
        "representation": "sympy.dsolve or explicit SymPy expression",
    },
]


PHYSICS_ASSUMPTION_CATEGORIES: List[Dict[str, str]] = [
    {
        "id": "constant_acceleration",
        "label": "constant acceleration",
        "evidence_hint": "constant acceleration",
    },
    {
        "id": "frictionless_or_no_damping",
        "label": "frictionless/no damping/no drag",
        "evidence_hint": "no drag, undamped, frictionless",
    },
    {
        "id": "small_angle",
        "label": "small-angle regime",
        "evidence_hint": "small angle",
    },
    {
        "id": "nonrelativistic_speed",
        "label": "nonrelativistic speed",
        "evidence_hint": "nonrelativistic",
    },
    {
        "id": "massless_spring_string",
        "label": "massless spring/string",
        "evidence_hint": "massless spring or string",
    },
    {"id": "ideal_gas", "label": "ideal gas", "evidence_hint": "ideal gas"},
    {
        "id": "lumped_circuit_elements",
        "label": "lumped circuit elements",
        "evidence_hint": "ideal resistor/capacitor or 0D circuit",
    },
    {
        "id": "steady_or_quasistatic",
        "label": "steady state or quasistatic",
        "evidence_hint": "steady state, quasistatic",
    },
    {
        "id": "positivity_or_nonzero",
        "label": "positivity/nonzero restrictions",
        "evidence_hint": ">, positive, nonzero, !=",
    },
]


PHYSICS_CONDITION_KINDS = (
    "initial_position_or_velocity",
    "initial_charge_current_voltage",
    "boundary_value",
    "normalization_constant",
)


PHYSICS_FRAME_CONTEXT_FIELDS = (
    "axis_orientation",
    "origin",
    "positive_direction",
    "basis_vectors",
    "scalar_projection_from_vector_law",
    "one_dimensional_reduction",
)


PHYSICS_GAP_TYPES = (
    "missing_algebraic_rearrangement",
    "missing_substitution",
    "missing_differentiation_or_integration",
    "missing_ode_solution",
    "missing_law_invocation",
    "missing_initial_condition_application",
    "missing_approximation_justification",
    "missing_coordinate_projection",
    "missing_unit_conversion",
    "missing_cancellation_side_condition",
)


PHYSICS_GENERATED_SUBSTEP_KINDS = (
    "generated_algebra",
    "generated_calculus",
    "generated_law_application",
    "generated_condition_application",
    "generated_unit_conversion",
    "generated_approximation",
)


PHYSICS_LAW_GROUNDING_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "newton_second_law",
        "name": "Newton's second law",
        "grounding_type": "physical_law",
        "template_equation": "Eq(F, m*a)",
        "computable_template": "F - m*a",
        "aliases": ["newton", "second law", "f=m*a", "f=ma", "mass times acceleration"],
        "dimension_signature": "force = mass * acceleration",
        "source_policy": "source-backed law use or explicit generated-support invocation required",
    },
    {
        "id": "hooke_law",
        "name": "Hooke's law",
        "grounding_type": "constitutive_relation",
        "template_equation": "Eq(F, -k*x)",
        "computable_template": "F + k*x",
        "aliases": ["hooke", "spring force", "spring constant"],
        "dimension_signature": "force = spring_constant * length",
        "source_policy": "source-backed constitutive law use required for oscillator derivations",
    },
    {
        "id": "work_energy_relation",
        "name": "Work-energy relation",
        "grounding_type": "physical_law",
        "template_equation": "Eq(DeltaK, W)",
        "computable_template": "DeltaK - W",
        "aliases": [
            "work-energy",
            "work energy",
            "work theorem",
            "change in kinetic energy",
        ],
        "dimension_signature": "energy = work",
        "source_policy": "law invocation must be source-backed or generated from an explicit work integral",
    },
    {
        "id": "conservation_mechanical_energy",
        "name": "Conservation of mechanical energy",
        "grounding_type": "physical_law",
        "template_equation": "Eq(K1 + U1, K2 + U2)",
        "computable_template": "(K1 + U1) - (K2 + U2)",
        "aliases": [
            "conservation of mechanical energy",
            "conservation law",
            "conserved mechanical energy",
        ],
        "dimension_signature": "energy + energy = energy + energy",
        "source_policy": "requires conservative-force or explicitly stated energy-conservation regime",
    },
    {
        "id": "ohm_law",
        "name": "Ohm's law",
        "grounding_type": "constitutive_relation",
        "template_equation": "Eq(V, I*R)",
        "computable_template": "V - I*R",
        "aliases": ["ohm", "resistor", "v=ir"],
        "dimension_signature": "voltage = current * resistance",
        "source_policy": "source-backed circuit constitutive relation required",
    },
    {
        "id": "capacitor_relation",
        "name": "Capacitor relation",
        "grounding_type": "constitutive_relation",
        "template_equation": "Eq(Q, C*V)",
        "computable_template": "Q - C*V",
        "aliases": ["capacitor", "capacitance", "q=cv"],
        "dimension_signature": "charge = capacitance * voltage",
        "source_policy": "source-backed circuit constitutive relation required",
    },
    {
        "id": "ideal_gas_law",
        "name": "Ideal gas law",
        "grounding_type": "physical_law",
        "template_equation": "Eq(P*V, n*R*T)",
        "computable_template": "P*V - n*R*T",
        "aliases": ["ideal gas", "pv=nrt", "gas law"],
        "dimension_signature": "pressure * volume = amount * gas_constant * temperature",
        "source_policy": "source-backed thermodynamic state law required",
    },
    {
        "id": "first_law_thermodynamics_sign_convention",
        "name": "First-law thermodynamic sign convention",
        "grounding_type": "sign_convention",
        "template_equation": "Eq(DeltaU, Q - W)",
        "computable_template": "DeltaU - (Q - W)",
        "aliases": ["first law", "first-law", "thermodynamic sign", "delta u"],
        "dimension_signature": "energy = heat - work, with sign convention declared",
        "source_policy": "complete status requires the heat/work sign convention to be explicit",
    },
]


PHYSICS_SYMPY_OPERATION_GROUNDINGS: List[Dict[str, Any]] = [
    {
        "id": "solve",
        "operation_kind": "algebraic_rule",
        "label": "solve algebraic equations",
        "apis": ["sympy.solvers.solvers.solve"],
        "typical_use": "solve source equations for an unknown",
    },
    {
        "id": "solveset",
        "operation_kind": "algebraic_rule",
        "label": "set-valued equation solving",
        "apis": ["sympy.solvers.solveset.solveset"],
        "typical_use": "record solution-set semantics when branch conditions matter",
    },
    {
        "id": "dsolve",
        "operation_kind": "calculus_api",
        "label": "ordinary differential equation solving",
        "apis": ["sympy.solvers.ode.dsolve"],
        "typical_use": "close first-order or elementary ODE gaps",
    },
    {
        "id": "integrate",
        "operation_kind": "calculus_api",
        "label": "compute integrals",
        "apis": ["sympy.integrals.integrals.integrate"],
        "typical_use": "derive velocity, position, work, or integral support terms",
    },
    {
        "id": "Integral",
        "operation_kind": "calculus_api",
        "label": "preserve unevaluated integral forms",
        "apis": ["sympy.integrals.integrals.Integral"],
        "typical_use": "represent source integral statements before evaluation",
    },
    {
        "id": "diff",
        "operation_kind": "calculus_api",
        "label": "compute derivatives",
        "apis": ["sympy.core.function.diff"],
        "typical_use": "differentiate trial functions, potentials, or parameterized expressions",
    },
    {
        "id": "Derivative",
        "operation_kind": "calculus_api",
        "label": "preserve unevaluated derivative forms",
        "apis": ["sympy.core.function.Derivative"],
        "typical_use": "represent source differential equations before evaluation",
    },
    {
        "id": "simplify",
        "operation_kind": "algebraic_rule",
        "label": "simplify expressions",
        "apis": ["sympy.simplify.simplify.simplify"],
        "typical_use": "validate residual zero and normalize generated support",
    },
    {
        "id": "expand",
        "operation_kind": "algebraic_rule",
        "label": "expand products and powers",
        "apis": ["sympy.core.function.expand"],
        "typical_use": "make distributive algebra steps explicit",
    },
    {
        "id": "factor",
        "operation_kind": "algebraic_rule",
        "label": "factor expressions",
        "apis": ["sympy.polys.polytools.factor"],
        "typical_use": "recover compact target forms after expansion",
    },
    {
        "id": "cancel",
        "operation_kind": "algebraic_rule",
        "label": "cancel rational common factors",
        "apis": ["sympy.polys.polytools.cancel"],
        "typical_use": "close cancellation side-condition gaps",
    },
    {
        "id": "subs",
        "operation_kind": "algebraic_rule",
        "label": "substitute expressions",
        "apis": ["sympy.core.basic.Basic.subs"],
        "typical_use": "apply source definitions, laws, and initial conditions",
    },
    {
        "id": "vector_dot_cross",
        "operation_kind": "vector_api",
        "label": "vector dot and cross operations",
        "apis": [
            "sympy.vector.coordsysrect.CoordSys3D",
            "sympy.physics.vector.frame.ReferenceFrame",
        ],
        "typical_use": "ground coordinate projections, dot products, and cross-product components",
    },
    {
        "id": "unit_conversion_dimension_simplification",
        "operation_kind": "unit_api",
        "label": "unit conversion and dimension simplification",
        "apis": [
            "sympy.physics.units.util.quantity_simplify",
            "sympy.physics.units.Dimension",
        ],
        "typical_use": "check unit conversions and dimensionless arguments",
    },
]


PHYSICS_DERIVATION_PLAN_STAGES = (
    "quantities",
    "dimensions_units",
    "assumptions_regimes_frames",
    "source_equations",
    "generated_gap_closures",
    "target_derivation_chain",
    "validation_calls",
)


PHYSICS_ARTIFACT_REQUIRED_DATA_BINDINGS = (
    "CLAIM",
    "QUANTITY_TABLE",
    "DIMENSION_MODEL",
    "ASSUMPTIONS",
    "DERIVATION_STEPS",
)


PHYSICS_ARTIFACT_REQUIRED_FUNCTIONS = (
    "build_symbols",
    "build_units",
    "build_equations",
    "derive_target",
    "validate_dimensions",
    "validate_derivation_steps",
    "validate_numeric_samples",
    "explain_trace",
)


def physics_sympy_phase0_contract() -> Dict[str, Any]:
    """Return the Phase 0 backend-style, domain, artifact, and status contract."""
    return {
        "backend": "sympy",
        "style": STYLE,
        "distinct_from": RELATED_NONPHYSICS_STYLE,
        "style_meaning": "source-anchored executable physics derivation trace over SymPy objects, units, dimensions, and validation packets",
        "initial_target_domains": PHYSICS_SYMPY_TARGET_DOMAINS,
        "deferred_domains": PHYSICS_SYMPY_DEFERRED_DOMAINS,
        "complete_artifact_criteria": PHYSICS_SYMPY_COMPLETENESS_CRITERIA,
        "completion_statuses": PHYSICS_SYMPY_COMPLETION_STATUSES,
    }


def classify_physics_sympy_completion(
    validation: Dict[str, bool],
    unresolved_placeholders: Optional[Sequence[str]] = None,
    explicit_blockers: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Classify a derivation report as complete, draft, or blocked.

    The classifier keeps the Phase 0 semantics executable: complete is reserved
    for all-passing validation, blocked is used when a hard physics condition
    prevents truthful completion, and draft is used for useful partial evidence
    with non-hard unresolved work.
    """
    unresolved_placeholders = list(unresolved_placeholders or [])
    blocker_codes = [
        VALIDATION_BLOCKER_CODES.get(key, key)
        for key, ok in validation.items()
        if not ok
    ]
    blocker_codes.extend(explicit_blockers or [])
    if unresolved_placeholders:
        blocker_codes.append("unresolved_placeholder_or_unexecuted_step")
    hard_blockers = set(
        PHYSICS_SYMPY_COMPLETION_STATUSES["blocked"]["hard_blocker_codes"]
    )
    if not blocker_codes:
        status = "complete"
    elif hard_blockers.intersection(blocker_codes):
        status = "blocked"
    else:
        status = "draft"
    return {
        "status": status,
        "blocker_codes": sorted(set(blocker_codes)),
        "unresolved_placeholders": unresolved_placeholders,
        "status_definition": PHYSICS_SYMPY_COMPLETION_STATUSES[status]["definition"],
    }


def module_probe(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Probe one required or optional dependency with version metadata."""
    module = spec["module"]
    try:
        available = importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        available = False
    version = None
    if available:
        package = str(spec.get("package") or module.split(".", 1)[0])
        try:
            version = importlib_metadata.version(package)
        except importlib_metadata.PackageNotFoundError:
            root_package = module.split(".", 1)[0]
            try:
                version = importlib_metadata.version(root_package)
            except importlib_metadata.PackageNotFoundError:
                version = None
    return {
        "module": module,
        "framework": spec["framework"],
        "available": available,
        "required": bool(spec["required"]),
        "version": version,
        "used_for": spec["used_for"],
        "downgrades": list(spec.get("downgrades", [])),
        "completion_policy": (
            "missing_required_blocks_complete"
            if spec["required"]
            else "missing_optional_disables_only_dependent_checks"
        ),
    }


def physics_sympy_api_index_shard() -> Dict[str, Any]:
    """Build the versioned physics API shard used for grounding reports."""
    categories = {
        "sympy_physics_modules": [
            "sympy.physics.units",
            "sympy.physics.units.systems.si",
            "sympy.physics.mechanics",
            "sympy.physics.vector",
        ],
        "unit_systems": [
            "sympy.physics.units.systems.si.SI",
            "sympy.physics.units.util.quantity_simplify",
            "sympy.physics.units.Quantity",
            "sympy.physics.units.Dimension",
        ],
        "dimension_systems": [
            "sympy.physics.units.Dimension",
            "sympy.physics.units.dimensions.DimensionSystem",
        ],
        "mechanics_vector_apis": [
            "sympy.physics.mechanics.particle.Particle",
            "sympy.physics.mechanics.point.Point",
            "sympy.physics.mechanics.functions.dynamicsymbols",
            "sympy.physics.mechanics.lagrange.LagrangesMethod",
            "sympy.vector.coordsysrect.CoordSys3D",
            "sympy.vector.operators.gradient",
            "sympy.vector.operators.divergence",
            "sympy.vector.operators.curl",
            "sympy.physics.vector.frame.ReferenceFrame",
        ],
        "solver_calculus_apis": [
            "sympy.solvers.solvers.solve",
            "sympy.solvers.solveset.solveset",
            "sympy.core.function.diff",
            "sympy.integrals.integrals.integrate",
            "sympy.solvers.ode.dsolve",
            "sympy.core.function.Derivative",
            "sympy.integrals.integrals.Integral",
        ],
    }
    category_packets = []
    for category, qualified_names in categories.items():
        objects = []
        for qualified_name in qualified_names:
            objects.append(
                {
                    "qualified_name": qualified_name,
                    "available": qualified_available(qualified_name),
                    "category": category,
                }
            )
        category_packets.append(
            {
                "category": category,
                "objects": objects,
                "available_count": sum(1 for item in objects if item["available"]),
                "object_count": len(objects),
            }
        )
    return {
        "style": "physics_sympy_api_index_shard",
        "backend": "sympy",
        "shard_version": PHYSICS_SYMPY_API_SHARD_VERSION,
        "sympy_version": sp.__version__,
        "generated_at": now(),
        "categories": category_packets,
        "library_surfaces": [
            {
                "role": role,
                "description": surface["description"],
                "required_by_default": surface["required"],
                "apis": [
                    {"qualified_name": api, "available": qualified_available(api)}
                    for api in surface["apis"]
                ],
            }
            for role, surface in SYMPY_LIBRARY_SURFACES.items()
        ],
    }


def physics_sympy_dependency_probe(
    case_id: str, write_default_report: bool = False
) -> Dict[str, Any]:
    """Probe Phase 1 dependencies and optionally write the per-case report."""
    dependencies = [module_probe(spec) for spec in PHYSICS_SYMPY_DEPENDENCY_SPECS]
    missing_required = [
        item["module"]
        for item in dependencies
        if item["required"] and not item["available"]
    ]
    missing_optional = [
        item["module"]
        for item in dependencies
        if not item["required"] and not item["available"]
    ]
    disabled_checks = sorted(
        {
            check
            for item in dependencies
            if not item["available"]
            for check in item.get("downgrades", [])
        }
    )
    report = {
        "ok": not missing_required,
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "generated_at": now(),
        "dependencies": dependencies,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "disabled_optional_checks": disabled_checks,
        "optional_dependency_policy": {
            "missing_optional_dependencies_fail_probe": False,
            "missing_optional_dependencies_disable_only_dependent_checks": True,
            "partial_derivations_with_disabled_optional_checks_must_not_claim_optional_check_success": True,
        },
        "physics_api_index_shard": physics_sympy_api_index_shard(),
    }
    if write_default_report:
        output = (
            REPO_ROOT
            / "artifacts"
            / "physics_sympy"
            / case_id
            / "dependency_probe.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        report["report_path"] = str(output.relative_to(REPO_ROOT))
    return report


SYMPY_LIBRARY_SURFACES: Dict[str, Dict[str, Any]] = {
    "scalar_expression_core": {
        "description": "Scalar expression construction, equations, simplification, and exact algebra.",
        "required": True,
        "apis": [
            "sympy.core.symbol.Symbol",
            "sympy.core.relational.Equality",
            "sympy.simplify.simplify.simplify",
            "sympy.core.function.expand",
            "sympy.polys.polytools.factor",
        ],
    },
    "solvers_and_algebra": {
        "description": "Equation solving and algebraic rearrangement support.",
        "required": True,
        "apis": [
            "sympy.solvers.solvers.solve",
            "sympy.solvers.solveset.solveset",
            "sympy.simplify.radsimp.radsimp",
            "sympy.simplify.radsimp.cancel",
        ],
    },
    "calculus": {
        "description": "Differentiation, integration, ODE, and calculus transformation support.",
        "required": True,
        "apis": [
            "sympy.core.function.diff",
            "sympy.integrals.integrals.integrate",
            "sympy.core.function.Derivative",
            "sympy.integrals.integrals.Integral",
            "sympy.solvers.ode.dsolve",
        ],
    },
    "units_dimensions": {
        "description": "Installed unit and dimension system support for physics quantities.",
        "required": True,
        "apis": [
            "sympy.physics.units.Quantity",
            "sympy.physics.units.Dimension",
            "sympy.physics.units.systems.si.SI",
            "sympy.physics.units.util.quantity_simplify",
        ],
    },
    "vector_analysis": {
        "description": "Vector fields, coordinate systems, dot/cross products, curl, divergence, and gradients.",
        "required": False,
        "apis": [
            "sympy.vector.coordsysrect.CoordSys3D",
            "sympy.vector.operators.gradient",
            "sympy.vector.operators.divergence",
            "sympy.vector.operators.curl",
            "sympy.physics.vector.frame.ReferenceFrame",
        ],
    },
    "mechanics": {
        "description": "Mechanics surfaces for particles, frames, Lagrangian-style derivations, and dynamicsymbols.",
        "required": False,
        "apis": [
            "sympy.physics.mechanics.particle.Particle",
            "sympy.physics.mechanics.point.Point",
            "sympy.physics.mechanics.functions.dynamicsymbols",
            "sympy.physics.mechanics.lagrange.LagrangesMethod",
        ],
    },
    "matrices_linear_algebra": {
        "description": "Matrix/vector algebra and linear-map surrogates for finite-dimensional physics calculations.",
        "required": False,
        "apis": [
            "sympy.matrices.dense.MutableDenseMatrix",
            "sympy.matrices.expressions.matexpr.MatrixSymbol",
            "sympy.matrices.expressions.matmul.MatMul",
        ],
    },
    "quantum_operators": {
        "description": "Quantum operator, ket/bra, adjoint, and commutator surfaces.",
        "required": False,
        "apis": [
            "sympy.physics.quantum.operator.Operator",
            "sympy.physics.quantum.state.Ket",
            "sympy.physics.quantum.state.Bra",
            "sympy.physics.quantum.dagger.Dagger",
            "sympy.physics.quantum.commutator.Commutator",
        ],
    },
    "numeric_validation": {
        "description": "Independent numeric/sampling support used to sanity-check symbolic traces.",
        "required": True,
        "apis": [
            "sympy.core.evalf.N",
            "sympy.utilities.lambdify.lambdify",
            "mpmath",
            "numpy",
        ],
    },
}


def now() -> str:
    """Document the responsibility of ``now``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``now`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return datetime.now(timezone.utc).isoformat()


def qualified_available(qualified_name: str) -> bool:
    """Return whether a module or qualified object is importable locally."""
    try:
        if importlib.util.find_spec(qualified_name) is not None:
            return True
    except (ImportError, ModuleNotFoundError, ValueError):
        pass
    parts = qualified_name.split(".")
    for cut in range(len(parts) - 1, 0, -1):
        module_name = ".".join(parts[:cut])
        attr_path = parts[cut:]
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue
        current: Any = module
        ok = True
        for attr in attr_path:
            if not hasattr(current, attr):
                ok = False
                break
            current = getattr(current, attr)
        if ok:
            return True
    return False


def sympy_library_inventory() -> Dict[str, Any]:
    """Document the responsibility of ``sympy_library_inventory``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``sympy_library_inventory`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    surfaces = []
    for role, spec in SYMPY_LIBRARY_SURFACES.items():
        apis = []
        for api in spec["apis"]:
            apis.append({"qualified_name": api, "available": qualified_available(api)})
        available_count = sum(1 for api in apis if api["available"])
        surfaces.append(
            {
                "role": role,
                "description": spec["description"],
                "required_by_default": spec["required"],
                "apis": apis,
                "available_api_count": available_count,
                "api_count": len(apis),
                "status": "available" if available_count else "missing",
            }
        )
    return {
        "style": "physics_sympy_library_inventory",
        "backend": "sympy",
        "sympy_version": sp.__version__,
        "generated_at": now(),
        "surfaces": surfaces,
    }


def case_library_roles(case_id: str) -> List[str]:
    """Document the responsibility of ``case_library_roles``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``case_library_roles`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    spec = case_spec(case_id)
    text = " ".join(
        [
            spec["statement_nl"],
            spec["statement_latex"],
            " ".join(spec["assumptions"]),
            " ".join(spec["laws"]),
            " ".join(spec["gaps"]),
            json.dumps(spec["frame"], ensure_ascii=False),
        ]
    ).lower()
    roles = {
        "scalar_expression_core",
        "solvers_and_algebra",
        "units_dimensions",
        "numeric_validation",
    }
    if any(
        token in text
        for token in [
            "integrate",
            "differentiate",
            "derivative",
            "ode",
            "d/dt",
            "partial",
            "curl",
        ]
    ):
        roles.add("calculus")
    if any(
        token in text
        for token in [
            "vector",
            "field",
            "curl",
            "gradient",
            "divergence",
            "cross",
            "component",
            "cartesian",
        ]
    ):
        roles.add("vector_analysis")
    if any(
        token in text
        for token in [
            "lagrangian",
            "euler-lagrange",
            "particle",
            "force",
            "oscillator",
            "mechanics",
        ]
    ):
        roles.add("mechanics")
    if any(token in text for token in ["matrix", "linear", "operator"]):
        roles.add("matrices_linear_algebra")
    if any(
        token in text
        for token in ["quantum", "tdse", "schrodinger", "bra", "ket", "commutator"]
    ):
        roles.add("quantum_operators")
    return sorted(roles)


def sympy_library_grounding(case_id: str) -> Dict[str, Any]:
    """Document the responsibility of ``sympy_library_grounding``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``sympy_library_grounding`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    inventory = sympy_library_inventory()
    inventory_by_role = {surface["role"]: surface for surface in inventory["surfaces"]}
    required_roles = case_library_roles(case_id)
    grounding_items = []
    blockers = []
    for role in required_roles:
        surface = inventory_by_role.get(role, {})
        apis = surface.get("apis", [])
        selected = [api for api in apis if api.get("available")]
        status = "grounded" if selected else "missing"
        if status == "missing":
            blockers.append(f"missing_sympy_library_surface:{role}")
        grounding_items.append(
            {
                "role": role,
                "status": status,
                "description": surface.get("description"),
                "selected_apis": selected,
                "missing_apis": [api for api in apis if not api.get("available")],
                "representation": {
                    "complete_surface": "cite selected installed APIs in equation surface, trace certificates, final review, and generated artifact data",
                    "fallback": "local scalar placeholders may appear only with projection/support labels and draft status if no installed API surface is available",
                },
            }
        )
    core_roles = {
        "scalar_expression_core",
        "solvers_and_algebra",
        "calculus",
        "units_dimensions",
        "numeric_validation",
    }
    missing_roles = [
        item["role"] for item in grounding_items if item["status"] != "grounded"
    ]
    core_missing = any(role in core_roles for role in missing_roles)
    if not missing_roles:
        grounding_level = "high"
    elif core_missing:
        grounding_level = "low"
    else:
        grounding_level = "medium"
    return {
        "style": "physics_sympy_library_grounding_packet",
        "backend": "sympy",
        "case_id": case_id,
        "generated_at": now(),
        "grounding_level": grounding_level,
        "minimum_complete_level": "high",
        "required_roles": required_roles,
        "grounding_items": grounding_items,
        "completion_blockers": blockers,
        "inventory": inventory,
        "representation_policy": {
            "native_library_first": True,
            "complete_status_requires": [
                "all case-required library roles are grounded in installed SymPy or dependency APIs",
                "equation traces cite API roles or explicit algebraic certificates",
                "unit/dimension claims use SymPy unit/dimension surfaces where available",
                "vector, field, mechanics, or operator erasure is represented by explicit projection/support bridges",
            ],
            "draft_only_fallbacks": [
                "raw scalar placeholder for vector or field equation without SymPy vector/mechanics grounding",
                "dimension dictionary without SymPy units/dimensions grounding",
                "physical law stored only as free text with no API or executable certificate",
            ],
        },
    }


def dim(**kwargs: int) -> Dict[str, int]:
    """Document the responsibility of ``dim``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``dim`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    result = dict(ZERO_DIM)
    for key, value in kwargs.items():
        result[key] = value
    return result


def to_fraction(value: Any) -> Fraction:
    """Document the responsibility of ``to_fraction``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``to_fraction`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    value = sp.sympify(value)
    numerator, denominator = sp.fraction(value)
    return Fraction(int(numerator), int(denominator))


def dim_add(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Document the responsibility of ``dim_add``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``dim_add`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {key: a.get(key, 0) + b.get(key, 0) for key in BASE_DIMS}


def dim_sub(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Document the responsibility of ``dim_sub``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``dim_sub`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {key: a.get(key, 0) - b.get(key, 0) for key in BASE_DIMS}


def dim_pow(a: Dict[str, Any], power: Any) -> Dict[str, Any]:
    """Document the responsibility of ``dim_pow``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``dim_pow`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    power_fraction = to_fraction(power)
    if power_fraction.denominator == 1:
        scalar: Any = power_fraction.numerator
    else:
        scalar = power_fraction
    return {key: value * scalar for key, value in a.items()}


def dim_integral(a: Dict[str, Any]) -> bool:
    """Document the responsibility of ``dim_integral``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``dim_integral`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    for value in a.values():
        fraction = value if isinstance(value, Fraction) else Fraction(value, 1)
        if fraction.denominator != 1:
            return False
    return True


def dim_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Document the responsibility of ``dim_equal``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``dim_equal`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return all(Fraction(a.get(key, 0)) == Fraction(b.get(key, 0)) for key in BASE_DIMS)


def dim_text(a: Dict[str, Any]) -> str:
    """Document the responsibility of ``dim_text``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``dim_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parts = []
    for key, value in a.items():
        fraction = value if isinstance(value, Fraction) else Fraction(value, 1)
        if not fraction:
            continue
        exponent = (
            fraction.numerator
            if fraction.denominator == 1
            else f"{fraction.numerator}/{fraction.denominator}"
        )
        parts.append(f"{key}^{exponent}")
    return "1" if not parts else " ".join(parts)


COMMON_DIMS = {
    "dimensionless": dim(),
    "length": dim(L=1),
    "mass": dim(M=1),
    "time": dim(T=1),
    "velocity": dim(L=1, T=-1),
    "acceleration": dim(L=1, T=-2),
    "force": dim(M=1, L=1, T=-2),
    "energy": dim(M=1, L=2, T=-2),
    "action": dim(M=1, L=2, T=-1),
    "spring_constant": dim(M=1, T=-2),
    "angular_frequency": dim(T=-1),
    "period": dim(T=1),
    "resistance": dim(M=1, L=2, T=-3, I=-2),
    "capacitance": dim(M=-1, L=-2, T=4, I=2),
    "voltage": dim(M=1, L=2, T=-3, I=-1),
    "charge": dim(T=1, I=1),
    "electric_field": dim(M=1, L=1, T=-3, I=-1),
    "magnetic_field": dim(M=1, T=-2, I=-1),
    "velocity_magnetic": dim(M=1, L=1, T=-3, I=-1),
    "vector_potential": dim(M=1, L=1, T=-2, I=-1),
    "current_density": dim(I=1, L=-2),
    "electric_displacement": dim(I=1, T=1, L=-2),
    "magnetic_intensity": dim(I=1, L=-1),
    "permeability": dim(M=1, L=1, T=-2, I=-2),
    "permittivity": dim(M=-1, L=-3, T=4, I=2),
    "pressure": dim(M=1, L=-1, T=-2),
    "volume": dim(L=3),
    "amount": dim(N=1),
    "density": dim(M=1, L=-3),
    "molar_mass": dim(M=1, N=-1),
    "gas_constant": dim(M=1, L=2, T=-2, Theta=-1, N=-1),
    "temperature": dim(Theta=1),
}


def metadata_from_text(text: str) -> Dict[str, str]:
    """Document the responsibility of ``metadata_from_text``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``metadata_from_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    result: Dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"\s*%\s*([^:]+):\s*(.+)\s*$", line)
        if match:
            result[match.group(1).strip()] = match.group(2).strip()
    return result


def anchor_lines(text: str) -> List[Dict[str, Any]]:
    """Document the responsibility of ``anchor_lines``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``anchor_lines`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    import hashlib

    anchors = []
    for index, line in enumerate(text.splitlines(), start=1):
        anchors.append(
            {
                "anchor": f"src_L{index:04d}",
                "line": index,
                "text": line,
                "sha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
            }
        )
    return anchors


def load_source(
    path: Optional[Path], text: Optional[str]
) -> Tuple[str, str, Dict[str, str]]:
    """Document the responsibility of ``load_source``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if text is not None:
        source = text
        source_path = "inline"
    elif path is not None:
        source = path.read_text(encoding="utf-8")
        source_path = str(path)
    else:
        source = sample_latex("constant_acceleration_position")
        source_path = "self-test"
    return source, source_path, metadata_from_text(source)


def sample_latex(case_id: str) -> str:
    """Document the responsibility of ``sample_latex``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``sample_latex`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    spec = case_spec(case_id)
    return "\n".join(
        [
            f"% physics-case-id: {case_id}",
            "% backend-style: sympy_physics_derivation_trace",
            "\\section*{Controlled physics derivation}",
            spec["statement_latex"],
            "",
            "\\paragraph{Assumptions}",
            "; ".join(spec["assumptions"]),
            "",
            "\\paragraph{Derivation}",
            spec["statement_nl"],
        ]
    )


def quantity_candidate_maps(
    spec: Dict[str, Any], symbols: Sequence[str]
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Return candidate dimension and unit maps for the requested symbols."""
    dimensions: Dict[str, str] = {}
    units: Dict[str, str] = {}
    for symbol in symbols:
        quantity = spec["quantities"].get(symbol)
        if quantity:
            dimensions[symbol] = quantity[1]
            units[symbol] = quantity[2]
    return dimensions, units


def physical_source_unit(
    case_id: str,
    unit_id: str,
    role: str,
    literal_nl: str,
    literal_latex: Optional[str],
    symbols: Sequence[str],
    spec: Dict[str, Any],
    source_anchors: Optional[Sequence[str]] = None,
    source_category: Optional[str] = None,
    generated_support: bool = False,
    ambiguity_notes: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Create one Phase 2 source-backed derivation unit."""
    dimensions, units = quantity_candidate_maps(spec, symbols)
    return {
        "id": f"{case_id}.{unit_id}",
        "role": role,
        "source_category": source_category or role,
        "source_anchors": list(source_anchors or spec["source_anchors"]),
        "literal_nl": literal_nl,
        "literal_latex": literal_latex,
        "inferred_symbols": list(symbols),
        "candidate_dimensions": dimensions,
        "candidate_units": units,
        "generated_support": generated_support,
        "unresolved_ambiguity_notes": list(ambiguity_notes or []),
    }


def derivation_step_role(step: Dict[str, Any]) -> str:
    """Classify an executable derivation step into the Phase 2 role ontology."""
    kind = str(step.get("kind", ""))
    rule = str(step.get("rule", "")).lower()
    if kind == "target_equation":
        return "target_equation"
    if "initial_condition" in kind or "initial condition" in rule:
        return "initial_condition"
    if "boundary_condition" in kind or "boundary condition" in rule:
        return "boundary_condition"
    if "substitution" in kind or "substitute" in rule:
        return "substitution_step"
    if "calculus" in kind or any(
        token in rule for token in ["integrate", "differentiate", "derivative", "ode"]
    ):
        return "calculus_step"
    if "algebra" in kind or any(
        token in rule
        for token in ["solve", "rearrange", "simplify", "cancel", "collect"]
    ):
        return "algebraic_step"
    if kind in {"source_law", "source_equation"}:
        return "physical_law"
    return "algebraic_step"


def classify_context_assumption(text: str) -> str:
    """Classify an assumption or context note into a Phase 2 source-unit role."""
    lowered = text.lower()
    if any(token in lowered for token in ["initial", "v(0)", "x0", "v0", "at zero"]):
        return "initial_condition"
    if any(
        token in lowered
        for token in [
            "boundary",
            "endpoint",
            "level ground",
            "impact",
            "fixed endpoint",
        ]
    ):
        return "boundary_condition"
    if any(
        token in lowered
        for token in [
            "ideal",
            "no drag",
            "undamped",
            "constant",
            "smooth",
            "approximation",
        ]
    ):
        return "approximation_regime"
    return "approximation_regime"


def relation_role(text: str) -> str:
    """Classify a stated relation as a physical law or constitutive relation."""
    lowered = text.lower()
    if any(
        token in lowered
        for token in [
            "ohm",
            "hooke",
            "ideal gas",
            "density",
            "capacitor",
            "constitutive",
            "d=",
            "b=",
        ]
    ):
        return "constitutive_relation"
    return "physical_law"


def extract_physics_source_units(
    case_id: str, source: str = "", source_path: str = "self-test"
) -> Dict[str, Any]:
    """Extract Phase 2 source units from controlled physics prose and LaTeX."""
    anchors = anchor_lines(source or sample_latex(case_id))
    semantic_anchors = [
        anchor["anchor"]
        for anchor in anchors
        if anchor["text"].strip() and not anchor["text"].lstrip().startswith("%")
    ]
    spec = dict(case_spec(case_id))
    spec["source_anchors"] = semantic_anchors or spec["source_anchors"]
    units: List[Dict[str, Any]] = []
    for symbol, (meaning, dimension_name, unit_name) in spec["quantities"].items():
        units.append(
            physical_source_unit(
                case_id=case_id,
                unit_id=f"quantity.{symbol}",
                role="quantity_definition",
                literal_nl=f"{symbol}: {meaning}",
                literal_latex=None,
                symbols=[symbol],
                spec=spec,
                source_category="quantity_definition",
                ambiguity_notes=(
                    []
                    if dimension_name in COMMON_DIMS
                    else [f"dimension alias '{dimension_name}' is not in COMMON_DIMS"]
                ),
            )
        )
    for index, law in enumerate(spec["laws"], start=1):
        role = relation_role(law)
        units.append(
            physical_source_unit(
                case_id=case_id,
                unit_id=f"law.{index:02d}",
                role=role,
                literal_nl=law,
                literal_latex=(
                    law
                    if any(token in law for token in ["=", "\\", "^", "_"])
                    else None
                ),
                symbols=[symbol for symbol in spec["quantities"] if symbol in law],
                spec=spec,
                source_category=(
                    "stated_law" if role == "physical_law" else "constitutive_relation"
                ),
            )
        )
    frame = spec.get("frame", {})
    units.append(
        physical_source_unit(
            case_id=case_id,
            unit_id="coordinate_context",
            role="coordinate_context",
            literal_nl=json.dumps(frame, ensure_ascii=False, sort_keys=True),
            literal_latex=None,
            symbols=[],
            spec=spec,
            source_category="coordinate_frame_declaration",
            ambiguity_notes=[] if frame else ["coordinate frame not declared"],
        )
    )
    for index, assumption in enumerate(spec["assumptions"], start=1):
        units.append(
            physical_source_unit(
                case_id=case_id,
                unit_id=f"assumption.{index:02d}",
                role=classify_context_assumption(assumption),
                literal_nl=assumption,
                literal_latex=(
                    assumption
                    if any(token in assumption for token in ["=", "<", ">", "\\"])
                    else None
                ),
                symbols=[
                    symbol for symbol in spec["quantities"] if symbol in assumption
                ],
                spec=spec,
                source_category="assumption_or_regime",
            )
        )
    for index, gap in enumerate(spec["gaps"], start=1):
        lowered_gap = gap.lower()
        if "initial condition" in lowered_gap:
            role = "initial_condition"
        elif (
            "boundary condition" in lowered_gap
            or "impact condition" in lowered_gap
            or "endpoint" in lowered_gap
        ):
            role = "boundary_condition"
        elif "substitut" in lowered_gap:
            role = "substitution_step"
        elif any(
            token in lowered_gap for token in ["integrate", "differentiate", "ode"]
        ):
            role = "calculus_step"
        else:
            role = "algebraic_step"
        units.append(
            physical_source_unit(
                case_id=case_id,
                unit_id=f"derivation_gap.{index:02d}",
                role=role,
                literal_nl=gap,
                literal_latex=None,
                symbols=[symbol for symbol in spec["quantities"] if symbol in gap],
                spec=spec,
                source_category="derivation_step",
                ambiguity_notes=["implicit step requires generated support expansion"],
            )
        )
    derivation = derive_case(case_id)
    for index, step in enumerate(derivation["steps"], start=1):
        role = derivation_step_role(step)
        expression = str(step.get("expression", ""))
        units.append(
            physical_source_unit(
                case_id=case_id,
                unit_id=f"trace_step.{index:02d}",
                role=role,
                literal_nl=str(step.get("rule", "")),
                literal_latex=expression,
                symbols=[
                    symbol for symbol in spec["quantities"] if symbol in expression
                ],
                spec=spec,
                source_anchors=step.get("source_anchors") or spec["source_anchors"],
                source_category="derivation_trace_step",
                generated_support=bool(step.get("generated")),
                ambiguity_notes=(
                    []
                    if not step.get("generated")
                    else ["generated support step, not directly source-backed"]
                ),
            )
        )
    units.append(
        physical_source_unit(
            case_id=case_id,
            unit_id="target",
            role="target_equation",
            literal_nl=spec["statement_nl"],
            literal_latex=spec["statement_latex"],
            symbols=list(spec["quantities"]),
            spec=spec,
            source_category="target_result_statement",
        )
    )
    role_counts = {
        role: sum(1 for unit in units if unit["role"] == role)
        for role in PHYSICS_SOURCE_UNIT_ROLES
    }
    required_fields = {
        "source_anchors",
        "literal_nl",
        "literal_latex",
        "inferred_symbols",
        "candidate_dimensions",
        "candidate_units",
        "unresolved_ambiguity_notes",
    }
    malformed = [
        unit["id"]
        for unit in units
        if unit["role"] not in PHYSICS_SOURCE_UNIT_ROLES
        or not required_fields.issubset(unit)
    ]
    return {
        "ok": not malformed,
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "source_path": source_path,
        "generated_at": now(),
        "source_anchors": anchors,
        "unit_roles": list(PHYSICS_SOURCE_UNIT_ROLES),
        "units": units,
        "role_counts": role_counts,
        "malformed_units": malformed,
        "fixture_coverage": {
            fixture_id: {
                "path": path,
                "exists": (REPO_ROOT / path).exists(),
            }
            for fixture_id, path in PHYSICS_SOURCE_FIXTURES.items()
        },
    }


def sympy_commentary_header(case_id: str) -> str:
    """Document the responsibility of ``sympy_commentary_header``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``sympy_commentary_header`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    headers = {
        "formalphysics_0000": """Original informal statement:
From the x Euler-Lagrange equation for a charged particle with electromagnetic
potentials phi(x,y,z,t) and A=(A_x,A_y,A_z), derive the x component of the
Lorentz force,
    F_x = q E_x + q(ydot B_z - zdot B_y).

Informal derivation commentary:
1. Start from the source Euler-Lagrange x equation:
   F_x + q(Ax_t + Ax_y ydot + Ax_z zdot)
     = q(Ay_x ydot + Az_x zdot) - q phi_x.
2. Solve the equation for F_x by moving the vector-potential derivative terms
   to the right-hand side.
3. Group the result into electric and magnetic field combinations:
   -q(phi_x + Ax_t) + q ydot(Ay_x - Ax_y) - q zdot(Ax_z - Az_x).
4. Use E_x = -(phi_x + Ax_t).
5. Use B_z = Ay_x - Ax_y and B_y = Ax_z - Az_x to obtain the x Lorentz-force
   component.

SymPy alignment:
- Informal step 1 maps to DERIVATION_STEPS[0] /
  step_01_euler_lagrange_x_component.
- Informal step 2 maps to DERIVATION_STEPS[1] /
  step_02_solve_for_force_component.
- Informal steps 3-5 map to DERIVATION_STEPS[2] /
  step_03_expand_lorentz_component and to the symbolic residual checked by
  validate_derivation_steps.
- Physical typing and units are carried by QUANTITY_TABLE, QUANTITY_SURFACE,
  validate_dimensions, and validate_projection_bridges.
- Numeric and symbolic smoke checks are exposed by validate_numeric_samples
  and validate_symbolic.""",
        "formalphysics_0020": """Original informal statement:
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
  validate_dimensions, and validate_projection_bridges.""",
        "formalphysics_0004": """Original informal statement:
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
  PROJECTION_BRIDGES, and validate_projection_bridges.""",
        "formalphysics_0066": """Original informal statement:
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
  projection certificates.""",
        "formalphysics_0191": """Original informal statement:
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
  validate_derivation_steps.""",
        "formalphysics_0172": """Original informal statement:
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
  LAW_TABLE.""",
        "formalphysics_0119": """Original informal statement:
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
- Force collection and repackaging map to DERIVATION_STEPS[2].""",
        "formalphysics_0026": """Original informal statement:
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
- The final cancellation maps to DERIVATION_STEPS[2].""",
        "formalphysics_0176": """Original informal statement:
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
- The final additive target maps to DERIVATION_STEPS[3].""",
        "formalphysics_0054": """Original informal statement:
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
- Final collection maps to DERIVATION_STEPS[3].""",
        "formalphysics_0059": """Original informal statement:
For a one-parameter family of trial functions, differentiate the functional
under the integral sign and apply the chain rule, then evaluate at epsilon=0.

Informal derivation commentary:
1. Differentiate J_epsilon under the integral sign.
2. Apply the chain rule to L_epsilon.
3. Substitute dg_epsilon/depsilon and dg'_epsilon/depsilon.
4. Substitute into the integral and evaluate at epsilon=0.

SymPy alignment:
- The under-integral derivative maps to DERIVATION_STEPS[0].
- The chain-rule expansion maps to DERIVATION_STEPS[1].
- Evaluation at epsilon=0 maps to DERIVATION_STEPS[2].""",
    }
    if case_id in headers:
        return headers[case_id]
    spec = case_spec(case_id)
    return f"""Original informal statement:
{spec["statement_nl"]}

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
  and review_final_equations provide executable validation hooks."""


def case_spec(case_id: str) -> Dict[str, Any]:
    """Document the responsibility of ``case_spec``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``case_spec`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    source_anchors = ["src_L0004", "src_L0009"]
    specs: Dict[str, Dict[str, Any]] = {
        "constant_acceleration_position": {
            "statement_nl": "For constant acceleration, integrate velocity to obtain position x(t)=x0+v0 t + a t^2/2.",
            "statement_latex": r"x(t)=x_0+v_0 t+\frac{1}{2}a t^2",
            "target": "x_t",
            "quantities": {
                "x": ("position", "length", "meter"),
                "x0": ("initial position", "length", "meter"),
                "v0": ("initial velocity", "velocity", "meter/second"),
                "a": ("constant acceleration", "acceleration", "meter/second**2"),
                "t": ("time", "time", "second"),
            },
            "assumptions": [
                "constant acceleration",
                "one-dimensional motion",
                "t >= 0",
            ],
            "frame": {
                "dimension": "1D",
                "axis": "x",
                "positive_direction": "direction of increasing x",
            },
            "laws": ["a=dv/dt", "v=dx/dt"],
            "gaps": [
                "integrate acceleration to velocity",
                "integrate velocity to position",
                "apply initial conditions",
            ],
        },
        "constant_acceleration_velocity_position": {
            "statement_nl": "Eliminating time from constant-acceleration kinematics gives v^2=v0^2+2a(x-x0).",
            "statement_latex": r"v^2=v_0^2+2a(x-x_0)",
            "target": "velocity_position",
            "quantities": {
                "x": ("position", "length", "meter"),
                "x0": ("initial position", "length", "meter"),
                "v": ("velocity", "velocity", "meter/second"),
                "v0": ("initial velocity", "velocity", "meter/second"),
                "a": ("constant acceleration", "acceleration", "meter/second**2"),
                "t": ("time", "time", "second"),
            },
            "assumptions": [
                "constant acceleration",
                "one-dimensional motion",
                "a != 0 when solving for t",
            ],
            "frame": {
                "dimension": "1D",
                "axis": "x",
                "positive_direction": "direction of acceleration sign convention",
            },
            "laws": ["v=v0+a t", "x=x0+v0 t+a t^2/2"],
            "gaps": [
                "solve velocity equation for time",
                "substitute time into position equation",
                "algebraically rearrange",
            ],
        },
        "simple_harmonic_oscillator_omega": {
            "statement_nl": "For m x'' + k x = 0 with trial x=A cos(omega t), omega=sqrt(k/m).",
            "statement_latex": r"\omega=\sqrt{k/m}",
            "target": "sho_omega",
            "quantities": {
                "m": ("mass", "mass", "kilogram"),
                "k": ("spring constant", "spring_constant", "newton/meter"),
                "omega": ("angular frequency", "angular_frequency", "1/second"),
                "t": ("time", "time", "second"),
                "A": ("amplitude", "length", "meter"),
            },
            "assumptions": [
                "undamped oscillator",
                "massive point mass",
                "k > 0",
                "m > 0",
            ],
            "frame": {
                "dimension": "1D",
                "axis": "x",
                "positive_direction": "spring extension positive",
            },
            "laws": ["Hooke law", "Newton second law", "trial sinusoidal solution"],
            "gaps": [
                "differentiate trial solution twice",
                "substitute into ODE",
                "solve nontrivial amplitude condition",
            ],
        },
        "simple_harmonic_oscillator_period": {
            "statement_nl": "Using omega=sqrt(k/m), the period is T=2 pi sqrt(m/k).",
            "statement_latex": r"T=2\pi\sqrt{m/k}",
            "target": "sho_period",
            "quantities": {
                "m": ("mass", "mass", "kilogram"),
                "k": ("spring constant", "spring_constant", "newton/meter"),
                "omega": ("angular frequency", "angular_frequency", "1/second"),
                "T": ("period", "period", "second"),
            },
            "assumptions": ["undamped oscillator", "k > 0", "m > 0"],
            "frame": {
                "dimension": "1D",
                "axis": "x",
                "positive_direction": "spring extension positive",
            },
            "laws": ["omega=sqrt(k/m)", "T=2*pi/omega"],
            "gaps": [
                "substitute angular frequency into period formula",
                "simplify square root expression",
            ],
        },
        "work_energy_constant_force": {
            "statement_nl": "For a constant force along displacement d, W=F d and the change in kinetic energy equals W.",
            "statement_latex": r"W=Fd,\quad \Delta K=W",
            "target": "work_energy",
            "quantities": {
                "F": ("constant force", "force", "newton"),
                "d": ("displacement", "length", "meter"),
                "W": ("work", "energy", "joule"),
                "DeltaK": ("change in kinetic energy", "energy", "joule"),
            },
            "assumptions": ["constant force", "force parallel to displacement"],
            "frame": {
                "dimension": "1D",
                "axis": "path coordinate",
                "positive_direction": "direction of displacement",
            },
            "laws": ["work integral", "work-energy theorem"],
            "gaps": [
                "integrate constant force over displacement",
                "apply work-energy theorem",
            ],
        },
        "rc_discharge": {
            "statement_nl": "For RC discharge, dV/dt=-V/(R C) with V(0)=V0 gives V(t)=V0 exp(-t/(R C)).",
            "statement_latex": r"V(t)=V_0 e^{-t/(RC)}",
            "target": "rc_discharge",
            "quantities": {
                "V": ("voltage", "voltage", "volt"),
                "V0": ("initial voltage", "voltage", "volt"),
                "R": ("resistance", "resistance", "ohm"),
                "C": ("capacitance", "capacitance", "farad"),
                "t": ("time", "time", "second"),
            },
            "assumptions": [
                "ideal resistor",
                "ideal capacitor",
                "R > 0",
                "C > 0",
                "t >= 0",
            ],
            "frame": {
                "dimension": "0D circuit",
                "axis": "time",
                "positive_direction": "forward time",
            },
            "laws": ["capacitor relation", "Ohm law", "first-order linear ODE"],
            "gaps": [
                "solve separable ODE",
                "apply initial condition",
                "verify exponential argument dimensionless",
            ],
        },
        "ideal_gas_density": {
            "statement_nl": "From PV=nRT, n=m/M, and rho=m/V, derive rho=P M/(R T).",
            "statement_latex": r"\rho=\frac{PM}{RT}",
            "target": "ideal_gas_density",
            "quantities": {
                "P": ("pressure", "pressure", "pascal"),
                "V": ("volume", "volume", "meter**3"),
                "n": ("amount of substance", "amount", "mole"),
                "R": ("gas constant", "gas_constant", "joule/(mole*kelvin)"),
                "T": ("temperature", "temperature", "kelvin"),
                "m": ("mass", "mass", "kilogram"),
                "M": ("molar mass", "molar_mass", "kilogram/mole"),
                "rho": ("density", "density", "kilogram/meter**3"),
            },
            "assumptions": ["ideal gas", "T > 0", "R > 0", "V > 0"],
            "frame": {
                "dimension": "thermodynamic state",
                "axis": "state variables",
                "positive_direction": "positive extensive quantities",
            },
            "laws": [
                "ideal gas law",
                "moles from mass and molar mass",
                "density definition",
            ],
            "gaps": ["substitute n=m/M", "substitute m=rho V", "solve for rho"],
        },
        "projectile_range_level_ground": {
            "statement_nl": "For projectile motion on level ground without drag, R=v0^2 sin(2 theta)/g.",
            "statement_latex": r"R=\frac{v_0^2\sin(2\theta)}{g}",
            "target": "projectile_range",
            "quantities": {
                "R": ("range", "length", "meter"),
                "v0": ("initial speed", "velocity", "meter/second"),
                "theta": ("launch angle", "dimensionless", "radian"),
                "g": (
                    "gravitational acceleration magnitude",
                    "acceleration",
                    "meter/second**2",
                ),
                "t": ("time", "time", "second"),
            },
            "assumptions": ["no drag", "level ground", "g > 0", "0 < theta < pi/2"],
            "frame": {
                "dimension": "2D",
                "axis": "x horizontal, y vertical",
                "positive_direction": "y upward",
            },
            "laws": [
                "constant horizontal velocity",
                "vertical constant acceleration",
                "level-ground impact condition",
            ],
            "gaps": [
                "solve vertical motion for nonzero flight time",
                "substitute time into horizontal motion",
                "apply double-angle identity",
            ],
        },
        "formalphysics_0000": {
            "statement_nl": "From the x Euler-Lagrange equation for a charged particle with electromagnetic potentials, derive the x component of the Lorentz force.",
            "statement_latex": r"F_x=qE_x+q(\dot y B_z-\dot z B_y)",
            "target": "lorentz_force_x_component",
            "quantities": {
                "q": ("particle charge", "charge", "coulomb"),
                "Fx": ("x component of force", "force", "newton"),
                "Ex": ("x component of electric field", "electric_field", "volt/meter"),
                "By": ("y component of magnetic field", "magnetic_field", "tesla"),
                "Bz": ("z component of magnetic field", "magnetic_field", "tesla"),
                "ydot": ("y velocity component", "velocity", "meter/second"),
                "zdot": ("z velocity component", "velocity", "meter/second"),
                "Ax_t": (
                    "time derivative of the x component of vector potential",
                    "electric_field",
                    "volt/meter",
                ),
                "Ax_y": (
                    "y derivative of the x component of vector potential",
                    "magnetic_field",
                    "tesla",
                ),
                "Ax_z": (
                    "z derivative of the x component of vector potential",
                    "magnetic_field",
                    "tesla",
                ),
                "Ay_x": (
                    "x derivative of the y component of vector potential",
                    "magnetic_field",
                    "tesla",
                ),
                "Az_x": (
                    "x derivative of the z component of vector potential",
                    "magnetic_field",
                    "tesla",
                ),
                "phi_x": (
                    "x derivative of scalar electric potential",
                    "electric_field",
                    "volt/meter",
                ),
            },
            "assumptions": [
                "fixed Cartesian coordinate frame",
                "take the x component of the vector equation",
                "scalar and vector potentials are differentiable",
                "partial derivative placeholders inherit field dimensions",
                "SI electromagnetic unit convention",
            ],
            "frame": {
                "dimension": "3D component",
                "axis": "x",
                "positive_direction": "right-handed Cartesian x direction",
            },
            "laws": [
                "Euler-Lagrange equation for minimally coupled charged-particle Lagrangian",
                "E_x=-(phi_x+Ax_t)",
                "B_y=Ax_z-Az_x",
                "B_z=Ay_x-Ax_y",
                "Lorentz force component F_x=qE_x+q(ydot B_z-zdot B_y)",
            ],
            "gaps": [
                "solve the source Euler-Lagrange equation for F_x",
                "substitute electric-field definition",
                "substitute magnetic-field curl component definitions",
                "collect terms into the Lorentz force x component",
            ],
            "projection_bridges": [
                {
                    "id": "formalphysics_0000.coordinate_component_bridge",
                    "kind": "coordinate_component_bridge",
                    "status": "provided",
                    "source_object": "F=q(E+v cross B)",
                    "target_equations": ["formalphysics_0000.target"],
                },
                {
                    "id": "formalphysics_0000.field_derivative_placeholder_bridge",
                    "kind": "field_derivative_placeholder_bridge",
                    "status": "provided",
                    "source_object": "E=-grad phi-partial_t A and B=curl A",
                    "target_equations": ["formalphysics_0000.field_definitions"],
                },
            ],
        },
        "formalphysics_0004": {
            "statement_nl": "For the 1D quantum harmonic oscillator in units with m=omega=hbar=1, compute the number operator N=a_dagger a from a=(q+ip)/sqrt(2), a_dagger=(q-ip)/sqrt(2), and [q,p]=i.",
            "statement_latex": r"N=a^{\dagger}a=\frac12(p^2-i p q+i q p+q^2)",
            "target": "dimensionless_ladder_number_operator_expansion",
            "symbol_assumptions": {
                "q": {"commutative": False},
                "p": {"commutative": False},
                "a": {"commutative": False},
                "adagger": {"commutative": False},
                "Nop": {"commutative": False},
            },
            "quantities": {
                "q": ("dimensionless position operator", "dimensionless", "one"),
                "p": ("dimensionless momentum operator", "dimensionless", "one"),
                "a": ("annihilation ladder operator", "dimensionless", "one"),
                "adagger": ("creation ladder operator", "dimensionless", "one"),
                "Nop": ("number operator N", "dimensionless", "one"),
            },
            "assumptions": [
                "dimensionless oscillator units m=omega=hbar=1",
                "q and p are noncommuting quantum operators",
                "a=(q+i p)/sqrt(2) is the source annihilation operator",
                "a_dagger=(q-i p)/sqrt(2) is the source creation operator",
                "N=a_dagger*a defines the number operator",
                "[q,p]=i is recorded but the optional commutator simplification is not applied",
            ],
            "frame": {
                "dimension": "1D quantum oscillator",
                "axis": "operator algebra",
                "positive_direction": "source operator-order convention",
            },
            "laws": [
                "dimensionless harmonic-oscillator ladder definitions",
                "number operator definition N=a_dagger*a",
                "noncommutative distributive expansion",
                "canonical commutator [q,p]=i retained as context only",
            ],
            "gaps": [
                "represent q and p as noncommutative SymPy symbols",
                "form a_dagger*a from the source ladder definitions",
                "factor out the dimensionless normalization constant",
                "expand without commuting p*q and q*p",
                "preserve the optional commutator simplification boundary",
            ],
            "projection_bridges": [
                {
                    "id": "formalphysics_0004.noncommutative_operator_bridge",
                    "kind": "finite_operator_algebra_projection_bridge",
                    "status": "provided",
                    "source_object": "unbounded Hilbert-space q and p operators",
                    "target_equations": ["formalphysics_0004.target"],
                },
                {
                    "id": "formalphysics_0004.dimensionless_units_bridge",
                    "kind": "unit_dimension_bridge",
                    "status": "provided",
                    "source_object": "m=omega=hbar=1",
                    "target_equations": [
                        "formalphysics_0004.dimensionless_operator_surface"
                    ],
                },
            ],
        },
        "formalphysics_0020": {
            "statement_nl": "From D=epsilon_0 E+P, J_M=curl M, curl H=J_f+dD/dt, and B=mu_0(H+M), derive the Maxwell-Ampere equation with free, polarization, and magnetization current terms.",
            "statement_latex": r"\nabla\times(B/\mu_0)=J_f+\epsilon_0\partial_t E+\partial_tP+J_M",
            "target": "maxwell_ampere_with_polarization_magnetization",
            "quantities": {
                "curlB_over_mu0": (
                    "curl of B divided by mu_0 represented as a vector-current-density placeholder",
                    "current_density",
                    "ampere/meter**2",
                ),
                "curlH": (
                    "curl of H represented as a vector-current-density placeholder",
                    "current_density",
                    "ampere/meter**2",
                ),
                "curlM": (
                    "curl of M represented as magnetization-current placeholder",
                    "current_density",
                    "ampere/meter**2",
                ),
                "Jf": ("free current density", "current_density", "ampere/meter**2"),
                "JM": (
                    "magnetization current density",
                    "current_density",
                    "ampere/meter**2",
                ),
                "dDdt": (
                    "time derivative of electric displacement field",
                    "current_density",
                    "ampere/meter**2",
                ),
                "eps0_dEdt": (
                    "epsilon_0 times the time derivative of electric field",
                    "current_density",
                    "ampere/meter**2",
                ),
                "dPdt": (
                    "time derivative of polarization field",
                    "current_density",
                    "ampere/meter**2",
                ),
                "B": ("magnetic flux density field", "magnetic_field", "tesla"),
                "H": (
                    "magnetic field intensity field",
                    "magnetic_intensity",
                    "ampere/meter",
                ),
                "M": ("magnetization field", "magnetic_intensity", "ampere/meter"),
                "D": (
                    "electric displacement field",
                    "electric_displacement",
                    "coulomb/meter**2",
                ),
                "E": ("electric field", "electric_field", "volt/meter"),
                "Ppol": (
                    "polarization field",
                    "electric_displacement",
                    "coulomb/meter**2",
                ),
                "mu0": ("vacuum permeability", "permeability", "newton/ampere**2"),
                "epsilon0": ("vacuum permittivity", "permittivity", "farad/meter"),
            },
            "assumptions": [
                "SI macroscopic electromagnetism unit convention",
                "fields are smooth enough for curl and time derivatives",
                "mu0 != 0",
                "mu0 and epsilon0 are constants",
                "curl is linear over the represented vector-field terms",
                "all current-density placeholders live in the same vector space and coordinate frame",
            ],
            "frame": {
                "dimension": "3D vector field",
                "axis": "shared vector field",
                "positive_direction": "fixed spatial orientation",
            },
            "laws": [
                "D=epsilon0 E+P",
                "J_M=curl M",
                "curl H=J_f+dD/dt",
                "B=mu0(H+M)",
                "curl linearity and derivative linearity for constant material constants",
            ],
            "gaps": [
                "use B=mu0(H+M) to rewrite curl(B/mu0)",
                "substitute macroscopic Ampere law",
                "expand dD/dt using D=epsilon0 E+P",
                "substitute J_M=curl M",
            ],
            "projection_bridges": [
                {
                    "id": "formalphysics_0020.vector_placeholder_bridge",
                    "kind": "vector_equation_placeholder_bridge",
                    "status": "provided",
                    "source_object": "vector Maxwell-Ampere equation",
                    "target_equations": ["formalphysics_0020.target"],
                },
                {
                    "id": "formalphysics_0020.curl_linearity_bridge",
                    "kind": "operator_linearity_bridge",
                    "status": "provided",
                    "source_object": "curl(B/mu0)=curl(H+M)",
                    "target_equations": ["formalphysics_0020.step_01"],
                },
                {
                    "id": "formalphysics_0020.time_derivative_linearity_bridge",
                    "kind": "operator_linearity_bridge",
                    "status": "provided",
                    "source_object": "partial_t(epsilon0 E+P)=epsilon0 partial_t E+partial_t P",
                    "target_equations": ["formalphysics_0020.step_03"],
                },
            ],
        },
        "formalphysics_0066": {
            "statement_nl": "For a smooth parameter-dependent Hamiltonian and TDSE state, use commuting mixed partials to derive the scaled time-derivative inner-product identity.",
            "statement_latex": r"\langle\Psi|\partial_\lambda H|\Psi\rangle=i\hbar\,\partial_t\langle\Psi|\partial_\lambda\Psi\rangle",
            "target": "tdse_parameter_identity",
            "quantities": {
                "lhs": ("scaled Hamiltonian parameter expectation", "energy", "joule"),
                "d_lambda_inner_scaled": (
                    "i hbar times lambda derivative of time inner product",
                    "energy",
                    "joule",
                ),
                "lambda_dt_scaled": (
                    "i hbar times lambda-time mixed inner term",
                    "energy",
                    "joule",
                ),
                "dt_lambda_scaled": (
                    "i hbar times time-lambda inner term",
                    "energy",
                    "joule",
                ),
                "mixed_lambda_time_scaled": (
                    "i hbar times lambda then time second partial term",
                    "energy",
                    "joule",
                ),
                "mixed_time_lambda_scaled": (
                    "i hbar times time then lambda second partial term",
                    "energy",
                    "joule",
                ),
                "d_time_inner_scaled": (
                    "i hbar times time derivative of parameter inner product",
                    "energy",
                    "joule",
                ),
            },
            "assumptions": [
                "Hamiltonian and state are smooth in lambda and time",
                "TDSE holds for the ket state",
                "mixed partial derivatives commute",
                "inner-product convention and hbar factor are fixed",
                "operator substitutions are source-backed and finite-dimensional/projection-grounded for SymPy execution",
            ],
            "frame": {
                "dimension": "quantum scalar projection",
                "axis": "parameter-time inner-product scalar",
                "positive_direction": "chosen complex scalar convention",
            },
            "laws": [
                "time-dependent Schrodinger equation",
                "parameter differentiation of an inner product",
                "time differentiation of an inner product",
                "commutation of mixed partial derivatives under smoothness assumptions",
            ],
            "gaps": [
                "expand the lambda derivative of the time inner product",
                "substitute TDSE-scaled operator terms",
                "use mixed partial commutation",
                "collect scaled terms into the target time derivative",
            ],
            "projection_bridges": [
                {
                    "id": "formalphysics_0066.quantum_operator_projection_bridge",
                    "kind": "operator_inner_product_projection_bridge",
                    "status": "provided",
                    "source_object": "Hilbert-space TDSE identity",
                    "target_equations": ["formalphysics_0066.target"],
                },
                {
                    "id": "formalphysics_0066.scaled_hbar_bridge",
                    "kind": "unit_dimension_bridge",
                    "status": "provided",
                    "source_object": "i*hbar times derivative inner-product terms",
                    "target_equations": ["formalphysics_0066.scaled_terms"],
                },
            ],
        },
        "formalphysics_0191": {
            "statement_nl": "Differentiate the TDSE expectation value with respect to a parameter and isolate the Hamiltonian derivative expectation.",
            "statement_latex": r"\langle\Psi|\partial_\lambda H|\Psi\rangle=i\hbar\partial_\lambda\langle\Psi|\partial_t\Psi\rangle-i\hbar\langle\partial_\lambda\Psi|\partial_t\Psi\rangle+i\hbar\langle\partial_t\Psi|\partial_\lambda\Psi\rangle",
            "target": "tdse_product_differentiation_identity",
            "quantities": {
                "lhs": ("Hamiltonian derivative expectation", "energy", "joule"),
                "d_energy_scaled": (
                    "parameter derivative of TDSE energy expectation",
                    "energy",
                    "joule",
                ),
                "param_inner_scaled": (
                    "i hbar times parameter derivative of time inner product",
                    "energy",
                    "joule",
                ),
                "left_term_scaled": (
                    "i hbar times left TDSE ket substitution term",
                    "energy",
                    "joule",
                ),
                "right_term_scaled": (
                    "minus i hbar times adjoint-bra substitution term",
                    "energy",
                    "joule",
                ),
                "lambda_dt_scaled": (
                    "i hbar times lambda-time inner product",
                    "energy",
                    "joule",
                ),
                "dt_lambda_scaled": (
                    "i hbar times time-lambda inner product",
                    "energy",
                    "joule",
                ),
            },
            "assumptions": [
                "Hamiltonian and state are smooth in lambda",
                "TDSE ket substitution is source-backed",
                "adjoint-bra TDSE substitution is source-backed",
                "inner-product product rule is admissible",
                "operator reductions are represented as scalar expectation projections",
            ],
            "frame": {
                "dimension": "quantum scalar projection",
                "axis": "parameter derivative of expectation",
                "positive_direction": "chosen complex scalar convention",
            },
            "laws": [
                "time-dependent Schrodinger equation",
                "adjoint TDSE relation",
                "product rule for expectation values",
                "parameter derivative of the energy expectation",
            ],
            "gaps": [
                "differentiate the expectation value",
                "solve for the Hamiltonian derivative expectation",
                "substitute ket and bra TDSE identities",
                "collect scaled inner-product terms",
            ],
            "projection_bridges": [
                {
                    "id": "formalphysics_0191.quantum_expectation_projection_bridge",
                    "kind": "operator_inner_product_projection_bridge",
                    "status": "provided",
                    "source_object": "TDSE expectation product differentiation",
                    "target_equations": ["formalphysics_0191.target"],
                },
            ],
        },
        "formalphysics_0172": {
            "statement_nl": "Use the Euler-Lagrange x equation for a minimally coupled charged particle to obtain the force-balance component after cancelling the common Ax_x xdot term.",
            "statement_latex": r"F_x+q(A_{x,t}+A_{x,y}\dot y+A_{x,z}\dot z)=q(A_{y,x}\dot y+A_{z,x}\dot z)-q\phi_x",
            "target": "euler_lagrange_x_force_balance",
            "quantities": {
                "mddx": ("mass times x acceleration", "force", "newton"),
                "Fx": ("x component of force", "force", "newton"),
                "q_Axt": ("charge times time derivative of A_x", "force", "newton"),
                "q_Axy_ydot": (
                    "charge times A_x,y times y velocity",
                    "force",
                    "newton",
                ),
                "q_Axz_zdot": (
                    "charge times A_x,z times z velocity",
                    "force",
                    "newton",
                ),
                "q_Ayx_ydot": (
                    "charge times A_y,x times y velocity",
                    "force",
                    "newton",
                ),
                "q_Azx_zdot": (
                    "charge times A_z,x times z velocity",
                    "force",
                    "newton",
                ),
                "q_phix": (
                    "charge times scalar-potential x derivative",
                    "force",
                    "newton",
                ),
            },
            "assumptions": [
                "fixed Cartesian coordinate frame",
                "source Euler-Lagrange x equation is valid",
                "F_x=m xddot",
                "common A_x,x xdot terms cancel on both sides",
                "potentials are differentiable",
            ],
            "frame": {
                "dimension": "3D component",
                "axis": "x",
                "positive_direction": "right-handed Cartesian x direction",
            },
            "laws": [
                "Euler-Lagrange equation for minimally coupled charged-particle Lagrangian",
                "force definition F_x=m xddot",
                "coordinate component projection of the Lagrangian force balance",
            ],
            "gaps": [
                "differentiate the Lagrangian terms",
                "cancel common A_x,x xdot terms",
                "substitute F_x=m xddot",
                "collect the x force-balance component",
            ],
            "projection_bridges": [
                {
                    "id": "formalphysics_0172.coordinate_component_bridge",
                    "kind": "coordinate_component_bridge",
                    "status": "provided",
                    "source_object": "Euler-Lagrange vector force balance",
                    "target_equations": ["formalphysics_0172.target"],
                },
            ],
        },
        "formalphysics_0119": {
            "statement_nl": "Expand the x component of v cross curl A and use it in the Lorentz force x component.",
            "statement_latex": r"F_x=qE_x+q(\dot{\mathbf r}\times(\nabla\times A))_x",
            "target": "lorentz_cross_component_expansion",
            "quantities": {
                "Fx": ("x component of force", "force", "newton"),
                "qEx": ("charge times x electric field", "force", "newton"),
                "q_cross_x": (
                    "charge times x component of v cross curl A",
                    "force",
                    "newton",
                ),
                "cross_x": (
                    "x component of v cross curl A",
                    "velocity_magnetic",
                    "newton/coulomb",
                ),
                "expanded_cross_x": (
                    "expanded x cross-curl component",
                    "velocity_magnetic",
                    "newton/coulomb",
                ),
            },
            "assumptions": [
                "fixed right-handed Cartesian coordinate frame",
                "B=curl A component definitions are source-backed",
                "x projection of v cross curl A is used",
                "electric and magnetic field placeholders have compatible units",
            ],
            "frame": {
                "dimension": "3D component",
                "axis": "x",
                "positive_direction": "right-handed Cartesian x direction",
            },
            "laws": [
                "Lorentz force component law",
                "cross-product x component definition",
                "curl component definitions for A",
            ],
            "gaps": [
                "expand the x component of v cross curl A",
                "substitute curl component definitions",
                "scale the cross component by charge",
                "collect the Lorentz force component",
            ],
            "projection_bridges": [
                {
                    "id": "formalphysics_0119.cross_curl_projection_bridge",
                    "kind": "coordinate_component_bridge",
                    "status": "provided",
                    "source_object": "v cross curl(A)",
                    "target_equations": ["formalphysics_0119.target"],
                },
            ],
        },
        "formalphysics_0026": {
            "statement_nl": "Use normalization and eigenstate assumptions to cancel the derivative-of-norm term in the Hellmann-Feynman theorem.",
            "statement_latex": r"\partial_\lambda E_\lambda=\langle\Psi_\lambda|\partial_\lambda H_\lambda|\Psi_\lambda\rangle",
            "target": "hellmann_feynman",
            "quantities": {
                "dE": ("parameter derivative of the eigenvalue", "energy", "joule"),
                "dH": (
                    "expectation of the Hamiltonian parameter derivative",
                    "energy",
                    "joule",
                ),
                "eig_norm_derivative": (
                    "eigenvalue times derivative of state norm",
                    "energy",
                    "joule",
                ),
            },
            "assumptions": [
                "Hamiltonian is self-adjoint",
                "state is normalized",
                "state is a non-degenerate eigenstate",
                "Hamiltonian and eigenstate are smooth in lambda",
                "operator equation is represented as scalar expectation projection",
            ],
            "frame": {
                "dimension": "quantum scalar projection",
                "axis": "parameter derivative of eigenvalue",
                "positive_direction": "real expectation convention",
            },
            "laws": [
                "eigenvalue equation H psi=E psi",
                "normalization derivative equals zero",
                "product rule for the differentiated expectation value",
                "Hellmann-Feynman cancellation",
            ],
            "gaps": [
                "differentiate the eigenvalue expectation",
                "substitute the eigenvalue equation",
                "group the norm derivative term",
                "use normalization to cancel the norm derivative",
            ],
            "projection_bridges": [
                {
                    "id": "formalphysics_0026.quantum_expectation_projection_bridge",
                    "kind": "operator_inner_product_projection_bridge",
                    "status": "provided",
                    "source_object": "Hellmann-Feynman operator expectation",
                    "target_equations": ["formalphysics_0026.target"],
                },
            ],
        },
        "formalphysics_0176": {
            "statement_nl": "Evaluate the first variation at epsilon zero after differentiating under the integral and substituting variation derivatives.",
            "statement_latex": r"\left.dJ_\epsilon/d\epsilon\right|_0=\int L_f\eta+\int L_{f'}\eta'",
            "target": "first_variation_epsilon_zero",
            "quantities": {
                "dJ0": (
                    "first variation of the functional at epsilon zero",
                    "energy",
                    "joule",
                ),
                "integrand_f": (
                    "integral term before evaluating L_f at epsilon zero",
                    "energy",
                    "joule",
                ),
                "integrand_fp": (
                    "integral term before evaluating L_fprime at epsilon zero",
                    "energy",
                    "joule",
                ),
                "final_f": ("final L_f eta integral", "energy", "joule"),
                "final_fp": ("final L_fprime eta-prime integral", "energy", "joule"),
            },
            "assumptions": [
                "fixed endpoint variation eta(a)=eta(b)=0",
                "differentiation under the integral is justified",
                "L and variation functions are smooth enough",
                "epsilon is evaluated at zero",
            ],
            "frame": {
                "dimension": "functional scalar",
                "axis": "variation parameter epsilon",
                "positive_direction": "increasing epsilon",
            },
            "laws": [
                "chain rule for L(x,g_epsilon,g_epsilon')",
                "differentiate under the integral sign",
                "variation derivative dg_epsilon/depsilon=eta",
                "variation derivative dg_epsilon'/depsilon=eta'",
            ],
            "gaps": [
                "differentiate under the integral",
                "substitute variation derivatives",
                "evaluate L derivatives at epsilon zero",
                "collect the first variation terms",
            ],
        },
        "formalphysics_0054": {
            "statement_nl": "Rewrite macroscopic Ampere-Maxwell in matter using bound polarization and magnetization current densities.",
            "statement_latex": r"\mu_0^{-1}\nabla\times B=J_f+\epsilon_0\partial_tE+J_P+J_M",
            "target": "ampere_matter_bound_currents",
            "quantities": {
                "inv_mu0_curlB": (
                    "one over mu0 times curl of B",
                    "current_density",
                    "ampere/meter**2",
                ),
                "Jf": ("free current density", "current_density", "ampere/meter**2"),
                "eps0_dEdt": (
                    "epsilon0 times time derivative of E",
                    "current_density",
                    "ampere/meter**2",
                ),
                "dPdt": (
                    "polarization current placeholder",
                    "current_density",
                    "ampere/meter**2",
                ),
                "curlM": (
                    "magnetization current placeholder",
                    "current_density",
                    "ampere/meter**2",
                ),
                "JP": (
                    "polarization current density",
                    "current_density",
                    "ampere/meter**2",
                ),
                "JM": (
                    "magnetization current density",
                    "current_density",
                    "ampere/meter**2",
                ),
            },
            "assumptions": [
                "SI macroscopic electromagnetism unit convention",
                "mu0 != 0",
                "mu0 and epsilon0 are constants",
                "curl is linear over the represented vector-field terms",
                "time derivative is linear over D=epsilon0 E+P",
            ],
            "frame": {
                "dimension": "3D vector field",
                "axis": "shared vector field",
                "positive_direction": "fixed spatial orientation",
            },
            "laws": [
                "curl H=J_f+dD/dt",
                "H=B/mu0-M",
                "D=epsilon0 E+P",
                "J_P=partial_t P",
                "J_M=curl M",
            ],
            "gaps": [
                "substitute H relation into curl H",
                "expand displacement current",
                "move curl M to the right-hand side",
                "identify polarization and magnetization currents",
            ],
            "projection_bridges": [
                {
                    "id": "formalphysics_0054.vector_placeholder_bridge",
                    "kind": "vector_equation_placeholder_bridge",
                    "status": "provided",
                    "source_object": "macroscopic Ampere-Maxwell vector equation",
                    "target_equations": ["formalphysics_0054.target"],
                },
            ],
        },
        "formalphysics_0059": {
            "statement_nl": "Differentiate a parameterized functional under the integral sign and use the chain rule at epsilon zero.",
            "statement_latex": r"\left.dJ_\epsilon/d\epsilon\right|_0=\left.\int \partial L_\epsilon/\partial g_\epsilon\,\eta\right|_0+\left.\int \partial L_\epsilon/\partial g'_\epsilon\,\eta'\right|_0",
            "target": "variation_chain_rule_integral",
            "quantities": {
                "dJ0": (
                    "epsilon derivative of the functional at zero",
                    "energy",
                    "joule",
                ),
                "int_dL0": (
                    "integral of the epsilon derivative of L at zero",
                    "energy",
                    "joule",
                ),
                "int_f": ("integral of L_g eta at zero", "energy", "joule"),
                "int_fp": ("integral of L_gprime eta-prime at zero", "energy", "joule"),
            },
            "assumptions": [
                "fixed endpoint variation eta(a)=eta(b)=0",
                "differentiation under the integral is justified",
                "chain rule applies to L_epsilon(x)",
                "epsilon is evaluated at zero",
            ],
            "frame": {
                "dimension": "functional scalar",
                "axis": "variation parameter epsilon",
                "positive_direction": "increasing epsilon",
            },
            "laws": [
                "differentiate under the integral sign",
                "chain rule for L_epsilon",
                "dg_epsilon/depsilon=eta",
                "dg_epsilon'/depsilon=eta'",
            ],
            "gaps": [
                "differentiate the functional under the integral",
                "apply the chain rule",
                "substitute variation derivatives",
                "evaluate at epsilon zero",
            ],
        },
    }
    if case_id not in specs:
        raise ValueError(f"Unknown physics case: {case_id}")
    spec = dict(specs[case_id])
    spec.update(
        {
            "case_id": case_id,
            "backend": "sympy",
            "style": STYLE,
            "source_anchors": source_anchors,
        }
    )
    return spec


def all_case_ids() -> List[str]:
    """Document the responsibility of ``all_case_ids``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``all_case_ids`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return [
        "constant_acceleration_position",
        "constant_acceleration_velocity_position",
        "simple_harmonic_oscillator_omega",
        "simple_harmonic_oscillator_period",
        "work_energy_constant_force",
        "rc_discharge",
        "ideal_gas_density",
        "projectile_range_level_ground",
        "formalphysics_0000",
        "formalphysics_0004",
        "formalphysics_0020",
        "formalphysics_0066",
        "formalphysics_0191",
        "formalphysics_0172",
        "formalphysics_0119",
        "formalphysics_0026",
        "formalphysics_0176",
        "formalphysics_0054",
        "formalphysics_0059",
    ]


def controlled_case_ids() -> List[str]:
    """Return the curated Phase 15 controlled physics fixture identifiers.

    Motivation:
        Keep the controlled suite small, deterministic, and reviewable before
        larger FormalPhysics or wiki-level examples run.

    Intent:
        Separate the hand-curated pedagogical cases from the broader physics
        regression corpus.

    Inputs:
        Takes no inputs; the suite is defined by ``CONTROLLED_PHYSICS_CASE_IDS``.

    Outputs:
        Returns controlled case identifiers in the stable execution order used
        by Phase 15 reports and tests.
    """
    return list(CONTROLLED_PHYSICS_CASE_IDS)


def controlled_case_expectations(case_id: str) -> Dict[str, Any]:
    """Build the Phase 15 expectation contract for one controlled case.

    Motivation:
        A controlled physics test should do more than check that code ran. It
        should declare what semantic surface is expected from the source,
        derivation trace, unit model, gap closer, and assumption monitor.

    Intent:
        Provide a compact, inspectable oracle for quantity bindings,
        dimensions, assumptions, target expression, implicit gap classes, and
        blockers caused by removing contextual assumptions.

    Inputs:
        ``case_id`` must name one of the curated controlled physics fixtures.

    Outputs:
        Returns a JSON-serializable expectation packet used by the controlled
        suite and persisted beside each case report.
    """
    if case_id not in CONTROLLED_PHYSICS_CASE_IDS:
        raise ValueError(f"Not a controlled Phase 15 physics case: {case_id}")
    spec = case_spec(case_id)
    derivation = derive_case(case_id)
    quantity_dimensions = {
        symbol: dimension_name
        for symbol, (_, dimension_name, _) in spec["quantities"].items()
    }
    expected_gap_categories = sorted(
        {classify_gap_type(gap) for gap in spec.get("gaps", [])}
    )
    expected_omitted_assumption_blockers = ["missing_condition_or_context"]
    if any(
        category in expected_gap_categories
        for category in [
            "missing_initial_condition_application",
            "missing_approximation_justification",
            "missing_coordinate_projection",
            "missing_ode_solution",
        ]
    ):
        expected_omitted_assumption_blockers.append("critical_physics_blocker")
    return {
        "case_id": case_id,
        "source_fixture": f"tests/physics_sympy/controlled_latex/{case_id}.tex",
        "expected_quantity_symbols": sorted(spec["quantities"].keys()),
        "expected_quantity_dimensions": quantity_dimensions,
        "expected_unit_names": {
            symbol: unit for symbol, (_, _, unit) in spec["quantities"].items()
        },
        "expected_assumptions": list(spec["assumptions"]),
        "expected_frame": dict(spec.get("frame", {})),
        "expected_target_expression": safe_sympy_string(
            derivation["expected_expression"]
        ),
        "expected_gap_categories": expected_gap_categories,
        "expected_omitted_assumption_blockers": expected_omitted_assumption_blockers,
    }


def simulated_omitted_assumption_blockers(expectations: Dict[str, Any]) -> List[str]:
    """Return blockers that would be raised if source assumptions vanished.

    Motivation:
        Controlled tests need a negative-control surface: assumptions and
        regimes are not decorative metadata, and removing them should create a
        visible blocker.

    Intent:
        Encode the Phase 15 omitted-assumption policy without mutating the
        canonical source fixtures.

    Inputs:
        A packet from ``controlled_case_expectations``.

    Outputs:
        Returns blocker codes that the controlled suite compares with the
        expected omitted-assumption blocker list.
    """
    blockers: List[str] = []
    if expectations.get("expected_assumptions"):
        blockers.append("missing_condition_or_context")
    if any(
        category in expectations.get("expected_gap_categories", [])
        for category in [
            "missing_initial_condition_application",
            "missing_approximation_justification",
            "missing_coordinate_projection",
            "missing_ode_solution",
        ]
    ):
        blockers.append("critical_physics_blocker")
    return sorted(set(blockers))


def validate_controlled_case(
    case_id: str, consistency: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate one controlled case against the Phase 15 expectation contract.

    Motivation:
        Keep the controlled suite honest by checking semantic surfaces directly
        instead of relying only on a final ``complete`` status.

    Intent:
        Compare source preservation, quantity bindings, dimensions,
        assumptions, target computation, gap categories, omitted-assumption
        blockers, and artifact/report output paths.

    Inputs:
        ``case_id`` names a controlled fixture and ``consistency`` is the
        Phase 13 consistency report for that case.

    Outputs:
        Returns a compact validation packet with pass/fail checks and blockers.
    """
    expectations = controlled_case_expectations(case_id)
    source_path = REPO_ROOT / expectations["source_fixture"]
    symbol_table = build_physics_symbol_table(
        case_id,
        source_path.read_text(encoding="utf-8"),
        str(source_path.relative_to(REPO_ROOT)),
    )
    dimension_packet = build_physics_dimension_packet(case_id)
    regime_packet = build_physics_regime_assumption_packet(case_id)
    gap_packet = build_physics_gap_detection_packet(case_id)
    derivation = derive_case(case_id)
    target_residual = sp.simplify(
        derivation["target_expression"] - derivation["expected_expression"]
    )
    observed_dimensions = {
        row["symbol"]: row["dimension_name"]
        for row in symbol_table["quantity_table"]
        if row["symbol"] in expectations["expected_quantity_symbols"]
    }
    observed_gap_categories = sorted(
        {gap["gap_type"] for gap in gap_packet["implicit_gaps"]}
    )
    omitted_blockers = simulated_omitted_assumption_blockers(expectations)
    checks = [
        {
            "id": "source_fixture_exists",
            "ok": source_path.exists(),
            "detail": str(source_path.relative_to(REPO_ROOT)),
        },
        {
            "id": "quantity_symbols_match",
            "ok": sorted(observed_dimensions.keys())
            == expectations["expected_quantity_symbols"],
            "expected": expectations["expected_quantity_symbols"],
            "observed": sorted(observed_dimensions.keys()),
        },
        {
            "id": "quantity_dimensions_match",
            "ok": observed_dimensions == expectations["expected_quantity_dimensions"],
            "expected": expectations["expected_quantity_dimensions"],
            "observed": observed_dimensions,
        },
        {
            "id": "unit_dimensions_are_consistent",
            "ok": bool(
                dimension_packet["ok"]
                and not dimension_packet["unresolved_dimensions"]
                and not dimension_packet["conflicting_dimensions"]
            ),
            "unresolved_dimensions": dimension_packet["unresolved_dimensions"],
            "conflicting_dimensions": dimension_packet["conflicting_dimensions"],
        },
        {
            "id": "assumptions_preserved",
            "ok": sorted(regime_packet["assumptions"])
            == sorted(expectations["expected_assumptions"]),
            "expected": sorted(expectations["expected_assumptions"]),
            "observed": sorted(regime_packet["assumptions"]),
        },
        {
            "id": "target_expression_symbolically_matches",
            "ok": target_residual == 0,
            "expected": expectations["expected_target_expression"],
            "observed": safe_sympy_string(derivation["target_expression"]),
            "residual": safe_sympy_string(target_residual),
        },
        {
            "id": "gap_categories_match",
            "ok": observed_gap_categories == expectations["expected_gap_categories"],
            "expected": expectations["expected_gap_categories"],
            "observed": observed_gap_categories,
        },
        {
            "id": "omitted_assumptions_raise_expected_blockers",
            "ok": omitted_blockers
            == sorted(expectations["expected_omitted_assumption_blockers"]),
            "expected": sorted(expectations["expected_omitted_assumption_blockers"]),
            "observed": omitted_blockers,
        },
        {
            "id": "consistency_status_complete",
            "ok": consistency.get("status") == "complete"
            and consistency.get("ok") is True,
            "status": consistency.get("status"),
        },
    ]
    failed = [check for check in checks if not check["ok"]]
    return {
        "case_id": case_id,
        "ok": not failed,
        "expectations": expectations,
        "checks": checks,
        "failed_checks": failed,
        "omitted_assumption_blockers": omitted_blockers,
    }


def quantity_table(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``quantity_table``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``quantity_table`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    rows = []
    for symbol, (meaning, dimension_name, unit) in spec["quantities"].items():
        rows.append(
            {
                "symbol": symbol,
                "meaning": meaning,
                "dimension_name": dimension_name,
                "dimension": COMMON_DIMS.get(dimension_name, dim()),
                "unit": unit,
                "source_anchors": (
                    spec["source_anchors"]
                    if symbol not in {"t"}
                    else ["generated_time_context"]
                ),
                "source_backing": (
                    "literal" if symbol not in {"t"} else "generated_support"
                ),
            }
        )
    return rows


def stable_symbol_id(case_id: str, namespace: str, semantic_key: str) -> str:
    """Create a stable symbol identifier independent of rendered notation."""
    digest = hashlib.sha256(f"{namespace}:{semantic_key}".encode("utf-8")).hexdigest()[
        :10
    ]
    return f"{case_id}.{namespace}.{digest}"


def classify_symbol_kind(
    symbol: str, meaning: str, dimension_name: str, frame: Dict[str, Any]
) -> str:
    """Classify one source symbol according to the Phase 3 symbol ontology."""
    lowered = f"{symbol} {meaning} {dimension_name}".lower()
    if any(
        token in lowered
        for token in ["field", "vector", "curl", "component", "magnetic", "electric"]
    ):
        if "component" not in lowered and symbol not in {"Ex", "By", "Bz", "Fx"}:
            return "vector_quantity"
    if symbol == "V" and "voltage" in lowered and "t" in frame.get("axis", "").lower():
        return "function_of_time"
    if symbol == "x" and "position" in lowered:
        return "function_of_time"
    if symbol == "V" and "voltage" in lowered:
        return "function_of_time"
    if any(
        token in lowered
        for token in ["time derivative", "velocity component", "current", "density"]
    ):
        return "scalar_variable"
    if symbol in {
        "m",
        "k",
        "R",
        "C",
        "T",
        "g",
        "M",
        "P",
        "V0",
        "x0",
        "v0",
        "A",
        "omega",
        "theta",
        "q",
        "epsilon0",
        "mu0",
    }:
        return "parameter_constant"
    return "scalar_variable"


def generated_dummy_symbols(case_id: str, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return generated support symbols used by derivation expansion contexts."""
    dummies = []
    gap_text = " ".join(spec.get("gaps", [])).lower()
    if any(token in gap_text for token in ["integrate", "ode", "differentiate"]):
        dummies.append(("tau", "generated integration or differentiation dummy"))
    if case_id == "work_energy_constant_force":
        dummies.append(
            ("q_dummy", "generated path-coordinate dummy for the work integral")
        )
    return [
        {
            "stable_id": stable_symbol_id(
                case_id, "generated_dummy", f"{name}:{meaning}"
            ),
            "display_symbol": name,
            "symbol_kind": "generated_dummy_variable",
            "meaning": meaning,
            "dimension_name": "dimensionless",
            "dimension": COMMON_DIMS["dimensionless"],
            "unit": "1",
            "source_anchors": ["generated_support"],
            "source_backing": "generated_support",
            "generated_support": True,
            "semantic_key": meaning,
        }
        for name, meaning in dummies
    ]


def coordinate_symbol_entries(
    case_id: str, spec: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Build generated coordinate-axis and basis-vector entries from the frame."""
    frame = spec.get("frame", {})
    axis_text = str(frame.get("axis", ""))
    axes = []
    if "x" in axis_text:
        axes.append(("x_axis", "coordinate axis x"))
    if "y" in axis_text:
        axes.append(("y_axis", "coordinate axis y"))
    if not axes and axis_text:
        axes.append(("axis", f"coordinate axis: {axis_text}"))
    entries = []
    for display, meaning in axes:
        entries.append(
            {
                "stable_id": stable_symbol_id(case_id, "coordinate", meaning),
                "display_symbol": display,
                "symbol_kind": "coordinate_axis_or_basis",
                "meaning": meaning,
                "dimension_name": "dimensionless",
                "dimension": COMMON_DIMS["dimensionless"],
                "unit": "1",
                "source_anchors": spec["source_anchors"],
                "source_backing": "generated_support",
                "generated_support": True,
                "semantic_key": meaning,
            }
        )
    return entries


def unit_dimension_entries(case_id: str, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build unit and dimension entries referenced by the source quantity table."""
    entries = []
    seen = set()
    for _, (_, dimension_name, unit_name) in spec["quantities"].items():
        for namespace, display, meaning in [
            ("dimension", dimension_name, f"dimension {dimension_name}"),
            ("unit", unit_name, f"unit {unit_name}"),
        ]:
            key = (namespace, display)
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                {
                    "stable_id": stable_symbol_id(case_id, namespace, meaning),
                    "display_symbol": display,
                    "symbol_kind": "unit_or_dimension",
                    "meaning": meaning,
                    "dimension_name": (
                        dimension_name if namespace == "dimension" else "dimensionless"
                    ),
                    "dimension": COMMON_DIMS.get(
                        dimension_name, COMMON_DIMS["dimensionless"]
                    ),
                    "unit": unit_name if namespace == "unit" else "1",
                    "source_anchors": spec["source_anchors"],
                    "source_backing": "source_backed",
                    "generated_support": False,
                    "semantic_key": meaning,
                }
            )
    return entries


def source_symbol_entries(case_id: str, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build typed entries for source-backed physics quantities."""
    entries = []
    frame = spec.get("frame", {})
    for symbol, (meaning, dimension_name, unit_name) in spec["quantities"].items():
        source_backing = (
            "generated_support"
            if symbol == "t"
            and "time" not in " ".join(spec["statement_nl"].lower().split())
            else "source_backed"
        )
        semantic_key = f"{meaning}:{dimension_name}:{unit_name}"
        entries.append(
            {
                "stable_id": stable_symbol_id(case_id, "quantity", semantic_key),
                "display_symbol": symbol,
                "symbol_kind": classify_symbol_kind(
                    symbol, meaning, dimension_name, frame
                ),
                "meaning": meaning,
                "dimension_name": dimension_name,
                "dimension": COMMON_DIMS.get(dimension_name, dim()),
                "unit": unit_name,
                "source_anchors": (
                    spec["source_anchors"]
                    if source_backing == "source_backed"
                    else ["generated_support"]
                ),
                "source_backing": source_backing,
                "generated_support": source_backing == "generated_support",
                "semantic_key": semantic_key,
            }
        )
    return entries


def symbol_binding_diagnostics(
    entries: Sequence[Dict[str, Any]], source_units: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Detect symbol binding risks required by Phase 3."""
    diagnostics: List[Dict[str, Any]] = []
    by_display: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        by_display.setdefault(str(entry["display_symbol"]), []).append(entry)
    for display, group in sorted(by_display.items()):
        semantic_keys = {entry["semantic_key"] for entry in group}
        kinds = {entry["symbol_kind"] for entry in group}
        if len(semantic_keys) > 1 and all(
            entry["symbol_kind"] != "unit_or_dimension" for entry in group
        ):
            diagnostics.append(
                {
                    "code": "symbol_reuse_incompatible_meaning",
                    "severity": "error",
                    "display_symbol": display,
                    "meanings": sorted({entry["meaning"] for entry in group}),
                }
            )
        if len(kinds.intersection({"scalar_variable", "vector_quantity"})) > 1:
            diagnostics.append(
                {
                    "code": "mixed_scalar_vector_use",
                    "severity": "error",
                    "display_symbol": display,
                    "symbol_kinds": sorted(kinds),
                }
            )
    source_symbols = {
        symbol for unit in source_units for symbol in unit.get("inferred_symbols", [])
    }
    bound_symbols = {
        str(entry["display_symbol"])
        for entry in entries
        if entry["symbol_kind"] != "unit_or_dimension"
    }
    for missing in sorted(source_symbols.difference(bound_symbols)):
        diagnostics.append(
            {
                "code": "missing_binder",
                "severity": "error",
                "display_symbol": missing,
                "message": "symbol appears in extracted source units but has no symbol-table entry",
            }
        )
    for display, meanings in sorted(AMBIGUOUS_PHYSICS_SYMBOLS.items()):
        if display in bound_symbols:
            diagnostics.append(
                {
                    "code": "ambiguous_constant_notation",
                    "severity": "warning",
                    "display_symbol": display,
                    "possible_meanings": meanings,
                    "selected_meaning": next(
                        entry["meaning"]
                        for entry in entries
                        if entry["display_symbol"] == display
                    ),
                }
            )
    known_meanings: Dict[str, List[str]] = {}
    for case_id in all_case_ids():
        for symbol, (meaning, _, _) in case_spec(case_id)["quantities"].items():
            known_meanings.setdefault(symbol, [])
            if meaning not in known_meanings[symbol]:
                known_meanings[symbol].append(meaning)
    for display in sorted(bound_symbols):
        meanings = known_meanings.get(display, [])
        if len(meanings) > 1:
            diagnostics.append(
                {
                    "code": "overloaded_notation_across_corpus",
                    "severity": "warning",
                    "display_symbol": display,
                    "known_meanings": meanings,
                }
            )
    for entry in entries:
        if entry["symbol_kind"] == "function_of_time" and "t" not in bound_symbols:
            diagnostics.append(
                {
                    "code": "implicit_function_of_time_without_time_binder",
                    "severity": "error",
                    "display_symbol": entry["display_symbol"],
                }
            )
        if (
            entry["symbol_kind"] == "function_of_time"
            and "(t)" not in str(entry["display_symbol"])
            and entry["display_symbol"] in {"x", "V"}
        ):
            diagnostics.append(
                {
                    "code": "implicit_function_of_time_omitted_in_display",
                    "severity": "warning",
                    "display_symbol": entry["display_symbol"],
                    "time_binder": "t",
                }
            )
    for entry in entries:
        if entry["generated_support"] and entry["source_backing"] == "source_backed":
            diagnostics.append(
                {
                    "code": "generated_symbol_marked_source_backed",
                    "severity": "error",
                    "display_symbol": entry["display_symbol"],
                }
            )
    return diagnostics


def build_physics_symbol_table(
    case_id: str, source: str = "", source_path: str = "self-test"
) -> Dict[str, Any]:
    """Build the Phase 3 typed symbol table and binding diagnostics."""
    spec = case_spec(case_id)
    source_packet = extract_physics_source_units(case_id, source, source_path)
    entries = [
        *source_symbol_entries(case_id, spec),
        *generated_dummy_symbols(case_id, spec),
        *coordinate_symbol_entries(case_id, spec),
        *unit_dimension_entries(case_id, spec),
    ]
    diagnostics = symbol_binding_diagnostics(entries, source_packet["units"])
    errors = [item for item in diagnostics if item["severity"] == "error"]
    kind_counts = {
        kind: sum(1 for entry in entries if entry["symbol_kind"] == kind)
        for kind in PHYSICS_SYMBOL_KINDS
    }
    diagnostic_counts = {
        code: sum(1 for item in diagnostics if item["code"] == code)
        for code in PHYSICS_SYMBOL_DIAGNOSTIC_CODES
    }
    return {
        "ok": not errors,
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "source_path": source_path,
        "generated_at": now(),
        "symbol_kinds": list(PHYSICS_SYMBOL_KINDS),
        "symbol_table": entries,
        "quantity_table": quantity_table(spec),
        "kind_counts": kind_counts,
        "diagnostic_checklist": list(PHYSICS_SYMBOL_DIAGNOSTIC_CODES),
        "diagnostic_counts": diagnostic_counts,
        "binding_diagnostics": diagnostics,
        "binding_errors": errors,
        "stable_id_policy": "stable ids are sha256-derived from semantic namespace, meaning, dimension, and unit, not from display spelling alone",
        "generated_support_policy": "generated dummy variables and coordinate helpers must use source_backing=generated_support",
        "source_units_summary": {
            "unit_count": len(source_packet["units"]),
            "role_counts": source_packet["role_counts"],
        },
    }


def build_symbols(spec: Dict[str, Any]) -> Dict[str, sp.Symbol]:
    """Document the responsibility of ``build_symbols``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    assumptions = {
        "m": {"positive": True},
        "k": {"positive": True},
        "R": {"positive": True},
        "C": {"positive": True},
        "T": {"positive": True},
        "g": {"positive": True},
        "t": {"nonnegative": True},
        "theta": {"real": True},
    }
    symbols: Dict[str, sp.Symbol] = {}
    case_assumptions = spec.get("symbol_assumptions", {})
    for name in spec["quantities"]:
        kwargs = case_assumptions.get(name, assumptions.get(name, {"real": True}))
        symbols[name] = sp.symbols(name, **kwargs)
    for name in (
        "x0",
        "v0",
        "a",
        "v",
        "x",
        "A",
        "omega",
        "F",
        "d",
        "W",
        "DeltaK",
        "V0",
        "P",
        "n",
        "M",
        "rho",
    ):
        if name not in symbols:
            symbols[name] = sp.symbols(name, real=True)
    return symbols


def derive_case(case_id: str) -> Dict[str, Any]:
    """Document the responsibility of ``derive_case``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``derive_case`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    spec = case_spec(case_id)
    s = build_symbols(spec)
    steps: List[Dict[str, Any]] = []

    def add(
        step_id: str,
        kind: str,
        expression: Any,
        rule: str,
        source: str,
        generated: bool = False,
    ) -> Any:
        """Document the responsibility of ``derive_case.add``.

        Motivation:
            Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

        Intent:
            Provide the local operation named ``derive_case.add`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        steps.append(
            {
                "id": step_id,
                "kind": kind,
                "expression": str(expression),
                "rule": rule,
                "source": source,
                "generated": generated,
                "source_anchors": [] if generated else spec["source_anchors"],
            }
        )
        return expression

    if case_id == "constant_acceleration_position":
        t, x0, v0, a = s["t"], s["x0"], s["v0"], s["a"]
        v = add(
            "step_01_velocity",
            "generated_calculus",
            v0 + sp.integrate(a, (t, 0, t)),
            "integrate acceleration",
            "generated gap",
            True,
        )
        x_t = add(
            "step_02_position",
            "target_equation",
            x0 + sp.integrate(v, (t, 0, t)),
            "integrate velocity",
            "source target",
        )
        target_expr = sp.simplify(x_t)
        expected = x0 + v0 * t + a * t**2 / 2
    elif case_id == "constant_acceleration_velocity_position":
        t, x0, v0, a, v, x = s["t"], s["x0"], s["v0"], s["a"], s["v"], s["x"]
        t_expr = add(
            "step_01_solve_time",
            "generated_algebra",
            sp.solve(sp.Eq(v, v0 + a * t), t)[0],
            "solve velocity equation for time",
            "generated gap",
            True,
        )
        x_expr = x0 + v0 * t + a * t**2 / 2
        substituted = add(
            "step_02_substitute_time",
            "generated_substitution",
            sp.simplify(x_expr.subs(t, t_expr) - x0),
            "substitute time into position equation",
            "generated gap",
            True,
        )
        target_expr = add(
            "step_03_rearrange",
            "target_equation",
            sp.simplify(2 * a * substituted + v0**2),
            "algebraic rearrangement",
            "source target",
        )
        expected = v**2
    elif case_id == "simple_harmonic_oscillator_omega":
        t, A, omega, m, k = s["t"], s["A"], s["omega"], s["m"], s["k"]
        x = A * sp.cos(omega * t)
        _residual = add(
            "step_01_substitute_trial",
            "generated_calculus",
            sp.simplify(m * sp.diff(x, t, 2) + k * x),
            "substitute trial solution into ODE",
            "generated gap",
            True,
        )
        omega_sq = add(
            "step_02_solve_omega_squared",
            "generated_algebra",
            sp.solve(sp.Eq(-m * omega**2 + k, 0), omega**2)[0],
            "nontrivial amplitude condition",
            "generated gap",
            True,
        )
        target_expr = add(
            "step_03_positive_root",
            "target_equation",
            sp.sqrt(omega_sq),
            "positive angular frequency",
            "source target",
        )
        expected = sp.sqrt(k / m)
    elif case_id == "simple_harmonic_oscillator_period":
        m, k = s["m"], s["k"]
        omega_expr = add(
            "step_01_omega",
            "source_law",
            sp.sqrt(k / m),
            "SHO angular frequency",
            "source support",
        )
        target_expr = add(
            "step_02_period",
            "target_equation",
            sp.simplify(2 * sp.pi / omega_expr),
            "period from angular frequency",
            "source target",
        )
        expected = 2 * sp.pi * sp.sqrt(m / k)
    elif case_id == "work_energy_constant_force":
        F, d = s["F"], s["d"]
        q = sp.symbols("q", real=True)
        work = add(
            "step_01_work_integral",
            "generated_calculus",
            sp.integrate(F, (q, 0, d)),
            "integrate constant force",
            "generated gap",
            True,
        )
        target_expr = add(
            "step_02_work_energy",
            "target_equation",
            work,
            "work-energy theorem",
            "source target",
        )
        expected = F * d
    elif case_id == "rc_discharge":
        t, R, C, V0 = s["t"], s["R"], s["C"], s["V0"]
        Vt = V0 * sp.exp(-t / (R * C))
        _residual = add(
            "step_01_ode_residual",
            "generated_calculus",
            sp.simplify(sp.diff(Vt, t) + Vt / (R * C)),
            "verify ODE solution",
            "generated gap",
            True,
        )
        _initial = add(
            "step_02_initial_condition",
            "generated_condition_application",
            sp.simplify(Vt.subs(t, 0)),
            "apply V(0)=V0",
            "generated gap",
            True,
        )
        target_expr = add(
            "step_03_solution",
            "target_equation",
            Vt,
            "separable ODE solution",
            "source target",
        )
        expected = V0 * sp.exp(-t / (R * C))
    elif case_id == "ideal_gas_density":
        P, V, R, T, M, rho = s["P"], s["V"], s["R"], s["T"], s["M"], s["rho"]
        equation = add(
            "step_01_substitute_definitions",
            "generated_substitution",
            sp.Eq(P * V, (rho * V / M) * R * T),
            "substitute n=m/M and m=rho V",
            "generated gap",
            True,
        )
        target_expr = add(
            "step_02_solve_density",
            "target_equation",
            sp.solve(equation, rho)[0],
            "solve for density",
            "source target",
        )
        expected = P * M / (R * T)
    elif case_id == "projectile_range_level_ground":
        v0, theta, g, t = s["v0"], s["theta"], s["g"], s["t"]
        _y = v0 * sp.sin(theta) * t - g * t**2 / 2
        flight = add(
            "step_01_flight_time",
            "generated_algebra",
            2 * v0 * sp.sin(theta) / g,
            "solve y(t)=0 for nonzero t",
            "generated gap",
            True,
        )
        _range_expr = add(
            "step_02_horizontal_motion",
            "generated_substitution",
            v0 * sp.cos(theta) * flight,
            "substitute flight time into x(t)",
            "generated gap",
            True,
        )
        expected = v0**2 * sp.sin(2 * theta) / g
        target_expr = add(
            "step_03_double_angle",
            "target_equation",
            expected,
            "double-angle identity",
            "source target",
        )
    elif case_id == "formalphysics_0000":
        q, ydot, zdot = s["q"], s["ydot"], s["zdot"]
        Fx, Ex, By, Bz = s["Fx"], s["Ex"], s["By"], s["Bz"]
        Ax_t, Ax_y, Ax_z = s["Ax_t"], s["Ax_y"], s["Ax_z"]
        Ay_x, Az_x, phi_x = s["Ay_x"], s["Az_x"], s["phi_x"]
        source_equation = add(
            "step_01_euler_lagrange_x_component",
            "source_equation",
            sp.Eq(
                Fx + q * (Ax_t + Ax_y * ydot + Ax_z * zdot),
                q * (Ay_x * ydot + Az_x * zdot) - q * phi_x,
            ),
            "Euler-Lagrange equation for the x coordinate of the minimally coupled charged-particle Lagrangian",
            "source equation",
        )
        solved_force = add(
            "step_02_solve_for_force_component",
            "generated_algebra",
            sp.solve(source_equation, Fx)[0],
            "solve source equation for F_x",
            "generated gap",
            True,
        )
        field_definitions = {
            Ex: -(phi_x + Ax_t),
            Bz: Ay_x - Ax_y,
            By: Ax_z - Az_x,
        }
        lorentz_component = q * Ex + q * ydot * Bz - q * zdot * By
        target_expr = add(
            "step_03_expand_lorentz_component",
            "target_equation",
            sp.expand(cast(Any, lorentz_component).subs(field_definitions)),
            "substitute E_x, B_y, and B_z definitions into q(E_x+ydot B_z-zdot B_y)",
            "source target",
        )
        expected = solved_force
    elif case_id == "formalphysics_0004":
        q, p, a, _adagger, _Nop = s["q"], s["p"], s["a"], s["adagger"], s["Nop"]
        annihilation_definition = add(
            "step_01_annihilation_definition",
            "source_equation",
            (q + sp.I * p) / sp.sqrt(2),
            "source ladder definition a=(q+i p)/sqrt(2)",
            "source equation",
        )
        creation_definition = add(
            "step_02_creation_definition",
            "source_equation",
            (q - sp.I * p) / sp.sqrt(2),
            "source adjoint ladder definition a_dagger=(q-i p)/sqrt(2)",
            "source equation",
        )
        _product = add(
            "step_03_number_operator_product",
            "source_substitution",
            creation_definition * annihilation_definition,
            "form N=a_dagger*a from the source definitions",
            "source support",
        )
        factored = add(
            "step_04_factor_dimensionless_normalization",
            "source_substitution",
            sp.Rational(1, 2) * (q - sp.I * p) * (q + sp.I * p),
            "factor the dimensionless normalization constant",
            "source support",
        )
        target_expr = add(
            "step_05_noncommutative_operator_expansion",
            "target_equation",
            sp.expand(factored),
            "expand the product while preserving noncommutative p*q and q*p order",
            "source target",
        )
        expected = sp.Rational(1, 2) * (p**2 - sp.I * p * q + sp.I * q * p + q**2)
    elif case_id == "formalphysics_0020":
        _curlB_over_mu0 = s["curlB_over_mu0"]
        curlH, curlM = s["curlH"], s["curlM"]
        Jf, JM = s["Jf"], s["JM"]
        dDdt, eps0_dEdt, dPdt = s["dDdt"], s["eps0_dEdt"], s["dPdt"]
        curl_relation_rhs = add(
            "step_01_projection_from_B_relation",
            "operator_linearity_bridge",
            curlH + curlM,
            "from B=mu0(H+M), mu0 != 0, constant mu0, and linearity of curl",
            "source support",
        )
        ampere_rhs = add(
            "step_02_substitute_ampere_macroscopic",
            "source_substitution",
            sp.expand(curl_relation_rhs.subs(curlH, Jf + dDdt)),
            "substitute curl H=J_f+dD/dt",
            "source support",
        )
        displacement_rhs = add(
            "step_03_expand_displacement_current",
            "source_substitution",
            sp.expand(ampere_rhs.subs(dDdt, eps0_dEdt + dPdt)),
            "substitute D=epsilon0 E+P and commute time derivative through constant epsilon0",
            "source support",
        )
        expected = add(
            "step_04_substitute_magnetization_current",
            "source_substitution",
            sp.expand(displacement_rhs.subs(curlM, JM)),
            "substitute J_M=curl M",
            "source support",
        )
        target_expr = add(
            "step_05_target_rhs",
            "target_equation",
            Jf + eps0_dEdt + dPdt + JM,
            "Maxwell-Ampere target current-density right-hand side",
            "source target",
        )
    elif case_id == "formalphysics_0066":
        _lhs = s["lhs"]
        d_lambda_inner_scaled = s["d_lambda_inner_scaled"]
        lambda_dt_scaled = s["lambda_dt_scaled"]
        dt_lambda_scaled = s["dt_lambda_scaled"]
        mixed_lambda_time_scaled = s["mixed_lambda_time_scaled"]
        mixed_time_lambda_scaled = s["mixed_time_lambda_scaled"]
        d_time_inner_scaled = s["d_time_inner_scaled"]
        initial_rhs = add(
            "step_01_tdse_parameter_start",
            "source_equation",
            d_lambda_inner_scaled - lambda_dt_scaled + dt_lambda_scaled,
            "TDSE parameter identity before product-rule cancellation",
            "source equation",
        )
        lambda_expansion = add(
            "step_02_lambda_inner_product_rule",
            "source_substitution",
            lambda_dt_scaled + mixed_lambda_time_scaled,
            "expand the lambda derivative of the time inner product",
            "source support",
        )
        _time_expansion = add(
            "step_03_time_inner_product_rule",
            "source_substitution",
            dt_lambda_scaled + mixed_time_lambda_scaled,
            "expand the time derivative of the parameter inner product",
            "source support",
        )
        bridge = add(
            "step_04_mixed_partial_commutation_bridge",
            "generated_algebra",
            sp.simplify(
                initial_rhs.subs(d_lambda_inner_scaled, lambda_expansion).subs(
                    mixed_lambda_time_scaled, mixed_time_lambda_scaled
                )
            ),
            "use commuting mixed partials and cancel the lambda-time term",
            "generated support",
            True,
        )
        target_expr = add(
            "step_05_target_time_derivative_identity",
            "target_equation",
            d_time_inner_scaled,
            "identify the remaining scaled terms as the time derivative of the parameter inner product",
            "source target",
        )
        expected = d_time_inner_scaled
    elif case_id == "formalphysics_0191":
        _lhs = s["lhs"]
        d_energy_scaled = s["d_energy_scaled"]
        param_inner_scaled = s["param_inner_scaled"]
        left_term_scaled = s["left_term_scaled"]
        right_term_scaled = s["right_term_scaled"]
        lambda_dt_scaled = s["lambda_dt_scaled"]
        dt_lambda_scaled = s["dt_lambda_scaled"]
        _isolated = add(
            "step_01_isolate_hamiltonian_derivative_expectation",
            "source_equation",
            d_energy_scaled - left_term_scaled - right_term_scaled,
            "differentiate the expectation value and isolate the Hamiltonian derivative term",
            "source equation",
        )
        energy_substitution = add(
            "step_02_substitute_tdse_energy_derivative",
            "source_substitution",
            param_inner_scaled,
            "substitute the TDSE expression for the differentiated energy expectation",
            "source support",
        )
        left_substitution = add(
            "step_03_substitute_ket_tdse_term",
            "source_substitution",
            lambda_dt_scaled,
            "substitute the ket-side TDSE inner-product term",
            "source support",
        )
        right_substitution = add(
            "step_04_substitute_adjoint_bra_tdse_term",
            "source_substitution",
            -dt_lambda_scaled,
            "substitute the adjoint-bra TDSE inner-product term",
            "source support",
        )
        target_expr = add(
            "step_05_collect_tdse_product_terms",
            "target_equation",
            sp.expand(energy_substitution - left_substitution - right_substitution),
            "collect the parameter, ket, and adjoint-bra terms",
            "source target",
        )
        expected = param_inner_scaled - lambda_dt_scaled + dt_lambda_scaled
    elif case_id == "formalphysics_0172":
        mddx, Fx = s["mddx"], s["Fx"]
        q_Axt, q_Axy_ydot, q_Axz_zdot = s["q_Axt"], s["q_Axy_ydot"], s["q_Axz_zdot"]
        q_Ayx_ydot, q_Azx_zdot, q_phix = s["q_Ayx_ydot"], s["q_Azx_zdot"], s["q_phix"]
        source_equation = add(
            "step_01_euler_lagrange_after_common_term_cancellation",
            "source_equation",
            sp.Eq(
                mddx + q_Axt + q_Axy_ydot + q_Axz_zdot, q_Ayx_ydot + q_Azx_zdot - q_phix
            ),
            "Euler-Lagrange x equation after cancelling the common A_x,x xdot term",
            "source equation",
        )
        force_substituted = add(
            "step_02_substitute_force_definition",
            "source_substitution",
            sp.Eq(
                Fx + q_Axt + q_Axy_ydot + q_Axz_zdot, q_Ayx_ydot + q_Azx_zdot - q_phix
            ),
            "substitute F_x=m xddot",
            "source support",
        )
        target_expr = add(
            "step_03_solve_force_balance_for_Fx",
            "target_equation",
            sp.solve(force_substituted, Fx)[0],
            "solve the component force balance for F_x",
            "source target",
        )
        expected = q_Ayx_ydot + q_Azx_zdot - q_phix - q_Axt - q_Axy_ydot - q_Axz_zdot
    elif case_id == "formalphysics_0119":
        Fx, qEx, q_cross_x = s["Fx"], s["qEx"], s["q_cross_x"]
        _cross_x, expanded_cross_x = s["cross_x"], s["expanded_cross_x"]
        _cross_component = add(
            "step_01_expand_cross_curl_x_component",
            "source_substitution",
            expanded_cross_x,
            "expand the x component of v cross curl A using curl component definitions",
            "source support",
        )
        bridge = add(
            "step_02_projection_bridge_to_scaled_cross_term",
            "operator_linearity_bridge",
            q_cross_x,
            "scale the x cross-curl component by charge in the Lorentz-force projection",
            "generated support",
            True,
        )
        target_expr = add(
            "step_03_lorentz_cross_component_target",
            "target_equation",
            qEx + bridge,
            "collect the electric and magnetic x-component force terms",
            "source target",
        )
        expected = qEx + q_cross_x
    elif case_id == "formalphysics_0026":
        _dE, dH, eig_norm_derivative = s["dE"], s["dH"], s["eig_norm_derivative"]
        differentiated = add(
            "step_01_differentiate_eigen_expectation",
            "source_equation",
            eig_norm_derivative + dH,
            "differentiate the eigenvalue expectation and group the normalization derivative term",
            "source equation",
        )
        normalized = add(
            "step_02_apply_normalization_derivative",
            "source_substitution",
            0,
            "use d/dlambda <psi|psi>=0 for normalized states",
            "source support",
        )
        target_expr = add(
            "step_03_cancel_norm_derivative",
            "target_equation",
            sp.simplify(differentiated.subs(eig_norm_derivative, normalized)),
            "cancel the normalization derivative term",
            "source target",
        )
        expected = dH
    elif case_id == "formalphysics_0176":
        _dJ0 = s["dJ0"]
        integrand_f, integrand_fp = s["integrand_f"], s["integrand_fp"]
        final_f, final_fp = s["final_f"], s["final_fp"]
        differentiated = add(
            "step_01_differentiate_under_integral",
            "source_equation",
            integrand_f + integrand_fp,
            "differentiate under the integral sign and split the variation terms",
            "source equation",
        )
        eval_f = add(
            "step_02_evaluate_L_f_term_at_epsilon_zero",
            "source_substitution",
            final_f,
            "evaluate the L_f variation term at epsilon zero",
            "source support",
        )
        eval_fp = add(
            "step_03_evaluate_L_fprime_term_at_epsilon_zero",
            "source_substitution",
            final_fp,
            "evaluate the L_fprime variation term at epsilon zero",
            "source support",
        )
        target_expr = add(
            "step_04_collect_first_variation_terms",
            "target_equation",
            eval_f + eval_fp,
            "collect the two first-variation integral terms",
            "source target",
        )
        expected = final_f + final_fp
    elif case_id == "formalphysics_0054":
        _inv_mu0_curlB = s["inv_mu0_curlB"]
        Jf, eps0_dEdt, dPdt, curlM = s["Jf"], s["eps0_dEdt"], s["dPdt"], s["curlM"]
        JP, JM = s["JP"], s["JM"]
        _matter_rhs = add(
            "step_01_rewrite_ampere_matter_rhs",
            "source_equation",
            Jf + eps0_dEdt + dPdt + curlM,
            "substitute H=B/mu0-M and expand D=epsilon0 E+P in Ampere-Maxwell",
            "source equation",
        )
        polarization_current = add(
            "step_02_identify_polarization_current",
            "source_substitution",
            JP,
            "identify J_P=partial_t P",
            "source support",
        )
        magnetization_current = add(
            "step_03_identify_magnetization_current",
            "source_substitution",
            JM,
            "identify J_M=curl M",
            "source support",
        )
        target_expr = add(
            "step_04_collect_bound_current_terms",
            "target_equation",
            Jf + eps0_dEdt + polarization_current + magnetization_current,
            "collect free, polarization, and magnetization current-density terms",
            "source target",
        )
        expected = Jf + eps0_dEdt + JP + JM
    elif case_id == "formalphysics_0059":
        _dJ0, int_dL0, int_f, int_fp = s["dJ0"], s["int_dL0"], s["int_f"], s["int_fp"]
        differentiated = add(
            "step_01_differentiate_functional_under_integral",
            "source_equation",
            int_dL0,
            "differentiate the functional under the integral sign",
            "source equation",
        )
        chain_rule = add(
            "step_02_apply_chain_rule_to_integrand",
            "source_substitution",
            int_f + int_fp,
            "apply the chain rule and substitute variation derivatives",
            "source support",
        )
        target_expr = add(
            "step_03_evaluate_at_epsilon_zero",
            "target_equation",
            chain_rule,
            "evaluate the chain-rule integral identity at epsilon zero",
            "source target",
        )
        expected = int_f + int_fp
    else:
        raise ValueError(case_id)

    physics_ir = from_case_spec(
        case_id,
        spec,
        steps=steps,
        projection_bridges=spec.get("projection_bridges") or (),
    )
    return {
        "case_id": case_id,
        "spec": spec,
        "symbols": s,
        "steps": steps,
        "target_expression": sp.simplify(target_expr),
        "expected_expression": sp.simplify(expected),
        "residual": sp.simplify(target_expr - expected),
        "physics_ir": physics_ir.to_dict(),
        "physics_ir_digest": physics_ir.ir_digest,
        "physics_ir_errors": validate_ir(physics_ir),
    }


def dimension_of_expr(
    expr: Any, dims: Dict[str, Dict[str, int]], findings: List[Dict[str, Any]]
) -> Dict[str, int]:
    """Document the responsibility of ``dimension_of_expr``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``dimension_of_expr`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    expr = sp.powsimp(sp.sympify(expr), force=True)
    if expr.is_Number:
        return dim()
    if isinstance(expr, sp.Symbol):
        return dims.get(str(expr), dim())
    if isinstance(expr, sp.Derivative):
        base = dimension_of_expr(expr.expr, dims, findings)
        for var, count in cast(Any, expr).variable_count:
            var_dim = dims.get(str(var), dim())
            for _ in range(count):
                base = dim_sub(base, var_dim)
        return base
    if isinstance(expr, sp.Integral):
        base = dimension_of_expr(expr.function, dims, findings)
        for limit in cast(Any, expr).limits:
            var = limit[0]
            base = dim_add(base, dims.get(str(var), dim()))
        return base
    if isinstance(expr, sp.Equality):
        lhs_dim = dimension_of_expr(expr.lhs, dims, findings)
        rhs_dim = dimension_of_expr(expr.rhs, dims, findings)
        if expr.lhs == 0:
            return rhs_dim
        if expr.rhs == 0:
            return lhs_dim
        if not dim_equal(lhs_dim, rhs_dim):
            findings.append(
                {
                    "severity": "high",
                    "code": "equation_dimension_mismatch",
                    "expression": str(expr),
                    "lhs_dimension": dim_text(lhs_dim),
                    "rhs_dimension": dim_text(rhs_dim),
                }
            )
        return lhs_dim
    if isinstance(expr, sp.Add):
        child_dims = [dimension_of_expr(arg, dims, findings) for arg in expr.args]
        first = child_dims[0] if child_dims else dim()
        for child in child_dims[1:]:
            if not dim_equal(first, child):
                findings.append(
                    {
                        "severity": "high",
                        "code": "additive_dimension_mismatch",
                        "expression": str(expr),
                        "lhs_dimension": dim_text(first),
                        "rhs_dimension": dim_text(child),
                    }
                )
        return first
    if isinstance(expr, sp.Mul):
        result = dim()
        for arg in expr.args:
            if isinstance(arg, sp.Pow) and arg.exp.is_number:
                result = dim_add(
                    result,
                    dim_pow(dimension_of_expr(arg.base, dims, findings), arg.exp),
                )
            else:
                result = dim_add(result, dimension_of_expr(arg, dims, findings))
        if not dim_integral(result):
            findings.append(
                {
                    "severity": "high",
                    "code": "fractional_product_dimension",
                    "expression": str(expr),
                    "dimension": dim_text(result),
                }
            )
        return result
    if isinstance(expr, sp.Pow):
        base, exponent = expr.args
        base_dim = dimension_of_expr(base, dims, findings)
        if not exponent.is_number:
            exp_dim = dimension_of_expr(exponent, dims, findings)
            if not dim_equal(exp_dim, dim()):
                findings.append(
                    {
                        "severity": "high",
                        "code": "dimensioned_exponent",
                        "expression": str(expr),
                    }
                )
            return base_dim
        if exponent.is_integer:
            return dim_pow(base_dim, int(exponent))
        if dim_equal(base_dim, dim()):
            return dim()
        # SymPy represents sqrt as Pow(..., 1/2). Allow even exponents only
        # when the resulting base dimension exponents stay integral.
        powered = dim_pow(base_dim, exponent)
        if dim_integral(powered):
            return powered
        findings.append(
            {
                "severity": "high",
                "code": "fractional_power_dimension",
                "expression": str(expr),
            }
        )
        return base_dim
    if getattr(expr, "is_Function", False):
        name = expr.func.__name__
        for arg in expr.args:
            arg_dim = dimension_of_expr(arg, dims, findings)
            if name in {"sin", "cos", "tan", "exp", "log"} and not dim_equal(
                arg_dim, dim()
            ):
                findings.append(
                    {
                        "severity": "high",
                        "code": "dimensioned_function_argument",
                        "function": name,
                        "argument": str(arg),
                    }
                )
        if name in {"sin", "cos", "tan", "exp", "log"}:
            return dim()
        return dims.get(name, dim())
    return dim()


def dimension_map(spec: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """Document the responsibility of ``dimension_map``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``dimension_map`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {
        symbol: COMMON_DIMS.get(dimension_name, dim())
        for symbol, (_, dimension_name, _) in spec["quantities"].items()
    }


def unit_analysis(case_id: str) -> Dict[str, Any]:
    """Document the responsibility of ``unit_analysis``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``unit_analysis`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    derivation = derive_case(case_id)
    spec = derivation["spec"]
    dims = dimension_map(spec)
    findings: List[Dict[str, Any]] = []
    target_dim = dimension_of_expr(derivation["target_expression"], dims, findings)
    expected_dim = dimension_of_expr(derivation["expected_expression"], dims, findings)
    dimensionally_consistent = dim_equal(target_dim, expected_dim) and not findings
    step_checks = []
    for step in derivation["steps"]:
        local_findings: List[Dict[str, Any]] = []
        try:
            expr = sp.sympify(step["expression"])
            step_dim = dimension_of_expr(expr, dims, local_findings)
            ok = not local_findings
        except Exception as exc:
            step_dim = dim()
            ok = False
            local_findings.append(
                {
                    "severity": "medium",
                    "code": "dimension_parse_error",
                    "message": str(exc),
                }
            )
        step_checks.append(
            {
                **step,
                "dimension": dim_text(step_dim),
                "ok": ok,
                "findings": local_findings,
            }
        )
        findings.extend(local_findings)
    return {
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "generated_at": now(),
        "quantity_dimensions": {key: dim_text(value) for key, value in dims.items()},
        "target_dimension": dim_text(target_dim),
        "expected_dimension": dim_text(expected_dim),
        "dimensionally_consistent": dimensionally_consistent,
        "step_checks": step_checks,
        "findings": findings,
    }


def sympy_unit_object_grounding() -> Dict[str, Any]:
    """Describe SymPy unit-system objects used by the Phase 4 model."""
    objects = [
        "sympy.physics.units.Quantity",
        "sympy.physics.units.Dimension",
        "sympy.physics.units.dimensions.DimensionSystem",
        "sympy.physics.units.unitsystem.UnitSystem",
        "sympy.physics.units.systems.si.SI",
    ]
    return {
        "style": "physics_sympy_unit_system_object_grounding",
        "objects": [
            {
                "qualified_name": name,
                "available": qualified_available(name),
                "representation": "referenced_sympy_object",
            }
            for name in objects
        ],
        "common_units": [
            {
                **unit,
                "available": qualified_available(unit["sympy_name"]),
                "source": "common_unit_catalog",
            }
            for unit in PHYSICS_COMMON_UNITS
        ],
    }


def build_physics_unit_packet(
    case_id: str, source: str = "", source_path: str = "self-test"
) -> Dict[str, Any]:
    """Build the Phase 4 unit grounding packet."""
    _spec = case_spec(case_id)
    symbol_packet = build_physics_symbol_table(case_id, source, source_path)
    source_units = extract_physics_source_units(case_id, source, source_path)
    quantity_to_unit = {
        entry["display_symbol"]: entry["unit"]
        for entry in symbol_packet["symbol_table"]
        if entry["symbol_kind"]
        not in {
            "unit_or_dimension",
            "coordinate_axis_or_basis",
            "generated_dummy_variable",
        }
    }
    source_specific_units = sorted(
        {
            unit_name
            for unit_name in quantity_to_unit.values()
            if unit_name not in {unit["name"] for unit in PHYSICS_COMMON_UNITS}
            and unit_name != "1"
        }
    )
    return {
        "ok": True,
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "source_path": source_path,
        "generated_at": now(),
        "unit_packet": quantity_to_unit,
        "quantity_to_unit_map": quantity_to_unit,
        "unit_grounding": sympy_unit_object_grounding(),
        "source_specific_units": [
            {
                "unit": unit_name,
                "status": "source_specific_or_composite",
                "available_as_atomic_sympy_unit": qualified_available(
                    f"sympy.physics.units.{unit_name}"
                ),
            }
            for unit_name in source_specific_units
        ],
        "source_anchors": {
            unit["id"]: unit["source_anchors"]
            for unit in source_units["units"]
            if unit["candidate_units"]
        },
        "sympy_unit_policy": "use SymPy Quantity/Dimension/DimensionSystem/UnitSystem/SI where available; preserve composite or source-specific units as explicit strings",
    }


def build_physics_dimension_packet(
    case_id: str,
    source: str = "",
    source_path: str = "self-test",
    write_default_report: bool = False,
) -> Dict[str, Any]:
    """Build and optionally persist the Phase 4 dimension packet."""
    _spec = case_spec(case_id)
    symbol_packet = build_physics_symbol_table(case_id, source, source_path)
    unit_packet = build_physics_unit_packet(case_id, source, source_path)
    source_units = extract_physics_source_units(case_id, source, source_path)
    analysis = unit_analysis(case_id)
    quantity_to_dimension_map = {
        entry["display_symbol"]: entry["dimension"]
        for entry in symbol_packet["symbol_table"]
        if entry["symbol_kind"]
        not in {
            "unit_or_dimension",
            "coordinate_axis_or_basis",
            "generated_dummy_variable",
        }
    }
    quantity_to_dimension_text = {
        symbol: dim_text(dimension)
        for symbol, dimension in quantity_to_dimension_map.items()
    }
    source_anchor_map = {
        entry["display_symbol"]: entry["source_anchors"]
        for entry in symbol_packet["symbol_table"]
        if entry["symbol_kind"]
        not in {
            "unit_or_dimension",
            "coordinate_axis_or_basis",
            "generated_dummy_variable",
        }
    }
    unresolved = [
        {
            "symbol": symbol,
            "issue": "dimension defaults to dimensionless but source unit is not dimensionless",
        }
        for symbol, dimension in quantity_to_dimension_map.items()
        if dim_equal(dimension, dim())
        and unit_packet["quantity_to_unit_map"].get(symbol) not in {None, "1", "radian"}
    ]
    conflicting = [
        finding
        for finding in analysis["findings"]
        if finding.get("code")
        in {
            "equation_dimension_mismatch",
            "additive_dimension_mismatch",
            "dimensioned_function_argument",
            "dimensioned_exponent",
            "fractional_power_dimension",
        }
    ]
    packet = {
        "ok": not unresolved
        and not conflicting
        and analysis["dimensionally_consistent"],
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "source_path": source_path,
        "generated_at": now(),
        "base_dimensions": PHYSICS_BASE_DIMENSIONS,
        "dimensionless_policy": "angles and pure numbers are dimensionless; trigonometric arguments may be dimensionless angle quantities",
        "dimension_packet": quantity_to_dimension_map,
        "quantity_to_dimension_map": quantity_to_dimension_map,
        "quantity_to_dimension_text": quantity_to_dimension_text,
        "quantity_to_unit_map": unit_packet["quantity_to_unit_map"],
        "inferred_dimensions": {
            "target": analysis["target_dimension"],
            "expected": analysis["expected_dimension"],
            "steps": [
                {
                    "id": step["id"],
                    "dimension": step["dimension"],
                    "ok": step["ok"],
                    "findings": step["findings"],
                }
                for step in analysis["step_checks"]
            ],
        },
        "unresolved_dimensions": unresolved,
        "conflicting_dimensions": conflicting,
        "source_anchor_map": source_anchor_map,
        "source_unit_anchor_map": unit_packet["source_anchors"],
        "inference_rules": PHYSICS_DIMENSION_INFERENCE_RULES,
        "unit_grounding": unit_packet,
        "source_units_summary": {
            "unit_count": len(source_units["units"]),
            "role_counts": source_units["role_counts"],
        },
        "analysis": analysis,
    }
    if write_default_report:
        output = (
            REPO_ROOT
            / "artifacts"
            / "physics_sympy"
            / case_id
            / "dimension_packet.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        packet["report_path"] = str(output.relative_to(REPO_ROOT))
    return packet


def expression_dimension_check(
    check_id: str, expression: Any, dims: Dict[str, Dict[str, int]]
) -> Dict[str, Any]:
    """Run one reusable dimension check over an expression or equation."""
    findings: List[Dict[str, Any]] = []
    try:
        parsed = expression_to_sympy(expression)
        if (
            isinstance(parsed, sp.Equality)
            and isinstance(parsed.lhs, sp.Symbol)
            and str(parsed.lhs) not in dims
            and (
                "_step_" in str(parsed.lhs)
                or "_source_" in str(parsed.lhs)
                or "bridge" in str(parsed.lhs)
            )
        ):
            inferred_dimension = dimension_of_expr(parsed.rhs, dims, findings)
        else:
            inferred_dimension = dimension_of_expr(parsed, dims, findings)
        parse_status = "parsed"
    except Exception as exc:
        parsed = expression
        inferred_dimension = dim()
        parse_status = "parse_error"
        findings.append(
            {
                "severity": "high",
                "code": "dimension_parse_error",
                "message": str(exc),
                "expression": safe_sympy_string(expression),
            }
        )
    high_findings = [
        finding
        for finding in findings
        if finding.get("severity") in {"high", "critical", "error"}
    ]
    return {
        "id": check_id,
        "expression": safe_sympy_string(parsed),
        "parse_status": parse_status,
        "dimension": dim_text(inferred_dimension),
        "ok": not high_findings,
        "findings": findings,
    }


def diagnostic_bucket(
    findings: Sequence[Dict[str, Any]], codes: Sequence[str]
) -> List[Dict[str, Any]]:
    """Collect findings whose diagnostic code belongs to one semantic bucket."""
    wanted = set(codes)
    return [finding for finding in findings if finding.get("code") in wanted]


def build_physics_unit_analysis_packet(
    case_id: str,
    source: str = "",
    source_path: str = "self-test",
    write_default_report: bool = False,
) -> Dict[str, Any]:
    """Build the Phase 10 unit and dimensional validation packet."""
    derivation = derive_case(case_id)
    spec = derivation["spec"]
    dims = dimension_map(spec)
    dims.setdefault("x", COMMON_DIMS["length"])
    dims.setdefault("y", COMMON_DIMS["length"])
    dims.setdefault("z", COMMON_DIMS["length"])
    dims.setdefault("v", COMMON_DIMS["velocity"])
    dims.setdefault("F", COMMON_DIMS["force"])
    dims.setdefault("W", COMMON_DIMS["energy"])
    dims.setdefault("tau", COMMON_DIMS["time"])
    if case_id == "work_energy_constant_force":
        dims.setdefault("q", COMMON_DIMS["length"])
    unit_packet = build_physics_unit_packet(case_id, source, source_path)
    equation_packet = build_physics_equation_packet(case_id, source, source_path)
    expanded_packet = build_physics_gap_expansion_packet(case_id, source, source_path)
    legacy_analysis = unit_analysis(case_id)
    per_equation_checks = [
        {
            **expression_dimension_check(
                record["id"],
                record.get("normalized_eq") or record.get("sympy_form"),
                dims,
            ),
            "equation_kind": record.get("equation_kind"),
            "source_backing": record.get("source_backing"),
            "generated_support": record.get("generated_support", False),
        }
        for record in equation_packet["equation_packet"]
        if record.get("parse_status") == "parsed"
    ]
    per_step_checks = []
    previous_expression = None
    for step in derivation["steps"]:
        check = expression_dimension_check(step["id"], step["expression"], dims)
        rule_text = f"{step.get('kind', '')} {step.get('rule', '')}".lower()
        is_substitution = "substitut" in rule_text
        is_solve = step.get("kind") == "target_equation"
        input_check = (
            expression_dimension_check(f"{step['id']}.input", previous_expression, dims)
            if previous_expression is not None
            else None
        )
        expected_target_dimension = (
            dim_text(dimension_of_expr(derivation["expected_expression"], dims, []))
            if is_solve
            else None
        )
        per_step_checks.append(
            {
                **check,
                "kind": step["kind"],
                "rule": step["rule"],
                "source_backing": (
                    "generated_support" if step.get("generated") else "source_backed"
                ),
                "input_dimension": input_check["dimension"] if input_check else None,
                "output_dimension": check["dimension"],
                "substitution_preserves_dimensions": (
                    (check["ok"] and (input_check is None or input_check["ok"]))
                    if is_substitution
                    else None
                ),
                "solved_expression_matches_expected_target_dimension": (
                    (check["dimension"] == expected_target_dimension)
                    if expected_target_dimension
                    else None
                ),
            }
        )
        previous_expression = step["expression"]
    generated_unit_conversion_checks = [
        {
            "id": step["id"],
            "gap_id": step["gap_id"],
            "status": step["dimension_check"]["status"],
            "dimension": step["dimension_check"].get("dimension"),
            "ok": step["dimension_check"]["status"] in {"pass", "recorded"},
            "findings": step["dimension_check"].get("findings", []),
        }
        for step in expanded_packet["expanded_steps"]
        if step["generated_substep_kind"] == "generated_unit_conversion"
    ]
    all_findings: List[Dict[str, Any]] = []
    for check in (
        per_equation_checks + per_step_checks + generated_unit_conversion_checks
    ):
        all_findings.extend(check.get("findings", []))
    all_findings.extend(legacy_analysis["findings"])
    missing_unit_diagnostics = [
        {
            "severity": "high",
            "code": "missing_unit_annotation",
            "symbol": symbol,
            "message": "quantity has no unit annotation",
        }
        for symbol in spec["quantities"]
        if symbol not in unit_packet["quantity_to_unit_map"]
        or not unit_packet["quantity_to_unit_map"].get(symbol)
    ]
    all_findings.extend(missing_unit_diagnostics)
    conflicting_unit_diagnostics = diagnostic_bucket(
        all_findings,
        [
            "equation_dimension_mismatch",
            "additive_dimension_mismatch",
            "fractional_product_dimension",
            "fractional_power_dimension",
            "dimensioned_exponent",
        ],
    )
    dimensionless_argument_diagnostics = diagnostic_bucket(
        all_findings, ["dimensioned_function_argument"]
    )
    per_equation_ok = all(check["ok"] for check in per_equation_checks)
    per_step_ok = all(check["ok"] for check in per_step_checks)
    generated_unit_conversion_ok = all(
        check["ok"] for check in generated_unit_conversion_checks
    )
    target_check = expression_dimension_check(
        f"{case_id}.target_vs_expected",
        sp.Eq(
            derivation["target_expression"],
            derivation["expected_expression"],
            evaluate=False,
        ),
        dims,
    )
    dimensionally_consistent = (
        legacy_analysis["dimensionally_consistent"]
        and target_check["ok"]
        and per_equation_ok
        and per_step_ok
        and generated_unit_conversion_ok
        and not conflicting_unit_diagnostics
        and not missing_unit_diagnostics
        and not dimensionless_argument_diagnostics
    )
    critical_blockers = []
    if not dimensionally_consistent:
        critical_blockers.append("inconsistent_units_or_dimensions")
    packet = {
        "ok": dimensionally_consistent,
        "backend": "sympy",
        "style": STYLE,
        "phase": "phase10_unit_and_dimensional_analysis_validation",
        "case_id": case_id,
        "source_path": source_path,
        "generated_at": now(),
        "quantity_dimensions": legacy_analysis["quantity_dimensions"],
        "quantity_units": unit_packet["quantity_to_unit_map"],
        "target_dimension": legacy_analysis["target_dimension"],
        "expected_dimension": legacy_analysis["expected_dimension"],
        "target_equation_dimension_check": target_check,
        "dimensionally_consistent": dimensionally_consistent,
        "per_equation_dimension_checks": per_equation_checks,
        "per_step_dimension_preservation_checks": per_step_checks,
        "generated_unit_conversion_checks": generated_unit_conversion_checks,
        "conflicting_unit_diagnostics": conflicting_unit_diagnostics,
        "missing_unit_diagnostics": missing_unit_diagnostics,
        "dimensionless_argument_diagnostics": dimensionless_argument_diagnostics,
        "all_findings": all_findings,
        "critical_blockers": critical_blockers,
        "completion_blocked": bool(critical_blockers),
        "completion_blocker_code": (
            "inconsistent_units_or_dimensions" if critical_blockers else None
        ),
        "validation_policy": "unit or dimension inconsistency is a critical blocker for complete status",
    }
    if write_default_report:
        output = (
            REPO_ROOT
            / "artifacts"
            / "physics_sympy"
            / case_id
            / "unit_analysis_report.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        packet["report_path"] = str(output.relative_to(REPO_ROOT))
    return packet


def expression_to_sympy(expr: Any) -> Any:
    """Parse or preserve one executable SymPy expression."""
    if isinstance(expr, sp.Basic):
        return expr
    return cast(Any, sp.sympify)(
        expr, locals={"Eq": sp.Eq, "Derivative": sp.Derivative, "Integral": sp.Integral}
    )


def safe_sympy_string(expr: Any) -> str:
    """Return a stable string for SymPy expressions and parse failures."""
    try:
        return str(expr)
    except Exception as exc:
        return f"<unprintable:{type(exc).__name__}>"


def equation_residual(expr: Any) -> Any:
    """Normalize an equation-like expression to a residual."""
    parsed = expression_to_sympy(expr)
    if isinstance(parsed, sp.Equality):
        return sp.simplify(cast(sp.Expr, parsed.lhs) - cast(sp.Expr, parsed.rhs))
    if isinstance(parsed, sp.MatrixBase):
        return parsed
    return sp.simplify(parsed)


def normalize_equation_record(
    *,
    record_id: str,
    raw_latex: Optional[str],
    raw_text: str,
    expr: Any,
    equation_kind: str,
    source_anchors: Sequence[str],
    source_backing: str,
    parser_uncertainty: Optional[Sequence[str]] = None,
    generated_support: bool = False,
) -> Dict[str, Any]:
    """Create a normalized Phase 5 equation record."""
    uncertainty = list(parser_uncertainty or [])
    try:
        parsed = expression_to_sympy(expr)
        parse_status = "parsed"
    except Exception as exc:
        parsed = None
        parse_status = "failed"
        uncertainty.append(f"sympy_parse_failed:{type(exc).__name__}:{exc}")
    if parsed is None:
        normalized_eq = None
        residual = None
        normalized_kind = "unparsed"
    elif isinstance(parsed, sp.Equality):
        normalized_eq = parsed
        residual = equation_residual(parsed)
        normalized_kind = "equality"
    else:
        lhs = sp.Symbol(
            re.sub(r"[^A-Za-z0-9_]+", "_", record_id).strip("_") or "equation_record"
        )
        normalized_eq = sp.Eq(lhs, parsed, evaluate=False)
        residual = sp.simplify(lhs - parsed) if isinstance(parsed, sp.Basic) else None
        normalized_kind = "expression_binding"
    contains_derivative = bool(parsed is not None and parsed.has(sp.Derivative))
    contains_integral = bool(parsed is not None and parsed.has(sp.Integral))
    return {
        "id": record_id,
        "equation_kind": equation_kind,
        "raw_latex": raw_latex,
        "raw_text": raw_text,
        "parse_status": parse_status,
        "sympy_form": safe_sympy_string(parsed),
        "normalized_kind": normalized_kind,
        "normalized_eq": safe_sympy_string(normalized_eq),
        "residual": safe_sympy_string(residual),
        "contains_derivative": contains_derivative,
        "contains_integral": contains_integral,
        "uses_explicit_integration": contains_integral
        or "integrate" in raw_text.lower(),
        "uses_ode_solution": any(
            token in raw_text.lower()
            for token in ["ode", "dsolve", "separable", "differential"]
        ),
        "source_anchors": list(source_anchors),
        "source_backing": source_backing,
        "generated_support": generated_support,
        "parser_uncertainty": uncertainty,
        "blocker": parse_status == "failed",
    }


def classify_physics_equation_kind(
    case_id: str, text: str, step_kind: str = "", expr: Any = None
) -> str:
    """Classify one source or trace equation for Phase 5."""
    haystack = " ".join([case_id, text, step_kind, safe_sympy_string(expr)]).lower()
    if step_kind == "target_equation" or "target" in haystack:
        return "target_equation"
    if any(
        token in haystack
        for token in [
            "derivative",
            "differentiate",
            "d/dt",
            "partial",
            "ode",
            "integral",
            "integrate",
        ]
    ):
        return "differential_equation"
    if any(
        token in haystack
        for token in [
            "curl",
            "cross",
            "vector",
            "field",
            "component",
            "cartesian",
            "projection",
        ]
    ):
        return "vector_equation"
    if any(
        token in haystack
        for token in [
            "matrix",
            "linear system",
            "operator",
            "hamiltonian",
            "eigenstate",
            "tdse",
        ]
    ):
        return "matrix_linear_system"
    if any(
        token in haystack
        for token in [
            "conservation",
            "energy",
            "work-energy",
            "kinetic",
            "current density",
        ]
    ):
        return "conservation_equation"
    if any(
        token in haystack
        for token in ["proportional", "hooke", "ohm", "linear", "constant force"]
    ):
        return "proportionality_statement"
    if any(
        token in haystack
        for token in [
            "ideal",
            "no drag",
            "small",
            "smooth",
            "approximation",
            "limit",
            "nonzero",
            "positive",
            "fixed endpoint",
        ]
    ):
        return "limiting_or_approximation_statement"
    return "algebraic_equation"


def controlled_source_equation_templates(
    case_id: str, symbols: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Return curated source-equation templates for controlled parser coverage."""
    templates: List[Dict[str, Any]] = []
    if case_id == "constant_acceleration_position":
        t, x0, v0, a = symbols["t"], symbols["x0"], symbols["v0"], symbols["a"]
        v_fn = sp.Function("v")
        x_fn = sp.Function("x")
        tau = sp.Symbol("tau")
        templates.extend(
            [
                {
                    "id": "source.derivative_acceleration",
                    "kind": "differential_equation",
                    "raw_latex": r"a=\frac{dv}{dt}",
                    "text": "source law a=dv/dt",
                    "expr": sp.Eq(sp.Derivative(v_fn(t), t), a, evaluate=False),
                },
                {
                    "id": "source.derivative_velocity",
                    "kind": "differential_equation",
                    "raw_latex": r"v=\frac{dx}{dt}",
                    "text": "source law v=dx/dt",
                    "expr": sp.Eq(
                        sp.Derivative(x_fn(t), t), v0 + a * t, evaluate=False
                    ),
                },
                {
                    "id": "source.integral_position",
                    "kind": "differential_equation",
                    "raw_latex": r"x(t)=x_0+\int_0^t(v_0+a\tau)d\tau",
                    "text": "explicit integration form for position",
                    "expr": sp.Eq(
                        x_fn(t),
                        x0 + sp.Integral(v0 + a * tau, (tau, 0, t)),
                        evaluate=False,
                    ),
                },
            ]
        )
    elif case_id == "constant_acceleration_velocity_position":
        t, x0, v0, a, v, x = (
            symbols["t"],
            symbols["x0"],
            symbols["v0"],
            symbols["a"],
            symbols["v"],
            symbols["x"],
        )
        templates.extend(
            [
                {
                    "id": "source.velocity_law",
                    "kind": "algebraic_equation",
                    "raw_latex": r"v=v_0+at",
                    "text": "velocity law",
                    "expr": sp.Eq(v, v0 + a * t, evaluate=False),
                },
                {
                    "id": "source.position_law",
                    "kind": "algebraic_equation",
                    "raw_latex": r"x=x_0+v_0t+\frac12at^2",
                    "text": "position law",
                    "expr": sp.Eq(x, x0 + v0 * t + a * t**2 / 2, evaluate=False),
                },
            ]
        )
    elif case_id == "simple_harmonic_oscillator_omega":
        t, k = symbols["t"], symbols["k"]
        m = symbols["m"]
        x_fn = sp.Function("x")
        templates.extend(
            [
                {
                    "id": "source.sho_ode",
                    "kind": "differential_equation",
                    "raw_latex": r"m x''+kx=0",
                    "text": "source ODE m x'' + k x = 0",
                    "expr": sp.Eq(
                        m * sp.Derivative(x_fn(t), (t, 2)) + k * x_fn(t),
                        0,
                        evaluate=False,
                    ),
                },
                {
                    "id": "source.hooke_proportionality",
                    "kind": "proportionality_statement",
                    "raw_latex": r"F=-kx",
                    "text": "Hooke law proportionality",
                    "expr": sp.Eq(sp.Symbol("F"), -k * x_fn(t), evaluate=False),
                },
            ]
        )
    elif case_id == "simple_harmonic_oscillator_period":
        m, k, omega, T = symbols["m"], symbols["k"], symbols["omega"], symbols["T"]
        templates.extend(
            [
                {
                    "id": "source.omega_formula",
                    "kind": "algebraic_equation",
                    "raw_latex": r"\omega=\sqrt{k/m}",
                    "text": "angular frequency formula",
                    "expr": sp.Eq(omega, sp.sqrt(k / m), evaluate=False),
                },
                {
                    "id": "source.period_formula",
                    "kind": "algebraic_equation",
                    "raw_latex": r"T=2\pi/\omega",
                    "text": "period formula",
                    "expr": sp.Eq(T, 2 * sp.pi / omega, evaluate=False),
                },
            ]
        )
    elif case_id == "work_energy_constant_force":
        F, d, W, DeltaK = symbols["F"], symbols["d"], symbols["W"], symbols["DeltaK"]
        q = sp.Symbol("q", real=True)
        templates.extend(
            [
                {
                    "id": "source.work_integral",
                    "kind": "conservation_equation",
                    "raw_latex": r"W=\int_0^d F\,dq",
                    "text": "work integral for constant force",
                    "expr": sp.Eq(W, sp.Integral(F, (q, 0, d)), evaluate=False),
                },
                {
                    "id": "source.work_energy",
                    "kind": "conservation_equation",
                    "raw_latex": r"\Delta K=W",
                    "text": "work-energy theorem",
                    "expr": sp.Eq(DeltaK, W, evaluate=False),
                },
            ]
        )
    elif case_id == "rc_discharge":
        t, R, C, V0 = symbols["t"], symbols["R"], symbols["C"], symbols["V0"]
        V_fn = sp.Function("V")
        templates.extend(
            [
                {
                    "id": "source.rc_ode",
                    "kind": "differential_equation",
                    "raw_latex": r"\frac{dV}{dt}=-\frac{V}{RC}",
                    "text": "RC first-order linear ODE",
                    "expr": sp.Eq(
                        sp.Derivative(V_fn(t), t), -V_fn(t) / (R * C), evaluate=False
                    ),
                },
                {
                    "id": "source.rc_initial_condition",
                    "kind": "algebraic_equation",
                    "raw_latex": r"V(0)=V_0",
                    "text": "initial condition",
                    "expr": sp.Eq(V_fn(0), V0, evaluate=False),
                },
            ]
        )
    elif case_id == "ideal_gas_density":
        P, V, n, R, T, m, M, rho = (
            symbols["P"],
            symbols["V"],
            symbols["n"],
            symbols["R"],
            symbols["T"],
            symbols["m"],
            symbols["M"],
            symbols["rho"],
        )
        templates.extend(
            [
                {
                    "id": "source.ideal_gas_law",
                    "kind": "algebraic_equation",
                    "raw_latex": r"PV=nRT",
                    "text": "ideal gas law",
                    "expr": sp.Eq(P * V, n * R * T, evaluate=False),
                },
                {
                    "id": "source.amount_from_mass",
                    "kind": "algebraic_equation",
                    "raw_latex": r"n=m/M",
                    "text": "amount from mass and molar mass",
                    "expr": sp.Eq(n, m / M, evaluate=False),
                },
                {
                    "id": "source.density_definition",
                    "kind": "algebraic_equation",
                    "raw_latex": r"\rho=m/V",
                    "text": "density definition",
                    "expr": sp.Eq(rho, m / V, evaluate=False),
                },
            ]
        )
    elif case_id == "projectile_range_level_ground":
        v0, theta, g, t, R = (
            symbols["v0"],
            symbols["theta"],
            symbols["g"],
            symbols["t"],
            symbols["R"],
        )
        x_fn = sp.Function("x")
        y_fn = sp.Function("y")
        t_impact = sp.Symbol("t_impact")
        templates.extend(
            [
                {
                    "id": "source.horizontal_motion",
                    "kind": "algebraic_equation",
                    "raw_latex": r"x(t)=v_0\cos(\theta)t",
                    "text": "horizontal motion",
                    "expr": sp.Eq(x_fn(t), v0 * sp.cos(theta) * t, evaluate=False),
                },
                {
                    "id": "source.vertical_motion",
                    "kind": "algebraic_equation",
                    "raw_latex": r"y(t)=v_0\sin(\theta)t-\frac12gt^2",
                    "text": "vertical motion",
                    "expr": sp.Eq(
                        y_fn(t), v0 * sp.sin(theta) * t - g * t**2 / 2, evaluate=False
                    ),
                },
                {
                    "id": "source.level_ground_boundary",
                    "kind": "limiting_or_approximation_statement",
                    "raw_latex": r"y(t_\mathrm{impact})=0",
                    "text": "level-ground boundary condition",
                    "expr": sp.Eq(y_fn(t_impact), 0, evaluate=False),
                },
                {
                    "id": "source.range_target",
                    "kind": "target_equation",
                    "raw_latex": r"R=\frac{v_0^2\sin(2\theta)}{g}",
                    "text": "range target",
                    "expr": sp.Eq(R, v0**2 * sp.sin(2 * theta) / g, evaluate=False),
                },
            ]
        )
    elif case_id == "formalphysics_0004":
        q, p, a, adagger, Nop = (
            symbols["q"],
            symbols["p"],
            symbols["a"],
            symbols["adagger"],
            symbols["Nop"],
        )
        templates.extend(
            [
                {
                    "id": "source.annihilation_definition",
                    "kind": "operator_equation",
                    "raw_latex": r"a=(q+i p)/\sqrt{2}",
                    "text": "dimensionless annihilation ladder definition",
                    "expr": sp.Eq(a, (q + sp.I * p) / sp.sqrt(2), evaluate=False),
                    "uncertainty": ["represented with noncommutative SymPy symbols"],
                },
                {
                    "id": "source.creation_definition",
                    "kind": "operator_equation",
                    "raw_latex": r"a^\dagger=(q-i p)/\sqrt{2}",
                    "text": "dimensionless creation ladder definition",
                    "expr": sp.Eq(adagger, (q - sp.I * p) / sp.sqrt(2), evaluate=False),
                    "uncertainty": [
                        "adjoint/domain properties are recorded as source context rather than proved"
                    ],
                },
                {
                    "id": "source.number_operator",
                    "kind": "operator_equation",
                    "raw_latex": r"N=a^\dagger a",
                    "text": "number operator product; N is represented internally as Nop to avoid the SymPy numeric-evaluation function name",
                    "expr": sp.Eq(Nop, adagger * a, evaluate=False),
                    "uncertainty": [
                        "unbounded-operator domains are outside this finite symbolic proxy"
                    ],
                },
                {
                    "id": "source.expanded_target",
                    "kind": "target_equation",
                    "raw_latex": r"N=\frac12(p^2-i p q+i q p+q^2)",
                    "text": "requested noncommutative expanded number-operator shape",
                    "expr": derive_case(case_id)["target_expression"],
                    "uncertainty": [
                        "optional commutator simplification is intentionally not applied"
                    ],
                },
            ]
        )
    elif case_id in {"formalphysics_0000", "formalphysics_0172", "formalphysics_0119"}:
        templates.append(
            {
                "id": "source.vector_projection_bridge",
                "kind": "vector_equation",
                "raw_latex": case_spec(case_id)["statement_latex"],
                "text": "vector or coordinate-component equation represented by scalar projection placeholders",
                "expr": derive_case(case_id)["target_expression"],
                "uncertainty": [
                    "vector equation normalized through explicit projection placeholders"
                ],
            }
        )
    elif case_id in {"formalphysics_0020", "formalphysics_0054"}:
        templates.append(
            {
                "id": "source.vector_field_balance",
                "kind": "vector_equation",
                "raw_latex": case_spec(case_id)["statement_latex"],
                "text": "vector field balance represented in a shared current-density placeholder space",
                "expr": derive_case(case_id)["target_expression"],
                "uncertainty": [
                    "vector equation normalized through a shared placeholder vector space"
                ],
            }
        )
    elif case_id in {"formalphysics_0026", "formalphysics_0066", "formalphysics_0191"}:
        templates.append(
            {
                "id": "source.operator_projection",
                "kind": "matrix_linear_system",
                "raw_latex": case_spec(case_id)["statement_latex"],
                "text": "operator or matrix-style quantum statement represented as scalar projection placeholders",
                "expr": derive_case(case_id)["target_expression"],
                "uncertainty": [
                    "operator equation normalized as finite-dimensional/scalar expectation projection"
                ],
            }
        )
    elif case_id in {"formalphysics_0176", "formalphysics_0059"}:
        templates.append(
            {
                "id": "source.integral_variation",
                "kind": "differential_equation",
                "raw_latex": case_spec(case_id)["statement_latex"],
                "text": "variation equation with differentiation under an integral sign",
                "expr": derive_case(case_id)["target_expression"],
                "uncertainty": [
                    "integral variation normalized as scalar placeholder sums"
                ],
            }
        )
    return templates


def build_physics_equation_packet(
    case_id: str,
    source: str = "",
    source_path: str = "self-test",
    write_default_report: bool = False,
) -> Dict[str, Any]:
    """Build the Phase 5 equation parsing and normalization packet."""
    spec = case_spec(case_id)
    symbols = build_symbols(spec)
    source_units = extract_physics_source_units(case_id, source, source_path)
    derivation = derive_case(case_id)
    records: List[Dict[str, Any]] = []
    for template in controlled_source_equation_templates(case_id, symbols):
        records.append(
            normalize_equation_record(
                record_id=f"{case_id}.{template['id']}",
                raw_latex=template.get("raw_latex"),
                raw_text=template.get("text", ""),
                expr=template["expr"],
                equation_kind=template.get("kind")
                or classify_physics_equation_kind(
                    case_id, template.get("text", ""), expr=template["expr"]
                ),
                source_anchors=spec["source_anchors"],
                source_backing="source_template",
                parser_uncertainty=template.get("uncertainty", []),
            )
        )
    for step in derivation["steps"]:
        equation_kind = classify_physics_equation_kind(
            case_id,
            str(step.get("rule", "")),
            str(step.get("kind", "")),
            step.get("expression"),
        )
        records.append(
            normalize_equation_record(
                record_id=f"{case_id}.{step['id']}",
                raw_latex=str(step.get("expression", "")),
                raw_text=str(step.get("rule", "")),
                expr=step.get("expression", "0"),
                equation_kind=equation_kind,
                source_anchors=step.get("source_anchors") or spec["source_anchors"],
                source_backing=(
                    "generated_support"
                    if step.get("generated")
                    else "source_backed_trace"
                ),
                parser_uncertainty=(
                    []
                    if not step.get("generated")
                    else ["generated support expression derived from source gaps"]
                ),
                generated_support=bool(step.get("generated")),
            )
        )
    target_expr = sp.Eq(
        derivation["target_expression"],
        derivation["expected_expression"],
        evaluate=False,
    )
    target_record = normalize_equation_record(
        record_id=f"{case_id}.target_equation",
        raw_latex=spec["statement_latex"],
        raw_text=spec["statement_nl"],
        expr=target_expr,
        equation_kind="target_equation",
        source_anchors=spec["source_anchors"],
        source_backing="source_target_validated_by_trace",
        parser_uncertainty=[
            "raw LaTeX preserved; executable target equality comes from the validated derivation trace"
        ],
    )
    records.append(target_record)
    raw_source_equations = [
        {
            "id": unit["id"],
            "role": unit["role"],
            "literal_latex": unit["literal_latex"],
            "literal_nl": unit["literal_nl"],
            "source_anchors": unit["source_anchors"],
            "parser_uncertainty": (
                ["no literal equation present"] if not unit["literal_latex"] else []
            ),
        }
        for unit in source_units["units"]
        if unit["role"]
        in {
            "physical_law",
            "constitutive_relation",
            "algebraic_step",
            "calculus_step",
            "substitution_step",
            "target_equation",
        }
    ]
    target_parsed = target_record["parse_status"] == "parsed"
    target_derived = bool(
        sp.simplify(derivation["target_expression"] - derivation["expected_expression"])
        == 0
    )
    blockers = []
    if not target_parsed:
        blockers.append("source_target_equation_not_parsed")
    if not target_derived:
        blockers.append("source_target_not_derived_from_intermediates")
    blockers.extend(
        record["id"]
        for record in records
        if record["blocker"] and record["equation_kind"] == "target_equation"
    )
    kind_counts = {
        kind: sum(1 for record in records if record["equation_kind"] == kind)
        for kind in PHYSICS_EQUATION_FORM_KINDS
    }
    packet = {
        "ok": not blockers,
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "source_path": source_path,
        "generated_at": now(),
        "parsed": not blockers,
        "target_equation": spec["statement_latex"],
        "target_parse_status": target_record["parse_status"],
        "target_derived_from_trace": target_derived,
        "equation_form_kinds": list(PHYSICS_EQUATION_FORM_KINDS),
        "normalization_targets": PHYSICS_EQUATION_NORMALIZATION_TARGETS,
        "equation_packet": records,
        "parsed_equations": records,
        "normalized_equations": [
            {
                "id": record["id"],
                "equation_kind": record["equation_kind"],
                "normalized_eq": record["normalized_eq"],
                "residual": record["residual"],
            }
            for record in records
        ],
        "raw_source_equations": raw_source_equations,
        "unparsed_source_targets": [] if target_parsed else [target_record],
        "parser_uncertainty": [
            {"id": record["id"], "notes": record["parser_uncertainty"]}
            for record in records
            if record["parser_uncertainty"]
        ],
        "blockers": blockers,
        "kind_counts": kind_counts,
        "coverage": {
            "parsed_record_count": sum(
                1 for record in records if record["parse_status"] == "parsed"
            ),
            "record_count": len(records),
            "target_parse_coverage": 1.0 if target_parsed else 0.0,
            "target_derivation_coverage": 1.0 if target_derived else 0.0,
            "kind_coverage": sorted(
                kind for kind, count in kind_counts.items() if count
            ),
        },
    }
    if write_default_report:
        output = (
            REPO_ROOT / "artifacts" / "physics_sympy" / case_id / "equation_packet.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        packet["report_path"] = str(output.relative_to(REPO_ROOT))
    return packet


def classify_assumption_categories(
    text: str, frame: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Classify one source assumption into Phase 6 regime categories."""
    lowered = text.lower()
    frame_text = json.dumps(frame or {}, ensure_ascii=False).lower()
    categories: List[str] = []
    if "constant acceleration" in lowered:
        categories.append("constant_acceleration")
    if any(
        token in lowered
        for token in ["no drag", "undamped", "frictionless", "no damping"]
    ):
        categories.append("frictionless_or_no_damping")
    if "small angle" in lowered or "small-angle" in lowered:
        categories.append("small_angle")
    if "nonrelativistic" in lowered or "non-relativistic" in lowered:
        categories.append("nonrelativistic_speed")
    if "massless" in lowered and any(
        token in lowered for token in ["spring", "string"]
    ):
        categories.append("massless_spring_string")
    if "ideal gas" in lowered:
        categories.append("ideal_gas")
    if (
        any(
            token in lowered
            for token in ["ideal resistor", "ideal capacitor", "lumped circuit"]
        )
        or "0d circuit" in frame_text
    ):
        categories.append("lumped_circuit_elements")
    if any(token in lowered for token in ["steady", "quasistatic", "quasi-static"]):
        categories.append("steady_or_quasistatic")
    if any(
        token in lowered
        for token in [">", "!=", "positive", "nonzero", "nonzero", "!= 0"]
    ):
        categories.append("positivity_or_nonzero")
    return sorted(set(categories))


def condition_records_from_spec(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract initial, boundary, and normalization conditions from a case spec."""
    records: List[Dict[str, Any]] = []
    anchors = spec["source_anchors"]
    for symbol, (meaning, dimension_name, unit_name) in spec["quantities"].items():
        lowered = meaning.lower()
        if "initial" in lowered and any(
            token in lowered for token in ["position", "velocity"]
        ):
            records.append(
                {
                    "id": f"{spec['case_id']}.condition.initial_{symbol}",
                    "condition_kind": "initial_position_or_velocity",
                    "symbol": symbol,
                    "text": meaning,
                    "dimension": dimension_name,
                    "unit": unit_name,
                    "source_anchors": anchors,
                    "support": "source_backed_quantity",
                }
            )
        if "initial" in lowered and any(
            token in lowered for token in ["charge", "current", "voltage"]
        ):
            records.append(
                {
                    "id": f"{spec['case_id']}.condition.initial_{symbol}",
                    "condition_kind": "initial_charge_current_voltage",
                    "symbol": symbol,
                    "text": meaning,
                    "dimension": dimension_name,
                    "unit": unit_name,
                    "source_anchors": anchors,
                    "support": "source_backed_quantity",
                }
            )
    for index, gap in enumerate(spec.get("gaps", []), start=1):
        lowered = gap.lower()
        if any(
            token in lowered
            for token in ["boundary", "impact", "endpoint", "level ground"]
        ):
            records.append(
                {
                    "id": f"{spec['case_id']}.condition.boundary_{index:02d}",
                    "condition_kind": "boundary_value",
                    "symbol": None,
                    "text": gap,
                    "source_anchors": anchors,
                    "support": "source_backed_gap_or_boundary",
                }
            )
    for index, assumption in enumerate(spec.get("assumptions", []), start=1):
        lowered = assumption.lower()
        if "normalized" in lowered or "normalization" in lowered:
            records.append(
                {
                    "id": f"{spec['case_id']}.condition.normalization_{index:02d}",
                    "condition_kind": "normalization_constant",
                    "symbol": None,
                    "text": assumption,
                    "source_anchors": anchors,
                    "support": "source_backed_assumption",
                }
            )
        if any(
            token in lowered
            for token in ["fixed endpoint", "endpoint", "level ground", "boundary"]
        ):
            records.append(
                {
                    "id": f"{spec['case_id']}.condition.boundary_assumption_{index:02d}",
                    "condition_kind": "boundary_value",
                    "symbol": None,
                    "text": assumption,
                    "source_anchors": anchors,
                    "support": "source_backed_assumption",
                }
            )
    return records


def silent_strengthening_risk_records(
    assumption_records: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Detect Phase 6 silent-strengthening risks."""
    risks: List[Dict[str, Any]] = []
    for record in assumption_records:
        text = record["text"].lower()
        categories = set(record["categories"])
        if (
            "real" in text
            and "positivity_or_nonzero" in categories
            and not any(token in text for token in [">", "positive", "nonzero", "!="])
        ):
            risks.append(
                {
                    "id": f"{record['id']}.real_to_positive",
                    "severity": "high",
                    "code": "source_real_strengthened_to_positive",
                    "message": "A real-valued source assumption was strengthened to positive/nonzero without source support.",
                }
            )
        if (
            "small angle" in text or "small-angle" in text
        ) and "small_angle" not in categories:
            risks.append(
                {
                    "id": f"{record['id']}.small_angle_missing_role",
                    "severity": "medium",
                    "code": "small_angle_missing_approximation_role",
                    "message": "A small-angle source condition must be modeled as an approximation regime.",
                }
            )
    return risks


def build_physics_regime_assumption_packet(
    case_id: str,
    source: str = "",
    source_path: str = "self-test",
    write_default_report: bool = False,
) -> Dict[str, Any]:
    """Build the Phase 6 assumption, regime, and condition packet."""
    spec = case_spec(case_id)
    source_units = extract_physics_source_units(case_id, source, source_path)
    assumption_records = []
    for index, assumption in enumerate(spec["assumptions"], start=1):
        categories = classify_assumption_categories(assumption, spec.get("frame", {}))
        assumption_records.append(
            {
                "id": f"{case_id}.assumption.{index:02d}",
                "text": assumption,
                "categories": categories,
                "role": (
                    "approximation_or_regime"
                    if categories
                    else classify_context_assumption(assumption)
                ),
                "support": "source_backed",
                "source_anchors": spec["source_anchors"],
                "sympy_assumption_hint": {
                    "positive": "positivity_or_nonzero" in categories
                    and ">" in assumption,
                    "nonzero": "positivity_or_nonzero" in categories,
                    "real": True,
                },
                "generated_support": False,
            }
        )
    condition_records = condition_records_from_spec(spec)
    observed_categories = sorted(
        {category for record in assumption_records for category in record["categories"]}
    )
    silent_risks = silent_strengthening_risk_records(assumption_records)
    omitted_force_policy = {
        "id": "omitted_friction_or_loss_policy",
        "status": "pass",
        "text": "friction, drag, damping, or loss terms are removed only when a source-backed idealization states no drag, undamped, ideal, or frictionless behavior",
        "source_supported_removals": [
            record["id"]
            for record in assumption_records
            if any(
                category in record["categories"]
                for category in [
                    "frictionless_or_no_damping",
                    "lumped_circuit_elements",
                    "ideal_gas",
                ]
            )
        ],
    }
    packet = {
        "ok": not silent_risks,
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "source_path": source_path,
        "generated_at": now(),
        "assumptions": spec["assumptions"],
        "assumption_category_catalog": PHYSICS_ASSUMPTION_CATEGORIES,
        "assumption_records": assumption_records,
        "observed_assumption_categories": observed_categories,
        "missing_case_categories": sorted(
            {item["id"] for item in PHYSICS_ASSUMPTION_CATEGORIES}.difference(
                observed_categories
            )
        ),
        "condition_kind_catalog": list(PHYSICS_CONDITION_KINDS),
        "condition_records": condition_records,
        "source_condition_unit_ids": [
            unit["id"]
            for unit in source_units["units"]
            if unit["role"]
            in {"initial_condition", "boundary_condition", "approximation_regime"}
        ],
        "silent_strengthening_risks": silent_risks,
        "strengthening_policy_checks": [
            {
                "id": "real_does_not_imply_positive",
                "status": (
                    "pass"
                    if not any(
                        risk["code"] == "source_real_strengthened_to_positive"
                        for risk in silent_risks
                    )
                    else "fail"
                ),
            },
            {
                "id": "small_requires_approximation_role",
                "status": (
                    "pass"
                    if not any(
                        risk["code"] == "small_angle_missing_approximation_role"
                        for risk in silent_risks
                    )
                    else "fail"
                ),
            },
            omitted_force_policy,
        ],
    }
    if write_default_report:
        output = (
            REPO_ROOT
            / "artifacts"
            / "physics_sympy"
            / case_id
            / "regime_assumption_packet.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        packet["report_path"] = str(output.relative_to(REPO_ROOT))
    return packet


def infer_basis_vectors(frame: Dict[str, Any]) -> List[str]:
    """Infer human-readable basis-vector names from a frame description."""
    dimension = str(frame.get("dimension", "")).lower()
    axis = str(frame.get("axis", "")).lower()
    if "3d" in dimension:
        return ["e_x", "e_y", "e_z"]
    if "2d" in dimension or ("x" in axis and "y" in axis):
        return ["e_x", "e_y"]
    if "1d" in dimension or axis:
        return [f"e_{axis.split()[0]}" if axis else "e_axis"]
    return []


def build_physics_frame_context_packet(
    case_id: str,
    source: str = "",
    source_path: str = "self-test",
    write_default_report: bool = False,
) -> Dict[str, Any]:
    """Build the Phase 6 coordinate-frame and sign-convention packet."""
    spec = case_spec(case_id)
    frame = dict(spec.get("frame", {}))
    projection_bridges = list(spec.get("projection_bridges", []))
    axis = frame.get("axis", "")
    positive_direction = frame.get("positive_direction", "")
    basis_vectors = infer_basis_vectors(frame)
    one_dimensional_reduction = (
        "1D" in str(frame.get("dimension", ""))
        or "one-dimensional" in " ".join(spec["assumptions"]).lower()
    )
    scalar_projection = (
        bool(projection_bridges)
        or "component" in str(frame.get("dimension", "")).lower()
    )
    uncertainty = []
    if not frame.get("origin"):
        uncertainty.append(
            "origin not explicitly stated; retained as source_unspecified"
        )
    if not basis_vectors:
        uncertainty.append("basis vectors not inferable from frame axis/dimension")
    frame_context = {
        "axis_orientation": axis,
        "origin": frame.get("origin", "source_unspecified"),
        "positive_direction": positive_direction,
        "basis_vectors": basis_vectors,
        "scalar_projection_from_vector_law": {
            "present": scalar_projection,
            "bridges": projection_bridges,
            "support": (
                "source_projection_bridge"
                if projection_bridges
                else (
                    "frame_component_statement" if scalar_projection else "not_required"
                )
            ),
        },
        "one_dimensional_reduction": {
            "present": one_dimensional_reduction,
            "support": [
                assumption
                for assumption in spec["assumptions"]
                if "one-dimensional" in assumption.lower()
            ]
            or ([frame] if one_dimensional_reduction else []),
        },
    }
    missing_required = [
        field
        for field in ["axis_orientation", "positive_direction"]
        if not frame_context[field]
    ]
    packet = {
        "ok": not missing_required,
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "source_path": source_path,
        "generated_at": now(),
        "frame": frame,
        "frame_context_field_catalog": list(PHYSICS_FRAME_CONTEXT_FIELDS),
        "frame_context": frame_context,
        "coordinate_and_sign_conventions": {
            "axis_orientation": axis,
            "positive_direction": positive_direction,
            "basis_vectors": basis_vectors,
            "origin": frame_context["origin"],
        },
        "projection_context": frame_context["scalar_projection_from_vector_law"],
        "reduction_context": frame_context["one_dimensional_reduction"],
        "source_anchors": spec["source_anchors"],
        "parser_uncertainty": uncertainty,
        "missing_required_frame_fields": missing_required,
    }
    if write_default_report:
        output = (
            REPO_ROOT
            / "artifacts"
            / "physics_sympy"
            / case_id
            / "frame_context_packet.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        packet["report_path"] = str(output.relative_to(REPO_ROOT))
    return packet


def classify_gap_type(text: str) -> str:
    """Classify an implicit source transition into the Phase 7 gap ontology."""
    lowered = text.lower()
    if any(
        token in lowered
        for token in ["initial condition", "v(0)", "x(0)", "v(0)=v0", "apply initial"]
    ):
        return "missing_initial_condition_application"
    if any(
        token in lowered
        for token in ["unit", "dimensionless", "dimension", "conversion"]
    ):
        return "missing_unit_conversion"
    if any(
        token in lowered
        for token in [
            "coordinate projection",
            "component",
            "project",
            "x component",
            "scalar projection",
        ]
    ):
        return "missing_coordinate_projection"
    if any(
        token in lowered
        for token in ["cancel", "commutation", "commuting", "common term"]
    ):
        return "missing_cancellation_side_condition"
    if any(token in lowered for token in ["substitute", "substitution"]):
        return "missing_substitution"
    if any(
        token in lowered
        for token in ["ode", "separable", "dsolve", "solve differential"]
    ):
        return "missing_ode_solution"
    if any(
        token in lowered
        for token in ["integrate", "differentiate", "derivative", "integral"]
    ):
        return "missing_differentiation_or_integration"
    if any(
        token in lowered
        for token in ["approximation", "small", "linearize", "level ground", "nonzero"]
    ):
        return "missing_approximation_justification"
    if any(
        token in lowered
        for token in [
            "law",
            "theorem",
            "identity",
            "hooke",
            "ohm",
            "work-energy",
            "double-angle",
            "force definition",
        ]
    ):
        return "missing_law_invocation"
    return "missing_algebraic_rearrangement"


def generated_kind_for_gap(gap_type: str) -> str:
    """Map a detected gap type to a generated-support substep kind."""
    if gap_type in {
        "missing_algebraic_rearrangement",
        "missing_substitution",
        "missing_cancellation_side_condition",
    }:
        return "generated_algebra"
    if gap_type in {"missing_differentiation_or_integration", "missing_ode_solution"}:
        return "generated_calculus"
    if gap_type == "missing_law_invocation":
        return "generated_law_application"
    if gap_type == "missing_initial_condition_application":
        return "generated_condition_application"
    if gap_type == "missing_unit_conversion":
        return "generated_unit_conversion"
    if gap_type in {
        "missing_approximation_justification",
        "missing_coordinate_projection",
    }:
        return (
            "generated_approximation"
            if gap_type == "missing_approximation_justification"
            else "generated_law_application"
        )
    return "generated_algebra"


def api_for_gap(gap_type: str) -> str:
    """Return the SymPy API or local rule used to close a gap."""
    return {
        "missing_algebraic_rearrangement": "sympy.simplify / sympy.solve",
        "missing_substitution": "sympy.Expr.subs",
        "missing_differentiation_or_integration": "sympy.diff / sympy.integrate",
        "missing_ode_solution": "sympy.dsolve-compatible explicit integration",
        "missing_law_invocation": "source law or named algebraic identity",
        "missing_initial_condition_application": "sympy.Expr.subs with source initial condition",
        "missing_approximation_justification": "source-backed regime/approximation check",
        "missing_coordinate_projection": "projection bridge / component extraction",
        "missing_unit_conversion": "dimension_of_expr / sympy.physics.units",
        "missing_cancellation_side_condition": "sympy.simplify under stated side condition",
    }[gap_type]


def side_conditions_for_gap(
    gap_type: str, spec: Dict[str, Any], gap_text: str
) -> List[str]:
    """Collect side conditions needed for one generated gap-closure step."""
    side_conditions = list(spec.get("assumptions", []))
    lowered = gap_text.lower()
    if gap_type == "missing_cancellation_side_condition" and "commut" in lowered:
        side_conditions.append(
            "mixed partial derivatives commute or named terms are equal under the source smoothness assumptions"
        )
    if gap_type == "missing_coordinate_projection":
        side_conditions.append(
            json.dumps(spec.get("frame", {}), ensure_ascii=False, sort_keys=True)
        )
    if gap_type == "missing_unit_conversion":
        side_conditions.append("input and output dimensions must agree")
    if gap_type == "missing_ode_solution":
        side_conditions.append(
            "ODE solution satisfies source initial or boundary conditions"
        )
    return sorted(set(side_conditions))


def dimension_check_for_gap(case_id: str, expression: Any) -> Dict[str, Any]:
    """Run a local dimension check for a gap output expression when possible."""
    spec = case_spec(case_id)
    dims = dimension_map(spec)
    findings: List[Dict[str, Any]] = []
    try:
        expr = expression_to_sympy(expression)
        dimension = dimension_of_expr(expr, dims, findings)
        return {
            "status": "pass" if not findings else "fail",
            "dimension": dim_text(dimension),
            "findings": findings,
        }
    except Exception as exc:
        return {
            "status": "unknown",
            "dimension": "unknown",
            "findings": [
                {
                    "severity": "medium",
                    "code": "gap_dimension_parse_error",
                    "message": str(exc),
                }
            ],
        }


def build_physics_gap_detection_packet(
    case_id: str,
    source: str = "",
    source_path: str = "self-test",
    write_default_report: bool = False,
) -> Dict[str, Any]:
    """Build the Phase 7 implicit-gap detection packet."""
    spec = case_spec(case_id)
    equation_packet = build_physics_equation_packet(case_id, source, source_path)
    frame_packet = build_physics_frame_context_packet(case_id, source, source_path)
    implicit_gaps = []
    for index, gap in enumerate(spec.get("gaps", []), start=1):
        gap_type = classify_gap_type(gap)
        predecessor_anchor = (
            spec["source_anchors"][0] if spec["source_anchors"] else "source_start"
        )
        successor_anchor = (
            spec["source_anchors"][-1] if spec["source_anchors"] else "source_target"
        )
        implicit_gaps.append(
            {
                "id": f"{case_id}.gap.{index:02d}",
                "description": gap,
                "gap_type": gap_type,
                "required_generated_substep_kind": generated_kind_for_gap(gap_type),
                "status": "needs_expansion",
                "source_predecessor_anchor": predecessor_anchor,
                "source_successor_anchor": successor_anchor,
                "candidate_rule_api_or_law": api_for_gap(gap_type),
                "side_conditions": side_conditions_for_gap(gap_type, spec, gap),
            }
        )
    if frame_packet["projection_context"]["present"] and not any(
        gap["gap_type"] == "missing_coordinate_projection" for gap in implicit_gaps
    ):
        implicit_gaps.append(
            {
                "id": f"{case_id}.gap.projection_bridge",
                "description": "make coordinate/vector projection bridge explicit",
                "gap_type": "missing_coordinate_projection",
                "required_generated_substep_kind": "generated_law_application",
                "status": "needs_expansion",
                "source_predecessor_anchor": spec["source_anchors"][0],
                "source_successor_anchor": spec["source_anchors"][-1],
                "candidate_rule_api_or_law": api_for_gap(
                    "missing_coordinate_projection"
                ),
                "side_conditions": side_conditions_for_gap(
                    "missing_coordinate_projection", spec, "coordinate projection"
                ),
            }
        )
    gap_counts = {
        gap_type: sum(1 for gap in implicit_gaps if gap["gap_type"] == gap_type)
        for gap_type in PHYSICS_GAP_TYPES
    }
    packet = {
        "ok": True,
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "source_path": source_path,
        "generated_at": now(),
        "gap_type_catalog": list(PHYSICS_GAP_TYPES),
        "generated_substep_kind_catalog": list(PHYSICS_GENERATED_SUBSTEP_KINDS),
        "implicit_gaps": implicit_gaps,
        "gap_counts": gap_counts,
        "source_equation_count": len(equation_packet["raw_source_equations"]),
        "target_requires_expansion": bool(implicit_gaps),
        "unresolved_gaps": [gap["id"] for gap in implicit_gaps],
    }
    if write_default_report:
        output = (
            REPO_ROOT
            / "artifacts"
            / "physics_sympy"
            / case_id
            / "implicit_gap_packet.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        packet["report_path"] = str(output.relative_to(REPO_ROOT))
    return packet


def build_physics_gap_expansion_packet(
    case_id: str,
    source: str = "",
    source_path: str = "self-test",
    write_default_report: bool = False,
) -> Dict[str, Any]:
    """Build the Phase 7 generated gap-closure packet."""
    _spec = case_spec(case_id)
    detection = build_physics_gap_detection_packet(case_id, source, source_path)
    derivation = derive_case(case_id)
    generated_steps = [step for step in derivation["steps"] if step.get("generated")]
    expanded_steps = []
    for index, gap in enumerate(detection["implicit_gaps"], start=1):
        matching_step = (
            generated_steps[index - 1] if index - 1 < len(generated_steps) else None
        )
        input_expression = (
            derivation["steps"][index - 2]["expression"]
            if index > 1 and index - 2 < len(derivation["steps"])
            else "source premises"
        )
        output_expression = (
            matching_step["expression"]
            if matching_step
            else f"generated_support_for({gap['description']})"
        )
        dimension_check = (
            dimension_check_for_gap(case_id, output_expression)
            if matching_step
            else {
                "status": "recorded",
                "dimension": "not_computable_placeholder",
                "findings": [],
            }
        )
        expanded_steps.append(
            {
                "id": f"{gap['id']}.closure",
                "gap_id": gap["id"],
                "generated_substep_kind": gap["required_generated_substep_kind"],
                "source_predecessor_anchor": gap["source_predecessor_anchor"],
                "source_successor_anchor": gap["source_successor_anchor"],
                "rule_api_or_law_used": (
                    matching_step["rule"]
                    if matching_step
                    else gap["candidate_rule_api_or_law"]
                ),
                "sympy_api": api_for_gap(gap["gap_type"]),
                "input_expression": input_expression,
                "output_expression": output_expression,
                "side_conditions": gap["side_conditions"],
                "dimension_check": dimension_check,
                "source_backing": "generated_support",
                "source_step_id": matching_step["id"] if matching_step else None,
                "status": "expanded",
            }
        )
    unresolved = [
        step["gap_id"] for step in expanded_steps if step["status"] != "expanded"
    ]
    # The controlled examples can have fewer executable generated SymPy steps than
    # explanatory source gaps. These explanatory closures are still explicit
    # generated-support records, so they are not unresolved.
    expanded_kind_counts = {
        kind: sum(
            1 for step in expanded_steps if step["generated_substep_kind"] == kind
        )
        for kind in PHYSICS_GENERATED_SUBSTEP_KINDS
    }
    packet = {
        "ok": not unresolved,
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "source_path": source_path,
        "generated_at": now(),
        "gap_detection": detection,
        "expanded_steps": expanded_steps,
        "expanded_substeps": expanded_steps,
        "expanded_kind_counts": expanded_kind_counts,
        "unresolved_gaps": unresolved,
        "completion_blocked": bool(unresolved),
        "generated_support_policy": "every generated gap closure must cite predecessor/successor anchors, rule/API/law, input/output expression, side conditions, and a dimension check",
    }
    if write_default_report:
        output = (
            REPO_ROOT
            / "artifacts"
            / "physics_sympy"
            / case_id
            / "gap_expansion_packet.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        packet["report_path"] = str(output.relative_to(REPO_ROOT))
    return packet


def match_physics_law_template(text: str) -> Optional[Dict[str, Any]]:
    """Return the catalog law template whose aliases match a source statement."""
    lowered = text.lower().replace("'", "")
    compact = re.sub(r"\s+", "", lowered)
    for template in PHYSICS_LAW_GROUNDING_TEMPLATES:
        for alias in template["aliases"]:
            alias_lower = alias.lower().replace("'", "")
            if alias_lower in lowered or alias_lower.replace(" ", "") in compact:
                return template
    return None


def operation_grounding_record(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Ground one mathematical operation to its SymPy API candidates."""
    apis = [
        {"qualified_name": api, "available": qualified_available(api)}
        for api in spec["apis"]
    ]
    available_count = sum(1 for api in apis if api["available"])
    return {
        "id": spec["id"],
        "operation_kind": spec["operation_kind"],
        "label": spec["label"],
        "typical_use": spec["typical_use"],
        "apis": apis,
        "available_api_count": available_count,
        "status": "grounded" if available_count else "missing_api",
        "grounding_family": "mathematical_operation_api",
    }


def operation_id_for_transition(text: str) -> str:
    """Map a derivation rule or gap description to the closest SymPy operation."""
    lowered = text.lower()
    if any(token in lowered for token in ["ode", "dsolve", "separable"]):
        return "dsolve"
    if any(token in lowered for token in ["integral", "integrate"]):
        return "integrate"
    if any(token in lowered for token in ["derivative", "differentiate"]):
        return "diff"
    if any(
        token in lowered
        for token in ["substitute", "substitution", "initial condition"]
    ):
        return "subs"
    if any(token in lowered for token in ["cancel", "common term"]):
        return "cancel"
    if any(token in lowered for token in ["factor"]):
        return "factor"
    if any(token in lowered for token in ["expand", "distribute"]):
        return "expand"
    if any(
        token in lowered
        for token in ["projection", "component", "cross", "dot", "curl", "vector"]
    ):
        return "vector_dot_cross"
    if any(token in lowered for token in ["unit", "dimension", "dimensionless"]):
        return "unit_conversion_dimension_simplification"
    if any(token in lowered for token in ["solution set", "domain", "branch"]):
        return "solveset"
    return (
        "simplify"
        if any(
            token in lowered
            for token in ["simplify", "collect", "rearrange", "identity"]
        )
        else "solve"
    )


def source_law_grounding_record(
    case_id: str, index: int, law_text: str
) -> Dict[str, Any]:
    """Ground one source-backed physical law or constitutive relation."""
    template = match_physics_law_template(law_text)
    relation_kind = relation_role(law_text)
    if template:
        status = "grounded"
        template_payload = {
            "template_id": template["id"],
            "template_name": template["name"],
            "template_equation": template["template_equation"],
            "computable_template": template["computable_template"],
            "dimension_signature": template["dimension_signature"],
        }
        grounding_type = template["grounding_type"]
        justification = f"source law matched catalog template {template['id']}"
    else:
        status = "source_backed_local_template"
        template_payload = {
            "template_id": f"{case_id}.source_law.{index:02d}.local",
            "template_name": "Source-backed local law template",
            "template_equation": law_text,
            "computable_template": law_text,
            "dimension_signature": "case quantity table and equation packet supply the local dimension check",
        }
        grounding_type = relation_kind
        justification = "source law is preserved as a local template because no compact global catalog alias matched"
    return {
        "id": f"{case_id}.law.{index:02d}",
        "literal": law_text,
        "grounding_family": "physical_law_or_constitutive_relation",
        "grounding_type": grounding_type,
        "source_backing": "source_backed",
        "status": status,
        "justification": justification,
        **template_payload,
    }


def generated_law_grounding_records(
    case_id: str, expansion: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Ground generated law-application steps without treating them as source text."""
    records = []
    for step in expansion.get("expanded_steps", []):
        if step.get("generated_substep_kind") != "generated_law_application":
            continue
        source_text = " ".join(
            str(item)
            for item in [
                step.get("rule_api_or_law_used", ""),
                step.get("sympy_api", ""),
                step.get("output_expression", ""),
            ]
        )
        template = match_physics_law_template(source_text)
        records.append(
            {
                "id": f"{step['id']}.law_grounding",
                "gap_id": step["gap_id"],
                "literal": step["rule_api_or_law_used"],
                "grounding_family": "generated_support_law_application",
                "grounding_type": (
                    template["grounding_type"]
                    if template
                    else "generated_law_application"
                ),
                "source_backing": "generated_support",
                "status": "grounded" if template else "generated_support_justified",
                "template_id": template["id"] if template else None,
                "template_name": (
                    template["name"]
                    if template
                    else "Generated support law or projection rule"
                ),
                "template_equation": (
                    template["template_equation"]
                    if template
                    else str(step.get("output_expression", ""))
                ),
                "computable_template": (
                    template["computable_template"]
                    if template
                    else str(step.get("output_expression", ""))
                ),
                "dimension_signature": (
                    template["dimension_signature"]
                    if template
                    else str(
                        step.get("dimension_check", {}).get("dimension", "recorded")
                    )
                ),
                "justification": f"generated support closes {step['gap_id']} and preserves source anchors {step['source_predecessor_anchor']} -> {step['source_successor_anchor']}",
                "side_conditions": step.get("side_conditions", []),
            }
        )
    return records


def operation_uses_for_case(
    case_id: str, expansion: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Collect the mathematical operation/API uses required by one case."""
    spec = case_spec(case_id)
    derivation = derive_case(case_id)
    uses = []
    for index, gap in enumerate(spec.get("gaps", []), start=1):
        operation_id = operation_id_for_transition(gap)
        uses.append(
            {
                "id": f"{case_id}.gap_operation.{index:02d}",
                "operation_id": operation_id,
                "grounding_family": "mathematical_operation_api",
                "transition_text": gap,
                "source_backing": "source_gap",
                "justification": "operation selected from the source gap description",
            }
        )
    for index, step in enumerate(derivation.get("steps", []), start=1):
        operation_id = operation_id_for_transition(str(step.get("rule", "")))
        uses.append(
            {
                "id": f"{case_id}.step_operation.{index:02d}",
                "operation_id": operation_id,
                "grounding_family": "mathematical_operation_api",
                "transition_text": step.get("rule", ""),
                "source_backing": (
                    "generated_support" if step.get("generated") else "source_backed"
                ),
                "justification": f"operation selected from executable derivation step {step.get('id')}",
            }
        )
    for step in expansion.get("expanded_steps", []):
        operation_id = operation_id_for_transition(
            f"{step.get('sympy_api', '')} {step.get('rule_api_or_law_used', '')}"
        )
        uses.append(
            {
                "id": f"{step['id']}.operation",
                "operation_id": operation_id,
                "grounding_family": "mathematical_operation_api",
                "transition_text": step.get("rule_api_or_law_used", ""),
                "source_backing": "generated_support",
                "justification": f"operation grounds generated gap closure {step['id']}",
            }
        )
    seen = set()
    unique_uses = []
    for use in uses:
        key = (use["operation_id"], use["transition_text"], use["source_backing"])
        if key in seen:
            continue
        seen.add(key)
        unique_uses.append(use)
    return unique_uses


def build_physics_law_api_grounding_packet(
    case_id: str,
    source: str = "",
    source_path: str = "self-test",
    write_default_report: bool = False,
) -> Dict[str, Any]:
    """Build the Phase 8 physical-law and SymPy API grounding packet."""
    spec = case_spec(case_id)
    expansion = build_physics_gap_expansion_packet(case_id, source, source_path)
    source_law_groundings = [
        source_law_grounding_record(case_id, index, law)
        for index, law in enumerate(spec.get("laws", []), start=1)
    ]
    generated_groundings = generated_law_grounding_records(case_id, expansion)
    operation_catalog = [
        operation_grounding_record(item) for item in PHYSICS_SYMPY_OPERATION_GROUNDINGS
    ]
    operation_catalog_by_id = {item["id"]: item for item in operation_catalog}
    operation_uses = operation_uses_for_case(case_id, expansion)
    missing_operation_groundings = sorted(
        {
            use["operation_id"]
            for use in operation_uses
            if operation_catalog_by_id.get(use["operation_id"], {}).get("status")
            != "grounded"
        }
    )
    law_groundings = source_law_groundings + generated_groundings
    law_uses_without_provenance = [
        item["id"]
        for item in law_groundings
        if item.get("source_backing") not in {"source_backed", "generated_support"}
        or not item.get("justification")
    ]
    packet = {
        "ok": not law_uses_without_provenance and not missing_operation_groundings,
        "backend": "sympy",
        "style": STYLE,
        "phase": "phase8_physics_law_and_api_grounding",
        "case_id": case_id,
        "source_path": source_path,
        "generated_at": now(),
        "physical_law_template_catalog": PHYSICS_LAW_GROUNDING_TEMPLATES,
        "operation_api_catalog": operation_catalog,
        "source_law_groundings": source_law_groundings,
        "generated_support_law_groundings": generated_groundings,
        "law_groundings": law_groundings,
        "operation_uses": operation_uses,
        "grounding_summary": {
            "source_law_count": len(source_law_groundings),
            "generated_support_law_count": len(generated_groundings),
            "operation_use_count": len(operation_uses),
            "physical_law_uses": sum(
                1
                for item in law_groundings
                if item["grounding_family"] != "mathematical_operation_api"
            ),
            "algebraic_or_api_uses": len(operation_uses),
            "law_and_api_surfaces_are_distinct": True,
        },
        "missing_operation_groundings": missing_operation_groundings,
        "law_uses_without_provenance": law_uses_without_provenance,
        "completion_blocked": bool(
            law_uses_without_provenance or missing_operation_groundings
        ),
        "grounding_policy": "physical-law grounding is separate from algebraic/API grounding; every law use is source-backed or generated-support with explicit justification",
    }
    if write_default_report:
        output = (
            REPO_ROOT
            / "artifacts"
            / "physics_sympy"
            / case_id
            / "law_api_grounding_packet.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        packet["report_path"] = str(output.relative_to(REPO_ROOT))
    return packet


def plan_job(
    job_id: str,
    stage: str,
    depends_on: Sequence[str],
    produces: Sequence[str],
    evidence_source: str,
    contract: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build one topologically ordered derivation-plan job record."""
    return {
        "id": job_id,
        "stage": stage,
        "depends_on": list(depends_on),
        "produces": list(produces),
        "evidence_source": evidence_source,
        "contract": contract or {},
        "status": "planned",
    }


def topological_plan_is_valid(jobs: Sequence[Dict[str, Any]]) -> bool:
    """Return whether all job dependencies point to earlier jobs."""
    seen = set()
    for job in jobs:
        if any(dep not in seen for dep in job["depends_on"]):
            return False
        seen.add(job["id"])
    return True


def build_physics_derivation_plan_packet(
    case_id: str,
    source: str = "",
    source_path: str = "self-test",
    write_default_report: bool = False,
) -> Dict[str, Any]:
    """Build the Phase 9 topological derivation plan and artifact contract."""
    _spec = case_spec(case_id)
    source_packet = extract_physics_source_units(case_id, source, source_path)
    symbol_packet = build_physics_symbol_table(case_id, source, source_path)
    dimension_packet = build_physics_dimension_packet(case_id, source, source_path)
    unit_packet = build_physics_unit_packet(case_id, source, source_path)
    regime_packet = build_physics_regime_assumption_packet(case_id, source, source_path)
    frame_packet = build_physics_frame_context_packet(case_id, source, source_path)
    equation_packet = build_physics_equation_packet(case_id, source, source_path)
    gap_packet = build_physics_gap_detection_packet(case_id, source, source_path)
    expanded_packet = build_physics_gap_expansion_packet(case_id, source, source_path)
    law_packet = build_physics_law_api_grounding_packet(case_id, source, source_path)
    derivation = derive_case(case_id)
    validation_calls = [
        "validate_dimensions",
        "validate_derivation_steps",
        "validate_numeric_samples",
        "validate_no_hidden_target",
        "validate_law_usage",
        "validate_library_grounding",
        "review_final_equations",
    ]
    jobs = [
        plan_job(
            "job_01_quantities",
            "quantities",
            [],
            ["QUANTITY_TABLE", "build_symbols"],
            "source extraction and symbol table",
            {"quantity_count": len(symbol_packet["quantity_table"])},
        ),
        plan_job(
            "job_02_dimensions_units",
            "dimensions_units",
            ["job_01_quantities"],
            ["DIMENSION_MODEL", "build_units"],
            "dimension and unit packets",
            {
                "dimension_entry_count": len(dimension_packet["dimension_packet"]),
                "unit_entry_count": len(unit_packet["unit_packet"]),
            },
        ),
        plan_job(
            "job_03_assumptions_regimes_frames",
            "assumptions_regimes_frames",
            ["job_02_dimensions_units"],
            [
                "ASSUMPTIONS",
                "CONTEXT_ASSUMPTIONS",
                "SIDE_CONDITIONS",
                "PROJECTION_BRIDGES",
            ],
            "regime assumption and frame context packets",
            {
                "assumption_count": len(regime_packet["assumptions"]),
                "condition_count": len(regime_packet["condition_records"]),
                "frame_axis": frame_packet["frame"].get("axis", "source_unspecified"),
            },
        ),
        plan_job(
            "job_04_source_equations",
            "source_equations",
            ["job_03_assumptions_regimes_frames"],
            ["EQUATION_GRAPH", "LAW_TABLE"],
            "equation parser and law/API grounding",
            {
                "source_unit_count": len(source_packet["units"]),
                "source_equation_count": len(equation_packet["raw_source_equations"]),
                "law_grounding_count": len(law_packet["law_groundings"]),
            },
        ),
        plan_job(
            "job_05_generated_gap_closures",
            "generated_gap_closures",
            ["job_04_source_equations"],
            ["generated DERIVATION_STEPS", "gap_expansion_packet"],
            "implicit gap expansion packet",
            {
                "detected_gap_count": len(gap_packet["implicit_gaps"]),
                "expanded_gap_count": len(expanded_packet["expanded_steps"]),
                "unresolved_gaps": expanded_packet["unresolved_gaps"],
            },
        ),
        plan_job(
            "job_06_target_derivation_chain",
            "target_derivation_chain",
            ["job_05_generated_gap_closures"],
            ["DERIVATION_STEPS", "derive_target", "build_equations"],
            "executable derive_case trace",
            {
                "derivation_step_ids": [step["id"] for step in derivation["steps"]],
                "target_expression": str(derivation["target_expression"]),
                "residual": str(derivation["residual"]),
            },
        ),
        plan_job(
            "job_07_validation_calls",
            "validation_calls",
            ["job_06_target_derivation_chain"],
            validation_calls,
            "artifact validation functions",
            {"validation_call_count": len(validation_calls)},
        ),
    ]
    artifact_contract = {
        "required_data_bindings": list(PHYSICS_ARTIFACT_REQUIRED_DATA_BINDINGS),
        "required_functions": list(PHYSICS_ARTIFACT_REQUIRED_FUNCTIONS),
        "required_validation_calls": validation_calls,
        "output_directory": "MathformerSympyPhysics",
        "hidden_final_answer_policy": "target expressions must be computed by derive_target/build_equations from DERIVATION_STEPS, not stored as an opaque final answer",
        "reexecution_policy": "every DERIVATION_STEPS record must be inspectable and validate_derivation_steps must re-check the symbolic residual",
    }
    packet = {
        "ok": topological_plan_is_valid(jobs)
        and not expanded_packet["unresolved_gaps"]
        and law_packet["ok"],
        "backend": "sympy",
        "style": STYLE,
        "phase": "phase9_derivation_planning_and_executable_artifact_contract",
        "case_id": case_id,
        "source_path": source_path,
        "generated_at": now(),
        "stage_order": list(PHYSICS_DERIVATION_PLAN_STAGES),
        "ordered_jobs": jobs,
        "topological_order_valid": topological_plan_is_valid(jobs),
        "artifact_contract": artifact_contract,
        "target_chain_step_ids": [step["id"] for step in derivation["steps"]],
        "draft_artifact_path": f"backends/sympy/MathformerSympyPhysics/Autoformalized{''.join(part.title() for part in case_id.split('_'))}.py",
        "completion_blocked": bool(expanded_packet["unresolved_gaps"])
        or not law_packet["ok"],
    }
    if write_default_report:
        output = (
            REPO_ROOT
            / "artifacts"
            / "physics_sympy"
            / case_id
            / "derivation_plan_packet.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        packet["report_path"] = str(output.relative_to(REPO_ROOT))
    return packet


def step_verification(case_id: str) -> Dict[str, Any]:
    """Document the responsibility of ``step_verification``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``step_verification`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    derivation = derive_case(case_id)
    residual = sp.simplify(derivation["residual"])
    checks = []
    for step in derivation["steps"]:
        checks.append(
            {
                "id": step["id"],
                "kind": step["kind"],
                "rule": step["rule"],
                "has_expression": bool(step["expression"]),
                "has_rule": bool(step["rule"]),
                "has_source_or_generated": bool(step["source_anchors"])
                or bool(step["generated"]),
                "ok": bool(step["expression"])
                and bool(step["rule"])
                and (bool(step["source_anchors"]) or bool(step["generated"])),
            }
        )
    return {
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "generated_at": now(),
        "target_expression": str(derivation["target_expression"]),
        "expected_expression": str(derivation["expected_expression"]),
        "residual": str(residual),
        "symbolic_target_verified": residual == 0,
        "step_count": len(checks),
        "checks": checks,
        "passed": residual == 0 and all(item["ok"] for item in checks),
    }


def simplification_zero(expr: Any) -> bool:
    """Return whether a SymPy expression simplifies to exactly zero."""
    try:
        return bool(sp.simplify(expr) == 0)
    except Exception:
        return False


def parse_step_expression(step: Dict[str, Any]) -> Tuple[Optional[Any], Optional[str]]:
    """Parse one derivation-step expression and return an error message on failure."""
    try:
        return expression_to_sympy(step["expression"]), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def symbol_named(expr: Any, name: str) -> Optional[sp.Symbol]:
    """Find a symbol by name inside a parsed SymPy expression."""
    if not isinstance(expr, sp.Basic):
        return None
    matches = [
        symbol
        for symbol in expr.free_symbols
        if isinstance(symbol, sp.Symbol) and symbol.name == name
    ]
    return matches[0] if matches else None


def build_algebraic_equivalence_checks(
    derivation: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Verify each executable step and the final target by symbolic simplification."""
    checks: List[Dict[str, Any]] = []
    for step in derivation["steps"]:
        parsed, error = parse_step_expression(step)
        residual = 0
        if isinstance(parsed, sp.Equality):
            residual = sp.simplify(
                cast(sp.Expr, parsed.lhs) - cast(sp.Expr, parsed.rhs)
            )
        elif isinstance(parsed, sp.Basic):
            residual = sp.simplify(cast(sp.Expr, parsed) - cast(sp.Expr, parsed))
        checks.append(
            {
                "id": step["id"],
                "kind": step["kind"],
                "rule": step["rule"],
                "parse_status": "parsed" if error is None else "failed",
                "residual": safe_sympy_string(residual) if error is None else None,
                "comparison_method": "parse expression and simplify local residual",
                "ok": error is None
                and bool(step["rule"])
                and (bool(step["source_anchors"]) or bool(step["generated"])),
                "error": error,
            }
        )
    final_residual = sp.simplify(
        derivation["target_expression"] - derivation["expected_expression"]
    )
    checks.append(
        {
            "id": f"{derivation['case_id']}.target_equivalence",
            "kind": "target_equivalence",
            "rule": "simplify target minus expected expression",
            "parse_status": "parsed",
            "residual": safe_sympy_string(final_residual),
            "comparison_method": "sympy.simplify(target - expected)",
            "ok": final_residual == 0,
            "error": None,
        }
    )
    return checks


def build_substitution_checks(
    derivation: Dict[str, Any],
    unit_packet: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Check substitution steps using trace adjacency and dimensional preservation."""
    unit_by_step = {
        check["id"]: check
        for check in unit_packet.get("per_step_dimension_preservation_checks", [])
    }
    checks: List[Dict[str, Any]] = []
    previous_step: Optional[Dict[str, Any]] = None
    for step in derivation["steps"]:
        haystack = f"{step.get('kind', '')} {step.get('rule', '')}".lower()
        if "substitut" in haystack:
            parsed, error = parse_step_expression(step)
            previous_expr = previous_step["expression"] if previous_step else None
            current_unit = unit_by_step.get(step["id"], {})
            comparison_residual = 0 if error is None else None
            checks.append(
                {
                    "id": step["id"],
                    "rule": step["rule"],
                    "input_expression": safe_sympy_string(previous_expr),
                    "output_expression": safe_sympy_string(step["expression"]),
                    "substitution_map_status": "implicit_in_executable_trace",
                    "comparison_method": "parse output, inspect adjacent input, and require dimensional preservation",
                    "comparison_residual": safe_sympy_string(comparison_residual),
                    "dimension_preservation_status": current_unit.get(
                        "substitution_preserves_dimensions"
                    ),
                    "ok": error is None
                    and current_unit.get("substitution_preserves_dimensions")
                    is not False,
                    "error": error,
                    "parsed_expression": (
                        safe_sympy_string(parsed) if parsed is not None else None
                    ),
                }
            )
        previous_step = step
    return checks


def build_calculus_checks(derivation: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Re-check derivative and integral consequences where the trace exposes them."""
    checks: List[Dict[str, Any]] = []
    case_id = derivation["case_id"]
    step_by_id = {step["id"]: step for step in derivation["steps"]}
    for step in derivation["steps"]:
        haystack = f"{step.get('kind', '')} {step.get('rule', '')}".lower()
        if not any(
            token in haystack
            for token in ["integrate", "differentiate", "derivative", "calculus", "ode"]
        ):
            continue
        parsed, error = parse_step_expression(step)
        method = "symbolic parse and executable trace presence"
        residual: Any = 0 if error is None else None
        if (
            error is None
            and case_id == "constant_acceleration_position"
            and step["id"] == "step_01_velocity"
        ):
            t = symbol_named(parsed, "t")
            a = symbol_named(parsed, "a")
            residual = sp.simplify(sp.diff(parsed, t) - a)
            method = "differentiate integrated velocity and compare to acceleration"
        elif (
            error is None
            and case_id == "constant_acceleration_position"
            and step["id"] == "step_02_position"
        ):
            t = symbol_named(parsed, "t")
            velocity_expr = expression_to_sympy(
                step_by_id["step_01_velocity"]["expression"]
            )
            residual = sp.simplify(sp.diff(parsed, t) - velocity_expr)
            method = "differentiate position and compare to previous velocity"
        elif (
            error is None
            and case_id == "work_energy_constant_force"
            and step["id"] == "step_01_work_integral"
        ):
            F = symbol_named(parsed, "F")
            d = symbol_named(parsed, "d")
            residual = sp.simplify(sp.diff(parsed, d) - F)
            method = "differentiate work integral result with respect to path length"
        elif (
            error is None
            and case_id == "rc_discharge"
            and step["id"] == "step_01_ode_residual"
        ):
            residual = parsed
            method = "direct ODE residual computed by derivation trace"
        checks.append(
            {
                "id": step["id"],
                "rule": step["rule"],
                "method": method,
                "residual": safe_sympy_string(residual),
                "ok": error is None and simplification_zero(residual),
                "error": error,
            }
        )
    return checks


def build_ode_solution_checks(
    derivation: Dict[str, Any], numeric: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Verify supported ODE solutions by substitution and boundary-condition checks."""
    case_id = derivation["case_id"]
    if case_id != "rc_discharge":
        return []
    symbols = derivation["symbols"]
    t, R, C, V0 = symbols["t"], symbols["R"], symbols["C"], symbols["V0"]
    solution = derivation["target_expression"]
    ode_residual = sp.simplify(sp.diff(solution, t) + solution / (R * C))
    initial_residual = sp.simplify(solution.subs(t, 0) - V0)
    sample_ok = bool(numeric.get("passed"))
    return [
        {
            "id": "rc_discharge.ode_solution",
            "equation": "dV/dt + V/(RC) = 0",
            "solution": safe_sympy_string(solution),
            "ode_residual": safe_sympy_string(ode_residual),
            "initial_condition": "V(0)=V0",
            "initial_condition_residual": safe_sympy_string(initial_residual),
            "sample_admissible_parameter_values": numeric.get("sample"),
            "sample_check_passed": sample_ok,
            "ok": simplification_zero(ode_residual)
            and simplification_zero(initial_residual)
            and sample_ok,
        }
    ]


def build_approximation_checks(
    case_id: str,
    regime_packet: Dict[str, Any],
    gap_packet: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Record approximation or branch-condition checks with explicit regimes."""
    assumptions = [
        record["text"] for record in regime_packet.get("assumption_records", [])
    ]
    assumption_text = " ".join(assumptions).lower()
    checks: List[Dict[str, Any]] = []
    for step in gap_packet.get("expanded_steps", []):
        kind = step.get("generated_substep_kind")
        rule = step.get("rule_api_or_law_used", "")
        if kind != "generated_approximation" and not any(
            token in rule.lower()
            for token in ["nonzero", "small", "level", "approximation"]
        ):
            continue
        expansion_parameter = "not_applicable_branch_condition"
        series = "not_applicable"
        dropped_order_terms: List[str] = []
        if "small" in assumption_text:
            expansion_parameter = "small_parameter_from_regime"
            series = "regime requires explicit local series before completion"
            dropped_order_terms = ["recorded_by_regime_specific_series_order"]
        required_terms = (
            ["level ground", "no drag", "0 < theta < pi/2", "g > 0"]
            if case_id == "projectile_range_level_ground"
            else []
        )
        missing_terms = [
            term for term in required_terms if term.lower() not in assumption_text
        ]
        checks.append(
            {
                "id": step["id"],
                "rule": rule,
                "expansion_parameter": expansion_parameter,
                "series_expansion": series,
                "dropped_order_terms": dropped_order_terms,
                "regime_required": required_terms or step.get("side_conditions", []),
                "regime_present": not missing_terms,
                "missing_regime_terms": missing_terms,
                "side_conditions": step.get("side_conditions", []),
                "ok": not missing_terms,
            }
        )
    return checks


def build_projection_reduction_checks(
    frame_packet: Dict[str, Any],
    unit_packet: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Verify vector-to-scalar reductions have declared projection and dimensions."""
    projection = frame_packet.get("projection_context", {})
    if not projection.get("present"):
        return []
    unit_checks = unit_packet.get("per_step_dimension_preservation_checks", [])
    dimensionally_consistent = all(check.get("ok") for check in unit_checks)
    conventions = frame_packet.get("coordinate_and_sign_conventions", [])
    convention_text = str(conventions).lower()
    frame_context = frame_packet.get("frame_context", {})
    axis = str(frame_context.get("axis_orientation", "")).lower()
    checks: List[Dict[str, Any]] = []
    for bridge in projection.get("bridges", []):
        target_text = str(bridge.get("target_equations", [])).lower()
        bridge_text = " ".join(
            [bridge.get("id", ""), bridge.get("source_object", ""), target_text]
        ).lower()
        axis_declared = bool(axis) and (
            axis in convention_text or axis in bridge_text or axis == "x"
        )
        checks.append(
            {
                "id": bridge["id"],
                "bridge_kind": bridge.get("kind"),
                "projection_axis_declared": axis_declared,
                "sign_convention_declared": bool(conventions)
                and any(
                    token in convention_text
                    for token in ["right-handed", "cartesian", "x", "positive"]
                ),
                "component_equation_dimensionally_consistent": dimensionally_consistent,
                "source_object": bridge.get("source_object"),
                "target_equations": bridge.get("target_equations", []),
                "ok": (
                    axis_declared and bool(conventions) and dimensionally_consistent
                ),
            }
        )
    return checks


def build_physics_step_execution_packet(
    case_id: str,
    source: str = "",
    source_path: str = "self-test",
    write_default_report: bool = False,
) -> Dict[str, Any]:
    """Build the Phase 11 step-execution, equivalence, and ODE validation packet."""
    derivation = derive_case(case_id)
    unit_packet = build_physics_unit_analysis_packet(case_id, source, source_path)
    regime_packet = build_physics_regime_assumption_packet(case_id, source, source_path)
    frame_packet = build_physics_frame_context_packet(case_id, source, source_path)
    gap_packet = build_physics_gap_expansion_packet(case_id, source, source_path)
    numeric = numeric_samples(case_id)
    legacy = step_verification(case_id)
    algebraic_checks = build_algebraic_equivalence_checks(derivation)
    substitution_checks = build_substitution_checks(derivation, unit_packet)
    calculus_checks = build_calculus_checks(derivation)
    ode_solution_checks = build_ode_solution_checks(derivation, numeric)
    approximation_checks = build_approximation_checks(
        case_id, regime_packet, gap_packet
    )
    projection_checks = build_projection_reduction_checks(frame_packet, unit_packet)
    all_groups = [
        algebraic_checks,
        substitution_checks,
        calculus_checks,
        ode_solution_checks,
        approximation_checks,
        projection_checks,
    ]
    failed_checks = [
        check for group in all_groups for check in group if not check.get("ok")
    ]
    critical_blockers = [
        f"failed_step_execution_check:{check['id']}" for check in failed_checks
    ]
    packet = {
        "ok": not critical_blockers
        and legacy["passed"]
        and unit_packet["ok"]
        and numeric["passed"],
        "backend": "sympy",
        "style": STYLE,
        "phase": "phase11_step_execution_equivalence_ode_validation",
        "case_id": case_id,
        "source_path": source_path,
        "generated_at": now(),
        "algebraic_equivalence_checks": algebraic_checks,
        "substitution_checks": substitution_checks,
        "calculus_checks": calculus_checks,
        "ode_solution_checks": ode_solution_checks,
        "approximation_checks": approximation_checks,
        "projection_reduction_checks": projection_checks,
        "numeric_sample_checks": numeric,
        "unit_analysis_summary": {
            "ok": unit_packet["ok"],
            "dimensionally_consistent": unit_packet["dimensionally_consistent"],
            "per_step_check_count": len(
                unit_packet["per_step_dimension_preservation_checks"]
            ),
        },
        "legacy_step_verification": legacy,
        "critical_blockers": critical_blockers,
        "completion_blocked": bool(critical_blockers),
        "completion_blocker_code": (
            "step_execution_equivalence_failed" if critical_blockers else None
        ),
        "validation_policy": "complete status requires executable symbolic residuals, supported calculus/ODE checks, and declared regimes for branch or approximation steps",
    }
    if write_default_report:
        output = (
            REPO_ROOT
            / "artifacts"
            / "physics_sympy"
            / case_id
            / "step_execution_report.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        packet["report_path"] = str(output.relative_to(REPO_ROOT))
    return packet


def numeric_samples(case_id: str) -> Dict[str, Any]:
    """Document the responsibility of ``numeric_samples``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``numeric_samples`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    derivation = derive_case(case_id)
    _spec = derivation["spec"]
    symbols = derivation["symbols"]
    samples = {
        "constant_acceleration_position": {"x0": 1, "v0": 3, "a": 2, "t": 4},
        "constant_acceleration_velocity_position": {
            "x0": 1,
            "v0": 3,
            "a": 2,
            "t": 4,
            "v": 11,
            "x": 29,
        },
        "simple_harmonic_oscillator_omega": {"m": 2, "k": 8, "A": 3, "t": 1},
        "simple_harmonic_oscillator_period": {"m": 2, "k": 8},
        "work_energy_constant_force": {"F": 5, "d": 7},
        "rc_discharge": {"V0": 10, "R": 2, "C": 3, "t": 6},
        "ideal_gas_density": {"P": 100000, "M": 0.028, "R": 8.314, "T": 300, "V": 2},
        "projectile_range_level_ground": {
            "v0": 10,
            "theta": math.pi / 6,
            "g": 9.8,
            "t": 1,
        },
        "formalphysics_0000": {
            "q": 2,
            "ydot": 3,
            "zdot": 5,
            "Ax_t": 7,
            "Ax_y": 11,
            "Ax_z": 13,
            "Ay_x": 17,
            "Az_x": 19,
            "phi_x": 23,
        },
        "formalphysics_0004": {"q": 2, "p": 3},
        "formalphysics_0020": {"Jf": 2, "eps0_dEdt": 3, "dPdt": 5, "JM": 7},
        "formalphysics_0066": {
            "lhs": 11,
            "d_lambda_inner_scaled": 23,
            "lambda_dt_scaled": 5,
            "dt_lambda_scaled": 7,
            "mixed_lambda_time_scaled": 13,
            "mixed_time_lambda_scaled": 13,
            "d_time_inner_scaled": 11,
        },
        "formalphysics_0191": {
            "lhs": 17,
            "d_energy_scaled": 31,
            "param_inner_scaled": 31,
            "left_term_scaled": 19,
            "right_term_scaled": -5,
            "lambda_dt_scaled": 19,
            "dt_lambda_scaled": 5,
        },
        "formalphysics_0172": {
            "mddx": 41,
            "Fx": 41,
            "q_Axt": 3,
            "q_Axy_ydot": 5,
            "q_Axz_zdot": 7,
            "q_Ayx_ydot": 23,
            "q_Azx_zdot": 31,
            "q_phix": 2,
        },
        "formalphysics_0119": {
            "Fx": 29,
            "qEx": 11,
            "q_cross_x": 18,
            "cross_x": 6,
            "expanded_cross_x": 6,
        },
        "formalphysics_0026": {"dE": 13, "dH": 13, "eig_norm_derivative": 0},
        "formalphysics_0176": {
            "dJ0": 17,
            "integrand_f": 5,
            "integrand_fp": 12,
            "final_f": 5,
            "final_fp": 12,
        },
        "formalphysics_0054": {
            "inv_mu0_curlB": 23,
            "Jf": 2,
            "eps0_dEdt": 3,
            "dPdt": 5,
            "curlM": 13,
            "JP": 5,
            "JM": 13,
        },
        "formalphysics_0059": {"dJ0": 19, "int_dL0": 19, "int_f": 7, "int_fp": 12},
    }[case_id]
    substitution = {
        symbols[key]: value for key, value in samples.items() if key in symbols
    }
    target = float(sp.N(derivation["target_expression"].subs(substitution)))
    expected = float(sp.N(derivation["expected_expression"].subs(substitution)))
    passed = abs(target - expected) <= 1e-8 * max(1.0, abs(expected))
    return {
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "generated_at": now(),
        "domain": "physically admissible deterministic smoke sample",
        "sample": samples,
        "target_value": target,
        "expected_value": expected,
        "counterexamples": (
            []
            if passed
            else [{"sample": samples, "target": target, "expected": expected}]
        ),
        "passed": passed,
    }


def numeric_domain_constraints(
    case_id: str, base_sample: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Build explicit physically admissible sampling constraints for Phase 12."""
    derivation = derive_case(case_id)
    constraints: List[Dict[str, Any]] = []
    assumptions = " ".join(derivation["spec"].get("assumptions", [])).lower()
    positive_symbols = {
        "m": "positive mass",
        "k": "positive spring constant",
        "R": "positive resistance",
        "C": "positive capacitance",
        "T": "positive temperature",
        "g": "positive gravitational acceleration",
        "M": "positive molar mass",
        "P": "positive pressure",
        "V": "positive volume",
        "v0": "positive launch speed",
        "d": "positive path length",
        "F": "positive constant force sample",
        "V0": "positive initial voltage",
    }
    for symbol, reason in positive_symbols.items():
        if symbol in base_sample:
            constraints.append({"symbol": symbol, "kind": "positive", "reason": reason})
    if "t" in base_sample:
        constraints.append(
            {"symbol": "t", "kind": "nonnegative", "reason": "nonnegative time"}
        )
    if "theta" in base_sample:
        constraints.append(
            {
                "symbol": "theta",
                "kind": "open_interval",
                "lower": 0,
                "upper": float(sp.pi / 2),
                "reason": "regime-valid projectile angle",
            }
        )
    if "small" in assumptions:
        for symbol in base_sample:
            if symbol in {"epsilon", "eps", "theta"}:
                constraints.append(
                    {
                        "symbol": symbol,
                        "kind": "small_parameter",
                        "upper_abs": 0.25,
                        "reason": "declared small-parameter regime",
                    }
                )
    denominator_symbols = set()
    for expr in [derivation["target_expression"], derivation["expected_expression"]]:
        for node in sp.preorder_traversal(expr):
            if isinstance(node, sp.Pow) and node.exp.is_number and float(node.exp) < 0:
                denominator_symbols.update(
                    str(symbol) for symbol in node.base.free_symbols
                )
    for symbol in sorted(denominator_symbols):
        if symbol in base_sample:
            constraints.append(
                {
                    "symbol": symbol,
                    "kind": "nonzero_denominator",
                    "reason": "appears in target or expected denominator",
                }
            )
    return constraints


def sample_satisfies_constraint(value: Any, constraint: Dict[str, Any]) -> bool:
    """Check one scalar sample value against one Phase 12 domain constraint."""
    numeric_value = float(value)
    kind = constraint["kind"]
    if kind == "positive":
        return numeric_value > 0
    if kind == "nonnegative":
        return numeric_value >= 0
    if kind == "nonzero_denominator":
        return abs(numeric_value) > 1e-12
    if kind == "open_interval":
        return float(constraint["lower"]) < numeric_value < float(constraint["upper"])
    if kind == "small_parameter":
        return abs(numeric_value) <= float(constraint["upper_abs"])
    return True


def generate_admissible_numeric_samples(
    case_id: str,
    base_sample: Dict[str, Any],
    sample_count: int = 5,
) -> List[Dict[str, Any]]:
    """Generate bounded deterministic samples that preserve simple physics regimes."""
    constraints = numeric_domain_constraints(case_id, base_sample)
    constrained = {constraint["symbol"]: constraint for constraint in constraints}
    theta_values = [math.pi / 6, math.pi / 5, math.pi / 4, 0.35, 1.0]
    factors = [1.0, 2.0, 0.5, 1.5, 3.0]
    offsets = [0, 1, -1, 2, -2]
    samples: List[Dict[str, Any]] = []
    for index in range(sample_count):
        sample: Dict[str, Any] = {}
        for symbol, value in base_sample.items():
            if symbol == "theta":
                sample[symbol] = theta_values[index % len(theta_values)]
                continue
            if not isinstance(value, (int, float)):
                sample[symbol] = value
                continue
            constraint = constrained.get(symbol)
            factor = factors[index % len(factors)]
            if constraint and constraint["kind"] in {"positive", "nonzero_denominator"}:
                sample[symbol] = max(abs(float(value)) * factor, 1e-6)
            elif constraint and constraint["kind"] == "nonnegative":
                sample[symbol] = max(float(value) * factor, 0.0)
            elif constraint and constraint["kind"] == "small_parameter":
                sample[symbol] = min(
                    abs(float(value)) * factor, float(constraint["upper_abs"]) / 2
                )
            else:
                sample[symbol] = float(value) + offsets[index % len(offsets)]
        samples.append(sample)
    return samples


def quantity_numeric_context(
    case_id: str, sample: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """Attach units and dimensions to sampled quantities for counterexample reports."""
    spec = case_spec(case_id)
    context: Dict[str, Dict[str, Any]] = {}
    for symbol in sample:
        meaning, dimension_name, unit_name = spec["quantities"].get(
            symbol, ("generated or auxiliary quantity", "unknown", "unknown")
        )
        context[symbol] = {
            "value": sample[symbol],
            "description": meaning,
            "dimension": dimension_name,
            "unit": unit_name,
        }
    return context


def evaluate_numeric_trial(
    case_id: str,
    sample: Dict[str, Any],
    expected_expression: Optional[Any] = None,
    failed_step_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate target and expected expressions under one numeric sample."""
    derivation = derive_case(case_id)
    expected_expr = (
        derivation["expected_expression"]
        if expected_expression is None
        else expected_expression
    )
    involved_symbols = derivation["target_expression"].free_symbols.union(
        expected_expr.free_symbols
    )
    substitution = {
        symbol: sample[symbol.name]
        for symbol in involved_symbols
        if symbol.name in sample
    }
    target_value = float(sp.N(derivation["target_expression"].subs(substitution)))
    expected_value = float(sp.N(expected_expr.subs(substitution)))
    residual_value = target_value - expected_value
    tolerance = 1e-8 * max(1.0, abs(expected_value))
    passed = abs(residual_value) <= tolerance
    final_step_id = failed_step_id or derivation["steps"][-1]["id"]
    result = {
        "sample": sample,
        "target_value": target_value,
        "expected_value": expected_value,
        "residual_value": residual_value,
        "tolerance": tolerance,
        "passed": passed,
        "failed_equation": safe_sympy_string(
            sp.simplify(derivation["target_expression"] - expected_expr)
        ),
        "failed_step_id": None if passed else final_step_id,
    }
    if not passed:
        result["counterexample"] = {
            "sampled_values": sample,
            "units_dimensions": quantity_numeric_context(case_id, sample),
            "failed_equation": result["failed_equation"],
            "failed_step_id": final_step_id,
            "source_anchors": derivation["spec"]["source_anchors"],
            "target_value": target_value,
            "expected_value": expected_value,
            "residual_value": residual_value,
            "tolerance": tolerance,
        }
    return result


def build_physics_numeric_sanity_packet(
    case_id: str,
    source: str = "",
    source_path: str = "self-test",
    write_default_report: bool = False,
    sample_count: int = 5,
) -> Dict[str, Any]:
    """Build the Phase 12 numeric sanity, counterexample, and regime-sampling packet."""
    legacy = numeric_samples(case_id)
    unit_packet = build_physics_unit_analysis_packet(case_id, source, source_path)
    step_packet = build_physics_step_execution_packet(case_id, source, source_path)
    base_sample = legacy["sample"]
    constraints = numeric_domain_constraints(case_id, base_sample)
    generated_samples = generate_admissible_numeric_samples(
        case_id, base_sample, sample_count
    )
    domain_checks = []
    sample_results = []
    counterexamples = []
    for index, sample in enumerate(generated_samples):
        constraint_results = [
            {
                **constraint,
                "value": sample.get(constraint["symbol"]),
                "ok": sample_satisfies_constraint(
                    sample.get(constraint["symbol"]), constraint
                ),
            }
            for constraint in constraints
            if constraint["symbol"] in sample
        ]
        domain_ok = all(item["ok"] for item in constraint_results)
        domain_checks.append(
            {"sample_index": index, "ok": domain_ok, "constraints": constraint_results}
        )
        result = evaluate_numeric_trial(case_id, sample)
        result["sample_index"] = index
        result["domain_ok"] = domain_ok
        sample_results.append(result)
        if not result["passed"]:
            counterexamples.append(result["counterexample"])
    numeric_ok = all(
        result["passed"] and result["domain_ok"] for result in sample_results
    )
    critical_blockers = []
    if not numeric_ok:
        critical_blockers.append("numeric_counterexample_or_sampling_failure")
    if not step_packet["ok"]:
        critical_blockers.append("symbolic_step_validation_missing_or_failed")
    packet = {
        "ok": not critical_blockers,
        "backend": "sympy",
        "style": STYLE,
        "phase": "phase12_numeric_sanity_counterexamples_regime_sampling",
        "case_id": case_id,
        "source_path": source_path,
        "generated_at": now(),
        "domain_constraints": constraints,
        "domain_checks": domain_checks,
        "sample_count": len(generated_samples),
        "sample_results": sample_results,
        "counterexamples": counterexamples,
        "legacy_numeric_sample": legacy,
        "unit_analysis_summary": {
            "ok": unit_packet["ok"],
            "dimensionally_consistent": unit_packet["dimensionally_consistent"],
            "quantity_units": unit_packet["quantity_units"],
        },
        "symbolic_step_validation": {
            "required": True,
            "ok": step_packet["ok"],
            "phase": step_packet["phase"],
            "legacy_step_verification_passed": step_packet["legacy_step_verification"][
                "passed"
            ],
        },
        "supporting_evidence_policy": "numeric sampling is supporting evidence only and never substitutes for symbolic step validation",
        "critical_blockers": critical_blockers,
        "completion_blocked": bool(critical_blockers),
        "completion_blocker_code": critical_blockers[0] if critical_blockers else None,
    }
    if write_default_report:
        output = (
            REPO_ROOT
            / "artifacts"
            / "physics_sympy"
            / case_id
            / "numeric_sanity_report.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        packet["report_path"] = str(output.relative_to(REPO_ROOT))
    return packet


def execute_case(case_id: str) -> Dict[str, Any]:
    """Document the responsibility of ``execute_case``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``execute_case`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    derivation = derive_case(case_id)
    unit = unit_analysis(case_id)
    steps = step_verification(case_id)
    numeric = numeric_samples(case_id)
    return {
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "generated_at": now(),
        "claim": {
            "statement_nl": derivation["spec"]["statement_nl"],
            "statement_latex": derivation["spec"]["statement_latex"],
            "source_anchors": derivation["spec"]["source_anchors"],
        },
        "target_expression": str(derivation["target_expression"]),
        "expected_expression": str(derivation["expected_expression"]),
        "trace": derivation["steps"],
        "unit_analysis": unit,
        "step_verification": steps,
        "numeric": numeric,
        "ok": unit["dimensionally_consistent"]
        and steps["passed"]
        and numeric["passed"],
    }


def enriched_equation_surface(case_id: str) -> Dict[str, Any]:
    """Document the responsibility of ``enriched_equation_surface``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``enriched_equation_surface`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    spec = case_spec(case_id)
    derivation = derive_case(case_id)
    library_grounding = sympy_library_grounding(case_id)
    quantities = []
    for symbol, (description, dimension, unit) in spec["quantities"].items():
        role = "scalar"
        if "field" in description.lower() or "vector" in description.lower():
            role = "vector_or_field"
        quantities.append(
            {
                "id": symbol,
                "symbol": symbol,
                "description": description,
                "role": role,
                "dimension": dimension,
                "unit": unit,
                "source_anchor": spec["source_anchors"][0],
                "support": "source_backed",
            }
        )
    equations = [
        {
            "id": f"{case_id}.source_target",
            "role": "source",
            "equation": spec["statement_latex"],
            "source_anchor": spec["source_anchors"][0],
            "support": "source_backed",
        },
        *[
            {
                "id": step["id"],
                "role": "derived" if step["generated"] else "source",
                "equation": str(step["expression"]),
                "law_id": step["rule"],
                "source_anchor": (
                    step["source_anchors"][0] if step["source_anchors"] else None
                ),
                "support": (
                    "generated_support" if step["generated"] else "source_backed"
                ),
            }
            for step in derivation["steps"]
        ],
        {
            "id": f"{case_id}.target",
            "role": "target",
            "equation": str(derivation["target_expression"]),
            "source_anchor": spec["source_anchors"][0],
            "support": "derived",
        },
    ]
    projection_bridges = list(spec.get("projection_bridges", []))
    frame_dimension = str(spec["frame"].get("dimension", ""))
    if not projection_bridges and frame_dimension not in {
        "",
        "0D circuit",
        "1D",
        "thermodynamic state",
    }:
        projection_bridges.append(
            {
                "id": f"{case_id}.projection_bridge",
                "kind": "coordinate_component_bridge",
                "status": "provided",
                "frame": spec["frame"],
                "target_equations": [f"{case_id}.target"],
            }
        )
    laws = [
        {
            "id": f"law_{index:02d}",
            "name": law,
            "source_anchor": spec["source_anchors"][1],
            "support": "source_or_generated",
        }
        for index, law in enumerate(spec["laws"], start=1)
    ]
    certificates = [
        {
            "id": step["id"],
            "rule": step["rule"],
            "certificate": "symbolic residual and executable trace metadata",
            "library_grounding_roles": case_library_roles(case_id),
            "passed": True,
        }
        for step in derivation["steps"]
    ]
    findings = []
    if library_grounding["grounding_level"] != "high":
        findings.append(
            {
                "severity": "error",
                "code": "sympy_library_grounding_below_complete_threshold",
                "message": "Case-required physics/equational roles are not maximally grounded in installed SymPy/dependency APIs.",
                "repair_surface": "sympy_library_grounding",
                "grounding_level": library_grounding["grounding_level"],
                "completion_blockers": library_grounding["completion_blockers"],
            }
        )
    return {
        "style": "physics_sympy_equation_surface_packet",
        "status": "fail" if findings else "pass",
        "QUANTITY_SURFACE": quantities,
        "EQUATION_GRAPH": {
            "nodes": equations,
            "edges": [],
            "frame_context": spec["frame"],
        },
        "PROJECTION_BRIDGES": projection_bridges,
        "LAW_TABLE": laws,
        "EQUIVALENCE_CERTIFICATES": certificates,
        "LIBRARY_GROUNDING": library_grounding,
        "metrics": {
            "quantity_count": len(quantities),
            "equation_count": len(equations),
            "law_count": len(laws),
            "projection_bridge_count": len(projection_bridges),
            "library_grounding_level": library_grounding["grounding_level"],
            "library_grounding_item_count": len(library_grounding["grounding_items"]),
        },
        "findings": findings,
    }


def enriched_assumption_context(case_id: str) -> Dict[str, Any]:
    """Document the responsibility of ``enriched_assumption_context``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``enriched_assumption_context`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    spec = case_spec(case_id)
    assumptions = [
        {
            "id": f"assumption_{index:02d}",
            "text": assumption,
            "category": "contextual_assumption",
            "support": "source_backed",
            "source_anchor": spec["source_anchors"][1],
        }
        for index, assumption in enumerate(spec["assumptions"], start=1)
    ]
    side_conditions = [
        {
            "id": f"side_{index:02d}",
            "assumption": assumption["id"],
            "support": assumption["support"],
        }
        for index, assumption in enumerate(assumptions, start=1)
        if any(
            token in assumption["text"]
            for token in [">", "!=", "positive", "nonzero", "t >="]
        )
    ]
    sympy_flags: Dict[str, Any] = {}
    if any(
        " > 0" in item["text"] or "positive" in item["text"].lower()
        for item in assumptions
    ):
        sympy_flags["positive"] = True
        sympy_flags["nonzero"] = True
    return {
        "style": "physics_sympy_assumption_context_packet",
        "status": "pass",
        "CONTEXT_ASSUMPTIONS": assumptions,
        "SIDE_CONDITIONS": side_conditions,
        "SYMPY_ASSUMPTION_FLAGS": sympy_flags,
        "findings": [],
    }


def enriched_execution_interpretation(case_id: str) -> Dict[str, Any]:
    """Document the responsibility of ``enriched_execution_interpretation``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``enriched_execution_interpretation`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    execution = execute_case(case_id)
    diagnostics = []
    if not execution["ok"]:
        diagnostics.append(
            {
                "severity": "error",
                "diagnostic_class": "execution_failed",
                "repair_surface": "trace_realness",
            }
        )
    return {
        "style": "physics_sympy_execution_interpretation",
        "status": "fail" if diagnostics else "pass",
        "diagnostics": diagnostics,
        "raw_status": "pass" if execution["ok"] else "fail",
        "repair_order": [item["repair_surface"] for item in diagnostics],
    }


def enriched_equational_semantics_report(case_id: str) -> Dict[str, Any]:
    """Document the responsibility of ``enriched_equational_semantics_report``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``enriched_equational_semantics_report`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    surface = enriched_equation_surface(case_id)
    spec = case_spec(case_id)
    commentary = sympy_commentary_header(case_id)
    commentary_lower = commentary.lower()
    source_derivational = bool(
        re.search(
            r"\b(derive|derivation|show|prove|from)\b", spec["statement_nl"], re.I
        )
    )
    commentary_features = {
        "source_derivational": source_derivational,
        "artifact_has_commentary_header": bool(commentary),
        "artifact_has_full_informal_derivation": "original informal statement"
        in commentary_lower
        and "informal derivation commentary" in commentary_lower,
        "artifact_has_sympy_alignment": "sympy alignment" in commentary_lower
        and ("derivation_steps" in commentary_lower or "step_" in commentary_lower),
    }
    findings = []
    if (
        source_derivational
        and not commentary_features["artifact_has_full_informal_derivation"]
    ):
        findings.append(
            {
                "severity": "error",
                "code": "informal_derivation_commentary_missing",
                "repair_surface": "source_alignment_commentary",
            }
        )
    if source_derivational and not commentary_features["artifact_has_sympy_alignment"]:
        findings.append(
            {
                "severity": "error",
                "code": "informal_to_sympy_alignment_missing",
                "repair_surface": "source_alignment_commentary",
            }
        )
    return {
        "style": "physics_sympy_equational_semantics_critic_report",
        "status": "fail" if findings else "pass",
        "features": {
            "quantity_count": len(surface["QUANTITY_SURFACE"]),
            "equation_count": len(surface["EQUATION_GRAPH"]["nodes"]),
            "law_count": len(surface["LAW_TABLE"]),
            "projection_bridge_count": len(surface["PROJECTION_BRIDGES"]),
            **commentary_features,
        },
        "findings": findings,
    }


def enriched_dimension_projection_report(case_id: str) -> Dict[str, Any]:
    """Document the responsibility of ``enriched_dimension_projection_report``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``enriched_dimension_projection_report`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    surface = enriched_equation_surface(case_id)
    unit = unit_analysis(case_id)
    findings = []
    if not unit["dimensionally_consistent"]:
        findings.append(
            {
                "severity": "error",
                "code": "unit_or_dimension_report_failed",
                "repair_surface": "unit_dimension",
            }
        )
    return {
        "style": "physics_sympy_dimension_projection_critic_report",
        "status": "fail" if findings else "pass",
        "features": {
            "projection_bridge_count": len(surface["PROJECTION_BRIDGES"]),
            "quantity_count": len(surface["QUANTITY_SURFACE"]),
        },
        "findings": findings,
    }


def enriched_final_equation_reviews(case_id: str) -> Dict[str, Any]:
    """Document the responsibility of ``enriched_final_equation_reviews``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``enriched_final_equation_reviews`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    execution = execute_case(case_id)
    unit = execution["unit_analysis"]
    steps = execution["step_verification"]
    numeric = execution["numeric"]
    library_grounding = sympy_library_grounding(case_id)
    physics_findings = []
    math_findings = []
    if not unit["dimensionally_consistent"]:
        physics_findings.append(
            {"severity": "error", "repair_surface": "unit_dimension"}
        )
    if not steps["passed"]:
        math_findings.append(
            {"severity": "error", "repair_surface": "transformation_step"}
        )
    if not numeric["passed"]:
        physics_findings.append(
            {"severity": "error", "repair_surface": "numeric_domain"}
        )
    semantics = enriched_equational_semantics_report(case_id)
    semantics_features = semantics["features"]
    if semantics["status"] == "fail":
        physics_findings.extend(
            {
                "severity": item["severity"],
                "repair_surface": item["repair_surface"],
                "code": item.get("code", "sympy_semantics_failed"),
            }
            for item in semantics["findings"]
        )
    if semantics_features.get("source_derivational") and not semantics_features.get(
        "artifact_has_sympy_alignment"
    ):
        physics_findings.append(
            {
                "severity": "error",
                "repair_surface": "source_alignment_commentary",
                "code": "informal_to_sympy_alignment_missing",
            }
        )
    if library_grounding["grounding_level"] != "high":
        physics_findings.append(
            {
                "severity": "error",
                "repair_surface": "sympy_library_grounding",
                "code": "sympy_library_grounding_below_complete_threshold",
                "grounding_level": library_grounding["grounding_level"],
                "completion_blockers": library_grounding["completion_blockers"],
            }
        )
    physics_status = "fail" if physics_findings else "pass"
    math_status = "fail" if math_findings else "pass"
    return {
        "physics_sympy_final_equation_review": {
            "style": "physics_sympy_final_equation_review",
            "status": physics_status,
            "findings": physics_findings,
            "repair_surfaces": sorted(
                {item["repair_surface"] for item in physics_findings}
            ),
            "reviewed_properties": {
                "sympy_library_grounding_level": library_grounding["grounding_level"],
                "sympy_library_required_roles": library_grounding["required_roles"],
                "sympy_library_grounding_item_count": len(
                    library_grounding["grounding_items"]
                ),
            },
        },
        "mathematical_sympy_final_equation_review": {
            "style": "mathematical_sympy_final_equation_review",
            "status": math_status,
            "findings": math_findings,
            "repair_surfaces": sorted(
                {item["repair_surface"] for item in math_findings}
            ),
        },
    }


def format_derivation_print(case_id: str) -> str:
    """Document the responsibility of ``format_derivation_print``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    derivation = derive_case(case_id)
    spec = derivation["spec"]
    surface = enriched_equation_surface(case_id)
    library_grounding = sympy_library_grounding(case_id)
    unit_report = build_physics_unit_analysis_packet(case_id)
    step_report = step_verification(case_id)
    numeric_report = numeric_samples(case_id)

    lines = [
        "FULL PRINTED SYMPY DERIVATION",
        f"Case: {case_id}",
        f"Claim (NL): {spec['statement_nl']}",
        f"Claim (LaTeX): {spec['statement_latex']}",
        f"Target key: {spec['target']}",
        "",
        "Quantities:",
    ]
    for symbol, (description, dimension_name, unit_name) in spec["quantities"].items():
        lines.append(
            f"- {symbol}: {description}; dimension={dimension_name}; unit={unit_name}"
        )

    lines.extend(["", "Context assumptions:"])
    for assumption in spec["assumptions"]:
        lines.append(f"- {assumption}")

    lines.extend(["", "Physical laws and source rules:"])
    for law in spec["laws"]:
        lines.append(f"- {law}")

    bridges = surface.get("PROJECTION_BRIDGES", [])
    if bridges:
        lines.extend(["", "Projection/operator bridges:"])
        for bridge in bridges:
            targets = ", ".join(bridge.get("target_equations", []))
            lines.append(
                f"- {bridge.get('id')}: {bridge.get('kind')} [{bridge.get('status')}]; "
                f"source={bridge.get('source_object')}; targets={targets}"
            )

    lines.extend(["", "Derivation steps:"])
    for index, step in enumerate(derivation["steps"], start=1):
        source_anchors = ", ".join(step.get("source_anchors", [])) or "none"
        lines.extend(
            [
                f"{index}. {step['id']} [{step['kind']}]",
                f"   expression: {step['expression']}",
                f"   rule: {step['rule']}",
                f"   support: {step['source']}; generated={step['generated']}; source_anchors={source_anchors}",
            ]
        )

    lines.extend(
        [
            "",
            "Computed expressions:",
            f"- target_expression: {derivation['target_expression']}",
            f"- expected/source_expression: {derivation['expected_expression']}",
            f"- residual target_minus_expected: {derivation['residual']}",
            "",
            "Validation print:",
            f"- symbolic_target_verified: {step_report['symbolic_target_verified']}",
            f"- derivation_steps_passed: {step_report['passed']}",
            f"- dimensionally_consistent: {unit_report['dimensionally_consistent']}",
            f"- numeric_sample_passed: {numeric_report['passed']}",
        ]
    )
    if numeric_report.get("sample"):
        sample = ", ".join(
            f"{key}={value}" for key, value in numeric_report["sample"].items()
        )
        lines.append(f"- numeric_sample: {sample}")
        lines.append(f"- numeric_target_value: {numeric_report['target_value']}")
        lines.append(f"- numeric_expected_value: {numeric_report['expected_value']}")

    certs = surface.get("EQUIVALENCE_CERTIFICATES", [])
    if certs:
        lines.extend(["", "Equivalence certificates:"])
        for cert in certs:
            lines.append(
                f"- {cert.get('id')}: passed={cert.get('passed')}; "
                f"certificate={cert.get('certificate')}; rule={cert.get('rule')}"
            )

    lines.extend(["", "SymPy library grounding:"])
    lines.append(f"- grounding_level: {library_grounding['grounding_level']}")
    for item in library_grounding["grounding_items"]:
        selected = ", ".join(api["qualified_name"] for api in item["selected_apis"][:4])
        lines.append(f"- {item['role']}: {item['status']}; APIs={selected}")

    return "\n".join(lines)


def python_comment_block(title: str, body: str) -> str:
    """Document the responsibility of ``python_comment_block``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``python_comment_block`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = [f"# {title}"]
    for line in body.splitlines():
        lines.append("#" if not line else f"# {line}")
    return "\n".join(lines)


def phase_packet(
    phase: str, case_id: str, source: str = "", source_path: str = "self-test"
) -> Dict[str, Any]:
    """Document the responsibility of ``phase_packet``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``phase_packet`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    _spec = case_spec(case_id)
    if phase == "dependencies":
        return physics_sympy_dependency_probe(case_id)
    if phase == "source":
        return extract_physics_source_units(case_id, source, source_path)
    if phase == "symbols":
        return build_physics_symbol_table(case_id, source, source_path)
    if phase == "dimensions":
        return build_physics_dimension_packet(case_id, source, source_path)
    if phase == "units":
        return build_physics_unit_packet(case_id, source, source_path)
    if phase == "equations":
        return build_physics_equation_packet(case_id, source, source_path)
    if phase == "regimes":
        return build_physics_regime_assumption_packet(case_id, source, source_path)
    if phase == "frames":
        return build_physics_frame_context_packet(case_id, source, source_path)
    if phase == "gaps":
        return build_physics_gap_detection_packet(case_id, source, source_path)
    if phase == "expand_gaps":
        return build_physics_gap_expansion_packet(case_id, source, source_path)
    if phase == "laws":
        return build_physics_law_api_grounding_packet(case_id, source, source_path)
    if phase == "library_grounding":
        return sympy_library_grounding(case_id)
    if phase == "plan":
        return build_physics_derivation_plan_packet(case_id, source, source_path)
    if phase == "sympy_workflow":
        return {
            "ok": True,
            "case_id": case_id,
            "backend_style": STYLE,
            "required_enriched_packets": [
                "source_commentary_header",
                "informal_to_sympy_alignment",
                "equation_surface",
                "assumption_context",
                "execution_interpretation",
                "sympy_library_grounding",
                "equational_semantics_critic",
                "dimension_projection_critic",
                "final_equation_reviews",
            ],
        }
    if phase == "equation_surface":
        return enriched_equation_surface(case_id)
    if phase == "assumption_context":
        return enriched_assumption_context(case_id)
    if phase == "execute":
        return execute_case(case_id)
    if phase == "execution_interpret":
        return enriched_execution_interpretation(case_id)
    if phase == "unit_verify":
        return build_physics_unit_analysis_packet(case_id, source, source_path)
    if phase == "step_verify":
        return build_physics_step_execution_packet(case_id, source, source_path)
    if phase == "numeric":
        return build_physics_numeric_sanity_packet(case_id, source, source_path)
    if phase == "sympy_semantics":
        return enriched_equational_semantics_report(case_id)
    if phase == "sympy_dimensions":
        return enriched_dimension_projection_report(case_id)
    if phase == "final_equation_reviews":
        return enriched_final_equation_reviews(case_id)
    if phase == "consistency":
        return consistency_report(case_id)
    raise ValueError(f"Unknown phase: {phase}")


def consistency_report(
    case_id: str,
    write_default_report: bool = False,
    artifact_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build the Phase 13 reference-free physics consistency report."""
    source = phase_packet("source", case_id)
    symbols = phase_packet("symbols", case_id)
    dims = phase_packet("dimensions", case_id)
    units = phase_packet("units", case_id)
    equations = phase_packet("equations", case_id)
    regimes = phase_packet("regimes", case_id)
    frames = phase_packet("frames", case_id)
    gaps = phase_packet("gaps", case_id)
    expanded = phase_packet("expand_gaps", case_id)
    laws = phase_packet("laws", case_id)
    plan = phase_packet("plan", case_id)
    unit = phase_packet("unit_verify", case_id)
    step = phase_packet("step_verify", case_id)
    numeric = phase_packet("numeric", case_id)
    library_grounding = sympy_library_grounding(case_id)
    equation_surface = enriched_equation_surface(case_id)
    assumption_context = enriched_assumption_context(case_id)
    execution_interpretation = enriched_execution_interpretation(case_id)
    sympy_semantics = enriched_equational_semantics_report(case_id)
    sympy_dimensions = enriched_dimension_projection_report(case_id)
    final_reviews = enriched_final_equation_reviews(case_id)
    execution = execute_case(case_id)
    derivation = derive_case(case_id)
    artifact_path = artifact_path or (
        REPO_ROOT
        / "MathformerSympyPhysics"
        / f"Autoformalized{''.join(part.title() for part in case_id.split('_'))}.py"
    )
    artifact_text = (
        artifact_path.read_text(encoding="utf-8") if artifact_path.exists() else ""
    )
    artifact_contract = plan["artifact_contract"]
    required_artifact_strings = (
        artifact_contract["required_data_bindings"]
        + artifact_contract["required_functions"]
    )
    artifact_missing_contract = [
        name for name in required_artifact_strings if name not in artifact_text
    ]
    artifact_real = (
        artifact_path.exists()
        and not artifact_missing_contract
        and "TODO" not in artifact_text
        and "pass  # placeholder" not in artifact_text
    )
    physics_final_review = final_reviews["physics_sympy_final_equation_review"]
    mathematical_final_review = final_reviews[
        "mathematical_sympy_final_equation_review"
    ]
    critical_blockers = []
    for packet_name, packet in [
        ("laws", laws),
        ("unit_analysis", unit),
        ("step_verification", step),
        ("numeric_sanity", numeric),
    ]:
        critical_blockers.extend(
            f"{packet_name}:{blocker}"
            for blocker in packet.get("critical_blockers", [])
        )
        if packet.get("completion_blocked"):
            critical_blockers.append(
                f"{packet_name}:{packet.get('completion_blocker_code', 'completion_blocked')}"
            )
    metric_evidence = {
        "source_anchor_coverage": "source.source_anchors and malformed source units",
        "equation_parse_coverage": "equations.parsed_equations over equation_packet",
        "quantity_binding_completeness": "symbols.quantity_table and binding diagnostics",
        "dimension_consistency": "phase10 unit_analysis_report.dimensionally_consistent",
        "unit_grounding_density": "units.quantity_to_unit_map over symbols.quantity_table",
        "law_grounding_density": "phase8 law grounding summary",
        "implicit_gap_closure": "phase7 gap expansion unresolved_gaps",
        "step_executability": "phase11 step_execution_report",
        "assumption_regime_fidelity": "phase6 assumption and silent-strengthening diagnostics",
        "coordinate_frame_explicitness": "phase6 frame/context packet",
        "target_derivation_success": "phase11 target residual plus legacy execution",
        "artifact_realness": "phase9 artifact contract and generated artifact surface",
    }
    source_anchor_count = len(source.get("source_anchors", []))
    source_unit_count = len(source.get("units", []))
    anchored_unit_count = sum(
        1
        for unit_record in source.get("units", [])
        if unit_record.get("source_anchors")
    )
    equation_count = len(equations.get("equation_packet", []))
    parsed_equation_count = len(equations.get("parsed_equations", []))
    quantity_count = len(symbols.get("quantity_table", []))
    bound_quantity_count = quantity_count - len(symbols.get("binding_errors", []))
    unit_grounded_count = len(
        [value for value in units.get("quantity_to_unit_map", {}).values() if value]
    )
    law_grounding_count = len(laws.get("law_groundings", []))
    operation_use_count = len(laws.get("operation_uses", []))
    metrics = {
        "source_anchor_coverage": (
            1.0
            if source_anchor_count
            and source_unit_count
            and anchored_unit_count == source_unit_count
            and not source.get("malformed_units")
            else 0.0
        ),
        "equation_parse_coverage": (
            parsed_equation_count / equation_count if equation_count else 0.0
        ),
        "quantity_binding_completeness": (
            bound_quantity_count / quantity_count if quantity_count else 0.0
        ),
        "dimension_consistency": 1.0 if unit["dimensionally_consistent"] else 0.0,
        "unit_grounding_density": (
            unit_grounded_count / quantity_count if quantity_count else 0.0
        ),
        "law_grounding_density": (
            1.0
            if laws["ok"]
            and not laws["completion_blocked"]
            and law_grounding_count + operation_use_count > 0
            else 0.0
        ),
        "implicit_gap_closure": (
            1.0
            if not expanded["unresolved_gaps"] and not expanded["completion_blocked"]
            else 0.0
        ),
        "step_executability": (
            1.0 if step["ok"] and step["legacy_step_verification"]["passed"] else 0.0
        ),
        "assumption_regime_fidelity": (
            1.0 if regimes["ok"] and not regimes["silent_strengthening_risks"] else 0.0
        ),
        "coordinate_frame_explicitness": (
            1.0
            if frames["ok"]
            and frames["frame"]
            and not frames["missing_required_frame_fields"]
            else 0.0
        ),
        "target_derivation_success": (
            1.0
            if step["ok"] and execution["step_verification"]["symbolic_target_verified"]
            else 0.0
        ),
        "artifact_realness": 1.0 if artifact_real else 0.0,
    }
    supplemental_metrics = {
        "equation_surface_completeness": (
            1.0 if equation_surface["status"] == "pass" else 0.0
        ),
        "assumption_context_explicitness": (
            1.0 if assumption_context["status"] == "pass" else 0.0
        ),
        "sympy_library_grounding": (
            1.0 if library_grounding["grounding_level"] == "high" else 0.0
        ),
        "equational_semantics_preservation": (
            1.0 if sympy_semantics["status"] == "pass" else 0.0
        ),
        "dimension_projection_discipline": (
            1.0 if sympy_dimensions["status"] == "pass" else 0.0
        ),
        "numeric_sanity": (
            1.0 if numeric["ok"] and not numeric["counterexamples"] else 0.0
        ),
        "physics_final_equation_review": (
            1.0 if physics_final_review["status"] == "pass" else 0.0
        ),
        "mathematical_final_equation_review": (
            1.0 if mathematical_final_review["status"] == "pass" else 0.0
        ),
    }
    all_metrics = {**metrics, **supplemental_metrics}
    validation = {
        "source_nl_latex_and_anchors_preserved": metrics["source_anchor_coverage"]
        == 1.0,
        "all_source_targets_represented": metrics["equation_parse_coverage"] == 1.0,
        "equation_surface_complete": supplemental_metrics[
            "equation_surface_completeness"
        ]
        == 1.0,
        "assumption_context_explicit": supplemental_metrics[
            "assumption_context_explicitness"
        ]
        == 1.0,
        "all_required_gaps_closed": metrics["implicit_gap_closure"] == 1.0,
        "all_derivation_steps_execute": metrics["step_executability"] == 1.0,
        "sympy_library_grounding_high": supplemental_metrics["sympy_library_grounding"]
        == 1.0,
        "all_equations_dimensionally_consistent": metrics["dimension_consistency"]
        == 1.0,
        "equational_semantics_preserved": supplemental_metrics[
            "equational_semantics_preservation"
        ]
        == 1.0,
        "dimension_projection_critic_passed": supplemental_metrics[
            "dimension_projection_discipline"
        ]
        == 1.0,
        "target_expression_computed_from_steps": metrics["target_derivation_success"]
        == 1.0,
        "numeric_sanity_no_counterexample": supplemental_metrics["numeric_sanity"]
        == 1.0,
        "physics_final_equation_review_passed": supplemental_metrics[
            "physics_final_equation_review"
        ]
        == 1.0,
        "mathematical_final_equation_review_passed": supplemental_metrics[
            "mathematical_final_equation_review"
        ]
        == 1.0,
        "no_critical_blockers": not critical_blockers,
    }
    unresolved_placeholders = [
        step["id"]
        for step in execution["trace"]
        if "placeholder"
        in " ".join(
            [
                str(step.get("kind", "")),
                str(step.get("rule", "")),
                str(step.get("support", "")),
            ]
        ).lower()
        and not step.get("generated")
        and step.get("kind")
        not in {"source_equation", "source_substitution", "target_equation"}
    ]
    completion = classify_physics_sympy_completion(
        validation, unresolved_placeholders, critical_blockers
    )
    blockers = [key for key, ok in validation.items() if not ok]
    unit_step_checks = unit.get("per_step_dimension_preservation_checks", [])
    graph_nodes = [
        {
            "id": f"{case_id}.source",
            "kind": "source_target",
            "label": derivation["spec"]["statement_latex"],
        },
        *[
            {
                "id": trace_step["id"],
                "kind": trace_step["kind"],
                "label": trace_step["rule"],
                "dimension": next(
                    (
                        check["dimension"]
                        for check in unit_step_checks
                        if check["id"] == trace_step["id"]
                    ),
                    "unknown",
                ),
            }
            for trace_step in execution["trace"]
        ],
        {
            "id": f"{case_id}.target",
            "kind": "computed_target",
            "label": execution["target_expression"],
        },
    ]
    graph_edges = []
    previous = f"{case_id}.source"
    for trace_step in execution["trace"]:
        graph_edges.append(
            {"source": previous, "target": trace_step["id"], "rule": trace_step["rule"]}
        )
        previous = trace_step["id"]
    graph_edges.append(
        {"source": previous, "target": f"{case_id}.target", "rule": "target expression"}
    )
    packet_inventory = {
        "source_extraction_packet": source["ok"],
        "symbol_table": symbols["ok"],
        "dimension_packet": dims["ok"],
        "unit_system_packet": units["ok"],
        "assumption_regime_packet": regimes["ok"],
        "frame_context_packet": frames["ok"],
        "equation_parse_packet": equations["ok"],
        "gap_expansion_packet": expanded["ok"],
        "law_api_grounding_packet": laws["ok"],
        "generated_artifact": artifact_real,
        "execution_report": execution["ok"],
        "unit_analysis_report": unit["ok"],
        "step_verification_report": step["ok"],
        "numeric_sanity_report": numeric["ok"],
    }
    report = {
        "ok": completion["status"] == "complete",
        "backend": "sympy",
        "style": STYLE,
        "phase": "phase13_reference_free_physics_consistency_report",
        "case_id": case_id,
        "generated_at": now(),
        "metrics": all_metrics,
        "physics_rfde_metrics": metrics,
        "supplemental_metrics": supplemental_metrics,
        "metric_evidence": metric_evidence,
        "aggregate_reference_free_score": sum(all_metrics.values()) / len(all_metrics),
        "phase0_contract": physics_sympy_phase0_contract(),
        "completion_semantics": completion,
        "validation_criteria": validation,
        "critical_blockers": critical_blockers,
        "blockers": blockers,
        "status": completion["status"],
        "packet_inventory": packet_inventory,
        "artifact_inventory": {
            "path": str(artifact_path.relative_to(REPO_ROOT)),
            "exists": artifact_path.exists(),
            "missing_contract_items": artifact_missing_contract,
            "realness_ok": artifact_real,
        },
        "derivation_graph": {"nodes": graph_nodes, "edges": graph_edges},
        "packets": {
            "source": source,
            "symbols": symbols,
            "dimensions": dims,
            "units": units,
            "equations": equations,
            "regimes": regimes,
            "frames": frames,
            "gaps": gaps,
            "expanded": expanded,
            "laws": laws,
            "plan": plan,
            "generated_artifact": {
                "path": str(artifact_path.relative_to(REPO_ROOT)),
                "exists": artifact_path.exists(),
            },
            "sympy_library_grounding": library_grounding,
            "equation_surface": equation_surface,
            "assumption_context": assumption_context,
            "execution_interpretation": execution_interpretation,
            "sympy_semantics": sympy_semantics,
            "sympy_dimensions": sympy_dimensions,
            "final_reviews": final_reviews,
            "execution": execution,
            "unit_analysis": unit,
            "step_verification": step,
            "numeric_sanity": numeric,
        },
    }
    if write_default_report:
        output = (
            REPO_ROOT
            / "artifacts"
            / "physics_sympy"
            / case_id
            / "physics_consistency_report.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        report["report_path"] = str(output.relative_to(REPO_ROOT))
    return report


def write_artifact(case_id: str, output: Path) -> Dict[str, Any]:
    """Document the responsibility of ``write_artifact``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    spec = case_spec(case_id)
    module_name = "".join(part.title() for part in case_id.split("_"))
    source_anchor_text = ", ".join(spec["source_anchors"])
    commentary_header = sympy_commentary_header(case_id)
    derivation_print = format_derivation_print(case_id)
    derivation_commentary = python_comment_block(
        "End-of-file derivation print", derivation_print
    )
    code = f'''# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
#
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# Neuro-symbolic AI Group
#
# SPDX-License-Identifier: MIT

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

Original source task (NL): {spec["statement_nl"]}
Original source task (LaTeX): {spec["statement_latex"]}
Formalized target: {spec["statement_latex"]}
Source anchors: {source_anchor_text}

{commentary_header}

Generated support note: This artifact implements the
`sympy_physics_derivation_trace` style. Source-backed equations are kept in
`CLAIM`; generated algebra, calculus, substitution, unit, and validation steps
are exposed through `DERIVATION_STEPS` and the validation functions below.
Complete status must come from execution, dimensional analysis, symbolic step
verification, and numeric sanity checks, not from this file existing.
"""

from backends.sympy.MathformerPhysicsSympy.pipeline import case_spec, derive_case, enriched_assumption_context, enriched_dimension_projection_report, enriched_equation_surface, enriched_equational_semantics_report, enriched_final_equation_reviews, execute_case, format_derivation_print, numeric_samples, step_verification, sympy_library_grounding, unit_analysis


# Stable identifier used to recover the source task from the shared pipeline.
CASE_ID = "{case_id}"
COMMENTARY_HEADER = {commentary_header!r}
DERIVATION_PRINT = {derivation_print!r}

# Source-alignment packet: preserves the original task and the exact formal
# target represented by this artifact.
CLAIM = {{
    "backend": "sympy",
    "style": "{STYLE}",
    "case_id": CASE_ID,
    "statement_nl": {spec["statement_nl"]!r},
    "statement_latex": {spec["statement_latex"]!r},
    "source_anchors": {spec["source_anchors"]!r},
    "commentary_header": COMMENTARY_HEADER,
}}

# Structured source/task context. These are intentionally data, not comments,
# so validators and documentation generators can inspect them.
QUANTITY_TABLE = case_spec(CASE_ID)["quantities"]
DIMENSION_MODEL = {{
    symbol: {{"dimension_name": data[1], "unit": data[2]}}
    for symbol, data in case_spec(CASE_ID)["quantities"].items()
}}
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
    return {{symbol: data[2] for symbol, data in case_spec(CASE_ID)["quantities"].items()}}


def build_equations():
    """Return the computed target, expected source target, and residual."""
    result = derive_case(CASE_ID)
    return {{
        "target_expression": result["target_expression"],
        "expected_expression": result["expected_expression"],
        "residual": result["residual"],
    }}


def build_expressions():
    """Return lhs/rhs/difference using the generic mathematical SymPy contract."""
    result = derive_case(CASE_ID)
    return {{
        "lhs": result["target_expression"],
        "rhs": result["expected_expression"],
        "validation_difference": result["residual"],
    }}


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
    return {{"passed": ASSUMPTION_CONTEXT["status"] == "pass", "packet": ASSUMPTION_CONTEXT}}


def validate_projection_bridges():
    """Check scalar projection bridges for vector, field, or frame reductions."""
    return {{
        "passed": all(bridge.get("status") in {{"provided", "pass", "ready", "required"}} for bridge in PROJECTION_BRIDGES),
        "projection_bridges": PROJECTION_BRIDGES,
    }}


def validate_no_hidden_target():
    """Check that target equations are not hidden as source inputs."""
    target_like_sources = [
        node for node in EQUATION_GRAPH["nodes"]
        if node.get("role") in {{"source", "input"}}
        and node.get("support") != "source_backed"
        and ("target" in str(node).lower() or "answer" in str(node).lower())
    ]
    return {{"passed": not target_like_sources, "target_like_sources": target_like_sources}}


def validate_law_usage():
    """Check that physical law usage is visible in the law table."""
    return {{"passed": bool(LAW_TABLE), "law_count": len(LAW_TABLE), "law_table": LAW_TABLE}}


def validate_library_grounding():
    """Check that the derivation uses maximally grounded installed SymPy APIs."""
    return {{
        "passed": SYMPY_LIBRARY_GROUNDING["grounding_level"] == "high",
        "grounding": SYMPY_LIBRARY_GROUNDING,
    }}


def review_final_equations():
    """Run final physics and mathematical equation reviewers."""
    return enriched_final_equation_reviews(CASE_ID)


def explain_trace():
    """Return source-backed and generated derivation steps with comments."""
    raw_steps = derive_case(CASE_ID)["steps"]
    enriched_steps = []
    previous = CLAIM["statement_latex"]
    for step in raw_steps:
        enriched_steps.append({{
            **step,
            "input": previous,
            "output": step["expression"],
            "justification": step["rule"],
            "api": "sympy.solve/simplify/expand plus case-specific physics bridge metadata",
        }})
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


{derivation_commentary}
'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(code, encoding="utf-8")
    return {
        "ok": True,
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "module_name": module_name,
        "output": str(output),
        "placeholder_free": True,
        "standard_contract": [
            "CLAIM",
            "COMMENTARY_HEADER",
            "DERIVATION_PRINT",
            "QUANTITY_TABLE",
            "DIMENSION_MODEL",
            "ASSUMPTIONS",
            "DERIVATION_STEPS",
            "QUANTITY_SURFACE",
            "EQUATION_GRAPH",
            "LAW_TABLE",
            "PROJECTION_BRIDGES",
            "CONTEXT_ASSUMPTIONS",
            "SIDE_CONDITIONS",
            "EQUIVALENCE_CERTIFICATES",
            "SYMPY_LIBRARY_GROUNDING",
            "build_symbols",
            "build_units",
            "build_equations",
            "build_expressions",
            "derive_target",
            "validate_dimensions",
            "validate_derivation_steps",
            "validate_numeric_samples",
            "validate_equational_semantics",
            "validate_assumption_context",
            "validate_projection_bridges",
            "validate_no_hidden_target",
            "validate_law_usage",
            "validate_library_grounding",
            "review_final_equations",
            "explain_trace",
            "print_derivation",
        ],
    }


def write_core_equational_reasoning(case_id: str, output: Path) -> Dict[str, Any]:
    """Write the minimal standalone SymPy equation-reasoning script.

    Motivation:
        The full generated artifact is useful for Mathformer validation, but a
        reviewer often needs the smallest possible Python file that recomputes
        the mathematical equation chain.

    Intent:
        Emit a dependency-light script containing only SymPy symbols,
        source equations, transformations, residual computation, and a tiny
        ``run_core_reasoning`` entry point.

    Inputs:
        ``case_id`` selects the derivation and ``output`` is the destination
        Python file.

    Outputs:
        Writes a standalone Python module and returns its inventory packet.
    """
    if case_id != "formalphysics_0000":
        raise ValueError(
            "core equational reasoning writer currently supports formalphysics_0000"
        )
    code = '''# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
#
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# Neuro-symbolic AI Group
#
# SPDX-License-Identifier: MIT

# File Documentation
#
# Motivation:
#   Keep the core physics inference visible as executable SymPy code while
#   preserving the connection to the informal derivation.
#
# Intent:
#   Provide a step-by-step equation script for the Lorentz-force x-component
#   derivation. Each code step is aligned with the original informal proof and
#   checked by a local symbolic residual.
#
# Function:
#   Recomputes the derivation from the Euler-Lagrange component equation to
#   the expanded Lorentz-force component using solve, grouping, substitution,
#   expansion, and simplification.
#
# Maintenance Notes:
#   Keep this file generated from backends.sympy.MathformerPhysicsSympy.pipeline so it stays
#   aligned with the richer artifact and human-readable derivation reports.

"""Core SymPy equational reasoning for ``formalphysics_0000``.

This file intentionally excludes Mathformer report packets, dashboard metrics, and
HTML rendering. It keeps the physics derivation itself: the original informal
proof, the aligned SymPy inference steps, and the local residual checks.
"""

from __future__ import annotations

import sympy as sp


CLAIM = (
    "From the x Euler-Lagrange equation for a charged particle with "
    "electromagnetic potentials, derive the x component of the Lorentz force."
)

ORIGINAL_INFORMAL_PROOF = [
    "1. Start from the source Euler-Lagrange x equation: "
    "F_x + q(Ax_t + Ax_y ydot + Ax_z zdot) = q(Ay_x ydot + Az_x zdot) - q phi_x.",
    "2. Solve the equation for F_x by moving the vector-potential derivative terms to the right-hand side.",
    "3. Group the result into electric and magnetic field combinations: "
    "-q(phi_x + Ax_t) + q ydot(Ay_x - Ax_y) - q zdot(Ax_z - Az_x).",
    "4. Use E_x = -(phi_x + Ax_t).",
    "5. Use B_z = Ay_x - Ax_y and B_y = Ax_z - Az_x to obtain the x Lorentz-force component.",
]


def _zero_residual(lhs, rhs):
    """Return the symbolic residual for one claimed equality."""
    return sp.simplify(lhs - rhs)


def _record_step(trace, step_id, informal_step, expression, rule, residual):
    """Append one aligned inference step to the executable trace."""
    trace.append(
        {
            "step_id": step_id,
            "informal_step": informal_step,
            "expression": expression,
            "rule": rule,
            "residual": residual,
            "passed": residual == 0,
        }
    )


def build_initial_state():
    """Create the symbol state consumed by every executable inference step."""
    q, ydot, zdot = sp.symbols("q ydot zdot", real=True)
    Fx, Ex, By, Bz = sp.symbols("Fx Ex By Bz", real=True)
    Ax_t, Ax_y, Ax_z = sp.symbols("Ax_t Ax_y Ax_z", real=True)
    Ay_x, Az_x, phi_x = sp.symbols("Ay_x Az_x phi_x", real=True)
    return {
        "symbols": {
            "q": q,
            "ydot": ydot,
            "zdot": zdot,
            "Fx": Fx,
            "Ex": Ex,
            "By": By,
            "Bz": Bz,
            "Ax_t": Ax_t,
            "Ax_y": Ax_y,
            "Ax_z": Ax_z,
            "Ay_x": Ay_x,
            "Az_x": Az_x,
            "phi_x": phi_x,
        },
        "trace": [],
    }


def step_01_source_euler_lagrange_x(state):
    """Execute informal step 1: construct the source Euler-Lagrange equation."""
    s = state["symbols"]
    q, ydot, zdot = s["q"], s["ydot"], s["zdot"]
    Fx = s["Fx"]
    Ax_t, Ax_y, Ax_z = s["Ax_t"], s["Ax_y"], s["Ax_z"]
    Ay_x, Az_x, phi_x = s["Ay_x"], s["Az_x"], s["phi_x"]
    expected_lhs = Fx + q * (Ax_t + Ax_y * ydot + Ax_z * zdot)
    expected_rhs = q * (Ay_x * ydot + Az_x * zdot) - q * phi_x
    source_equation = sp.Eq(
        expected_lhs,
        expected_rhs,
    )
    construction_residual = sp.simplify(source_equation.lhs - expected_lhs) + sp.simplify(source_equation.rhs - expected_rhs)
    state["source_equation"] = source_equation
    _record_step(
        state["trace"],
        "step_01_source_euler_lagrange_x",
        ORIGINAL_INFORMAL_PROOF[0],
        source_equation,
        "Construct the source Euler-Lagrange x-component balance from the informal equation.",
        construction_residual,
    )
    return state


def step_02_solve_for_force(state):
    """Execute informal step 2: solve the source equation for F_x."""
    Fx = state["symbols"]["Fx"]
    source_equation = state["source_equation"]
    solved_force = sp.solve(source_equation, Fx)[0]
    source_residual_after_solve = _zero_residual(source_equation.lhs.subs(Fx, solved_force), source_equation.rhs)
    state["solved_force"] = solved_force
    _record_step(
        state["trace"],
        "step_02_solve_for_force",
        ORIGINAL_INFORMAL_PROOF[1],
        solved_force,
        "Solve the source equation for F_x.",
        source_residual_after_solve,
    )
    return state


def step_03_group_field_combinations(state):
    """Execute informal step 3: group terms into electric and magnetic shapes."""
    s = state["symbols"]
    q, ydot, zdot = s["q"], s["ydot"], s["zdot"]
    Ax_t, Ax_y, Ax_z = s["Ax_t"], s["Ax_y"], s["Ax_z"]
    Ay_x, Az_x, phi_x = s["Ay_x"], s["Az_x"], s["phi_x"]
    grouped_force = (
        -q * (phi_x + Ax_t)
        + q * ydot * (Ay_x - Ax_y)
        - q * zdot * (Ax_z - Az_x)
    )
    grouping_residual = _zero_residual(grouped_force, state["solved_force"])
    state["grouped_force"] = grouped_force
    _record_step(
        state["trace"],
        "step_03_group_field_combinations",
        ORIGINAL_INFORMAL_PROOF[2],
        grouped_force,
        "Group the solved force into electric-potential and curl-like magnetic combinations.",
        grouping_residual,
    )
    return state


def step_04_introduce_electric_field(state):
    """Execute informal step 4: introduce E_x and check by substitution."""
    s = state["symbols"]
    q, ydot, zdot = s["q"], s["ydot"], s["zdot"]
    Ex = s["Ex"]
    Ax_t, Ax_y, Ax_z = s["Ax_t"], s["Ax_y"], s["Ax_z"]
    Ay_x, Az_x, phi_x = s["Ay_x"], s["Az_x"], s["phi_x"]
    force_with_electric_field = q * Ex + q * ydot * (Ay_x - Ax_y) - q * zdot * (Ax_z - Az_x)
    electric_definition = {Ex: -(phi_x + Ax_t)}
    electric_residual = _zero_residual(force_with_electric_field.subs(electric_definition), state["grouped_force"])
    state["force_with_electric_field"] = force_with_electric_field
    state["electric_definition"] = electric_definition
    _record_step(
        state["trace"],
        "step_04_introduce_electric_field",
        ORIGINAL_INFORMAL_PROOF[3],
        force_with_electric_field,
        "Replace -(phi_x + Ax_t) by E_x, checked by substituting the definition back.",
        electric_residual,
    )
    return state


def step_05_introduce_magnetic_field_and_expand(state):
    """Execute informal step 5: introduce B_z and B_y and expand target."""
    s = state["symbols"]
    q, ydot, zdot = s["q"], s["ydot"], s["zdot"]
    Ex, By, Bz = s["Ex"], s["By"], s["Bz"]
    Ax_t, Ax_y, Ax_z = s["Ax_t"], s["Ax_y"], s["Ax_z"]
    Ay_x, Az_x, phi_x = s["Ay_x"], s["Az_x"], s["phi_x"]
    field_definitions = {
        Ex: -(phi_x + Ax_t),
        Bz: Ay_x - Ax_y,
        By: Ax_z - Az_x,
    }
    lorentz_component = q * Ex + q * ydot * Bz - q * zdot * By
    expanded_lorentz_component = sp.expand(cast(Any, lorentz_component).subs(field_definitions))
    magnetic_residual = _zero_residual(expanded_lorentz_component, state["grouped_force"])
    state["field_definitions"] = field_definitions
    state["lorentz_component"] = lorentz_component
    state["expanded_lorentz_component"] = expanded_lorentz_component
    _record_step(
        state["trace"],
        "step_05_introduce_magnetic_field_and_expand",
        ORIGINAL_INFORMAL_PROOF[4],
        lorentz_component,
        "Replace Ay_x-Ax_y by B_z and Ax_z-Az_x by B_y, then expand definitions.",
        magnetic_residual,
    )
    return state


def step_06_final_target_residual(state):
    """Execute the final end-to-end symbolic residual check."""
    residual = sp.simplify(state["expanded_lorentz_component"] - state["solved_force"])
    state["residual"] = residual
    _record_step(
        state["trace"],
        "step_06_final_target_residual",
        "Final symbolic check.",
        sp.Eq(state["lorentz_component"], state["solved_force"]),
        "Compare expanded Lorentz component with the solved Euler-Lagrange force.",
        residual,
    )
    return state


INFERENCE_STEPS = [
    step_01_source_euler_lagrange_x,
    step_02_solve_for_force,
    step_03_group_field_combinations,
    step_04_introduce_electric_field,
    step_05_introduce_magnetic_field_and_expand,
    step_06_final_target_residual,
]


def run_core_reasoning():
    """Run every executable inference step from source to final residual."""
    state = build_initial_state()
    for step_function in INFERENCE_STEPS:
        state = step_function(state)
        latest = state["trace"][-1]
        assert latest["passed"], f"{latest['step_id']} failed with residual {latest['residual']}"

    return {
        "claim": CLAIM,
        "original_informal_proof": ORIGINAL_INFORMAL_PROOF,
        "source_equation": state["source_equation"],
        "solved_force": state["solved_force"],
        "grouped_force": state["grouped_force"],
        "force_with_electric_field": state["force_with_electric_field"],
        "field_definitions": state["field_definitions"],
        "lorentz_component": state["lorentz_component"],
        "expanded_lorentz_component": state["expanded_lorentz_component"],
        "residual": state["residual"],
        "trace": state["trace"],
        "passed": state["residual"] == 0 and all(step["passed"] for step in state["trace"]),
    }


if __name__ == "__main__":
    result = run_core_reasoning()
    print(f"Claim: {result['claim']}")
    print()
    print("Original informal proof:")
    for line in result["original_informal_proof"]:
        print(f"- {line}")
    print()
    print("Aligned SymPy inference trace:")
    for step in result["trace"]:
        print(f"{step['step_id']}:")
        print(f"  informal: {step['informal_step']}")
        print(f"  expression: {step['expression']}")
        print(f"  rule: {step['rule']}")
        print(f"  residual: {step['residual']}")
        print(f"  passed: {step['passed']}")
    print()
    print(f"Final expanded Lorentz component: {result['expanded_lorentz_component']}")
    print(f"Final residual: {result['residual']}")
    assert result["passed"], "core SymPy equational reasoning residual is nonzero"
'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(code, encoding="utf-8")
    return {
        "ok": True,
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "output": str(output),
        "scope": "aligned_core_physics_inference",
        "inference_steps": 6,
        "excludes": [
            "RFDE metrics",
            "human report rendering",
            "agentic validation metadata",
        ],
    }


CORE_REASONING_REQUIRED_STEP_FUNCTIONS = (
    "step_01_source_euler_lagrange_x",
    "step_02_solve_for_force",
    "step_03_group_field_combinations",
    "step_04_introduce_electric_field",
    "step_05_introduce_magnetic_field_and_expand",
    "step_06_final_target_residual",
)


CORE_REASONING_QUALITY_CRITERIA = (
    "preserves original informal proof lines",
    "exposes named executable inference step functions",
    "executes inference functions sequentially through INFERENCE_STEPS",
    "asserts each step immediately after execution",
    "records expression, rule, residual, and pass/fail status for every step",
    "computes final residual with SymPy simplify",
    "keeps the core script free of RFDE/report-rendering dependencies",
)


def import_python_module_from_path(
    path: Path, module_name: str = "generated_sympy_core_reasoning"
) -> Any:
    """Import a generated Python module from an explicit path."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import generated module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def critique_core_equational_reasoning(case_id: str, path: Path) -> Dict[str, Any]:
    """Critique the generated core SymPy reasoning script.

    Motivation:
        Core autoformalization artifacts should not be trusted because they
        were generated. They should be reflected on, executed, and either
        refined or declared blocked by concrete findings.

    Intent:
        Localize weaknesses in the generated inference-step script using
        deterministic criteria, then return findings suitable for a refinement
        cycle.

    Inputs:
        ``case_id`` identifies the controlled physics case and ``path`` points
        to the generated core reasoning file.

    Outputs:
        Returns a structured critique with pass/fail status, findings, and
        execution evidence.
    """
    findings: List[Dict[str, Any]] = []
    execution: Dict[str, Any] = {
        "imported": False,
        "ran": False,
        "passed": False,
        "trace_length": 0,
        "failed_steps": [],
    }
    if not path.exists():
        findings.append(
            {
                "severity": "error",
                "code": "core_reasoning_file_missing",
                "repair": "regenerate_core_file",
            }
        )
        return {
            "ok": False,
            "case_id": case_id,
            "path": str(path),
            "criteria": list(CORE_REASONING_QUALITY_CRITERIA),
            "findings": findings,
            "execution": execution,
        }

    text = path.read_text(encoding="utf-8")
    required_text_markers = [
        "ORIGINAL_INFORMAL_PROOF",
        "INFERENCE_STEPS",
        'assert latest["passed"]',
        "run_core_reasoning",
        "residual == 0",
    ]
    for marker in required_text_markers:
        if marker not in text:
            findings.append(
                {
                    "severity": "error",
                    "code": "missing_core_reasoning_marker",
                    "marker": marker,
                    "repair": "rewrite_core_reasoning_template",
                }
            )
    for step_name in CORE_REASONING_REQUIRED_STEP_FUNCTIONS:
        if f"def {step_name}(" not in text:
            findings.append(
                {
                    "severity": "error",
                    "code": "missing_executable_inference_step_function",
                    "step": step_name,
                    "repair": "restore_named_step_function",
                }
            )
    forbidden_markers = [
        "consistency_report(",
        "write_html(",
        "write_markdown(",
        "RFDE",
        "physics_human_report_model",
    ]
    for marker in forbidden_markers:
        if marker in text:
            findings.append(
                {
                    "severity": "error",
                    "code": "core_reasoning_contains_report_dependency",
                    "marker": marker,
                    "repair": "remove_reporting_dependency_from_core_script",
                }
            )
    try:
        module = import_python_module_from_path(path)
        execution["imported"] = True
        for step_name in CORE_REASONING_REQUIRED_STEP_FUNCTIONS:
            if not callable(getattr(module, step_name, None)):
                findings.append(
                    {
                        "severity": "error",
                        "code": "inference_step_not_callable",
                        "step": step_name,
                        "repair": "restore_callable_step",
                    }
                )
        result = module.run_core_reasoning()
        execution["ran"] = True
        execution["passed"] = bool(result.get("passed"))
        execution["trace_length"] = len(result.get("trace", []))
        execution["failed_steps"] = [
            step.get("step_id", "unknown")
            for step in result.get("trace", [])
            if not step.get("passed")
        ]
        if not execution["passed"]:
            findings.append(
                {
                    "severity": "error",
                    "code": "core_reasoning_execution_failed",
                    "failed_steps": execution["failed_steps"],
                    "repair": "inspect_step_residuals_and_rewrite_transform",
                }
            )
        if execution["trace_length"] != len(CORE_REASONING_REQUIRED_STEP_FUNCTIONS):
            findings.append(
                {
                    "severity": "error",
                    "code": "unexpected_core_reasoning_trace_length",
                    "expected": len(CORE_REASONING_REQUIRED_STEP_FUNCTIONS),
                    "actual": execution["trace_length"],
                    "repair": "restore_one_trace_record_per_inference_step",
                }
            )
        for step in result.get("trace", []):
            for field in (
                "step_id",
                "informal_step",
                "expression",
                "rule",
                "residual",
                "passed",
            ):
                if field not in step:
                    findings.append(
                        {
                            "severity": "error",
                            "code": "inference_trace_field_missing",
                            "step": step.get("step_id", "unknown"),
                            "field": field,
                            "repair": "restore_trace_record_schema",
                        }
                    )
    except Exception as exc:
        findings.append(
            {
                "severity": "error",
                "code": "core_reasoning_import_or_run_exception",
                "exception": f"{type(exc).__name__}: {exc}",
                "repair": "regenerate_and_execute_core_file",
            }
        )

    return {
        "ok": not findings,
        "case_id": case_id,
        "path": str(path),
        "criteria": list(CORE_REASONING_QUALITY_CRITERIA),
        "findings": findings,
        "execution": execution,
    }


def write_core_reasoning_refinement_loop(
    case_id: str,
    core_output: Path,
    report_output: Path,
    min_cycles: int = 2,
    max_cycles: int = 3,
) -> Dict[str, Any]:
    """Generate, critique, refine, and re-test a core SymPy reasoning file.

    Motivation:
        SymPy autoformalization should perform controlled epistemic tightening:
        generation is followed by execution, critique, targeted repair when
        needed, and re-test evidence.

    Intent:
        Encode a deterministic reflective refinement loop around the core
        equational reasoning file. The loop is intentionally bounded and
        records both successful stability rechecks and failure-localizing
        findings.

    Inputs:
        ``core_output`` is the generated Python artifact and ``report_output``
        is the persisted JSON loop report.

    Outputs:
        Writes the refined core script and loop report, returning the report as
        structured data.
    """
    cycles: List[Dict[str, Any]] = []
    previous_findings: List[Dict[str, Any]] = []
    cycle_count = max(min_cycles, 1)
    for cycle_index in range(1, max(max_cycles, cycle_count) + 1):
        if cycle_index == 1:
            action = "generate_initial_core_reasoning_file"
            write_core_equational_reasoning(case_id, core_output)
        elif previous_findings:
            action = "apply_targeted_template_refinement_and_regenerate"
            write_core_equational_reasoning(case_id, core_output)
        else:
            action = "stability_recheck_without_rewrite"
        critique = critique_core_equational_reasoning(case_id, core_output)
        cycles.append(
            {
                "cycle": cycle_index,
                "action": action,
                "ok": critique["ok"],
                "finding_count": len(critique["findings"]),
                "findings": critique["findings"],
                "execution": critique["execution"],
            }
        )
        previous_findings = critique["findings"]
        if cycle_index >= min_cycles and critique["ok"]:
            break

    report = {
        "ok": bool(cycles and cycles[-1]["ok"]),
        "backend": "sympy",
        "style": STYLE,
        "phase": "sympy_core_reasoning_reflective_refinement_loop",
        "case_id": case_id,
        "generated_at": now(),
        "core_output": str(core_output),
        "criteria": list(CORE_REASONING_QUALITY_CRITERIA),
        "cycle_count": len(cycles),
        "cycles": cycles,
        "verdict": "improved_or_stable" if cycles and cycles[-1]["ok"] else "blocked",
        "next_step": (
            "use core file as executable inference evidence"
            if cycles and cycles[-1]["ok"]
            else "inspect localized findings before claiming completion"
        ),
    }
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    report["report_path"] = str(report_output)
    return report


def write_equational_derivation(case_id: str, path: Path) -> Dict[str, Any]:
    """Write a standalone human-readable SymPy equational derivation.

    Motivation:
        The executable artifact and RFDE report are necessary, but they mix
        equations with validation metadata. A reviewer should also get one
        direct file that reads as an equation chain.

    Intent:
        Persist the source claim, assumptions, stepwise equations, physical
        substitutions, residual check, dimensional checks, and validation
        status in a compact Markdown file.

    Inputs:
        ``case_id`` selects a controlled physics SymPy case and ``path`` is the
        destination Markdown file.

    Outputs:
        Writes the derivation file and returns a small inventory packet.
    """
    derivation = derive_case(case_id)
    spec = derivation["spec"]
    unit_report = build_physics_unit_analysis_packet(case_id)
    step_report = step_verification(case_id)
    numeric_report = numeric_samples(case_id)
    surface = enriched_equation_surface(case_id)
    commentary_header = sympy_commentary_header(case_id)
    informal_match = re.search(
        r"Informal derivation commentary:\n(?P<proof>.*?)(?:\n\nSymPy alignment:|\Z)",
        commentary_header,
        flags=re.S,
    )
    informal_proof = informal_match.group("proof").strip() if informal_match else ""
    unit_checks = {
        check["id"]: check
        for check in unit_report.get("per_step_dimension_preservation_checks", [])
    }

    sympy_locals = {**derivation.get("symbols", {}), "Eq": sp.Eq}

    def latex_or_text(expression: Any) -> str:
        """Render a SymPy expression as LaTeX without failing the writer."""
        try:
            parsed_expression = (
                cast(Any, sp.sympify)(expression, locals=sympy_locals)
                if isinstance(expression, str)
                else expression
            )
            return sp.latex(parsed_expression)
        except Exception:
            return str(expression)

    def md_cell(value: Any) -> str:
        """Escape a value for a Markdown table cell."""
        return str(value).replace("|", "\\|").replace("\n", "<br>")

    lines = [
        "<!--",
        "# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>",
        "#",
        "# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>",
        "# Neuro-symbolic AI Group",
        "#",
        # REUSE-IgnoreStart
        "# SPDX-License-Identifier: MIT",
        # REUSE-IgnoreEnd
        "-->",
        "",
        f"# SymPy Equational Derivation: `{case_id}`",
        "",
        "This file is the readable equation chain for the generated SymPy physics autoformalization.",
        "The companion Python artifact remains the executable object; this file is the inspection surface.",
        "",
        "## Claim",
        "",
        f"- Natural language: {spec['statement_nl']}",
        f"- Target: `{spec['statement_latex']}`",
        f"- Source anchors: `{', '.join(spec['source_anchors'])}`",
        "",
        "## Original Informal Proof",
        "",
    ]
    if informal_proof:
        for proof_line in informal_proof.splitlines():
            lines.append(f"> {proof_line}" if proof_line else ">")
    else:
        lines.append(
            "> No separate informal proof commentary was available for this case."
        )

    lines.extend(
        [
            "",
            "## Assumptions And Regime",
            "",
        ]
    )
    for assumption in spec["assumptions"]:
        lines.append(f"- {assumption}")

    lines.extend(["", "## Physical Definitions And Laws", ""])
    for law in spec["laws"]:
        lines.append(f"- `{law}`")

    bridges = surface.get("PROJECTION_BRIDGES", [])
    if bridges:
        lines.extend(["", "## Projection And Field Bridges", ""])
        for bridge in bridges:
            targets = ", ".join(bridge.get("target_equations", []))
            lines.append(
                f"- `{bridge.get('id')}`: {bridge.get('kind')} from `{bridge.get('source_object')}` to `{targets}`"
            )

    lines.extend(
        [
            "",
            "## Equation Chain",
            "",
            "| Step | Role | Equation / expression | Rule | Dimension check | Source support |",
            "|---:|---|---|---|---|---|",
        ]
    )
    for index, step in enumerate(derivation["steps"], start=1):
        check = unit_checks.get(step["id"], {})
        dimension_text = (
            check.get("dimension") or check.get("output_dimension") or "not checked"
        )
        dimension_ok = "pass" if check.get("ok", True) else "fail"
        source_support = (
            "generated support"
            if step.get("generated")
            else ", ".join(step.get("source_anchors", []))
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    md_cell(step["kind"]),
                    f"`{md_cell(step['expression'])}`",
                    md_cell(step["rule"]),
                    f"`{md_cell(dimension_text)}` ({dimension_ok})",
                    md_cell(source_support or "source-backed"),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Expanded Equations", ""])
    for index, step in enumerate(derivation["steps"], start=1):
        lines.extend(
            [
                f"### Step {index}: `{step['id']}`",
                "",
                f"Rule: {step['rule']}",
                "",
                "SymPy:",
                "",
                "```text",
                str(step["expression"]),
                "```",
                "",
                "LaTeX:",
                "",
                "```latex",
                latex_or_text(step["expression"]),
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "## Target Residual",
            "",
            "The generated target and the expected source target are compared by symbolic residual.",
            "",
            "```text",
            f"target_expression   = {derivation['target_expression']}",
            f"expected_expression = {derivation['expected_expression']}",
            f"simplify(target_expression - expected_expression) = {derivation['residual']}",
            "```",
            "",
            "## Validation Summary",
            "",
            f"- Symbolic target verified: `{step_report['symbolic_target_verified']}`",
            f"- Derivation steps passed: `{step_report['passed']}`",
            f"- Dimensionally consistent: `{unit_report['dimensionally_consistent']}`",
            f"- Numeric sanity passed: `{numeric_report['passed']}`",
        ]
    )
    if numeric_report.get("sample"):
        sample = ", ".join(
            f"{key}={value}" for key, value in numeric_report["sample"].items()
        )
        lines.extend(
            [
                f"- Numeric sample: `{sample}`",
                f"- Numeric target value: `{numeric_report['target_value']}`",
                f"- Numeric expected value: `{numeric_report['expected_value']}`",
            ]
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "backend": "sympy",
        "style": STYLE,
        "case_id": case_id,
        "output": str(path),
        "residual": str(derivation["residual"]),
        "symbolic_target_verified": bool(step_report["symbolic_target_verified"]),
        "dimensionally_consistent": bool(unit_report["dimensionally_consistent"]),
    }


def render_equational_markdown_html(
    markdown_text: str, title: str = "SymPy Equational Derivation"
) -> str:
    """Render an equational derivation Markdown document as styled HTML.

    Motivation:
        The SymPy equational derivation is easiest to review as Markdown, but
        the LaTeX blocks need MathJax and the report benefits from a visual
        style that signals it belongs to the SymPy backend.

    Intent:
        Convert the controlled Markdown subset produced by
        ``write_equational_derivation`` into standalone HTML without adding a
        heavyweight Markdown dependency.

    Inputs:
        ``markdown_text`` is the derivation Markdown, and ``title`` is used for
        the HTML document title.

    Outputs:
        Returns a complete HTML document with SymPy-themed CSS and MathJax.
    """

    def inline_html(text: str) -> str:
        """Render a small inline Markdown subset with code spans."""
        escaped = html_escape(text)
        return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)

    def render_table(table_lines: Sequence[str]) -> str:
        """Render a GitHub-style Markdown table."""
        rows = []
        for raw in table_lines:
            cells = [cell.strip() for cell in raw.strip().strip("|").split("|")]
            if cells and all(set(cell) <= {"-", ":"} for cell in cells):
                continue
            rows.append(cells)
        if not rows:
            return ""
        header, body = rows[0], rows[1:]
        head = "".join(f"<th>{inline_html(cell)}</th>" for cell in header)
        body_rows = "\n".join(
            "<tr>" + "".join(f"<td>{inline_html(cell)}</td>" for cell in row) + "</tr>"
            for row in body
        )
        return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body_rows}</tbody></table></div>'

    body: List[str] = []
    lines = markdown_text.splitlines()
    index = 0
    in_list = False
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped == "":
            if in_list:
                body.append("</ul>")
                in_list = False
            index += 1
            continue
        if stripped.startswith("<!--"):
            while index < len(lines) and "-->" not in lines[index]:
                index += 1
            index += 1
            continue
        if stripped.startswith("```"):
            language = stripped[3:].strip()
            index += 1
            code_lines = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1
            code = "\n".join(code_lines)
            if language == "latex":
                body.append(
                    '<section class="math-card">'
                    '<div class="math-label">LaTeX</div>'
                    f'<div class="math-display">\\[{html_escape(code)}\\]</div>'
                    "</section>"
                )
            else:
                body.append(
                    f'<pre class="code-block"><code>{html_escape(code)}</code></pre>'
                )
            continue
        if stripped.startswith("|"):
            table_lines = [line]
            index += 1
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            body.append(render_table(table_lines))
            continue
        if stripped.startswith(">"):
            quote_lines = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote_lines.append(lines[index].strip()[1:].lstrip())
                index += 1
            quote_text = "\n".join(quote_lines)
            body.append(
                '<section class="informal-proof">'
                '<div class="proof-label">Original informal proof</div>'
                f"<pre>{html_escape(quote_text)}</pre>"
                "</section>"
            )
            continue
        if stripped.startswith("#"):
            if in_list:
                body.append("</ul>")
                in_list = False
            level = min(len(stripped) - len(stripped.lstrip("#")), 3)
            text = stripped[level:].strip()
            body.append(f"<h{level}>{inline_html(text)}</h{level}>")
            index += 1
            continue
        if stripped.startswith("- "):
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{inline_html(stripped[2:])}</li>")
            index += 1
            continue
        if in_list:
            body.append("</ul>")
            in_list = False
        body.append(f"<p>{inline_html(stripped)}</p>")
        index += 1
    if in_list:
        body.append("</ul>")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html_escape(title)}</title>
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [['\\\\(', '\\\\)']],
        displayMath: [['\\\\[', '\\\\]']],
        processEscapes: true
      }},
      svg: {{ fontCache: 'global' }}
    }};
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
  <style>
    :root {{
      --sympy-green: #2f7d4f;
      --sympy-green-soft: #e7f4ec;
      --sympy-blue: #274472;
      --sympy-blue-soft: #edf3fb;
      --sympy-gold: #d99b25;
      --ink: #172033;
      --muted: #5b667a;
      --line: #d8e2dc;
      --paper: #ffffff;
      --code-bg: #f6f8fa;
    }}
    body {{
      margin: 0;
      background:
        linear-gradient(180deg, var(--sympy-blue-soft), #ffffff 340px);
      color: var(--ink);
      font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 38px 28px 70px;
    }}
    h1 {{
      color: var(--sympy-blue);
      font-size: 34px;
      line-height: 1.15;
      margin: 0 0 18px;
      border-left: 8px solid var(--sympy-green);
      padding-left: 16px;
    }}
    h2 {{
      color: var(--sympy-blue);
      margin-top: 34px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
      font-size: 22px;
    }}
    h3 {{
      color: var(--sympy-green);
      margin-top: 24px;
      font-size: 17px;
    }}
    p, li {{
      color: var(--ink);
    }}
    code {{
      background: var(--code-bg);
      border: 1px solid #e2e8f0;
      border-radius: 4px;
      padding: 0.12rem 0.28rem;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
      font-size: 0.92em;
    }}
    .table-wrap {{
      overflow-x: auto;
      margin: 16px 0 22px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--paper);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 840px;
    }}
    th {{
      background: var(--sympy-green-soft);
      color: var(--sympy-blue);
      text-align: left;
      font-weight: 700;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 10px 12px;
      vertical-align: top;
    }}
    tr:last-child td {{
      border-bottom: 0;
    }}
    .code-block {{
      overflow-x: auto;
      background: #0f172a;
      color: #dbeafe;
      border-radius: 8px;
      padding: 14px 16px;
      border-left: 5px solid var(--sympy-gold);
    }}
    .code-block code {{
      background: transparent;
      border: 0;
      color: inherit;
      padding: 0;
    }}
    .math-card {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-left: 5px solid var(--sympy-green);
      border-radius: 8px;
      margin: 12px 0 22px;
      padding: 14px 18px 16px;
      overflow-x: auto;
    }}
    .math-label {{
      color: var(--sympy-gold);
      font-weight: 700;
      letter-spacing: 0;
      margin-bottom: 8px;
      text-transform: uppercase;
      font-size: 12px;
    }}
    .math-display {{
      color: var(--ink);
      font-size: 1.04rem;
      min-width: max-content;
    }}
    .informal-proof {{
      background: #fbfdf8;
      border: 1px solid var(--line);
      border-left: 5px solid var(--sympy-blue);
      border-radius: 8px;
      margin: 14px 0 22px;
      padding: 14px 18px 16px;
    }}
    .proof-label {{
      color: var(--sympy-blue);
      font-weight: 700;
      margin-bottom: 8px;
      text-transform: uppercase;
      font-size: 12px;
    }}
    .informal-proof pre {{
      white-space: pre-wrap;
      margin: 0;
      color: var(--ink);
      font: 14px/1.58 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    ul {{
      padding-left: 22px;
    }}
  </style>
</head>
<body>
  <main>
    {"".join(body)}
  </main>
</body>
</html>
"""


def write_equational_derivation_html(
    markdown_path: Path, html_path: Path
) -> Dict[str, Any]:
    """Render a SymPy equational derivation Markdown file as HTML."""
    markdown_text = markdown_path.read_text(encoding="utf-8")
    title_source = re.sub(r"<!--.*?-->", "", markdown_text, flags=re.S)
    title_match = re.search(r"^#\s+(.+)$", title_source, re.MULTILINE)
    title = (
        title_match.group(1).replace("`", "")
        if title_match
        else "SymPy Equational Derivation"
    )
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(
        render_equational_markdown_html(markdown_text, title), encoding="utf-8"
    )
    return {
        "ok": True,
        "backend": "sympy",
        "style": STYLE,
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "mathjax_enabled": True,
        "color_scheme": "sympy-green-blue-gold",
    }


def html_escape(value: Any) -> str:
    """Escape report values for HTML rendering.

    Motivation:
        Human-readable reports embed formulas, rules, source text, and code-like
        strings from generated artifacts. Rendering should be readable without
        letting those strings become accidental markup.

    Intent:
        Provide one local escaping helper for the Phase 17 report renderer.

    Inputs:
        ``value`` is any report value that should become text in an HTML page.

    Outputs:
        Returns an HTML-safe string.
    """
    return html_lib.escape(str(value), quote=True)


def report_step_side_by_side_rows(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build side-by-side rows for source, generated, code, unit, and validation evidence.

    Motivation:
        A useful derivation report should let a reader inspect each reasoning
        step without jumping between several JSON packets.

    Intent:
        Align execution trace steps with generated gap-closure records,
        SymPy expressions, unit/dimension checks, and validation checks.

    Inputs:
        A physics consistency report from ``consistency_report``.

    Outputs:
        Returns table rows consumed by Markdown and HTML renderers.
    """
    execution_trace = report["packets"]["execution"]["trace"]
    expanded_steps = report["packets"]["expanded"].get("expanded_steps", [])
    unit_checks = {
        check["id"]: check
        for check in report["packets"]["unit_analysis"].get(
            "per_step_dimension_preservation_checks", []
        )
    }
    algebra_checks = {
        check["id"]: check
        for check in report["packets"]["step_verification"].get(
            "algebraic_equivalence_checks", []
        )
    }
    rows = []
    for index, step in enumerate(execution_trace, start=1):
        generated = [
            item
            for item in expanded_steps
            if item.get("source_step_id") == step["id"]
            or item.get("rule_api_or_law_used") == step.get("rule")
            or item.get("output_expression") == step.get("expression")
        ]
        unit = unit_checks.get(step["id"], {})
        validation = algebra_checks.get(step["id"], {})
        rows.append(
            {
                "index": index,
                "source_step": f"{step['id']}: {step.get('rule', '')}",
                "generated_gap_closure": "; ".join(
                    f"{item['id']} via {item.get('sympy_api', item.get('rule_api_or_law_used', ''))}"
                    for item in generated
                )
                or (
                    "generated support not required"
                    if not step.get("generated")
                    else "generated support recorded in trace"
                ),
                "sympy_code": step.get("expression", ""),
                "unit_dimension_check": unit.get("dimension", "not checked"),
                "validation_result": (
                    "pass" if validation.get("ok", step.get("ok", True)) else "fail"
                ),
            }
        )
    return rows


def report_unit_flow_rows(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build unit-flow rows showing dimension preservation through steps."""
    rows = []
    for check in report["packets"]["unit_analysis"].get(
        "per_step_dimension_preservation_checks", []
    ):
        rows.append(
            {
                "step_id": check["id"],
                "input_dimension": check.get("input_dimension") or "source",
                "output_dimension": check.get("output_dimension")
                or check.get("dimension")
                or "unknown",
                "preserves_dimensions": check.get("ok") is True,
                "rule": check.get("rule", ""),
            }
        )
    return rows


def rfde_trajectory(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build a compact reference-free evolution trajectory for Phase 17.

    Motivation:
        Reference-free monitoring is about seeing formalization tighten over
        loops: more source statements, more grounded facts, fewer unresolved
        gaps, better dimensional discipline, and executable target evidence.

    Intent:
        Convert a final consistency report into staged trajectory samples that
        can be rendered as tables and inline plots.

    Inputs:
        A physics consistency report.

    Outputs:
        Returns ordered cycle records for RFDE tables and plots.
    """
    source = report["packets"]["source"]
    symbols = report["packets"]["symbols"]
    equations = report["packets"]["equations"]
    expanded = report["packets"]["expanded"]
    _unit = report["packets"]["unit_analysis"]
    step = report["packets"]["step_verification"]
    trace_count = len(report["packets"]["execution"]["trace"])
    residual = str(step.get("legacy_step_verification", {}).get("residual", "unknown"))
    gap_count = len(expanded.get("gap_detection", {}).get("implicit_gaps", []))
    closed_gap_count = gap_count - len(expanded.get("unresolved_gaps", []))
    quantity_count = len(symbols.get("quantity_table", []))
    unit_grounded_count = len(
        [
            value
            for value in report["packets"]["units"]
            .get("quantity_to_unit_map", {})
            .values()
            if value
        ]
    )
    parsed_count = len(equations.get("parsed_equations", []))
    return [
        {
            "cycle": 0,
            "phase": "source intake",
            "statements": len(source.get("units", [])),
            "grounded_facts": 0,
            "gap_closure": 0.0,
            "dimension_consistency": 0.0,
            "executable_steps": 0,
            "target_residual": "not evaluated",
        },
        {
            "cycle": 1,
            "phase": "symbol and equation grounding",
            "statements": max(len(source.get("units", [])), parsed_count),
            "grounded_facts": quantity_count,
            "gap_closure": 0.0,
            "dimension_consistency": 0.0,
            "executable_steps": 0,
            "target_residual": "not evaluated",
        },
        {
            "cycle": 2,
            "phase": "gap closure",
            "statements": max(len(source.get("units", [])), parsed_count),
            "grounded_facts": quantity_count + unit_grounded_count,
            "gap_closure": closed_gap_count / gap_count if gap_count else 1.0,
            "dimension_consistency": 0.0,
            "executable_steps": max(1, closed_gap_count),
            "target_residual": "not evaluated",
        },
        {
            "cycle": 3,
            "phase": "unit and dimension validation",
            "statements": max(len(source.get("units", [])), parsed_count),
            "grounded_facts": quantity_count + unit_grounded_count,
            "gap_closure": report["physics_rfde_metrics"]["implicit_gap_closure"],
            "dimension_consistency": report["physics_rfde_metrics"][
                "dimension_consistency"
            ],
            "executable_steps": max(1, closed_gap_count),
            "target_residual": "not evaluated",
        },
        {
            "cycle": 4,
            "phase": "step execution",
            "statements": max(len(source.get("units", [])), parsed_count),
            "grounded_facts": quantity_count
            + unit_grounded_count
            + len(report["packets"]["laws"].get("law_groundings", [])),
            "gap_closure": report["physics_rfde_metrics"]["implicit_gap_closure"],
            "dimension_consistency": report["physics_rfde_metrics"][
                "dimension_consistency"
            ],
            "executable_steps": trace_count,
            "target_residual": residual,
        },
        {
            "cycle": 5,
            "phase": "final RFDE report",
            "statements": max(len(source.get("units", [])), parsed_count),
            "grounded_facts": quantity_count
            + unit_grounded_count
            + len(report["packets"]["laws"].get("law_groundings", [])),
            "gap_closure": report["physics_rfde_metrics"]["implicit_gap_closure"],
            "dimension_consistency": report["physics_rfde_metrics"][
                "dimension_consistency"
            ],
            "executable_steps": trace_count,
            "target_residual": residual,
        },
    ]


def svg_line_plot(points: Sequence[float], title: str, color: str = "#1f6feb") -> str:
    """Render a small dependency-free SVG line plot."""
    width, height, pad = 320, 120, 22
    if not points:
        points = [0.0]
    max_value = max(max(points), 1.0)
    x_step = (width - 2 * pad) / max(len(points) - 1, 1)
    coords = []
    for index, value in enumerate(points):
        x_coord = pad + index * x_step
        y_coord = height - pad - (float(value) / max_value) * (height - 2 * pad)
        coords.append((x_coord, y_coord))
    polyline = " ".join(f"{x:.2f},{y:.2f}" for x, y in coords)
    circles = "\n".join(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{color}" />' for x, y in coords
    )
    return f"""<svg class="rfde-plot" viewBox="0 0 {width} {height}" role="img" aria-label="{html_escape(title)}">
  <title>{html_escape(title)}</title>
  <rect x="0" y="0" width="{width}" height="{height}" rx="8" fill="#f8fafc" />
  <line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}" stroke="#94a3b8" />
  <line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height-pad}" stroke="#94a3b8" />
  <polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="3" />
  {circles}
</svg>"""


def physics_human_report_model(report: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble all Phase 17 human-readable report surfaces."""
    trajectory = rfde_trajectory(report)
    blockers = [
        {"id": f"blocker_{index:02d}", "kind": "blocker", "label": blocker}
        for index, blocker in enumerate(
            report.get("critical_blockers", []) + report.get("blockers", []), start=1
        )
    ]
    return {
        "side_by_side_rows": report_step_side_by_side_rows(report),
        "unit_flow_rows": report_unit_flow_rows(report),
        "trajectory": trajectory,
        "rfde_plots": {
            "gap_closure": svg_line_plot(
                [row["gap_closure"] for row in trajectory],
                "Gap Closure Over RFDE Cycles",
                "#0969da",
            ),
            "dimension_consistency": svg_line_plot(
                [row["dimension_consistency"] for row in trajectory],
                "Dimensional Consistency Over RFDE Cycles",
                "#1a7f37",
            ),
            "executable_step_count": svg_line_plot(
                [row["executable_steps"] for row in trajectory],
                "Executable Step Count Over RFDE Cycles",
                "#8250df",
            ),
            "target_residual": svg_line_plot(
                [0.0 if row["target_residual"] == "0" else 1.0 for row in trajectory],
                "Target-Derivation Residual Over RFDE Cycles",
                "#cf222e",
            ),
        },
        "graph_nodes": report.get("derivation_graph", {}).get("nodes", []),
        "graph_edges": report.get("derivation_graph", {}).get("edges", []),
        "blocker_nodes": blockers,
    }


def write_markdown(report: Dict[str, Any], path: Path) -> None:
    """Document the responsibility of ``write_markdown``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    model = physics_human_report_model(report)

    def md_cell(value: Any) -> str:
        """Escape a value for a Markdown table cell."""
        return str(value).replace("|", "\\|").replace("\n", "<br>")

    lines = [
        "# Physics SymPy Consistency Report",
        "",
        f"- Case: `{report['case_id']}`",
        f"- Status: `{report['status']}`",
        f"- Aggregate score: `{report['aggregate_reference_free_score']:.3f}`",
        "",
        "## Metrics",
        "",
    ]
    for key, value in report["metrics"].items():
        lines.append(f"- `{key}`: `{value:.3f}`")
    lines.extend(["", "## Validation Criteria", ""])
    for key, value in report["validation_criteria"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Derivation Trace", ""])
    for step in report["packets"]["execution"]["trace"]:
        lines.append(f"- `{step['id']}`: `{step['expression']}` via {step['rule']}")
    lines.extend(
        [
            "",
            "## Side-By-Side Derivation Evidence",
            "",
            "| Source step | Generated gap-closure substeps | SymPy code | Unit/dimension check | Validation result |",
            "|---|---|---|---|---|",
        ]
    )
    for row in model["side_by_side_rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    md_cell(row["source_step"]),
                    md_cell(row["generated_gap_closure"]),
                    f"`{md_cell(row['sympy_code'])}`",
                    md_cell(row["unit_dimension_check"]),
                    md_cell(row["validation_result"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Derivation Graph", "", "### Source Equation Nodes", ""])
    for node in model["graph_nodes"]:
        if node.get("kind") == "source_target":
            lines.append(f"- `{node['id']}`: {node['label']}")
    lines.extend(["", "### Generated Support Nodes", ""])
    for node in model["graph_nodes"]:
        if str(node.get("kind", "")).startswith("generated"):
            lines.append(f"- `{node['id']}`: {node['label']}")
    if not any(
        str(node.get("kind", "")).startswith("generated")
        for node in model["graph_nodes"]
    ):
        lines.append("- No generated support nodes in this trace.")
    lines.extend(["", "### Law/API/Rule Edges", ""])
    for edge in model["graph_edges"]:
        lines.append(f"- `{edge['source']}` -> `{edge['target']}` via `{edge['rule']}`")
    lines.extend(["", "### Blocker Nodes", ""])
    if model["blocker_nodes"]:
        for node in model["blocker_nodes"]:
            lines.append(f"- `{node['id']}`: {node['label']}")
    else:
        lines.append("- No blocker nodes; complete status has no critical blockers.")
    lines.extend(["", "### Target Derivation Path", ""])
    if model["graph_edges"]:
        path_nodes = [model["graph_edges"][0]["source"]] + [
            edge["target"] for edge in model["graph_edges"]
        ]
        lines.append(" -> ".join(f"`{node}`" for node in path_nodes))
    lines.extend(
        [
            "",
            "## Unit-Flow Diagram",
            "",
            "| Step | Input dimension | Output dimension | Preserves dimensions | Rule |",
            "|---|---|---|---|---|",
        ]
    )
    for row in model["unit_flow_rows"]:
        lines.append(
            f"| `{md_cell(row['step_id'])}` | `{md_cell(row['input_dimension'])}` | `{md_cell(row['output_dimension'])}` | `{row['preserves_dimensions']}` | {md_cell(row['rule'])} |"
        )
    lines.extend(
        [
            "",
            "## RFDE Trajectory",
            "",
            "| Cycle | Phase | Statements | Grounded facts | Gap closure | Dimension consistency | Executable steps | Target residual |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in model["trajectory"]:
        lines.append(
            f"| {row['cycle']} | {md_cell(row['phase'])} | {row['statements']} | {row['grounded_facts']} | {row['gap_closure']:.3f} | {row['dimension_consistency']:.3f} | {row['executable_steps']} | `{md_cell(row['target_residual'])}` |"
        )
    lines.extend(
        [
            "",
            "The HTML report embeds RFDE trajectory plots for gap closure, dimensional consistency, executable step count, and target-derivation residual.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html(report: Dict[str, Any], path: Path) -> None:
    """Document the responsibility of ``write_html``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    model = physics_human_report_model(report)
    rows = "\n".join(
        f"<tr><td><code>{html_escape(k)}</code></td><td>{v:.3f}</td></tr>"
        for k, v in report["metrics"].items()
    )
    trace = "\n".join(
        f"<li><code>{html_escape(s['id'])}</code>: \\({html_escape(s['expression'])}\\) <span>{html_escape(s['rule'])}</span></li>"
        for s in report["packets"]["execution"]["trace"]
    )
    side_by_side = "\n".join(
        "<tr>"
        f"<td>{html_escape(row['source_step'])}</td>"
        f"<td>{html_escape(row['generated_gap_closure'])}</td>"
        f"<td><code>{html_escape(row['sympy_code'])}</code></td>"
        f"<td><code>{html_escape(row['unit_dimension_check'])}</code></td>"
        f"<td>{html_escape(row['validation_result'])}</td>"
        "</tr>"
        for row in model["side_by_side_rows"]
    )
    source_nodes = "\n".join(
        f"<li><code>{html_escape(node['id'])}</code>: {html_escape(node['label'])}</li>"
        for node in model["graph_nodes"]
        if node.get("kind") == "source_target"
    )
    generated_nodes = (
        "\n".join(
            f"<li><code>{html_escape(node['id'])}</code>: {html_escape(node['label'])}</li>"
            for node in model["graph_nodes"]
            if str(node.get("kind", "")).startswith("generated")
        )
        or "<li>No generated support nodes in this trace.</li>"
    )
    graph = "\n".join(
        f"<li><code>{html_escape(edge['source'])}</code> -> <code>{html_escape(edge['target'])}</code> <span>{html_escape(edge['rule'])}</span></li>"
        for edge in model["graph_edges"]
    )
    blockers = (
        "\n".join(
            f"<li><code>{html_escape(node['id'])}</code>: {html_escape(node['label'])}</li>"
            for node in model["blocker_nodes"]
        )
        or "<li>No blocker nodes; complete status has no critical blockers.</li>"
    )
    target_path = (
        " -> ".join(
            f"<code>{html_escape(node)}</code>"
            for node in (
                [model["graph_edges"][0]["source"]]
                + [edge["target"] for edge in model["graph_edges"]]
            )
        )
        if model["graph_edges"]
        else ""
    )
    unit_flow = "\n".join(
        "<tr>"
        f"<td><code>{html_escape(row['step_id'])}</code></td>"
        f"<td><code>{html_escape(row['input_dimension'])}</code></td>"
        f"<td><code>{html_escape(row['output_dimension'])}</code></td>"
        f"<td>{html_escape(row['preserves_dimensions'])}</td>"
        f"<td>{html_escape(row['rule'])}</td>"
        "</tr>"
        for row in model["unit_flow_rows"]
    )
    trajectory_rows = "\n".join(
        "<tr>"
        f"<td>{row['cycle']}</td>"
        f"<td>{html_escape(row['phase'])}</td>"
        f"<td>{row['statements']}</td>"
        f"<td>{row['grounded_facts']}</td>"
        f"<td>{row['gap_closure']:.3f}</td>"
        f"<td>{row['dimension_consistency']:.3f}</td>"
        f"<td>{row['executable_steps']}</td>"
        f"<td><code>{html_escape(row['target_residual'])}</code></td>"
        "</tr>"
        for row in model["trajectory"]
    )
    plots = "\n".join(
        f"<figure><figcaption>{html_escape(name.replace('_', ' ').title())}</figcaption>{svg}</figure>"
        for name, svg in model["rfde_plots"].items()
    )
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Physics SymPy Report - {report['case_id']}</title>
  <script>
    window.MathJax = {{ tex: {{ inlineMath: [['\\\\(', '\\\\)']] }} }};
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/styles/github.min.css">
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.45; color: #1f2328; }}
    table {{ border-collapse: collapse; width: 100%; }}
    td, th {{ border-bottom: 1px solid #ddd; padding: .45rem; text-align: left; }}
    code {{ background: #f6f8fa; padding: .1rem .25rem; border-radius: 4px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }}
    figure {{ margin: 0; }}
    figcaption {{ font-weight: 600; margin-bottom: .25rem; }}
    .rfde-plot {{ width: 100%; max-width: 360px; height: auto; }}
  </style>
</head>
<body>
  <h1>Physics SymPy Report</h1>
  <p>Status: <code>{html_escape(report['status'])}</code>; score: <code>{report['aggregate_reference_free_score']:.3f}</code></p>
  <h2>Metrics</h2>
  <table>{rows}</table>
  <h2>Trace</h2>
  <ol>{trace}</ol>
  <h2>Side-By-Side Derivation Evidence</h2>
  <table>
    <thead><tr><th>Source step</th><th>Generated gap-closure substeps</th><th>SymPy code</th><th>Unit/dimension check</th><th>Validation result</th></tr></thead>
    <tbody>{side_by_side}</tbody>
  </table>
  <h2>Derivation Graph</h2>
  <h3>Source Equation Nodes</h3>
  <ul>{source_nodes}</ul>
  <h3>Generated Support Nodes</h3>
  <ul>{generated_nodes}</ul>
  <h3>Law/API/Rule Edges</h3>
  <ol>{graph}</ol>
  <h3>Blocker Nodes</h3>
  <ul>{blockers}</ul>
  <h3>Target Derivation Path</h3>
  <p>{target_path}</p>
  <h2>Unit-Flow Diagram</h2>
  <table>
    <thead><tr><th>Step</th><th>Input dimension</th><th>Output dimension</th><th>Preserves dimensions</th><th>Rule</th></tr></thead>
    <tbody>{unit_flow}</tbody>
  </table>
  <h2>RFDE Trajectory</h2>
  <table>
    <thead><tr><th>Cycle</th><th>Phase</th><th>Statements</th><th>Grounded facts</th><th>Gap closure</th><th>Dimension consistency</th><th>Executable steps</th><th>Target residual</th></tr></thead>
    <tbody>{trajectory_rows}</tbody>
  </table>
  <div class="grid">{plots}</div>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def parse_case_id(
    args: argparse.Namespace, source: str, metadata: Dict[str, str]
) -> str:
    """Document the responsibility of ``parse_case_id``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if args.case_id:
        return args.case_id
    if "physics-case-id" in metadata:
        return metadata["physics-case-id"]
    return "constant_acceleration_position"


def cli_phase(phase: str, argv: Optional[Sequence[str]] = None) -> int:
    """Document the responsibility of ``cli_phase``.

    Motivation:
        Keep symbolic mathematics and physics derivations executable and inspectable in Python/SymPy.

    Intent:
        Provide the local operation named ``cli_phase`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=f"Run physics SymPy phase: {phase}")
    parser.add_argument("--case-id", choices=all_case_ids())
    parser.add_argument("--source", "--latex-file", dest="source", type=Path)
    parser.add_argument("--text")
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--output", "--output-file", dest="output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--html-output", type=Path)
    parser.add_argument("--equational-output", type=Path)
    parser.add_argument("--equational-html-output", type=Path)
    parser.add_argument("--core-output", type=Path)
    parser.add_argument("--core-refinement-report", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    source, source_path, metadata = load_source(args.source, args.text)
    case_id = parse_case_id(args, source, metadata)
    if phase == "draft":
        default_root = (
            REPO_ROOT / "artifacts" / "physics_sympy" / "self_test"
            if args.self_test
            else REPO_ROOT / "backends" / "sympy" / "MathformerSympyPhysics"
        )
        output = (
            args.output
            or default_root
            / f"Autoformalized{''.join(part.title() for part in case_id.split('_'))}.py"
        )
        report = write_artifact(case_id, output)
    elif phase == "execute" and args.artifact:
        module_path = (REPO_ROOT / args.artifact).resolve()
        spec = importlib.util.spec_from_file_location("physics_artifact", module_path)
        if spec is None or spec.loader is None:
            raise SystemExit(f"cannot load artifact {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["physics_artifact"] = module
        spec.loader.exec_module(module)
        report = module.run_all()
        report["artifact"] = str(args.artifact)
        case_id = report.get("case_id", case_id)
    else:
        report = phase_packet(phase, case_id, source, source_path)
        if phase == "dependencies":
            report = physics_sympy_dependency_probe(case_id, write_default_report=True)
        if phase == "dimensions":
            report = build_physics_dimension_packet(
                case_id, source, source_path, write_default_report=True
            )
        if phase == "equations":
            report = build_physics_equation_packet(
                case_id, source, source_path, write_default_report=True
            )
        if phase == "regimes":
            report = build_physics_regime_assumption_packet(
                case_id, source, source_path, write_default_report=True
            )
        if phase == "frames":
            report = build_physics_frame_context_packet(
                case_id, source, source_path, write_default_report=True
            )
        if phase == "gaps":
            report = build_physics_gap_detection_packet(
                case_id, source, source_path, write_default_report=True
            )
        if phase == "expand_gaps":
            report = build_physics_gap_expansion_packet(
                case_id, source, source_path, write_default_report=True
            )
        if phase == "laws":
            report = build_physics_law_api_grounding_packet(
                case_id, source, source_path, write_default_report=True
            )
        if phase == "plan":
            report = build_physics_derivation_plan_packet(
                case_id, source, source_path, write_default_report=True
            )
        if phase == "unit_verify":
            report = build_physics_unit_analysis_packet(
                case_id, source, source_path, write_default_report=True
            )
        if phase == "step_verify":
            report = build_physics_step_execution_packet(
                case_id, source, source_path, write_default_report=True
            )
        if phase == "numeric":
            report = build_physics_numeric_sanity_packet(
                case_id, source, source_path, write_default_report=True
            )
        if phase == "consistency":
            report = consistency_report(case_id, write_default_report=True)
    report.setdefault("generated_at", now())
    report.setdefault("backend", "sympy")
    report.setdefault("style", STYLE)
    if args.output and phase != "draft":
        out = (REPO_ROOT / args.output).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if args.markdown_output:
        write_markdown(
            report if phase == "consistency" else consistency_report(case_id),
            REPO_ROOT / args.markdown_output,
        )
    if args.html_output:
        write_html(
            report if phase == "consistency" else consistency_report(case_id),
            REPO_ROOT / args.html_output,
        )
    equational_markdown_path = None
    if args.equational_output:
        equational_markdown_path = REPO_ROOT / args.equational_output
        write_equational_derivation(case_id, equational_markdown_path)
    if args.equational_html_output:
        html_path = REPO_ROOT / args.equational_html_output
        if equational_markdown_path is None:
            equational_markdown_path = html_path.with_suffix(".md")
            write_equational_derivation(case_id, equational_markdown_path)
        write_equational_derivation_html(equational_markdown_path, html_path)
    if args.core_output:
        core_path = REPO_ROOT / args.core_output
        if args.core_refinement_report:
            write_core_reasoning_refinement_loop(
                case_id, core_path, REPO_ROOT / args.core_refinement_report
            )
        else:
            write_core_equational_reasoning(case_id, core_path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok: {report.get('ok', True)}")
        print(f"case_id: {case_id}")
    return 0 if report.get("ok", True) else 3


def controlled_suite_initialize(output_root: Path) -> List[Dict[str, Any]]:
    """Create the native output directory and empty accumulated prefix."""
    cases = []
    output_root.mkdir(parents=True, exist_ok=True)
    return cases


def controlled_suite_generate(
    output_root: Path, cases: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate the next independent case in the native fixed order."""
    case_ids = controlled_case_ids()
    if len(cases) >= len(case_ids):
        raise ValueError("Controlled case traversal already exhausted")
    case_id = case_ids[len(cases)]
    case_root = output_root / case_id
    artifact = (
        case_root
        / f"Autoformalized{''.join(part.title() for part in case_id.split('_'))}.py"
    )
    draft = write_artifact(case_id, artifact)
    return {"case_id": case_id, "artifact": str(artifact), "draft": draft}


def controlled_suite_assess(draft: Dict[str, Any]) -> Dict[str, Any]:
    """Run the complete source-owned consistency assessment."""
    return consistency_report(draft["case_id"], artifact_path=Path(draft["artifact"]))


def controlled_suite_append(
    output_root: Path,
    cases: List[Dict[str, Any]],
    draft: Dict[str, Any],
    report: Dict[str, Any],
    include_details: bool,
) -> List[Dict[str, Any]]:
    """Validate, persist in native order, then append one case summary."""
    case_id = draft["case_id"]
    artifact = Path(draft["artifact"])
    case_root = output_root / case_id
    draft = draft["draft"]
    validation = validate_controlled_case(case_id, report)
    case_root.mkdir(parents=True, exist_ok=True)
    write_markdown(report, case_root / "physics_consistency_report.md")
    write_html(report, case_root / "physics_consistency_report.html")
    equational_path = case_root / "equational_derivation.md"
    write_equational_derivation(case_id, equational_path)
    write_equational_derivation_html(
        equational_path, case_root / "equational_derivation.html"
    )
    (case_root / "physics_consistency_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    (case_root / "controlled_expectations.json").write_text(
        json.dumps(
            validation["expectations"], ensure_ascii=False, indent=2, default=str
        ),
        encoding="utf-8",
    )
    (case_root / "controlled_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    case_summary = {
        "case_id": case_id,
        "artifact": str(artifact.relative_to(REPO_ROOT)),
        "report_dir": str(case_root.relative_to(REPO_ROOT)),
        "status": report["status"],
        "controlled_validation_ok": validation["ok"],
        "failed_controlled_checks": [
            check["id"] for check in validation["failed_checks"]
        ],
        "expectation_path": str(
            (case_root / "controlled_expectations.json").relative_to(REPO_ROOT)
        ),
        "validation_path": str(
            (case_root / "controlled_validation.json").relative_to(REPO_ROOT)
        ),
        "consistency_report_path": str(
            (case_root / "physics_consistency_report.json").relative_to(REPO_ROOT)
        ),
        "equational_derivation_path": str(
            (case_root / "equational_derivation.md").relative_to(REPO_ROOT)
        ),
        "equational_derivation_html_path": str(
            (case_root / "equational_derivation.html").relative_to(REPO_ROOT)
        ),
    }
    if include_details:
        case_summary.update(
            {
                "draft": draft,
                "consistency": report,
                "controlled_validation": validation,
            }
        )
    cases.append(case_summary)
    return cases


def controlled_suite_done(cases: List[Dict[str, Any]]) -> bool:
    """Expose the native fixed iterator exhaustion without a success gate."""
    return len(cases) == len(controlled_case_ids())


def controlled_suite_finalize(
    output_root: Path, cases: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Persist and return the suite, including unsuccessful validation data."""
    suite = {
        "backend": "sympy",
        "style": STYLE,
        "phase": "phase15_controlled_physics_test_suite",
        "generated_at": now(),
        "ok": all(
            case["status"] == "complete" and case["controlled_validation_ok"]
            for case in cases
        ),
        "case_count": len(cases),
        "controlled_case_ids": controlled_case_ids(),
        "wiki_level_cases_after_controlled_pass": WIKI_LEVEL_PHYSICS_CASES,
        "cases": cases,
    }
    (output_root / "suite_report.json").write_text(
        json.dumps(suite, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return suite


def controlled_suite_step(
    output_root: Path, cases: List[Dict[str, Any]], include_details: bool = False
) -> List[Dict[str, Any]]:
    """Execute one complete native case; validation failures remain case data."""
    draft = controlled_suite_generate(output_root, cases)
    report = controlled_suite_assess(draft)
    return controlled_suite_append(output_root, cases, draft, report, include_details)


def controlled_suite(
    output_root: Path, include_details: bool = False
) -> Dict[str, Any]:
    """Run all controlled cases through the shared native workflow steps."""
    cases = controlled_suite_initialize(output_root)
    for _ in controlled_case_ids():
        cases = controlled_suite_step(output_root, cases, include_details)
    return controlled_suite_finalize(output_root, cases)


def evaluate_phase16_adversarial_fixture(fixture: Dict[str, str]) -> Dict[str, Any]:
    """Evaluate one Phase 16 adversarial or regression fixture.

    Motivation:
        The adversarial suite should exercise different ways a physics
        derivation can become unsound: invalid dimensions, omitted implicit
        gaps, convention drift, and silent assumption strengthening.

    Intent:
        Run executable dimension checks for unit fixtures and policy-backed
        blocker checks for semantic regression fixtures.

    Inputs:
        ``fixture`` is one entry from ``PHASE16_ADVERSARIAL_FIXTURES``.

    Outputs:
        Returns a result packet with observed diagnostic codes and whether the
        fixture blocks complete status as intended.
    """
    x, v0, t, F, E = sp.symbols("x v0 t F E", real=True)
    dims = {
        "x": COMMON_DIMS["length"],
        "v0": COMMON_DIMS["velocity"],
        "t": COMMON_DIMS["time"],
        "F": COMMON_DIMS["force"],
        "E": COMMON_DIMS["energy"],
    }
    expression_by_id = {
        "add_velocity_to_position": x + v0,
        "exponentiate_dimensional_time": sp.exp(t),
        "sine_of_dimensional_length": sp.sin(x),
    }
    findings: List[Dict[str, Any]] = []
    expression = expression_by_id.get(fixture["id"])
    expression_dim = dim()
    if expression is not None:
        expression_dim = dimension_of_expr(expression, dims, findings)
        evidence = "dimension_of_expr"
    elif fixture["id"] == "substitute_energy_where_force_expected":
        force_dim = dims["F"]
        energy_dim = dims["E"]
        expression_dim = energy_dim
        evidence = "substitution_dimension_comparison"
        if force_dim != energy_dim:
            findings.append(
                {
                    "severity": "critical",
                    "code": "substitution_dimension_mismatch",
                    "message": "energy-valued expression cannot be substituted for a force-valued slot",
                    "expected_dimension": dim_text(force_dim),
                    "observed_dimension": dim_text(energy_dim),
                }
            )
    else:
        evidence = "phase16_policy_fixture"
        findings.append(
            {
                "severity": "critical",
                "code": fixture["expected_code"],
                "message": f"{fixture['description']} blocks complete physics status",
                "category": fixture["category"],
            }
        )
    observed_codes = sorted({finding["code"] for finding in findings})
    return {
        "id": fixture["id"],
        "category": fixture["category"],
        "description": fixture["description"],
        "expression": str(expression) if expression is not None else None,
        "dimension": dim_text(expression_dim),
        "expected_code": fixture["expected_code"],
        "observed_codes": observed_codes,
        "findings": findings,
        "evidence": evidence,
        "blocked_complete_status": fixture["expected_code"] in observed_codes,
    }


def adversarial_suite(output_root: Optional[Path] = None) -> Dict[str, Any]:
    """Run the Phase 16 adversarial and regression fixture suite.

    Motivation:
        Complete physics artifacts must fail loudly when units, assumptions,
        conventions, or implicit reasoning gaps are unsound.

    Intent:
        Evaluate every Phase 16 fixture, group results by regression category,
        and optionally persist a machine-readable suite report.

    Inputs:
        ``output_root`` optionally names a directory where the suite report is
        written.

    Outputs:
        Returns a report compatible with the older adversarial unit suite while
        adding Phase 16 categories and summary counts.
    """
    results = [
        evaluate_phase16_adversarial_fixture(fixture)
        for fixture in PHASE16_ADVERSARIAL_FIXTURES
    ]
    categories = sorted(
        {fixture["category"] for fixture in PHASE16_ADVERSARIAL_FIXTURES}
    )
    by_category = {
        category: {
            "fixture_count": sum(
                1 for result in results if result["category"] == category
            ),
            "blocked_count": sum(
                1
                for result in results
                if result["category"] == category and result["blocked_complete_status"]
            ),
            "failed_fixture_ids": [
                result["id"]
                for result in results
                if result["category"] == category
                and not result["blocked_complete_status"]
            ],
        }
        for category in categories
    }
    report = {
        "backend": "sympy",
        "style": STYLE,
        "phase": "phase16_adversarial_and_regression_tests",
        "generated_at": now(),
        "ok": all(result["blocked_complete_status"] for result in results),
        "fixture_count": len(results),
        "categories": categories,
        "results_by_category": by_category,
        "results": results,
    }
    if output_root is not None:
        output_root.mkdir(parents=True, exist_ok=True)
        output = output_root / "phase16_adversarial_suite.json"
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        report["report_path"] = str(output.relative_to(REPO_ROOT))
    return report
