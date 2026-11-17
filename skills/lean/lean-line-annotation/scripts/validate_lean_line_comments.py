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

"""Validate readable, source-aware comments in generated Lean files."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import re
from typing import Any, Dict, List, Optional, Sequence

DEFAULT_MARKER = "NL/LaTeX:"
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
    r"Source anchors?|"
    r"Generated note|Generated equivalent|Formalization note|Mathlib grounding|"
    r"Interface note|Operational note|Draft note"
    r")\b",
    re.IGNORECASE,
)


def line_has_comment_marker(line: str, marker: str) -> bool:
    """Document the responsibility of ``line_has_comment_marker``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``line_has_comment_marker`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    marker_index = line.find(marker)
    if marker_index < 0:
        return False
    before_marker = line[:marker_index]
    return "--" in before_marker or "/-" in before_marker


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


def validate_text(
    text: str,
    *,
    marker: str = DEFAULT_MARKER,
    allow_fences: bool = False,
    allow_legacy_marker: bool = False,
    require_doc_comments: bool = False,
    require_semantic_comments: bool = False,
) -> Dict[str, Any]:
    """Document the responsibility of ``validate_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    failures: List[Dict[str, Any]] = []
    line_count = 0
    pending_doc_comment: Optional[str] = None
    in_doc_comment = False
    in_block_comment = False
    doc_comment_lines: List[str] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        line_count = line_no
        stripped = line.strip()
        if allow_fences and stripped == "%%%%%%%%%%":
            continue
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
        if marker in line and not allow_legacy_marker:
            failures.append(
                {
                    "line": line_no,
                    "code": line,
                    "reason": f"legacy per-line marker {marker!r} should be removed",
                }
            )
        if NOISE_COMMENT_RE.match(stripped):
            failures.append(
                {
                    "line": line_no,
                    "code": line,
                    "reason": "comment only explains syntactic file structure",
                }
            )
        if (
            is_syntactic_line(stripped)
            and "--" in line
            and not stripped.startswith("--")
        ):
            failures.append(
                {
                    "line": line_no,
                    "code": line,
                    "reason": "syntactic Lean line should not carry an explanatory trailing comment",
                }
            )
        if is_declaration_line(stripped):
            if require_doc_comments and pending_doc_comment is None:
                failures.append(
                    {
                        "line": line_no,
                        "code": line,
                        "reason": "declaration should have a preceding doc comment",
                    }
                )
            if require_semantic_comments:
                if pending_doc_comment is None:
                    failures.append(
                        {
                            "line": line_no,
                            "code": line,
                            "reason": (
                                "declaration should have a source-aware doc comment "
                                "with Natural language/LaTeX or generated-note alignment"
                            ),
                        }
                    )
                elif not has_semantic_annotation(pending_doc_comment):
                    failures.append(
                        {
                            "line": line_no,
                            "code": line,
                            "reason": (
                                "declaration doc comment should identify source alignment "
                                "or generated formalization notes"
                            ),
                        }
                    )
            pending_doc_comment = None
        elif not stripped.startswith("--") and not stripped.startswith("@["):
            pending_doc_comment = None
    return {
        "ok": not failures,
        "line_count": line_count,
        "legacy_marker": marker,
        "failure_count": len(failures),
        "failures": failures,
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
            "import Mathlib",
            "",
            "/--",
            "Original source (NL): Truth is derivable.",
            "Original source (LaTeX): `\\mathrm{True}`.",
            "-/",
            "theorem generated_example : True := by",
            "  trivial",
        ]
    )
    bad = "\n".join(
        [
            "import Mathlib -- NL/LaTeX: annotated import",
            "-- NL/LaTeX: separates imports from declarations",
            "end Generated -- NL/LaTeX: close generated namespace",
        ]
    )
    missing_semantic = "\n".join(
        [
            "/-- Truth is derivable. -/",
            "theorem generated_example : True := by",
            "  trivial",
        ]
    )
    good_report = validate_text(good, require_semantic_comments=True)
    bad_report = validate_text(bad)
    missing_semantic_report = validate_text(
        missing_semantic, require_semantic_comments=True
    )
    return {
        "ok": (
            good_report["ok"]
            and not bad_report["ok"]
            and bad_report["failure_count"] >= 3
            and not missing_semantic_report["ok"]
        ),
        "good": good_report,
        "bad": bad_report,
        "missing_semantic": missing_semantic_report,
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
        f"lines: {report.get('line_count', 0)}",
        f"legacy_marker: {report.get('legacy_marker', DEFAULT_MARKER)}",
        f"failures: {report.get('failure_count', 0)}",
    ]
    for item in report.get("failures", [])[:20]:
        lines.append(f"- line {item['line']}: {item['reason']}: {item['code']}")
    if len(report.get("failures", [])) > 20:
        lines.append(f"... {len(report['failures']) - 20} more failures")
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
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--marker", default=DEFAULT_MARKER)
    parser.add_argument("--allow-fences", action="store_true")
    parser.add_argument("--allow-legacy-marker", action="store_true")
    parser.add_argument("--require-doc-comments", action="store_true")
    parser.add_argument("--require-semantic-comments", action="store_true")
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
        report = run_self_test()
    else:
        if not args.files:
            raise SystemExit("provide at least one Lean file or use --self-test")
        reports = []
        for path in args.files:
            text = path.read_text(encoding="utf-8")
            item = validate_text(
                text,
                marker=args.marker,
                allow_fences=args.allow_fences,
                allow_legacy_marker=args.allow_legacy_marker,
                require_doc_comments=args.require_doc_comments,
                require_semantic_comments=args.require_semantic_comments,
            )
            item["file"] = str(path)
            reports.append(item)
        report = {
            "ok": all(item["ok"] for item in reports),
            "files": reports,
            "failure_count": sum(item["failure_count"] for item in reports),
        }
    if args.json:
        import json

        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if "files" in report:
            print(f"ok: {report['ok']}")
            print(f"files: {len(report['files'])}")
            print(f"failures: {report['failure_count']}")
            for item in report["files"]:
                if not item["ok"]:
                    print(f"\n{item['file']}")
                    print(render_text(item))
        else:
            print(f"ok: {report['ok']}")
            print("self_test: true")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
