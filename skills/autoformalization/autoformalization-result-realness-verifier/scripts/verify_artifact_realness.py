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

"""Verify that autoformalization artifacts are not mocked final results."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

try:
    from reasoning_log import append_reasoning_log_entry
except Exception:  # pragma: no cover - script must still work standalone.
    append_reasoning_log_entry = None  # type: ignore[assignment]


SKILL_NAME = "autoformalization-result-realness-verifier"
HOOK_ID = "artifact.realness_gate"

TEXT_PATTERNS: List[Tuple[str, str, str]] = [
    (
        "sorry_placeholder",
        r"(?<![A-Za-z0-9_])sorry(?![A-Za-z0-9_])",
        "Lean contains `sorry`.",
    ),
    (
        "admit_placeholder",
        r"(?<![A-Za-z0-9_])admit(?![A-Za-z0-9_])",
        "Lean contains `admit`.",
    ),
    (
        "axiom_placeholder",
        r"(?<![A-Za-z0-9_])axiom(?![A-Za-z0-9_])",
        "Lean contains an `axiom` declaration.",
    ),
    (
        "exact_query_placeholder",
        r"(?<![A-Za-z0-9_])exact\?",
        "Lean contains an unresolved `exact?` suggestion.",
    ),
    (
        "mock_marker",
        r"(?i)\b(mock|mocked|stub|fake|simulated)\b",
        "Artifact contains a mock/stub marker.",
    ),
    (
        "placeholder_marker",
        r"(?i)\bplaceholder\b",
        "Artifact contains a placeholder marker.",
    ),
    ("todo_marker", r"\b(TODO|FIXME)\b", "Artifact contains TODO/FIXME markers."),
]

SCAFFOLD_PATTERNS: List[Tuple[str, str, str]] = [
    (
        "interface_scaffold_marker",
        r"(?i)\binterface scaffold\b",
        "Artifact is labeled as an interface scaffold.",
    ),
    ("scaffold_marker", r"(?i)\bscaffold\b", "Artifact is labeled as a scaffold."),
    (
        "intentionally_abstract_marker",
        r"(?i)\bintentionally abstract\b",
        "Artifact contains an intentionally abstract boundary.",
    ),
    (
        "abstract_boundary_marker",
        r"(?i)\babstract boundary\b",
        "Artifact contains an abstract boundary marker.",
    ),
]

REPORT_BAD_STATUS = {
    "mock",
    "mocked",
    "planned",
    "simulated",
    "skipped",
    "stub",
    "unexecuted",
}

LEGACY_LINE_COMMENT_MARKER = "NL/LaTeX:"
SYNTACTIC_PREFIXES = (
    "import ",
    "open ",
    "open scoped ",
    "namespace ",
    "end ",
    "section ",
    "noncomputable section",
    "universe ",
    "variable ",
    "set_option ",
)
NOISE_COMMENT_RE = re.compile(
    r"^\s*--\s*(?:NL/LaTeX:\s*)?"
    r"(?:separate|separates|close|closes|open|opens|begin|begins|end|ends)\b",
    re.IGNORECASE,
)
DECLARATION_RE = re.compile(
    r"^\s*(?:private\s+|protected\s+|noncomputable\s+)*"
    r"(?:theorem|lemma|def|abbrev|structure|class|instance)\b"
)
SEMANTIC_COMMENT_RE = re.compile(
    r"\b(?:"
    r"Original source|Source theorem|Source statement|Natural language|LaTeX|"
    r"Generated note|Generated equivalent|Formalization note|Mathlib grounding|"
    r"Interface note|Operational note|Draft note"
    r")\b",
    re.IGNORECASE,
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


def line_col(text: str, pos: int) -> Tuple[int, int]:
    """Document the responsibility of ``line_col``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``line_col`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    line = text.count("\n", 0, pos) + 1
    last_newline = text.rfind("\n", 0, pos)
    col = pos + 1 if last_newline == -1 else pos - last_newline
    return line, col


def snippet(text: str, start: int, end: int) -> str:
    """Document the responsibility of ``snippet``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``snippet`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    left = max(0, start - 45)
    right = min(len(text), end + 45)
    return " ".join(text[left:right].split())


