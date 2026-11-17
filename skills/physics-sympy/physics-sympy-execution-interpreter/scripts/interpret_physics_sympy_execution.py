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

"""Interpret raw execution diagnostics from SymPy physics artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Sequence

PATTERN_CLASSES = [
    (
        "dependency_import",
        "critical",
        r"ModuleNotFoundError|ImportError|No module named",
    ),
    ("parse", "error", r"SyntaxError|parse|LaTeX.*failed|could not parse"),
    ("symbol_assumption", "error", r"NameError|KeyError|assumption|domain"),
    ("unit_dimension", "error", r"dimension|unit|Dimensional|incompatible units"),
    (
        "transformation_residual",
        "error",
        r"residual|simplify.*False|symbolic.*fail|AssertionError",
    ),
    ("numeric_counterexample", "error", r"counterexample|numeric.*fail|sample.*fail"),
    (
        "projection_bridge",
        "error",
        r"projection|component|vector.*erased|field.*erased",
    ),
    ("law_grounding", "error", r"law.*missing|ungrounded law|physical law"),
    (
        "hidden_target",
        "critical",
        r"hidden target|target.*assumption|target.*input|copied target",
    ),
    ("empty_equation", "critical", r"vacuous|empty equation|no equations|placeholder"),
]


def load_text(path: Path | None, inline: str | None) -> str:
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
    if inline is not None:
        return inline
    if path is not None:
        return path.read_text(encoding="utf-8")
    return ""


def load_json_or_text(path: Path | None) -> tuple[dict[str, Any], str]:
    """Document the responsibility of ``load_json_or_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if path is None:
        return {}, ""
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text), text
    except json.JSONDecodeError:
        return {}, text


def status_from_findings(findings: list[dict[str, Any]]) -> str:
    """Document the responsibility of ``status_from_findings``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    severity_order = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    max_sev = max((severity_order[item["severity"]] for item in findings), default=0)
    return "fail" if max_sev >= 2 else "warn" if max_sev == 1 else "pass"


def build_report(text: str, execution_report: dict[str, Any]) -> dict[str, Any]:
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
    combined = text + "\n" + json.dumps(execution_report, ensure_ascii=False)
    findings: list[dict[str, Any]] = []
    for diagnostic_class, severity, pattern in PATTERN_CLASSES:
        match = re.search(pattern, combined, re.I)
        if match:
            findings.append(
                {
                    "severity": severity,
                    "diagnostic_class": diagnostic_class,
                    "message": f"Execution output matched {diagnostic_class} diagnostic.",
                    "evidence": combined[max(0, match.start() - 80) : match.end() + 80],
                    "repair_surface": {
                        "dependency_import": "dependency_import",
                        "parse": "equation_parse",
                        "symbol_assumption": "assumption_context",
                        "unit_dimension": "unit_dimension",
                        "transformation_residual": "transformation_step",
                        "numeric_counterexample": "numeric_domain",
                        "projection_bridge": "projection_bridge",
                        "law_grounding": "law_grounding",
                        "hidden_target": "target_nonleakage",
                        "empty_equation": "trace_realness",
                    }[diagnostic_class],
                }
            )
    explicit_status = str(execution_report.get("status", "")).lower()
    if explicit_status in {"fail", "failed", "error", "blocked"} and not findings:
        findings.append(
            {
                "severity": "error",
                "diagnostic_class": "execution_failed",
                "message": "Execution report status indicates failure but no finer class matched.",
                "repair_surface": "trace_realness",
            }
        )
    return {
        "style": "physics_sympy_execution_interpretation",
        "status": status_from_findings(findings),
        "diagnostics": findings,
        "raw_status": execution_report.get("status"),
        "repair_order": [item["repair_surface"] for item in findings],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
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
    parser.add_argument("--execution-report", type=Path)
    parser.add_argument("--stdout-file", type=Path)
    parser.add_argument("--stderr-file", type=Path)
    parser.add_argument("--text")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
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
        report = build_report("ModuleNotFoundError: No module named 'sympy'", {})
        assert report["status"] == "fail"
        assert report["diagnostics"][0]["diagnostic_class"] == "dependency_import"
    else:
        execution_report, report_text = load_json_or_text(args.execution_report)
        text = "\n".join(
            [
                report_text,
                load_text(args.stdout_file, None),
                load_text(args.stderr_file, None),
                load_text(None, args.text),
            ]
        )
        report = build_report(text, execution_report)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
