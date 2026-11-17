# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Executable SymPy unit-flow semantics tied directly to equations."""

from __future__ import annotations

from typing import Any, Mapping, cast

import sympy as sp
from sympy.physics.units import (
    ampere,
    coulomb,
    joule,
    kelvin,
    kilogram,
    meter,
    mole,
    newton,
    pascal,
    second,
    volt,
)
from sympy.physics.units.systems.si import SI

UNIT_ENV = {
    "1": sp.Integer(1),
    "dimensionless": sp.Integer(1),
    "ampere": ampere,
    "coulomb": coulomb,
    "joule": joule,
    "kelvin": kelvin,
    "kilogram": kilogram,
    "meter": meter,
    "mole": mole,
    "newton": newton,
    "pascal": pascal,
    "second": second,
    "volt": volt,
}


def parse_unit(text: str) -> sp.Expr:
    """Parse the repository's restricted unit grammar without ``eval``."""

    return cast(Any, sp.sympify)(text.replace("^", "**"), locals=UNIT_ENV)


def dimensional_expression(
    expression: sp.Basic, quantity_units: Mapping[str, str]
) -> sp.Expr:
    substitutions = {
        symbol: parse_unit(unit)
        for symbol in expression.free_symbols
        if (unit := quantity_units.get(str(symbol)))
    }
    unitful = expression.xreplace(substitutions)
    return sp.simplify(cast(sp.Expr, SI.get_dimensional_expr(unitful)))


def validate_unitful_equation(
    equation: sp.Basic,
    quantity_units: Mapping[str, str],
) -> dict[str, Any]:
    """Validate equality dimensions and dimensionless function arguments."""

    if not isinstance(equation, sp.Equality):
        raise TypeError("Expected an unevaluated SymPy equality")
    findings: list[dict[str, Any]] = []
    lhs_dimension = dimensional_expression(equation.lhs, quantity_units)
    rhs_dimension = dimensional_expression(equation.rhs, quantity_units)
    dimension_system = SI.get_dimension_system()
    assert dimension_system is not None

    def dependencies(dimension: sp.Expr) -> dict[Any, Any] | None:
        try:
            return dimension_system.get_dimensional_dependencies(dimension)
        except TypeError:
            return None

    lhs_dependencies = dependencies(lhs_dimension)
    rhs_dependencies = dependencies(rhs_dimension)
    if lhs_dependencies != rhs_dependencies:
        findings.append(
            {
                "severity": "high",
                "code": "unitful_equation_dimension_mismatch",
                "lhs_dimension": str(lhs_dimension),
                "rhs_dimension": str(rhs_dimension),
            }
        )
    for function in equation.atoms(sp.Function):
        if function.func not in {sp.exp, sp.sin, sp.cos, sp.tan, sp.log}:
            continue
        for argument in function.args:
            argument_dimension = dimensional_expression(argument, quantity_units)
            if dependencies(argument_dimension):
                findings.append(
                    {
                        "severity": "high",
                        "code": "dimensioned_function_argument",
                        "function": str(function.func),
                        "argument": str(argument),
                        "dimension": str(argument_dimension),
                    }
                )
    return {
        "schema_version": 1,
        "style": "physics_unit_flow_witness",
        "equation": str(equation),
        "lhs_dimension": str(lhs_dimension),
        "rhs_dimension": str(rhs_dimension),
        "validation_kind": "symbolic_sympy_physics_units",
        "ok": not findings,
        "findings": findings,
    }