def is_syntactic_line(stripped: str) -> bool:
    """Document the responsibility of ``is_syntactic_line``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``is_syntactic_line`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return stripped.startswith(SYNTACTIC_PREFIXES)


def is_declaration_line(stripped: str) -> bool:
    """Document the responsibility of ``is_declaration_line``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``is_declaration_line`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return bool(DECLARATION_RE.match(stripped))


def has_semantic_annotation(comment: str) -> bool:
    """Document the responsibility of ``has_semantic_annotation``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_semantic_annotation`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return bool(SEMANTIC_COMMENT_RE.search(comment))


def finding(
    *,
    code: str,
    severity: str,
    source: str,
    message: str,
    path: Optional[str] = None,
    line: Optional[int] = None,
    column: Optional[int] = None,
    evidence: Optional[str] = None,
) -> Dict[str, Any]:
    """Document the responsibility of ``finding``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    result: Dict[str, Any] = {
        "code": code,
        "severity": severity,
        "source": source,
        "message": message,
    }
    if path is not None:
        result["path"] = path
    if line is not None:
        result["line"] = line
    if column is not None:
        result["column"] = column
    if evidence is not None:
        result["evidence"] = evidence
    return result


def scan_text(
    *,
    text: str,
    source: str,
    path: Optional[str],
    artifact_status: str,
    allow_placeholders: bool,
    allow_interface_scaffold: bool,
    check_comment_hygiene: bool,
    require_semantic_comments: bool,
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``scan_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``scan_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings: List[Dict[str, Any]] = []
    for code, pattern, message in TEXT_PATTERNS:
        for match in re.finditer(pattern, text):
            line, col = line_col(text, match.start())
            severity = (
                "low" if artifact_status == "draft" or allow_placeholders else "high"
            )
            findings.append(
                finding(
                    code=code,
                    severity=severity,
                    source=source,
                    path=path,
                    line=line,
                    column=col,
                    message=message,
                    evidence=snippet(text, match.start(), match.end()),
                )
            )
    for code, pattern, message in SCAFFOLD_PATTERNS:
        for match in re.finditer(pattern, text):
            line, col = line_col(text, match.start())
            severity = (
                "low"
                if artifact_status == "draft" or allow_interface_scaffold
                else "high"
            )
            findings.append(
                finding(
                    code=code,
                    severity=severity,
                    source=source,
                    path=path,
                    line=line,
                    column=col,
                    message=message,
                    evidence=snippet(text, match.start(), match.end()),
                )
            )
    if check_comment_hygiene and source in {"lean_scan", "inline_text_scan"}:
        pending_doc_comment: Optional[str] = None
        in_doc_comment = False
        in_block_comment = False
        doc_comment_lines: List[str] = []
        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if in_block_comment:
                if "-/" in stripped:
                    in_block_comment = False
                continue
            if in_doc_comment:
                doc_comment_lines.append(stripped)
                if "-/" in stripped:
                    pending_doc_comment = "\n".join(doc_comment_lines)
                    in_doc_comment = False
                    doc_comment_lines = []
                continue
            if stripped.startswith("/--"):
                doc_comment_lines = [stripped]
                if "-/" in stripped:
                    pending_doc_comment = "\n".join(doc_comment_lines)
                    doc_comment_lines = []
                else:
                    in_doc_comment = True
                continue
            if stripped.startswith("/-"):
                if "-/" not in stripped:
                    in_block_comment = True
                continue
            if not stripped:
                continue
            if LEGACY_LINE_COMMENT_MARKER in line:
                findings.append(
                    finding(
                        code="legacy_nl_latex_line_comment",
                        severity="high" if artifact_status == "final" else "low",
                        source=source,
                        path=path,
                        line=line_no,
                        message=(
                            "Generated Lean uses the legacy per-line "
                            f"`{LEGACY_LINE_COMMENT_MARKER}` comment style."
                        ),
                        evidence=line,
                    )
                )
            if NOISE_COMMENT_RE.match(stripped):
                findings.append(
                    finding(
                        code="syntax_only_comment",
                        severity="high" if artifact_status == "final" else "low",
                        source=source,
                        path=path,
                        line=line_no,
                        message="Generated Lean comment only describes syntactic file structure.",
                        evidence=line,
                    )
                )
            if (
                is_syntactic_line(stripped)
                and "--" in line
                and not stripped.startswith("--")
            ):
                findings.append(
                    finding(
                        code="comment_on_syntactic_line",
                        severity="high" if artifact_status == "final" else "low",
                        source=source,
                        path=path,
                        line=line_no,
                        message="Generated Lean attaches an explanatory comment to a syntactic line.",
                        evidence=line,
                    )
                )
            if require_semantic_comments and is_declaration_line(stripped):
                severity = "high" if artifact_status == "final" else "low"
                if pending_doc_comment is None:
                    findings.append(
                        finding(
                            code="missing_semantic_declaration_comment",
                            severity=severity,
                            source=source,
                            path=path,
                            line=line_no,
                            message=(
                                "Generated Lean declaration lacks a source-aware doc comment "
                                "with Natural language/LaTeX or generated-note alignment."
                            ),
                            evidence=line,
                        )
                    )
                elif not has_semantic_annotation(pending_doc_comment):
                    findings.append(
                        finding(
                            code="thin_semantic_declaration_comment",
                            severity=severity,
                            source=source,
                            path=path,
                            line=line_no,
                            message=(
                                "Generated Lean declaration doc comment does not identify "
                                "source alignment or generated formalization notes."
                            ),
                            evidence=line,
                        )
                    )
                pending_doc_comment = None
            elif not stripped.startswith("--") and not stripped.startswith("@["):
                pending_doc_comment = None
    return findings


def iter_json_atoms(value: Any, prefix: str = "$") -> Iterable[Tuple[str, Any]]:
    """Document the responsibility of ``iter_json_atoms``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``iter_json_atoms`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if isinstance(value, dict):
        for key, child in value.items():
            yield from iter_json_atoms(child, f"{prefix}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_json_atoms(child, f"{prefix}[{index}]")
    else:
        yield prefix, value


def scan_report(path: Path, artifact_status: str) -> List[Dict[str, Any]]:
    """Document the responsibility of ``scan_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``scan_report`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings: List[Dict[str, Any]] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [
            finding(
                code="report_parse_error",
                severity="high",
                source="report_scan",
                path=rel(path),
                message=f"Could not parse report JSON: {exc}",
            )
        ]

    for atom_path, value in iter_json_atoms(data):
        key = atom_path.rsplit(".", 1)[-1].lower()
        if isinstance(value, str):
            lowered = value.lower()
            if (
                key in {"status", "state", "verdict", "result_source"}
                and lowered in REPORT_BAD_STATUS
            ):
                findings.append(
                    finding(
                        code="report_non_real_status",
                        severity="high" if artifact_status == "final" else "low",
                        source="report_scan",
                        path=rel(path),
                        message=f"Report field {atom_path} has non-real status `{value}`.",
                    )
                )
            if re.search(r"\b(mock|mocked|stub|fake|simulated|placeholder)\b", lowered):
                findings.append(
                    finding(
                        code="report_mock_marker",
                        severity="high" if artifact_status == "final" else "low",
                        source="report_scan",
                        path=rel(path),
                        message=f"Report field {atom_path} contains a mock/stub marker.",
                        evidence=value[:240],
                    )
                )
        if isinstance(value, bool):
            if (
                key in {"correctness", "executed", "execution_ok", "lean_ok"}
                and value is False
            ):
                findings.append(
                    finding(
                        code="report_failed_execution_gate",
                        severity="high" if artifact_status == "final" else "low",
                        source="report_scan",
                        path=rel(path),
                        message=f"Report field {atom_path} is false.",
                    )
                )
        if isinstance(value, int):
            if key == "planned_count" and value > 0:
                findings.append(
                    finding(
                        code="report_planned_outputs_remaining",
                        severity="high" if artifact_status == "final" else "low",
                        source="report_scan",
                        path=rel(path),
                        message=f"Report field {atom_path} has {value} planned outputs remaining.",
                    )
                )
    return findings


