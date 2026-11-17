#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
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

"""Run textbook autoformalization jobs object by object with honest gates."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
REALNESS_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "autoformalization"
    / "autoformalization-result-realness-verifier"
    / "scripts"
    / "verify_artifact_realness.py"
)
CONSISTENCY_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "lean"
    / "lean-consistency-report-orchestrator"
    / "scripts"
    / "run_lean_consistency_report.py"
)


JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "status": {"type": "string", "enum": ["draft_generated", "blocked"]},
        "lean_code": {"type": "string"},
        "notes": {"type": "string"},
        "unresolved_dependencies": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["status", "lean_code", "notes", "unresolved_dependencies"],
}


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


def load_json(path: Path) -> Dict[str, Any]:
    """Document the responsibility of ``load_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Dict[str, Any]) -> None:
    """Document the responsibility of ``write_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8"
    )


def slugify(value: str, default: str = "job") -> str:
    """Document the responsibility of ``slugify``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``slugify`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return slug[:120] or default


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Document the responsibility of ``extract_json_object``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_json_object`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass
    for start in [idx for idx, char in enumerate(stripped) if char == "{"]:
        for end in reversed([idx for idx, char in enumerate(stripped) if char == "}"]):
            if end <= start:
                continue
            try:
                parsed = json.loads(stripped[start : end + 1])
            except Exception:
                continue
            if isinstance(parsed, dict):
                return parsed
    return None


def extract_fenced_lean(text: str) -> str:
    """Document the responsibility of ``extract_fenced_lean``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_fenced_lean`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    match = re.search(
        r"```(?:lean|lean4)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE
    )
    if match:
        return match.group(1).strip()
    return ""


def provider_available(provider: str) -> Dict[str, Any]:
    """Document the responsibility of ``provider_available``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``provider_available`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if provider == "none":
        return {"available": False, "reason": "provider disabled"}
    if provider == "codex-cli":
        path = shutil.which("codex")
        return {
            "available": path is not None,
            "path": path,
            "reason": "codex CLI found" if path else "codex CLI not found on PATH",
        }
    raise ValueError(f"unknown provider: {provider}")


def object_agent_usage(job: Dict[str, Any], run_dir: Path) -> Dict[str, Any]:
    """Document the responsibility of ``object_agent_usage``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``object_agent_usage`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {
        "agent_or_skill": "textbook-autoformalization-batch-orchestrator",
        "generator_provider": "codex-cli",
        "hook_id": "draft.textbook_object_autoformalization_run",
        "hook_phase": "drafting",
        "hook_owner_skill": "textbook-autoformalization-batch-orchestrator",
        "step": "textbook_object_autoformalization_job_start",
        "usage_site": {
            "job_id": job.get("job_id"),
            "source_unit_id": job.get("source_unit_id"),
            "target_kind": job.get("target_kind"),
            "source_file": job.get("source_file"),
            "line_start": job.get("line_start"),
            "line_end": job.get("line_end"),
            "run_dir": str(run_dir),
        },
    }


def object_convergence_criteria(job: Dict[str, Any]) -> Dict[str, Any]:
    """Document the responsibility of ``object_convergence_criteria``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``object_convergence_criteria`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {
        "source": "textbook_object_runner",
        "criteria": (
            "complete only when generation produces Lean and configured realness "
            "plus unified consistency gates pass; otherwise status is blocked or draft"
        ),
        "required_gates": job.get("required_gates", []),
        "current_evidence": {},
    }


def make_generation_prompt(job: Dict[str, Any], prompt_text: str) -> str:
    """Document the responsibility of ``make_generation_prompt``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return (
        "You are executing one Mathformer textbook autoformalization job.\n"
        "Return a JSON object matching the provided schema. Do not edit files.\n\n"
        "Requirements:\n"
        "- Generate Lean4 code for exactly this object.\n"
        "- Maximize mathlib-native APIs and keep imports as narrow as you can justify.\n"
        "- Include source-aware declaration comments with Original source (NL) and Original source (LaTeX).\n"
        "- If the job contains line_translation_packet, source_anchor, or src_L#### references, preserve them with a compact `Source anchors: ...` line in each source-backed declaration comment.\n"
        "- Use the paired proof text when available.\n"
        "- Do not use `sorry`, `admit`, target `axiom`, mock markers, or scaffold completion claims.\n"
        "- If the object cannot be honestly formalized, set status to `blocked`, leave lean_code empty, and explain the blocker.\n"
        "- If code is generated, set status to `draft_generated`; downstream gates decide whether it becomes complete.\n\n"
        "Boundary note: the batch runner, not the model response, executes the local Mathformer skills, "
        "Lean checks, realness gate, and consistency reports. If a named local skill is not available "
        "inside this spawned Codex session, do not block for that reason; generate the best honest Lean "
        "draft or block only for a mathematical/formalization reason.\n\n"
        f"Job JSON:\n```json\n{json.dumps(job, indent=2, sort_keys=True, ensure_ascii=False)}\n```\n\n"
        f"Job prompt:\n{prompt_text}\n"
    )


