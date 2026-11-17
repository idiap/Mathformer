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

"""Post-hoc comparison against withheld FormalPhysics formal answers.

The withheld answer is treated as inspiration, not as a benchmark label or an
oracle. This script is intentionally safe for post-hoc reflection: it records
whether a local Mathformer candidate is available, but it can still produce a
dataset-only inspiration report when the candidate is not present yet.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Sequence

STYLE = "physics_formal_answer_comparison_reflection"
POLICY = "inspiration_only_not_benchmark"
REAL = "\u211d"
LINEAR_ARROW = "\u2192\u2097"


def case_id_from_index(index: int) -> str:
    """Document the responsibility of ``case_id_from_index``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``case_id_from_index`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return f"formalphysics_{index:04d}"


def index_from_case_id(case_id: str) -> int:
    """Document the responsibility of ``index_from_case_id``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``index_from_case_id`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    match = re.fullmatch(r"formalphysics_(\d{4})", case_id)
    if not match:
        raise ValueError(f"unsupported FormalPhysics case id: {case_id}")
    return int(match.group(1))


def load_records(dataset: Path) -> list[dict[str, Any]]:
    """Document the responsibility of ``load_records``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    records = json.loads(dataset.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"expected {dataset} to contain a JSON list")
    return records


def analyze_lean(code: str) -> dict[str, Any]:
    """Document the responsibility of ``analyze_lean``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``analyze_lean`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    imports = re.findall(r"^import\s+(.+)$", code, flags=re.MULTILINE)
    theorem_names = re.findall(
        r"^\s*theorem\s+([A-Za-z0-9_'.]+)", code, flags=re.MULTILINE
    )
    axiom_names = re.findall(r"^\s*axiom\s+([A-Za-z0-9_'.]+)", code, flags=re.MULTILINE)
    comments = re.findall(r"/--.*?-/|--.*?$", code, flags=re.MULTILINE | re.DOTALL)
    source_like_comments = [
        comment
        for comment in comments
        if re.search(
            r"source|anchor|original|C\d+|physics|Lorentz|Ampere|Maxwell",
            comment,
            re.IGNORECASE,
        )
    ]
    raw_real_bound_identifiers = 0
    for binder in re.findall(
        r"\(([A-Za-z0-9_'\s]+)\s*:\s*" + re.escape(REAL) + r"\)", code
    ):
        raw_real_bound_identifiers += len(
            [part for part in binder.split() if part.strip()]
        )
    has_line_anchors = bool(
        re.search(
            r"source[-_ ]?(line|index|anchor)|Original source|NL/LaTeX",
            code,
            re.IGNORECASE,
        )
    )
    source_anchor_strength = (
        "line_anchored"
        if has_line_anchors
        else ("label_or_topic_comment" if source_like_comments else "missing")
    )
    return {
        "char_count": len(code),
        "line_count": len(code.splitlines()),
        "imports": imports,
        "broad_imports": [item for item in imports if item.strip() == "Mathlib"],
        "theorem_names": theorem_names,
        "theorem_count": len(theorem_names),
        "axiom_names": axiom_names,
        "has_sorry_or_admit": bool(re.search(r"\b(sorry|admit)\b", code)),
        "uses_linarith": "linarith" in code,
        "uses_ring": bool(re.search(r"\bring\b", code)),
        "uses_calc": bool(re.search(r"\bcalc\b", code)),
        "raw_real_surface_count": code.count(f": {REAL}")
        + len(re.findall(r"\bReal\b", code)),
        "raw_real_bound_identifier_count": raw_real_bound_identifiers,
        "function_field_surface": bool(
            re.search(r"\bX\s*\u2192\s*V\b|\(X\s*\u2192\s*V\)", code)
        ),
        "module_vector_surface": "[Module \u211d V]" in code
        or "[Module Real V]" in code,
        "linear_map_surface": LINEAR_ARROW in code or "LinearMap" in code,
        "quantity_or_dimension_surface": bool(
            re.search(r"Quantity|PhysDim|dimension|unit", code, re.IGNORECASE)
        ),
        "explicit_source_anchor_surface": bool(source_like_comments),
        "source_anchor_strength": source_anchor_strength,
        "source_like_comment_count": len(source_like_comments),
        "namespace_autoformal": "namespace AutoFormal" in code,
    }


def compile_lean(code: str, *, cwd: Path, timeout: int) -> dict[str, Any]:
    """Document the responsibility of ``compile_lean``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``compile_lean`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "WithheldFormalPhysics.lean"
        path.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(
                ["lake", "env", "lean", str(path)],
                cwd=cwd,
                text=True,
                capture_output=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "attempted": True,
                "status": "timeout",
                "returncode": None,
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "warning_count": 0,
            }
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    return {
        "attempted": True,
        "status": "pass" if proc.returncode == 0 else "fail",
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "warning_count": stdout.count("warning:") + stderr.count("warning:"),
    }


