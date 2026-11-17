#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Give workflow routing a typed projection surface before broad prose search.
#
# Intent:
#   Build Mathformer skill projection cards from task registries and taxonomy
#   coordinates.
#
# Function:
#   Reads task registries, joins composed skills to workflow coordinates, writes
#   skill projection cards, and emits a report.
#
# Maintenance Notes:
#   Keep coordinate names synchronized with workflow_taxonomy.json.

"""Build meta-skill taxonomy projection cards."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_PATH = REPO_ROOT / "meta_skills" / "taxonomy" / "workflow_taxonomy.json"
TASK_ROOT = REPO_ROOT / "meta_skills" / "registry" / "tasks"
OUTPUT_PATH = REPO_ROOT / "meta_skills" / "taxonomy" / "skill_projection_cards.json"
REPORT_PATH = REPO_ROOT / "artifacts" / "meta_skills" / "skill_projection_report.json"


def rel(path: Path, root: Path | None = None) -> str:
    root = REPO_ROOT if root is None else root
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def initialize_build(
    output_path: Path,
    report_path: Path,
    root: Path = REPO_ROOT,
    taxonomy_path: Path | None = None,
    task_root: Path | None = None,
) -> dict[str, Any]:
    taxonomy = load_json(
        taxonomy_path
        if taxonomy_path is not None
        else root / "meta_skills/taxonomy/workflow_taxonomy.json"
    )
    coordinates = {row["task_id"]: row for row in taxonomy["workflow_coordinates"]}
    cards: dict[str, dict[str, Any]] = {}
    findings: list[dict[str, Any]] = []
    skill_paths = {
        path.parent.name: path.relative_to(root).as_posix()
        for path in (root / "skills").glob("*/*/SKILL.md")
    }
    return {
        "coordinates": coordinates,
        "skill_paths": skill_paths,
        "cards": cards,
        "findings": findings,
        "registries": [
            str(p)
            for p in sorted(
                (
                    task_root
                    if task_root is not None
                    else root / "meta_skills/registry/tasks"
                ).glob("*/task_registry.json")
            )
        ],
        "pending_cards": [],
        "card_order": [],
        "destinations": {
            "output_path": str(output_path),
            "report_path": str(report_path),
        },
        "repository_root": str(root),
    }


def accumulate_registry(state: dict[str, Any], registry_path: Path) -> None:
    coordinates, cards, findings, skill_paths = (
        state[k] for k in ("coordinates", "cards", "findings", "skill_paths")
    )
    data = load_json(registry_path)
    coord = coordinates.get(data["task_id"])
    if not coord and data["task_id"] != "_template":
        findings.append(
            {
                "severity": "warning",
                "code": "task_without_taxonomy_coordinate",
                "task_id": data["task_id"],
            }
        )
        return
    if data["task_id"] == "_template":
        return
    for skill in data.get("composed_skills", []):
        skill_id = skill["skill_id"]
        if skill_id not in cards:
            state["card_order"].append(skill_id)
        card = cards.setdefault(
            skill_id,
            {
                "skill_id": skill_id,
                "path": skill_paths.get(
                    skill_id, f"skills/<unknown>/{skill_id}/SKILL.md"
                ),
                "task_ids": [],
                "workflow_ids": [],
                "reasoning_types": [],
                "backend_families": [],
                "formal_system_targets": [],
                "object_domains": [],
                "risk_classes": [],
            },
        )
        card["task_ids"].append(data["task_id"])
        card["workflow_ids"].append(coord["workflow_id"])
        for field in (
            "reasoning_types",
            "backend_families",
            "formal_system_targets",
            "object_domains",
            "risk_classes",
        ):
            for item in coord[field]:
                if item not in card[field]:
                    card[field].append(item)


def registry_iteration(state: dict[str, Any]) -> dict[str, Any]:
    if state["registries"]:
        path = state["registries"][0]
        accumulate_registry(state, Path(path))
        state["registries"] = state["registries"][1:]
    return {"state": state, "done": not state["registries"]}


def prepare_card_pass(state: dict[str, Any]) -> dict[str, Any]:
    state["pending_cards"] = list(state["card_order"])
    return state


def normalize_card(state: dict[str, Any], card: dict[str, Any]) -> None:
    root = Path(state["repository_root"])
    findings = state["findings"]
    skill_path = root / card["path"]
    if not skill_path.exists():
        findings.append(
            {
                "severity": "error",
                "code": "projection_missing_skill_path",
                "skill_id": card["skill_id"],
                "path": rel(skill_path, root),
            }
        )
    for field in (
        "task_ids",
        "workflow_ids",
        "reasoning_types",
        "backend_families",
        "object_domains",
        "risk_classes",
    ):
        card[field] = sorted(set(card[field]))


def card_iteration(state: dict[str, Any]) -> dict[str, Any]:
    if state["pending_cards"]:
        key = state["pending_cards"][0]
        normalize_card(state, state["cards"][key])
        state["pending_cards"] = state["pending_cards"][1:]
    return {"state": state, "done": not state["pending_cards"]}


def write_cards(state: dict[str, Any]) -> dict[str, Any]:
    output_path = Path(state["destinations"]["output_path"])
    payload = {
        "schema_version": "mathformer.meta_skills.skill_projection_cards.v0.1",
        "generated_by": "meta_skills/scripts/build_skill_projections.py",
        "cards": sorted(state["cards"].values(), key=lambda row: row["skill_id"]),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return {
        "state": state,
        "output": rel(output_path, Path(state["repository_root"])),
        "card_count": len(payload["cards"]),
    }


def write_report(written: dict[str, Any]) -> dict[str, Any]:
    state = written["state"]
    report_path = Path(state["destinations"]["report_path"])
    report = {
        "schema_version": 1,
        "style": "mathformer_meta_skill_projection_report",
        "ok": not any(f["severity"] == "error" for f in state["findings"]),
        "card_count": written["card_count"],
        "output": written["output"],
        "findings": state["findings"],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    return report


def build(
    output_path: Path = OUTPUT_PATH, report_path: Path = REPORT_PATH
) -> dict[str, Any]:
    state = initialize_build(
        output_path, report_path, REPO_ROOT, TAXONOMY_PATH, TASK_ROOT
    )
    while state["registries"]:
        registry_iteration(state)
    prepare_card_pass(state)
    while state["pending_cards"]:
        card_iteration(state)
    return write_report(write_cards(state))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build(args.output, args.report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("PASS skill projections" if report["ok"] else "FAIL skill projections")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
