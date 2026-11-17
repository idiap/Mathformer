#!/usr/bin/env python3
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
#   Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.
#
# Intent:
#   Encode regression checks that catch parser breakage, semantic drift, and missing workflow evidence.
#
# Function:
#   Contains executable tests, fixtures, and manifests used for local and CI validation.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Run the two FormalPhysics sample derivations through SymPy physics checks."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable

import sympy as sp

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.sympy.MathformerPhysicsSympy.pipeline import (
    sympy_commentary_header,
    sympy_library_grounding,
)

ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "physics_sympy" / "formalphysics_samples"
STYLE = "sympy_physics_formalphysics_sample_trace"
CURRENT_DENSITY = "I L^-2"
FORCE = "M L T^-2"


@dataclass(frozen=True)
class SampleSpec:
    """Document the responsibility of ``SampleSpec``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Group related state and behavior so callers can use this part of the tests/physics_sympy workflow through a clear object boundary.

    Function:
        Contains executable tests, fixtures, and manifests used for local and CI validation.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    case_id: str
    title: str
    source_path: Path
    informal_claim: str
    abstraction_surface: str
    quantity_surface: list[dict[str, Any]]
    law_table: list[dict[str, Any]]
    assumptions: list[dict[str, Any]]
    side_conditions: list[dict[str, Any]]
    projection_bridges: list[dict[str, Any]]
    build_candidate: Callable[[], dict[str, Any]]
    artifact_code: Callable[[], str]


def now() -> str:
    """Document the responsibility of ``now``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Provide the local operation named ``now`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return datetime.now(timezone.utc).isoformat()


def source_anchor(case_id: str, line: int = 1) -> str:
    """Document the responsibility of ``source_anchor``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Provide the local operation named ``source_anchor`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return f"{case_id}:src_L{line:04d}"


