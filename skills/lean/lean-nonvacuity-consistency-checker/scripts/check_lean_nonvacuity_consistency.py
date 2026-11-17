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

"""Check Lean theorem-like declarations for vacuity and thin-proof patterns."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

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


SKILL_NAME = "lean-nonvacuity-consistency-checker"
HOOK_ID = "consistency.nonvacuity"
EXTRACTOR_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "lean"
    / "lean-informalization-extractor"
    / "scripts"
    / "extract_lean_informalization.py"
)

THEOREM_LIKE = {"theorem", "lemma", "axiom"}
BINDER_RE = re.compile(r"[\(\{]\s*([A-Za-z_][A-Za-z0-9_']*)\s*:\s*([^)\}]+)[\)\}]")


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


def extractor_for_paths(paths: Sequence[Path]) -> Dict[str, Any]:
    """Document the responsibility of ``extractor_for_paths``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extractor_for_paths`` while preserving the surrounding module contract.

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


def normalize_prop(text: str) -> str:
    """Document the responsibility of ``normalize_prop``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_prop`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    cleaned = re.sub(r"--.*", "", text)
    cleaned = re.sub(r"\s+", "", cleaned)
    cleaned = cleaned.removesuffix(":=").strip()
    return cleaned


def conclusion_from_signature(signature: str) -> str:
    """Document the responsibility of ``conclusion_from_signature``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``conclusion_from_signature`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    head = signature.split(":=", 1)[0].strip()
    depth = 0
    last_colon = -1
    for index, char in enumerate(head):
        if char in "({[":
            depth += 1
        elif char in ")}]" and depth > 0:
            depth -= 1
        elif char == ":" and depth == 0:
            last_colon = index
    if last_colon >= 0:
        return head[last_colon + 1 :].strip()
    match = re.search(r"\)\s*:\s*(.+)$", head)
    if match:
        return match.group(1).strip()
    return ""


def binders_from_signature(signature: str) -> List[Tuple[str, str]]:
    """Document the responsibility of ``binders_from_signature``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``binders_from_signature`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return [(name, value.strip()) for name, value in BINDER_RE.findall(signature)]


