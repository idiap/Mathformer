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
#   Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.
#
# Intent:
#   Tell coding agents what context to load, what invariants to preserve, and how to validate their work.
#
# Function:
#   Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Measure and plan loops for maximizing mathlib grounding of Lean artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

from reasoning_log import (
    append_reasoning_log_entry,
)

SKILL_NAME = "mathlib-grounding-maximizer"
HOOK_ID = "mathlib.grounding_maximize"


def rel(path: Path) -> str:
    """Document the responsibility of ``rel``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``rel`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def utc_now() -> str:
    """Document the responsibility of ``utc_now``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``utc_now`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return datetime.now(timezone.utc).isoformat()


def append_event(
    reasoning_log: Optional[Path], step: str, payload: Dict[str, Any]
) -> None:
    """Document the responsibility of ``append_event``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``append_event`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if reasoning_log is None:
        return
    append_reasoning_log_entry(
        reasoning_log,
        step=step,
        payload={"skill": SKILL_NAME, "hook_id": HOOK_ID, **payload},
    )


def run_json_command(cmd: Sequence[str], *, timeout_sec: int = 120) -> Dict[str, Any]:
    """Document the responsibility of ``run_json_command``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    started = time.perf_counter()
    proc = subprocess.run(
        list(cmd),
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=timeout_sec,
    )
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    payload: Dict[str, Any]
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "parse_error": True,
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
        }
    payload["_command"] = list(cmd)
    payload["_returncode"] = proc.returncode
    payload["_duration_ms"] = duration_ms
    if proc.stderr:
        payload["_stderr_tail"] = proc.stderr[-2000:]
    return payload


def script_path(skill: str, script: str) -> str:
    """Document the responsibility of ``script_path``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``script_path`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    matches = list((REPO_ROOT / "skills").glob(f"*/{skill}/scripts/{script}"))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"expected one script for skill {skill!r}, found {len(matches)}"
        )
    return matches[0].relative_to(REPO_ROOT).as_posix()


def import_report_for(path: Path) -> Dict[str, Any]:
    """Document the responsibility of ``import_report_for``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``import_report_for`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return run_json_command(
        [
            sys.executable,
            script_path("mathlib-import-minimizer", "minimize_imports.py"),
            "--lean-file",
            rel(path),
            "--json",
        ],
        timeout_sec=60,
    )


def compat_report_for(path: Path, *, run_lake_check: bool) -> Dict[str, Any]:
    """Document the responsibility of ``compat_report_for``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``compat_report_for`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    cmd = [
        sys.executable,
        script_path("mathlib-compatibility-auditor", "check_mathlib_compat.py"),
        "--lean-file",
        rel(path),
        "--json",
    ]
    if run_lake_check:
        cmd.extend(["--run-lake-check", "--lake-workdir", "."])
    return run_json_command(cmd, timeout_sec=180 if run_lake_check else 60)


def realness_report_for(path: Path) -> Dict[str, Any]:
    """Document the responsibility of ``realness_report_for``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``realness_report_for`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return run_json_command(
        [
            sys.executable,
            script_path(
                "autoformalization-result-realness-verifier",
                "verify_artifact_realness.py",
            ),
            "--lean-file",
            rel(path),
            "--json",
        ],
        timeout_sec=60,
    )


def reference_free_report_for(paths: Sequence[Path]) -> Dict[str, Any]:
    """Document the responsibility of ``reference_free_report_for``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``reference_free_report_for`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    cmd = [
        sys.executable,
        script_path(
            "reference-free-critic-monitor", "monitor_reference_free_critics.py"
        ),
        "--no-reasoning-log",
        "--json",
    ]
    for path in paths:
        cmd.extend(["--lean-file", rel(path)])
    return run_json_command(cmd, timeout_sec=120)


