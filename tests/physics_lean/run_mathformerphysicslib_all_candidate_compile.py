#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Compile every tracked MathformerPhysicsLib Lean case with fresh evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
LEAN_ROOT = REPO_ROOT / "libraries/MathformerPhysicsLib/Lean"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts/physics_lean/all_candidate_compile/report.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_version(
    command: list[str], *, repository_root: Path = REPO_ROOT
) -> dict[str, Any]:
    result = subprocess.run(
        command, cwd=repository_root, text=True, capture_output=True
    )
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def compile_case(
    path: Path, *, timeout_seconds: int, repository_root: Path = REPO_ROOT
) -> dict[str, Any]:
    command = ["lake", "env", "lean", path.relative_to(repository_root).as_posix()]
    try:
        result = subprocess.run(
            command,
            cwd=repository_root,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
        return {
            "case_id": path.parent.name,
            "path": path.relative_to(repository_root).as_posix(),
            "source_sha256": digest(path),
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "compiled": result.returncode == 0,
            "diagnostic_sha256": hashlib.sha256(
                (result.stdout + "\n" + result.stderr).encode()
            ).hexdigest(),
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or f"timeout after {timeout_seconds}s"
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return {
            "case_id": path.parent.name,
            "path": path.relative_to(repository_root).as_posix(),
            "source_sha256": digest(path),
            "command": command,
            "returncode": None,
            "stdout": stdout,
            "stderr": stderr,
            "compiled": False,
            "timeout": True,
            "diagnostic_sha256": hashlib.sha256(
                (stdout + "\n" + stderr).encode()
            ).hexdigest(),
        }


def discover_cases(repository_root: Path | None = None) -> list[Path]:
    lean_root = (
        LEAN_ROOT
        if repository_root is None
        else repository_root / "libraries/MathformerPhysicsLib/Lean"
    )
    return sorted(lean_root.glob("formalphysics_*/MathformerPhysics.lean"))


def finish_report(
    results: list[dict[str, Any]], output: Path, *, repository_root: Path = REPO_ROOT
) -> dict[str, Any]:
    lean_version = command_version(
        ["lake", "env", "lean", "--version"], repository_root=repository_root
    )
    manifest = repository_root / "lake-manifest.json"
    payload = {
        "schema_version": 1,
        "style": "mathformerphysicslib_all_candidate_compile",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "workflow_executed": True,
        "checks_passed": bool(results) and all(item["compiled"] for item in results),
        "artifact_status": "candidate",
        "library_status": (
            "accepted"
            if results and all(item["compiled"] for item in results)
            else "blocked"
        ),
        "release_ok": False,
        "case_count": len(results),
        "compiled_count": sum(1 for item in results if item["compiled"]),
        "lean_version": lean_version,
        "lake_manifest_sha256": digest(manifest) if manifest.exists() else None,
        "results": results,
    }
    payload["blockers"] = (
        [] if payload["checks_passed"] else ["candidate_compile_failure"]
    )
    payload["terminal_states"] = [] if payload["checks_passed"] else ["compile_failed"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def discover_state(repository_root: Path | None = None) -> dict[str, Any]:
    """Expose the native sorted iterator and its ordered accumulator."""
    return {
        "cases": [str(path) for path in discover_cases(repository_root)],
        "index": 0,
        "results": [],
    }


def compile_next(
    state: dict[str, Any], *, timeout_seconds: int, repository_root: Path
) -> dict[str, Any]:
    return compile_case(
        Path(state["cases"][state["index"]]),
        timeout_seconds=timeout_seconds,
        repository_root=repository_root,
    )


def advance_state(state: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    return {
        **state,
        "index": state["index"] + 1,
        "results": [*state["results"], record],
    }


def empty_state(state: dict[str, Any]) -> dict[str, Any]:
    """Identity projection for the zero-iteration native traversal."""
    if state != {"cases": [], "index": 0, "results": []}:
        raise ValueError("empty stage requires the empty discovery state")
    return state


def run(
    output: Path, *, timeout_seconds: int, repository_root: Path | None = None
) -> dict[str, Any]:
    state = discover_state(repository_root)
    root = REPO_ROOT if repository_root is None else repository_root
    if not state["cases"]:
        state = empty_state(state)
    while state["index"] < len(state["cases"]):
        record = compile_next(
            state, timeout_seconds=timeout_seconds, repository_root=root
        )
        state = advance_state(state, record)
    return finish_report(state["results"], output, repository_root=root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = run(args.output, timeout_seconds=args.timeout_seconds)
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if args.json
        else f"compiled {payload['compiled_count']}/{payload['case_count']}"
    )
    return 0 if payload["checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
