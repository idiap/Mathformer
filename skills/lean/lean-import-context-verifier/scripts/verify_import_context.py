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

"""Verify generated Lean against intended import contexts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

try:
    from reasoning_log import append_reasoning_log_entry
except Exception:  # pragma: no cover - optional in standalone use
    append_reasoning_log_entry = None  # type: ignore[assignment]


SKILL_NAME = "lean-import-context-verifier"
HOOK_ID = "mathlib.import.context"
IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s*(?:--.*)?$")


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


def normalize_import(value: str) -> List[str]:
    """Document the responsibility of ``normalize_import``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_import`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = value.strip().strip("`")
    if text.startswith("import "):
        text = text[len("import ") :].strip()
    return [part.strip().strip(",") for part in text.split() if part.strip()]


def parse_imports(text: str) -> List[str]:
    """Document the responsibility of ``parse_imports``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    imports: List[str] = []
    for raw in text.splitlines():
        match = IMPORT_RE.match(raw)
        if match:
            imports.extend(normalize_import(match.group(1)))
    return imports


def strip_import_lines(text: str) -> str:
    """Document the responsibility of ``strip_import_lines``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``strip_import_lines`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return "\n".join(
        raw for raw in text.splitlines() if not IMPORT_RE.match(raw)
    ).strip()


def ordered_unique(values: Sequence[str]) -> Tuple[List[str], List[str]]:
    """Document the responsibility of ``ordered_unique``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``ordered_unique`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    seen: set[str] = set()
    result: List[str] = []
    duplicates: List[str] = []
    for item in values:
        if item in seen:
            duplicates.append(item)
            continue
        seen.add(item)
        result.append(item)
    return result, duplicates


