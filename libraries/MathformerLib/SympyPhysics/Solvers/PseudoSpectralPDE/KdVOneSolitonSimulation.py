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

r"""Pseudo-spectral validation for the KdV one-soliton MathformerLib entry.

Original source URL:
    https://en.wikipedia.org/wiki/Korteweg%E2%80%93De_Vries_equation

Source-aligned validation target:
    The analytic one-soliton for
    \phi_t+\phi_{xxx}-6\phi\phi_x=0
    should remain close to the numerical PDE evolution over a short time.

Generated support note:
    This is not a proof by itself. It is a simulation/instantiation validator
    attached to the symbolic SymPy derivation in `AnalyticSoliton`.
"""

from __future__ import annotations

from typing import Dict

import numpy as np


CASE_ID = "korteweg_de_vries_one_soliton_simulation"
SOLVER_TYPE = "PseudoSpectralPDE"
SOURCE_URL = "https://en.wikipedia.org/wiki/Korteweg%E2%80%93De_Vries_equation"


CLAIM = {
    "backend": "sympy",
    "library": "libraries.MathformerLib.SympyPhysics",
    "solver_type": SOLVER_TYPE,
    "style": "sympy_physics_simulation_validation",
    "case_id": CASE_ID,
    "source_url": SOURCE_URL,
    "statement_nl": "Numerically validate the KdV one-soliton against the source sign convention.",
    "statement_latex": (
        r"\phi_t+\phi_{xxx}-6\phi\phi_x=0,\quad "
        r"\phi(x,t)=-\frac{c}{2}\operatorname{sech}^2"
        r"\left(\frac{\sqrt c}{2}(x-ct-a)\right)"
    ),
}


def sech(z):
    """Numerical hyperbolic secant used by the source soliton profile."""
    return 1.0 / np.cosh(z)


def exact_solution(x, t, c=1.0, a=0.0):
    """Evaluate the source-aligned negative sech-squared KdV soliton."""
    return -0.5 * c * sech(np.sqrt(c) * (x - c * t - a) / 2.0) ** 2


def rhs(phi, wave_numbers):
    """Compute phi_t = -phi_xxx + 6 phi phi_x for the declared sign convention."""
    phihat = np.fft.fft(phi)
    phi_x = np.fft.ifft(1j * wave_numbers * phihat).real
    phi_xxx = np.fft.ifft((1j * wave_numbers) ** 3 * phihat).real
    return -phi_xxx + 6.0 * phi * phi_x


def simulate(lx=80.0, n=256, final_time=0.05, dt=0.001, c=1.0, a=0.0) -> Dict[str, object]:
    """Run a short pseudo-spectral RK4 validation against the exact soliton."""
    x = np.linspace(-lx / 2.0, lx / 2.0, n, endpoint=False)
    dx = lx / n
    wave_numbers = 2.0 * np.pi * np.fft.fftfreq(n, d=dx)
    phi = exact_solution(x, 0.0, c=c, a=a)
    steps = int(round(final_time / dt))
    dt_eff = final_time / steps
    for _ in range(steps):
        k1 = rhs(phi, wave_numbers)
        k2 = rhs(phi + 0.5 * dt_eff * k1, wave_numbers)
        k3 = rhs(phi + 0.5 * dt_eff * k2, wave_numbers)
        k4 = rhs(phi + dt_eff * k3, wave_numbers)
        phi = phi + dt_eff * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
    expected = exact_solution(x, final_time, c=c, a=a)
    error = phi - expected
    return {
        "case_id": CASE_ID,
        "claim": CLAIM,
        "solver_type": SOLVER_TYPE,
        "equation": "phi_t + phi_xxx - 6 phi phi_x = 0",
        "grid": {"lx": lx, "n": n, "dx": dx},
        "time": {"final_time": final_time, "dt": dt_eff, "steps": steps},
        "parameters": {"c": c, "a": a},
        "max_abs_error": float(np.max(np.abs(error))),
        "l2_error": float(np.sqrt(np.mean(error**2))),
        "tolerance": 1e-8,
        "passed": bool(np.max(np.abs(error)) <= 1e-8),
    }


def validate_symbolic() -> Dict[str, object]:
    """Report that symbolic proof is delegated to the analytic soliton entry."""
    return {
        "passed": True,
        "delegated_to": "libraries.MathformerLib.SympyPhysics.Solvers.AnalyticSoliton.KdVOneSoliton",
        "role": "simulation_support",
    }


def validate_numeric_samples() -> Dict[str, object]:
    """Run the default numerical simulation validation."""
    return simulate()


def explain_trace() -> list[Dict[str, object]]:
    """Describe the source-aligned simulation/instantiation trace."""
    return [
        {"step": 1, "kind": "initialization", "rule": "sample exact source soliton at t=0"},
        {"step": 2, "kind": "pde_rhs", "rule": "Fourier pseudo-spectral derivatives for phi_x and phi_xxx"},
        {"step": 3, "kind": "time_step", "rule": "RK4 integration of phi_t = -phi_xxx + 6 phi phi_x"},
        {"step": 4, "kind": "validation", "rule": "compare numerical state with exact source soliton at final time"},
    ]


def run_all() -> Dict[str, object]:
    """Execute the default simulation validation packet."""
    result = simulate()
    result["symbolic"] = validate_symbolic()
    result["trace"] = explain_trace()
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(run_all(), indent=2))
