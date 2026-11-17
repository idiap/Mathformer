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

"""Audit SymPy-family artifacts for source alignment and explanatory comments."""

from __future__ import annotations

import ast
import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


ARTIFACT_ROOTS = [
    REPO_ROOT / "MathformerSympy",
    REPO_ROOT / "MathformerSympyPhysics",
    REPO_ROOT / "MathformerLib" / "SympyPhysics",
]


REQUIRED_TOP_LEVEL_MARKERS = [
    "source",
    "latex",
]


REQUIRED_API_NAMES = [
    "CLAIM",
    "validate_symbolic",
    "validate_numeric_samples",
    "explain_trace",
]


def read_module(path: Path) -> tuple[ast.Module | None, str, str | None]:
    """Document the responsibility of ``read_module``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return None, text, str(exc)
    return tree, text, None


def assigned_names(tree: ast.Module) -> set[str]:
    """Document the responsibility of ``assigned_names``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Provide the local operation named ``assigned_names`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def function_docs(tree: ast.Module) -> dict[str, str]:
    """Document the responsibility of ``function_docs``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Provide the local operation named ``function_docs`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    docs: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            docs[node.name] = ast.get_docstring(node) or ""
    return docs


def audit_file(path: Path) -> dict[str, Any]:
    """Document the responsibility of ``audit_file``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Provide the local operation named ``audit_file`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    tree, text, parse_error = read_module(path)
    if tree is None:
        return {
            "path": str(path.relative_to(REPO_ROOT)),
            "ok": False,
            "findings": [{"code": "parse_error", "message": parse_error}],
        }
    module_doc = ast.get_docstring(tree) or ""
    names = assigned_names(tree)
    docs = function_docs(tree)
    findings = []
    lowered_doc = module_doc.lower()
    for marker in REQUIRED_TOP_LEVEL_MARKERS:
        if marker not in lowered_doc and marker not in text.lower():
            findings.append(
                {"code": "missing_source_alignment_marker", "marker": marker}
            )
    for name in REQUIRED_API_NAMES:
        if name not in names and name not in docs:
            findings.append({"code": "missing_standard_api", "name": name})
    for name in [name for name in REQUIRED_API_NAMES if name in docs]:
        if not docs[name]:
            findings.append({"code": "missing_function_comment", "name": name})
    if "CLAIM" in names and "statement_latex" not in text and "source_url" not in text:
        findings.append({"code": "claim_lacks_original_task_reference"})
    if "generated support" not in lowered_doc and "generated" not in text.lower():
        findings.append({"code": "missing_generated_support_boundary"})
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "ok": not findings,
        "module_doc_present": bool(module_doc),
        "function_doc_count": sum(1 for value in docs.values() if value),
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
    files = []
    for root in ARTIFACT_ROOTS:
        if root.exists():
            files.extend(
                path for path in root.rglob("*.py") if path.name != "__init__.py"
            )
    results = [audit_file(path) for path in sorted(files)]
    report = {
        "ok": all(item["ok"] for item in results),
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
