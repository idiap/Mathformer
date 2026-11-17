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

"""Check logical-shape agreement between Lean declarations and source comments."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

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


SKILL_NAME = "lean-declaration-shape-consistency-checker"
HOOK_ID = "consistency.declaration_shape"
EXTRACTOR_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "lean"
    / "lean-informalization-extractor"
    / "scripts"
    / "extract_lean_informalization.py"
)

THEOREM_LIKE = {"theorem", "lemma", "axiom"}


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


def source_text(declaration: Dict[str, Any]) -> str:
    """Document the responsibility of ``source_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``source_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    fields = declaration.get("source_alignment", {}) or {}
    pieces = [
        fields.get("original_nl", ""),
        fields.get("original_latex", ""),
        fields.get("generated_notes", ""),
        fields.get("generated_equivalents", ""),
        declaration.get("informal_statement", ""),
    ]
    return " ".join(str(piece) for piece in pieces if piece)


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
        "assumption",
        "axiomatized",
        "certificate",
        "explicit witness",
        "external",
        "field",
        "interface",
        "model",
        "operational consequence",
        "parameter",
        "predicate",
        "criterion",
        "record",
        "represented",
        "structure",
        "witness field",
    )
    return any(marker in text for marker in markers)


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
    lowered = f" {text.lower()} "
    return any(
        token in text for token in ("\\iff", "\\Leftrightarrow", "<->", "<=>", "\u2194")
    ) or any(
        phrase in lowered
        for phrase in (
            " if and only if ",
            " iff ",
            " equivalent to ",
            " are equivalent ",
        )
    )


def signature_has_equivalence(signature: str) -> bool:
    """Document the responsibility of ``signature_has_equivalence``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``signature_has_equivalence`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return any(
        token in signature for token in ("\u2194", " Iff ", "Iff.", "<->", "\\iff")
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
    lowered = f" {text.lower()} "
    return any(token in text for token in ("\\exists", "\u2203")) or any(
        phrase in lowered
        for phrase in (
            " there exists ",
            " exists ",
            " existence of ",
            " nonempty ",
            " has a witness ",
            " admits ",
        )
    )


def signature_has_existential(signature: str, declaration: Dict[str, Any]) -> bool:
    """Document the responsibility of ``signature_has_existential``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``signature_has_existential`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    name = str(declaration.get("name", ""))
    combined = f"{signature} {name}"
    return any(
        token in combined
        for token in (
            "\u2203",
            "\u03a3",
            "Exists",
            "ExistsUnique",
            "Nonempty",
            "Subtype",
            "Sigma",
            "Certificate",
            "Existence",
            "Witness",
        )
    )


def has_uniqueness_claim(text: str) -> bool:
    """Document the responsibility of ``has_uniqueness_claim``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_uniqueness_claim`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lowered = f" {text.lower()} "
    return any(token in text for token in ("\\exists!", "\u2203!")) or any(
        phrase in lowered
        for phrase in (" unique ", " uniquely ", " uniqueness ", " exactly one ")
    )


