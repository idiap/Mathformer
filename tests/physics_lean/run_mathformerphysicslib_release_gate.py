#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

"""Gate the promoted MathformerPhysicsLib surface with fresh kernel evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
PUBLIC_ROOT = REPO_ROOT / "libraries/MathformerPhysicsLib.lean"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts/physics_lean/release_gate/report.json"

from libraries.MathformerPhysicsLib.release_status import (
    build_release_status,
)

IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s*$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def imported_files() -> list[Path]:
    files: list[Path] = []
    for line in PUBLIC_ROOT.read_text(encoding="utf-8").splitlines():
        match = IMPORT_RE.match(line)
        if not match:
            continue
        for module in match.group(1).split():
            path = REPO_ROOT / (module.replace(".", "/") + ".lean")
            if path.exists():
                files.append(path)
    return files


def run_command(command: list[str], *, timeout: int = 900) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "command": command,
            "returncode": result.returncode,
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "diagnostic_sha256": hashlib.sha256(
                (result.stdout + "\n" + result.stderr).encode()
            ).hexdigest(),
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or f"timeout after {timeout}s"
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return {
            "command": command,
            "returncode": None,
            "ok": False,
            "timeout": True,
            "stdout": stdout,
            "stderr": stderr,
            "diagnostic_sha256": hashlib.sha256(
                (stdout + "\n" + stderr).encode()
            ).hexdigest(),
        }


def build_public_root() -> dict[str, Any]:
    return run_command(["lake", "build", "MathformerPhysicsLib"])


def check_coherence() -> dict[str, Any]:
    return run_command(
        [
            sys.executable,
            "skills/mathformerphysicslib/mathformerphysicslib-coherence-gate/scripts/gate_coherence.py",
            "--require-release",
            "--json",
        ],
        timeout=180,
    )


def check_lean_version() -> dict[str, Any]:
    return run_command(["lake", "env", "lean", "--version"], timeout=30)


def assess_release(build: dict, coherence: dict, lean_version: dict) -> dict[str, Any]:
    checks_passed = build["ok"] and coherence["ok"] and lean_version["ok"]
    return build_release_status(
        workflow_executed=True,
        checks_passed=checks_passed,
        artifact_status="promoted" if checks_passed else "blocked",
        library_status="accepted" if build["ok"] and coherence["ok"] else "blocked",
        blockers=[
            blocker
            for blocker, failed in (
                ("public_root_compile_failed", not build["ok"]),
                ("coherence_release_blocked", not coherence["ok"]),
                ("lean_version_unavailable", not lean_version["ok"]),
            )
            if failed
        ],
        terminal_states=(
            []
            if checks_passed
            else ["compile_failed" if not build["ok"] else "blocked"]
        ),
    )


def write_report(
    output: Path,
    imports: list[Path],
    build: dict,
    coherence: dict,
    lean_version: dict,
    release: dict,
) -> dict[str, Any]:
    lake_manifest = REPO_ROOT / "lake-manifest.json"
    payload = {
        "schema_version": 1,
        "style": "mathformerphysicslib_release_gate",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        **release,
        "public_root": PUBLIC_ROOT.relative_to(REPO_ROOT).as_posix(),
        "public_root_sha256": sha256(PUBLIC_ROOT),
        "imported_modules": [
            {"path": path.relative_to(REPO_ROOT).as_posix(), "sha256": sha256(path)}
            for path in imports
        ],
        "lean_version": lean_version,
        "lake_manifest_sha256": (
            sha256(lake_manifest) if lake_manifest.exists() else None
        ),
        "build": build,
        "coherence": coherence,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def run(output: Path) -> dict[str, Any]:
    build = build_public_root()
    coherence = check_coherence()
    lean_version = check_lean_version()
    imports = imported_files()
    release = assess_release(build, coherence, lean_version)
    return write_report(output, imports, build, coherence, lean_version, release)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = run(args.output)
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if args.json
        else f"release_ok={payload['release_ok']}"
    )
    return 0 if payload["release_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
