#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

# File Documentation
#
# Motivation:
#   Automate repository maintenance tasks that would be error-prone if performed by hand.
#
# Intent:
#   Expose command-line entry points for setup, generation, indexing, auditing, and proof execution.
#
# Function:
#   Implements operational glue used by tests, skills, docs, and developer workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Generate fresh SymPy autoformalizations for the FormalPhysics top-10 samples."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.sympy.MathformerPhysicsSympy import (
    pipeline,
)

SOURCE_ROOT = REPO_ROOT / "data/benchmarks/formal_science/physics_top10_sources"
ARTIFACT_ROOT = REPO_ROOT / "artifacts/physics_sympy/from_scratch_sympy"
LIB_ROOT = REPO_ROOT / "libraries/MathformerPhysicsLib/SymPy"


CASES: dict[str, dict[str, str]] = {
    "formalphysics_0000": {
        "rank": "01",
        "source_index": "0",
        "title": "Lorentz force x component from the charged-particle Lagrangian",
        "abstraction_surface": (
            "scalar coordinate-component equation with field-derivative placeholders "
            "grounded by SymPy scalar, calculus, units, vector, and mechanics APIs"
        ),
    },
    "formalphysics_0020": {
        "rank": "02",
        "source_index": "20",
        "title": "Maxwell-Ampere equation with polarization and magnetization",
        "abstraction_surface": (
            "vector-equation additive surface with operator-linearity placeholders "
            "grounded by SymPy scalar, calculus, units, vector, and matrix/linear-algebra APIs"
        ),
    },
    "formalphysics_0066": {
        "rank": "03",
        "source_index": "66",
        "title": "TDSE parameter identity from commuting mixed partials",
        "abstraction_surface": (
            "quantum scalar-projection surface with TDSE product-rule placeholders "
            "grounded by SymPy scalar algebra, calculus, units, and quantum operator APIs"
        ),
    },
    "formalphysics_0191": {
        "rank": "04",
        "source_index": "191",
        "title": "TDSE expectation derivative product-rule identity",
        "abstraction_surface": (
            "quantum expectation scalar-projection surface with ket and adjoint-bra "
            "substitution placeholders grounded by SymPy scalar, calculus, units, and quantum APIs"
        ),
    },
    "formalphysics_0172": {
        "rank": "05",
        "source_index": "172",
        "title": "Euler-Lagrange charged-particle x force balance",
        "abstraction_surface": (
            "coordinate-component force-balance surface with electromagnetic potential "
            "derivative placeholders grounded by SymPy scalar, mechanics, vector, and units APIs"
        ),
    },
    "formalphysics_0119": {
        "rank": "06",
        "source_index": "119",
        "title": "Lorentz cross-curl x component expansion",
        "abstraction_surface": (
            "coordinate-component cross-product/curl surface grounded by SymPy scalar, "
            "vector, units, and matrix/linear-algebra APIs"
        ),
    },
    "formalphysics_0026": {
        "rank": "07",
        "source_index": "26",
        "title": "Hellmann-Feynman theorem via normalization cancellation",
        "abstraction_surface": (
            "quantum expectation scalar-projection surface with eigenstate and normalization "
            "bridges grounded by SymPy scalar, calculus, units, and quantum operator APIs"
        ),
    },
    "formalphysics_0176": {
        "rank": "08",
        "source_index": "176",
        "title": "First variation evaluated at epsilon zero",
        "abstraction_surface": (
            "variational integral equation surface grounded by SymPy scalar algebra, "
            "calculus, units/action typing, and numeric validation APIs"
        ),
    },
    "formalphysics_0054": {
        "rank": "09",
        "source_index": "54",
        "title": "Ampere-Maxwell in matter with bound currents",
        "abstraction_surface": (
            "macroscopic electromagnetism current-density surface with constitutive-law "
            "and operator-linearity placeholders grounded by SymPy scalar, calculus, vector, and units APIs"
        ),
    },
    "formalphysics_0059": {
        "rank": "10",
        "source_index": "59",
        "title": "Variation chain-rule integral identity at epsilon zero",
        "abstraction_surface": (
            "variational chain-rule integral surface grounded by SymPy scalar algebra, "
            "calculus, units/action typing, and numeric validation APIs"
        ),
    },
}


def json_safe(value: Any) -> str:
    """Document the responsibility of ``json_safe``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Provide the local operation named ``json_safe`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def write_json(path: Path, value: Any) -> None:
    """Document the responsibility of ``write_json``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_safe(value) + "\n", encoding="utf-8")


