#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Prevent task-local generated skills and repair probes from being promoted
#   after one appealing run.
#
# Intent:
#   Validate generated-skill lifecycle packets and promotion gates.
#
# Function:
#   Checks lifecycle state, required artifacts, seeded-defect result, promotion
#   evidence, and writes a report.
#
# Maintenance Notes:
#   Keep required artifact names synchronized with generated_skill_lifecycle.schema.json.

"""Validate generated skill lifecycle records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = (
    REPO_ROOT / "meta_skills" / "schemas" / "generated_skill_lifecycle.schema.json"
)
GENERATED_ROOT = REPO_ROOT / "meta_skills" / "registry" / "generated_skills"
OUTPUT_PATH = (
    REPO_ROOT
    / "artifacts"
    / "meta_skills"
    / "generated_skill_lifecycle_validation.json"
)


def rel(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_lifecycle(
    path: Path, schema: dict[str, Any], repo_root: Path = REPO_ROOT
) -> list[dict[str, Any]]:
    data = load_json(path)
    root = path.parent
    findings: list[dict[str, Any]] = []
    for field in schema["required"]:
        if field not in data:
            findings.append(
                {
                    "severity": "error",
                    "code": "missing_field",
                    "path": rel(path, repo_root),
                    "field": field,
                }
            )
    if findings:
        return findings
    if data["state"] not in schema["states"]:
        findings.append(
            {
                "severity": "error",
                "code": "invalid_state",
                "path": rel(path, repo_root),
                "state": data["state"],
            }
        )
    for artifact in schema["required_artifacts_for_task_local_validation"]:
        artifact_path = root / artifact
        if not artifact_path.exists():
            findings.append(
                {
                    "severity": "error",
                    "code": "missing_lifecycle_artifact",
                    "path": rel(path, repo_root),
                    "artifact": rel(artifact_path, repo_root),
                }
            )
    defect = root / "seeded_defect_result.json"
    if defect.exists():
        defect_data = load_json(defect)
        if defect_data.get("accepted_defect") is True:
            findings.append(
                {
                    "severity": "error",
                    "code": "seeded_defect_accepted",
                    "path": rel(defect, repo_root),
                }
            )
    gate = data.get("promotion_gate", {})
    for field in schema["promotion_gate_required"]:
        if field not in gate:
            findings.append(
                {
                    "severity": "error",
                    "code": "promotion_gate_missing_field",
                    "path": rel(path, repo_root),
                    "field": field,
                }
            )
    if gate.get("target_state") == "promoted" and gate.get(
        "observed_repeated_use_count", 0
    ) < gate.get("required_repeated_use_count", 2):
        findings.append(
            {
                "severity": "error",
                "code": "promotion_without_repeated_use",
                "path": rel(path, repo_root),
            }
        )
    if data["state"] == "draft" and gate.get("allowed") is True:
        findings.append(
            {
                "severity": "error",
                "code": "draft_promotion_gate_open",
                "path": rel(path, repo_root),
            }
        )
    return findings


def prepare(context: dict[str, Any], record_bound: int | None = None) -> dict[str, Any]:
    """Load and discover once; the adapter bound rejects, never truncates."""
    root = Path(context["repo_root"]).resolve()
    schema = load_json(root / SCHEMA_PATH.relative_to(REPO_ROOT))
    paths = sorted(
        (root / GENERATED_ROOT.relative_to(REPO_ROOT)).glob("*/lifecycle.json")
    )
    if record_bound is not None and len(paths) > record_bound:
        raise ValueError("discovered records exceed workflow specialization bound")
    return {
        "schema": schema,
        "state": {
            "paths": [str(p) for p in paths],
            "cursor": 0,
            "results": [],
            "all_findings": [],
        },
        "has_records": bool(paths),
    }


def validate_record(
    schema: dict[str, Any], state: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    if not state["paths"]:
        return {"findings": []}
    return {
        "findings": validate_lifecycle(
            Path(state["paths"][state["cursor"]]),
            schema,
            Path(context["repo_root"]).resolve(),
        )
    }


def accumulate(
    state: dict[str, Any], findings: list[dict[str, Any]], context: dict[str, Any]
) -> dict[str, Any]:
    if not state["paths"]:
        return {"state": state, "done": True}
    path = Path(state["paths"][state["cursor"]])
    updated = {
        "paths": state["paths"],
        "cursor": state["cursor"] + 1,
        "all_findings": [*state["all_findings"], *findings],
        "results": [
            *state["results"],
            {
                "path": rel(path, Path(context["repo_root"]).resolve()),
                "ok": not any(f["severity"] == "error" for f in findings),
                "findings": findings,
            },
        ],
    }
    return {"state": updated, "done": updated["cursor"] == len(updated["paths"])}


def write_report(state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "style": "mathformer_meta_generated_skill_lifecycle_validation",
        "ok": bool(state["paths"])
        and not any(f["severity"] == "error" for f in state["all_findings"]),
        "record_count": len(state["paths"]),
        "results": state["results"],
        "findings": state["all_findings"],
    }
    output_path = Path(context["repo_root"]).resolve() / OUTPUT_PATH.relative_to(
        REPO_ROOT
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return {"report": payload}


def run() -> dict[str, Any]:
    context = {"repo_root": str(REPO_ROOT)}
    prepared = prepare(context)
    state = prepared["state"]
    for _ in state["paths"]:
        findings = validate_record(prepared["schema"], state, context)["findings"]
        state = accumulate(state, findings, context)["state"]
    return write_report(state, context)["report"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = run()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "PASS generated skill lifecycle"
            if payload["ok"]
            else "FAIL generated skill lifecycle"
        )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
