#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Ensure runtime skill traces are complete enough to support diagnosis,
#   workflow evolution, and promotion decisions.
#
# Intent:
#   Validate JSONL trace files against the local runtime schema.
#
# Function:
#   Checks required event fields, allowed steps, referenced artifacts, and
#   writes an artifact report.
#
# Maintenance Notes:
#   Keep allowed steps synchronized with skills/SKILL_HOOKS.yaml.

"""Validate runtime skill-application traces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = (
    REPO_ROOT / "meta_skills" / "schemas" / "runtime_skill_application.schema.json"
)
TRACE_ROOT = REPO_ROOT / "artifacts" / "meta_skills" / "runtime"
OUTPUT_PATH = REPO_ROOT / "artifacts" / "meta_skills" / "runtime_trace_validation.json"


def rel(path: Path, repository_root: Path | None = None) -> str:
    try:
        return (
            path.resolve()
            .relative_to(REPO_ROOT if repository_root is None else repository_root)
            .as_posix()
        )
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_file(
    path: Path, schema: dict[str, Any], repository_root: Path | None = None
) -> tuple[int, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    allowed_steps = set(schema["allowed_steps"])
    event_count = 0
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            event_count += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                findings.append(
                    {
                        "severity": "error",
                        "code": "invalid_jsonl",
                        "path": rel(path, repository_root),
                        "line": line_no,
                        "detail": str(exc),
                    }
                )
                continue
            for field in schema["required"]:
                if field not in row:
                    findings.append(
                        {
                            "severity": "error",
                            "code": "missing_field",
                            "path": rel(path, repository_root),
                            "line": line_no,
                            "field": field,
                        }
                    )
            if row.get("step") not in allowed_steps:
                findings.append(
                    {
                        "severity": "error",
                        "code": "invalid_step",
                        "path": rel(path, repository_root),
                        "line": line_no,
                        "step": row.get("step"),
                    }
                )
            if not isinstance(row.get("evidence"), list) or not row.get("evidence"):
                findings.append(
                    {
                        "severity": "error",
                        "code": "missing_evidence",
                        "path": rel(path, repository_root),
                        "line": line_no,
                    }
                )
            if not isinstance(row.get("artifacts"), list):
                findings.append(
                    {
                        "severity": "error",
                        "code": "artifacts_not_list",
                        "path": rel(path, repository_root),
                        "line": line_no,
                    }
                )
            else:
                for artifact in row["artifacts"]:
                    artifact_path = (
                        REPO_ROOT if repository_root is None else repository_root
                    ) / str(artifact)
                    if not artifact_path.exists():
                        findings.append(
                            {
                                "severity": "error",
                                "code": "missing_artifact",
                                "path": rel(path, repository_root),
                                "line": line_no,
                                "artifact": rel(artifact_path, repository_root),
                            }
                        )
    if event_count == 0:
        findings.append(
            {
                "severity": "error",
                "code": "empty_trace",
                "path": rel(path, repository_root),
            }
        )
    return event_count, findings


def initialize(repository_root: Path | None = None) -> dict[str, Any]:
    """Load native inputs and initialize the loop's carried state."""
    schema_path = (
        SCHEMA_PATH
        if repository_root is None
        else repository_root
        / "meta_skills/schemas/runtime_skill_application.schema.json"
    )
    trace_root = (
        TRACE_ROOT
        if repository_root is None
        else repository_root / "artifacts/meta_skills/runtime"
    )
    output_path = (
        OUTPUT_PATH
        if repository_root is None
        else repository_root / "artifacts/meta_skills/runtime_trace_validation.json"
    )
    schema = load_json(schema_path)
    traces = sorted(trace_root.glob("*.jsonl"))
    return {
        "schema": schema,
        "traces": [str(path) for path in traces],
        "cursor": 0,
        "results": [],
        "all_findings": [],
        "repository_root": str(
            REPO_ROOT if repository_root is None else repository_root
        ),
        "output_path": str(output_path),
    }


def validate_current(state: dict[str, Any]) -> dict[str, Any]:
    """Use the original per-file validator without changing its checks."""
    path = Path(state["traces"][state["cursor"]])
    root = Path(state["repository_root"])
    count, findings = validate_file(path, state["schema"], root)
    return {"path": rel(path, root), "event_count": count, "findings": findings}


def accumulate(state: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    """Carry every finding forward in native file and event order."""
    findings = check["findings"]
    state["all_findings"].extend(findings)
    state["results"].append(
        {
            "path": check["path"],
            "event_count": check["event_count"],
            "ok": not any(f["severity"] == "error" for f in findings),
            "findings": findings,
        }
    )
    state["cursor"] += 1
    return state


def write_report(state: dict[str, Any]) -> dict[str, Any]:
    traces, results, all_findings = (
        state["traces"],
        state["results"],
        state["all_findings"],
    )
    payload = {
        "schema_version": 1,
        "style": "mathformer_meta_runtime_trace_validation",
        "ok": bool(traces) and not any(f["severity"] == "error" for f in all_findings),
        "trace_count": len(traces),
        "results": results,
        "findings": all_findings,
    }
    output_path = Path(state["output_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return payload


def run() -> dict[str, Any]:
    state = initialize()
    while state["cursor"] < len(state["traces"]):
        state = accumulate(state, validate_current(state))
    return write_report(state)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = run()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("PASS runtime traces" if payload["ok"] else "FAIL runtime traces")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
