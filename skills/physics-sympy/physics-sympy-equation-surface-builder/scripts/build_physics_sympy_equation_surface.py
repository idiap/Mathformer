#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.
#
# Intent:
#   Tell coding agents what context to load, what invariants to preserve, and how to validate their work.
#
# Function:
#   Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Build a first-pass equation surface for SymPy physics derivations."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable, Sequence

PHYSICS_TERMS = [
    "velocity",
    "acceleration",
    "force",
    "mass",
    "energy",
    "momentum",
    "charge",
    "current",
    "field",
    "pressure",
    "temperature",
]

VECTOR_TERMS = [
    "vector",
    "field",
    "curl",
    "gradient",
    "divergence",
    "\\vec",
    "\\times",
    "cross",
    "dot",
]


def load_json(path: Path | None) -> dict[str, Any]:
    """Document the responsibility of ``load_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path | None, inline: str | None) -> str:
    """Document the responsibility of ``read_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if inline is not None:
        return inline
    if path is not None:
        return path.read_text(encoding="utf-8")
    return ""


def as_list(value: Any) -> list[Any]:
    """Document the responsibility of ``as_list``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``as_list`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return [value]


def first_present(packet: dict[str, Any], keys: Iterable[str]) -> Any:
    """Document the responsibility of ``first_present``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``first_present`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    for key in keys:
        if key in packet:
            return packet[key]
    return None


def collect_quantities(
    symbol_packet: dict[str, Any],
    dimension_packet: dict[str, Any],
    unit_packet: dict[str, Any],
) -> list[dict[str, Any]]:
    """Document the responsibility of ``collect_quantities``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``collect_quantities`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    raw = first_present(
        symbol_packet,
        ["quantities", "symbols", "entries", "quantity_table", "QUANTITY_TABLE"],
    )
    dimensions = (
        first_present(
            dimension_packet, ["dimensions", "quantity_dimensions", "entries"]
        )
        or {}
    )
    units = first_present(unit_packet, ["units", "quantity_units", "entries"]) or {}
    quantities: list[dict[str, Any]] = []
    for index, item in enumerate(as_list(raw)):
        if isinstance(item, str):
            name = item
            source = {"symbol": item}
        elif isinstance(item, dict):
            name = str(
                item.get("symbol") or item.get("name") or item.get("id") or f"q{index}"
            )
            source = item
        else:
            name = f"q{index}"
            source = {"raw": item}
        dim = source.get("dimension")
        if dim is None and isinstance(dimensions, dict):
            dim = dimensions.get(name)
        unit = source.get("unit")
        if unit is None and isinstance(units, dict):
            unit = units.get(name)
        role = str(source.get("role") or source.get("kind") or "scalar")
        if any(term in name.lower() for term in ["vec", "field", "vector"]):
            role = "vector_or_field"
        quantities.append(
            {
                "id": name,
                "symbol": name,
                "role": role,
                "dimension": dim,
                "unit": unit,
                "source_anchor": source.get("source_anchor") or source.get("anchor"),
                "support": source.get("support", "source_or_generated"),
            }
        )
    return quantities


