#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Validate the committed, profile-complete uv dependency lock."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[2]


def check_uv(repository_root: Path) -> dict:
    result = subprocess.run(
        ["uv", "lock", "--check"], cwd=repository_root, text=True, capture_output=True
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def read_files(repository_root: Path) -> dict:
    pyproject = repository_root / "pyproject.toml"
    lock = repository_root / "uv.lock"
    project_text = pyproject.read_text(encoding="utf-8") if pyproject.exists() else ""
    lock_text = lock.read_text(encoding="utf-8") if lock.exists() else ""
    return {"project_text": project_text, "lock_text": lock_text}


def build_payload(repository_root: Path, result: dict, texts: dict) -> dict:
    pyproject = repository_root / "pyproject.toml"
    lock = repository_root / "uv.lock"
    project_text, lock_text = texts["project_text"], texts["lock_text"]
    profiles = ["physics", "mcp", "documents", "providers", "knowledge-base"]
    cases = {
        "pyproject_present": pyproject.exists(),
        "lock_present": lock.exists(),
        "lock_current": result["returncode"] == 0,
        "profiles_declared": all(
            f"{profile} = [" in project_text for profile in profiles
        ),
        "reference_packages_locked": all(
            f'name = "{package}"' in lock_text
            for package in (
                "sympy",
                "mcp",
                "docling",
                "openai",
                "anthropic",
                "huggingface-hub",
            )
        ),
        "python_abi_range_locked": "requires-python" in lock_text,
    }
    payload = {
        "schema_version": 1,
        "suite": "dependency_lock_contract",
        "ok": all(cases.values()),
        "cases": cases,
        "profiles": profiles,
        "uv_stdout": result["stdout"],
        "uv_stderr": result["stderr"],
    }
    return payload


def print_and_return(payload: dict, json_output: bool) -> int:
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if json_output
        else ("PASS" if payload["ok"] else "FAIL")
    )
    return 0 if payload["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = check_uv(REPO_ROOT)
    texts = read_files(REPO_ROOT)
    payload = build_payload(REPO_ROOT, result, texts)
    return print_and_return(payload, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
