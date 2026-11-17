#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Run the MathformerPhysicsLib foundations workflow smoke test."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = (
    REPO_ROOT
    / "artifacts"
    / "mathformerphysicslib"
    / "foundations"
    / "controlled_suite"
)


def run_json(*args: str, repository_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Run a command and parse JSON stdout."""
    proc = subprocess.run(
        [sys.executable, *args],
        cwd=repository_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed: {args}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


CONCEPTS = [
    "real vector field on Euclidean 3-space",
    "component projection",
    "linear operator",
    "curl-like differential operator",
    "time derivative operator",
    "source-backed physical law witness",
    "dimension-compatible equality",
    "generated support assumption label",
    "complete Hilbert inner product state space",
    "orthogonal projection in a Hilbert space",
    "orthonormal Hilbert basis and Parseval coordinates",
    "bounded self-adjoint Hilbert operator",
    "unbounded position and momentum operators with dense common invariant domain and canonical commutator",
    "Schwartz wavefunction position-momentum model",
    "real-line L2 Schwartz-to-L2 instantiation for position and momentum",
    "Hilbert-Schmidt operator norm from matrix trace inner product",
]


def prepare(repository_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Create the native artifact directory and initial concept argv state."""
    artifact_dir = repository_root / ARTIFACT_DIR.relative_to(REPO_ROOT)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        name: str(artifact_dir / filename)
        for name, filename in (
            ("intake", "intake.json"),
            ("surface_plan", "surface_plan.json"),
            ("draft_report", "draft_report.json"),
            ("verification_report", "verification_report.json"),
            ("workbench", "workbench.json"),
        )
    }
    intake_cmd = [
        "skills/physics-common/physics-foundation-object-intake/scripts/intake_physics_foundation_objects.py",
        "--packet-id",
        "priority_1_foundations",
        "--output",
        paths["intake"],
        "--json",
    ]
    return {"paths": paths, "state": {"argv": intake_cmd, "cursor": 0}}


def append_concept(state: dict[str, Any]) -> dict[str, Any]:
    """Advance the fixed native iterator by exactly one concept."""
    cursor = state["cursor"]
    if not 0 <= cursor < len(CONCEPTS):
        raise ValueError("Concept iterator is outside its source-owned bounds")
    argv = [*state["argv"], "--concept", CONCEPTS[cursor]]
    cursor += 1
    return {"state": {"argv": argv, "cursor": cursor}, "done": cursor == len(CONCEPTS)}


def intake(state: dict, paths: dict, repository_root: Path = REPO_ROOT) -> dict:
    """Run intake, retaining the file handoff and parsed stdout."""
    return {
        "packet": paths["intake"],
        "report": run_json(*state["argv"], repository_root=repository_root),
    }


def surface(packet: str, paths: dict, repository_root: Path = REPO_ROOT) -> dict:
    """Run the native surface command without changing its arguments."""
    report = run_json(
        "skills/mathformerphysicslib/mathformerphysicslib-foundation-surface-designer/scripts/design_foundation_surfaces.py",
        "--object-packet",
        packet,
        "--output",
        paths["surface_plan"],
        "--json",
        repository_root=repository_root,
    )
    return {"plan": paths["surface_plan"], "report": report}


def draft(plan: str, paths: dict, repository_root: Path = REPO_ROOT) -> dict:
    """Run the native draft command without changing its arguments."""
    report = run_json(
        "skills/mathformerphysicslib/mathformerphysicslib-foundation-drafter/scripts/draft_foundation_modules.py",
        "--surface-plan",
        plan,
        "--output",
        paths["draft_report"],
        "--json",
        repository_root=repository_root,
    )
    return {"report": report}


def verify(paths: dict, repository_root: Path = REPO_ROOT) -> dict:
    """Run the native verify command without changing its arguments."""
    report = run_json(
        "skills/mathformerphysicslib/mathformerphysicslib-foundation-verifier/scripts/verify_foundation_modules.py",
        "--output",
        paths["verification_report"],
        "--json",
        repository_root=repository_root,
    )
    return {"report": report}


def workbench(packet: str, paths: dict, repository_root: Path = REPO_ROOT) -> dict:
    """Run the native workbench command without changing its arguments."""
    report = run_json(
        "skills/mathformerphysicslib/mathformerphysicslib-object-workbench/scripts/build_mathformerphysicslib_object_workbench.py",
        "--object-packet",
        packet,
        "--output",
        paths["workbench"],
        "--json",
        repository_root=repository_root,
    )

    return {"report": report}