def finding_count(report: Dict[str, Any], severity: Optional[str] = None) -> int:
    """Document the responsibility of ``finding_count``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings = report.get("findings", [])
    if severity is None:
        return len(findings) if isinstance(findings, list) else 0
    return sum(
        1
        for item in findings
        if isinstance(item, dict) and item.get("severity") == severity
    )


def has_broad_import(
    import_report: Dict[str, Any], compat_report: Dict[str, Any]
) -> bool:
    """Document the responsibility of ``has_broad_import``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_broad_import`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    for key in ("original_imports", "deduped_imports", "minimized_imports"):
        imports = import_report.get(key, [])
        if isinstance(imports, list) and "Mathlib" in imports:
            return True
    for item in compat_report.get("findings", []):
        if isinstance(item, dict) and item.get("code") == "broad_import_mathlib":
            return True
    return False


def add_todo(
    todos: List[Dict[str, Any]],
    *,
    priority: str,
    loop: str,
    file: str,
    task: str,
    evidence: Dict[str, Any],
    next_hook: str,
) -> None:
    """Document the responsibility of ``add_todo``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``add_todo`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    todos.append(
        {
            "status": "todo",
            "priority": priority,
            "loop": loop,
            "file": file,
            "task": task,
            "evidence": evidence,
            "next_hook": next_hook,
        }
    )


