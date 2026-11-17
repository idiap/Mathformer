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

"""Evaluate internal consistency of informalized Lean proof packets."""

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


SKILL_NAME = "lean-informal-proof-internal-consistency-verifier"
HOOK_ID = "postformalization.informal_internal_consistency"

EXTRACTOR_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "lean"
    / "lean-informalization-extractor"
    / "scripts"
    / "extract_lean_informalization.py"
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
    "proof",
    "proved",
    "statement",
    "declaration",
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


def token_overlap(left: str, right: str) -> float:
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
    left_words = words(left)
    right_words = words(right)
    if not left_words or not right_words:
        return 1.0
    return len(left_words & right_words) / max(
        1, min(len(left_words), len(right_words))
    )


def statement_text(declaration: Dict[str, Any]) -> str:
    """Document the responsibility of ``statement_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``statement_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    fields = declaration.get("source_alignment", {})
    pieces = [
        declaration.get("informal_statement", ""),
        fields.get("generated_equivalents", ""),
        declaration.get("signature", ""),
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
    fields = declaration.get("source_alignment", {})
    pieces = [
        fields.get("generated_notes", ""),
        fields.get("generated_equivalents", ""),
        fields.get("mathlib_grounding", ""),
        fields.get("other", ""),
        declaration.get("informal_statement", ""),
        declaration.get("proof_summary", ""),
    ]
    return " ".join(str(piece) for piece in pieces if piece).lower()


def has_equivalence(text: str) -> bool:
    """Document the responsibility of ``has_equivalence``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_equivalence`` while preserving the surrounding module contract.

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


def has_implication(text: str) -> bool:
    """Document the responsibility of ``has_implication``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_implication`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lowered = text.lower()
    return (
        "→" in text
        or "\\Rightarrow" in text
        or " implies " in lowered
        or " imply " in lowered
        or " if " in lowered
    )


def has_existential(text: str) -> bool:
    """Document the responsibility of ``has_existential``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_existential`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lowered = text.lower()
    return (
        "∃" in text
        or "\\exists" in text
        or " exists " in lowered
        or " there exists " in lowered
        or "nonempty" in lowered
        or "witness" in lowered
    )


def has_negation(text: str) -> bool:
    """Document the responsibility of ``has_negation``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_negation`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lowered = text.lower()
    return (
        "¬" in text or " not " in lowered or " no " in lowered or "does not" in lowered
    )


def add_finding(
    findings: List[Dict[str, Any]],
    *,
    severity: str,
    code: str,
    message: str,
    file_name: str,
    declaration: Dict[str, Any],
    evidence: Optional[Dict[str, Any]] = None,
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
    finding: Dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
        "file": file_name,
        "declaration": declaration.get("name"),
        "line": declaration.get("line"),
    }
    if evidence:
        finding["evidence"] = evidence
    findings.append(finding)


