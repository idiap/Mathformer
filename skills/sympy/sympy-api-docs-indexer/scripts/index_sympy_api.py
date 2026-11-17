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

"""Build a compact local SymPy API index."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import inspect
import json
from pathlib import Path
from typing import Any, Iterable

DEFAULT_MODULES = [
    "sympy",
    "sympy.core",
    "sympy.concrete",
    "sympy.simplify",
    "sympy.polys",
    "sympy.calculus",
    "sympy.matrices",
    "sympy.solvers",
    "sympy.physics.units",
    "sympy.physics.units.systems.si",
    "sympy.physics.vector",
    "sympy.physics.mechanics",
    "sympy.physics.quantum",
    "sympy.vector",
]


def first_paragraph(doc: str | None) -> str:
    """Document the responsibility of ``first_paragraph``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``first_paragraph`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not doc:
        return ""
    paragraphs = [part.strip().replace("\n", " ") for part in doc.split("\n\n")]
    return next((part for part in paragraphs if part), "")


def extract_examples(doc: str | None, limit: int = 4) -> list[str]:
    """Document the responsibility of ``extract_examples``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_examples`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not doc:
        return []
    examples: list[str] = []
    capture = False
    for line in doc.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("examples"):
            capture = True
            continue
        if capture and stripped.startswith(">>>"):
            examples.append(stripped)
        if len(examples) >= limit:
            break
    return examples


def assumption_hints(doc: str | None) -> list[str]:
    """Document the responsibility of ``assumption_hints``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``assumption_hints`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not doc:
        return []
    hints = []
    lowered = doc.lower()
    for word in [
        "integer",
        "positive",
        "nonnegative",
        "real",
        "complex",
        "commutative",
        "finite",
    ]:
        if word in lowered:
            hints.append(word)
    return hints


def related_names(obj: Any) -> list[str]:
    """Document the responsibility of ``related_names``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``related_names`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    names = []
    for attr in ["eval", "doit", "rewrite", "expand", "simplify", "diff"]:
        if hasattr(obj, attr):
            names.append(attr)
    return names


def safe_signature(obj: Any) -> str | None:
    """Document the responsibility of ``safe_signature``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``safe_signature`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    try:
        return str(inspect.signature(obj))
    except Exception:
        return None


def source_hash(obj: Any) -> str | None:
    """Document the responsibility of ``source_hash``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``source_hash`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    try:
        src = inspect.getsource(obj).encode("utf-8")
    except Exception:
        return None
    return hashlib.sha256(src).hexdigest()


def iter_public_objects(module_name: str) -> Iterable[dict[str, Any]]:
    """Document the responsibility of ``iter_public_objects``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``iter_public_objects`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    module = importlib.import_module(module_name)
    for name in sorted(dir(module)):
        if name.startswith("_"):
            continue
        try:
            obj = getattr(module, name)
        except Exception:
            continue
        if not (inspect.isfunction(obj) or inspect.isclass(obj)):
            continue
        obj_module = getattr(obj, "__module__", "")
        if not obj_module.startswith("sympy"):
            continue
        kind = "class" if inspect.isclass(obj) else "function"
        doc = inspect.getdoc(obj)
        yield {
            "name": name,
            "qualified_name": f"{obj_module}.{getattr(obj, '__name__', name)}",
            "module": obj_module,
            "indexed_from": module_name,
            "kind": kind,
            "signature": safe_signature(obj),
            "doc_summary": first_paragraph(doc),
            "examples": extract_examples(doc),
            "assumption_hints": assumption_hints(doc),
            "related": related_names(obj),
            "source_file": inspect.getsourcefile(obj),
            "source_hash": source_hash(obj),
            "docs_url": f"https://docs.sympy.org/latest/search.html?q={name}",
        }


def build_index(module_names: list[str]) -> dict[str, Any]:
    """Document the responsibility of ``build_index``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    import sympy

    objects: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, str]] = []
    for module_name in module_names:
        try:
            for item in iter_public_objects(module_name):
                objects.setdefault(item["qualified_name"], item)
        except Exception as exc:
            errors.append(
                {"module": module_name, "error": f"{type(exc).__name__}: {exc}"}
            )
    return {
        "backend": "sympy",
        "sympy_version": sympy.__version__,
        "sympy_file": getattr(sympy, "__file__", None),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "freshness_key": f"sympy:{sympy.__version__}:{getattr(sympy, '__file__', '')}",
        "modules": module_names,
        "objects": sorted(objects.values(), key=lambda item: item["qualified_name"]),
        "errors": errors,
    }


def main() -> int:
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", action="append", dest="modules")
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/sympy_api/index.json")
    )
    parser.add_argument(
        "--modules-output-dir", type=Path, default=Path("artifacts/sympy_api/modules")
    )
    parser.add_argument(
        "--jsonl-output", type=Path, default=Path("artifacts/sympy_api/index.jsonl")
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    index = build_index(args.modules or DEFAULT_MODULES)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.jsonl_output.parent.mkdir(parents=True, exist_ok=True)
    args.jsonl_output.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in index["objects"]),
        encoding="utf-8",
    )
    args.modules_output_dir.mkdir(parents=True, exist_ok=True)
    by_module: dict[str, list[dict[str, Any]]] = {}
    for item in index["objects"]:
        by_module.setdefault(item["indexed_from"], []).append(item)
    for module_name, objects in by_module.items():
        module_path = args.modules_output_dir / f"{module_name.replace('.', '_')}.json"
        module_path.write_text(
            json.dumps(
                {
                    "backend": "sympy",
                    "sympy_version": index["sympy_version"],
                    "freshness_key": index["freshness_key"],
                    "indexed_from": module_name,
                    "objects": objects,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    if args.self_test:
        names = {item["qualified_name"] for item in index["objects"]}
        required = {
            "sympy.concrete.summations.summation",
            "sympy.simplify.simplify.simplify",
            "sympy.core.symbol.Symbol",
            "sympy.physics.units.quantities.Quantity",
            "sympy.vector.coordsysrect.CoordSys3D",
        }
        missing = sorted(required - names)
        required_fields = {
            "qualified_name",
            "module",
            "kind",
            "signature",
            "doc_summary",
            "examples",
            "assumption_hints",
            "related",
            "source_file",
            "docs_url",
        }
        field_missing = sorted(
            {
                field
                for item in index["objects"][:20]
                for field in required_fields
                if field not in item
            }
        )
        result = {
            "ok": not missing and not field_missing,
            "missing": missing,
            "field_missing": field_missing,
            "object_count": len(index["objects"]),
            "output": str(args.output),
            "modules_output_dir": str(args.modules_output_dir),
            "jsonl_output": str(args.jsonl_output),
        }
        print(json.dumps(result, indent=2, sort_keys=True) if args.json else result)
        return 0 if result["ok"] else 1

    summary = {
        "ok": True,
        "object_count": len(index["objects"]),
        "output": str(args.output),
    }
    print(json.dumps(summary, indent=2, sort_keys=True) if args.json else summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
