#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Verify structural readiness of MathformerPhysicsLib foundation modules."""

from __future__ import annotations

from typing import Any

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MODULES = sorted(
    (REPO_ROOT / "MathformerPhysicsLib" / "Lean" / "Foundations").glob("*.lean")
)
FOUNDATION_INDEX_MODULE = "MathformerPhysicsLib.Lean.Foundations"
BANNED = [r"\bsorry\b", r"\badmit\b", r"^\s*axiom\b", r"Prop\s*:=\s*True"]


def rel(path: Path, repository_root: Path | None = None) -> str:
    """Return repo-relative path."""
    return path.resolve().relative_to(repository_root or REPO_ROOT).as_posix()


def check_module(path: Path, repository_root: Path | None = None) -> dict[str, Any]:
    """Check one module for structural promotion blockers."""
    text = path.read_text(encoding="utf-8")
    blockers = []
    warnings = []
    for pattern in BANNED:
        if re.search(pattern, text, re.M):
            blockers.append(f"banned_pattern:{pattern}")
    if "Mathlib grounding:" not in text:
        blockers.append("missing_mathlib_grounding_comment")
    if "import Mathlib" in text:
        warnings.append("broad_mathlib_import_justified_for_foundation_bootstrap")
    if "/--" not in text:
        blockers.append("missing_declaration_comments")
    return {
        "path": rel(path, repository_root),
        "ok": not blockers,
        "promotion_ready": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "declaration_comment_count": text.count("/--"),
    }


def check_foundation_index_compile(
    repository_root: Path | None = None,
) -> dict[str, Any]:
    """Build the accepted foundation index through Lake."""
    proc = subprocess.run(
        ["lake", "build", FOUNDATION_INDEX_MODULE],
        cwd=repository_root or REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "module": FOUNDATION_INDEX_MODULE,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def initialize_scan(paths: Sequence[Path]) -> dict[str, Any]:
    """Capture the ordered native selection, including repeated paths."""
    return {"paths": [str(path) for path in paths], "cursor": 0, "modules": []}


def scan_next(
    state: dict[str, Any], repository_root: Path | None = None
) -> dict[str, Any]:
    """Visit one module; blockers never terminate the selected traversal."""
    cursor = state["cursor"]
    if type(cursor) is not int or not 0 <= cursor < len(state["paths"]):
        raise ValueError("Scan cursor outside the selected module list")
    if len(state["modules"]) != cursor:
        raise ValueError("Scan results do not match the cursor")
    item = check_module(Path(state["paths"][cursor]), repository_root)
    advanced = {
        "paths": list(state["paths"]),
        "cursor": cursor + 1,
        "modules": [*state["modules"], item],
    }
    return {"state": advanced, "done": advanced["cursor"] == len(advanced["paths"])}


def collect_structure(state: dict[str, Any]) -> dict[str, Any]:
    """Flatten all structural blockers before the compiler boundary."""
    if (
        state["cursor"] != len(state["paths"])
        or len(state["modules"]) != state["cursor"]
    ):
        raise ValueError("Cannot collect an incomplete module traversal")
    modules = state["modules"]
    return {
        "modules": modules,
        "blockers": [
            f"{item['path']}:{blocker}"
            for item in modules
            for blocker in item["blockers"]
        ],
    }


def skip_compile() -> dict[str, Any]:
    return {"ok": True, "skipped": True}


def finalize_report(
    structure: dict[str, Any], index_compile: dict[str, Any]
) -> dict[str, Any]:
    """Combine structure and compilation without inferring proof validity."""
    modules = structure["modules"]
    blockers = list(structure["blockers"])
    if not index_compile["ok"]:
        blockers.append(f"{FOUNDATION_INDEX_MODULE}:compile_failed")
    return {
        "style": "physics_foundation_verification_report",
        "module_count": len(modules),
        "ok": not blockers and bool(modules),
        "promotion_ready_count": sum(1 for item in modules if item["promotion_ready"]),
        "modules": modules,
        "accepted_index_compile": index_compile,
        "blockers": blockers,
        "terminal_state": (
            "verification_passed"
            if not blockers and modules
            else "verification_blocked"
        ),
    }


def build_report(
    paths: list[Path], *, compile_index: bool, repository_root: Path | None = None
) -> dict[str, Any]:
    """Build verification report using the same steps exposed over MCP."""
    state = initialize_scan(paths)
    while state["cursor"] < len(state["paths"]):
        state = scan_next(state, repository_root)["state"]
    structure = collect_structure(state)
    index = (
        check_foundation_index_compile(repository_root)
        if compile_index
        else skip_compile()
    )
    return finalize_report(structure, index)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-index-compile", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def parse_options(argv: Sequence[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    return {
        **vars(args),
        "module": [str(p) for p in args.module],
        "output": str(args.output) if args.output else None,
    }


def select_modules(
    args: dict[str, Any], repository_root: Path | None = None
) -> dict[str, Any]:
    """Resolve CLI paths against cwd, or against an explicit mounted cwd."""
    defaults = (
        DEFAULT_MODULES
        if repository_root is None
        else sorted(
            (repository_root / "MathformerPhysicsLib/Lean/Foundations").glob("*.lean")
        )
    )
    paths = [Path(p) for p in args["module"]] or defaults
    if repository_root is not None:
        paths = [p if p.is_absolute() else repository_root / p for p in paths]
    return {"state": initialize_scan(paths), "has_modules": bool(paths)}


def self_test(repository_root: Path | None = None) -> dict[str, Any]:
    tmp = (
        repository_root or REPO_ROOT
    ) / "artifacts/mathformerphysicslib/foundations/verification_self_test.lean"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(
        "import Mathlib\n\n/-- Mathlib grounding: self-test. -/\ndef okFoundation : Nat := 0\n",
        encoding="utf-8",
    )
    report = build_report([tmp], compile_index=False, repository_root=repository_root)
    assert report["ok"], report
    tmp.unlink()
    return report


def emit_report(
    args: dict[str, Any], report: dict[str, Any], repository_root: Path | None = None
) -> dict[str, Any]:
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args["output"]:
        path = Path(args["output"])
        if repository_root is not None and not path.is_absolute():
            path = repository_root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output + "\n", encoding="utf-8")
    if args["json"] or not args["output"]:
        print(output)
    return {"text": output, "exit_code": 0 if report["ok"] else 1}


def main(argv: Sequence[str] | None = None) -> int:
    """Run structural verification."""
    args = parse_options(argv)
    if args["self_test"]:
        report = self_test()
    else:
        paths = select_modules(args)["state"]["paths"]
        report = build_report(
            [Path(p) for p in paths], compile_index=not args["skip_index_compile"]
        )
    return emit_report(args, report)["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