def boundary_text(declaration: Dict[str, Any]) -> str:
    """Document the responsibility of ``boundary_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``boundary_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    fields = declaration.get("source_alignment", {}) or {}
    pieces = [
        fields.get("generated_notes", ""),
        fields.get("generated_equivalents", ""),
        fields.get("mathlib_grounding", ""),
        fields.get("other", ""),
        declaration.get("informal_statement", ""),
        declaration.get("proof_summary", ""),
    ]
    return " ".join(str(piece) for piece in pieces if piece).lower()


def has_boundary_marker(declaration: Dict[str, Any]) -> bool:
    """Document the responsibility of ``has_boundary_marker``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_boundary_marker`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = boundary_text(declaration)
    markers = (
        "accessor",
        "assumption",
        "axiomatized",
        "certificate",
        "external",
        "field",
        "interface",
        "record",
        "repackaging",
        "represented",
        "smoke",
        "wrapper",
        "witness",
    )
    return any(marker in text for marker in markers)


def add_finding(
    findings: List[Dict[str, Any]],
    *,
    severity: str,
    code: str,
    message: str,
    file_name: str,
    declaration: Dict[str, Any],
    evidence: Dict[str, Any],
) -> None:
    """Document the responsibility of ``add_finding``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings.append(
        {
            "severity": severity,
            "code": code,
            "message": message,
            "file": file_name,
            "declaration": declaration.get("name"),
            "line": declaration.get("line"),
            "evidence": evidence,
        }
    )


def declaration_findings(
    file_name: str, declaration: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``declaration_findings``.

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
    kind = str(declaration.get("kind", ""))
    if kind not in THEOREM_LIKE:
        return findings
    _name = str(declaration.get("name", ""))
    signature = str(declaration.get("signature", ""))
    conclusion = conclusion_from_signature(signature)
    normalized_conclusion = normalize_prop(conclusion)
    binders = binders_from_signature(signature)
    features = declaration.get("proof_features", {}) or {}
    dependencies = [str(dep) for dep in features.get("probable_dependencies", []) or []]
    tactics = set(str(tactic) for tactic in features.get("tactics", []) or [])
    boundary = has_boundary_marker(declaration)

    if kind == "axiom":
        add_finding(
            findings,
            severity="high",
            code="axiom_boundary",
            message="The declaration is an axiom; it supplies no proof evidence.",
            file_name=file_name,
            declaration=declaration,
            evidence={"signature": signature},
        )

    false_binders = [
        (binder, value) for binder, value in binders if normalize_prop(value) == "False"
    ]
    if false_binders:
        add_finding(
            findings,
            severity="high",
            code="false_hypothesis_vacuity",
            message="The theorem has a `False` hypothesis, so the result is vacuous.",
            file_name=file_name,
            declaration=declaration,
            evidence={"false_binders": false_binders, "signature": signature},
        )

    for binder, value in binders:
        if (
            normalized_conclusion
            and normalize_prop(value) == normalized_conclusion
            and not boundary
        ):
            add_finding(
                findings,
                severity="high",
                code="target_repeated_as_hypothesis",
                message="A visible hypothesis has the same proposition as the theorem conclusion.",
                file_name=file_name,
                declaration=declaration,
                evidence={
                    "binder": binder,
                    "binder_type": value,
                    "conclusion": conclusion,
                },
            )

    for dep in dependencies:
        binder_map = {binder: value for binder, value in binders}
        if (
            dep in binder_map
            and normalized_conclusion
            and normalize_prop(binder_map[dep]) == normalized_conclusion
            and not boundary
        ):
            add_finding(
                findings,
                severity="high",
                code="proof_exact_target_hypothesis",
                message="The proof exactly delegates to a hypothesis whose type is the target conclusion.",
                file_name=file_name,
                declaration=declaration,
                evidence={"dependency": dep, "conclusion": conclusion},
            )

    if normalized_conclusion == "True" and not boundary:
        add_finding(
            findings,
            severity="medium",
            code="trivial_true_conclusion",
            message="The theorem concludes `True`; verify this is not being used as a placeholder result.",
            file_name=file_name,
            declaration=declaration,
            evidence={"signature": signature},
        )

    if (
        dependencies
        and len(dependencies) == 1
        and dependencies[0] in {binder for binder, _ in binders}
        and not boundary
    ):
        add_finding(
            findings,
            severity="medium",
            code="thin_visible_hypothesis_wrapper",
            message="The proof appears to use only one visible hypothesis; review whether this is a real theorem or a documented interface wrapper.",
            file_name=file_name,
            declaration=declaration,
            evidence={"dependency": dependencies[0], "signature": signature},
        )

    if (
        tactics <= {"trivial"}
        and "trivial" in tactics
        and not boundary
        and normalized_conclusion != "True"
    ):
        add_finding(
            findings,
            severity="low",
            code="trivial_tactic_review",
            message="The theorem uses only trivial proof search; review whether the result is substantively encoded in the statement.",
            file_name=file_name,
            declaration=declaration,
            evidence={"tactics": sorted(tactics), "signature": signature},
        )

    return findings


def score_from_findings(findings: Sequence[Dict[str, Any]]) -> int:
    """Document the responsibility of ``score_from_findings``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    high = sum(1 for item in findings if item.get("severity") == "high")
    medium = sum(1 for item in findings if item.get("severity") == "medium")
    low = sum(1 for item in findings if item.get("severity") == "low")
    return max(0, 100 - min(90, 35 * high) - min(35, 7 * medium) - min(10, 2 * low))


def analyze_extractor_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Document the responsibility of ``analyze_extractor_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``analyze_extractor_report`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings: List[Dict[str, Any]] = []
    theorem_like_count = 0
    declaration_count = 0
    for file_packet in report.get("files", []) or []:
        file_name = str(file_packet.get("file", "<unknown>"))
        for declaration in file_packet.get("declarations", []) or []:
            declaration_count += 1
            if declaration.get("kind") in THEOREM_LIKE:
                theorem_like_count += 1
            findings.extend(declaration_findings(file_name, declaration))
    blocking = [item for item in findings if item.get("severity") == "high"]
    return {
        "generated_at_utc": utc_now(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": not blocking,
        "summary": {
            "declaration_count": declaration_count,
            "theorem_like_count": theorem_like_count,
            "finding_count": len(findings),
            "blocking_finding_count": len(blocking),
            "nonvacuity_score": score_from_findings(findings),
        },
        "findings": findings,
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
    good_text = """
/--
Generated note (NL): This interface wrapper is represented by an explicit assumption boundary.
-/
theorem good_wrapper (P : Prop) (h : P) : P := by
  exact h
"""
    bad_text = """
/--
Original source (NL): The target conclusion follows.
-/
theorem bad_false_hypothesis (P : Prop) (h : False) : P := by
  cases h
"""
    good = analyze_extractor_report(
        extractor_for_text(good_text, "good_nonvacuity_fixture")
    )
    bad = analyze_extractor_report(
        extractor_for_text(bad_text, "bad_nonvacuity_fixture")
    )
    bad_codes = {item.get("code") for item in bad.get("findings", [])}
    ok = (
        bool(good.get("ok"))
        and not bool(bad.get("ok"))
        and "false_hypothesis_vacuity" in bad_codes
    )
    return {
        "generated_at_utc": utc_now(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": ok,
        "summary": {
            "good_fixture_ok": good.get("ok"),
            "bad_fixture_ok": bad.get("ok"),
            "bad_codes": sorted(str(code) for code in bad_codes),
        },
        "fixtures": {"good": good, "bad": bad},
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
    parser.add_argument(
        "--lean-file", action="append", default=[], help="Lean file to analyze."
    )
    parser.add_argument("--text", help="Inline Lean text fixture to analyze.")
    parser.add_argument(
        "--name", default="inline.lean", help="Name for inline text input."
    )
    parser.add_argument(
        "--extractor-report",
        type=Path,
        help="Existing informalization extractor JSON report.",
    )
    parser.add_argument(
        "--include-extractor-report",
        action="store_true",
        help="Embed the extractor report in output.",
    )
    parser.add_argument(
        "--reasoning-log-file", type=Path, help="Optional JSONL reasoning log path."
    )
    parser.add_argument("--output-file", type=Path, help="Optional JSON output path.")
    parser.add_argument(
        "--expect-ok",
        action="store_true",
        help="Return nonzero when the report is not ok.",
    )
    parser.add_argument(
        "--self-test", action="store_true", help="Run built-in fixtures."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
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
    if args.self_test:
        report = run_self_test()
    else:
        append_event(args.reasoning_log_file, "lean_nonvacuity_consistency_start", {})
        if args.extractor_report:
            extractor_report = json.loads(
                args.extractor_report.read_text(encoding="utf-8")
            )
        elif args.text is not None:
            extractor_report = extractor_for_text(args.text, args.name)
        else:
            paths = [Path(path) for path in args.lean_file]
            extractor_report = extractor_for_paths(paths)
        report = analyze_extractor_report(extractor_report)
        if args.include_extractor_report:
            report["extractor_report"] = extractor_report
        append_event(
            args.reasoning_log_file,
            "lean_nonvacuity_consistency_complete",
            report.get("summary", {}),
        )

    if args.output_file:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        args.output_file.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"ok={report.get('ok')} nonvacuity_score={report.get('summary', {}).get('nonvacuity_score')} "
            f"findings={report.get('summary', {}).get('finding_count', 0)}"
        )
    return 1 if args.expect_ok and not report.get("ok") else 0


if __name__ == "__main__":
    raise SystemExit(main())