def run_tool(args: list[str]) -> None:
    """Document the responsibility of ``run_tool``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    result = subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "tool failed: "
            + " ".join(args)
            + f"\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def source_path(case_id: str, spec: dict[str, str]) -> Path:
    """Document the responsibility of ``source_path``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Provide the local operation named ``source_path`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return SOURCE_ROOT / f"{spec['rank']}_{case_id}.tex"


def sha256_text(text: str) -> str:
    """Document the responsibility of ``sha256_text``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Provide the local operation named ``sha256_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def import_artifact(path: Path) -> Any:
    """Document the responsibility of ``import_artifact``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Provide the local operation named ``import_artifact`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    module_name = f"mathformer_sympy_artifact_{path.parent.name}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import generated artifact at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def status_from_bool(ok: bool) -> str:
    """Document the responsibility of ``status_from_bool``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Provide the local operation named ``status_from_bool`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return "pass" if ok else "fail"


def normalize_execution_report(report: dict[str, Any]) -> dict[str, Any]:
    """Document the responsibility of ``normalize_execution_report``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Provide the local operation named ``normalize_execution_report`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    normalized = dict(report)
    normalized["status"] = status_from_bool(bool(report.get("ok")))
    return normalized


def summary_for_case(
    *,
    case_id: str,
    case_spec: dict[str, str],
    source_ref: str,
    source_sha256: str,
    artifact: Path,
    consistency: dict[str, Any],
    execution: dict[str, Any],
    library_grounding: dict[str, Any],
    reports: dict[str, Path],
) -> dict[str, Any]:
    """Document the responsibility of ``summary_for_case``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Provide the local operation named ``summary_for_case`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    final_reviews = consistency["packets"]["final_reviews"]
    physics_review = final_reviews["physics_sympy_final_equation_review"]
    mathematical_review = final_reviews["mathematical_sympy_final_equation_review"]
    unit = execution["unit_analysis"]
    steps = execution["step_verification"]
    numeric = execution["numeric"]
    semantics = consistency["packets"]["sympy_semantics"]
    dimension_projection = consistency["packets"]["sympy_dimensions"]
    return {
        "case_id": case_id,
        "title": case_spec["title"],
        "status": consistency["status"],
        "source_ref": source_ref,
        "source_sha256": source_sha256,
        "source_index": case_spec["source_index"],
        "metrics": {
            "execution": 1.0 if execution.get("ok") else 0.0,
            "unit": 1.0 if unit["dimensionally_consistent"] else 0.0,
            "step": 1.0 if steps["passed"] else 0.0,
            "numeric": 1.0 if numeric["passed"] else 0.0,
            "semantics": 1.0 if semantics["status"] == "pass" else 0.0,
            "dimension_projection": (
                1.0 if dimension_projection["status"] == "pass" else 0.0
            ),
            "sympy_library_grounding": (
                1.0 if library_grounding["grounding_level"] == "high" else 0.0
            ),
            "physics_final_review": 1.0 if physics_review["status"] == "pass" else 0.0,
            "mathematical_final_review": (
                1.0 if mathematical_review["status"] == "pass" else 0.0
            ),
        },
        "validation_criteria": {
            "execution": bool(execution.get("ok")),
            "unit": bool(unit["dimensionally_consistent"]),
            "step": bool(steps["passed"]),
            "numeric": bool(numeric["passed"]),
            "semantics": semantics["status"] == "pass",
            "dimension_projection": dimension_projection["status"] == "pass",
            "sympy_library_grounding_high": library_grounding["grounding_level"]
            == "high",
            "physics_final_review": physics_review["status"] == "pass",
            "mathematical_final_review": mathematical_review["status"] == "pass",
        },
        "residual": str(execution["step_verification"]["residual"]),
        "numeric_residual": str(
            execution["numeric"]["target_value"]
            - execution["numeric"]["expected_value"]
        ),
        "abstraction_surface": case_spec["abstraction_surface"],
        "sympy_library_grounding": {
            "grounding_level": library_grounding["grounding_level"],
            "required_roles": library_grounding["required_roles"],
        },
        "artifact": str(artifact.relative_to(REPO_ROOT)),
        "reports": {
            key: str(path.relative_to(REPO_ROOT)) for key, path in reports.items()
        },
        "known_limits": [
            "SymPy validates an equational abstraction, not a full Lean-style vector calculus proof.",
            "Operator laws and coordinate/component projections are explicit assumptions and projection bridges.",
        ],
    }