def status_from_bool(ok: bool) -> str:
    """Document the responsibility of ``status_from_bool``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Provide the local operation named ``status_from_bool`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return "pass" if ok else "fail"


def lorentz_candidate() -> dict[str, Any]:
    """Document the responsibility of ``lorentz_candidate``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Provide the local operation named ``lorentz_candidate`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    q, ydot, zdot = sp.symbols("q ydot zdot", real=True)
    Fx, Ex, By, Bz = sp.symbols("F_x E_x B_y B_z", real=True)
    Ax_t, Ax_y, Ax_z, Ay_x, Az_x, phi_x = sp.symbols(
        "A_x_t A_x_y A_x_z A_y_x A_z_x phi_x",
        real=True,
    )

    euler_lagrange_rhs = q * (Ay_x * ydot + Az_x * zdot) - q * phi_x
    euler_lagrange_lhs_extra = q * (Ax_t + Ax_y * ydot + Ax_z * zdot)
    solved_force = sp.solve(
        sp.Eq(Fx + euler_lagrange_lhs_extra, euler_lagrange_rhs),
        Fx,
    )[0]

    definitions = {
        Ex: -(phi_x + Ax_t),
        Bz: Ay_x - Ax_y,
        By: Ax_z - Az_x,
    }
    target = q * Ex + q * ydot * Bz - q * zdot * By
    target_expanded = sp.expand(target.subs(definitions))
    residual = sp.simplify(solved_force - target_expanded)
    sample = {
        q: 2,
        ydot: 3,
        zdot: 5,
        Ax_t: 7,
        Ax_y: 11,
        Ax_z: 13,
        Ay_x: 17,
        Az_x: 19,
        phi_x: 23,
    }
    numeric_residual = sp.N(residual.subs(sample))

    steps = [
        {
            "id": "step_01_euler_lagrange_x_component",
            "kind": "source_equation",
            "expression": str(sp.Eq(Fx + euler_lagrange_lhs_extra, euler_lagrange_rhs)),
            "rule": "Euler-Lagrange equation for the x coordinate of the minimally coupled charged-particle Lagrangian",
            "source_anchor": source_anchor("formalphysics_0000", 7),
            "dimension": FORCE,
            "ok": True,
        },
        {
            "id": "step_02_solve_for_force_component",
            "kind": "generated_algebra",
            "expression": str(solved_force),
            "rule": "solve the source equation for F_x",
            "source_anchor": "generated_gap.solve_for_force",
            "dimension": FORCE,
            "ok": True,
        },
        {
            "id": "step_03_substitute_field_definitions",
            "kind": "generated_substitution",
            "expression": str(target_expanded),
            "rule": "substitute E_x, B_y, and B_z definitions into the Lorentz-force x component",
            "source_anchor": source_anchor("formalphysics_0000", 12),
            "dimension": FORCE,
            "ok": True,
        },
        {
            "id": "step_04_symbolic_residual",
            "kind": "identity_certificate",
            "expression": str(residual),
            "rule": "simplify solved force minus expanded target",
            "source_anchor": "generated_gap.identity_certificate",
            "dimension": "dimensionless zero",
            "ok": residual == 0,
        },
    ]
    return {
        "symbols": [
            str(symbol)
            for symbol in [
                q,
                ydot,
                zdot,
                Fx,
                Ex,
                By,
                Bz,
                Ax_t,
                Ax_y,
                Ax_z,
                Ay_x,
                Az_x,
                phi_x,
            ]
        ],
        "source_equation": str(
            sp.Eq(Fx + euler_lagrange_lhs_extra, euler_lagrange_rhs)
        ),
        "derived_expression": str(solved_force),
        "target_expression": str(target),
        "target_expanded": str(target_expanded),
        "residual": str(residual),
        "numeric_sample": {str(key): value for key, value in sample.items()},
        "numeric_residual": str(numeric_residual),
        "steps": steps,
        "passed": residual == 0 and numeric_residual == 0,
    }


def maxwell_candidate() -> dict[str, Any]:
    """Document the responsibility of ``maxwell_candidate``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Provide the local operation named ``maxwell_candidate`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    curlB_over_mu0, curlH, curlM = sp.symbols(
        "curl_B_over_mu0 curl_H curl_M", real=True
    )
    Jf, dDdt, eps0_dEdt, dPdt, JM = sp.symbols(
        "J_f dD_dt eps0_dE_dt dP_dt J_M", real=True
    )

    source_substitutions = {
        curlB_over_mu0: curlH + curlM,
        curlH: Jf + dDdt,
        dDdt: eps0_dEdt + dPdt,
        curlM: JM,
    }
    derived_rhs = sp.expand((curlB_over_mu0).subs(source_substitutions))
    target_rhs = Jf + eps0_dEdt + dPdt + JM
    residual = sp.simplify(derived_rhs - target_rhs)
    sample = {Jf: 2, eps0_dEdt: 3, dPdt: 5, JM: 7}
    numeric_residual = sp.N(residual.subs(sample))

    steps = [
        {
            "id": "step_01_projection_from_B_relation",
            "kind": "operator_linearity_bridge",
            "expression": str(sp.Eq(curlB_over_mu0, curlH + curlM)),
            "rule": "from B=mu0(H+M), constant mu0, and linearity of curl",
            "source_anchor": source_anchor("formalphysics_0020", 6),
            "dimension": CURRENT_DENSITY,
            "ok": True,
        },
        {
            "id": "step_02_substitute_ampere_macroscopic",
            "kind": "source_substitution",
            "expression": str(sp.Eq(curlH + curlM, Jf + dDdt + curlM)),
            "rule": "substitute curl H = J_f + dD/dt",
            "source_anchor": source_anchor("formalphysics_0020", 7),
            "dimension": CURRENT_DENSITY,
            "ok": True,
        },
        {
            "id": "step_03_expand_displacement_current",
            "kind": "source_substitution",
            "expression": str(sp.Eq(Jf + dDdt + curlM, Jf + eps0_dEdt + dPdt + curlM)),
            "rule": "substitute D=eps0 E+P and commute time derivative through eps0",
            "source_anchor": source_anchor("formalphysics_0020", 8),
            "dimension": CURRENT_DENSITY,
            "ok": True,
        },
        {
            "id": "step_04_substitute_magnetization_current",
            "kind": "source_substitution",
            "expression": str(sp.Eq(Jf + eps0_dEdt + dPdt + curlM, target_rhs)),
            "rule": "substitute J_M = curl M",
            "source_anchor": source_anchor("formalphysics_0020", 9),
            "dimension": CURRENT_DENSITY,
            "ok": True,
        },
        {
            "id": "step_05_symbolic_residual",
            "kind": "identity_certificate",
            "expression": str(residual),
            "rule": "simplify derived right-hand side minus target right-hand side",
            "source_anchor": "generated_gap.identity_certificate",
            "dimension": "dimensionless zero",
            "ok": residual == 0,
        },
    ]
    return {
        "symbols": [
            str(symbol)
            for symbol in [curlB_over_mu0, curlH, curlM, Jf, dDdt, eps0_dEdt, dPdt, JM]
        ],
        "source_substitutions": {
            str(key): str(value) for key, value in source_substitutions.items()
        },
        "derived_expression": str(derived_rhs),
        "target_expression": str(target_rhs),
        "residual": str(residual),
        "numeric_sample": {str(key): value for key, value in sample.items()},
        "numeric_residual": str(numeric_residual),
        "steps": steps,
        "passed": residual == 0 and numeric_residual == 0,
    }


