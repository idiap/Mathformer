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

"""Extract conservative informalization packets from Lean4 artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
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


SKILL_NAME = "lean-informalization-extractor"
HOOK_ID = "postformalization.informalize"

DECL_RE = re.compile(
    r"^\s*(?:private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
    r"(?P<kind>theorem|lemma|def|abbrev|structure|class|instance|axiom)\b"
    r"(?:\s+(?P<name>[A-Za-z_][A-Za-z0-9_'.]*))?"
)
IMPORT_RE = re.compile(r"^\s*import\s+([A-Za-z0-9_'.]+)")
PLACEHOLDER_RE = re.compile(r"(?<![A-Za-z0-9_])(sorry|admit|exact\?)(?![A-Za-z0-9_])")
TACTIC_RE = re.compile(
    r"\b("
    r"exact|intro|intros|apply|refine|constructor|cases|simp|simpa|rw|rfl|"
    r"trivial|omega|linarith|ring|norm_num|aesop|tauto|have|let|specialize|"
    r"calc|ext|funext"
    r")\b"
)
DEPENDENCY_RE = re.compile(
    r"\b(?:exact|apply|refine|simpa\s+using|rw\s+\[?)\s+([A-Za-z_][A-Za-z0-9_'.]*)"
)
DOC_MARKER_RE = re.compile(
    r"^\s*(?P<label>"
    r"Original source(?:\s+\([^)]+\))?|Natural language|LaTeX|"
    r"Generated note(?:\s+\([^)]+\))?|Generated equivalent(?:\s+\([^)]+\))?|"
    r"Formalization note|Mathlib grounding(?:\s+\([^)]+\))?|"
    r"Interface note|Operational note|Draft note"
    r")\s*:\s*(?P<value>.*)$",
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


def normalize_comment_line(line: str) -> str:
    """Document the responsibility of ``normalize_comment_line``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_comment_line`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    stripped = line.strip()
    if stripped.startswith("/--"):
        stripped = stripped[3:]
    if stripped.endswith("-/"):
        stripped = stripped[:-2]
    return stripped.strip(" *")


def compact(text: str) -> str:
    """Document the responsibility of ``compact``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``compact`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return " ".join(text.split())


def parse_doc_comment(comment: str) -> Dict[str, Any]:
    """Document the responsibility of ``parse_doc_comment``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    fields: Dict[str, List[str]] = {
        "original_nl": [],
        "original_latex": [],
        "generated_notes": [],
        "generated_equivalents": [],
        "mathlib_grounding": [],
        "other": [],
    }
    current = "other"
    for raw_line in comment.splitlines():
        line = normalize_comment_line(raw_line)
        if not line:
            continue
        match = DOC_MARKER_RE.match(line)
        if match:
            label = match.group("label").lower()
            value = match.group("value").strip()
            if "original source" in label and "(nl)" in label:
                current = "original_nl"
            elif label == "natural language":
                current = "original_nl"
            elif (
                "original source" in label and "(latex)" in label
            ) or label == "latex":
                current = "original_latex"
            elif "generated equivalent" in label:
                current = "generated_equivalents"
            elif "mathlib grounding" in label:
                current = "mathlib_grounding"
            elif (
                "generated note" in label
                or "formalization note" in label
                or "interface note" in label
                or "operational note" in label
                or "draft note" in label
            ):
                current = "generated_notes"
            else:
                current = "other"
            if value:
                fields[current].append(value)
            continue
        fields[current].append(line)
    return {key: compact(" ".join(value)) for key, value in fields.items()}


def collect_declarations(lines: List[str]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``collect_declarations``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``collect_declarations`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    declarations: List[Dict[str, Any]] = []
    pending_doc: Optional[Tuple[int, int, str]] = None
    in_doc = False
    doc_start = 0
    doc_lines: List[str] = []
    in_block_comment = False
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if in_block_comment:
            if "-/" in stripped:
                in_block_comment = False
            continue
        if in_doc:
            doc_lines.append(line)
            if "-/" in stripped:
                pending_doc = (doc_start, idx, "\n".join(doc_lines))
                in_doc = False
                doc_lines = []
            continue
        if stripped.startswith("/--"):
            doc_start = idx
            doc_lines = [line]
            if "-/" in stripped:
                pending_doc = (doc_start, idx, "\n".join(doc_lines))
                doc_lines = []
            else:
                in_doc = True
            continue
        if stripped.startswith("/-"):
            if "-/" not in stripped:
                in_block_comment = True
            continue
        if not stripped or stripped.startswith("@["):
            continue
        match = DECL_RE.match(line)
        if match:
            kind = match.group("kind")
            name = match.group("name") or f"anonymous_{kind}_{idx}"
            doc = pending_doc
            declarations.append(
                {
                    "kind": kind,
                    "name": name,
                    "line": idx,
                    "doc_start_line": doc[0] if doc else None,
                    "doc_end_line": doc[1] if doc else None,
                    "doc_comment": doc[2] if doc else "",
                }
            )
            pending_doc = None
        else:
            pending_doc = None
    for pos, declaration in enumerate(declarations):
        next_doc_start = (
            declarations[pos + 1].get("doc_start_line")
            if pos + 1 < len(declarations)
            else None
        )
        end_line = (next_doc_start - 1) if next_doc_start else len(lines)
        start_line = int(declaration["line"])
        segment = "\n".join(lines[start_line - 1 : end_line])
        declaration["end_line"] = end_line
        declaration["segment"] = segment
        declaration["signature"] = split_signature_and_body(
            declaration["kind"], segment
        )[0]
    return declarations


def split_signature_and_body(kind: str, segment: str) -> Tuple[str, str]:
    """Document the responsibility of ``split_signature_and_body``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``split_signature_and_body`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if ":= by" in segment:
        index = segment.find(":= by")
        return compact(segment[: index + len(":= by")]), segment[index + len(":= by") :]
    if kind in {"theorem", "lemma"}:
        index = segment.rfind(":=")
    else:
        index = segment.find(":=")
    if index >= 0:
        return compact(segment[: index + len(":=")]), segment[index + len(":=") :]
    return compact(segment), ""


def proof_body(segment: str) -> str:
    """Document the responsibility of ``proof_body``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``proof_body`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return split_signature_and_body("theorem", segment)[1]


