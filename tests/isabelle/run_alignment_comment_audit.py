#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
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

"""Audit generated Isabelle theories for source alignment and explanatory comments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
THEORY_ROOT = REPO_ROOT / "Isabelle"

REQUIRED_MARKERS = [
    "Original source (NL)",
    "Original source (LaTeX)",
    "Original proof idea (NL)",
    "Formalized target (Isabelle/HOL)",
    "Generated note",
    "Source anchors",
    "Source-backed theorem",
]

PLACEHOLDER_RE = re.compile(r"\b(?:sorry|oops|quickcheck_params)\b")


def rel(path: Path) -> str:
    """Document the responsibility of ``rel``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Provide the local operation named ``rel`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def audit_theory(path: Path) -> dict[str, Any]:
    """Document the responsibility of ``audit_theory``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Provide the local operation named ``audit_theory`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = path.read_text(encoding="utf-8")
    findings: list[dict[str, Any]] = []
    for marker in REQUIRED_MARKERS:
        if marker not in text:
            findings.append({"code": "missing_alignment_marker", "marker": marker})
    placeholders = sorted(set(PLACEHOLDER_RE.findall(text)))
    if placeholders:
        findings.append({"code": "placeholder_marker", "markers": placeholders})
    expected_header = f"theory {path.stem}"
    if expected_header not in text:
        findings.append({"code": "theory_name_mismatch", "expected": expected_header})
    if "imports Main" not in text:
        findings.append({"code": "missing_main_import"})
    if "begin" not in text or not text.rstrip().endswith("end"):
        findings.append({"code": "malformed_theory_boundary"})
    theorem_blocks = re.findall(r"\b(?:theorem|lemma)\s+([A-Za-z0-9_']+)\s*:", text)
    if not theorem_blocks:
        findings.append({"code": "missing_theorem_or_lemma"})
    if "proof" not in text or "qed" not in text:
        findings.append({"code": "missing_structured_isar_proof"})
    return {
        "path": rel(path),
        "ok": not findings,
        "theorem_count": len(theorem_blocks),
        "placeholder_free": not placeholders,
        "findings": findings,
    }


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
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    theories = sorted(THEORY_ROOT.glob("*.thy")) if THEORY_ROOT.exists() else []
    results = [audit_theory(path) for path in theories]
    report = {
        "ok": bool(results) and all(item["ok"] for item in results),
        "artifact_count": len(results),
        "results": results,
    }
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"ok: {report['ok']}")
        print(f"artifact_count: {report['artifact_count']}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
