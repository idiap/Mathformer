#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Ensure meta-skills integrate with the independent MCP service through
#   workflow-level actions and central config, not per-skill draft tools.
#
# Intent:
#   Validate the MCP-facing meta-skill action boundary.
#
# Function:
#   Checks workflow action declarations, hub action ids, server tool names,
#   config-folder references, and draft generated-skill denial policy.
#
# Maintenance Notes:
#   Keep allowed MCP tools synchronized with scripts/mcp_server.py.

"""Validate meta-skill MCP workflow boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = REPO_ROOT / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import mathformer  # noqa: E402

WORKFLOW_ACTIONS = REPO_ROOT / "meta_skills" / "registry" / "workflow_actions.yaml"
OUTPUT_PATH = REPO_ROOT / "artifacts" / "mcp" / "meta_skill_service_self_test.json"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def mcp_tool_names(root: Path = REPO_ROOT) -> list[str]:
    server_text = (root / "scripts" / "mcp_server.py").read_text(encoding="utf-8")
    return sorted(set(re.findall(r"def (mathformer_[a-z_]+)\(", server_text)))


def load_boundary(path: Path) -> tuple[dict, dict]:
    data = load_json(path)
    registry = mathformer.build_registry()
    return data, registry


def check_action_row(row: dict, registry, findings: list[dict]) -> None:
    action_id = row.get("action_id")
    if action_id not in registry:
        findings.append(
            {
                "severity": "error",
                "code": "unknown_meta_workflow_action",
                "action_id": action_id,
            }
        )
    if row.get("draft_skill_execution") != "denied":
        findings.append(
            {
                "severity": "error",
                "code": "draft_skill_execution_not_denied",
                "action_id": action_id,
            }
        )


def check_tool_set(data: dict, findings: list[dict], root: Path) -> dict:
    actual_tools = set(mcp_tool_names(root))
    allowed_tools = set(data.get("allowed_mcp_tools", []))
    if actual_tools != allowed_tools:
        findings.append(
            {
                "severity": "error",
                "code": "mcp_tool_set_mismatch",
                "actual_tools": sorted(actual_tools),
                "allowed_tools": sorted(allowed_tools),
            }
        )

    return {"allowed": sorted(allowed_tools), "actual": sorted(actual_tools)}


def check_config_docs(findings: list[dict], root: Path) -> None:
    config_docs = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in [
            root / "config" / "README.md",
            root / "docs" / "architecture" / "MCP_SERVER.md",
            root / "docs" / "operations" / "INDEPENDENT_MCP_SERVICE_TODOS.md",
        ]
        if path.exists()
    ).lower()
    if "config/" not in config_docs or "api key" not in config_docs:
        findings.append({"severity": "error", "code": "config_api_key_docs_missing"})


def check_denied_surfaces(data: dict, findings: list[dict]) -> None:
    denied = set(data.get("denied_surfaces", []))
    required_denials = {
        "per_generated_skill_mcp_tools",
        "direct_draft_skill_execution",
        "skill_environment_api_key_loading",
    }
    missing_denials = sorted(required_denials - denied)
    if missing_denials:
        findings.append(
            {
                "severity": "error",
                "code": "missing_denied_surfaces",
                "missing": missing_denials,
            }
        )


def write_boundary_payload(
    data: dict,
    tools: dict,
    findings: list[dict],
    output_path: Path,
    workflow_actions_path: str,
) -> dict:
    allowed_tools, actual_tools = tools["allowed"], tools["actual"]
    payload = {
        "schema_version": 1,
        "style": "mathformer_meta_mcp_boundary_validation",
        "ok": not any(f["severity"] == "error" for f in findings),
        "workflow_actions": data.get("workflow_actions", []),
        "allowed_mcp_tools": sorted(allowed_tools),
        "actual_mcp_tools": sorted(actual_tools),
        "config_root": "config/",
        "workflow_actions_path": workflow_actions_path,
        "findings": findings,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return payload


def run() -> dict[str, Any]:
    data, registry = load_boundary(WORKFLOW_ACTIONS)
    findings: list[dict[str, Any]] = []
    for row in data.get("workflow_actions", []):
        check_action_row(row, registry, findings)
    tools = check_tool_set(data, findings, REPO_ROOT)
    check_config_docs(findings, REPO_ROOT)
    check_denied_surfaces(data, findings)
    return write_boundary_payload(
        data, tools, findings, OUTPUT_PATH, rel(WORKFLOW_ACTIONS)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = run()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("PASS MCP boundary" if payload["ok"] else "FAIL MCP boundary")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