def discover_candidate(case_id: str, artifacts_dir: Path) -> Path | None:
    """Document the responsibility of ``discover_candidate``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``discover_candidate`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    case_dir = artifacts_dir / case_id
    if not case_dir.exists():
        return None
    candidates = sorted(case_dir.glob("*.lean"))
    return candidates[0] if candidates else None


def analyze_candidate(
    case_id: str,
    explicit: dict[str, Path],
    artifacts_dir: Path,
    *,
    execute_lean: bool,
    lean_cwd: Path,
    timeout: int,
) -> dict[str, Any]:
    """Document the responsibility of ``analyze_candidate``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``analyze_candidate`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    path = explicit.get(case_id) or discover_candidate(case_id, artifacts_dir)
    if path is None:
        available_packets = (
            sorted(item.name for item in (artifacts_dir / case_id).glob("*.json"))
            if (artifacts_dir / case_id).exists()
            else []
        )
        return {
            "available": False,
            "path": None,
            "available_packets": available_packets,
            "note": "No local Mathformer Lean candidate was found for this case.",
        }
    code = path.read_text(encoding="utf-8")
    return {
        "available": True,
        "path": str(path),
        "analysis": analyze_lean(code),
        "lean_compile": (
            compile_lean(code, cwd=lean_cwd, timeout=timeout)
            if execute_lean
            else {"attempted": False}
        ),
    }


def case_inspiration(
    case_id: str, formal_analysis: dict[str, Any], candidate: dict[str, Any]
) -> list[dict[str, str]]:
    """Document the responsibility of ``case_inspiration``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``case_inspiration`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    suggestions: list[dict[str, str]] = []
    if formal_analysis["uses_ring"] or formal_analysis["uses_linarith"]:
        suggestions.append(
            {
                "kind": "proof_tactic",
                "summary": "Dataset proof isolates algebraic rearrangement lemmas that Lean can solve with `ring`/`linarith`.",
                "monotonic_use": "Use as a local proof tactic after source-preserving theorem shape, units, and assumptions are fixed.",
            }
        )
    if candidate["available"]:
        candidate_analysis = candidate["analysis"]
        candidate_compile = candidate.get("lean_compile", {})
        if candidate_compile.get("status") == "pass":
            suggestions.append(
                {
                    "kind": "mathformer_candidate_compiles",
                    "summary": "The local Mathformer candidate also compiles, so comparison can focus on theorem shape and physics semantics rather than only executability.",
                    "monotonic_use": "Keep Lean execution as a necessary gate, then run source, unit, assumption, and final hypothesis reviewers.",
                }
            )
        if (
            candidate_analysis["quantity_or_dimension_surface"]
            and not formal_analysis["quantity_or_dimension_surface"]
        ):
            suggestions.append(
                {
                    "kind": "mathformer_candidate_stronger_physics_surface",
                    "summary": "The local candidate exposes quantity or dimension-tagged surfaces that the dataset formalization does not.",
                    "monotonic_use": "Preserve this stronger physics surface unless a reviewer finds a source-backed reason to simplify it.",
                }
            )
        if (
            candidate_analysis["source_anchor_strength"] == "line_anchored"
            and formal_analysis["source_anchor_strength"] != "line_anchored"
        ):
            suggestions.append(
                {
                    "kind": "mathformer_candidate_stronger_anchors",
                    "summary": "The local candidate carries stronger source-index/source-anchor metadata than the dataset formalization.",
                    "monotonic_use": "Keep these anchors through import and proof refinements.",
                }
            )
    if formal_analysis["linear_map_surface"]:
        suggestions.append(
            {
                "kind": "abstraction",
                "summary": "Dataset proof models field operators such as curl and time derivative as linear maps.",
                "monotonic_use": "Adopt as a reusable operator layer only with explicit physics-law provenance and unit/dimension obligations.",
            }
        )
    if formal_analysis["broad_imports"]:
        suggestions.append(
            {
                "kind": "import_policy",
                "summary": "Dataset proof compiles with broad imports, but this should be refined by Mathformer's import minimizer.",
                "monotonic_use": "Use broad imports only as a draft bridge, then rerun import minimization.",
            }
        )
    if (
        formal_analysis["raw_real_surface_count"] > 5
        or formal_analysis["raw_real_bound_identifier_count"] >= 5
    ) and not formal_analysis["quantity_or_dimension_surface"]:
        suggestions.append(
            {
                "kind": "physics_semantics_gap",
                "summary": "Dataset proof is executable but largely erases units/dimensions into raw scalar algebra.",
                "monotonic_use": "Keep or add quantity wrappers, projection lemmas, and unit reports before accepting a stronger Mathformer result.",
            }
        )
    if (
        formal_analysis["function_field_surface"]
        and not formal_analysis["quantity_or_dimension_surface"]
    ):
        suggestions.append(
            {
                "kind": "field_surface_gap",
                "summary": "Dataset proof keeps fields as functions over a domain but does not attach physical dimensions or unit systems.",
                "monotonic_use": "Reuse the function-field surface while enriching codomains or assumptions with dimension/unit metadata.",
            }
        )
    if formal_analysis["source_anchor_strength"] != "line_anchored":
        suggestions.append(
            {
                "kind": "source_anchor_gap",
                "summary": "Dataset proof has limited source-anchor/comment surface beyond a topical or claim label.",
                "monotonic_use": "Preserve Mathformer's line-translation and anchor guards; do not remove anchors to match the dataset style.",
            }
        )
    if not candidate["available"]:
        suggestions.append(
            {
                "kind": "candidate_status",
                "summary": "No local Mathformer Lean candidate exists yet for direct formalization-to-formalization comparison.",
                "monotonic_use": "Use this report to seed reviewer expectations, then rerun after the candidate artifact exists.",
            }
        )
    return suggestions


