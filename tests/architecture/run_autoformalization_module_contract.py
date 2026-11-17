#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Check the stable APIs extracted from the autoformalization runtimes."""

from __future__ import annotations

import argparse
import ast
import importlib
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

MODULES = {
    "physics_ir": REPO_ROOT / "libraries/MathformerPhysicsLib/physics_ir.py",
    "release_status": REPO_ROOT / "libraries/MathformerPhysicsLib/release_status.py",
    "provenance": REPO_ROOT / "libraries/MathformerPhysicsLib/provenance.py",
    "unit_semantics": REPO_ROOT / "libraries/MathformerPhysicsLib/unit_semantics.py",
    "write_audit": REPO_ROOT / "scripts/workflow_write_audit.py",
}
PUBLIC_APIS = {
    "physics_ir": (
        "PhysicsDerivationIR",
        "from_case_spec",
        "backend_packet",
        "compare_backend_packets",
    ),
    "release_status": ("build_release_status", "validate_release_status"),
    "provenance": ("digest", "release_evidence_staleness"),
    "unit_semantics": (
        "parse_unit",
        "dimensional_expression",
        "validate_unitful_equation",
    ),
    "write_audit": ("snapshot_repository", "audit_snapshots"),
}


def local_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def has_cycle(graph: dict[str, set[str]]) -> bool:
    active: set[str] = set()
    complete: set[str] = set()

    def visit(node: str) -> bool:
        if node in active:
            return True
        if node in complete:
            return False
        active.add(node)
        if any(visit(child) for child in graph[node]):
            return True
        active.remove(node)
        complete.add(node)
        return False

    return any(visit(node) for node in graph)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    loaded: dict[str, Any] = {}
    import_errors: dict[str, str] = {}
    for name in MODULES:
        module_name = (
            f"libraries.MathformerPhysicsLib.{name}"
            if name != "write_audit"
            else "scripts.workflow_write_audit"
        )
        try:
            loaded[name] = importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover - reported as contract evidence
            import_errors[name] = f"{type(exc).__name__}: {exc}"

    api_missing = {
        name: [symbol for symbol in symbols if not hasattr(loaded.get(name), symbol)]
        for name, symbols in PUBLIC_APIS.items()
    }
    api_missing = {name: symbols for name, symbols in api_missing.items() if symbols}

    prefixes = {
        name: (
            "libraries.MathformerPhysicsLib." + name
            if name != "write_audit"
            else "scripts.workflow_write_audit"
        )
        for name in MODULES
    }
    graph = {
        name: {
            child
            for child, module_name in prefixes.items()
            if module_name in local_imports(path)
        }
        for name, path in MODULES.items()
    }
    pipeline_text = (
        REPO_ROOT / "backends/sympy/MathformerPhysicsSympy/pipeline.py"
    ).read_text(encoding="utf-8")
    cases = {
        "modules_import": not import_errors,
        "stable_public_apis": not api_missing,
        "extracted_modules_are_acyclic": not has_cycle(graph),
        "pipeline_facade_emits_shared_ir": "from_case_spec(" in pipeline_text
        and '"physics_ir"' in pipeline_text,
    }
    payload = {
        "schema_version": 1,
        "suite": "autoformalization_module_contract",
        "ok": all(cases.values()),
        "cases": cases,
        "import_errors": import_errors,
        "missing_public_symbols": api_missing,
        "import_graph": {name: sorted(children) for name, children in graph.items()},
    }
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if args.json
        else ("PASS" if payload["ok"] else "FAIL")
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
