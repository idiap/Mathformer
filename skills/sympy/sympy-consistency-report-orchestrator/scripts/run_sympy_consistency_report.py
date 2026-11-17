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

"""Build a reference-free consistency report for a SymPy autoformalization."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


def read_json(path: Path | None) -> dict[str, Any]:
    """Document the responsibility of ``read_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def metric_bool(value: bool | None) -> float:
    """Document the responsibility of ``metric_bool``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``metric_bool`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return 1.0 if value else 0.0


def build_report(args: argparse.Namespace) -> dict[str, Any]:
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
    parse = read_json(args.parse_packet)
    assumptions = read_json(args.assumptions)
    grounding = read_json(args.grounding)
    execution = read_json(args.execution)
    identity = read_json(args.identity)
    counterexamples = read_json(args.counterexamples)
    trace = read_json(args.trace)
    draft = read_json(args.draft_report)
    claim = execution.get("claim", {})

    units = parse.get("units", [])
    source_backed = [unit for unit in units if unit.get("source_anchors")]
    covered = [
        unit
        for unit in units
        if unit.get("source_anchors") and unit.get("status") == "parsed"
    ]
    source_anchor_coverage = len(covered) / max(1, len(source_backed))
    metrics = {
        "parse_coverage": float(parse.get("parse_coverage", 0.0)),
        "assumption_fidelity": float(assumptions.get("assumption_fidelity", 0.0)),
        "api_grounding_density": float(grounding.get("coverage", 0.0)),
        "symbolic_equivalence": metric_bool(
            identity.get("passed") or execution.get("symbolic", {}).get("passed")
        ),
        "numeric_robustness": metric_bool(execution.get("numeric", {}).get("passed")),
        "counterexample_absence": metric_bool(counterexamples.get("passed")),
        "transformation_trace_executability": metric_bool(trace.get("passed")),
        "reverse_informal_consistency": (
            1.0
            if claim.get("statement_nl") and claim.get("statement_latex") and units
            else 0.0
        ),
        "source_anchor_coverage": source_anchor_coverage,
        "artifact_realness": (
            1.0
            if draft.get("placeholder_free") and not execution.get("placeholder_hits")
            else 0.0
        ),
    }
    aggregate = sum(metrics.values()) / max(1, len(metrics))
    validation_criteria = {
        "every_formalized_formula_parsed": metrics["parse_coverage"] == 1.0,
        "assumptions_source_backed_or_marked_generated": metrics["assumption_fidelity"]
        == 1.0,
        "api_grounding_available": metrics["api_grounding_density"] > 0.0,
        "symbolic_validation_passed": metrics["symbolic_equivalence"] == 1.0,
        "numeric_sampling_no_violations": metrics["numeric_robustness"] == 1.0,
        "no_counterexample_found": metrics["counterexample_absence"] == 1.0,
        "trace_steps_cited_and_executable": metrics[
            "transformation_trace_executability"
        ]
        == 1.0,
        "reverse_informalization_agrees_with_source_claim": metrics[
            "reverse_informal_consistency"
        ]
        == 1.0,
        "artifact_placeholder_free": metrics["artifact_realness"] == 1.0,
    }
    blockers = [name for name, ok in validation_criteria.items() if not ok]
    return {
        "backend": "sympy",
        "style": "sympy_equational_trace",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact": str(args.artifact) if args.artifact else None,
        "metrics": metrics,
        "aggregate_reference_free_score": aggregate,
        "validation_criteria": validation_criteria,
        "blockers": blockers,
        "status": "complete" if not blockers else "draft",
        "inputs": {
            "parse_packet": str(args.parse_packet),
            "assumptions": str(args.assumptions),
            "grounding": str(args.grounding),
            "execution": str(args.execution),
            "identity": str(args.identity),
            "counterexamples": str(args.counterexamples),
            "trace": str(args.trace),
        },
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    """Document the responsibility of ``write_markdown``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = [
        "# SymPy Reference-Free Consistency Report",
        "",
        f"- Artifact: `{report.get('artifact')}`",
        f"- Status: `{report['status']}`",
        f"- Aggregate score: `{report['aggregate_reference_free_score']:.3f}`",
        "",
        "## Metrics",
        "",
    ]
    for key, value in report["metrics"].items():
        lines.append(f"- `{key}`: `{value:.3f}`")
    lines.extend(["", "## Validation Criteria", ""])
    for key, value in report["validation_criteria"].items():
        lines.append(f"- `{key}`: `{value}`")
    if report["blockers"]:
        lines.extend(["", "## Blockers", ""])
        for blocker in report["blockers"]:
            lines.append(f"- `{blocker}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html(report: dict[str, Any], path: Path) -> None:
    """Document the responsibility of ``write_html``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    metric_rows = "\n".join(
        f"<tr><td><code>{key}</code></td><td>{value:.3f}</td><td><div class='bar'><span style='width:{value * 100:.1f}%'></span></div></td></tr>"
        for key, value in report["metrics"].items()
    )
    criteria = "\n".join(
        f"<li class='{'ok' if value else 'bad'}'><code>{key}</code>: {value}</li>"
        for key, value in report["validation_criteria"].items()
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SymPy Reference-Free Report</title>
  <script>
    window.MathJax = {{tex: {{inlineMath: [['$', '$'], ['\\\\(', '\\\\)']]}}}};
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.11.1/styles/github.min.css">
  <script defer src="https://cdn.jsdelivr.net/npm/highlight.js@11.11.1/lib/common.min.js"></script>
  <script defer>window.addEventListener('DOMContentLoaded', () => hljs.highlightAll());</script>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1f2937; }}
    main {{ max-width: 1100px; margin: 0 auto; }}
    h1 {{ font-size: 30px; margin-bottom: 4px; }}
    .summary {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 20px 0; }}
    .panel {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 14px; background: #fff; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 9px; text-align: left; }}
    .bar {{ height: 9px; background: #e5e7eb; border-radius: 999px; overflow: hidden; }}
    .bar span {{ display: block; height: 100%; background: #2563eb; }}
    .ok {{ color: #166534; }}
    .bad {{ color: #991b1b; }}
    code {{ font-size: 0.92em; }}
  </style>
</head>
<body>
<main>
  <h1>SymPy Reference-Free Consistency Report</h1>
  <p><code>{report.get('artifact')}</code></p>
  <section class="summary">
    <div class="panel"><strong>Status</strong><br><code>{report['status']}</code></div>
    <div class="panel"><strong>Aggregate</strong><br>{report['aggregate_reference_free_score']:.3f}</div>
    <div class="panel"><strong>Style</strong><br><code>{report['style']}</code></div>
  </section>
  <section class="panel">
    <h2>Metrics</h2>
    <table><thead><tr><th>Metric</th><th>Score</th><th>Visual</th></tr></thead><tbody>{metric_rows}</tbody></table>
  </section>
  <section class="panel">
    <h2>Validation Criteria</h2>
    <ul>{criteria}</ul>
  </section>
</main>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def main() -> int:
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--parse-packet", type=Path)
    parser.add_argument("--assumptions", type=Path)
    parser.add_argument("--grounding", type=Path)
    parser.add_argument("--draft-report", type=Path)
    parser.add_argument("--execution", type=Path)
    parser.add_argument("--identity", type=Path)
    parser.add_argument("--counterexamples", type=Path)
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--html", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        root = Path("artifacts/sympy/wiki_sum_first_odd_numbers")
        if not (root / "trace_verification.json").exists():
            subprocess.run([sys.executable, "tests/sympy/run_wiki_case.py"], check=True)
        args.artifact = Path(
            "backends/sympy/MathformerSympy/AutoformalizedSumFirstOddNumbers.py"
        )
        args.parse_packet = root / "parse_packet.json"
        args.assumptions = root / "assumptions.json"
        args.grounding = root / "api_grounding.json"
        args.draft_report = root / "draft_report.json"
        args.execution = root / "execution_report.json"
        args.identity = root / "symbolic_validation.json"
        args.counterexamples = root / "counterexample_report.json"
        args.trace = root / "trace_verification.json"
    missing = [
        name
        for name in [
            "parse_packet",
            "assumptions",
            "grounding",
            "draft_report",
            "execution",
            "identity",
            "counterexamples",
            "trace",
        ]
        if getattr(args, name) is None
    ]
    if missing:
        parser.error(
            f"missing required arguments: {', '.join('--' + item.replace('_', '-') for item in missing)}"
        )

    report = build_report(args)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    if args.markdown:
        write_markdown(report, args.markdown)
    if args.html:
        write_html(report, args.html)
    print(
        text
        if args.json
        else f"sympy consistency status={report['status']} score={report['aggregate_reference_free_score']:.3f}"
    )
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
