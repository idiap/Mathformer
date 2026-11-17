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

"""Execute a generated SymPy artifact and persist the validation report."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

PLACEHOLDERS = ["TODO", "pass  #", "NotImplemented", "mock", "stub"]


def load_module(path: Path) -> Any:
    """Document the responsibility of ``load_module``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def placeholder_hits(path: Path) -> list[str]:
    """Document the responsibility of ``placeholder_hits``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``placeholder_hits`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = path.read_text(encoding="utf-8")
    return [needle for needle in PLACEHOLDERS if needle in text]


def execute(path: Path, max_n: int) -> dict[str, Any]:
    """Document the responsibility of ``execute``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``execute`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    module = load_module(path)
    symbolic = module.validate_symbolic()
    numeric = module.validate_numeric_samples(max_n=max_n)
    trace = module.explain_trace()
    hits = placeholder_hits(path)
    return {
        "backend": "sympy",
        "artifact": str(path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claim": getattr(module, "CLAIM", {}),
        "symbolic": symbolic,
        "numeric": numeric,
        "trace": trace,
        "placeholder_hits": hits,
        "ok": bool(
            symbolic.get("passed") and numeric.get("passed") and trace and not hits
        ),
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
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-n", type=int, default=50)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        args.artifact = Path(
            "backends/sympy/MathformerSympy/AutoformalizedSumFirstOddNumbers.py"
        )
        if not args.artifact.exists():
            subprocess.run([sys.executable, "tests/sympy/run_wiki_case.py"], check=True)
    if args.artifact is None:
        parser.error("--artifact is required unless --self-test is used")

    report = execute(args.artifact, args.max_n)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text if args.json else f"sympy execution ok={report['ok']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
