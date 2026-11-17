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

"""Organize extracted LaTeX theory units into thematic TeX bundles."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, List, Optional, Sequence, Tuple


def slugify(value: str, default: str = "bundle") -> str:
    """Document the responsibility of ``slugify``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``slugify`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return slug[:96] or default


def load_units(path: Path) -> Dict[str, Any]:
    """Document the responsibility of ``load_units``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if "units" not in data:
        raise ValueError(f"{path} does not contain a units array")
    return data


def group_key(unit: Dict[str, Any], group_by: str) -> Tuple[str, str]:
    """Document the responsibility of ``group_key``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``group_key`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    chapter = unit.get("chapter") or Path(unit.get("file", "source")).stem
    if group_by == "chapter":
        title = chapter
    else:
        section = unit.get("section") or unit.get("subsection") or "front-matter"
        title = f"{chapter} / {section}"
    return slugify(title), title


def chunk_units(
    units: Sequence[Dict[str, Any]], max_units: int
) -> List[List[Dict[str, Any]]]:
    """Document the responsibility of ``chunk_units``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``chunk_units`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if max_units <= 0 or len(units) <= max_units:
        return [list(units)]
    return [
        list(units[idx : idx + max_units]) for idx in range(0, len(units), max_units)
    ]


def render_bundle(
    title: str, units: Sequence[Dict[str, Any]], source_report: Optional[str]
) -> str:
    """Document the responsibility of ``render_bundle``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines: List[str] = [
        "% Auto-generated source-preserving theory bundle.",
        "% Generated by textbook-theory-tex-organizer.",
    ]
    if source_report:
        lines.append(f"% Extraction report: {source_report}")
    lines.extend(["", f"\\section*{{{title}}}", ""])
    for unit in units:
        proof_ids = ", ".join(unit.get("paired_proof_unit_ids", [])) or "none"
        labels = ", ".join(unit.get("labels", [])) or "none"
        lines.extend(
            [
                f"% Unit: {unit['id']}",
                f"% Kind: {unit.get('kind')} | Env: {unit.get('env')} | Labels: {labels}",
                f"% Source: {unit.get('file')}:{unit.get('line_start')}-{unit.get('line_end')}",
                f"% Paired proof units: {proof_ids}",
            ]
        )
        proof_for = unit.get("proof_for_unit_id")
        if proof_for:
            lines.append(f"% Proof for unit: {proof_for}")
        lines.extend([unit.get("latex", "").rstrip(), ""])
    return "\n".join(lines).rstrip() + "\n"


def organize(
    report: Dict[str, Any],
    output_dir: Path,
    *,
    group_by: str,
    max_units_per_file: int,
    source_report_path: Optional[Path],
) -> Dict[str, Any]:
    """Document the responsibility of ``organize``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``organize`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    tex_dir = output_dir / "tex"
    tex_dir.mkdir(parents=True, exist_ok=True)

    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for unit in sorted(
        report["units"], key=lambda item: item.get("source_order", 10**9)
    ):
        grouped[group_key(unit, group_by)].append(unit)

    bundles: List[Dict[str, Any]] = []
    ordered_groups = sorted(
        grouped.items(),
        key=lambda item: min(unit.get("source_order", 10**9) for unit in item[1]),
    )
    for (base_slug, title), units in ordered_groups:
        for chunk_idx, chunk in enumerate(
            chunk_units(units, max_units_per_file), start=1
        ):
            suffix = (
                f"-part-{chunk_idx:02d}" if len(units) > max_units_per_file > 0 else ""
            )
            bundle_id = f"{base_slug}{suffix}"
            tex_file = tex_dir / f"{bundle_id}.tex"
            tex_file.write_text(
                render_bundle(
                    title,
                    chunk,
                    str(source_report_path) if source_report_path else None,
                ),
                encoding="utf-8",
            )
            kind_counts = Counter(unit.get("kind") for unit in chunk)
            bundles.append(
                {
                    "bundle_id": bundle_id,
                    "title": title,
                    "tex_file": str(tex_file),
                    "unit_ids": [unit["id"] for unit in chunk],
                    "unit_count": len(chunk),
                    "kind_counts": dict(sorted(kind_counts.items())),
                }
            )

    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_report": str(source_report_path) if source_report_path else None,
        "output_dir": str(output_dir),
        "group_by": group_by,
        "max_units_per_file": max_units_per_file,
        "summary": {
            "bundle_count": len(bundles),
            "unit_count": sum(bundle["unit_count"] for bundle in bundles),
        },
        "bundles": bundles,
    }
    manifest_file = output_dir / "organized_manifest.json"
    manifest["manifest_file"] = str(manifest_file)
    manifest_file.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest


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
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        report = {
            "units": [
                {
                    "id": "u1",
                    "kind": "definition",
                    "env": "definition",
                    "labels": ["def:x"],
                    "file": "chapter.tex",
                    "line_start": 1,
                    "line_end": 3,
                    "chapter": "Foundations",
                    "section": "Metric facts",
                    "paired_proof_unit_ids": [],
                    "latex": "\\begin{definition}\\label{def:x}X.\\end{definition}",
                },
                {
                    "id": "u2",
                    "kind": "proof",
                    "env": "proof",
                    "labels": [],
                    "file": "chapter.tex",
                    "line_start": 4,
                    "line_end": 5,
                    "chapter": "Foundations",
                    "section": "Metric facts",
                    "paired_proof_unit_ids": [],
                    "proof_for_unit_id": "u1",
                    "latex": "\\begin{proof}Done.\\end{proof}",
                },
            ]
        }
        report_file = tmp_path / "theory_units.json"
        report_file.write_text(json.dumps(report), encoding="utf-8")
        manifest = organize(
            report,
            tmp_path / "out",
            group_by="section",
            max_units_per_file=10,
            source_report_path=report_file,
        )
        assert manifest["summary"]["bundle_count"] == 1, manifest
        tex_path = Path(manifest["bundles"][0]["tex_file"])
        assert "Unit: u1" in tex_path.read_text(encoding="utf-8")
        return {"ok": True, "summary": manifest["summary"]}


def parse_args() -> argparse.Namespace:
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
        "--theory-units-json",
        type=Path,
        help="Report emitted by latex-archive-theory-extractor",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=False,
        help="Directory for organized TeX bundles",
    )
    parser.add_argument("--group-by", choices=("section", "chapter"), default="section")
    parser.add_argument("--max-units-per-file", type=int, default=40)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


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
    args = parse_args()
    if args.self_test:
        print(json.dumps(run_self_test(), indent=2, sort_keys=True))
        return 0
    if args.theory_units_json is None:
        raise SystemExit("--theory-units-json is required unless --self-test is used")
    report_path = args.theory_units_json.resolve()
    report = load_units(report_path)
    output_dir = (args.output_dir or report_path.parent / "organized").resolve()
    manifest = organize(
        report,
        output_dir,
        group_by=args.group_by,
        max_units_per_file=args.max_units_per_file,
        source_report_path=report_path,
    )
    summary = {
        "ok": True,
        "manifest_file": manifest["manifest_file"],
        **manifest["summary"],
    }
    print(json.dumps(summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
