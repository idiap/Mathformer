# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Collect reusable Mathformer library components separately from one-off examples and experiments.
#
# Intent:
#   Expose promoted code and documentation surfaces that other workflows can depend on.
#
# Function:
#   Defines library modules, helpers, and symbolic examples used by tests and generated docs.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

r"""MathformerLib SymPy derivation for the KdV one-soliton solution.

Original source URL:
    https://en.wikipedia.org/wiki/Korteweg%E2%80%93De_Vries_equation

Original source task (NL):
    Verify the Korteweg-De Vries one-soliton against the KdV sign convention.

Original source task (LaTeX):
    \phi_t+\phi_{xxx}-6\phi\phi_x=0,
    \phi(x,t)=-\frac{c}{2}\operatorname{sech}^2
    \left(\frac{\sqrt c}{2}(x-ct-a)\right)

The source convention used by this artifact is

    phi_t + phi_xxx - 6 phi phi_x = 0.

With c > 0, the one-soliton solution in this sign convention is

    phi(x, t) = -c/2 * sech(sqrt(c) * (x - c*t - a) / 2)**2.

The module verifies the traveling-wave reduction, the integrated ODE, the
parameter constraints, and the PDE residual directly in SymPy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import sympy as sp


STYLE = "sympy_physics_derivation_trace"
SOLVER_TYPE = "AnalyticSoliton"
CASE_ID = "korteweg_de_vries_one_soliton"
SOURCE_URL = "https://en.wikipedia.org/wiki/Korteweg%E2%80%93De_Vries_equation"


CLAIM = {
    "backend": "sympy",
    "library": "libraries.MathformerLib.SympyPhysics",
    "solver_type": SOLVER_TYPE,
    "style": STYLE,
    "case_id": CASE_ID,
    "statement_nl": (
        "For the KdV sign convention phi_t + phi_xxx - 6 phi phi_x = 0, "
        "the traveling-wave one-soliton phi(x,t) = -c/2 sech^2(sqrt(c)(x-c t-a)/2) "
        "solves the equation for c > 0."
    ),
    "statement_latex": (
        r"\phi_t+\phi_{xxx}-6\phi\phi_x=0,\quad "
        r"\phi(x,t)=-\frac{c}{2}\operatorname{sech}^2"
        r"\left(\frac{\sqrt c}{2}(x-ct-a)\right)"
    ),
    "source_url": SOURCE_URL,
    "source_anchors": ["wiki:korteweg_de_vries_equation:kde_definition", "wiki:korteweg_de_vries_equation:one_soliton"],
}


QUANTITY_TABLE = {
    "x": {"meaning": "spatial coordinate", "dimension": "length", "role": "independent variable"},
    "t": {"meaning": "time", "dimension": "time", "role": "independent variable"},
    "phi": {"meaning": "KdV field", "dimension": "normalized field", "role": "dependent variable"},
    "c": {"meaning": "soliton speed", "dimension": "normalized speed", "role": "positive parameter"},
    "a": {"meaning": "phase/translation parameter", "dimension": "length", "role": "real parameter"},
    "z": {"meaning": "traveling-wave coordinate x - c t - a", "dimension": "length", "role": "generated support"},
}


ASSUMPTIONS = ["c > 0", "a real", "rapid decay at spatial infinity", "normalized KdV sign convention"]


DERIVATION_STEPS = [
    {
        "id": "step_01_pde",
        "kind": "source_equation",
        "expression": "phi_t + phi_xxx - 6*phi*phi_x = 0",
        "rule": "source KdV sign convention",
        "source_anchors": CLAIM["source_anchors"],
    },
    {
        "id": "step_02_traveling_wave",
        "kind": "generated_substitution",
        "expression": "phi(x,t) = f(z), z = x - c*t - a",
        "rule": "traveling wave ansatz",
        "source_anchors": [],
        "generated": True,
    },
    {
        "id": "step_03_reduced_ode",
        "kind": "generated_calculus",
        "expression": "-c*f' + f''' - 6*f*f' = 0",
        "rule": "chain rule reduction",
        "source_anchors": [],
        "generated": True,
    },
    {
        "id": "step_04_integrated_ode",
        "kind": "generated_calculus",
        "expression": "f'' - c*f - 3*f**2 = 0",
        "rule": "integrate once using decay boundary condition",
        "source_anchors": [],
        "generated": True,
    },
    {
        "id": "step_05_sech_ansatz",
        "kind": "generated_algebra",
        "expression": "f(z) = -A*sech(B*z)**2",
        "rule": "localized sech-squared ansatz",
        "source_anchors": [],
        "generated": True,
    },
    {
        "id": "step_06_parameter_conditions",
        "kind": "generated_algebra",
        "expression": "B**2 = c/4 and A = c/2",
        "rule": "match constant and sech-squared coefficients",
        "source_anchors": [],
        "generated": True,
    },
    {
        "id": "step_07_target_solution",
        "kind": "target_equation",
        "expression": "-c/2*sech(sqrt(c)*(x-c*t-a)/2)**2",
        "rule": "substitute parameter conditions",
        "source_anchors": CLAIM["source_anchors"],
    },
]


@dataclass(frozen=True)
class KdVSymbols:
    """Document the responsibility of ``KdVSymbols``.

    Motivation:
        Collect reusable Mathformer library components separately from one-off examples and experiments.

    Intent:
        Group related state and behavior so callers can use this part of the libraries/MathformerLib/SympyPhysics/Solvers/AnalyticSoliton workflow through a clear object boundary.

    Function:
        Defines library modules, helpers, and symbolic examples used by tests and generated docs.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """
    x: sp.Symbol
    t: sp.Symbol
    c: sp.Symbol
    a: sp.Symbol
    z: sp.Symbol
    A: sp.Symbol
    B: sp.Symbol


def build_symbols() -> KdVSymbols:
    """Build symbols with assumptions matching the source task."""
    x, t, a, z = sp.symbols("x t a z", real=True)
    c, A, B = sp.symbols("c A B", positive=True)
    return KdVSymbols(x=x, t=t, c=c, a=a, z=z, A=A, B=B)


def sech(arg: Any) -> Any:
    """Use SymPy's hyperbolic secant for the source sech-squared profile."""
    return sp.sech(arg)