def run_codex_generation(
    job: Dict[str, Any],
    prompt_text: str,
    run_dir: Path,
    *,
    model: Optional[str],
    timeout_sec: int,
) -> Dict[str, Any]:
    """Document the responsibility of ``run_codex_generation``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    schema_file = run_dir / "codex_output_schema.json"
    output_file = run_dir / "codex_last_message.json"
    event_file = run_dir / "codex_events.jsonl"
    prompt_file = run_dir / "codex_prompt.md"
    schema_file.write_text(
        json.dumps(JSON_SCHEMA, indent=2, sort_keys=True), encoding="utf-8"
    )
    prompt = make_generation_prompt(job, prompt_text)
    prompt_file.write_text(prompt, encoding="utf-8")

    cmd = [
        "codex",
        "-a",
        "never",
        "exec",
        "-C",
        str(REPO_ROOT),
        "-s",
        "read-only",
        "--output-schema",
        str(schema_file),
        "--output-last-message",
        str(output_file),
        "--json",
        "-",
    ]
    if model:
        cmd[3:3] = ["-m", model]
    started = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        input=prompt,
        text=True,
        capture_output=True,
        timeout=timeout_sec,
    )
    event_file.write_text(proc.stdout, encoding="utf-8")
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    last_message = (
        output_file.read_text(encoding="utf-8") if output_file.exists() else proc.stdout
    )
    parsed = extract_json_object(last_message)
    if parsed is None:
        lean_code = extract_fenced_lean(last_message)
        parsed = {
            "status": "draft_generated" if lean_code else "blocked",
            "lean_code": lean_code,
            "notes": (
                "Could not parse JSON response; used fenced Lean fallback."
                if lean_code
                else "Could not parse JSON response."
            ),
            "unresolved_dependencies": [],
        }
    return {
        "provider": "codex-cli",
        "cmd": cmd,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "duration_ms": duration_ms,
        "stdout_file": str(event_file),
        "stderr": proc.stderr[-4000:],
        "last_message_file": str(output_file),
        "parsed": parsed,
    }


def run_command(cmd: Sequence[str], *, timeout_sec: int = 180) -> Dict[str, Any]:
    """Document the responsibility of ``run_command``.

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
    try:
        proc = subprocess.run(
            list(cmd),
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
        return {
            "cmd": list(cmd),
            "returncode": proc.returncode,
            "ok": proc.returncode == 0,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "stdout": proc.stdout[-6000:],
            "stderr": proc.stderr[-6000:],
            "timeout": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": list(cmd),
            "returncode": None,
            "ok": False,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "stdout": (exc.stdout or "")[-6000:],
            "stderr": (exc.stderr or f"timeout after {timeout_sec}s")[-6000:],
            "timeout": True,
        }


def run_gates(lean_file: Path, run_dir: Path, *, lean_check: bool) -> Dict[str, Any]:
    """Document the responsibility of ``run_gates``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    realness_file = run_dir / "realness_report.json"
    consistency_file = run_dir / "consistency_report.json"
    realness = run_command(
        [
            "python3",
            str(REALNESS_SCRIPT),
            "--lean-file",
            str(lean_file),
            "--artifact-status",
            "final",
            "--output-file",
            str(realness_file),
            "--json",
        ],
        timeout_sec=120,
    )
    consistency_cmd = [
        "python3",
        str(CONSISTENCY_SCRIPT),
        "--lean-file",
        str(lean_file),
        "--output-file",
        str(consistency_file),
        "--target-mathlib-compatibility",
        "80",
        "--target-reference-free-score",
        "80",
        "--json",
    ]
    if lean_check:
        consistency_cmd.append("--run-lean-check")
    consistency = run_command(consistency_cmd, timeout_sec=240)
    return {
        "realness": {**realness, "report_file": str(realness_file)},
        "consistency": {**consistency, "report_file": str(consistency_file)},
        "ok": realness["ok"] and consistency["ok"],
    }


def process_job(
    job_entry: Dict[str, Any],
    output_dir: Path,
    *,
    provider: str,
    provider_info: Dict[str, Any],
    model: Optional[str],
    timeout_sec: int,
    lean_check: bool,
    force: bool,
) -> Dict[str, Any]:
    """Document the responsibility of ``process_job``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``process_job`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    job = load_json(Path(job_entry["job_file"]))
    job_id = job["job_id"]
    run_dir = output_dir / "runs" / job_id
    result_file = run_dir / "result.json"
    if result_file.exists() and not force:
        return load_json(result_file)

    run_dir.mkdir(parents=True, exist_ok=True)
    prompt_text = Path(job["prompt_file"]).read_text(encoding="utf-8")
    (run_dir / "job.json").write_text(
        json.dumps(job, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8"
    )
    (run_dir / "prompt.md").write_text(prompt_text, encoding="utf-8")

    result: Dict[str, Any] = {
        "schema_version": 1,
        "job_id": job_id,
        "source_unit_id": job.get("source_unit_id"),
        "target_kind": job.get("target_kind"),
        "started_at": utc_now(),
        "run_dir": str(run_dir),
        "provider": provider,
        "provider_info": provider_info,
        "status": "blocked",
        "status_reason": "",
        "agent_usage": object_agent_usage(job, run_dir),
        "convergence_criteria": object_convergence_criteria(job),
        "lean_file": None,
        "generation": None,
        "gates": None,
        "completed_at": None,
    }

    if not provider_info.get("available"):
        result["status"] = "blocked_no_generative_provider"
        result["status_reason"] = provider_info.get("reason", "provider unavailable")
        result["convergence_criteria"]["current_evidence"] = {
            "provider_available": False,
            "status": result["status"],
        }
        result["completed_at"] = utc_now()
        write_json(result_file, result)
        return result

    try:
        generation = run_codex_generation(
            job,
            prompt_text,
            run_dir,
            model=model,
            timeout_sec=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        generation = {
            "provider": provider,
            "ok": False,
            "returncode": None,
            "stderr": f"timeout after {timeout_sec}s",
            "stdout_file": None,
            "last_message_file": None,
            "parsed": {
                "status": "blocked",
                "lean_code": "",
                "notes": str(exc),
                "unresolved_dependencies": [],
            },
        }
    result["generation"] = generation
    parsed = generation.get("parsed") or {}
    lean_code = (parsed.get("lean_code") or "").strip()
    if not generation.get("ok") or parsed.get("status") == "blocked" or not lean_code:
        result["status"] = "blocked_generation"
        result["status_reason"] = (
            parsed.get("notes")
            or generation.get("stderr")
            or "generation produced no Lean code"
        )
        result["convergence_criteria"]["current_evidence"] = {
            "provider_available": True,
            "generation_ok": generation.get("ok"),
            "generated_lean": bool(lean_code),
            "status": result["status"],
        }
        result["completed_at"] = utc_now()
        write_json(result_file, result)
        return result

    lean_file = run_dir / f"{slugify(job_id)}.lean"
    lean_file.write_text(lean_code.rstrip() + "\n", encoding="utf-8")
    result["lean_file"] = str(lean_file)
    gates = run_gates(lean_file, run_dir, lean_check=lean_check)
    result["gates"] = gates
    result["status"] = "complete" if gates["ok"] else "draft_failed_gates"
    result["status_reason"] = (
        "all configured gates passed"
        if gates["ok"]
        else "one or more configured gates failed"
    )
    result["convergence_criteria"]["current_evidence"] = {
        "provider_available": True,
        "generation_ok": generation.get("ok"),
        "generated_lean": True,
        "realness_ok": gates["realness"]["ok"],
        "consistency_ok": gates["consistency"]["ok"],
        "status": result["status"],
    }
    result["completed_at"] = utc_now()
    write_json(result_file, result)
    return result


def select_jobs(
    manifest: Dict[str, Any],
    *,
    start_at: int,
    max_jobs: Optional[int],
    kind: Optional[str],
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``select_jobs``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``select_jobs`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    jobs = manifest.get("jobs", [])
    if kind:
        jobs = [job for job in jobs if job.get("target_kind") == kind]
    if start_at > 1:
        jobs = jobs[start_at - 1 :]
    if max_jobs is not None:
        jobs = jobs[:max_jobs]
    return jobs


def run_batch(
    batch_manifest: Path,
    output_dir: Path,
    *,
    provider: str,
    model: Optional[str],
    timeout_sec: int,
    start_at: int,
    max_jobs: Optional[int],
    kind: Optional[str],
    lean_check: bool,
    force: bool,
) -> Dict[str, Any]:
    """Document the responsibility of ``run_batch``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    manifest = load_json(batch_manifest)
    output_dir.mkdir(parents=True, exist_ok=True)
    provider_info = provider_available(provider)
    selected_jobs = select_jobs(
        manifest, start_at=start_at, max_jobs=max_jobs, kind=kind
    )
    results: List[Dict[str, Any]] = []
    for job_entry in selected_jobs:
        result = process_job(
            job_entry,
            output_dir,
            provider=provider,
            provider_info=provider_info,
            model=model,
            timeout_sec=timeout_sec,
            lean_check=lean_check,
            force=force,
        )
        results.append(
            {
                "job_id": result["job_id"],
                "target_kind": result.get("target_kind"),
                "status": result["status"],
                "status_reason": result.get("status_reason"),
                "lean_file": result.get("lean_file"),
                "result_file": str(Path(result["run_dir"]) / "result.json"),
            }
        )
        run_manifest = build_run_manifest(
            batch_manifest=batch_manifest,
            output_dir=output_dir,
            provider=provider,
            provider_info=provider_info,
            selected_count=len(selected_jobs),
            results=collect_recorded_result_summaries(output_dir) or results,
        )
        write_json(output_dir / "run_manifest.json", run_manifest)
    return build_run_manifest(
        batch_manifest=batch_manifest,
        output_dir=output_dir,
        provider=provider,
        provider_info=provider_info,
        selected_count=len(selected_jobs),
        results=collect_recorded_result_summaries(output_dir) or results,
    )


def collect_recorded_result_summaries(output_dir: Path) -> List[Dict[str, Any]]:
    """Document the responsibility of ``collect_recorded_result_summaries``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``collect_recorded_result_summaries`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    summaries: List[Dict[str, Any]] = []
    runs_dir = output_dir / "runs"
    if not runs_dir.exists():
        return summaries
    for result_file in sorted(runs_dir.glob("*/result.json")):
        try:
            result = load_json(result_file)
        except Exception:
            continue
        summaries.append(
            {
                "job_id": result.get("job_id"),
                "target_kind": result.get("target_kind"),
                "status": result.get("status"),
                "status_reason": result.get("status_reason"),
                "lean_file": result.get("lean_file"),
                "result_file": str(result_file),
            }
        )
    return summaries


def build_run_manifest(
    *,
    batch_manifest: Path,
    output_dir: Path,
    provider: str,
    provider_info: Dict[str, Any],
    selected_count: int,
    results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Document the responsibility of ``build_run_manifest``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    status_counts = Counter(result["status"] for result in results)
    kind_counts = Counter(result.get("target_kind") for result in results)
    return {
        "schema_version": 1,
        "updated_at": utc_now(),
        "batch_manifest": str(batch_manifest),
        "output_dir": str(output_dir),
        "provider": provider,
        "provider_info": provider_info,
        "selected_job_count": selected_count,
        "processed_job_count": len(results),
        "summary": {
            "status_counts": dict(sorted(status_counts.items())),
            "target_kind_counts": dict(sorted(kind_counts.items())),
        },
        "results": results,
    }


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
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        job_file = tmp_path / "job.json"
        prompt_file = tmp_path / "prompt.md"
        job = {
            "job_id": "textbook-job-test",
            "source_unit_id": "u1",
            "target_kind": "theorem",
            "job_file": str(job_file),
            "prompt_file": str(prompt_file),
            "source_statement_latex": "\\begin{theorem}True.\\end{theorem}",
            "paired_proof_latex": "\\begin{proof}Trivial.\\end{proof}",
        }
        job_file.write_text(json.dumps(job), encoding="utf-8")
        prompt_file.write_text("Toy theorem job", encoding="utf-8")
        manifest_file = tmp_path / "batch_manifest.json"
        manifest_file.write_text(
            json.dumps(
                {
                    "jobs": [
                        {
                            "job_id": job["job_id"],
                            "target_kind": "theorem",
                            "job_file": str(job_file),
                            "prompt_file": str(prompt_file),
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        run_manifest = run_batch(
            manifest_file,
            tmp_path / "out",
            provider="none",
            model=None,
            timeout_sec=5,
            start_at=1,
            max_jobs=1,
            kind=None,
            lean_check=False,
            force=True,
        )
        assert run_manifest["processed_job_count"] == 1, run_manifest
        assert (
            run_manifest["summary"]["status_counts"]["blocked_no_generative_provider"]
            == 1
        ), run_manifest
        result = load_json(Path(run_manifest["results"][0]["result_file"]))
        assert (
            result["agent_usage"]["usage_site"]["job_id"] == "textbook-job-test"
        ), result
        assert "criteria" in result["convergence_criteria"], result
        assert (
            result["convergence_criteria"]["current_evidence"]["status"]
            == "blocked_no_generative_provider"
        ), result
        return {"ok": True, "summary": run_manifest["summary"]}


def parse_args() -> argparse.Namespace:
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
    parser.add_argument(
        "--batch-manifest",
        type=Path,
        help="Batch manifest emitted by build_textbook_autoformalization_batch.py",
    )
    parser.add_argument("--output-dir", type=Path, help="Run output directory")
    parser.add_argument(
        "--provider", choices=("codex-cli", "none"), default="codex-cli"
    )
    parser.add_argument("--model", help="Optional codex model override")
    parser.add_argument("--timeout-sec", type=int, default=900)
    parser.add_argument(
        "--start-at", type=int, default=1, help="1-based selected job offset"
    )
    parser.add_argument(
        "--max-jobs", type=int, help="Maximum number of jobs to process"
    )
    parser.add_argument("--kind", help="Only process jobs of this target kind")
    parser.add_argument(
        "--skip-lean-check",
        action="store_true",
        help="Skip `lake env lean` inside consistency report",
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-run jobs even if result.json exists"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
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
    args = parse_args()
    if args.self_test:
        print(json.dumps(run_self_test(), indent=2, sort_keys=True))
        return 0
    if args.batch_manifest is None:
        raise SystemExit("--batch-manifest is required unless --self-test is used")
    batch_manifest = args.batch_manifest.resolve()
    output_dir = (args.output_dir or batch_manifest.parent / "object_runs").resolve()
    run_manifest = run_batch(
        batch_manifest,
        output_dir,
        provider=args.provider,
        model=args.model,
        timeout_sec=args.timeout_sec,
        start_at=args.start_at,
        max_jobs=args.max_jobs,
        kind=args.kind,
        lean_check=not args.skip_lean_check,
        force=args.force,
    )
    write_json(output_dir / "run_manifest.json", run_manifest)
    print(
        json.dumps(
            {
                "ok": True,
                "run_manifest": str(output_dir / "run_manifest.json"),
                **run_manifest["summary"],
            },
            indent=2 if args.json else None,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
