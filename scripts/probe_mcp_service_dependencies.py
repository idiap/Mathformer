#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make independent MCP service deployment dependency closure visible before a
#   long-running server is started.
#
# Intent:
#   Report Python package availability, external prover/toolchain availability,
#   and service config readiness without relying on agent skill environments.
#
# Function:
#   Emits JSON suitable for hub actions, self-checks, and operator diagnostics.
#
# Maintenance Notes:
#   Keep package names synchronized with requirements-mcp-service.txt and
#   config/mathformer_mcp.example.toml.

"""Probe dependencies for the independent Mathformer MCP service."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import shutil
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]

PYTHON_PACKAGES = {
    "mcp": {"distribution": "mcp", "required": True, "family": "mcp"},
    "httpx": {"distribution": "httpx", "required": True, "family": "mcp"},
    "uvicorn": {"distribution": "uvicorn", "required": True, "family": "mcp"},
    "sympy": {"distribution": "sympy", "required": False, "family": "sympy"},
    "numpy": {"distribution": "numpy", "required": False, "family": "sympy"},
    "huggingface_hub": {
        "distribution": "huggingface_hub",
        "required": False,
        "family": "benchmark",
    },
    "docling": {"distribution": "docling", "required": False, "family": "paper"},
    "openai": {"distribution": "openai", "required": False, "family": "provider"},
    "anthropic": {"distribution": "anthropic", "required": False, "family": "provider"},
    "google-genai": {
        "distribution": "google-genai",
        "required": False,
        "family": "provider",
    },
}

EXTERNAL_TOOLS = {
    "lake": {"required": False, "family": "lean"},
    "lean": {"required": False, "family": "lean"},
    "vampire": {"required": False, "family": "atp"},
    "rocq": {"required": False, "family": "rocq"},
    "coqc": {"required": False, "family": "rocq"},
    "isabelle": {"required": False, "family": "isabelle"},
}


def package_status(name: str, metadata: dict[str, Any]) -> dict[str, Any]:
    distribution = str(metadata["distribution"])
    try:
        version = importlib.metadata.version(distribution)
        available = True
    except importlib.metadata.PackageNotFoundError:
        version = None
        available = False
    return {
        "name": name,
        "distribution": distribution,
        "available": available,
        "version": version,
        "required": bool(metadata["required"]),
        "family": metadata["family"],
    }


def tool_status(name: str, metadata: dict[str, Any]) -> dict[str, Any]:
    path = shutil.which(name)
    return {
        "name": name,
        "available": bool(path),
        "path": path,
        "required": bool(metadata["required"]),
        "family": metadata["family"],
    }


def parse_requirements(path: Path) -> list[str]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entries.append(stripped)
    return entries


def initialize_scans() -> dict[str, Any]:
    return {
        name: {"cursor": 0, "rows": [], "done": False} for name in ("packages", "tools")
    }


def scan_next(state: dict[str, Any], table: dict, probe: Any) -> dict[str, Any]:
    cursor = state["cursor"]
    if state["done"] or not 0 <= cursor < len(table) or len(state["rows"]) != cursor:
        raise ValueError("dependency scan cursor is out of bounds or inconsistent")
    name, meta = list(table.items())[cursor]
    row = probe(name, meta)
    return {
        "cursor": cursor + 1,
        "rows": state["rows"] + [row],
        "done": cursor + 1 == len(table),
    }


def package_next(state: dict[str, Any]) -> dict[str, Any]:
    return scan_next(state, PYTHON_PACKAGES, package_status)


def tool_next(state: dict[str, Any]) -> dict[str, Any]:
    return scan_next(state, EXTERNAL_TOOLS, tool_status)


def classify_dependencies(packages: list[dict], tools: list[dict]) -> dict[str, Any]:
    missing_required = [
        {"kind": "python_package", "name": item["name"], "family": item["family"]}
        for item in packages
        if item["required"] and not item["available"]
    ] + [
        {"kind": "external_tool", "name": item["name"], "family": item["family"]}
        for item in tools
        if item["required"] and not item["available"]
    ]
    optional_blockers = [
        {"kind": "python_package", "name": item["name"], "family": item["family"]}
        for item in packages
        if not item["required"] and not item["available"]
    ] + [
        {"kind": "external_tool", "name": item["name"], "family": item["family"]}
        for item in tools
        if not item["required"] and not item["available"]
    ]
    return {
        "missing_required": missing_required,
        "optional_blockers": optional_blockers,
        "ready": not missing_required,
    }


def read_service_requirements() -> list[str]:
    return parse_requirements(REPO_ROOT / "requirements-mcp-service.txt")


def assemble_report(
    packages: list[dict],
    tools: list[dict],
    missing: dict,
    requirements: list[str],
    status: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "style": "mathformer_mcp_service_dependency_report",
        "ok": True,
        "ready": missing["ready"],
        "status": status,
        "requirements_file": "requirements-mcp-service.txt",
        "requirements": requirements,
        "python_packages": packages,
        "external_tools": tools,
        "missing_required": missing["missing_required"],
        "optional_blockers": missing["optional_blockers"],
    }


def build_dependency_report() -> dict[str, Any]:
    scans = initialize_scans()
    packages, tools = scans["packages"], scans["tools"]
    while not packages["done"]:
        packages = package_next(packages)
    while not tools["done"]:
        tools = tool_next(tools)
    missing = classify_dependencies(packages["rows"], tools["rows"])
    requirements = read_service_requirements()
    return assemble_report(
        packages["rows"],
        tools["rows"],
        missing,
        requirements,
        "ready" if missing["ready"] else "blocked",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = build_dependency_report()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("ok" if payload["ok"] else "failed")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