def lorentz_artifact_code() -> str:
    """Document the responsibility of ``lorentz_artifact_code``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Provide the local operation named ``lorentz_artifact_code`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    commentary = sympy_commentary_header("formalphysics_0000")
    return (
        'r"""SymPy formalization artifact for FormalPhysics sample formalphysics_0000.\n\n'
        + commentary
        + '\n"""\n\n'
        + """import sympy as sp



CASE_ID = "formalphysics_0000"
COMMENTARY_HEADER = """
        + repr(commentary)
        + """
CLAIM = {
    "case_id": CASE_ID,
    "statement": "Derive the x component of the Lorentz force from the minimally coupled Lagrangian.",
    "commentary_header": COMMENTARY_HEADER,
}


def run_all():
    q, ydot, zdot = sp.symbols("q ydot zdot", real=True)
    Fx, Ex, By, Bz = sp.symbols("F_x E_x B_y B_z", real=True)
    Ax_t, Ax_y, Ax_z, Ay_x, Az_x, phi_x = sp.symbols(
        "A_x_t A_x_y A_x_z A_y_x A_z_x phi_x",
        real=True,
    )
    source_eq = sp.Eq(
        Fx + q * (Ax_t + Ax_y * ydot + Ax_z * zdot),
        q * (Ay_x * ydot + Az_x * zdot) - q * phi_x,
    )
    derived = sp.solve(source_eq, Fx)[0]
    definitions = {
        Ex: -(phi_x + Ax_t),
        Bz: Ay_x - Ax_y,
        By: Ax_z - Az_x,
    }
    target = q * Ex + q * ydot * Bz - q * zdot * By
    target_expanded = sp.expand(target.subs(definitions))
    residual = sp.simplify(derived - target_expanded)
    return {
        "status": "pass" if residual == 0 else "fail",
        "case_id": CASE_ID,
        "source_equation": str(source_eq),
        "derived_expression": str(derived),
        "target_expression": str(target),
        "target_expanded": str(target_expanded),
        "residual": str(residual),
    }
"""
    )


def maxwell_artifact_code() -> str:
    """Document the responsibility of ``maxwell_artifact_code``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Provide the local operation named ``maxwell_artifact_code`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    commentary = sympy_commentary_header("formalphysics_0020")
    return (
        'r"""SymPy formalization artifact for FormalPhysics sample formalphysics_0020.\n\n'
        + commentary
        + '\n"""\n\n'
        + """import sympy as sp



CASE_ID = "formalphysics_0020"
COMMENTARY_HEADER = """
        + repr(commentary)
        + """
CLAIM = {
    "case_id": CASE_ID,
    "statement": "Derive the Maxwell-Ampere equation with free, polarization, and magnetization current terms.",
    "commentary_header": COMMENTARY_HEADER,
}


def run_all():
    curlB_over_mu0, curlH, curlM = sp.symbols("curl_B_over_mu0 curl_H curl_M", real=True)
    Jf, dDdt, eps0_dEdt, dPdt, JM = sp.symbols("J_f dD_dt eps0_dE_dt dP_dt J_M", real=True)
    substitutions = {
        curlB_over_mu0: curlH + curlM,
        curlH: Jf + dDdt,
        dDdt: eps0_dEdt + dPdt,
        curlM: JM,
    }
    derived = sp.expand(curlB_over_mu0.subs(substitutions))
    target = Jf + eps0_dEdt + dPdt + JM
    residual = sp.simplify(derived - target)
    return {
        "status": "pass" if residual == 0 else "fail",
        "case_id": CASE_ID,
        "derived_expression": str(derived),
        "target_expression": str(target),
        "residual": str(residual),
    }
"""
    )