def make_finding(
    severity: str,
    code: str,
    message: str,
    *,
    evidence: Optional[str] = None,
) -> Dict[str, Any]:
    """Document the responsibility of ``make_finding``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    finding: Dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if evidence is not None:
        finding["evidence"] = evidence
    return finding


def run_lean(text: str, *, timeout_sec: int) -> Dict[str, Any]:
    """Document the responsibility of ``run_lean``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    with tempfile.TemporaryDirectory(prefix="mathformer-import-context-") as tmp:
        path = Path(tmp) / "ImportContextCheck.lean"
        path.write_text(text + "\n", encoding="utf-8")
        proc = subprocess.run(
            ["lake", "env", "lean", str(path)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def build_check_text(
    imports: Sequence[str], body: str, declarations: Sequence[str]
) -> str:
    """Document the responsibility of ``build_check_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = [f"import {item}" for item in imports]
    if body.strip():
        lines.append(body.strip())
    for decl in declarations:
        lines.append(f"#check {decl}")
    return "\n".join(lines)


def verify(
    *,
    name: str,
    text: str,
    expected_imports: Sequence[str],
    expected_declarations: Sequence[str],
    allow_broad_mathlib: bool,
    check_lean: bool,
    timeout_sec: int,
) -> Dict[str, Any]:
    """Document the responsibility of ``verify``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    actual_imports, duplicate_imports = ordered_unique(parse_imports(text))
    expected_unique, expected_duplicates = ordered_unique(list(expected_imports))
    context_imports = expected_unique or actual_imports
    findings: List[Dict[str, Any]] = []
    lean_checks: List[Dict[str, Any]] = []

    if "Mathlib" in actual_imports and not allow_broad_mathlib:
        findings.append(
            make_finding(
                "high",
                "broad_mathlib_import",
                "Generated Lean uses broad `import Mathlib` without an import-policy waiver.",
                evidence="Mathlib",
            )
        )

    for item in duplicate_imports:
        findings.append(
            make_finding(
                "medium",
                "duplicate_import",
                "Generated Lean imports the same module more than once.",
                evidence=item,
            )
        )

    for item in expected_duplicates:
        findings.append(
            make_finding(
                "low",
                "duplicate_expected_import",
                "Expected import list contains a duplicate module.",
                evidence=item,
            )
        )

    missing = sorted(set(expected_unique) - set(actual_imports))
    for item in missing:
        findings.append(
            make_finding(
                "high",
                "missing_expected_import",
                "Generated Lean does not import an expected module.",
                evidence=item,
            )
        )

    if expected_declarations and not context_imports:
        findings.append(
            make_finding(
                "high",
                "missing_import_context",
                "Expected declarations were provided but no import context is available.",
            )
        )

    if expected_declarations and not check_lean:
        findings.append(
            make_finding(
                "low",
                "declaration_context_unchecked",
                "Expected declarations were named but `--check-lean` was not enabled.",
            )
        )

    if check_lean:
        body = strip_import_lines(text)
        if body:
            file_check = run_lean(
                build_check_text(context_imports, body, []),
                timeout_sec=timeout_sec,
            )
            file_check["kind"] = "file_under_context"
            lean_checks.append(file_check)
            if not file_check["ok"]:
                findings.append(
                    make_finding(
                        "high",
                        "lean_file_context_check_failed",
                        "Lean file/snippet failed under the intended import context.",
                        evidence=file_check["stderr"] or file_check["stdout"],
                    )
                )
        if expected_declarations:
            decl_check = run_lean(
                build_check_text(context_imports, "", expected_declarations),
                timeout_sec=timeout_sec,
            )
            decl_check["kind"] = "expected_declarations"
            decl_check["declarations"] = list(expected_declarations)
            lean_checks.append(decl_check)
            if not decl_check["ok"]:
                findings.append(
                    make_finding(
                        "high",
                        "expected_declaration_check_failed",
                        "At least one expected declaration failed under the intended imports.",
                        evidence=decl_check["stderr"] or decl_check["stdout"],
                    )
                )

    blocking = [item for item in findings if item["severity"] == "high"]
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "name": name,
        "ok": not blocking,
        "summary": {
            "actual_import_count": len(actual_imports),
            "expected_import_count": len(expected_unique),
            "expected_declaration_count": len(expected_declarations),
            "finding_count": len(findings),
            "blocking_finding_count": len(blocking),
            "lean_check_count": len(lean_checks),
        },
        "actual_imports": actual_imports,
        "expected_imports": expected_unique,
        "context_imports": context_imports,
        "expected_declarations": list(expected_declarations),
        "lean_checks": lean_checks,
        "findings": findings,
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
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--lean-file", type=Path)
    source.add_argument("--text")
    parser.add_argument("--name", default="import_context")
    parser.add_argument("--expected-import", action="append", default=[])
    parser.add_argument("--expected-declaration", action="append", default=[])
    parser.add_argument("--allow-broad-mathlib", action="store_true")
    parser.add_argument("--check-lean", action="store_true")
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--expect-blocking", action="store_true")
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--reasoning-log-file", type=Path)
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
    text = ""
    name = args.name
    if args.lean_file:
        text = args.lean_file.read_text(encoding="utf-8")
        name = str(args.lean_file)
    elif args.text is not None:
        text = args.text

    expected_imports = [
        item for raw in args.expected_import for item in normalize_import(raw)
    ]
    append_event(
        args.reasoning_log_file,
        "lean_import_context_verification_start",
        {
            "name": name,
            "expected_import_count": len(expected_imports),
            "expected_declaration_count": len(args.expected_declaration),
            "check_lean": args.check_lean,
        },
    )
    report = verify(
        name=name,
        text=text,
        expected_imports=expected_imports,
        expected_declarations=args.expected_declaration,
        allow_broad_mathlib=args.allow_broad_mathlib,
        check_lean=args.check_lean,
        timeout_sec=args.timeout_sec,
    )
    append_event(
        args.reasoning_log_file,
        "lean_import_context_verification_complete",
        {
            "ok": report["ok"],
            "blocking_finding_count": report["summary"]["blocking_finding_count"],
            "lean_check_count": report["summary"]["lean_check_count"],
        },
    )

    if args.output_file:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        args.output_file.write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"ok: {report['ok']}")
        print(f"actual_imports: {len(report['actual_imports'])}")
        print(f"expected_imports: {len(report['expected_imports'])}")
        for finding in report["findings"]:
            print(f"{finding['severity']} {finding['code']}: {finding['message']}")

    if args.expect_blocking:
        return 0 if not report["ok"] else 1
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
