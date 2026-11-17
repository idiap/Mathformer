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

"""First-pass physical-semantics critic for Lean physics artifacts."""

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


def add_finding(
    findings: list[dict[str, Any]], severity: str, code: str, message: str
) -> None:
    """Document the responsibility of ``add_finding``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings.append({"severity": severity, "code": code, "message": message})


def has_any(text: str, patterns: Sequence[str]) -> bool:
    """Document the responsibility of ``has_any``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_any`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lower = text.lower()
    return any(pattern.lower() in lower for pattern in patterns)


def packet_text(packet: dict[str, Any]) -> str:
    return json.dumps(packet, ensure_ascii=False) if packet else ""


def module_header_comment(lean_text: str) -> str:
    """Return the first module doc comment when it is the first non-import item."""
    lines = lean_text.splitlines()
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped or stripped.startswith("import "):
            index += 1
            continue
        break
    if index >= len(lines) or not lines[index].lstrip().startswith("/-!"):
        return ""
    collected = []
    while index < len(lines):
        collected.append(lines[index])
        if "-/" in lines[index]:
            break
        index += 1
    return "\n".join(collected)


def build_report(
    *,
    source_text: str,
    lean_text: str,
    type_packet: dict[str, Any],
    assumption_packet: dict[str, Any],
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
    source_physical = has_any(
        source_text,
        [
            "velocity",
            "acceleration",
            "force",
            "mass",
            "energy",
            "momentum",
            "field",
            "charge",
            "current",
            "unit",
            "dimension",
        ],
    )
    source_vector = has_any(
        source_text,
        [
            "vector",
            "field",
            "cross",
            "curl",
            "gradient",
            "divergence",
            "\\vec",
            "\\times",
            "×",
        ],
    )
    source_frame = has_any(
        source_text,
        [
            "frame",
            "coordinate",
            "basis",
            "inertial",
            "observer",
            "gauge",
            "sign convention",
        ],
    )
    source_law = has_any(
        source_text,
        ["newton", "maxwell", "lagrange", "hamilton", "euler", "conservation", "law"],
    )
    source_has_informal_derivation = has_any(
        source_text, ["informal derivation", "question", "show that", "derive"]
    )
    packet_surface = packet_text(type_packet) + "\n" + packet_text(assumption_packet)
    combined_surface = lean_text + "\n" + packet_surface
    has_quantity = bool(
        re.search(
            r"\b(Quantity|PhysDim|Dim|Unit|UnitDimensionCompatible|DimensionCompatible|"
            r"fourierPositionIntegral|fourierDerivativeIntegral|fourierWindowIntegral|"
            r"FourierIntegrationByPartsGrounding)\b",
            combined_surface,
        )
    )
    has_vector_quantity = bool(
        re.search(
            r"\b(VectorQuantity|VectorField|Field|Vector|Fin\s+\d+|EuclideanSpace|"
            r"InnerProductSpace|NormedAddCommGroup|CompleteSpace|Hilbert|Bochner)\b",
            combined_surface,
        )
    )
    has_context = bool(
        re.search(r"\b(PhysicsContext|frame|Frame|Regime|SourceLaw|law)\b", lean_text)
    )
    has_source_law = bool(
        re.search(
            r"\b(SourceLaw|law|Law|newton|maxwell|conservation)\b", lean_text, re.I
        )
    )
    header = module_header_comment(lean_text)
    header_lower = header.lower()
    has_commentary_header = bool(header)
    has_full_informal_header = "informal" in header_lower and (
        "derivation" in header_lower or "target" in header_lower
    )
    has_formal_alignment = bool(
        re.search(
            r"\b(formal alignment|lean proof|maps to|corresponding lean|mirrors these steps|proof block)\b",
            header,
            re.I,
        )
    )
    raw_real_count = len(re.findall(r"\b(Real|Float|Rat|Int)\b", lean_text))
    target_as_axiom = bool(
        re.search(r"^\s*(axiom|constant)\b", lean_text, re.M)
    ) and has_any(lean_text, ["target", "claim", "theorem"])

    packet_features = (
        type_packet.get("features", {}) if isinstance(type_packet, dict) else {}
    )
    packet_declares_vectors = bool(
        packet_features.get("vectors") or packet_features.get("fields")
    )
    packet_declares_context = bool(
        packet_features.get("coordinate_frames") or type_packet.get("lean_surfaces")
    )

    if source_physical and not has_quantity:
        add_finding(
            findings,
            "critical",
            "physical_quantities_erased",
            "Source appears to use dimensioned physical quantities, but the Lean artifact has no visible quantity or dimension surface.",
        )
    if source_vector and not (has_vector_quantity or packet_declares_vectors):
        add_finding(
            findings,
            "critical",
            "vector_structure_erased",
            "Source appears vectorial or field-based, but no Lean vector/field quantity surface is visible.",
        )
    if source_frame and not (has_context or packet_declares_context):
        add_finding(
            findings,
            "error",
            "frame_context_missing",
            "Source mentions frame, coordinate, basis, gauge, or sign context, but the Lean artifact does not expose a physics context.",
        )
    if source_law and not has_source_law:
        add_finding(
            findings,
            "error",
            "law_grounding_missing",
            "Source invokes a physical law or conservation principle, but no law binding is visible in Lean.",
        )
    if source_physical and not has_commentary_header:
        add_finding(
            findings,
            "error",
            "informal_commentary_header_missing",
            "Lean physics artifacts must keep the original informal statement and derivation in a module doc-comment header.",
        )
    if source_has_informal_derivation and not has_full_informal_header:
        add_finding(
            findings,
            "error",
            "full_informal_derivation_not_in_header",
            "The module header does not visibly preserve the original informal derivation or target statement.",
        )
    if source_has_informal_derivation and not has_formal_alignment:
        add_finding(
            findings,
            "error",
            "informal_to_formal_alignment_missing",
            "The module header does not map informal derivation steps to corresponding Lean hypotheses, lemmas, or proof blocks.",
        )
    if source_physical and raw_real_count >= 3 and not has_quantity:
        add_finding(
            findings,
            "critical",
            "raw_scalar_erasure",
            "Multiple raw scalar types appear without a quantity bridge for a physical source claim.",
        )
    if target_as_axiom:
        add_finding(
            findings,
            "critical",
            "target_as_unchecked_constant",
            "Lean artifact may introduce the target claim through an axiom or constant.",
        )
    if not assumption_packet and source_physical:
        add_finding(
            findings,
            "warning",
            "missing_assumption_packet",
            "No assumption packet was provided for a physics artifact.",
        )

    max_severity = max(
        (
            {"info": 0, "warning": 1, "error": 2, "critical": 3}[item["severity"]]
            for item in findings
        ),
        default=0,
    )
    status = "fail" if max_severity >= 2 else "warn" if max_severity == 1 else "pass"
    return {
        "style": "physics_lean_physical_semantics_critic_report",
        "status": status,
        "features": {
            "source_physical": source_physical,
            "source_vector": source_vector,
            "source_frame": source_frame,
            "source_law": source_law,
            "lean_has_quantity_surface": has_quantity,
            "lean_has_vector_surface": has_vector_quantity,
            "lean_has_context_surface": has_context,
            "type_packet_surface_checked": bool(type_packet),
            "assumption_packet_surface_checked": bool(assumption_packet),
            "lean_has_commentary_header": has_commentary_header,
            "lean_has_full_informal_header": has_full_informal_header,
            "lean_has_formal_alignment": has_formal_alignment,
            "raw_real_count": raw_real_count,
        },
        "findings": findings,
        "generative_probe_hints": [
            "Generate an interpretation where scalar erasure makes the Lean theorem true but the source physics false.",
            "Try to reconstruct the missing physical law behind each transformation.",
            "Ask whether a coordinate projection lemma is needed to connect scalar algebra back to the vector claim.",
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
    parser.add_argument("--assumption-packet", type=Path)
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
            source_text="A vector force field obeys Newton's law in an inertial frame.",
            lean_text="theorem bad (F m a : Real) : F = m * a := by sorry",
            type_packet={},
            assumption_packet={},
        )
        assert report["status"] == "fail"
        assert any(
            item["code"] == "vector_structure_erased" for item in report["findings"]
        )
    else:
        report = build_report(
            source_text=read_text(args.source_file, args.source_text),
            lean_text=read_text(args.lean_file, args.lean_text),
            type_packet=load_json(args.type_packet),
            assumption_packet=load_json(args.assumption_packet),
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