def append_event(reasoning_log: Optional[Path], report: Dict[str, Any]) -> None:
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
        step="result_realness_verification_complete",
        payload={
            "skill": SKILL_NAME,
            "hook_id": HOOK_ID,
            "ok": report["ok"],
            "artifact_status": report["artifact_status"],
            "finding_count": report["summary"]["finding_count"],
            "blocking_finding_count": report["summary"]["blocking_finding_count"],
        },
    )


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
    findings: List[Dict[str, Any]] = []
    scanned: List[str] = []

    for lean_file in args.lean_file:
        path = (REPO_ROOT / lean_file).resolve()
        text = path.read_text(encoding="utf-8")
        scanned.append(rel(path))
        findings.extend(
            scan_text(
                text=text,
                source="lean_scan",
                path=rel(path),
                artifact_status=args.artifact_status,
                allow_placeholders=args.allow_placeholders,
                allow_interface_scaffold=args.allow_interface_scaffold,
                check_comment_hygiene=not args.skip_line_comment_check,
                require_semantic_comments=not args.skip_semantic_comment_check,
            )
        )

    for index, text in enumerate(args.text):
        name = args.name or f"inline_text_{index + 1}"
        scanned.append(name)
        findings.extend(
            scan_text(
                text=text,
                source="inline_text_scan",
                path=name,
                artifact_status=args.artifact_status,
                allow_placeholders=args.allow_placeholders,
                allow_interface_scaffold=args.allow_interface_scaffold,
                check_comment_hygiene=not args.skip_line_comment_check,
                require_semantic_comments=not args.skip_semantic_comment_check,
            )
        )

    for report_file in [*args.report_file, *args.history_file]:
        path = (REPO_ROOT / report_file).resolve()
        scanned.append(rel(path))
        findings.extend(scan_report(path, args.artifact_status))

    blocking = [item for item in findings if item["severity"] == "high"]
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "artifact_status": args.artifact_status,
        "ok": not blocking,
        "scanned": scanned,
        "summary": {
            "finding_count": len(findings),
            "blocking_finding_count": len(blocking),
            "severity_counts": {
                "high": sum(1 for item in findings if item["severity"] == "high"),
                "medium": sum(1 for item in findings if item["severity"] == "medium"),
                "low": sum(1 for item in findings if item["severity"] == "low"),
            },
        },
        "findings": findings,
    }
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
    lines = [
        f"ok: {report['ok']}",
        f"artifact_status: {report['artifact_status']}",
        f"scanned: {len(report['scanned'])}",
        f"findings: {report['summary']['finding_count']}",
        f"blocking: {report['summary']['blocking_finding_count']}",
    ]
    for item in report["findings"]:
        location = item.get("path", "<unknown>")
        if "line" in item:
            location += f":{item['line']}"
        lines.append(
            f"- {item['severity']} {item['code']} {location}: {item['message']}"
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
    parser.add_argument("--report-file", action="append", type=Path, default=[])
    parser.add_argument("--history-file", action="append", type=Path, default=[])
    parser.add_argument("--text", action="append", default=[])
    parser.add_argument("--name")
    parser.add_argument(
        "--artifact-status", choices=["final", "draft"], default="final"
    )
    parser.add_argument("--allow-placeholders", action="store_true")
    parser.add_argument("--allow-interface-scaffold", action="store_true")
    parser.add_argument(
        "--skip-line-comment-check",
        action="store_true",
        help="Skip generated Lean source-comment hygiene checks.",
    )
    parser.add_argument(
        "--skip-semantic-comment-check",
        action="store_true",
        help="Skip source-aware semantic declaration comment checks.",
    )
    parser.add_argument("--expect-blocking", action="store_true")
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--reasoning-log-file", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if (
        not args.lean_file
        and not args.report_file
        and not args.history_file
        and not args.text
    ):
        parser.error(
            "provide at least one --lean-file, --report-file, --history-file, or --text"
        )
    return args


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
    report = build_report(args)
    if args.output_file is not None:
        output_file = (REPO_ROOT / args.output_file).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    reasoning_log = (
        (REPO_ROOT / args.reasoning_log_file).resolve()
        if args.reasoning_log_file
        else None
    )
    append_event(reasoning_log, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    has_blocking = report["summary"]["blocking_finding_count"] > 0
    if args.expect_blocking:
        return 0 if has_blocking else 4
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
