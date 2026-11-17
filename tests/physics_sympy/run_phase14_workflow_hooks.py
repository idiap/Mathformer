#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.
#
# Intent:
#   Encode regression checks that catch parser breakage, semantic drift, and missing workflow evidence.
#
# Function:
#   Contains executable tests, fixtures, and manifests used for local and CI validation.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Check Phase 14 workflow hooks and loop integration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_PATH = REPO_ROOT / "skills" / "SKILL_HOOKS.yaml"
WORKFLOW_PLAN_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "physics-sympy"
    / "physics-sympy-workflow-orchestrator"
    / "scripts"
    / "build_physics_sympy_workflow_plan.py"
)

REQUIRED_HOOK_IDS = [
    "physics.dependencies.probe",
    "physics.source.extract",
    "physics.symbols.build",
    "physics.dimensions.model",
    "physics.units.ground",
    "physics.equations.parse",
    "physics.regimes.model",
    "physics.frames.build",
    "physics.gaps.detect",
    "physics.gaps.expand",
    "physics.laws.ground",
    "draft.physics_sympy_derivation",
    "execute.physics_sympy_derivation",
    "physics.units.verify",
    "physics.steps.verify",
    "physics.numeric.sample",
    "consistency.physics_derivation_report",
]

REQUIRED_DIRECT_ROUTES = {
    "autoformalize physics derivation with SymPy": "physics-sympy-derivation-drafter",
    "derive physics result in SymPy": "physics-sympy-derivation-drafter",
    "run physics unit analysis": "physics-unit-analysis-verifier",
    "close implicit physics derivation gaps": "physics-derivation-gap-expander",
    "verify physics derivation trace": "physics-derivation-step-verifier",
}

REQUIRED_LOOP_ITEMS = set(REQUIRED_HOOK_IDS) | {
    "sympy_physics_derivation_trace_loop",
    "critique.reference_free_monitor",
    "evaluation.rfde_report",
    "duration_ms",
    "agent_usage",
    "cost_trace_policy",
}


def extract_loop_block(text: str, loop_id: str) -> str:
    """Return one loop-contract block from the hook manifest."""
    marker = f"  - id: {loop_id}"
    start = text.find(marker)
    if start < 0:
        return ""
    next_start = text.find("\n  - id: ", start + len(marker))
    if next_start < 0:
        next_start = len(text)
    return text[start:next_start]


def direct_routes(text: str) -> Dict[str, str]:
    """Parse the direct request routing block."""
    marker = "direct_request_routing:"
    start = text.find(marker)
    if start < 0:
        return {}
    block = text[start + len(marker) :]
    routes: Dict[str, str] = {}
    for raw_line in block.splitlines():
        if raw_line and not raw_line.startswith(" "):
            break
        stripped = raw_line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        routes[key.strip()] = value.strip()
    return routes


def run_workflow_plan() -> Dict[str, Any]:
    """Run the deterministic workflow-plan script and return its JSON output."""
    completed = subprocess.run(
        [sys.executable, str(WORKFLOW_PLAN_SCRIPT), "--self-test", "--json"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def run_check() -> Dict[str, Any]:
    """Validate Phase 14 hook and workflow-loop coverage."""
    findings: List[str] = []
    text = HOOKS_PATH.read_text(encoding="utf-8")
    hook_ids = {
        line.strip().split("id:", 1)[1].strip()
        for line in text.splitlines()
        if line.strip().startswith("- id:")
    }
    missing_hooks = sorted(set(REQUIRED_HOOK_IDS) - hook_ids)
    if missing_hooks:
        findings.append(f"missing required hook ids: {missing_hooks}")

    loop_block = extract_loop_block(text, "sympy_physics_derivation_trace_loop")
    if not loop_block:
        findings.append("missing sympy_physics_derivation_trace_loop")
    for item in sorted(REQUIRED_LOOP_ITEMS):
        if item not in loop_block:
            findings.append(f"loop missing required item: {item}")

    routes = direct_routes(text)
    for route, owner in REQUIRED_DIRECT_ROUTES.items():
        if routes.get(route) != owner:
            findings.append(
                f"direct route mismatch for {route!r}: {routes.get(route)!r}"
            )

    for owner in set(REQUIRED_DIRECT_ROUTES.values()):
        if not any((REPO_ROOT / "skills").glob(f"*/{owner}/SKILL.md")):
            findings.append(f"direct-route owner skill missing: {owner}")

    plan = run_workflow_plan()
    for hook_id in REQUIRED_HOOK_IDS:
        if hook_id not in plan["required_hooks"]:
            findings.append(f"workflow plan missing required hook: {hook_id}")
    for recommended in ["critique.reference_free_monitor", "evaluation.rfde_report"]:
        if recommended not in plan["recommended_hooks"]:
            findings.append(
                f"workflow plan missing recommended RFDE hook: {recommended}"
            )
    if (
        plan.get("rfde_trajectory_reporting", {}).get("required_report")
        != "consistency.physics_derivation_report"
    ):
        findings.append(
            "workflow plan does not connect RFDE trajectory reporting to consistency report"
        )
    if plan.get("cost_accounting", {}).get("required_payload_fields") != [
        "duration_ms",
        "agent_usage",
    ]:
        findings.append("workflow plan cost accounting fields are missing or malformed")
    protected = " ".join(plan.get("protected_evidence", []))
    if "RFDE trajectory" not in protected or "cost trace" not in protected:
        findings.append(
            "workflow plan protected evidence does not include RFDE trajectory and cost trace"
        )

    return {
        "ok": not findings,
        "backend": "sympy",
        "style": "sympy_physics_derivation_trace",
        "phase": "phase14_workflow_hooks_and_loop_integration",
        "findings": findings,
        "required_hook_count": len(REQUIRED_HOOK_IDS),
        "required_direct_route_count": len(REQUIRED_DIRECT_ROUTES),
        "loop_present": bool(loop_block),
        "workflow_plan_status": plan.get("status"),
    }


def main() -> int:
    """Serve as the command-line entry point for the Phase 14 validation check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_check()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"ok: {report['ok']}")
        print(f"findings: {len(report['findings'])}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
