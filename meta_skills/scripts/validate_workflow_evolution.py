#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make long recursive workflows inspectable as states, transitions, gates,
#   reflective questions, and next deltas.
#
# Intent:
#   Validate workflow evolution graph artifacts.
#
# Function:
#   Checks required graph fields, transition endpoints, evidence path existence,
#   and writes a validation report.
#
# Maintenance Notes:
#   Keep this script aligned with workflow_evolution.schema.json.

"""Validate meta-skill workflow evolution graphs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "meta_skills" / "schemas" / "workflow_evolution.schema.json"
GRAPH_ROOT = REPO_ROOT / "meta_skills" / "registry" / "tasks"
OUTPUT_PATH = (
    REPO_ROOT / "artifacts" / "meta_skills" / "workflow_evolution_validation.json"
)


def relative_path(path: Path, root: Path | None = None) -> str:
    try:
        return (
            path.resolve()
            .relative_to(root if root is not None else REPO_ROOT)
            .as_posix()
        )
    except ValueError:
        return str(path)


rel = relative_path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_evidence(
    paths: list[str],
    graph_path: Path,
    location: str,
    findings: list[dict[str, Any]],
    repository_root: Path | None = None,
) -> None:
    root = repository_root if repository_root is not None else REPO_ROOT

    def rel(path):
        return relative_path(path, root)

    if not paths:
        findings.append(
            {
                "severity": "error",
                "code": "missing_evidence",
                "path": rel(graph_path),
                "location": location,
            }
        )
    for value in paths:
        evidence_path = root / value
        if not evidence_path.exists():
            findings.append(
                {
                    "severity": "error",
                    "code": "missing_evidence_path",
                    "path": rel(graph_path),
                    "location": location,
                    "evidence": rel(evidence_path),
                }
            )


def validate_graph(
    path: Path, schema: dict[str, Any], repository_root: Path | None = None
) -> list[dict[str, Any]]:
    root = repository_root if repository_root is not None else REPO_ROOT

    def rel(path):
        return relative_path(path, root)

    data = load_json(path)
    findings: list[dict[str, Any]] = []
    for field in schema["required"]:
        if field not in data:
            findings.append(
                {
                    "severity": "error",
                    "code": "missing_field",
                    "path": rel(path),
                    "field": field,
                }
            )
    if findings:
        return findings
    source = root / str(data["source_report"])
    if not source.exists():
        findings.append(
            {
                "severity": "error",
                "code": "missing_source_report",
                "path": rel(path),
                "source_report": rel(source),
            }
        )

    state_ids = {row.get("state_id") for row in data.get("states", [])}
    nested = schema["nested_required"]
    for collection, fields in nested.items():
        rows = data.get(collection)
        if not isinstance(rows, list) or not rows:
            findings.append(
                {
                    "severity": "error",
                    "code": "empty_collection",
                    "path": rel(path),
                    "collection": collection,
                }
            )
            continue
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                findings.append(
                    {
                        "severity": "error",
                        "code": "non_object_row",
                        "path": rel(path),
                        "collection": collection,
                        "index": index,
                    }
                )
                continue
            for field in fields:
                if field not in row:
                    findings.append(
                        {
                            "severity": "error",
                            "code": "missing_nested_field",
                            "path": rel(path),
                            "collection": collection,
                            "index": index,
                            "field": field,
                        }
                    )
            if "evidence" in row:
                check_evidence(
                    list(row.get("evidence") or []),
                    path,
                    f"{collection}[{index}]",
                    findings,
                    root,
                )

    for index, row in enumerate(data.get("transitions", [])):
        if row.get("from") not in state_ids or row.get("to") not in state_ids:
            findings.append(
                {
                    "severity": "error",
                    "code": "transition_unknown_endpoint",
                    "path": rel(path),
                    "index": index,
                    "from": row.get("from"),
                    "to": row.get("to"),
                }
            )
    if not data.get("next_delta", {}).get("decision"):
        findings.append(
            {
                "severity": "error",
                "code": "next_delta_missing_decision",
                "path": rel(path),
            }
        )
    return findings


def initialize(repository_root: Path | None = None) -> dict[str, Any]:
    root = repository_root if repository_root is not None else REPO_ROOT
    schema = load_json(
        root / "meta_skills/schemas/workflow_evolution.schema.json"
        if repository_root is not None
        else SCHEMA_PATH
    )
    graph_root = (
        root / "meta_skills/registry/tasks"
        if repository_root is not None
        else GRAPH_ROOT
    )
    paths = sorted(graph_root.glob("*/workflow_evolution.json"))
    return {
        "repository_root": str(root),
        "output_path": str(
            root / "artifacts/meta_skills/workflow_evolution_validation.json"
            if repository_root is not None
            else OUTPUT_PATH
        ),
        "schema": schema,
        "nested_order": (
            list(schema["nested_required"])
            if isinstance(schema, dict)
            and isinstance(schema.get("nested_required"), dict)
            else []
        ),
        "paths": [str(path) for path in paths],
        "cursor": 0,
        "results": [],
        "all_findings": [],
    }


def validate_current(state: dict[str, Any]) -> list[dict[str, Any]]:
    # JSON transports may sort object keys; carry source iteration order explicitly.
    schema = state["schema"]
    if isinstance(schema, dict) and isinstance(schema.get("nested_required"), dict):
        schema = dict(schema)
        schema["nested_required"] = {
            key: schema["nested_required"][key] for key in state["nested_order"]
        }
    return validate_graph(
        Path(state["paths"][state["cursor"]]), schema, Path(state["repository_root"])
    )


def accumulate(state: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    path = Path(state["paths"][state["cursor"]])
    state["all_findings"].extend(findings)
    state["results"].append(
        {
            "path": rel(path, Path(state["repository_root"])),
            "ok": not any(f["severity"] == "error" for f in findings),
            "findings": findings,
        }
    )
    state["cursor"] += 1
    return state


def finish(state: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "style": "mathformer_meta_workflow_evolution_validation",
        "ok": bool(state["paths"])
        and not any(f["severity"] == "error" for f in state["all_findings"]),
        "graph_count": len(state["paths"]),
        "results": state["results"],
        "findings": state["all_findings"],
    }
    output = Path(state["output_path"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def run() -> dict[str, Any]:
    state = initialize()
    while state["cursor"] < len(state["paths"]):
        accumulate(state, validate_current(state))
    return finish(state)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = run()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("PASS workflow evolution" if payload["ok"] else "FAIL workflow evolution")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
