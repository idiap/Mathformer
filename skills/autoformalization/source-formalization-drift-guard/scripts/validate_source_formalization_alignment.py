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

"""Validate source-anchor coverage in Lean formalizations."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
import tempfile
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


SKILL_NAME = "source-formalization-drift-guard"
HOOK_ID = "postformalization.source_anchor_drift_guard"
DECL_RE = re.compile(
    r"^\s*(?:private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
    r"(theorem|lemma|def|abbrev|class|structure|inductive|instance)\s+([^\s(:{]+)"
)
SOURCE_ANCHOR_RE = re.compile(
    r"Source anchors?:\s*([A-Za-z0-9_:\-.,\s]+)", re.IGNORECASE
)
SINGLE_ANCHOR_RE = re.compile(r"src_L\d{4}")
RANGE_RE = re.compile(r"(src_L(\d{4}))\s*-\s*(src_L(\d{4}))")
SOURCE_LIKE_RE = re.compile(
    r"Original source|Generated note|Generated equivalent|LaTeX|Natural language",
    re.IGNORECASE,
)


@dataclass
class LeanDeclaration:
    """Document the responsibility of ``LeanDeclaration``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Group related state and behavior so callers can use this part of the skills/autoformalization/source-formalization-drift-guard/scripts workflow through a clear object boundary.

    Function:
        Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    kind: str
    name: str
    line: int
    comment: str


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


def load_text(path: Path) -> str:
    """Document the responsibility of ``load_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    resolved = (REPO_ROOT / path).resolve() if not path.is_absolute() else path
    return resolved.read_text(encoding="utf-8")


def strip_comment_delimiters(lines: Sequence[str]) -> str:
    """Document the responsibility of ``strip_comment_delimiters``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``strip_comment_delimiters`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not lines:
        return ""
    values = list(lines)
    values[0] = re.sub(r"^\s*/-+!?\s?", "", values[0])
    values[-1] = re.sub(r"\s*-+/\s*$", "", values[-1])
    return "\n".join(line.rstrip() for line in values).strip()


def parse_declarations(text: str) -> List[LeanDeclaration]:
    """Document the responsibility of ``parse_declarations``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = text.splitlines()
    pending_comment = ""
    in_comment = False
    comment_lines: List[str] = []
    decls: List[LeanDeclaration] = []
    for line_no, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if in_comment:
            comment_lines.append(raw)
            if "-/" in raw:
                pending_comment = strip_comment_delimiters(comment_lines)
                comment_lines = []
                in_comment = False
            continue
        if stripped.startswith("/--") or stripped.startswith("/-!"):
            comment_lines = [raw]
            if "-/" in raw:
                pending_comment = strip_comment_delimiters(comment_lines)
                comment_lines = []
            else:
                in_comment = True
            continue
        if not stripped:
            continue
        match = DECL_RE.match(raw)
        if match is not None:
            kind, name = match.groups()
            decls.append(
                LeanDeclaration(
                    kind=kind, name=name, line=line_no, comment=pending_comment
                )
            )
            pending_comment = ""
        elif not stripped.startswith("--"):
            pending_comment = ""
    return decls


def expand_anchor_token(token: str) -> List[str]:
    """Document the responsibility of ``expand_anchor_token``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``expand_anchor_token`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    token = token.strip()
    match = RANGE_RE.fullmatch(token)
    if match is not None:
        start = int(match.group(2))
        end = int(match.group(4))
        if start <= end:
            return [f"src_L{index:04d}" for index in range(start, end + 1)]
    return SINGLE_ANCHOR_RE.findall(token)


def extract_anchors(comment: str) -> List[str]:
    """Document the responsibility of ``extract_anchors``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_anchors`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    anchors: List[str] = []
    for match in SOURCE_ANCHOR_RE.finditer(comment):
        payload = match.group(1)
        for raw_token in re.split(r"[,\s]+", payload):
            if raw_token.strip():
                anchors.extend(expand_anchor_token(raw_token))
    seen: Set[str] = set()
    unique: List[str] = []
    for anchor in anchors:
        if anchor not in seen:
            seen.add(anchor)
            unique.append(anchor)
    return unique


def packet_anchor_ids(packet: Dict[str, Any]) -> Set[str]:
    """Document the responsibility of ``packet_anchor_ids``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``packet_anchor_ids`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    ids = {
        str(item.get("id")) for item in packet.get("source_lines", []) if item.get("id")
    }
    if ids:
        return ids
    collected: Set[str] = set()
    for unit in packet.get("translation_units", []):
        collected.update(str(item) for item in unit.get("source_line_ids", []))
    return collected


def formalizable_anchor_ids(packet: Dict[str, Any]) -> Set[str]:
    """Document the responsibility of ``formalizable_anchor_ids``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``formalizable_anchor_ids`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    ids: Set[str] = set()
    for unit in packet.get("translation_units", []):
        if unit.get("formalizable", True):
            ids.update(str(item) for item in unit.get("source_line_ids", []))
    return ids


