#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Gate FormalPhysics Lean outputs against trivial grounding debt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = (
    REPO_ROOT / "artifacts" / "physics_lean" / "formal_science_grounding_debt"
)
MONITOR = "skills/physics-lean/physics-lean-drift-pathology-monitor/scripts/monitor_physics_lean_drift_pathologies.py"
CASE_0059 = (
    REPO_ROOT
    / "MathformerPhysicsLib"
    / "Lean"
    / "formalphysics_0059"
    / "MathformerPhysics.lean"
)
CASE_0191 = (
    REPO_ROOT
    / "MathformerPhysicsLib"
    / "Lean"
    / "formalphysics_0191"
    / "MathformerPhysics.lean"
)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON with a stable layout."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_json(args: list[str], *, repository_root: Path | None = None) -> dict[str, Any]:
    """Run a repository command and parse JSON stdout."""
    proc = subprocess.run(
        [sys.executable, *args],
        cwd=repository_root if repository_root is not None else REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(args)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


def monitor_text(
    source: str, lean: str, lean_path: str, *, repository_root: Path | None = None
) -> dict[str, Any]:
    """Run the drift monitor over inline source and Lean text."""
    return run_json(
        [
            MONITOR,
            "--source-text",
            source,
            "--lean-text",
            lean,
            "--lean-file",
            lean_path,
        ],
        repository_root=repository_root,
    )


def monitor_case(
    path: Path, source: str, *, repository_root: Path | None = None
) -> dict[str, Any]:
    """Run the drift monitor over a FormalPhysics Lean case."""
    return run_json(
        [
            MONITOR,
            "--source-text",
            source,
            "--lean-file",
            path.relative_to(
                repository_root if repository_root is not None else REPO_ROOT
            ).as_posix(),
        ],
        repository_root=repository_root,
    )


def debt_codes(report: dict[str, Any]) -> set[str]:
    """Return grounding-debt finding codes."""
    return {
        str(item.get("code"))
        for item in report.get("grounding_debt_report", {}).get("findings", [])
        if item.get("code")
    }


def text_has(path: Path, needles: Sequence[str]) -> bool:
    """Return whether all required fragments appear in a file."""
    text = path.read_text(encoding="utf-8")
    return all(needle in text for needle in needles)


def case_path(case_id: str, repository_root: Path | None = None) -> Path:
    """Resolve a fixed native case under the selected repository mount."""
    paths = {"0191": CASE_0191, "0059": CASE_0059}
    path = paths[case_id]
    return (
        path
        if repository_root is None
        else repository_root / path.relative_to(REPO_ROOT)
    )


def monitor_synthetic(*, repository_root: Path | None = None) -> dict[str, Any]:
    """Run the native synthetic regression exactly once."""
    return monitor_text(
        "A Hamiltonian source law and Hilbert-space state imply the result.",
        (
            "abbrev Law (_ : Prop) : Prop := True\n"
            "abbrev UnitDimensionCompatible (_ : Prop) : Prop := True\n"
            "theorem bad (source_law : True) (psi H : Real) "
            "(unit_dimension_bridge : UnitDimensionCompatible True) : True := by trivial\n"
        ),
        "libraries/MathformerPhysicsLib/Lean/formalphysics_9999/MathformerPhysics.lean",
        repository_root=repository_root,
    )


def monitor_named_case(
    case_id: str, *, repository_root: Path | None = None
) -> dict[str, Any]:
    """Run one of the two fixed native monitor cases."""
    sources = {
        "0191": "TDSE product differentiation uses Hilbert states, Hamiltonians, adjoint bra law, ket law, and parameter derivatives.",
        "0059": "Calculus of variations uses fixed endpoints, differentiation under the integral, and chain-rule integral substitution.",
    }
    return monitor_case(
        case_path(case_id, repository_root),
        sources[case_id],
        repository_root=repository_root,
    )


def construct_checks(
    bad: dict[str, Any],
    case_0191: dict[str, Any],
    case_0059: dict[str, Any],
    *,
    repository_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Construct all five checks, including file checks after negative findings."""
    root = repository_root if repository_root is not None else REPO_ROOT
    case_0191_path = case_path("0191", repository_root)
    case_0059_path = case_path("0059", repository_root)
    return [
        {
            "id": "trivial_support_debt_blocks",
            "ok": {
                "prop_true_support_definition",
                "local_law_shim_true",
                "source_law_typed_true",
            }
            <= debt_codes(bad),
            "detail": {"codes": sorted(debt_codes(bad))},
        },
        {
            "id": "formalphysics_0191_no_true_law_debt",
            "ok": "source_law_typed_true" not in debt_codes(case_0191)
            and "local_law_shim_true" not in debt_codes(case_0191),
            "detail": {"codes": sorted(debt_codes(case_0191))},
        },
        {
            "id": "formalphysics_0059_no_true_law_debt",
            "ok": "source_law_typed_true" not in debt_codes(case_0059)
            and "local_law_shim_true" not in debt_codes(case_0059),
            "detail": {"codes": sorted(debt_codes(case_0059))},
        },
        {
            "id": "formalphysics_0191_uses_hilbert_foundation_support",
            "ok": text_has(
                case_0191_path,
                [
                    "import MathformerPhysicsLib.Lean.Foundations",
                    "InnerProductSpace ℂ H",
                    "HilbertBoundedOperator",
                    "TimeDependentSchrodingerProductDifferentiationFrontier",
                ],
            ),
            "detail": {"file": case_0191_path.relative_to(root).as_posix()},
        },
        {
            "id": "formalphysics_0059_exposes_variational_derivative_integral_packet",
            "ok": text_has(
                case_0059_path,
                [
                    "VariationChainIntegralFrontier",
                    "differentiate_under_integral",
                    "chain_rule_integral_substitution",
                    "fixed_endpoints",
                ],
            ),
            "detail": {"file": case_0059_path.relative_to(root).as_posix()},
        },
    ]


def aggregate(checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Retain every check and compute the native aggregate."""
    return {
        "schema_version": 1,
        "style": "formal_science_grounding_debt_gate",
        "ok": all(check["ok"] for check in checks),
        "checks": checks,
    }


def report_path(repository_root: Path | None = None) -> Path:
    """Return the source-owned report location."""
    directory = (
        ARTIFACT_ROOT
        if repository_root is None
        else repository_root / "artifacts/physics_lean/formal_science_grounding_debt"
    )
    return directory / "report.json"


def write_report(
    report: dict[str, Any], *, repository_root: Path | None = None
) -> dict[str, Any]:
    """Publish with the native stable JSON writer and retain the report."""
    write_json(report_path(repository_root), report)
    return report


def emit_return(report: dict[str, Any], json_output: bool) -> int:
    """Print the native JSON or status line and return its exit code."""
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("PASS" if report["ok"] else "FAIL", "formal science grounding debt gate")
    return 0 if report["ok"] else 1


def main(
    argv: Sequence[str] | None = None, *, repository_root: Path | None = None
) -> int:
    """Run the compact FormalScience grounding-debt gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    bad = monitor_synthetic(repository_root=repository_root)
    case_0191 = monitor_named_case("0191", repository_root=repository_root)
    case_0059 = monitor_named_case("0059", repository_root=repository_root)
    checks = construct_checks(
        bad, case_0191, case_0059, repository_root=repository_root
    )
    report = aggregate(checks)
    write_report(report, repository_root=repository_root)
    return emit_return(report, args.json)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
