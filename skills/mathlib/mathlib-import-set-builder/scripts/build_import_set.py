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

"""Build a narrow intended import set from mathlib evidence packets."""

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
except Exception:  # pragma: no cover - optional in standalone use
    append_reasoning_log_entry = None  # type: ignore[assignment]


SKILL_NAME = "mathlib-import-set-builder"
HOOK_ID = "mathlib.import.plan"
IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s*(?:--.*)?$")
MODULE_RE = re.compile(r"^(?:Mathlib|Mathformer)(?:\.[A-Za-z0-9_']+)*$")
IMPORT_KEYS = {
    "import",
    "imports",
    "module",
    "modules",
    "top_imports",
    "relevant_modules",
    "expected_imports",
    "gold_expected_imports",
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
    text = value.strip().strip("`").strip()
    if text.startswith("import "):
        text = text[len("import ") :].strip()
    parts = [part.strip().strip(",") for part in text.split()]
    return [part for part in parts if part]


def parse_imports_from_lean(text: str) -> List[str]:
    """Document the responsibility of ``parse_imports_from_lean``.

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
            for item in normalize_import(match.group(1)):
                imports.append(item)
    return imports


def walk_json_for_imports(value: Any) -> Iterable[str]:
    """Document the responsibility of ``walk_json_for_imports``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``walk_json_for_imports`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if isinstance(value, dict):
        for key, child in value.items():
            if key in IMPORT_KEYS:
                yield from walk_json_for_imports(child)
            else:
                yield from walk_json_for_imports(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json_for_imports(child)
    elif isinstance(value, str):
        for item in normalize_import(value):
            if item.startswith(("Mathlib", "Mathformer")):
                yield item


def ordered_unique(imports: Iterable[str]) -> Tuple[List[str], List[str]]:
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
    duplicates: List[str] = []
    result: List[str] = []
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


def build_report(
    *,
    expected_imports: Sequence[str],
    candidate_imports: Sequence[str],
    existing_imports: Sequence[str],
    allow_broad_mathlib: bool,
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
    all_inputs = [
        *expected_imports,
        *candidate_imports,
        *existing_imports,
    ]
    planned_imports, duplicates = ordered_unique(all_inputs)
    findings: List[Dict[str, Any]] = []

    invalid = [item for item in planned_imports if not MODULE_RE.match(item)]
    for item in invalid:
        findings.append(
            make_finding(
                "high",
                "invalid_import_name",
                "Import does not look like a supported Mathlib/Mathformer module.",
                evidence=item,
            )
        )

    for item in sorted(set(duplicates)):
        findings.append(
            make_finding(
                "low",
                "duplicate_import_input",
                "Import appeared more than once in the evidence packet.",
                evidence=item,
            )
        )

    if "Mathlib" in planned_imports and not allow_broad_mathlib:
        findings.append(
            make_finding(
                "high",
                "broad_mathlib_import",
                "Broad `import Mathlib` is not allowed for a planned final import set.",
                evidence="Mathlib",
            )
        )

    if not planned_imports:
        findings.append(
            make_finding(
                "medium",
                "empty_import_set",
                "No imports were found in the provided evidence.",
            )
        )

    sorted_imports = sorted(planned_imports, key=lambda item: (item == "Mathlib", item))
    high_findings = [item for item in findings if item["severity"] == "high"]
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": not high_findings,
        "summary": {
            "planned_import_count": len(sorted_imports),
            "finding_count": len(findings),
            "blocking_finding_count": len(high_findings),
        },
        "planned_imports": sorted_imports,
        "import_block": "\n".join(f"import {item}" for item in sorted_imports),
        "sources": {
            "expected_imports": list(expected_imports),
            "candidate_imports": list(candidate_imports),
            "existing_imports": list(existing_imports),
        },
        "findings": findings,
    }


def load_candidate_json(paths: Sequence[Path]) -> List[str]:
    """Document the responsibility of ``load_candidate_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    imports: List[str] = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        imports.extend(walk_json_for_imports(data))
    return imports


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
    parser.add_argument("--expected-import", action="append", default=[])
    parser.add_argument("--candidate-import", action="append", default=[])
    parser.add_argument("--candidate-json", type=Path, action="append", default=[])
    parser.add_argument("--lean-file", type=Path, action="append", default=[])
    parser.add_argument("--allow-broad-mathlib", action="store_true")
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
    expected_imports = [
        item for raw in args.expected_import for item in normalize_import(raw)
    ]
    candidate_imports = [
        item for raw in args.candidate_import for item in normalize_import(raw)
    ]
    candidate_imports.extend(load_candidate_json(args.candidate_json))
    existing_imports: List[str] = []
    for path in args.lean_file:
        existing_imports.extend(
            parse_imports_from_lean(path.read_text(encoding="utf-8"))
        )

    append_event(
        args.reasoning_log_file,
        "mathlib_import_plan_start",
        {
            "expected_import_count": len(expected_imports),
            "candidate_import_count": len(candidate_imports),
            "lean_file_count": len(args.lean_file),
        },
    )
    report = build_report(
        expected_imports=expected_imports,
        candidate_imports=candidate_imports,
        existing_imports=existing_imports,
        allow_broad_mathlib=args.allow_broad_mathlib,
    )
    append_event(
        args.reasoning_log_file,
        "mathlib_import_plan_complete",
        {
            "ok": report["ok"],
            "planned_import_count": report["summary"]["planned_import_count"],
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
        print(f"imports: {report['summary']['planned_import_count']}")
        for item in report["planned_imports"]:
            print(f"- {item}")
        for finding in report["findings"]:
            print(f"{finding['severity']} {finding['code']}: {finding['message']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