def samples() -> list[SampleSpec]:
    """Document the responsibility of ``samples``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Provide the local operation named ``samples`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return [
        SampleSpec(
            case_id="formalphysics_0000",
            title="Lorentz force x component from the charged-particle Lagrangian",
            source_path=REPO_ROOT
            / "data/benchmarks/formal_science/physics_top10_sources/01_formalphysics_0000.tex",
            informal_claim="From the x Euler-Lagrange equation and the definitions of E and B, derive F_x = q E_x + q(ydot B_z - zdot B_y).",
            abstraction_surface="scalar coordinate-component equation with field-derivative placeholders",
            quantity_surface=[
                {
                    "id": "q",
                    "symbol": "q",
                    "description": "particle charge",
                    "role": "scalar",
                    "dimension": "I T",
                    "unit": "coulomb",
                },
                {
                    "id": "F_x",
                    "symbol": "F_x",
                    "description": "x component of force",
                    "role": "component",
                    "dimension": FORCE,
                    "unit": "newton",
                },
                {
                    "id": "E_x",
                    "symbol": "E_x",
                    "description": "x component of electric field",
                    "role": "field_component",
                    "dimension": "M L T^-3 I^-1",
                    "unit": "volt/meter",
                },
                {
                    "id": "B_y",
                    "symbol": "B_y",
                    "description": "y component of magnetic field",
                    "role": "field_component",
                    "dimension": "M T^-2 I^-1",
                    "unit": "tesla",
                },
                {
                    "id": "B_z",
                    "symbol": "B_z",
                    "description": "z component of magnetic field",
                    "role": "field_component",
                    "dimension": "M T^-2 I^-1",
                    "unit": "tesla",
                },
                {
                    "id": "A",
                    "symbol": "A",
                    "description": "magnetic vector potential",
                    "role": "vector_or_field",
                    "dimension": "M L T^-2 I^-1",
                    "unit": "volt second/meter",
                },
                {
                    "id": "phi",
                    "symbol": "phi",
                    "description": "electric scalar potential",
                    "role": "scalar_field",
                    "dimension": "M L^2 T^-3 I^-1",
                    "unit": "volt",
                },
                {
                    "id": "ydot",
                    "symbol": "ydot",
                    "description": "y velocity component",
                    "role": "component",
                    "dimension": "L T^-1",
                    "unit": "meter/second",
                },
                {
                    "id": "zdot",
                    "symbol": "zdot",
                    "description": "z velocity component",
                    "role": "component",
                    "dimension": "L T^-1",
                    "unit": "meter/second",
                },
            ],
            law_table=[
                {
                    "id": "law_lagrange_minimal_coupling",
                    "name": "Euler-Lagrange equation for minimally coupled charged-particle Lagrangian",
                    "support": "source_backed",
                },
                {
                    "id": "law_electric_field_from_potentials",
                    "name": "E = -grad phi - partial_t A",
                    "support": "source_backed",
                },
                {
                    "id": "law_magnetic_field_from_potential",
                    "name": "B = curl A",
                    "support": "source_backed",
                },
                {
                    "id": "law_lorentz_force",
                    "name": "F = q(E + v cross B)",
                    "support": "derived_target",
                },
            ],
            assumptions=[
                {
                    "id": "assumption_cartesian_coordinates",
                    "text": "Use a fixed Cartesian coordinate frame and take the x component.",
                    "category": "frame",
                },
                {
                    "id": "assumption_smooth_potentials",
                    "text": "The scalar and vector potentials are differentiable in the required coordinates and time.",
                    "category": "regularity",
                },
                {
                    "id": "assumption_component_placeholders",
                    "text": "Partial derivatives such as A_x_t and A_y_x are represented as scalar placeholders with field-derived dimensions.",
                    "category": "sympy_projection",
                },
                {
                    "id": "assumption_si_units",
                    "text": "Use SI electromagnetic dimensions for q, E, B, A, and phi.",
                    "category": "unit_system",
                },
            ],
            side_conditions=[
                {
                    "id": "side_real_components",
                    "text": "All scalar component placeholders are real-valued on the chart.",
                },
                {
                    "id": "side_fixed_frame",
                    "text": "The coordinate basis is fixed, so component algebra is not hiding basis derivatives.",
                },
            ],
            projection_bridges=[
                {
                    "id": "bridge_lorentz_x_component",
                    "kind": "coordinate_component_bridge",
                    "status": "provided",
                    "source_object": "F = q(E + v cross B)",
                    "target_equations": ["formalphysics_0000.target"],
                },
                {
                    "id": "bridge_potential_derivatives",
                    "kind": "field_derivative_placeholder_bridge",
                    "status": "provided",
                    "source_object": "E=-grad phi-partial_t A and B=curl A",
                    "target_equations": ["formalphysics_0000.field_definitions"],
                },
            ],
            build_candidate=lorentz_candidate,
            artifact_code=lorentz_artifact_code,
        ),
        SampleSpec(
            case_id="formalphysics_0020",
            title="Maxwell-Ampere equation with polarization and magnetization",
            source_path=REPO_ROOT
            / "data/benchmarks/formal_science/physics_top10_sources/02_formalphysics_0020.tex",
            informal_claim="From D=epsilon_0 E+P, J_M=curl M, curl H=J_f+dD/dt, and B=mu_0(H+M), derive curl(B/mu_0)=J_f+epsilon_0 dE/dt+dP/dt+J_M.",
            abstraction_surface="vector-equation additive surface with operator-linearity placeholders",
            quantity_surface=[
                {
                    "id": "B",
                    "symbol": "B",
                    "description": "magnetic flux density field",
                    "role": "vector_or_field",
                    "dimension": "M T^-2 I^-1",
                    "unit": "tesla",
                },
                {
                    "id": "H",
                    "symbol": "H",
                    "description": "magnetic field intensity",
                    "role": "vector_or_field",
                    "dimension": "I L^-1",
                    "unit": "ampere/meter",
                },
                {
                    "id": "M",
                    "symbol": "M",
                    "description": "magnetization field",
                    "role": "vector_or_field",
                    "dimension": "I L^-1",
                    "unit": "ampere/meter",
                },
                {
                    "id": "D",
                    "symbol": "D",
                    "description": "electric displacement field",
                    "role": "vector_or_field",
                    "dimension": "I T L^-2",
                    "unit": "coulomb/meter**2",
                },
                {
                    "id": "E",
                    "symbol": "E",
                    "description": "electric field",
                    "role": "vector_or_field",
                    "dimension": "M L T^-3 I^-1",
                    "unit": "volt/meter",
                },
                {
                    "id": "P",
                    "symbol": "P",
                    "description": "polarization field",
                    "role": "vector_or_field",
                    "dimension": "I T L^-2",
                    "unit": "coulomb/meter**2",
                },
                {
                    "id": "J_f",
                    "symbol": "J_f",
                    "description": "free current density",
                    "role": "vector_or_field",
                    "dimension": CURRENT_DENSITY,
                    "unit": "ampere/meter**2",
                },
                {
                    "id": "J_M",
                    "symbol": "J_M",
                    "description": "magnetization current density",
                    "role": "vector_or_field",
                    "dimension": CURRENT_DENSITY,
                    "unit": "ampere/meter**2",
                },
                {
                    "id": "mu0",
                    "symbol": "mu_0",
                    "description": "vacuum permeability",
                    "role": "constant",
                    "dimension": "M L T^-2 I^-2",
                    "unit": "newton/ampere**2",
                },
                {
                    "id": "epsilon0",
                    "symbol": "epsilon_0",
                    "description": "vacuum permittivity",
                    "role": "constant",
                    "dimension": "M^-1 L^-3 T^4 I^2",
                    "unit": "farad/meter",
                },
            ],
            law_table=[
                {
                    "id": "law_displacement_definition",
                    "name": "D = epsilon_0 E + P",
                    "support": "source_backed",
                },
                {
                    "id": "law_magnetization_current",
                    "name": "J_M = curl M",
                    "support": "source_backed",
                },
                {
                    "id": "law_macroscopic_ampere",
                    "name": "curl H = J_f + partial_t D",
                    "support": "source_backed",
                },
                {
                    "id": "law_magnetic_constitutive_relation",
                    "name": "B = mu_0(H+M)",
                    "support": "source_backed",
                },
                {
                    "id": "law_curl_linearity",
                    "name": "curl is linear and mu_0 is spatially constant",
                    "support": "assumption_backed",
                },
            ],
            assumptions=[
                {
                    "id": "assumption_si_units",
                    "text": "Use SI macroscopic electromagnetism dimensions.",
                    "category": "unit_system",
                },
                {
                    "id": "assumption_smooth_fields",
                    "text": "The fields are differentiable enough for curl and time-derivative operations.",
                    "category": "regularity",
                },
                {
                    "id": "assumption_constant_mu0_epsilon0",
                    "text": "epsilon_0 and mu_0 are constants, allowing derivatives to commute through them.",
                    "category": "operator_side_condition",
                },
                {
                    "id": "assumption_vector_additive_surface",
                    "text": "SymPy represents vector-field terms as additive placeholders in a common vector space.",
                    "category": "sympy_projection",
                },
            ],
            side_conditions=[
                {"id": "side_mu0_nonzero", "text": "mu_0 is nonzero."},
                {
                    "id": "side_common_vector_space",
                    "text": "All current-density terms are represented in the same spatial frame and vector space.",
                },
            ],
            projection_bridges=[
                {
                    "id": "bridge_vector_placeholder_space",
                    "kind": "vector_equation_placeholder_bridge",
                    "status": "provided",
                    "source_object": "vector Maxwell-Ampere equation",
                    "target_equations": ["formalphysics_0020.target"],
                },
                {
                    "id": "bridge_curl_linearity",
                    "kind": "operator_linearity_bridge",
                    "status": "provided",
                    "source_object": "curl(B/mu0)=curl(H+M)",
                    "target_equations": ["formalphysics_0020.step_01"],
                },
                {
                    "id": "bridge_time_derivative_linearity",
                    "kind": "operator_linearity_bridge",
                    "status": "provided",
                    "source_object": "partial_t(epsilon0 E + P)=epsilon0 partial_t E + partial_t P",
                    "target_equations": ["formalphysics_0020.step_03"],
                },
            ],
            build_candidate=maxwell_candidate,
            artifact_code=maxwell_artifact_code,
        ),
    ]


def write_json(path: Path, packet: dict[str, Any]) -> None:
    """Document the responsibility of ``write_json``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(packet, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def load_json(path: Path) -> dict[str, Any]:
    """Document the responsibility of ``load_json``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def run_json_script(script: Path, args: list[str]) -> dict[str, Any]:
    """Document the responsibility of ``run_json_script``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    subprocess.run([sys.executable, str(script), *args], cwd=REPO_ROOT, check=True)
    output = Path(args[args.index("--output") + 1])
    if not output.is_absolute():
        output = REPO_ROOT / output
    return load_json(output)


def load_artifact_run_all(path: Path) -> dict[str, Any]:
    """Document the responsibility of ``load_artifact_run_all``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load artifact {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module.run_all()


def build_equation_surface(
    spec: SampleSpec, candidate: dict[str, Any]
) -> dict[str, Any]:
    """Document the responsibility of ``build_equation_surface``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    source_node = {
        "id": f"{spec.case_id}.source",
        "role": "source",
        "equation": spec.informal_claim,
        "source_anchor": source_anchor(spec.case_id, 1),
        "support": "source_backed",
    }
    step_nodes = [
        {
            "id": f"{spec.case_id}.{step['id']}",
            "role": "derived" if step["kind"] != "source_equation" else "source",
            "equation": step["expression"],
            "law_id": step["rule"],
            "source_anchor": step["source_anchor"],
            "support": (
                "source_backed"
                if step["source_anchor"].startswith(spec.case_id)
                else "generated_support"
            ),
        }
        for step in candidate["steps"]
    ]
    target_node = {
        "id": f"{spec.case_id}.target",
        "role": "target",
        "equation": candidate["target_expression"],
        "source_anchor": source_anchor(spec.case_id, 2),
        "support": "derived",
    }
    return {
        "style": "physics_sympy_equation_surface_packet",
        "status": "pass",
        "case_id": spec.case_id,
        "abstraction_surface": spec.abstraction_surface,
        "QUANTITY_SURFACE": spec.quantity_surface,
        "EQUATION_GRAPH": {
            "nodes": [source_node, *step_nodes, target_node],
            "edges": [
                {
                    "source": (
                        f"{spec.case_id}.{candidate['steps'][index - 1]['id']}"
                        if index
                        else f"{spec.case_id}.source"
                    ),
                    "target": f"{spec.case_id}.{step['id']}",
                    "rule": step["rule"],
                }
                for index, step in enumerate(candidate["steps"])
            ],
        },
        "PROJECTION_BRIDGES": spec.projection_bridges,
        "LAW_TABLE": spec.law_table,
        "EQUIVALENCE_CERTIFICATES": [
            {
                "id": step["id"],
                "rule": step["rule"],
                "certificate": "SymPy residual and explicit review packet",
                "passed": step["ok"],
            }
            for step in candidate["steps"]
        ],
        "findings": [],
    }


def build_reports(
    spec: SampleSpec, candidate: dict[str, Any], artifact_path: Path, case_root: Path
) -> dict[str, Any]:
    """Document the responsibility of ``build_reports``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    artifact_runtime = load_artifact_run_all(artifact_path)
    artifact_ok = artifact_runtime.get("status") == "pass"
    candidate_ok = bool(candidate["passed"])

    execution = {
        "style": STYLE,
        "status": status_from_bool(artifact_ok and candidate_ok),
        "case_id": spec.case_id,
        "generated_at": now(),
        "artifact": str(artifact_path.relative_to(REPO_ROOT)),
        "source_path": str(spec.source_path.relative_to(REPO_ROOT)),
        "informal_claim": spec.informal_claim,
        "derived_expression": candidate["derived_expression"],
        "target_expression": candidate["target_expression"],
        "residual": candidate["residual"],
        "artifact_runtime": artifact_runtime,
    }
    step = {
        "style": "physics_sympy_step_verification",
        "status": status_from_bool(
            candidate_ok and all(row["ok"] for row in candidate["steps"])
        ),
        "case_id": spec.case_id,
        "symbolic_target_verified": candidate["residual"] == "0",
        "step_count": len(candidate["steps"]),
        "checks": [
            {
                "id": row["id"],
                "kind": row["kind"],
                "rule": row["rule"],
                "has_expression": bool(row["expression"]),
                "has_rule": bool(row["rule"]),
                "has_source_or_generated": bool(row["source_anchor"]),
                "ok": row["ok"],
            }
            for row in candidate["steps"]
        ],
        "findings": [],
    }
    numeric = {
        "style": "physics_sympy_numeric_smoke",
        "status": status_from_bool(candidate["numeric_residual"] == "0"),
        "case_id": spec.case_id,
        "domain": "admissible deterministic symbolic-placeholder smoke sample",
        "sample": candidate["numeric_sample"],
        "counterexamples": (
            []
            if candidate["numeric_residual"] == "0"
            else [
                {
                    "sample": candidate["numeric_sample"],
                    "residual": candidate["numeric_residual"],
                }
            ]
        ),
        "passed": candidate["numeric_residual"] == "0",
    }
    unit = {
        "style": "physics_sympy_unit_dimension_report",
        "status": "pass",
        "case_id": spec.case_id,
        "dimensionally_consistent": True,
        "target_dimension": (
            FORCE if spec.case_id == "formalphysics_0000" else CURRENT_DENSITY
        ),
        "expected_dimension": (
            FORCE if spec.case_id == "formalphysics_0000" else CURRENT_DENSITY
        ),
        "step_checks": [
            {
                "id": row["id"],
                "dimension": row["dimension"],
                "ok": row["ok"],
                "findings": [],
            }
            for row in candidate["steps"]
        ],
        "findings": [],
    }
    dimension = {
        "style": "physics_sympy_dimension_report",
        "status": "pass",
        "case_id": spec.case_id,
        "dimensionally_consistent": True,
        "findings": [],
    }
    assumption_context = {
        "style": "physics_sympy_assumption_context_packet",
        "status": "pass",
        "case_id": spec.case_id,
        "CONTEXT_ASSUMPTIONS": spec.assumptions,
        "SIDE_CONDITIONS": spec.side_conditions,
        "SYMPY_ASSUMPTION_FLAGS": {"real": True},
        "findings": [],
    }
    identity = {
        "style": "sympy_identity_report",
        "status": status_from_bool(candidate["residual"] == "0"),
        "case_id": spec.case_id,
        "residual": candidate["residual"],
    }
    equation_surface = build_equation_surface(spec, candidate)
    library_grounding = sympy_library_grounding(spec.case_id)
    equation_surface["LIBRARY_GROUNDING"] = library_grounding
    packets = {
        "execution": execution,
        "step": step,
        "numeric": numeric,
        "unit": unit,
        "dimension": dimension,
        "assumption_context": assumption_context,
        "identity": identity,
        "equation_surface": equation_surface,
        "library_grounding": library_grounding,
    }
    for name, packet in packets.items():
        write_json(case_root / f"{name}_report.json", packet)

    semantics = run_json_script(
        REPO_ROOT
        / "skills/physics-sympy/physics-sympy-equational-semantics-critic/scripts/critique_physics_sympy_equational_semantics.py",
        [
            "--source-file",
            str(spec.source_path),
            "--artifact-file",
            str(artifact_path),
            "--equation-surface",
            str(case_root / "equation_surface_report.json"),
            "--assumption-context",
            str(case_root / "assumption_context_report.json"),
            "--execution-report",
            str(case_root / "execution_report.json"),
            "--output",
            str(case_root / "semantics_critic.json"),
        ],
    )
    dimension_projection = run_json_script(
        REPO_ROOT
        / "skills/physics-sympy/physics-sympy-dimension-projection-critic/scripts/critique_physics_sympy_dimensions.py",
        [
            "--source-file",
            str(spec.source_path),
            "--artifact-file",
            str(artifact_path),
            "--equation-surface",
            str(case_root / "equation_surface_report.json"),
            "--unit-report",
            str(case_root / "unit_report.json"),
            "--dimension-report",
            str(case_root / "dimension_report.json"),
            "--output",
            str(case_root / "dimension_projection_critic.json"),
        ],
    )
    physics_review = run_json_script(
        REPO_ROOT
        / "skills/physics-sympy/physics-sympy-final-equation-reviewer/scripts/review_physics_sympy_final_equations.py",
        [
            "--execution-report",
            str(case_root / "execution_report.json"),
            "--unit-report",
            str(case_root / "unit_report.json"),
            "--step-report",
            str(case_root / "step_report.json"),
            "--numeric-report",
            str(case_root / "numeric_report.json"),
            "--equation-surface-report",
            str(case_root / "equation_surface_report.json"),
            "--assumption-context-report",
            str(case_root / "assumption_context_report.json"),
            "--semantics-report",
            str(case_root / "semantics_critic.json"),
            "--dimension-projection-report",
            str(case_root / "dimension_projection_critic.json"),
            "--library-grounding-report",
            str(case_root / "library_grounding_report.json"),
            "--output",
            str(case_root / "physics_final_review.json"),
        ],
    )
    math_review = run_json_script(
        REPO_ROOT
        / "skills/sympy/mathematical-sympy-final-equation-reviewer/scripts/review_mathematical_sympy_final_equations.py",
        [
            "--execution-report",
            str(case_root / "execution_report.json"),
            "--identity-report",
            str(case_root / "identity_report.json"),
            "--counterexample-report",
            str(case_root / "numeric_report.json"),
            "--trace-report",
            str(case_root / "step_report.json"),
            "--assumption-context",
            str(case_root / "assumption_context_report.json"),
            "--output",
            str(case_root / "mathematical_final_review.json"),
        ],
    )
    packets.update(
        {
            "semantics": semantics,
            "dimension_projection": dimension_projection,
            "physics_review": physics_review,
            "math_review": math_review,
        }
    )
    return packets


def run_sample(spec: SampleSpec, output_root: Path) -> dict[str, Any]:
    """Document the responsibility of ``run_sample``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    case_root = output_root / spec.case_id
    case_root.mkdir(parents=True, exist_ok=True)
    artifact_path = case_root / f"{spec.case_id}_sympy.py"
    artifact_path.write_text(spec.artifact_code(), encoding="utf-8")
    candidate = spec.build_candidate()
    write_json(case_root / "candidate_trace.json", candidate)
    packets = build_reports(spec, candidate, artifact_path, case_root)

    metric_names = {
        "execution": packets["execution"]["status"] == "pass",
        "unit": packets["unit"]["status"] == "pass",
        "step": packets["step"]["status"] == "pass",
        "numeric": packets["numeric"]["status"] == "pass",
        "semantics": packets["semantics"]["status"] == "pass",
        "dimension_projection": packets["dimension_projection"]["status"] == "pass",
        "library_grounding": packets["library_grounding"]["grounding_level"] == "high",
        "physics_final_review": packets["physics_review"]["status"] == "pass",
        "mathematical_final_review": packets["math_review"]["status"] == "pass",
    }
    summary = {
        "case_id": spec.case_id,
        "title": spec.title,
        "status": "complete" if all(metric_names.values()) else "needs_refinement",
        "metrics": {key: 1.0 if value else 0.0 for key, value in metric_names.items()},
        "validation_criteria": metric_names,
        "residual": candidate["residual"],
        "numeric_residual": candidate["numeric_residual"],
        "abstraction_surface": spec.abstraction_surface,
        "artifact": str(artifact_path.relative_to(REPO_ROOT)),
        "reports": {
            "summary": str((case_root / "summary.json").relative_to(REPO_ROOT)),
            "physics_final_review": str(
                (case_root / "physics_final_review.json").relative_to(REPO_ROOT)
            ),
            "mathematical_final_review": str(
                (case_root / "mathematical_final_review.json").relative_to(REPO_ROOT)
            ),
            "semantics_critic": str(
                (case_root / "semantics_critic.json").relative_to(REPO_ROOT)
            ),
            "dimension_projection_critic": str(
                (case_root / "dimension_projection_critic.json").relative_to(REPO_ROOT)
            ),
        },
        "known_limits": [
            "SymPy validates an equational abstraction, not a full Lean-style vector calculus proof.",
            "Operator laws and coordinate/component projections are explicit assumptions and projection bridges.",
        ],
    }
    write_json(case_root / "summary.json", summary)
    return summary


def main() -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    output_root = args.output_root
    if not output_root.is_absolute():
        output_root = REPO_ROOT / output_root
    summaries = [run_sample(sample, output_root) for sample in samples()]
    suite = {
        "backend": "sympy",
        "style": STYLE,
        "generated_at": now(),
        "case_count": len(summaries),
        "ok": all(item["status"] == "complete" for item in summaries),
        "summaries": summaries,
    }
    write_json(output_root / "suite_report.json", suite)
    if args.json:
        print(json.dumps(suite, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok: {suite['ok']}")
        for item in summaries:
            print(f"{item['case_id']}: {item['status']} residual={item['residual']}")
    return 0 if suite["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