def evaluate(
    paths: dict,
    intake: dict,
    surface: dict,
    draft: dict,
    verify: dict,
    workbench: dict,
    repository_root: Path = REPO_ROOT,
) -> dict:
    """Apply the nine native checks and assemble the unchanged summary."""
    checks = {
        "intake_has_priority_1": intake["object_count"] >= 12,
        "intake_has_hilbert_surfaces": {
            "hilbert_state.inner_product_space",
            "hilbert_state.orthogonality_projection",
            "hilbert_state.orthonormal_basis",
            "hilbert_operator.adjoint_self_adjoint",
            "unbounded_operator.position_momentum_core",
            "position_momentum.schwartz_l2_model",
            "position_momentum.real_line_l2_instantiation",
            "hilbert_operator.hilbert_schmidt",
        }
        <= {item["object_id"] for item in intake["objects"]},
        "surface_plan_complete": surface["terminal_state"] == "surface_plan_complete",
        "surface_plan_has_hilbert_module": "libraries/MathformerPhysicsLib/Lean/Foundations/HilbertSpace.lean"
        in surface["accepted_index_imports"],
        "surface_plan_is_recursive": surface["recursive_policy"]["recursive"] is True
        and surface["recursive_policy"][
            "initial_surfaces_are_level_0_not_terminal_theory"
        ]
        is True,
        "hilbert_recursive_frontier_present": {
            "hilbert_state.inner_product_space",
            "hilbert_state.orthogonality_projection",
            "hilbert_state.orthonormal_basis",
            "hilbert_operator.adjoint_self_adjoint",
            "unbounded_operator.position_momentum_core",
            "position_momentum.schwartz_l2_model",
            "position_momentum.real_line_l2_instantiation",
            "hilbert_operator.hilbert_schmidt",
        }
        <= {item["object_id"] for item in surface["recursive_frontier"]},
        "draft_preview_only": draft["terminal_state"] == "draft_preview",
        "verification_passed": verify["ok"] is True,
        "workbench_reuses_foundations": workbench["reuse_count"] >= 3,
    }
    result = {
        "ok": all(checks.values()),
        "checks": checks,
        "artifacts": {
            "intake": str(Path(paths["intake"]).relative_to(repository_root)),
            "surface_plan": str(
                Path(paths["surface_plan"]).relative_to(repository_root)
            ),
            "draft_report": str(
                Path(paths["draft_report"]).relative_to(repository_root)
            ),
            "verification_report": str(
                Path(paths["verification_report"]).relative_to(repository_root)
            ),
            "workbench": str(Path(paths["workbench"]).relative_to(repository_root)),
        },
        "summary": {
            "object_count": intake["object_count"],
            "surface_count": surface["surface_count"],
            "verified_modules": verify["promotion_ready_count"],
            "workbench_reuse_count": workbench["reuse_count"],
            "recursive_frontier_count": surface["recursive_frontier_count"],
        },
    }
    return {"result": result, "rendered_result": json.dumps(result, indent=2)}


def emit(result: dict, json_mode: bool, rendered_result: str | None = None) -> dict:
    """Render native CLI output and retain the source exit-code decision."""
    if rendered_result is not None and json.loads(rendered_result) != result:
        raise ValueError("Rendered result differs from the native report")
    if json_mode:
        stdout = (
            json.dumps(result, indent=2) if rendered_result is None else rendered_result
        )
    else:
        stdout = "MathformerPhysicsLib foundations workflow: " + (
            "ok" if result["ok"] else "failed"
        )
    print(stdout)
    return {"stdout": stdout + "\n", "exit_code": 0 if result["ok"] else 1}


def main() -> int:
    """Run the foundations workflow suite through the shared native steps."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    prepared = prepare()
    paths, state = prepared["paths"], prepared["state"]
    for _concept in CONCEPTS:
        state = append_concept(state)["state"]
    intake_result = intake(state, paths)
    surface_result = surface(intake_result["packet"], paths)
    draft_result = draft(surface_result["plan"], paths)
    verify_result = verify(paths)
    workbench_result = workbench(intake_result["packet"], paths)
    result = evaluate(
        paths,
        intake_result["report"],
        surface_result["report"],
        draft_result["report"],
        verify_result["report"],
        workbench_result["report"],
    )
    return emit(result["result"], args.json, result["rendered_result"])["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
