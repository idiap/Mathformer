#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.
#
# Intent:
#   Encode regression checks that catch parser breakage, semantic drift, and missing workflow evidence.
#
# Function:
#   Contains executable tests, fixtures, and manifests used for local and CI validation.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Run the first end-to-end SymPy backend case."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)


def run(check_id: str, cmd: list[str], timeout: int = 120) -> dict[str, Any]:
    """Document the responsibility of ``run``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    start = time.perf_counter()
    proc = subprocess.run(
        cmd, cwd=REPO_ROOT, text=True, capture_output=True, timeout=timeout
    )
    return {
        "id": check_id,
        "cmd": cmd,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "duration_ms": round((time.perf_counter() - start) * 1000, 3),
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def prepare(options: dict[str, Any]) -> dict[str, Any]:
    """Construct the native fixed plan and create its output directory."""
    root = Path(
        options.get("artifact_root", "artifacts/sympy/wiki_sum_first_odd_numbers")
    )
    source = Path("tests/latex/wiki_level/sum_first_odd_numbers.tex")
    generated = root / "AutoformalizedSumFirstOddNumbers.py"
    paths = {
        "deps": root / "dependency_probe.json",
        "api_index": root / "api_index.json",
        "parse": root / "parse_packet.json",
        "assumptions": root / "assumptions.json",
        "grounding": root / "api_grounding.json",
        "draft": root / "draft_report.json",
        "execution": root / "execution_report.json",
        "identity": root / "symbolic_validation.json",
        "counterexamples": root / "counterexample_report.json",
        "trace": root / "trace_verification.json",
        "consistency": root / "sympy_consistency_report.json",
        "markdown": root / "sympy_consistency_report.md",
        "html": root / "sympy_consistency_report.html",
    }

    commands = [
        (
            "dependency_probe",
            [
                str(PYTHON),
                "skills/sympy/sympy-dependency-prober/scripts/probe_sympy_dependencies.py",
                "--output",
                str(paths["deps"]),
                "--json",
            ],
        ),
        (
            "api_index",
            [
                str(PYTHON),
                "skills/sympy/sympy-api-docs-indexer/scripts/index_sympy_api.py",
                "--output",
                str(paths["api_index"]),
                "--self-test",
                "--json",
            ],
        ),
        (
            "parse_source",
            [
                str(PYTHON),
                "skills/sympy/sympy-expression-parser/scripts/parse_sympy_expressions.py",
                "--source",
                str(source),
                "--output",
                str(paths["parse"]),
                "--json",
            ],
        ),
        (
            "model_assumptions",
            [
                str(PYTHON),
                "skills/sympy/sympy-assumption-modeler/scripts/model_sympy_assumptions.py",
                "--parse-packet",
                str(paths["parse"]),
                "--output",
                str(paths["assumptions"]),
                "--json",
            ],
        ),
        (
            "ground_api",
            [
                str(PYTHON),
                "skills/sympy/sympy-concept-grounding-navigator/scripts/ground_sympy_concepts.py",
                "--api-index",
                str(paths["api_index"]),
                "--concept",
                "finite_sum",
                "--concept",
                "odd_numbers",
                "--concept",
                "square",
                "--concept",
                "symbolic_simplification",
                "--concept",
                "natural_number",
                "--output",
                str(paths["grounding"]),
                "--json",
            ],
        ),
        (
            "draft_artifact",
            [
                str(PYTHON),
                "skills/sympy/sympy-autoformalization-drafter/scripts/draft_sympy_case.py",
                "--parse-packet",
                str(paths["parse"]),
                "--assumptions",
                str(paths["assumptions"]),
                "--grounding",
                str(paths["grounding"]),
                "--output",
                str(generated),
                "--report",
                str(paths["draft"]),
                "--json",
            ],
        ),
        (
            "execute_artifact",
            [
                str(PYTHON),
                "skills/sympy/sympy-execution-runner/scripts/run_sympy_artifact.py",
                "--artifact",
                str(generated),
                "--output",
                str(paths["execution"]),
                "--json",
            ],
        ),
        (
            "validate_identity",
            [
                str(PYTHON),
                "skills/sympy/sympy-identity-validator/scripts/validate_sympy_identity.py",
                "--artifact",
                str(generated),
                "--output",
                str(paths["identity"]),
                "--json",
            ],
        ),
        (
            "search_counterexamples",
            [
                str(PYTHON),
                "skills/sympy/sympy-counterexample-searcher/scripts/search_sympy_counterexamples.py",
                "--artifact",
                str(generated),
                "--max-n",
                "100",
                "--output",
                str(paths["counterexamples"]),
                "--json",
            ],
        ),
        (
            "verify_trace",
            [
                str(PYTHON),
                "skills/sympy/sympy-transformation-trace-verifier/scripts/verify_sympy_trace.py",
                "--artifact",
                str(generated),
                "--output",
                str(paths["trace"]),
                "--json",
            ],
        ),
        (
            "consistency_report",
            [
                str(PYTHON),
                "skills/sympy/sympy-consistency-report-orchestrator/scripts/run_sympy_consistency_report.py",
                "--artifact",
                str(generated),
                "--parse-packet",
                str(paths["parse"]),
                "--assumptions",
                str(paths["assumptions"]),
                "--grounding",
                str(paths["grounding"]),
                "--draft-report",
                str(paths["draft"]),
                "--execution",
                str(paths["execution"]),
                "--identity",
                str(paths["identity"]),
                "--counterexamples",
                str(paths["counterexamples"]),
                "--trace",
                str(paths["trace"]),
                "--output",
                str(paths["consistency"]),
                "--markdown",
                str(paths["markdown"]),
                "--html",
                str(paths["html"]),
                "--json",
            ],
        ),
    ]

    root.mkdir(parents=True, exist_ok=True)
    return {
        "options": dict(options),
        "python": str(PYTHON),
        "commands": [{"id": key, "argv": argv} for key, argv in commands],
        "index": 0,
        "results": [],
        "artifacts": {k: str(v) for k, v in paths.items()},
        "generated": str(generated),
    }


def execute_step(state: dict[str, Any]) -> dict[str, Any]:
    """Run the next command once, preserving run()'s timeout and exceptions."""
    command = state["commands"][state["index"]]
    return run(command["id"], command["argv"])


def advance(
    state: dict[str, Any], result: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    """Append the observed result and stop at failure or native exhaustion."""
    state = {
        **state,
        "results": [*state["results"], result],
        "index": state["index"] + 1,
    }
    return state, not result["ok"] or state["index"] == len(state["commands"])


def finalize(state: dict[str, Any]) -> dict[str, Any]:
    """Write and print the source-owned completion, including failed prefixes."""
    root = Path(
        state["options"].get(
            "artifact_root", "artifacts/sympy/wiki_sum_first_odd_numbers"
        )
    )
    report = {
        "ok": all(item["ok"] for item in state["results"]),
        "python": state["python"],
        "results": state["results"],
        "artifacts": state["artifacts"],
    }
    (root / "e2e_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(report, indent=2, sort_keys=True)
        if state["options"].get("json", False)
        else f"sympy wiki e2e ok={report['ok']}"
    )
    return {
        "report": report,
        "report_path": str(root / "e2e_report.json"),
        "exit_code": 0 if report["ok"] else 1,
    }


def main() -> int:
    """Parse CLI options and run the same blocks exposed through MCP."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("artifacts/sympy/wiki_sum_first_odd_numbers"),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    state = prepare({"artifact_root": str(args.artifact_root), "json": args.json})
    while True:
        state, done = advance(state, execute_step(state))
        if done:
            break
    return finalize(state)["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