def write_case(
    case_id: str, case_spec: dict[str, str], promote_lib: bool
) -> dict[str, Any]:
    """Document the responsibility of ``write_case``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    src = source_path(case_id, case_spec)
    source_text = src.read_text(encoding="utf-8")
    case_root = ARTIFACT_ROOT / case_id
    artifact = case_root / "MathformerPhysics.py"
    draft = pipeline.write_artifact(case_id, artifact)
    module = import_artifact(artifact)

    execution = normalize_execution_report(module.run_all())
    unit = module.validate_dimensions()
    step = module.validate_derivation_steps()
    numeric = module.validate_numeric_samples()
    equation_surface = module.EQUATION_SURFACE
    assumption_context = module.ASSUMPTION_CONTEXT
    library_grounding = module.validate_library_grounding()["grounding"]
    semantics = module.validate_equational_semantics()
    dimension_projection = module.run_all()["dimension_projection"]
    final_reviews = module.review_final_equations()
    consistency = pipeline.consistency_report(case_id)

    reports: dict[str, Path] = {
        "summary": case_root / "summary.json",
        "draft": case_root / "draft_report.json",
        "execution": case_root / "execution_report.json",
        "unit": case_root / "unit_report.json",
        "step": case_root / "step_report.json",
        "numeric": case_root / "numeric_report.json",
        "equation_surface": case_root / "equation_surface_report.json",
        "assumption_context": case_root / "assumption_context_report.json",
        "library_grounding": case_root / "library_grounding.json",
        "semantics_critic": case_root / "semantics_critic.json",
        "dimension_projection_critic": case_root / "dimension_projection_critic.json",
        "physics_final_review": case_root / "physics_final_review.json",
        "mathematical_final_review": case_root / "mathematical_final_review.json",
        "identity": case_root / "identity_report.json",
        "counterexample": case_root / "counterexample_report.json",
        "trace": case_root / "trace_report.json",
        "physics_final_review_external": case_root
        / "physics_final_review.external.json",
        "mathematical_final_review_external": case_root
        / "mathematical_final_review.external.json",
        "consistency": case_root / "physics_consistency_report.json",
        "workflow_plan": case_root / "workflow_plan.json",
    }

    write_json(reports["draft"], draft)
    write_json(reports["execution"], execution)
    write_json(reports["unit"], unit)
    write_json(reports["step"], step)
    write_json(reports["numeric"], numeric)
    write_json(reports["equation_surface"], equation_surface)
    write_json(reports["assumption_context"], assumption_context)
    write_json(reports["library_grounding"], library_grounding)
    write_json(reports["semantics_critic"], semantics)
    write_json(reports["dimension_projection_critic"], dimension_projection)
    write_json(
        reports["physics_final_review"],
        final_reviews["physics_sympy_final_equation_review"],
    )
    write_json(
        reports["mathematical_final_review"],
        final_reviews["mathematical_sympy_final_equation_review"],
    )
    write_json(reports["consistency"], consistency)
    write_json(
        reports["workflow_plan"],
        pipeline.phase_packet(
            "sympy_workflow", case_id, source_text, str(src.relative_to(REPO_ROOT))
        ),
    )
    pipeline.write_markdown(consistency, case_root / "physics_consistency_report.md")
    pipeline.write_html(consistency, case_root / "physics_consistency_report.html")

    run_tool(
        [
            "skills/sympy/sympy-identity-validator/scripts/validate_sympy_identity.py",
            "--artifact",
            str(artifact.relative_to(REPO_ROOT)),
            "--output",
            str(reports["identity"].relative_to(REPO_ROOT)),
        ]
    )
    run_tool(
        [
            "skills/sympy/sympy-counterexample-searcher/scripts/search_sympy_counterexamples.py",
            "--artifact",
            str(artifact.relative_to(REPO_ROOT)),
            "--output",
            str(reports["counterexample"].relative_to(REPO_ROOT)),
        ]
    )
    run_tool(
        [
            "skills/sympy/sympy-transformation-trace-verifier/scripts/verify_sympy_trace.py",
            "--artifact",
            str(artifact.relative_to(REPO_ROOT)),
            "--output",
            str(reports["trace"].relative_to(REPO_ROOT)),
        ]
    )
    run_tool(
        [
            "skills/physics-sympy/physics-sympy-final-equation-reviewer/scripts/review_physics_sympy_final_equations.py",
            "--execution-report",
            str(reports["execution"].relative_to(REPO_ROOT)),
            "--unit-report",
            str(reports["unit"].relative_to(REPO_ROOT)),
            "--step-report",
            str(reports["step"].relative_to(REPO_ROOT)),
            "--numeric-report",
            str(reports["numeric"].relative_to(REPO_ROOT)),
            "--equation-surface-report",
            str(reports["equation_surface"].relative_to(REPO_ROOT)),
            "--assumption-context-report",
            str(reports["assumption_context"].relative_to(REPO_ROOT)),
            "--semantics-report",
            str(reports["semantics_critic"].relative_to(REPO_ROOT)),
            "--dimension-projection-report",
            str(reports["dimension_projection_critic"].relative_to(REPO_ROOT)),
            "--library-grounding-report",
            str(reports["library_grounding"].relative_to(REPO_ROOT)),
            "--output",
            str(reports["physics_final_review_external"].relative_to(REPO_ROOT)),
        ]
    )
    run_tool(
        [
            "skills/sympy/mathematical-sympy-final-equation-reviewer/scripts/review_mathematical_sympy_final_equations.py",
            "--execution-report",
            str(reports["execution"].relative_to(REPO_ROOT)),
            "--identity-report",
            str(reports["identity"].relative_to(REPO_ROOT)),
            "--counterexample-report",
            str(reports["counterexample"].relative_to(REPO_ROOT)),
            "--trace-report",
            str(reports["trace"].relative_to(REPO_ROOT)),
            "--assumption-context",
            str(reports["assumption_context"].relative_to(REPO_ROOT)),
            "--output",
            str(reports["mathematical_final_review_external"].relative_to(REPO_ROOT)),
        ]
    )

    summary = summary_for_case(
        case_id=case_id,
        case_spec=case_spec,
        source_ref=str(src.relative_to(REPO_ROOT)),
        source_sha256=sha256_text(source_text),
        artifact=artifact,
        consistency=consistency,
        execution=execution,
        library_grounding=library_grounding,
        reports=reports,
    )
    write_json(reports["summary"], summary)

    if promote_lib:
        lib_dir = LIB_ROOT / case_id
        lib_dir.mkdir(parents=True, exist_ok=True)
        lib_artifact = lib_dir / "MathformerPhysics.py"
        shutil.copyfile(artifact, lib_artifact)
        lib_summary = dict(summary)
        lib_summary["artifact"] = str(lib_artifact.relative_to(REPO_ROOT))
        lib_summary["source_artifact"] = str(artifact.relative_to(REPO_ROOT))
        write_json(lib_dir / "summary.json", lib_summary)

    return summary


def initialize() -> dict[str, Any]:
    """Start the ordered case traversal; summaries carry no refinement state."""
    return {"cursor": 0, "summaries": [], "summaries_json": []}


def select_case(state: dict[str, Any]) -> dict[str, Any]:
    case_id, spec = list(CASES.items())[state["cursor"]]
    return {"id": case_id, "spec": spec}


def advance(
    state: dict[str, Any], summary: dict[str, Any], summary_json: str | None = None
) -> tuple[dict[str, Any], bool]:
    updated = {
        "cursor": state["cursor"] + 1,
        "summaries": [*state["summaries"], summary],
        "summaries_json": [
            *state["summaries_json"],
            json_safe(summary) if summary_json is None else summary_json,
        ],
    }
    return updated, updated["cursor"] == len(CASES)


def aggregate(state: dict[str, Any]) -> tuple[dict[str, Any], int]:
    # Preserve insertion order across transports that canonicalize JSON object keys.
    summaries = [json.loads(text) for text in state["summaries_json"]]
    result = {
        "backend": "sympy",
        "style": pipeline.STYLE,
        "case_count": len(summaries),
        "ok": all(summary["status"] == "complete" for summary in summaries),
        "summaries": summaries,
    }
    return result, 0 if result["ok"] else 3


def emit_json(result_json: str) -> str:
    text = result_json + "\n"
    print(text, end="")
    return text


def emit_paths(result: dict[str, Any]) -> str:
    text = "".join(
        path + "\n"
        for summary in result["summaries"]
        for path in (
            summary["artifact"],
            summary["reports"]["summary"],
            summary["reports"]["consistency"],
        )
    )
    print(text, end="")
    return text


def main() -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--promote-lib",
        action="store_true",
        help="also copy generated SymPy artifacts into libraries/MathformerPhysicsLib/SymPy",
    )
    parser.add_argument(
        "--json", action="store_true", help="print full JSON instead of generated paths"
    )
    args = parser.parse_args()

    state = initialize()
    for _ in CASES:
        case = select_case(state)
        summary = write_case(case["id"], case["spec"], args.promote_lib)
        state, _ = advance(state, summary)
    result, code = aggregate(state)
    if args.json:
        emit_json(json_safe(result))
    else:
        emit_paths(result)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