def todos_for_file(
    *,
    path: Path,
    import_report: Dict[str, Any],
    compat_report: Dict[str, Any],
    realness_report: Dict[str, Any],
    target_compatibility_score: int,
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``todos_for_file``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``todos_for_file`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    todos: List[Dict[str, Any]] = []
    file_name = rel(path)
    compat_score = int(compat_report.get("compatibility_score") or 0)

    if has_broad_import(import_report, compat_report):
        add_todo(
            todos,
            priority="P0",
            loop="import_loop",
            file=file_name,
            task="Replace broad `import Mathlib` with verified narrow imports, then re-run Lean and import-context checks.",
            evidence={
                "imports": import_report.get("original_imports", []),
                "suggested_import_block": import_report.get(
                    "suggested_import_block", ""
                ),
            },
            next_hook="mathlib.import.minimize",
        )

    realness_summary = realness_report.get("summary", {})
    blocking_realness = int(realness_summary.get("blocking_finding_count") or 0)
    if blocking_realness:
        add_todo(
            todos,
            priority="P0",
            loop="scaffold_realness_loop",
            file=file_name,
            task="Remove scaffold/mock/placeholder/finality blockers before the artifact can be treated as complete.",
            evidence={
                "blocking_finding_count": blocking_realness,
                "findings": realness_report.get("findings", [])[:5],
            },
            next_hook="artifact.realness_gate",
        )

    for item in compat_report.get("findings", []):
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        if code == "missing_doc_comment":
            add_todo(
                todos,
                priority="P2",
                loop="scaffold_realness_loop",
                file=file_name,
                task="Add an immediate source-aware doc comment to the undocumented declaration.",
                evidence=item,
                next_hook="annotate.line_comment_guard",
            )
        elif code not in {"broad_import_mathlib"}:
            add_todo(
                todos,
                priority="P1" if item.get("severity") in {"high", "medium"} else "P2",
                loop="native_api_loop",
                file=file_name,
                task="Resolve the compatibility-auditor finding by preferring mathlib-native APIs or documenting the abstraction boundary.",
                evidence=item,
                next_hook="audit.compatibility",
            )

    if compat_score < target_compatibility_score:
        add_todo(
            todos,
            priority="P1",
            loop="native_api_loop",
            file=file_name,
            task="Raise the compatibility score to the configured target through concept coverage, API replacement, and import refinement.",
            evidence={
                "compatibility_score": compat_score,
                "target_compatibility_score": target_compatibility_score,
                "compatibility_band": compat_report.get("compatibility_band"),
            },
            next_hook="mathlib.compatibility_loop",
        )

    return todos


def summarize_file(
    *,
    path: Path,
    import_report: Dict[str, Any],
    compat_report: Dict[str, Any],
    realness_report: Dict[str, Any],
    todos: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Document the responsibility of ``summarize_file``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``summarize_file`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    realness_summary = realness_report.get("summary", {})
    return {
        "file": rel(path),
        "ok": not todos,
        "imports": import_report.get("original_imports", []),
        "broad_import": has_broad_import(import_report, compat_report),
        "compatibility_score": compat_report.get("compatibility_score"),
        "compatibility_band": compat_report.get("compatibility_band"),
        "critical_review_score": compat_report.get("critical_review_score"),
        "realness_ok": realness_report.get("ok"),
        "realness_blocking_finding_count": realness_summary.get(
            "blocking_finding_count", 0
        ),
        "compatibility_finding_count": finding_count(compat_report),
        "todo_count": len(todos),
        "todos": todos,
    }


def compare_baseline(
    report: Dict[str, Any], baseline_file: Optional[Path]
) -> Dict[str, Any]:
    """Document the responsibility of ``compare_baseline``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``compare_baseline`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if baseline_file is None or not baseline_file.exists():
        return {
            "baseline_present": False,
            "ok": True,
            "regressions": [],
            "improvements": [],
        }
    baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
    current_summary = report["summary"]
    baseline_summary = baseline.get("summary", {})
    regressions: List[Dict[str, Any]] = []
    improvements: List[Dict[str, Any]] = []

    nondecreasing = ["min_compatibility_score", "reference_free_confidence_score"]
    nonincreasing = [
        "broad_import_count",
        "realness_blocking_finding_count",
        "todo_count",
    ]
    for key in nondecreasing:
        old = baseline_summary.get(key)
        new = current_summary.get(key)
        if isinstance(old, (int, float)) and isinstance(new, (int, float)):
            if new < old:
                regressions.append({"metric": key, "baseline": old, "current": new})
            elif new > old:
                improvements.append({"metric": key, "baseline": old, "current": new})
    for key in nonincreasing:
        old = baseline_summary.get(key)
        new = current_summary.get(key)
        if isinstance(old, (int, float)) and isinstance(new, (int, float)):
            if new > old:
                regressions.append({"metric": key, "baseline": old, "current": new})
            elif new < old:
                improvements.append({"metric": key, "baseline": old, "current": new})
    return {
        "baseline_present": True,
        "ok": not regressions,
        "regressions": regressions,
        "improvements": improvements,
    }


def build_report(
    *,
    lean_files: Sequence[Path],
    target_compatibility_score: int,
    target_reference_free_score: int,
    run_lake_check: bool,
    baseline_file: Optional[Path],
    reasoning_log_file: Optional[Path],
) -> Dict[str, Any]:
    """Document the responsibility of ``build_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    append_event(
        reasoning_log_file,
        "mathlib_grounding_maximization_start",
        {
            "lean_files": [rel(path) for path in lean_files],
            "target_compatibility_score": target_compatibility_score,
            "target_reference_free_score": target_reference_free_score,
        },
    )
    file_reports: List[Dict[str, Any]] = []
    all_todos: List[Dict[str, Any]] = []
    for index, path in enumerate(lean_files, start=1):
        append_event(
            reasoning_log_file,
            "mathlib_grounding_maximization_round_start",
            {"round_index": index, "lean_file": rel(path)},
        )
        import_report = import_report_for(path)
        compat_report = compat_report_for(path, run_lake_check=run_lake_check)
        realness_report = realness_report_for(path)
        todos = todos_for_file(
            path=path,
            import_report=import_report,
            compat_report=compat_report,
            realness_report=realness_report,
            target_compatibility_score=target_compatibility_score,
        )
        all_todos.extend(todos)
        file_report = summarize_file(
            path=path,
            import_report=import_report,
            compat_report=compat_report,
            realness_report=realness_report,
            todos=todos,
        )
        file_report["raw_reports"] = {
            "import_minimizer": import_report,
            "compatibility_audit": compat_report,
            "realness": realness_report,
        }
        file_reports.append(file_report)
        append_event(
            reasoning_log_file,
            "mathlib_grounding_measurement_complete",
            {
                "lean_file": rel(path),
                "compatibility_score": file_report.get("compatibility_score"),
                "broad_import": file_report["broad_import"],
                "todo_count": len(todos),
            },
        )

    reference_free_report = reference_free_report_for(lean_files)
    reference_summary = reference_free_report.get("summary", {})
    reference_free_score = int(
        reference_summary.get("reference_free_confidence_score") or 0
    )
    if reference_free_score < target_reference_free_score:
        all_todos.append(
            {
                "status": "todo",
                "priority": "P1",
                "loop": "monotonicity_loop",
                "file": "*",
                "task": "Raise the set-level reference-free confidence score without increasing hard risks or shrinking source/theorem surfaces.",
                "evidence": {
                    "reference_free_confidence_score": reference_free_score,
                    "target_reference_free_score": target_reference_free_score,
                    "weak_dimension_count": reference_summary.get(
                        "weak_dimension_count"
                    ),
                },
                "next_hook": "critique.reference_free_monitor",
            }
        )

    min_compatibility_score = min(
        [int(item.get("compatibility_score") or 0) for item in file_reports],
        default=0,
    )
    broad_import_count = sum(1 for item in file_reports if item["broad_import"])
    realness_blockers = sum(
        int(item.get("realness_blocking_finding_count") or 0) for item in file_reports
    )
    summary = {
        "file_count": len(file_reports),
        "min_compatibility_score": min_compatibility_score,
        "target_compatibility_score": target_compatibility_score,
        "reference_free_confidence_score": reference_free_score,
        "target_reference_free_score": target_reference_free_score,
        "broad_import_count": broad_import_count,
        "realness_blocking_finding_count": realness_blockers,
        "todo_count": len(all_todos),
        "files_below_target_count": sum(
            1
            for item in file_reports
            if int(item.get("compatibility_score") or 0) < target_compatibility_score
        ),
        "files_with_broad_imports": [
            item["file"] for item in file_reports if item["broad_import"]
        ],
    }
    report: Dict[str, Any] = {
        "generated_at_utc": utc_now(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": (
            min_compatibility_score >= target_compatibility_score
            and reference_free_score >= target_reference_free_score
            and broad_import_count == 0
            and realness_blockers == 0
            and not all_todos
        ),
        "summary": summary,
        "loop_sequence": [
            "import_loop",
            "native_api_loop",
            "concept_coverage_loop",
            "web_grounding_loop",
            "scaffold_realness_loop",
            "monotonicity_loop",
        ],
        "files": file_reports,
        "reference_free_report": reference_free_report,
        "todos": all_todos,
    }
    monotonicity = compare_baseline(report, baseline_file)
    report["monotonicity_comparison"] = monotonicity
    if not monotonicity["ok"]:
        report["ok"] = False
    append_event(
        reasoning_log_file,
        "mathlib_grounding_fix_plan_ready",
        {
            "ok": report["ok"],
            "todo_count": len(all_todos),
            "broad_import_count": broad_import_count,
        },
    )
    append_event(
        reasoning_log_file,
        "mathlib_grounding_monotonic_gate_complete",
        monotonicity,
    )
    append_event(
        reasoning_log_file,
        "mathlib_grounding_maximization_complete",
        {"ok": report["ok"], "summary": summary},
    )
    return report


def run_self_test() -> Dict[str, Any]:
    """Document the responsibility of ``run_self_test``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    with tempfile.TemporaryDirectory(prefix="mathlib-grounding-self-test-") as temp_dir:
        root = Path(temp_dir)
        clean = root / "Clean.lean"
        broad = root / "Broad.lean"
        clean.write_text(
            "\n".join(
                [
                    "import Mathlib.Init",
                    "",
                    "/--",
                    "Original source (NL): Truth is derivable.",
                    "Original source (LaTeX): `\\mathrm{True}`.",
                    "-/",
                    "theorem clean_truth : True := by",
                    "  trivial",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        broad.write_text(
            "\n".join(
                [
                    "import Mathlib",
                    "",
                    "/--",
                    "Original source (NL): Truth is derivable.",
                    "Original source (LaTeX): `\\mathrm{True}`.",
                    "-/",
                    "theorem broad_truth : True := by",
                    "  trivial",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        report = build_report(
            lean_files=[clean, broad],
            target_compatibility_score=100,
            target_reference_free_score=1,
            run_lake_check=False,
            baseline_file=None,
            reasoning_log_file=None,
        )
    broad_todo_detected = any(
        todo.get("loop") == "import_loop" and "Broad.lean" in str(todo.get("file"))
        for todo in report["todos"]
    )
    self_test_ok = broad_todo_detected and not report["ok"]
    return {
        "ok": self_test_ok,
        "generated_at_utc": utc_now(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "self_test": {
            "broad_import_todo_detected": broad_todo_detected,
            "fixture_report_ok": report["ok"],
            "todo_count": len(report["todos"]),
        },
        "report": report,
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Document the responsibility of ``parse_args``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lean-file", action="append", type=Path, default=[])
    parser.add_argument("--target-compatibility-score", type=int, default=100)
    parser.add_argument("--target-reference-free-score", type=int, default=80)
    parser.add_argument("--run-lake-check", action="store_true")
    parser.add_argument("--baseline-file", type=Path)
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--reasoning-log-file", type=Path)
    parser.add_argument("--expect-ok", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def render_text(report: Dict[str, Any]) -> str:
    """Document the responsibility of ``render_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    summary = report["summary"]
    lines = [
        f"ok: {report['ok']}",
        f"files: {summary['file_count']}",
        f"min_compatibility_score: {summary['min_compatibility_score']}",
        f"reference_free_confidence_score: {summary['reference_free_confidence_score']}",
        f"broad_import_count: {summary['broad_import_count']}",
        f"realness_blocking_finding_count: {summary['realness_blocking_finding_count']}",
        f"todos: {summary['todo_count']}",
    ]
    for todo in report.get("todos", [])[:20]:
        lines.append(
            f"- {todo['priority']} {todo['loop']} {todo['file']}: {todo['task']}"
        )
    if len(report.get("todos", [])) > 20:
        lines.append(f"... {len(report['todos']) - 20} more todos")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    args = parse_args(argv)
    if args.self_test:
        report = run_self_test()
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"ok: {report['ok']}")
        return 0 if report["ok"] else 3

    if not args.lean_file:
        print(
            "error: at least one --lean-file is required unless --self-test is used",
            file=sys.stderr,
        )
        return 2

    lean_files = [
        (REPO_ROOT / path).resolve() if not path.is_absolute() else path
        for path in args.lean_file
    ]
    missing = [str(path) for path in lean_files if not path.exists()]
    if missing:
        print(f"error: missing Lean files: {', '.join(missing)}", file=sys.stderr)
        return 2

    try:
        report = build_report(
            lean_files=lean_files,
            target_compatibility_score=args.target_compatibility_score,
            target_reference_free_score=args.target_reference_free_score,
            run_lake_check=args.run_lake_check,
            baseline_file=args.baseline_file,
            reasoning_log_file=args.reasoning_log_file,
        )
    except Exception as exc:  # pragma: no cover - defensive CLI boundary.
        append_event(
            args.reasoning_log_file,
            "mathlib_grounding_maximization_error",
            {"error": str(exc)},
        )
        raise

    if args.output_file is not None:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        args.output_file.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if args.write_baseline:
        baseline_file = args.baseline_file or Path(
            "artifacts/mathlib_grounding/baseline.json"
        )
        baseline_file.parent.mkdir(parents=True, exist_ok=True)
        baseline_file.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    return 3 if args.expect_ok and not report["ok"] else 0


if __name__ == "__main__":
    sys.exit(main())
