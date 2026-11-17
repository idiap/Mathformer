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

"""Critique unit and dimension discipline in Lean physics artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Sequence


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
    if path is None:
        return ""
    return path.read_text(encoding="utf-8")


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


def source_has_units(text: str) -> bool:
    """Document the responsibility of ``source_has_units``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``source_has_units`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return bool(
        re.search(
            r"\b(unit|dimension|meter|metre|second|kilogram|newton|joule|volt|tesla|ampere|length|time|mass|velocity|force|energy|momentum)\b",
            text,
            re.I,
        )
    )


def source_has_vectors(text: str) -> bool:
    """Document the responsibility of ``source_has_vectors``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``source_has_vectors`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return bool(
        re.search(
            r"\b(vector|field|curl|divergence|gradient|cross)\b|\\vec|\\times|×",
            text,
            re.I,
        )
    )


def build_report(
    *,
    source_text: str,
    lean_text: str,
    type_packet: dict[str, Any],
    unit_report: dict[str, Any],
) -> dict[str, Any]:
    """Document the responsibility of ``build_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings: list[dict[str, Any]] = []
    has_units = source_has_units(source_text)
    has_vectors = source_has_vectors(source_text)
    lean_has_dim = bool(
        re.search(r"\b(PhysDim|Quantity|VectorQuantity|Unit|Dimension)\b", lean_text)
    )
    lean_has_projection = bool(
        re.search(
            r"\b(project|projection|coord|coordinate|toReal|scalar)\b", lean_text, re.I
        )
    )
    lean_raw_real = len(re.findall(r"\b(Real|Float|Rat)\b", lean_text))
    lean_has_unit_lemma = bool(
        re.search(r"\b(unit|dimension|dim|compatible|homogeneous)\b", lean_text, re.I)
    )
    type_text = json.dumps(type_packet, ensure_ascii=False)
    packet_has_dim = (
        "PhysDim" in type_text
        or "Quantity" in type_text
        or "dimension" in type_text.lower()
    )
    packet_has_vector = (
        "VectorQuantity" in type_text
        or "vector" in type_text.lower()
        or "field" in type_text.lower()
    )

    if has_units and not (lean_has_dim or packet_has_dim):
        findings.append(
            {
                "severity": "critical",
                "code": "missing_dimension_policy",
                "message": "Source appears dimensioned, but neither Lean nor type packet exposes a dimension policy.",
            }
        )
    if has_units and lean_raw_real >= 3 and not lean_has_projection:
        findings.append(
            {
                "severity": "critical",
                "code": "raw_real_without_projection_bridge",
                "message": "Physical quantities appear represented as raw scalar values without projection lemmas.",
            }
        )
    if has_vectors and not (
        packet_has_vector or "VectorQuantity" in lean_text or "Vector" in lean_text
    ):
        findings.append(
            {
                "severity": "critical",
                "code": "vector_dimension_erasure",
                "message": "Vector or field source structure lacks a visible vector quantity or projection discipline.",
            }
        )
    if has_units and not lean_has_unit_lemma:
        findings.append(
            {
                "severity": "error",
                "code": "missing_unit_obligations",
                "message": "Lean artifact does not visibly attach unit or dimension obligations to transformations.",
            }
        )
    if unit_report.get("status") in {"fail", "blocked"}:
        findings.append(
            {
                "severity": "critical",
                "code": "unit_report_blocking",
                "message": "Provided unit report has blocking status.",
            }
        )
    if not unit_report and has_units:
        findings.append(
            {
                "severity": "error",
                "code": "missing_unit_report",
                "message": "Dimensioned source claim lacks a unit report.",
            }
        )

    severity_rank = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    max_severity = max(
        (severity_rank[item["severity"]] for item in findings), default=0
    )
    status = "fail" if max_severity >= 2 else "warn" if max_severity == 1 else "pass"
    return {
        "style": "physics_lean_dimension_critic_report",
        "status": status,
        "features": {
            "source_has_units": has_units,
            "source_has_vectors": has_vectors,
            "lean_has_dimension_surface": lean_has_dim,
            "lean_raw_real_count": lean_raw_real,
            "lean_has_projection_bridge": lean_has_projection,
            "lean_has_unit_lemma_signal": lean_has_unit_lemma,
        },
        "findings": findings,
        "codex_exec_probe_seeds": [
            "Generate a unit-system substitution test for the Lean theorem and identify missing dimension hypotheses.",
            "Generate a coordinate projection stress test for any vector equation in the source.",
            "Try to rewrite the theorem as dimensionless scalar algebra and identify what physical content is lost.",
        ],
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
    parser.add_argument("--lean-file", type=Path)
    parser.add_argument("--lean-text")
    parser.add_argument("--type-packet", type=Path)
    parser.add_argument("--unit-report", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
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
        report = build_report(
            source_text="Force equals mass times acceleration with units newton, kilogram, meter, and second.",
            lean_text="theorem bad (F m a : Real) : F = m * a := by sorry",
            type_packet={},
            unit_report={},
        )
        assert report["status"] == "fail"
        assert any(
            item["code"] == "missing_dimension_policy" for item in report["findings"]
        )
    else:
        report = build_report(
            source_text=read_text(args.source_file, args.source_text),
            lean_text=read_text(args.lean_file, args.lean_text),
            type_packet=load_json(args.type_packet),
            unit_report=load_json(args.unit_report),
        )
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
