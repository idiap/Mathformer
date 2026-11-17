#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

"""Exercise reasoning-log fixtures as a consumer application would."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from reasoning_log import (
    append_skill_complete,
    append_skill_error,
    append_skill_progress,
    append_skill_start,
)  # noqa: E402
from summarize_reasoning_log import summarize  # noqa: E402


def build_log(path: Path, *, mode: str) -> None:
    call_id = append_skill_start(
        path,
        skill="reasoning-log-schema-guardian",
        hook_id="control.reasoning_log_schema",
        run_id=f"consumer-fixture-{mode}",
        intent=f"Build {mode} consumer fixture.",
        inputs={"mode": mode},
        artifacts={"log_file": str(path), "log_file_sha256": "fixture"},
        human_summary=f"Started the {mode} consumer fixture.",
    )
    if mode == "multi_skill":
        append_skill_progress(
            path,
            phase="evidence_recorded",
            skill="reasoning-log-schema-guardian",
            hook_id="control.reasoning_log_schema",
            skill_call_id=call_id,
            run_id=f"consumer-fixture-{mode}",
            intent=f"Build {mode} consumer fixture.",
            inputs={"mode": mode},
            artifacts={
                "report": "artifacts/example/report.json",
                "report_sha256": "fixture",
            },
            evidence={"review_stage": "source_alignment"},
            human_summary="Recorded a source-alignment stage for the multi-skill fixture.",
        )
    if mode == "blocked":
        append_skill_error(
            path,
            skill="reasoning-log-schema-guardian",
            hook_id="control.reasoning_log_schema",
            skill_call_id=call_id,
            run_id=f"consumer-fixture-{mode}",
            intent=f"Build {mode} consumer fixture.",
            inputs={"mode": mode},
            artifacts={"log_file": str(path), "log_file_sha256": "fixture"},
            risks={"blocker": "recoverable fixture blocker"},
            next_action="Repair the fixture input and rerun the consumer summary.",
            error="recoverable fixture blocker",
        )
        return
    append_skill_complete(
        path,
        skill="reasoning-log-schema-guardian",
        hook_id="control.reasoning_log_schema",
        skill_call_id=call_id,
        run_id=f"consumer-fixture-{mode}",
        intent=f"Build {mode} consumer fixture.",
        inputs={"mode": mode},
        artifacts={"log_file": str(path), "log_file_sha256": "fixture"},
        evidence={"mode": mode},
        decision={"status": "pass"},
        risks={},
        next_action="Use the structured summary fields directly.",
        human_summary=f"Completed the {mode} consumer fixture.",
    )


def check_summary(summary: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for field in (
        "run_ids",
        "skills",
        "timeline",
        "artifacts",
        "risks",
        "next_actions",
    ):
        if field not in summary:
            errors.append(f"missing_summary_field:{field}")
    if not summary.get("skills"):
        errors.append("missing_skills")
    if not summary.get("timeline"):
        errors.append("missing_timeline")
    if not isinstance(summary.get("artifacts"), dict):
        errors.append("artifacts_not_object")
    return errors


CASES = {
    "single_skill_success": "single",
    "multi_skill_physics_like": "multi_skill",
    "recoverable_blocker": "blocked",
    "wrapper_only_fallback": "wrapper",
}


def initialize_suite(root: Path) -> Dict[str, Any]:
    return {
        "root": str(root),
        "cases": [{"case_id": key, "mode": value} for key, value in CASES.items()],
        "cursor": 0,
        "checks": [],
    }


def evaluate_fixture(state: Dict[str, Any]) -> Dict[str, Any]:
    root = Path(state["root"])
    case = state["cases"][state["cursor"]]
    case_id, mode = case["case_id"], case["mode"]
    log_file = root / f"{case_id}.jsonl"
    build_log(log_file, mode=mode)
    summary = summarize(log_file, hooks_file=REPO_ROOT / "skills" / "SKILL_HOOKS.yaml")
    errors = check_summary(summary)
    return {
        "case_id": case_id,
        "ok": not errors,
        "errors": errors,
        "status_values": sorted(
            {item.get("status") for item in summary.get("timeline", [])}
        ),
        "structured_fields_available": {
            "status": bool(summary.get("timeline")),
            "skill": bool(summary.get("skills")),
            "run_id": bool(summary.get("run_ids")),
            "artifacts": isinstance(summary.get("artifacts"), dict),
            "risks": "risks" in summary,
            "next_actions": "next_actions" in summary,
        },
    }


def append_and_advance(state: Dict[str, Any], check: Dict[str, Any]) -> Dict[str, Any]:
    return {**state, "checks": [*state["checks"], check], "cursor": state["cursor"] + 1}


def aggregate_suite(state: Dict[str, Any]) -> Dict[str, Any]:
    checks = state["checks"]
    return {
        "schema_version": 1,
        "style": "reasoning_log_consumer_contract_suite",
        "ok": all(check["ok"] for check in checks),
        "checks": checks,
    }


def run_suite() -> Dict[str, Any]:
    with TemporaryDirectory() as temp_dir:
        state = initialize_suite(Path(temp_dir))
        for _ in state["cases"]:
            state = append_and_advance(state, evaluate_fixture(state))
    return aggregate_suite(state)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    report = run_suite()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for check in report["checks"]:
            print(f"{'PASS' if check['ok'] else 'FAIL'} {check['case_id']}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
