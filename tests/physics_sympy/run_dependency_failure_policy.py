#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Check that missing SymPy is reported as a structured dependency blocker."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_with_sympy_blocked(
    script: str, repository_root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Run one script with an import hook that makes `sympy` unavailable."""
    with tempfile.TemporaryDirectory() as tmp_raw:
        tmp = Path(tmp_raw)
        (tmp / "sitecustomize.py").write_text(
            """
import importlib.abc

class _BlockSympy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "sympy" or fullname.startswith("sympy."):
            raise ModuleNotFoundError("No module named 'sympy'", name="sympy")
        return None

import sys
sys.meta_path.insert(0, _BlockSympy())
""".lstrip(),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{tmp}{os.pathsep}{env.get('PYTHONPATH', '')}"
        completed = subprocess.run(
            [sys.executable, script, "--json"],
            cwd=repository_root,
            env=env,
            text=True,
            capture_output=True,
        )
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        parsed = {}
    return {
        "script": script,
        "returncode": completed.returncode,
        "stdout_json": parsed,
        "stderr": completed.stderr,
        "raw_stdout": completed.stdout,
    }


SCRIPTS = (
    "tests/physics_sympy/run_phase1_dependency_grounding.py",
    "tests/physics_sympy/run_controlled_suite.py",
)


def initialize_results() -> list[dict[str, Any]]:
    return []


def collect_next(
    results: list[dict[str, Any]], repository_root: Path = REPO_ROOT
) -> dict[str, Any]:
    result = run_with_sympy_blocked(SCRIPTS[len(results)], repository_root)
    accumulated = [*results, result]
    return {"results": accumulated, "done": len(accumulated) == len(SCRIPTS)}


def begin_validation(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {"index": 0, "results": results, "findings": []}


def inspect_current(state: dict[str, Any]) -> dict[str, Any]:
    result = state["results"][state["index"]]
    return {"result": result, "missing": not result["stdout_json"]}


def record_missing(
    state: dict[str, Any], result: dict[str, Any]
) -> list[dict[str, Any]]:
    findings = list(state["findings"])
    findings.append(
        {
            "severity": "high",
            "code": "missing_structured_json",
            "script": result["script"],
            "stdout": result["raw_stdout"][-500:],
            "stderr": result["stderr"][-500:],
        }
    )
    return findings


def check_nonempty(
    state: dict[str, Any], result: dict[str, Any]
) -> list[dict[str, Any]]:
    findings = list(state["findings"])
    parsed = result["stdout_json"]
    if parsed.get("style") != "physics_sympy_dependency_blocker":
        findings.append(
            {
                "severity": "high",
                "code": "wrong_missing_dependency_style",
                "script": result["script"],
                "style": parsed.get("style"),
            }
        )
    codes = {
        item.get("code")
        for item in parsed.get("findings", [])
        if isinstance(item, dict)
    }
    if "missing_required_dependency" not in codes:
        findings.append(
            {
                "severity": "high",
                "code": "missing_dependency_code_absent",
                "script": result["script"],
                "findings": parsed.get("findings", []),
            }
        )
    if "Traceback" in result["stderr"] or "Traceback" in result["raw_stdout"]:
        findings.append(
            {
                "severity": "high",
                "code": "traceback_leaked",
                "script": result["script"],
            }
        )
    if result["returncode"] == 0:
        findings.append(
            {
                "severity": "medium",
                "code": "missing_dependency_returned_success",
                "script": result["script"],
            }
        )
    return findings


def advance_validation(
    state: dict[str, Any], findings: list[dict[str, Any]]
) -> dict[str, Any]:
    next_state = {**state, "index": state["index"] + 1, "findings": findings}
    return {
        "state": next_state,
        "done": next_state["index"] == len(next_state["results"]),
    }


def build_report(state: dict[str, Any]) -> dict[str, Any]:
    results, findings = state["results"], state["findings"]
    return {
        "schema_version": 1,
        "ok": not any(item["severity"] == "high" for item in findings),
        "style": "physics_sympy_dependency_failure_policy",
        "results": results,
        "findings": findings,
    }


def run_check() -> dict[str, Any]:
    """Run the same two collection steps before inspecting either result."""
    results = initialize_results()
    for _ in SCRIPTS:
        results = collect_next(results)["results"]
    state = begin_validation(results)
    for _ in results:
        inspected = inspect_current(state)
        check = record_missing if inspected["missing"] else check_nonempty
        state = advance_validation(state, check(state, inspected["result"]))["state"]
    return build_report(state)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the policy test."""
    args = parse_args(argv)
    report = run_check()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok: {report['ok']}")
        print(f"findings: {len(report['findings'])}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