def dep_matches_name(dep: str, name: str) -> bool:
    """Document the responsibility of ``dep_matches_name``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``dep_matches_name`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return dep == name


def visible_hypothesis_dependency(dep: str, signature: str) -> bool:
    """Document the responsibility of ``visible_hypothesis_dependency``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``visible_hypothesis_dependency`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return bool(re.search(rf"\(\s*{re.escape(dep)}\b", signature)) or bool(
        re.search(rf"\{{\s*{re.escape(dep)}\b", signature)
    )


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
    return any(
        marker in text
        for marker in (
            "explicit assumption",
            "explicit hypothesis",
            "criterion",
            "model",
            "external",
            "interface",
            "component",
            "represented",
            "provided",
            "witness",
        )
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
    kind = declaration.get("kind", "")
    if kind not in {"theorem", "lemma", "axiom"}:
        return findings
    name = str(declaration.get("name", ""))
    signature = str(declaration.get("signature", ""))
    statement = statement_text(declaration)
    summary = str(declaration.get("proof_summary", ""))
    features = declaration.get("proof_features", {}) or {}
    tactics = set(features.get("tactics", []) or [])
    dependencies = [str(dep) for dep in features.get("probable_dependencies", []) or []]
    body_line_count = int(features.get("body_line_count", 0) or 0)
    placeholders = features.get("placeholder_tokens", []) or []
    delegated = bool(features.get("delegated_to_hypothesis"))

    if not declaration.get("informal_statement"):
        add_finding(
            findings,
            severity="high",
            code="missing_informal_statement",
            message="The informalized theorem packet has no statement.",
            file_name=file_name,
            declaration=declaration,
        )
    if not summary:
        add_finding(
            findings,
            severity="high",
            code="missing_proof_summary",
            message="The informalized theorem packet has no proof summary.",
            file_name=file_name,
            declaration=declaration,
        )
    if placeholders:
        add_finding(
            findings,
            severity="high",
            code="placeholder_in_informalized_proof",
            message="The proof packet contains unresolved proof-placeholder tokens.",
            file_name=file_name,
            declaration=declaration,
            evidence={"tokens": placeholders},
        )
    if kind == "axiom":
        add_finding(
            findings,
            severity="high",
            code="axiom_as_proof_packet",
            message="An axiom cannot serve as an internally consistent informalized proof.",
            file_name=file_name,
            declaration=declaration,
        )
    if kind in {"theorem", "lemma"} and body_line_count == 0:
        add_finding(
            findings,
            severity="high",
            code="missing_proof_body",
            message="The proof packet has no extracted proof body.",
            file_name=file_name,
            declaration=declaration,
        )
    circular = [dep for dep in dependencies if dep_matches_name(dep, name)]
    if circular:
        add_finding(
            findings,
            severity="high",
            code="circular_informalized_dependency",
            message="The informalized proof depends on the declaration being proved.",
            file_name=file_name,
            declaration=declaration,
            evidence={"dependencies": circular},
        )

    if has_equivalence(statement):
        bidirectional_evidence = bool({"constructor", "cases"} & tactics) or any(
            visible_hypothesis_dependency(dep, signature) or "iff" in dep.lower()
            for dep in dependencies
        )
        if not bidirectional_evidence:
            add_finding(
                findings,
                severity="medium",
                code="equivalence_without_bidirectional_evidence",
                message="The informalized statement is an equivalence, but the proof summary lacks clear two-direction evidence.",
                file_name=file_name,
                declaration=declaration,
                evidence={"tactics": sorted(tactics), "dependencies": dependencies},
            )

    if has_implication(statement):
        implication_evidence = bool(
            {"intro", "intros", "exact", "apply", "refine", "simpa"} & tactics
        ) or bool(dependencies)
        if not implication_evidence:
            add_finding(
                findings,
                severity="low",
                code="implication_without_intro_or_dependency_evidence",
                message="The informalized statement appears implicational, but the proof summary lacks introduction or dependency evidence.",
                file_name=file_name,
                declaration=declaration,
                evidence={"tactics": sorted(tactics)},
            )

    if has_existential(statement):
        witness_evidence = (
            bool({"constructor", "refine", "exact"} & tactics)
            or bool(dependencies)
            or "witness" in summary.lower()
        )
        if not witness_evidence:
            add_finding(
                findings,
                severity="medium",
                code="existential_without_witness_evidence",
                message="The informalized statement appears existential, but the proof summary exposes no witness or dependency evidence.",
                file_name=file_name,
                declaration=declaration,
                evidence={"tactics": sorted(tactics), "proof_summary": summary},
            )

    if delegated:
        hidden_dependencies = [
            dep
            for dep in dependencies
            if dep.startswith("h") and not visible_hypothesis_dependency(dep, signature)
        ]
        if hidden_dependencies and not has_boundary_marker(declaration):
            add_finding(
                findings,
                severity="medium",
                code="hidden_hypothesis_delegation",
                message="The proof delegates to a hypothesis that is not visibly documented as a proof boundary.",
                file_name=file_name,
                declaration=declaration,
                evidence={"dependencies": hidden_dependencies},
            )

    if "trivial proof search" in summary.lower():
        statement_words = words(statement)
        if "true" not in statement_words and "truth" not in statement_words:
            add_finding(
                findings,
                severity="medium",
                code="trivial_summary_for_nontrivial_statement",
                message="The proof summary says the theorem is trivial, but the statement is not obviously a truth proposition.",
                file_name=file_name,
                declaration=declaration,
                evidence={
                    "informal_statement": declaration.get("informal_statement", "")
                },
            )

    if "not classified" in summary.lower() and body_line_count > 0:
        add_finding(
            findings,
            severity="medium",
            code="generic_unclassified_proof_summary",
            message="The proof body exists, but the informalized proof summary gives no useful proof shape.",
            file_name=file_name,
            declaration=declaration,
            evidence={"body_line_count": body_line_count},
        )

    if statement and summary and not dependencies:
        overlap = token_overlap(statement, summary)
        if (
            overlap < 0.06
            and not has_boundary_marker(declaration)
            and not has_negation(statement)
        ):
            add_finding(
                findings,
                severity="low",
                code="low_statement_proof_summary_overlap",
                message="The informal statement and proof summary share very little vocabulary and no dependency handoff is visible.",
                file_name=file_name,
                declaration=declaration,
                evidence={"overlap": round(overlap, 4)},
            )

    return findings


def collect_findings(extractor_report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``collect_findings``.

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
    for file_packet in extractor_report.get("files", []):
        file_name = file_packet.get("file", "")
        for declaration in file_packet.get("declarations", []):
            findings.extend(declaration_findings(file_name, declaration))
    return findings


def build_report(extractor_report: Dict[str, Any]) -> Dict[str, Any]:
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
    findings = collect_findings(extractor_report)
    high = [item for item in findings if item.get("severity") == "high"]
    medium = [item for item in findings if item.get("severity") == "medium"]
    low = [item for item in findings if item.get("severity") == "low"]
    score = max(0, 100 - 35 * len(high) - min(30, 2 * len(medium)) - min(10, len(low)))
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
            "internal_consistency_score": score,
            "finding_count": len(findings),
            "blocking_finding_count": len(high),
            "medium_finding_count": len(medium),
            "low_finding_count": len(low),
        },
        "extractor_report": extractor_report,
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
            "Generated note (NL): Truth is equivalent to truth.",
            "Generated equivalent (LaTeX): `True \\iff True`.",
            "-/",
            "theorem good_iff : True ↔ True := by",
            "  constructor",
            "  · intro h",
            "    exact h",
            "  · intro h",
            "    exact h",
        ]
    )
    placeholder = "\n".join(
        [
            "/--",
            "Generated note (NL): Truth is derivable.",
            "Generated equivalent (LaTeX): `True`.",
            "-/",
            "theorem bad_placeholder : True := by",
            "  sorry",
        ]
    )
    circular = "\n".join(
        [
            "/--",
            "Generated note (NL): Truth is derivable.",
            "Generated equivalent (LaTeX): `True`.",
            "-/",
            "theorem circular_dep : True := by",
            "  exact circular_dep",
        ]
    )
    good_report = build_report(extractor_for_text(good, "good_fixture"))
    placeholder_report = build_report(
        extractor_for_text(placeholder, "placeholder_fixture")
    )
    circular_report = build_report(extractor_for_text(circular, "circular_fixture"))
    return {
        "generated_at_utc": utc_now(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": good_report["ok"]
        and not placeholder_report["ok"]
        and not circular_report["ok"],
        "summary": {
            "good_ok": good_report["ok"],
            "placeholder_blocked": not placeholder_report["ok"],
            "circular_blocked": not circular_report["ok"],
        },
        "self_test": {
            "good": good_report,
            "placeholder": placeholder_report,
            "circular": circular_report,
        },
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
    summary = report.get("summary", {})
    lines = [
        f"ok: {report['ok']}",
        f"files: {summary.get('file_count', 0)}",
        f"declarations: {summary.get('declaration_count', 0)}",
        f"theorem_like: {summary.get('theorem_like_count', 0)}",
        f"internal_consistency_score: {summary.get('internal_consistency_score', 'n/a')}",
        f"findings: {summary.get('finding_count', 0)}",
        f"blocking: {summary.get('blocking_finding_count', 0)}",
    ]
    for finding in report.get("findings", [])[:30]:
        lines.append(
            f"- {finding.get('severity')} {finding.get('file')}:{finding.get('line')} "
            f"{finding.get('code')} {finding.get('declaration')}: {finding.get('message')}"
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
    parser.add_argument("--informalization-report", type=Path)
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
        "lean_informal_internal_consistency_start",
        {"file_count": len(args.lean_file)},
    )
    if args.self_test:
        report = run_self_test()
    elif args.informalization_report:
        report_path = (REPO_ROOT / args.informalization_report).resolve()
        extractor_report = json.loads(report_path.read_text(encoding="utf-8"))
        report = build_report(extractor_report)
    elif args.text:
        report = build_report(extractor_for_text(args.text, args.name))
    else:
        paths = [
            (REPO_ROOT / path).resolve() if not path.is_absolute() else path
            for path in args.lean_file
        ]
        report = build_report(extractor_for_paths(paths))
    append_event(
        reasoning_log,
        "lean_informal_internal_consistency_complete",
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
