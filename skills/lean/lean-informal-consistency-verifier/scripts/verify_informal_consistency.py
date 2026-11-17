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

"""Verify reverse-informalization consistency for final Lean artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Set

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

try:
    from reasoning_log import append_reasoning_log_entry
except Exception:  # pragma: no cover
    append_reasoning_log_entry = None  # type: ignore[assignment]


SKILL_NAME = "lean-informal-consistency-verifier"
HOOK_ID = "postformalization.informal_consistency"

EXTRACTOR_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "lean"
    / "lean-informalization-extractor"
    / "scripts"
    / "extract_lean_informalization.py"
)
REALNESS_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "autoformalization"
    / "autoformalization-result-realness-verifier"
    / "scripts"
    / "verify_artifact_realness.py"
)

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_'-]*")
STOPWORDS = {
    "the",
    "and",
    "or",
    "of",
    "to",
    "in",
    "a",
    "an",
    "is",
    "are",
    "be",
    "by",
    "for",
    "with",
    "that",
    "this",
    "as",
    "it",
    "then",
    "if",
    "iff",
    "lean",
    "source",
    "generated",
    "note",
}


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
    if reasoning_log is None or append_reasoning_log_entry is None:
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


def run_lean_check(path: Path) -> Dict[str, Any]:
    """Document the responsibility of ``run_lean_check``.

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
        ["lake", "env", "lean", rel(path)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=180,
    )
    return {
        "file": rel(path),
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def extractor_for(paths: Sequence[Path]) -> Dict[str, Any]:
    """Document the responsibility of ``extractor_for``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extractor_for`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    cmd = [sys.executable, str(EXTRACTOR_SCRIPT), "--json"]
    for path in paths:
        cmd.extend(["--lean-file", rel(path)])
    return run_json_command(cmd, timeout_sec=120)


def extractor_for_text(text: str, name: str) -> Dict[str, Any]:
    """Document the responsibility of ``extractor_for_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extractor_for_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return run_json_command(
        [
            sys.executable,
            str(EXTRACTOR_SCRIPT),
            "--text",
            text,
            "--name",
            name,
            "--json",
        ],
        timeout_sec=60,
    )


def realness_for(paths: Sequence[Path]) -> Dict[str, Any]:
    """Document the responsibility of ``realness_for``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``realness_for`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    cmd = [sys.executable, str(REALNESS_SCRIPT), "--json"]
    for path in paths:
        cmd.extend(["--lean-file", rel(path)])
    return run_json_command(cmd, timeout_sec=120)


def realness_for_text(text: str, name: str) -> Dict[str, Any]:
    """Document the responsibility of ``realness_for_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``realness_for_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return run_json_command(
        [
            sys.executable,
            str(REALNESS_SCRIPT),
            "--text",
            text,
            "--name",
            name,
            "--json",
        ],
        timeout_sec=60,
    )


def words(text: str) -> Set[str]:
    """Document the responsibility of ``words``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``words`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {
        word.lower()
        for word in WORD_RE.findall(text)
        if word.lower() not in STOPWORDS and len(word) > 2
    }


def token_overlap(source: str, signature: str) -> float:
    """Document the responsibility of ``token_overlap``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``token_overlap`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    source_words = words(source)
    signature_words = words(signature)
    if not source_words or not signature_words:
        return 1.0
    return len(source_words & signature_words) / max(
        1, min(len(source_words), len(signature_words))
    )


def has_equivalence_claim(text: str) -> bool:
    """Document the responsibility of ``has_equivalence_claim``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_equivalence_claim`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lowered = text.lower()
    return (
        "\\iff" in text
        or "↔" in text
        or " if and only if " in lowered
        or " equivalent " in lowered
        or " iff " in lowered
    )


def has_existential_claim(text: str) -> bool:
    """Document the responsibility of ``has_existential_claim``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_existential_claim`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lowered = text.lower()
    return (
        "\\exists" in text
        or "∃" in text
        or " there exists " in lowered
        or " exists " in lowered
    )


def explicit_boundary_text(declaration: Dict[str, Any]) -> str:
    """Document the responsibility of ``explicit_boundary_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``explicit_boundary_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    fields = declaration.get("source_alignment", {})
    return " ".join(
        str(fields.get(key, ""))
        for key in (
            "generated_notes",
            "generated_equivalents",
            "mathlib_grounding",
            "other",
        )
    ).lower()


def declaration_consistency_findings(
    file_name: str, declaration: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``declaration_consistency_findings``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings: List[Dict[str, Any]] = []
    kind = declaration.get("kind", "")
    if kind not in {"theorem", "lemma", "axiom"}:
        return findings
    line = declaration.get("line")
    signature = declaration.get("signature", "")
    source_fields = declaration.get("source_alignment", {})
    source_text = " ".join(
        str(source_fields.get(key, ""))
        for key in (
            "original_nl",
            "original_latex",
            "generated_notes",
            "generated_equivalents",
        )
    )
    if not declaration.get("informal_statement"):
        findings.append(
            {
                "severity": "high",
                "code": "missing_informal_statement",
                "message": "The reverse informalization has no theorem statement.",
                "file": file_name,
                "declaration": declaration.get("name"),
                "line": line,
            }
        )
    if not declaration.get("proof_summary"):
        findings.append(
            {
                "severity": "high",
                "code": "missing_proof_summary",
                "message": "The reverse informalization has no proof summary.",
                "file": file_name,
                "declaration": declaration.get("name"),
                "line": line,
            }
        )
    if (
        has_equivalence_claim(source_text)
        and "↔" not in signature
        and "<->" not in signature
    ):
        findings.append(
            {
                "severity": "high",
                "code": "equivalence_shape_mismatch",
                "message": "Source/comment claims an equivalence, but the Lean signature has no equivalence connective.",
                "file": file_name,
                "declaration": declaration.get("name"),
                "line": line,
            }
        )
    if (
        has_existential_claim(source_text)
        and "∃" not in signature
        and "Exists" not in signature
        and "Subtype" not in signature
    ):
        findings.append(
            {
                "severity": "medium",
                "code": "existential_shape_review",
                "message": "Source/comment appears existential; review whether the Lean signature exposes the witness/result shape.",
                "file": file_name,
                "declaration": declaration.get("name"),
                "line": line,
            }
        )
    overlap = token_overlap(source_text, signature)
    if source_text and overlap < 0.08:
        findings.append(
            {
                "severity": "medium",
                "code": "low_source_signature_overlap",
                "message": "Source/comment vocabulary has very low overlap with the Lean signature; review semantic drift.",
                "file": file_name,
                "declaration": declaration.get("name"),
                "line": line,
                "overlap": round(overlap, 4),
            }
        )
    proof_features = declaration.get("proof_features", {})
    if proof_features.get("delegated_to_hypothesis"):
        boundary = explicit_boundary_text(declaration)
        honest_boundary = any(
            token in boundary
            for token in (
                "explicit assumption",
                "explicit hypothesis",
                "criterion",
                "model",
                "external",
                "interface",
                "component",
                "represented",
            )
        )
        findings.append(
            {
                "severity": "low" if honest_boundary else "medium",
                "code": "proof_delegates_to_hypothesis",
                "message": "Lean proof closes by exact use of a hypothesis; ensure this is an intended theorem-boundary assumption.",
                "file": file_name,
                "declaration": declaration.get("name"),
                "line": line,
                "honest_boundary_documented": honest_boundary,
            }
        )
    return findings


def collect_consistency_findings(
    extractor_report: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``collect_consistency_findings``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings: List[Dict[str, Any]] = []
    for item in extractor_report.get("findings", []):
        if item.get("severity") == "high":
            findings.append({"source": "informalization_extractor", **item})
    for file_packet in extractor_report.get("files", []):
        file_name = file_packet.get("file", "")
        for declaration in file_packet.get("declarations", []):
            findings.extend(declaration_consistency_findings(file_name, declaration))
    return findings


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
    good = "\n".join(
        [
            "import Mathlib.Init",
            "",
            "/--",
            "Original source (NL): Truth is derivable.",
            "Original source (LaTeX): `\\mathrm{True}`.",
            "-/",
            "theorem generated_true : True := by",
            "  trivial",
        ]
    )
    bad = "\n".join(
        [
            "/--",
            "Original source (NL): The statement holds if and only if the condition holds.",
            "Original source (LaTeX): `P \\iff Q`.",
            "-/",
            "theorem generated_bad : True := by",
            "  sorry",
        ]
    )
    good_report = verify_text(good, name="good_fixture", run_lean_check=False)
    bad_report = verify_text(bad, name="bad_fixture", run_lean_check=False)
    report = {
        "generated_at_utc": utc_now(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": good_report["ok"] and not bad_report["ok"],
        "self_test": {
            "good": good_report,
            "bad": bad_report,
        },
        "summary": {
            "good_ok": good_report["ok"],
            "bad_blocked": not bad_report["ok"],
        },
    }
    return report


def build_report(
    *,
    extractor_report: Dict[str, Any],
    realness_report: Dict[str, Any],
    consistency_findings: List[Dict[str, Any]],
    lean_checks: List[Dict[str, Any]],
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
    findings = list(consistency_findings)
    for item in realness_report.get("findings", []):
        if item.get("severity") == "high":
            findings.append({"source": "realness_gate", **item})
    for check in lean_checks:
        if not check.get("ok"):
            findings.append(
                {
                    "source": "lean_check",
                    "severity": "high",
                    "code": "lean_check_failed",
                    "message": "Lean did not accept the file during informal-consistency verification.",
                    "file": check.get("file"),
                    "stderr_tail": check.get("stderr_tail"),
                }
            )
    high = [item for item in findings if item.get("severity") == "high"]
    medium = [item for item in findings if item.get("severity") == "medium"]
    low = [item for item in findings if item.get("severity") == "low"]
    score = max(0, 100 - 30 * len(high) - min(35, 3 * len(medium)) - min(10, len(low)))
    return {
        "generated_at_utc": utc_now(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": not high,
        "summary": {
            "file_count": extractor_report.get("summary", {}).get("file_count", 0),
            "declaration_count": extractor_report.get("summary", {}).get(
                "declaration_count", 0
            ),
            "theorem_like_count": extractor_report.get("summary", {}).get(
                "theorem_like_count", 0
            ),
            "consistency_score": score,
            "finding_count": len(findings),
            "blocking_finding_count": len(high),
            "medium_finding_count": len(medium),
            "low_finding_count": len(low),
            "realness_ok": bool(realness_report.get("ok")),
            "lean_check_count": len(lean_checks),
            "lean_checks_ok": all(check.get("ok") for check in lean_checks),
        },
        "extractor_report": extractor_report,
        "realness_report": realness_report,
        "lean_checks": lean_checks,
        "findings": findings,
    }


def verify_paths(paths: Sequence[Path], *, run_lean_check_flag: bool) -> Dict[str, Any]:
    """Document the responsibility of ``verify_paths``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    extractor_report = extractor_for(paths)
    realness_report = realness_for(paths)
    consistency_findings = collect_consistency_findings(extractor_report)
    lean_checks = (
        [run_lean_check(path) for path in paths] if run_lean_check_flag else []
    )
    return build_report(
        extractor_report=extractor_report,
        realness_report=realness_report,
        consistency_findings=consistency_findings,
        lean_checks=lean_checks,
    )


def verify_text(text: str, *, name: str, run_lean_check: bool) -> Dict[str, Any]:
    """Document the responsibility of ``verify_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    extractor_report = extractor_for_text(text, name)
    realness_report = realness_for_text(text, name)
    consistency_findings = collect_consistency_findings(extractor_report)
    return build_report(
        extractor_report=extractor_report,
        realness_report=realness_report,
        consistency_findings=consistency_findings,
        lean_checks=[] if not run_lean_check else [],
    )


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
    summary = report.get("summary", {})
    lines = [
        f"ok: {report['ok']}",
        f"files: {summary.get('file_count', 0)}",
        f"declarations: {summary.get('declaration_count', 0)}",
        f"theorem_like: {summary.get('theorem_like_count', 0)}",
        f"consistency_score: {summary.get('consistency_score', 'n/a')}",
        f"findings: {summary.get('finding_count', 0)}",
        f"blocking: {summary.get('blocking_finding_count', 0)}",
    ]
    for finding in report.get("findings", [])[:30]:
        lines.append(
            f"- {finding.get('severity')} {finding.get('file', finding.get('path', ''))}:"
            f"{finding.get('line', '')} {finding.get('code')} {finding.get('message')}"
        )
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
    parser.add_argument("--lean-file", action="append", type=Path, default=[])
    parser.add_argument("--text", default="")
    parser.add_argument("--name", default="inline_text")
    parser.add_argument("--run-lean-check", action="store_true")
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--reasoning-log-file", type=Path)
    parser.add_argument("--no-reasoning-log", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--expect-ok", action="store_true")
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
    reasoning_log = None
    if args.reasoning_log_file and not args.no_reasoning_log:
        reasoning_log = (REPO_ROOT / args.reasoning_log_file).resolve()
    append_event(
        reasoning_log,
        "lean_informal_consistency_start",
        {"file_count": len(args.lean_file)},
    )
    if args.self_test:
        report = run_self_test()
    elif args.text:
        report = verify_text(
            args.text, name=args.name, run_lean_check=args.run_lean_check
        )
    else:
        paths = [
            (REPO_ROOT / path).resolve() if not path.is_absolute() else path
            for path in args.lean_file
        ]
        report = verify_paths(paths, run_lean_check_flag=args.run_lean_check)
    append_event(
        reasoning_log,
        "lean_informal_consistency_complete",
        {"ok": report["ok"], **report.get("summary", {})},
    )
    if args.output_file:
        output = (REPO_ROOT / args.output_file).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    if args.expect_ok and not report["ok"]:
        return 3
    return 0 if report["ok"] or not args.expect_ok else 3


if __name__ == "__main__":
    sys.exit(main())