def validate_alignment(
    packet: Dict[str, Any],
    lean_text: str,
    *,
    min_anchor_coverage: float,
) -> Dict[str, Any]:
    """Document the responsibility of ``validate_alignment``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    available = packet_anchor_ids(packet)
    required = formalizable_anchor_ids(packet) or available
    decls = parse_declarations(lean_text)
    covered: Set[str] = set()
    orphan: Set[str] = set()
    declarations: List[Dict[str, Any]] = []
    source_like_without_anchor: List[Dict[str, Any]] = []
    for decl in decls:
        anchors = extract_anchors(decl.comment)
        covered.update(anchor for anchor in anchors if anchor in available)
        orphan.update(anchor for anchor in anchors if anchor not in available)
        if SOURCE_LIKE_RE.search(decl.comment) and not anchors:
            source_like_without_anchor.append(
                {"name": decl.name, "kind": decl.kind, "line": decl.line}
            )
        declarations.append(
            {
                "name": decl.name,
                "kind": decl.kind,
                "line": decl.line,
                "anchor_count": len(anchors),
                "anchors": anchors,
            }
        )
    coverage = (len(covered & required) / len(required)) if required else 1.0
    uncovered = sorted(required - covered)
    findings: List[Dict[str, Any]] = []
    if orphan:
        findings.append(
            {
                "severity": "high",
                "kind": "orphan_source_anchor",
                "message": "Lean comments cite source anchors not present in the packet.",
                "anchors": sorted(orphan),
            }
        )
    if coverage < min_anchor_coverage:
        findings.append(
            {
                "severity": "high",
                "kind": "low_anchor_coverage",
                "message": f"Anchor coverage {coverage:.3f} is below required {min_anchor_coverage:.3f}.",
                "uncovered_anchor_count": len(uncovered),
            }
        )
    if source_like_without_anchor:
        findings.append(
            {
                "severity": "medium",
                "kind": "source_comment_without_anchor",
                "message": "Some source-aware declaration comments lack Source anchors.",
                "declarations": source_like_without_anchor,
            }
        )
    ok = not any(item["severity"] == "high" for item in findings)
    return {
        "schema_version": 1,
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": ok,
        "summary": {
            "declaration_count": len(decls),
            "declarations_with_anchors": sum(
                1 for item in declarations if item["anchor_count"] > 0
            ),
            "available_anchor_count": len(available),
            "required_anchor_count": len(required),
            "covered_anchor_count": len(covered & required),
            "uncovered_anchor_count": len(uncovered),
            "orphan_anchor_count": len(orphan),
            "anchor_coverage": coverage,
            "min_anchor_coverage": min_anchor_coverage,
        },
        "declarations": declarations,
        "uncovered_anchors": uncovered,
        "orphan_anchors": sorted(orphan),
        "findings": findings,
    }


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
    packet = {
        "source_lines": [
            {"id": "src_L0001", "text": "Theorem."},
            {"id": "src_L0002", "text": "Proof."},
        ],
        "translation_units": [
            {"id": "lt_001", "source_line_ids": ["src_L0001"], "formalizable": True},
            {"id": "lt_002", "source_line_ids": ["src_L0002"], "formalizable": True},
        ],
    }
    lean = """
/--
Original source (NL): Theorem.
Source anchors: src_L0001-src_L0002
-/
theorem toy : True := by
  trivial
"""
    report = validate_alignment(packet, lean, min_anchor_coverage=1.0)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        packet_file = tmp_path / "packet.json"
        lean_file = tmp_path / "Toy.lean"
        packet_file.write_text(json.dumps(packet), encoding="utf-8")
        lean_file.write_text(lean, encoding="utf-8")
        rereport = validate_alignment(
            json.loads(packet_file.read_text()),
            lean_file.read_text(),
            min_anchor_coverage=1.0,
        )
    checks = {
        "ok": report["ok"],
        "full_coverage": report["summary"]["anchor_coverage"] == 1.0,
        "range_expanded": report["summary"]["covered_anchor_count"] == 2,
        "file_roundtrip": rereport["ok"],
    }
    return {"ok": all(checks.values()), "checks": checks, "summary": report["summary"]}


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
    parser.add_argument("--packet", type=Path)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--lean-file", type=Path)
    source.add_argument("--lean-text")
    parser.add_argument("--min-anchor-coverage", type=float, default=0.85)
    parser.add_argument("--reasoning-log-file", type=Path)
    parser.add_argument("--expect-ok", action="store_true")
    parser.add_argument("--self-test", action="store_true")
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
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 3
    if args.packet is None:
        raise SystemExit("--packet is required unless --self-test is used")
    packet_path = (
        (REPO_ROOT / args.packet).resolve()
        if not args.packet.is_absolute()
        else args.packet
    )
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    if args.lean_text is not None:
        lean_text = args.lean_text
        lean_source = "<text>"
    elif args.lean_file is not None:
        lean_path = (
            (REPO_ROOT / args.lean_file).resolve()
            if not args.lean_file.is_absolute()
            else args.lean_file
        )
        lean_text = lean_path.read_text(encoding="utf-8")
        lean_source = rel(lean_path)
    else:
        raise SystemExit(
            "--lean-file or --lean-text is required unless --self-test is used"
        )
    append_event(
        args.reasoning_log_file,
        "source_anchor_drift_guard_start",
        {"packet": rel(packet_path), "lean_source": lean_source},
    )
    report = validate_alignment(
        packet, lean_text, min_anchor_coverage=args.min_anchor_coverage
    )
    report["packet_file"] = rel(packet_path)
    report["lean_source"] = lean_source
    append_event(
        args.reasoning_log_file, "source_anchor_drift_guard_complete", report["summary"]
    )
    if args.expect_ok and not report["ok"]:
        append_event(
            args.reasoning_log_file,
            "source_anchor_drift_guard_error",
            {"reason": "alignment guard failed"},
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 3
    print(
        json.dumps(report, ensure_ascii=False, indent=2)
        if args.json
        else json.dumps(report["summary"], indent=2)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