def declaration_proof_body(kind: str, segment: str) -> str:
    """Document the responsibility of ``declaration_proof_body``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``declaration_proof_body`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return split_signature_and_body(kind, segment)[1]


def theorem_like(kind: str) -> bool:
    """Document the responsibility of ``theorem_like``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``theorem_like`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return kind in {"theorem", "lemma", "axiom"}


def summarize_proof(kind: str, name: str, segment: str) -> Dict[str, Any]:
    """Document the responsibility of ``summarize_proof``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``summarize_proof`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    body = declaration_proof_body(kind, segment)
    tactics = sorted(set(TACTIC_RE.findall(body)))
    dependencies = []
    for match in DEPENDENCY_RE.finditer(body):
        dep = match.group(1).rstrip("],)")
        if dep not in dependencies:
            dependencies.append(dep)
    exact_match = re.search(r"\bexact\s+([A-Za-z_][A-Za-z0-9_'.]*)", body)
    delegated = bool(exact_match and exact_match.group(1).startswith("h"))
    placeholders = sorted(set(PLACEHOLDER_RE.findall(segment)))
    if not theorem_like(kind):
        summary = f"`{name}` introduces a {kind} with the Lean definition or fields shown in its signature."
    elif kind == "axiom":
        summary = f"`{name}` is declared as an axiom, so no Lean proof body is present."
    elif not body.strip():
        summary = f"`{name}` has no parsed Lean proof body in this extractor pass."
    elif "rfl" in tactics:
        summary = f"`{name}` is closed by definitional equality (`rfl`) within Lean."
    elif "trivial" in tactics:
        summary = f"`{name}` is closed by Lean's trivial proof search."
    elif exact_match:
        summary = f"`{name}` is proved by exact use of `{exact_match.group(1)}`."
    elif tactics:
        summary = f"`{name}` is proved with Lean tactics: {', '.join(tactics)}."
    else:
        summary = f"`{name}` is proved by a Lean proof term or tactic block not classified by this extractor."
    return {
        "body_line_count": len([line for line in body.splitlines() if line.strip()]),
        "tactics": tactics,
        "probable_dependencies": dependencies,
        "placeholder_tokens": placeholders,
        "delegated_to_hypothesis": delegated,
        "summary": summary,
    }


