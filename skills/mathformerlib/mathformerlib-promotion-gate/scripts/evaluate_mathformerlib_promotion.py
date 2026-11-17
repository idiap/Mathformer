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

"""Evaluate whether a Lean artifact may be promoted into Mathformerlib."""

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

SKILL_NAME = "mathformerlib-promotion-gate"
HOOK_ID = "mathformerlib.promotion_gate"
REALNESS_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "autoformalization"
    / "autoformalization-result-realness-verifier"
    / "scripts"
    / "verify_artifact_realness.py"
)


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


def run_realness(args: argparse.Namespace) -> Dict[str, Any]:
    """Document the responsibility of ``run_realness``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    cmd = [sys.executable, str(REALNESS_SCRIPT), "--artifact-status", "final", "--json"]
    if args.lean_file is not None:
        cmd.extend(["--lean-file", str(args.lean_file)])
    else:
        cmd.extend(["--text", args.text or "", "--name", args.name])
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "summary": {"blocking_finding_count": 1},
            "findings": [
                {
                    "severity": "high",
                    "code": "realness_output_parse_error",
                    "message": proc.stderr
                    or proc.stdout
                    or "realness verifier did not emit JSON",
                }
            ],
        }
    payload["returncode"] = proc.returncode
    return payload


def compile_lean_file(path: Path, timeout_sec: int) -> Dict[str, Any]:
    """Document the responsibility of ``compile_lean_file``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``compile_lean_file`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            ["lake", "env", "lean", str(path)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        direct_report = {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "duration_ms": duration_ms,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "timeout": False,
            "path": rel(path),
            "method": "lake env lean",
        }
    except subprocess.TimeoutExpired as exc:
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        return {
            "ok": False,
            "returncode": None,
            "duration_ms": duration_ms,
            "stdout": (exc.stdout or "")[-4000:],
            "stderr": (exc.stderr or f"timeout after {timeout_sec}s")[-4000:],
            "timeout": True,
            "path": rel(path),
            "method": "lake env lean",
        }

    if direct_report["ok"] or "unknown module prefix" not in (
        direct_report["stderr"] + direct_report["stdout"]
    ):
        return direct_report

    module = rel(path)
    if module.endswith(".lean"):
        module = module[:-5].replace("/", ".")
    fallback_started = time.perf_counter()
    try:
        fallback = subprocess.run(
            ["lake", "build", module],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
        fallback_duration_ms = round((time.perf_counter() - fallback_started) * 1000, 3)
        return {
            "ok": fallback.returncode == 0,
            "returncode": fallback.returncode,
            "duration_ms": fallback_duration_ms,
            "stdout": fallback.stdout[-4000:],
            "stderr": fallback.stderr[-4000:],
            "timeout": False,
            "path": rel(path),
            "method": "lake build",
            "target": module,
            "initial_method": "lake env lean",
            "initial_stderr": direct_report["stderr"][-1000:],
        }
    except subprocess.TimeoutExpired as exc:
        fallback_duration_ms = round((time.perf_counter() - fallback_started) * 1000, 3)
        return {
            "ok": False,
            "returncode": None,
            "duration_ms": fallback_duration_ms,
            "stdout": (exc.stdout or "")[-4000:],
            "stderr": (exc.stderr or f"timeout after {timeout_sec}s")[-4000:],
            "timeout": True,
            "path": rel(path),
            "method": "lake build",
            "target": module,
            "initial_method": "lake env lean",
            "initial_stderr": direct_report["stderr"][-1000:],
        }


def compile_text(text: str, name: str, timeout_sec: int) -> Dict[str, Any]:
    """Document the responsibility of ``compile_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``compile_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    scratch_dir = REPO_ROOT / "artifacts" / "tmp" / "mathformerlib_promotion"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        suffix=".lean",
        prefix=f"{name}_",
        dir=scratch_dir,
        delete=False,
    ) as handle:
        handle.write(text)
        scratch_path = Path(handle.name)
    try:
        return compile_lean_file(scratch_path, timeout_sec)
    finally:
        try:
            scratch_path.unlink()
        except OSError:
            pass


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
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
    realness = run_realness(args)
    compile_report: Optional[Dict[str, Any]] = None
    if args.compile:
        if args.lean_file is not None:
            compile_report = compile_lean_file(args.lean_file, args.compile_timeout_sec)
        else:
            compile_report = compile_text(
                args.text or "", args.name, args.compile_timeout_sec
            )

    findings: List[Dict[str, Any]] = []
    for finding in realness.get("findings", []):
        if finding.get("severity") == "high":
            findings.append({"source": "realness", **finding})
    if compile_report is not None and not compile_report["ok"]:
        findings.append(
            {
                "source": "compile",
                "severity": "high",
                "code": "lean_compile_failed",
                "message": "Lean compilation failed for promotion candidate.",
                "stderr": compile_report.get("stderr"),
                "stdout": compile_report.get("stdout"),
            }
        )
    ok = not findings
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "candidate": None if args.lean_file is None else rel(args.lean_file),
        "name": args.name,
        "ok": ok,
        "promotion_status": "accepted" if ok else "blocked",
        "summary": {
            "finding_count": len(findings),
            "blocking_finding_count": len(findings),
            "compile_checked": compile_report is not None,
            "realness_ok": bool(realness.get("ok")),
            "compile_ok": (
                None if compile_report is None else bool(compile_report.get("ok"))
            ),
        },
        "realness_report": realness,
        "compile_report": compile_report,
        "findings": findings,
    }


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
    lines = [
        f"ok: {report['ok']}",
        f"promotion_status: {report['promotion_status']}",
        f"findings: {report['summary']['finding_count']}",
    ]
    for finding in report["findings"][:20]:
        lines.append(f"- {finding['severity']} {finding['code']}: {finding['message']}")
    return "\n".join(lines)


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
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--lean-file", type=Path)
    group.add_argument("--text")
    parser.add_argument("--name", default="promotion_candidate")
    parser.add_argument("--compile", action="store_true")
    parser.add_argument("--compile-timeout-sec", type=int, default=120)
    parser.add_argument("--expect-blocking", action="store_true")
    parser.add_argument("--reasoning-log-file", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


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
    append_event(
        args.reasoning_log_file,
        "mathformerlib_promotion_gate_start",
        {
            "lean_file": None if args.lean_file is None else str(args.lean_file),
            "name": args.name,
        },
    )
    report = build_report(args)
    append_event(
        args.reasoning_log_file,
        "mathformerlib_promotion_gate_complete",
        {
            "ok": report["ok"],
            "promotion_status": report["promotion_status"],
            **report["summary"],
        },
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    if args.expect_blocking:
        return 0 if not report["ok"] else 4
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
