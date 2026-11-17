#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Run the controlled Mathlib indexing and navigation suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable
OUTPUT_PATH = REPO_ROOT / "artifacts" / "mathlib_index" / "indexing_control_suite.json"

COMMANDS = [
    [
        "skills/mathlib/mathlib-index-builder/scripts/build_mathlib_index.py",
        "--max-files",
        "220",
        "--json",
    ],
    [
        "skills/mathlib/mathlib-index-builder/scripts/build_mathlib_index.py",
        "--validate-existing",
        "--json",
    ],
    [
        "skills/mathlib/mathlib-concept-ontology-manager/scripts/validate_concept_ontology.py",
        "--json",
    ],
    [
        "skills/mathlib/mathlib-term-expansion-annotator/scripts/annotate_mathlib_terms.py",
        "--self-test",
        "--json",
    ],
    [
        "skills/mathlib/mathlib-navigation-state-planner/scripts/plan_mathlib_navigation_state.py",
        "--self-test",
        "--json",
    ],
    [
        "skills/mathlib/mathlib-navigation-state-planner/scripts/plan_mathlib_navigation_state.py",
        "--monotonic-check",
        "--json",
    ],
]


def run_command(parts: list[str], repo_root: Path | None = None) -> dict[str, Any]:
    start = time.time()
    proc = subprocess.run(
        [PYTHON, *parts],
        cwd=REPO_ROOT if repo_root is None else repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=240,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"stdout": proc.stdout}
    return {
        "command": [PYTHON, *parts],
        "returncode": proc.returncode,
        "duration_seconds": round(time.time() - start, 3),
        "ok": proc.returncode == 0 and payload.get("ok") is not False,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
        "payload": payload,
    }


def additional_oracles(repo_root: Path | None = None) -> list[dict[str, Any]]:
    repo_root = REPO_ROOT if repo_root is None else repo_root
    index_path = repo_root / "artifacts" / "mathlib_index" / "index.json"
    reranker_path = repo_root / "artifacts" / "mathlib_index" / "reranker_cache.json"
    annotation_path = (
        repo_root / "artifacts" / "mathlib_index" / "term_annotation_self_test.json"
    )
    navigation_path = (
        repo_root / "artifacts" / "mathlib_index" / "navigation_state_self_test.json"
    )
    index = json.loads(index_path.read_text(encoding="utf-8"))
    reranker = json.loads(reranker_path.read_text(encoding="utf-8"))
    annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
    navigation = json.loads(navigation_path.read_text(encoding="utf-8"))
    checks = [
        {
            "id": "index.version_stamp",
            "ok": {
                "lean_version",
                "mathlib_git_revision",
                "file_count",
                "declaration_count",
                "build_timestamp_utc",
            }
            <= set(index.get("version_stamp", {})),
        },
        {
            "id": "index.theorem_shape_and_graph",
            "ok": bool(index.get("declarations"))
            and all("theorem_shape" in row for row in index["declarations"][:20])
            and bool(index.get("declaration_graph")),
        },
        {
            "id": "index.optional_reranker_cache",
            "ok": index.get("optional_rerankers", {}).get("cache_path")
            == "artifacts/mathlib_index/reranker_cache.json"
            and reranker.get("enabled_by_default") is False
            and reranker.get("embedding_kind") == "deterministic_token_hash"
            and reranker.get("entry_count", 0) > 0,
        },
        {
            "id": "annotation.overloaded_terms",
            "ok": annotation.get("ok") is True
            and all(row.get("ok") for row in annotation.get("results", [])),
        },
        {
            "id": "navigation.gaps_and_monotonicity",
            "ok": navigation.get("ok") is True
            and "monotonic" in navigation
            and navigation["monotonic"].get("ok") is True
            and navigation.get("gap_count", 0) > 0
            and {
                "descend",
                "inspect_sibling",
                "query_declarations",
                "verify_candidate",
                "mark_gap",
            }
            <= set(navigation.get("operation_catalog", [])),
        },
    ]
    return checks


def execute_command(
    state: dict[str, Any], repo_root: Path | None = None
) -> dict[str, Any]:
    return run_command(COMMANDS[state["position"]], repo_root)


def advance_state(state: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    position = state["position"] + 1
    return {
        "state": {"position": position, "results": [*state["results"], result]},
        "done": position == len(COMMANDS),
    }


def commands_passed(state: dict[str, Any]) -> bool:
    return all(row["ok"] for row in state["results"])


def finish_report(
    state: dict[str, Any],
    oracle_checks: list[dict[str, Any]],
    output: Path | None = None,
) -> dict[str, Any]:
    results = state["results"]
    output = OUTPUT_PATH if output is None else output
    ok = all(row["ok"] for row in results) and all(row["ok"] for row in oracle_checks)
    payload = {
        "schema_version": 1,
        "style": "mathlib_indexing_control_suite",
        "ok": ok,
        "summary": {
            "command_pass": sum(1 for row in results if row["ok"]),
            "command_fail": sum(1 for row in results if not row["ok"]),
            "oracle_pass": sum(1 for row in oracle_checks if row["ok"]),
            "oracle_fail": sum(1 for row in oracle_checks if not row["ok"]),
        },
        "results": results,
        "oracle_checks": oracle_checks,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def run_suite(
    repo_root: Path | None = None, output: Path | None = None
) -> dict[str, Any]:
    state = {"position": 0, "results": []}
    for _ in COMMANDS:
        result = execute_command(state, repo_root)
        state = advance_state(state, result)["state"]
    oracle_checks = additional_oracles(repo_root) if commands_passed(state) else []
    return finish_report(state, oracle_checks, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = run_suite()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "PASS mathlib indexing control suite"
            if payload["ok"]
            else "FAIL mathlib indexing control suite"
        )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