def build_traveling_wave_profile() -> Dict[str, Any]:
    """Derive the coefficient conditions for the generated sech-squared ansatz."""
    s = build_symbols()
    profile = -s.A * sech(s.B * s.z) ** 2
    profile_residual = sp.diff(profile, s.z, 2) - s.c * profile - 3 * profile**2
    coefficient_form = sp.simplify(profile_residual / (-profile))
    coefficient_form = sp.expand_trig(coefficient_form.subs(sp.tanh(s.B * s.z) ** 2, 1 - sech(s.B * s.z) ** 2))
    return {
        "symbols": s,
        "profile": profile,
        "integrated_ode_residual": sp.factor(profile_residual),
        "coefficient_form": sp.collect(sp.expand(coefficient_form), sech(s.B * s.z) ** 2),
        "conditions": {s.B**2: s.c / 4, s.A: s.c / 2},
    }


def soliton_expression() -> Any:
    """Return the source-aligned KdV one-soliton expression."""
    s = build_symbols()
    z = s.x - s.c * s.t - s.a
    return -s.c * sech(sp.sqrt(s.c) * z / 2) ** 2 / 2


def pde_residual(expr: Any) -> Any:
    """Compute the KdV PDE residual for the declared source sign convention."""
    s = build_symbols()
    return sp.simplify(sp.diff(expr, s.t) + sp.diff(expr, s.x, 3) - 6 * expr * sp.diff(expr, s.x))


def reduced_ode_residual() -> Any:
    """Check the once-integrated traveling-wave ODE residual."""
    s = build_symbols()
    f = -s.c * sech(sp.sqrt(s.c) * s.z / 2) ** 2 / 2
    return sp.simplify(sp.diff(f, s.z, 2) - s.c * f - 3 * f**2)


def derive_target() -> Any:
    """Compute the target expression from the symbolic derivation."""
    return soliton_expression()


def validate_symbolic() -> bool:
    """Validate both the PDE residual and the reduced ODE residual."""
    return pde_residual(soliton_expression()) == 0 and reduced_ode_residual() == 0


def validate_numeric_samples() -> Dict[str, Any]:
    """Sample the symbolic residual on admissible parameter instances."""
    expr = soliton_expression()
    residual = pde_residual(expr)
    s = build_symbols()
    samples = [
        {s.x: 0.0, s.t: 0.0, s.c: 1.0, s.a: 0.0},
        {s.x: 2.0, s.t: 0.5, s.c: 3.0, s.a: -0.25},
        {s.x: -1.5, s.t: 1.25, s.c: 0.75, s.a: 0.4},
    ]
    evaluations = []
    for sample in samples:
        value = float(sp.N(residual.subs(sample)))
        evaluations.append({"sample": {str(k): v for k, v in sample.items()}, "residual": value, "passed": abs(value) <= 1e-10})
    return {
        "case_id": CASE_ID,
        "kind": "numeric_symbolic_residual_samples",
        "evaluations": evaluations,
        "passed": all(item["passed"] for item in evaluations),
    }


def explain_trace() -> List[Dict[str, Any]]:
    """Return source-backed and generated derivation steps."""
    return DERIVATION_STEPS


def run_all() -> Dict[str, Any]:
    """Execute the full MathformerLib SymPy validation packet."""
    target = derive_target()
    residual = pde_residual(target)
    ode_residual = reduced_ode_residual()
    profile = build_traveling_wave_profile()
    numeric = validate_numeric_samples()
    symbolic_passed = residual == 0 and ode_residual == 0
    return {
        "backend": "sympy",
        "library": "libraries.MathformerLib.SympyPhysics",
        "solver_type": SOLVER_TYPE,
        "style": STYLE,
        "case_id": CASE_ID,
        "claim": CLAIM,
        "assumptions": ASSUMPTIONS,
        "quantity_table": QUANTITY_TABLE,
        "target_expression": str(target),
        "pde_residual": str(residual),
        "reduced_ode_residual": str(ode_residual),
        "profile_residual_before_conditions": str(profile["integrated_ode_residual"]),
        "coefficient_form": str(profile["coefficient_form"]),
        "parameter_conditions": {"B**2": "c/4", "A": "c/2"},
        "derivation_steps": DERIVATION_STEPS,
        "numeric_samples": numeric,
        "validation_criteria": {
            "pde_residual_zero": residual == 0,
            "reduced_ode_residual_zero": ode_residual == 0,
            "numeric_residual_samples_pass": numeric["passed"],
            "source_sign_convention_explicit": True,
            "generated_steps_marked": all(step.get("source_anchors") or step.get("generated") for step in DERIVATION_STEPS),
        },
        "status": "complete" if symbolic_passed and numeric["passed"] else "draft",
        "ok": symbolic_passed and numeric["passed"],
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_all(), indent=2, default=str))