def build_case_report(
    *,
    records: list[dict[str, Any]],
    case_id: str,
    dataset: Path,
    execute_lean: bool,
    lean_cwd: Path,
    timeout: int,
    explicit_candidates: dict[str, Path],
    artifacts_dir: Path,
) -> dict[str, Any]:
    """Document the responsibility of ``build_case_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    index = index_from_case_id(case_id)
    record = records[index]
    formal_answer = str(record.get("formal_answer") or "")
    formal_analysis = analyze_lean(formal_answer)
    compile_report = (
        compile_lean(formal_answer, cwd=lean_cwd, timeout=timeout)
        if execute_lean
        else {"attempted": False}
    )
    candidate = analyze_candidate(
        case_id,
        explicit_candidates,
        artifacts_dir,
        execute_lean=execute_lean,
        lean_cwd=lean_cwd,
        timeout=timeout,
    )
    comparison_status = (
        "candidate_comparison" if candidate["available"] else "dataset_only_inspiration"
    )
    return {
        "case_id": case_id,
        "source_index": index,
        "field": record.get("field"),
        "dataset_path": str(dataset),
        "policy": POLICY,
        "comparison_status": comparison_status,
        "source_summary": {
            "question_char_count": len(str(record.get("question", ""))),
            "answer_char_count": len(str(record.get("answer", ""))),
            "formal_answer_present": bool(formal_answer),
        },
        "withheld_dataset_formalization": {
            "analysis": formal_analysis,
            "lean_compile": compile_report,
            "role": "post_hoc_inspiration_not_ground_truth",
        },
        "mathformer_candidate": candidate,
        "reflection": {
            "can_be_better_than_dataset": True,
            "why_not_a_benchmark": [
                "The withheld code is one generated formalization, not a canonical physics semantics.",
                "A Mathformer artifact may be stronger if it preserves units, dimensions, frames, assumptions, and source anchors more explicitly.",
                "Compilation is necessary evidence but not sufficient physical adequacy.",
            ],
            "localized_refinement_opportunities": case_inspiration(
                case_id, formal_analysis, candidate
            ),
        },
    }


def parse_candidate_args(items: Sequence[str]) -> dict[str, Path]:
    """Document the responsibility of ``parse_candidate_args``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parsed: dict[str, Path] = {}
    for item in items:
        if "=" not in item:
            raise ValueError("--mathformer-artifact values must be CASE_ID=PATH")
        case_id, path = item.split("=", 1)
        parsed[case_id.strip()] = Path(path).expanduser()
    return parsed


