#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Gate promoted cross-backend physics semantics independently of coverage."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILDER = REPO_ROOT / "tests/physics_sympy/run_cross_backend_semantic_packet.py"
MANIFEST = REPO_ROOT / "libraries/MathformerPhysicsLib/MANIFEST.json"


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "cross_backend_packet_builder", BUILDER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load cross-backend packet builder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def prepare_gate(manifest_path: Path | None = None):
    """Read source-owned case sets and load the native builder, even when empty."""
    manifest_path = MANIFEST if manifest_path is None else manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    registry = manifest.get("artifact_registry") or []
    promoted = {
        backend: {
            row["case_id"]
            for row in registry
            if row.get("backend") == backend and row.get("status") == "promoted"
        }
        for backend in ("Lean", "SymPy", "Isabelle")
    }
    registered = {
        backend: {row["case_id"] for row in registry if row.get("backend") == backend}
        for backend in ("Lean", "SymPy", "Isabelle")
    }
    aligned_cases = sorted(promoted["Lean"] & promoted["SymPy"])
    builder = load_builder()
    plan = {
        "aligned_cases": aligned_cases,
        "promoted": {key: sorted(value) for key, value in promoted.items()},
        "registered": {key: sorted(value) for key, value in registered.items()},
    }
    return plan, builder


def initial_cases():
    """Initialize the native accumulator (also the empty scan result)."""
    return []


def append_case(plan, cases, case_id, packet):
    """Accumulate one case; ordinary mismatches never terminate the scan."""
    registered = plan["registered"]
    expected_backends = {"lean", "sympy"}
    if case_id in registered["Isabelle"]:
        expected_backends.add("isabelle")
    observed = set(packet.get("semantic_parity", {}).get("backends", []))
    cases.append(
        {
            "case_id": case_id,
            "semantic_parity": packet.get("semantic_parity", {}).get("semantic_parity")
            is True,
            "expected_backends": sorted(expected_backends),
            "observed_backends": sorted(observed),
            "coverage_ok": expected_backends == observed,
            "source_digest": packet.get("physics_ir", {}).get("source_digest"),
            "ir_digest": packet.get("physics_ir", {}).get("ir_digest"),
            "findings": packet.get("semantic_parity", {}).get("findings", []),
        }
    )
    return cases


def build_report(plan, cases):
    """Report semantic parity and promotion coverage independently."""
    promoted = {key: set(value) for key, value in plan["promoted"].items()}
    coverage = {
        backend: {
            "promoted": sorted(promoted[backend]),
            "promoted_count": len(promoted[backend]),
            "absent_from_three_backend_intersection": sorted(
                promoted[backend]
                - (promoted["Lean"] & promoted["SymPy"] & promoted["Isabelle"])
            ),
        }
        for backend in promoted
    }
    payload = {
        "schema_version": 1,
        "style": "physics_cross_backend_parity_gate",
        "workflow_executed": True,
        "checks_passed": bool(cases)
        and all(item["semantic_parity"] and item["coverage_ok"] for item in cases),
        "artifact_status": "promoted",
        "library_status": "accepted",
        "release_ok": bool(cases)
        and all(item["semantic_parity"] and item["coverage_ok"] for item in cases),
        "case_count": len(cases),
        "cases": cases,
        "coverage": coverage,
    }
    payload["blockers"] = (
        [] if payload["release_ok"] else ["cross_backend_semantic_or_coverage_mismatch"]
    )
    payload["terminal_states"] = [] if payload["release_ok"] else ["blocked"]
    return payload


def emit_report(payload, json_output):
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if json_output
        else ("PASS" if payload["release_ok"] else "FAIL")
    )
    return 0 if payload["release_ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    plan, builder = prepare_gate()
    cases = initial_cases()
    for case_id in plan["aligned_cases"]:
        append_case(plan, cases, case_id, builder.build_packet(case_id))
    return emit_report(build_report(plan, cases), args.json)


if __name__ == "__main__":
    raise SystemExit(main())