def signature_has_uniqueness(signature: str) -> bool:
    """Document the responsibility of ``signature_has_uniqueness``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``signature_has_uniqueness`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return any(
        token in signature
        for token in (
            "\u2203!",
            "ExistsUnique",
            "Unique",
            "Subsingleton",
            "Function.Injective",
            "=",
        )
    )


def has_implication_claim(text: str) -> bool:
    """Document the responsibility of ``has_implication_claim``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_implication_claim`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lowered = f" {text.lower()} "
    return any(
        token in text for token in ("\\Rightarrow", "\\to", "\u2192", "=>")
    ) or any(
        phrase in lowered for phrase in (" implies ", " imply ", " whenever ", " if ")
    )


def signature_has_implication(signature: str) -> bool:
    """Document the responsibility of ``signature_has_implication``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``signature_has_implication`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return (
        any(token in signature for token in ("\u2192", "->", "=>"))
        or bool(re.search(r"\([A-Za-z_][A-Za-z0-9_']*\s*:\s*[^)]*\)", signature))
        or bool(re.search(r"[\(\{][^)\}]+:[^)\}]+[\)\}]", signature))
    )


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
    signature = str(declaration.get("signature", ""))
    text = source_text(declaration)
    boundary = has_boundary_marker(declaration)

    if not declaration.get("informal_statement"):
        add_finding(
            findings,
            severity="high",
            code="missing_informal_statement",
            message="The theorem-like declaration has no source-facing informal statement.",
            file_name=file_name,
            declaration=declaration,
            evidence={"signature": signature},
        )

    source_fields = declaration.get("source_alignment", {}) or {}
    if not any(
        str(source_fields.get(key, "")).strip()
        for key in (
            "original_nl",
            "original_latex",
            "generated_notes",
            "generated_equivalents",
        )
    ):
        add_finding(
            findings,
            severity="medium",
            code="missing_source_alignment_packet",
            message="The theorem-like declaration has no original or generated statement annotation.",
            file_name=file_name,
            declaration=declaration,
            evidence={"signature": signature},
        )

    if has_equivalence_claim(text) and not signature_has_equivalence(f" {signature} "):
        add_finding(
            findings,
            severity="high",
            code="equivalence_shape_mismatch",
            message="The source advertises an equivalence/iff claim, but the Lean signature is not visibly bidirectional.",
            file_name=file_name,
            declaration=declaration,
            evidence={"source_text": text[:500], "signature": signature},
        )

    if (
        has_existential_claim(text)
        and not signature_has_existential(signature, declaration)
        and not boundary
    ):
        add_finding(
            findings,
            severity="high",
            code="existential_shape_mismatch",
            message="The source advertises existence, but the Lean signature has no visible existential, witness, certificate, or representation note.",
            file_name=file_name,
            declaration=declaration,
            evidence={"source_text": text[:500], "signature": signature},
        )

    if (
        has_uniqueness_claim(text)
        and not signature_has_uniqueness(signature)
        and not boundary
    ):
        add_finding(
            findings,
            severity="medium",
            code="uniqueness_shape_review",
            message="The source advertises uniqueness; verify that the Lean signature preserves or explicitly represents uniqueness.",
            file_name=file_name,
            declaration=declaration,
            evidence={"source_text": text[:500], "signature": signature},
        )

    if has_implication_claim(text) and not signature_has_implication(signature):
        add_finding(
            findings,
            severity="low",
            code="conditional_shape_review",
            message="The source sounds conditional, but no hypothesis/arrow is visible in the Lean signature.",
            file_name=file_name,
            declaration=declaration,
            evidence={"source_text": text[:500], "signature": signature},
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
    return max(0, 100 - min(80, 30 * high) - min(35, 8 * medium) - min(10, 2 * low))


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
    shape_score = score_from_findings(findings)
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
            "shape_score": shape_score,
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
Original source (NL): P iff Q.
Original source (LaTeX): `P \\iff Q`.
-/
theorem good_shape (P Q : Prop) : Iff P Q := by
  sorry
"""
    bad_text = """
/--
Original source (NL): P iff Q.
Original source (LaTeX): `P \\iff Q`.
-/
theorem bad_shape (P Q : Prop) : P -> Q := by
  sorry
"""
    good = analyze_extractor_report(extractor_for_text(good_text, "good_shape_fixture"))
    bad = analyze_extractor_report(extractor_for_text(bad_text, "bad_shape_fixture"))
    bad_codes = {item.get("code") for item in bad.get("findings", [])}
    ok = (
        bool(good.get("ok"))
        and not bool(bad.get("ok"))
        and "equivalence_shape_mismatch" in bad_codes
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
        append_event(
            args.reasoning_log_file, "lean_declaration_shape_consistency_start", {}
        )
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
            "lean_declaration_shape_consistency_complete",
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
            f"ok={report.get('ok')} shape_score={report.get('summary', {}).get('shape_score')} "
            f"findings={report.get('summary', {}).get('finding_count', 0)}"
        )
    return 1 if args.expect_ok and not report.get("ok") else 0


if __name__ == "__main__":
    raise SystemExit(main())