def collect_equations(equation_packet: dict[str, Any]) -> list[dict[str, Any]]:
    """Document the responsibility of ``collect_equations``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``collect_equations`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    raw = first_present(
        equation_packet,
        ["equations", "entries", "parsed_equations", "DERIVATION_STEPS"],
    )
    equations: list[dict[str, Any]] = []
    for index, item in enumerate(as_list(raw)):
        if isinstance(item, str):
            expr = item
            source = {"equation": item}
        elif isinstance(item, dict):
            expr = str(
                item.get("equation")
                or item.get("expr")
                or item.get("expression")
                or item.get("output")
                or item
            )
            source = item
        else:
            expr = str(item)
            source = {"raw": item}
        role = str(
            source.get("role")
            or source.get("kind")
            or ("target" if "target" in expr.lower() else "source")
        )
        equations.append(
            {
                "id": str(source.get("id") or f"eq{index}"),
                "role": role,
                "equation": expr,
                "source_anchor": source.get("source_anchor") or source.get("anchor"),
                "law_id": source.get("law_id") or source.get("law"),
                "support": source.get("support", "source_or_generated"),
            }
        )
    return equations


def collect_laws(law_packet: dict[str, Any]) -> list[dict[str, Any]]:
    """Document the responsibility of ``collect_laws``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``collect_laws`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    raw = first_present(law_packet, ["laws", "law_table", "entries", "LAW_TABLE"])
    laws: list[dict[str, Any]] = []
    for index, item in enumerate(as_list(raw)):
        if isinstance(item, str):
            laws.append(
                {"id": f"law{index}", "name": item, "support": "source_or_generated"}
            )
        elif isinstance(item, dict):
            laws.append(
                {
                    "id": str(item.get("id") or item.get("name") or f"law{index}"),
                    "name": str(item.get("name") or item.get("law") or item),
                    "source_anchor": item.get("source_anchor") or item.get("anchor"),
                    "support": item.get("support", "source_or_generated"),
                }
            )
    return laws


def source_has(text: str, terms: Sequence[str]) -> bool:
    """Document the responsibility of ``source_has``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``source_has`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def build_packet(
    *,
    source_text: str,
    symbol_packet: dict[str, Any],
    dimension_packet: dict[str, Any],
    unit_packet: dict[str, Any],
    equation_packet: dict[str, Any],
    frame_packet: dict[str, Any],
    law_packet: dict[str, Any],
    library_grounding_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Document the responsibility of ``build_packet``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    quantities = collect_quantities(symbol_packet, dimension_packet, unit_packet)
    equations = collect_equations(equation_packet)
    laws = collect_laws(law_packet)
    projection_bridges = []
    if any(
        q["role"] in {"vector", "field", "vector_or_field", "operator"}
        for q in quantities
    ):
        if source_has(source_text, VECTOR_TERMS):
            projection_bridges.append(
                {
                    "id": "projection_bridge_0",
                    "kind": "component_or_scalar_projection",
                    "status": "required",
                    "source": "vector_or_field_surface_detected",
                    "target_equations": [
                        eq["id"]
                        for eq in equations
                        if eq["role"] in {"target", "derived"}
                    ],
                }
            )

    findings: list[dict[str, Any]] = []
    if source_has(source_text, PHYSICS_TERMS) and not quantities:
        findings.append(
            {
                "severity": "error",
                "code": "missing_quantity_surface",
                "message": "Source uses physical quantities but no quantity surface entries were provided.",
                "repair_surface": "quantity_surface",
            }
        )
    if source_has(source_text, VECTOR_TERMS) and not projection_bridges:
        findings.append(
            {
                "severity": "warning",
                "code": "projection_bridge_not_established",
                "message": "Source appears vector, field, or operator based; scalar SymPy equations need an explicit projection bridge.",
                "repair_surface": "projection_bridge",
            }
        )
    if equations and not any(eq["role"] == "target" for eq in equations):
        findings.append(
            {
                "severity": "warning",
                "code": "target_equation_not_marked",
                "message": "No equation is explicitly marked as the target.",
                "repair_surface": "equation_parse",
            }
        )
    target_like_sources = [
        eq
        for eq in equations
        if eq["role"] == "source"
        and re.search(r"\b(target|claim|answer)\b", eq["equation"], re.I)
    ]
    if target_like_sources:
        findings.append(
            {
                "severity": "error",
                "code": "target_like_source_equation",
                "message": "A source equation appears target-shaped and must be checked for leakage.",
                "repair_surface": "target_nonleakage",
                "equations": [eq["id"] for eq in target_like_sources],
            }
        )
    library_grounding_packet = library_grounding_packet or {}
    grounding_level = library_grounding_packet.get("grounding_level")
    if grounding_level and grounding_level != "high":
        findings.append(
            {
                "severity": "error",
                "code": "sympy_library_grounding_below_complete_threshold",
                "message": "Physics SymPy equation surface is not maximally grounded in installed library APIs.",
                "repair_surface": "sympy_library_grounding",
                "grounding_level": grounding_level,
                "completion_blockers": library_grounding_packet.get(
                    "completion_blockers", []
                ),
            }
        )

    max_severity = max(
        (
            {"info": 0, "warning": 1, "error": 2, "critical": 3}[f["severity"]]
            for f in findings
        ),
        default=0,
    )
    return {
        "style": "physics_sympy_equation_surface_packet",
        "status": (
            "fail" if max_severity >= 2 else "warn" if max_severity == 1 else "pass"
        ),
        "QUANTITY_SURFACE": quantities,
        "EQUATION_GRAPH": {
            "nodes": equations,
            "edges": [],
            "frame_context": frame_packet,
        },
        "PROJECTION_BRIDGES": projection_bridges,
        "LAW_TABLE": laws,
        "LIBRARY_GROUNDING": library_grounding_packet,
        "metrics": {
            "quantity_count": len(quantities),
            "equation_count": len(equations),
            "law_count": len(laws),
            "projection_bridge_count": len(projection_bridges),
            "library_grounding_level": grounding_level or "missing",
        },
        "findings": findings,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Document the responsibility of ``parse_args``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--source-text")
    parser.add_argument("--symbol-packet", type=Path)
    parser.add_argument("--dimension-packet", type=Path)
    parser.add_argument("--unit-packet", type=Path)
    parser.add_argument("--equation-packet", type=Path)
    parser.add_argument("--frame-packet", type=Path)
    parser.add_argument("--law-packet", type=Path)
    parser.add_argument("--library-grounding-packet", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    args = parse_args(argv)
    if args.self_test:
        packet = build_packet(
            source_text="A vector force field is projected onto x and the target is F_x = m a_x.",
            symbol_packet={
                "quantities": [
                    {"symbol": "F_vec", "role": "vector", "dimension": "force"}
                ]
            },
            dimension_packet={},
            unit_packet={},
            equation_packet={
                "equations": [
                    {"id": "target", "role": "target", "equation": "F_x = m*a_x"}
                ]
            },
            frame_packet={"frame": "cartesian"},
            law_packet={"laws": [{"id": "newton", "name": "Newton second law"}]},
            library_grounding_packet={
                "grounding_level": "high",
                "required_roles": ["scalar_expression_core"],
            },
        )
        assert packet["status"] in {"pass", "warn"}
        assert packet["PROJECTION_BRIDGES"]
        assert packet["LIBRARY_GROUNDING"]["grounding_level"] == "high"
    else:
        packet = build_packet(
            source_text=read_text(args.source_file, args.source_text),
            symbol_packet=load_json(args.symbol_packet),
            dimension_packet=load_json(args.dimension_packet),
            unit_packet=load_json(args.unit_packet),
            equation_packet=load_json(args.equation_packet),
            frame_packet=load_json(args.frame_packet),
            law_packet=load_json(args.law_packet),
            library_grounding_packet=load_json(args.library_grounding_packet),
        )
    output = json.dumps(packet, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
