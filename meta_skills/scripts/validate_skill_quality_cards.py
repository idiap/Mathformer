#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make deterministic and generative boundaries explicit for high-risk skills.
#
# Intent:
#   Validate quality cards as dependency-free JSON-compatible YAML files.
#
# Function:
#   Checks required epistemic fields, skill references, validation oracle shape,
#   and promotion-gate blockers, then writes a report.
#
# Maintenance Notes:
#   Cards use JSON syntax in .yaml files so the repository avoids a YAML dependency.

"""Validate Mathformer meta-skill quality cards."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "meta_skills" / "schemas" / "skill_quality_card.schema.json"
CARD_ROOT = REPO_ROOT / "meta_skills" / "quality_cards"
OUTPUT_PATH = (
    REPO_ROOT / "artifacts" / "meta_skills" / "skill_quality_card_validation.json"
)


def rel(path: Path, repository_root: Path | None = None) -> str:
    try:
        return (
            path.resolve()
            .relative_to(repository_root if repository_root is not None else REPO_ROOT)
            .as_posix()
        )
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_card(
    path: Path, schema: dict[str, Any], repository_root: Path | None = None
) -> list[dict[str, Any]]:
    data = load_json(path)
    findings: list[dict[str, Any]] = []
    for field in schema["required"]:
        if field not in data:
            findings.append(
                {
                    "severity": "error",
                    "code": "missing_field",
                    "path": rel(path, repository_root),
                    "field": field,
                }
            )
    if findings:
        return findings

    if data.get("subject_type") not in schema["allowed_subject_types"]:
        findings.append(
            {
                "severity": "error",
                "code": "invalid_subject_type",
                "path": rel(path, repository_root),
            }
        )

    if data.get("subject_type") == "skill":
        skill_path = (
            repository_root if repository_root is not None else REPO_ROOT
        ) / str(data.get("skill_path", ""))
        if not skill_path.exists():
            findings.append(
                {
                    "severity": "error",
                    "code": "missing_skill_path",
                    "path": rel(path, repository_root),
                    "skill_path": rel(skill_path, repository_root),
                }
            )

    for field in (
        "deterministic_boundary",
        "generative_boundary",
        "epistemic_risks",
        "necessary_conditions",
        "representation_contract",
        "validation_oracles",
        "failure_modes",
    ):
        value = data.get(field)
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(item, str) and item.strip() for item in value)
        ):
            findings.append(
                {
                    "severity": "error",
                    "code": "invalid_non_empty_string_list",
                    "path": rel(path, repository_root),
                    "field": field,
                }
            )

    gate = data.get("promotion_gate")
    if not isinstance(gate, dict):
        findings.append(
            {
                "severity": "error",
                "code": "promotion_gate_not_object",
                "path": rel(path, repository_root),
            }
        )
    else:
        for field in schema["promotion_gate_required"]:
            if field not in gate:
                findings.append(
                    {
                        "severity": "error",
                        "code": "promotion_gate_missing_field",
                        "path": rel(path, repository_root),
                        "field": field,
                    }
                )
        if not gate.get("blocking_conditions"):
            findings.append(
                {
                    "severity": "error",
                    "code": "promotion_gate_missing_blockers",
                    "path": rel(path, repository_root),
                }
            )

    for command in data.get("validation_oracles", []):
        if not command.startswith("python "):
            findings.append(
                {
                    "severity": "error",
                    "code": "oracle_not_python_command",
                    "path": rel(path, repository_root),
                    "command": command,
                }
            )

    return findings


def initialize(repository_root: Path | None = None) -> dict[str, Any]:
    """Load the schema and sorted paths, preserving native discovery order."""
    schema_path = (
        SCHEMA_PATH
        if repository_root is None
        else repository_root / "meta_skills/schemas/skill_quality_card.schema.json"
    )
    card_root = (
        CARD_ROOT
        if repository_root is None
        else repository_root / "meta_skills/quality_cards"
    )
    output_path = (
        OUTPUT_PATH
        if repository_root is None
        else repository_root
        / "artifacts/meta_skills/skill_quality_card_validation.json"
    )
    schema = load_json(schema_path)
    paths = sorted(card_root.glob("*.yaml"))
    return {
        "schema": schema,
        "paths": [str(path) for path in paths],
        "cursor": 0,
        "results": [],
        "findings": [],
        "repository_root": str(
            repository_root if repository_root is not None else REPO_ROOT
        ),
        "output_path": str(output_path),
    }


def validate_next(state: dict[str, Any]) -> dict[str, Any]:
    """Consume exactly one card; ordinary findings do not stop iteration."""
    path = Path(state["paths"][state["cursor"]])
    root = Path(state["repository_root"])
    card_findings = validate_card(path, state["schema"], root)
    state["findings"].extend(card_findings)
    state["results"].append(
        {
            "path": rel(path, root),
            "ok": not any(f["severity"] == "error" for f in card_findings),
            "findings": card_findings,
        }
    )
    state["cursor"] += 1
    return state


def write_report(state: dict[str, Any]) -> dict[str, Any]:
    """Write the native payload only after all discovered cards were consumed."""
    paths, results, findings = state["paths"], state["results"], state["findings"]
    payload = {
        "schema_version": 1,
        "style": "mathformer_meta_skill_quality_card_validation",
        "ok": bool(paths) and not any(f["severity"] == "error" for f in findings),
        "card_count": len(paths),
        "results": results,
        "findings": findings,
    }
    output_path = Path(state["output_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return payload


def run() -> dict[str, Any]:
    state = initialize()
    while state["cursor"] < len(state["paths"]):
        state = validate_next(state)
    return write_report(state)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = run()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("PASS quality cards" if payload["ok"] else "FAIL quality cards")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
