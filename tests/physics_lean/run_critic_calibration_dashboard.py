#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Build calibration metrics from independently labeled physics fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "artifacts/physics_lean/calibration/dashboard.json"
VENV_PYTHON = REPO_ROOT / ".venv/bin/python"


def run_json(command: list[str]) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
    elapsed = time.perf_counter() - started
    if result.returncode != 0:
        raise RuntimeError(f"{command} failed\n{result.stdout}\n{result.stderr}")
    return json.loads(result.stdout), elapsed


def confusion(rows: list[tuple[bool, bool]]) -> dict[str, Any]:
    tp = sum(label and prediction for label, prediction in rows)
    tn = sum(not label and not prediction for label, prediction in rows)
    fp = sum(not label and prediction for label, prediction in rows)
    fn = sum(label and not prediction for label, prediction in rows)
    positive = tp + fn
    negative = tn + fp
    return {
        "samples": len(rows),
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "false_positive_rate": fp / negative if negative else 0.0,
        "false_negative_rate": fn / positive if positive else 0.0,
        "accuracy": (tp + tn) / len(rows) if rows else 0.0,
    }


def initialize(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    return {
        "options": {"output": str(args.output), "json": args.json},
        "state": {"runs": [], "rows": {}},
    }


def derivation(state: dict[str, Any]) -> dict[str, Any]:
    runs = state["runs"]
    target, elapsed = run_json(
        [
            sys.executable,
            "tests/physics_lean/run_derivation_completeness_regression.py",
            "--json",
        ]
    )
    runs.append({"suite": target["style"], "wall_seconds": elapsed})
    target_by_id = {item["id"]: item for item in target["checks"]}
    target_rows = [
        (
            True,
            str(target_by_id[name]["detail"].get("status", "")).startswith("blocked"),
        )
        for name in ("direct_target_hypothesis_blocks", "wrapped_target_witness_blocks")
    ]
    target_rows.append(
        (
            False,
            str(
                target_by_id["legitimate_source_law_witness_passes"]["detail"].get(
                    "status", ""
                )
            ).startswith("blocked"),
        )
    )

    state["rows"]["target_restatement"] = target_rows
    return state


def grounding(state: dict[str, Any]) -> dict[str, Any]:
    runs = state["runs"]
    grounding, elapsed = run_json(
        [
            sys.executable,
            "tests/physics_lean/run_formal_science_grounding_debt_gate.py",
            "--json",
        ]
    )
    runs.append({"suite": grounding["style"], "wall_seconds": elapsed})
    grounding_by_id = {item["id"]: item for item in grounding["checks"]}
    drift_rows = [
        (
            True,
            bool(grounding_by_id["trivial_support_debt_blocks"]["detail"].get("codes")),
        ),
        (
            False,
            bool(
                grounding_by_id["formalphysics_0191_no_true_law_debt"]["detail"].get(
                    "codes"
                )
            ),
        ),
        (
            False,
            bool(
                grounding_by_id["formalphysics_0059_no_true_law_debt"]["detail"].get(
                    "codes"
                )
            ),
        ),
    ]

    state["rows"]["source_drift_or_trivial_grounding"] = drift_rows
    return state


def redefinition(state: dict[str, Any]) -> dict[str, Any]:
    runs = state["runs"]
    duplicate, elapsed = run_json(
        [
            sys.executable,
            "tests/physics_lean/run_redefinition_critic_calibration.py",
            "--json",
        ]
    )
    runs.append({"suite": duplicate["suite"], "wall_seconds": elapsed})
    duplicate_rows = [
        (True, duplicate["duplicate"]["finding_count"] > 0),
        (False, duplicate["healthy"]["finding_count"] > 0),
    ]

    state["rows"]["duplicate_ownership"] = duplicate_rows
    return state


def units(state: dict[str, Any]) -> dict[str, Any]:
    runs = state["runs"]
    unit_python = str(VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable))
    units, elapsed = run_json(
        [unit_python, "tests/physics_sympy/run_unit_semantics_contract.py", "--json"]
    )
    runs.append({"suite": units["suite"], "wall_seconds": elapsed})
    witnesses = units["witnesses"]
    unit_rows = [
        (False, not witnesses["valid"]["ok"]),
        (True, not witnesses["unit_mutation"]["ok"]),
        (True, not witnesses["function_argument"]["ok"]),
    ]

    state["rows"]["unit_mismatch"] = unit_rows
    return state


def summarize(state: dict[str, Any]) -> dict[str, Any]:
    runs = state["runs"]
    metrics = {
        "source_drift_or_trivial_grounding": confusion(
            state["rows"]["source_drift_or_trivial_grounding"]
        ),
        "target_restatement": confusion(state["rows"]["target_restatement"]),
        "duplicate_ownership": confusion(state["rows"]["duplicate_ownership"]),
        "unit_mismatch": confusion(state["rows"]["unit_mismatch"]),
    }
    payload = {
        "schema_version": 1,
        "style": "physics_critic_calibration_dashboard",
        "ok": all(
            item["false_positive"] == 0 and item["false_negative"] == 0
            for item in metrics.values()
        ),
        "evaluation_sets": {
            "curated_regressions": sum(item["samples"] for item in metrics.values()),
            "held_out_source_cases": 1,
            "adversarial_mutations": 6,
            "genuine_new_formalizations": 0,
        },
        "metrics": metrics,
        "execution": {
            "subprocess_count": len(runs),
            "wall_seconds": round(sum(item["wall_seconds"] for item in runs), 4),
            "runs": runs,
            "hidden_chain_of_thought_recorded": False,
        },
        "limitations": [
            "The labeled fixture set is small and reports calibration evidence, not population-level accuracy.",
            "Genuine new formalization evaluation remains empty until independently reviewed cases are added.",
        ],
    }
    return payload


def publish(options: dict[str, Any], payload: dict[str, Any]) -> int:
    output = Path(options["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if options["json"]
        else ("PASS" if payload["ok"] else "FAIL")
    )
    return 0 if payload["ok"] else 1


def main() -> int:
    initialized = initialize()
    state = initialized["state"]
    for step in (derivation, grounding, redefinition, units):
        state = step(state)
    return publish(initialized["options"], summarize(state))


if __name__ == "__main__":
    raise SystemExit(main())