def informal_statement_for(
    declaration: Dict[str, Any], doc_fields: Dict[str, str]
) -> str:
    """Document the responsibility of ``informal_statement_for``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``informal_statement_for`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if doc_fields.get("original_nl"):
        return doc_fields["original_nl"]
    if doc_fields.get("generated_notes"):
        return doc_fields["generated_notes"]
    return f"Lean declaration `{declaration['name']}` has signature: {declaration['signature']}"


def declaration_findings(
    declaration: Dict[str, Any], doc_fields: Dict[str, str], proof: Dict[str, Any]
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
    kind = declaration["kind"]
    if not declaration.get("doc_comment"):
        findings.append(
            {
                "severity": "high" if theorem_like(kind) else "medium",
                "code": "missing_doc_comment",
                "message": "Declaration lacks a source-aware doc comment for reverse informalization.",
                "line": declaration["line"],
            }
        )
    elif not any(
        doc_fields.get(key)
        for key in (
            "original_nl",
            "original_latex",
            "generated_notes",
            "generated_equivalents",
        )
    ):
        findings.append(
            {
                "severity": "medium",
                "code": "weak_doc_comment",
                "message": "Doc comment does not expose original-source or generated-note alignment.",
                "line": declaration["line"],
            }
        )
    if proof["placeholder_tokens"]:
        findings.append(
            {
                "severity": "high",
                "code": "placeholder_in_proof",
                "message": "Proof segment contains unresolved placeholder tokens.",
                "line": declaration["line"],
                "tokens": proof["placeholder_tokens"],
            }
        )
    if kind == "axiom":
        findings.append(
            {
                "severity": "high",
                "code": "axiom_declaration",
                "message": "Axioms cannot be informalized as completed Lean proofs.",
                "line": declaration["line"],
            }
        )
    if theorem_like(kind) and proof["body_line_count"] == 0 and kind != "axiom":
        findings.append(
            {
                "severity": "high",
                "code": "missing_proof_body",
                "message": "Theorem-like declaration has no parsed proof body.",
                "line": declaration["line"],
            }
        )
    if proof["delegated_to_hypothesis"]:
        findings.append(
            {
                "severity": "low",
                "code": "delegated_to_hypothesis",
                "message": "Proof closes by exact use of a hypothesis; keep the delegation visible in consistency review.",
                "line": declaration["line"],
            }
        )
    return findings


def extract_text(text: str, *, name: str) -> Dict[str, Any]:
    """Document the responsibility of ``extract_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = text.splitlines()
    imports = [match.group(1) for line in lines if (match := IMPORT_RE.match(line))]
    declarations = collect_declarations(lines)
    packets: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    for declaration in declarations:
        doc_fields = parse_doc_comment(declaration.get("doc_comment", ""))
        proof = summarize_proof(
            declaration["kind"], declaration["name"], declaration["segment"]
        )
        decl_findings = declaration_findings(declaration, doc_fields, proof)
        for item in decl_findings:
            findings.append({"file": name, "declaration": declaration["name"], **item})
        packets.append(
            {
                "kind": declaration["kind"],
                "name": declaration["name"],
                "line": declaration["line"],
                "end_line": declaration["end_line"],
                "signature": declaration["signature"],
                "doc_comment": declaration.get("doc_comment", ""),
                "informal_statement": informal_statement_for(declaration, doc_fields),
                "source_alignment": doc_fields,
                "proof_summary": proof["summary"],
                "proof_features": {
                    key: value for key, value in proof.items() if key != "summary"
                },
                "findings": decl_findings,
            }
        )
    theorem_like_count = sum(1 for item in packets if theorem_like(item["kind"]))
    return {
        "file": name,
        "imports": imports,
        "line_count": len(lines),
        "declarations": packets,
        "summary": {
            "declaration_count": len(packets),
            "theorem_like_count": theorem_like_count,
            "finding_count": len(findings),
            "blocking_finding_count": sum(
                1 for item in findings if item.get("severity") == "high"
            ),
        },
        "findings": findings,
    }


def extract_files(paths: Sequence[Path]) -> Dict[str, Any]:
    """Document the responsibility of ``extract_files``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_files`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    files = []
    all_findings: List[Dict[str, Any]] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        packet = extract_text(text, name=rel(path))
        files.append(packet)
        all_findings.extend(packet["findings"])
    return build_report(files, all_findings)


def build_report(
    files: List[Dict[str, Any]], findings: List[Dict[str, Any]]
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
    declaration_count = sum(file["summary"]["declaration_count"] for file in files)
    theorem_like_count = sum(file["summary"]["theorem_like_count"] for file in files)
    blocking = [item for item in findings if item.get("severity") == "high"]
    return {
        "generated_at_utc": utc_now(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": not blocking,
        "summary": {
            "file_count": len(files),
            "declaration_count": declaration_count,
            "theorem_like_count": theorem_like_count,
            "finding_count": len(findings),
            "blocking_finding_count": len(blocking),
        },
        "files": files,
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
            "theorem generated_bad : True := by",
            "  sorry",
        ]
    )
    good_report = extract_text(good, name="good_fixture")
    bad_report = extract_text(bad, name="bad_fixture")
    report = build_report(
        [good_report, bad_report], [*good_report["findings"], *bad_report["findings"]]
    )
    report["self_test"] = {
        "good_ok": good_report["summary"]["blocking_finding_count"] == 0,
        "bad_blocked": bad_report["summary"]["blocking_finding_count"] > 0,
    }
    report["ok"] = report["self_test"]["good_ok"] and report["self_test"]["bad_blocked"]
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
        f"files: {summary['file_count']}",
        f"declarations: {summary['declaration_count']}",
        f"theorem_like: {summary['theorem_like_count']}",
        f"findings: {summary['finding_count']}",
        f"blocking: {summary['blocking_finding_count']}",
    ]
    for finding in report.get("findings", [])[:20]:
        lines.append(
            f"- {finding.get('severity')} {finding.get('file')}:{finding.get('line')}: "
            f"{finding.get('code')} {finding.get('message')}"
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
        "lean_informalization_extraction_start",
        {"file_count": len(args.lean_file)},
    )
    if args.self_test:
        report = run_self_test()
    elif args.text:
        file_packet = extract_text(args.text, name=args.name)
        report = build_report([file_packet], file_packet["findings"])
    else:
        paths = [
            (REPO_ROOT / path).resolve() if not path.is_absolute() else path
            for path in args.lean_file
        ]
        report = extract_files(paths)
    append_event(
        reasoning_log,
        "lean_informalization_extraction_complete",
        {"ok": report["ok"], **report["summary"]},
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
