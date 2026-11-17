#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Provide a concrete Rocq validation command that works with or without a local Rocq compiler.
#
# Intent:
#   Separate structural artifact realness checks from optional external proof-assistant execution.
#
# Function:
#   Validates one `.v` file or a directory of `.v` files and runs `rocq compile`/`coqc` when available.
#
# Maintenance Notes:
#   Keep compiler discovery delegated to `MathformerRocq.autoformalize`.

"""Validate and optionally compile Rocq proof scripts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.rocq.MathformerRocq.autoformalize import (  # noqa: E402 - direct-script path setup above
    DEFAULT_OUTPUT_DIR,
    run_external_check,
    self_test,
    utc_now,
    validate_file,
    write_json,
)


def collect_files(path: Path) -> List[Path]:
    """Return Rocq files covered by the validation target.

    Motivation:
        The runner should work for both a single proof artifact and a backend directory.

    Intent:
        Normalize file and directory inputs into a deterministic list of `.v` paths.

    Inputs:
        `path` is the user-provided validation target.

    Outputs:
        Returns sorted Rocq source paths.
    """

    if path.is_file():
        return [path]
    return sorted(path.glob("*.v"))


def run_validation(
    *,
    path: Path,
    compiler_bin: Optional[Path],
    timeout_sec: int,
    require_compiler: bool,
) -> Dict[str, Any]:
    """Validate and optionally compile all Rocq files under a target.

    Motivation:
        Mathformer needs a single report that distinguishes structural success from unavailable external tooling.

    Intent:
        Aggregate per-file structural checks and compiler checks into one backend execution report.

    Inputs:
        `path` selects files, `compiler_bin` optionally overrides discovery, and `require_compiler` controls skip policy.

    Outputs:
        Returns a JSON-serializable execution report.
    """

    files = collect_files(path)
    validations = structural_pass(files)
    external = external_pass(files, compiler_bin=compiler_bin, timeout_sec=timeout_sec)
    return aggregate_validation(
        path=path,
        files=files,
        validations=validations,
        external=external,
        require_compiler=require_compiler,
    )


def structural_pass(files):
    """Visit all files in order, retaining reported structural failures."""
    return [validate_file(file_path) for file_path in files]


def external_pass(files, *, compiler_bin, timeout_sec):
    """Visit all files after structural validation, including failed files."""
    return [
        run_external_check(
            file_path, compiler_bin=compiler_bin, timeout_sec=timeout_sec
        )
        for file_path in files
    ]


def aggregate_validation(*, path, files, validations, external, require_compiler):
    """Pack the native report after both complete, ordered passes."""
    missing_compiler = any(item.get("skipped") for item in external)
    structural_ok = files and all(item["ok"] for item in validations)
    external_ok = all(item["ok"] for item in external) and not (
        require_compiler and missing_compiler
    )
    return {
        "schema_version": 1,
        "skill": "rocq-execution-runner",
        "hook_id": "execute.rocq_initial",
        "generated_at_utc": utc_now(),
        "path": str(path),
        "file_count": len(files),
        "require_compiler": require_compiler,
        "structural_ok": structural_ok,
        "external_ok": external_ok,
        "compiler_available": not missing_compiler,
        "validations": validations,
        "external_checks": external,
        "ok": bool(structural_ok and external_ok),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the Rocq execution runner CLI.

    Motivation:
        Make Rocq validation available to tests, skills, and manual users.

    Intent:
        Parse arguments, run validation or self-test, write reports, and return a clear exit code.

    Inputs:
        `argv` optionally supplies command-line arguments.

    Outputs:
        Returns zero only when validation succeeds under the selected compiler policy.
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--compiler-bin", type=Path)
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--require-compiler", action="store_true")
    parser.add_argument("--report-file", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        payload = self_test()
    else:
        payload = run_validation(
            path=args.path,
            compiler_bin=args.compiler_bin,
            timeout_sec=args.timeout_sec,
            require_compiler=args.require_compiler,
        )
    if args.report_file is not None:
        write_json(args.report_file, payload)
    if args.json or args.self_test:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("PASS" if payload.get("ok") else "FAIL")
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
