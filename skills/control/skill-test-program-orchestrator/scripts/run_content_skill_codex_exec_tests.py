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

"""Run generative/content skill probes through codex exec."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROBES = SKILL_DIR / "references" / "content_probes.json"
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

from reasoning_log import (
    append_reasoning_log_entry,
)

SKILL_NAME = "skill-test-program-orchestrator"
HOOK_ID = "test.skill_program"


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


def load_probe_file(path: Path) -> Dict[str, Any]:
    """Document the responsibility of ``load_probe_file``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"Probe file must be a JSON object: {path}")
    return parsed


def normalize_probe_oracle(
    probe: Dict[str, Any],
    default_oracle: Dict[str, Any],
) -> Dict[str, Any]:
    """Document the responsibility of ``normalize_probe_oracle``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_probe_oracle`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    oracle = dict(default_oracle)
    oracle.update(probe.get("oracle", {}))
    oracle["required_substrings"] = list(oracle.get("required_substrings", []))
    oracle["required_any_substrings"] = [
        list(group) for group in oracle.get("required_any_substrings", [])
    ]
    oracle["forbidden_substrings"] = list(oracle.get("forbidden_substrings", []))
    return oracle


def evaluate_oracle(text: str, oracle: Dict[str, Any]) -> Dict[str, Any]:
    """Document the responsibility of ``evaluate_oracle``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``evaluate_oracle`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lower_text = text.lower()
    missing_required = [
        item
        for item in oracle.get("required_substrings", [])
        if str(item).lower() not in lower_text
    ]
    missing_required_any = [
        group
        for group in oracle.get("required_any_substrings", [])
        if not any(str(item).lower() in lower_text for item in group)
    ]
    present_forbidden = [
        item
        for item in oracle.get("forbidden_substrings", [])
        if str(item).lower() in lower_text
    ]
    nonempty_lines = [line for line in text.splitlines() if line.strip()]
    min_lines = int(oracle.get("min_nonempty_lines", 1))
    return {
        "ok": (
            not missing_required
            and not missing_required_any
            and not present_forbidden
            and len(nonempty_lines) >= min_lines
        ),
        "missing_required": missing_required,
        "missing_required_any": missing_required_any,
        "present_forbidden": present_forbidden,
        "nonempty_line_count": len(nonempty_lines),
    }


def build_codex_command(
    *,
    codex_bin: str,
    prompt_file: Path,
    final_message_file: Path,
    model: Optional[str],
    sandbox: str,
    profile: Optional[str],
    timeout_sec: int,
) -> List[str]:
    """Document the responsibility of ``build_codex_command``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    cmd = [
        codex_bin,
        "exec",
        "--cd",
        str(REPO_ROOT),
        "--sandbox",
        sandbox,
        "--output-last-message",
        str(final_message_file),
    ]
    if model:
        cmd.extend(["--model", model])
    if profile:
        cmd.extend(["--profile", profile])
    # The timeout is enforced by subprocess; include it in metadata via prompt only.
    cmd.extend(["-"])
    return cmd


def execute_probe(
    probe: Dict[str, Any],
    *,
    oracle: Dict[str, Any],
    codex_bin: str,
    output_dir: Path,
    execute: bool,
    reuse_existing: bool,
    model: Optional[str],
    sandbox: str,
    profile: Optional[str],
    timeout_sec: int,
) -> Dict[str, Any]:
    """Document the responsibility of ``execute_probe``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``execute_probe`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    probe_id = probe["id"]
    probe_dir = output_dir / probe_id
    probe_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = probe_dir / "prompt.md"
    final_message_file = probe_dir / "final_message.md"
    stdout_file = probe_dir / "stdout.txt"
    stderr_file = probe_dir / "stderr.txt"
    result_file = probe_dir / "result.json"
    prompt = str(probe["prompt"]).strip() + (
        "\n\nReturn only the requested compact JSON-like object. Do not edit files.\n"
    )
    prompt_file.write_text(prompt, encoding="utf-8")
    cmd = build_codex_command(
        codex_bin=codex_bin,
        prompt_file=prompt_file,
        final_message_file=final_message_file,
        model=model,
        sandbox=sandbox,
        profile=profile,
        timeout_sec=timeout_sec,
    )
    planned = {
        "id": probe_id,
        "skill": probe.get("skill"),
        "family": probe.get("family"),
        "execute": execute,
        "cmd": cmd,
        "prompt_file": rel(prompt_file),
        "final_message_file": rel(final_message_file),
        "stdout_file": rel(stdout_file),
        "stderr_file": rel(stderr_file),
        "result_file": rel(result_file),
        "oracle": oracle,
    }
    if reuse_existing:
        old_result: Dict[str, Any] = {}
        if result_file.exists():
            try:
                old_result = json.loads(result_file.read_text(encoding="utf-8"))
            except Exception:
                old_result = {}
        final_text = (
            final_message_file.read_text(encoding="utf-8")
            if final_message_file.exists()
            else ""
        )
        oracle_result = evaluate_oracle(final_text, oracle)
        returncode = old_result.get("returncode")
        process_ok = returncode in {0, None}
        result = {
            **planned,
            "ok": process_ok and oracle_result["ok"],
            "status": "reused",
            "returncode": returncode,
            "duration_ms": 0,
            "oracle_result": oracle_result,
            "final_message_preview": final_text[:1000],
        }
        result_file.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return result
    if not execute:
        result = {
            **planned,
            "ok": True,
            "status": "planned",
            "returncode": None,
            "duration_ms": 0,
            "oracle_result": None,
        }
        result_file.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return result

    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        stdout_file.write_text(proc.stdout, encoding="utf-8")
        stderr_file.write_text(proc.stderr, encoding="utf-8")
        final_text = (
            final_message_file.read_text(encoding="utf-8")
            if final_message_file.exists()
            else proc.stdout
        )
        oracle_result = evaluate_oracle(final_text, oracle)
        result = {
            **planned,
            "ok": proc.returncode == 0 and oracle_result["ok"],
            "status": "executed",
            "returncode": proc.returncode,
            "duration_ms": duration_ms,
            "oracle_result": oracle_result,
            "final_message_preview": final_text[:1000],
        }
    except subprocess.TimeoutExpired as exc:
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        stdout_file.write_text(exc.stdout or "", encoding="utf-8")
        stderr_file.write_text(
            exc.stderr or f"timeout after {timeout_sec}s", encoding="utf-8"
        )
        result = {
            **planned,
            "ok": False,
            "status": "timeout",
            "returncode": None,
            "duration_ms": duration_ms,
            "oracle_result": {
                "ok": False,
                "missing_required": oracle.get("required_substrings", []),
                "missing_required_any": oracle.get("required_any_substrings", []),
                "present_forbidden": [],
                "nonempty_line_count": 0,
            },
            "final_message_preview": "",
        }
    result_file.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def run_probes(
    *,
    probes_file: Path,
    output_dir: Path,
    execute: bool,
    reuse_existing: bool,
    limit: Optional[int],
    skill_filter: Optional[str],
    codex_bin: str,
    model: Optional[str],
    sandbox: str,
    profile: Optional[str],
    timeout_sec: int,
    reasoning_log: Optional[Path],
) -> Dict[str, Any]:
    """Document the responsibility of ``run_probes``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    probe_data = load_probe_file(probes_file)
    default_oracle = probe_data.get("default_oracle", {})
    probes = list(probe_data.get("probes", []))
    if skill_filter:
        probes = [probe for probe in probes if probe.get("skill") == skill_filter]
    if limit is not None:
        probes = probes[:limit]

    append_event(
        reasoning_log,
        "skill_test_content_codex_exec_start",
        {
            "execute": execute,
            "reuse_existing": reuse_existing,
            "probe_count": len(probes),
            "probes_file": rel(probes_file),
            "codex_bin": codex_bin,
            "sandbox": sandbox,
        },
    )
    results: List[Dict[str, Any]] = []
    for probe in probes:
        oracle = normalize_probe_oracle(probe, default_oracle)
        result = execute_probe(
            probe,
            oracle=oracle,
            codex_bin=codex_bin,
            output_dir=output_dir,
            execute=execute,
            reuse_existing=reuse_existing,
            model=model,
            sandbox=sandbox,
            profile=profile,
            timeout_sec=timeout_sec,
        )
        results.append(result)
        append_event(
            reasoning_log,
            "skill_test_content_codex_exec_result",
            {
                "probe_id": result["id"],
                "skill": result.get("skill"),
                "status": result["status"],
                "ok": result["ok"],
                "duration_ms": result["duration_ms"],
            },
        )

    failures = [item for item in results if not item["ok"]]
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "ok": not failures,
        "execute": execute,
        "codex_bin": codex_bin,
        "summary": {
            "probe_count": len(results),
            "passed_count": sum(1 for item in results if item["ok"]),
            "failure_count": len(failures),
            "executed_count": sum(
                1 for item in results if item["status"] == "executed"
            ),
            "reused_count": sum(1 for item in results if item["status"] == "reused"),
            "planned_count": sum(1 for item in results if item["status"] == "planned"),
        },
        "results": results,
    }
    append_event(
        reasoning_log,
        "skill_test_content_codex_exec_complete",
        {
            "ok": report["ok"],
            "probe_count": len(results),
            "failure_count": len(failures),
        },
    )
    return report


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
        f"execute: {report['execute']}",
        f"probes: {summary['probe_count']}",
        f"passed: {summary['passed_count']}",
        f"failures: {summary['failure_count']}",
    ]
    for item in report["results"]:
        status = "PASS" if item["ok"] else "FAIL"
        lines.append(f"- {status} {item['id']} [{item.get('skill')}] {item['status']}")
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
    parser.add_argument("--probes-file", type=Path, default=DEFAULT_PROBES)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/skill_test_program/content"),
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=Path("artifacts/skill_test_program/content_report.json"),
    )
    parser.add_argument(
        "--reasoning-log-file",
        type=Path,
        default=Path("artifacts/skill_test_program/reasoning.jsonl"),
    )
    parser.add_argument("--no-reasoning-log", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--reuse-existing", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--skill")
    parser.add_argument("--codex-bin", default=shutil.which("codex") or "codex")
    parser.add_argument("--model")
    parser.add_argument("--profile")
    parser.add_argument("--sandbox", default="read-only")
    parser.add_argument("--timeout-sec", type=int, default=180)
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
    probes_file = (REPO_ROOT / args.probes_file).resolve()
    output_dir = (REPO_ROOT / args.output_dir).resolve()
    report_file = (REPO_ROOT / args.report_file).resolve()
    reasoning_log = (
        None
        if args.no_reasoning_log
        else (REPO_ROOT / args.reasoning_log_file).resolve()
    )
    report = run_probes(
        probes_file=probes_file,
        output_dir=output_dir,
        execute=args.execute,
        reuse_existing=args.reuse_existing,
        limit=args.limit,
        skill_filter=args.skill,
        codex_bin=args.codex_bin,
        model=args.model,
        sandbox=args.sandbox,
        profile=args.profile,
        timeout_sec=args.timeout_sec,
        reasoning_log=reasoning_log,
    )
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
