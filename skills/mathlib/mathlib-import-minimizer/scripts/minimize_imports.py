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

"""Audit and conservatively minimize Lean import blocks."""

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


SKILL_NAME = "mathlib-import-minimizer"
HOOK_ID = "mathlib.import.minimize"
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


def normalize_imports(value: str) -> List[str]:
    """Document the responsibility of ``normalize_imports``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_imports`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = value.strip()
    if text.startswith("import "):
        text = text[len("import ") :].strip()
    return [part.strip().strip(",") for part in text.split() if part.strip()]


def split_imports_and_body(text: str) -> Tuple[List[str], List[str]]:
    """Document the responsibility of ``split_imports_and_body``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``split_imports_and_body`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    imports: List[str] = []
    body: List[str] = []
    for raw in text.splitlines():
        match = IMPORT_RE.match(raw)
        if match:
            imports.extend(normalize_imports(match.group(1)))
        else:
            body.append(raw)
    return imports, body


def ordered_unique(imports: Sequence[str]) -> Tuple[List[str], List[str]]:
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
    for item in imports:
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


def render(imports: Sequence[str], body: Sequence[str]) -> str:
    """Document the responsibility of ``render``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = [f"import {item}" for item in imports]
    body_text = "\n".join(body).strip()
    if body_text:
        lines.append(body_text)
    return "\n".join(lines) + "\n"


def lean_check(
    imports: Sequence[str], body: Sequence[str], *, timeout_sec: int
) -> Dict[str, Any]:
    """Document the responsibility of ``lean_check``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    with tempfile.TemporaryDirectory(prefix="mathformer-import-minimize-") as tmp:
        path = Path(tmp) / "ImportMinimizeCheck.lean"
        path.write_text(render(imports, body), encoding="utf-8")
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


def greedy_minimize(
    imports: Sequence[str],
    body: Sequence[str],
    *,
    timeout_sec: int,
) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
    """Document the responsibility of ``greedy_minimize``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``greedy_minimize`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    current = list(imports)
    removed: List[str] = []
    checks: List[Dict[str, Any]] = []
    baseline = lean_check(current, body, timeout_sec=timeout_sec)
    baseline["kind"] = "baseline"
    checks.append(baseline)
    if not baseline["ok"]:
        return current, removed, checks

    for item in list(current):
        trial = [candidate for candidate in current if candidate != item]
        check = lean_check(trial, body, timeout_sec=timeout_sec)
        check["kind"] = "remove_import_trial"
        check["import"] = item
        checks.append(check)
        if check["ok"]:
            current = trial
            removed.append(item)
    return current, removed, checks


def minimize(
    *,
    name: str,
    text: str,
    allow_broad_mathlib: bool,
    check_lean: bool,
    timeout_sec: int,
) -> Dict[str, Any]:
    """Document the responsibility of ``minimize``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``minimize`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    imports, body = split_imports_and_body(text)
    deduped, duplicates = ordered_unique(imports)
    findings: List[Dict[str, Any]] = []
    lean_checks: List[Dict[str, Any]] = []
    verified_removed: List[str] = []
    minimized = sorted(deduped, key=lambda item: (item == "Mathlib", item))

    for item in sorted(set(duplicates)):
        findings.append(
            make_finding(
                "medium",
                "duplicate_import",
                "Import appears more than once and should be deduplicated.",
                evidence=item,
            )
        )

    if "Mathlib" in deduped and not allow_broad_mathlib:
        findings.append(
            make_finding(
                "high",
                "broad_mathlib_import",
                "Broad `import Mathlib` remains in the import block.",
                evidence="Mathlib",
            )
        )

    if check_lean:
        minimized, verified_removed, lean_checks = greedy_minimize(
            minimized,
            body,
            timeout_sec=timeout_sec,
        )
        if lean_checks and not lean_checks[0]["ok"]:
            findings.append(
                make_finding(
                    "high",
                    "baseline_lean_check_failed",
                    "Original deduplicated file did not compile, so import minimization is not trustworthy.",
                    evidence=lean_checks[0]["stderr"] or lean_checks[0]["stdout"],
                )
            )
        for item in verified_removed:
            findings.append(
                make_finding(
                    "low",
                    "verified_removable_import",
                    "Import was removed after Lean still compiled.",
                    evidence=item,
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
            "original_import_count": len(imports),
            "deduped_import_count": len(deduped),
            "minimized_import_count": len(minimized),
            "verified_removed_count": len(verified_removed),
            "finding_count": len(findings),
            "blocking_finding_count": len(blocking),
            "lean_check_count": len(lean_checks),
        },
        "original_imports": imports,
        "deduped_imports": sorted(deduped, key=lambda item: (item == "Mathlib", item)),
        "minimized_imports": minimized,
        "verified_removed_imports": verified_removed,
        "suggested_import_block": "\n".join(f"import {item}" for item in minimized),
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
    parser.add_argument("--name", default="import_minimization")
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
    name = args.name
    text = ""
    if args.lean_file:
        text = args.lean_file.read_text(encoding="utf-8")
        name = str(args.lean_file)
    elif args.text is not None:
        text = args.text

    append_event(
        args.reasoning_log_file,
        "mathlib_import_minimization_start",
        {"name": name, "check_lean": args.check_lean},
    )
    report = minimize(
        name=name,
        text=text,
        allow_broad_mathlib=args.allow_broad_mathlib,
        check_lean=args.check_lean,
        timeout_sec=args.timeout_sec,
    )
    append_event(
        args.reasoning_log_file,
        "mathlib_import_minimization_complete",
        {
            "ok": report["ok"],
            "minimized_import_count": report["summary"]["minimized_import_count"],
            "blocking_finding_count": report["summary"]["blocking_finding_count"],
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
        print(f"imports: {report['summary']['minimized_import_count']}")
        for finding in report["findings"]:
            print(f"{finding['severity']} {finding['code']}: {finding['message']}")

    if args.expect_blocking:
        return 0 if not report["ok"] else 1
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