def render_markdown(report: dict[str, Any]) -> str:
    """Document the responsibility of ``render_markdown``.

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
        "# FormalPhysics Post-Hoc Formal-Answer Reflection",
        "",
        f"- Policy: `{report['policy']}`",
        f"- Dataset: `{report['dataset']}`",
        f"- Created: `{report['created_at']}`",
        "",
        "This is not a benchmark score. The withheld formal answer is treated as executable inspiration and a source of possible localized refinements.",
        "",
    ]
    for case in report["cases"]:
        formal = case["withheld_dataset_formalization"]
        analysis = formal["analysis"]
        compile_report = formal["lean_compile"]
        lines.extend(
            [
                f"## {case['case_id']}",
                "",
                f"- Field: `{case['field']}`",
                f"- Comparison status: `{case['comparison_status']}`",
                f"- Dataset theorem names: {', '.join(analysis['theorem_names']) or '(none)'}",
                f"- Dataset imports: {', '.join(analysis['imports']) or '(none)'}",
                f"- Dataset Lean compile: `{compile_report.get('status', 'not_attempted')}` with {compile_report.get('warning_count', 0)} warnings",
                f"- Dataset source-anchor strength: `{analysis['source_anchor_strength']}`",
                f"- Dataset raw real bound identifiers: `{analysis['raw_real_bound_identifier_count']}`",
                f"- Mathformer candidate: `{case['mathformer_candidate'].get('path') or 'missing'}`",
                f"- Mathformer candidate Lean compile: `{case['mathformer_candidate'].get('lean_compile', {}).get('status', 'not_attempted')}`",
                "",
                "Refinement opportunities:",
            ]
        )
        for item in case["reflection"]["localized_refinement_opportunities"]:
            lines.append(
                f"- `{item['kind']}`: {item['summary']} {item['monotonic_use']}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


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
    records = load_records(args.dataset)
    explicit_candidates = parse_candidate_args(args.mathformer_artifact or [])
    cases = [
        build_case_report(
            records=records,
            case_id=case_id,
            dataset=args.dataset,
            execute_lean=args.execute_lean,
            lean_cwd=args.lean_cwd,
            timeout=args.timeout,
            explicit_candidates=explicit_candidates,
            artifacts_dir=args.artifacts_dir,
        )
        for case_id in args.case_id
    ]
    return {
        "style": STYLE,
        "policy": POLICY,
        "dataset": str(args.dataset),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cases": cases,
        "pipeline_reflection": {
            "status": "post_hoc_reflection",
            "recommended_hook": "reflection.physics_formal_answer_compare",
            "first_pass_guard": "Do not load formal_answer before informal-first drafting and review.",
            "refinement_route": "refine.physics_lean_review",
        },
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
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/benchmarks/formal_science/FormalPhysics.json"),
    )
    parser.add_argument("--case-id", action="append", required=True)
    parser.add_argument(
        "--artifacts-dir", type=Path, default=Path("artifacts/physics_lean")
    )
    parser.add_argument("--mathformer-artifact", action="append", default=[])
    parser.add_argument("--execute-lean", action="store_true")
    parser.add_argument("--lean-cwd", type=Path, default=Path("."))
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--self-test", action="store_true")
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
        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp) / "FormalPhysics.json"
            dataset.write_text(
                json.dumps(
                    [
                        {
                            "field": "Electromagnetism",
                            "question": "Show a=b.",
                            "answer": "By h.",
                            "formal_answer": "import Mathlib\nnamespace AutoFormal\ntheorem T (a b : \u211d) (h : a = b) : a = b := h\n",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            args.dataset = dataset
            args.case_id = ["formalphysics_0000"]
            args.execute_lean = False
            args.artifacts_dir = Path(tmp) / "artifacts"
            args.mathformer_artifact = []
            report = build_report(args)
            assert report["policy"] == POLICY
            assert report["cases"][0]["comparison_status"] == "dataset_only_inspiration"
            assert (
                report["cases"][0]["withheld_dataset_formalization"]["role"]
                == "post_hoc_inspiration_not_ground_truth"
            )
            print(json.dumps({"ok": True, "style": STYLE}, indent=2))
            return 0
    report = build_report(args)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    if args.output_md:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_markdown(report), encoding="utf-8")
    if not args.output_json and not args.output_md:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
