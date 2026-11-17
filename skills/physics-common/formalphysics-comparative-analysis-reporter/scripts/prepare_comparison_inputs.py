#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Prepare FormalPhysics comparison inputs deterministically before expensive
#   Lean and generative judging.
#
# Intent:
#   Remove obsolete self-generated JSON fields, rediscover current repo
#   artifacts, and attach full Foundations dependency evidence.
#
# Function:
#   Emits cleaned records and a comparison manifest for report builders.
#
# Maintenance Notes:
#   Keep this script deterministic and side-effect limited to the output
#   directory.

"""Prepare FormalPhysics comparative-analysis inputs.

The script treats the informal reference answer as non-gold evidence and drops
obsolete `mathformerphysics_output` fields by default. Current Mathformer
outputs are rediscovered from the repository so the comparison does not reuse
stale JSON blobs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Sequence

STYLE = "formalphysics_comparative_analysis_inputs"
REFERENCE_ROLE = "non_gold_reference_evidence"
OBSOLETE_SELF_FIELD = "mathformerphysics_output"
EXTERNAL_FIELD = "formaldiscovery_output"


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[4]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def case_id(index: int) -> str:
    return f"formalphysics_{index:04d}"


DECLARATION_PATTERN = re.compile(
    r"^\s*(theorem|lemma|def|abbrev|structure|class|instance|axiom|opaque)\s+([A-Za-z0-9_'.]+)?",
    flags=re.MULTILINE,
)


def line_number_at(code: str, offset: int) -> int:
    return code.count("\n", 0, offset) + 1


def declaration_doc_start(lines: list[str], start_line: int) -> int:
    search_start = max(0, start_line - 12)
    cursor = start_line - 2
    if cursor < 0 or not lines[cursor].strip().endswith("-/"):
        return start_line
    for idx in range(cursor, search_start - 1, -1):
        stripped = lines[idx].strip()
        if stripped.startswith("/--") or stripped.startswith("/-!"):
            return idx + 1
    return start_line


def declaration_records(
    code: str, *, include_excerpts: bool = False, max_excerpt_lines: int = 36
) -> list[dict[str, Any]]:
    lines = code.splitlines()
    matches = list(DECLARATION_PATTERN.finditer(code))
    records: list[dict[str, Any]] = []
    for position, match in enumerate(matches):
        start_line = line_number_at(code, match.start())
        next_start_line = (
            line_number_at(code, matches[position + 1].start())
            if position + 1 < len(matches)
            else len(lines) + 1
        )
        line_end = max(
            start_line, min(next_start_line - 1, start_line + max_excerpt_lines - 1)
        )
        record: dict[str, Any] = {
            "kind": match.group(1),
            "name": match.group(2) or "",
            "line_start": start_line,
            "line_end": line_end,
        }
        if include_excerpts:
            excerpt_start = declaration_doc_start(lines, start_line)
            excerpt_end = max(line_end, excerpt_start)
            record["excerpt_line_start"] = excerpt_start
            record["excerpt_line_end"] = excerpt_end
            record["excerpt"] = "\n".join(lines[excerpt_start - 1 : excerpt_end])
        records.append(record)
    return records


def analyze_lean_text(
    code: str, *, include_declaration_excerpts: bool = False
) -> dict[str, Any]:
    imports = re.findall(r"^\s*import\s+(.+)$", code, flags=re.MULTILINE)
    declarations = declaration_records(
        code, include_excerpts=include_declaration_excerpts
    )
    return {
        "char_count": len(code),
        "line_count": len(code.splitlines()),
        "sha256": sha256_text(code),
        "imports": imports,
        "imports_foundations": [
            item
            for item in imports
            if "MathformerPhysicsLib.Lean.Foundations" in item
            or item.strip().startswith("MathformerPhysicsLib.Lean.Foundations")
        ],
        "broad_import_mathlib": any(item.strip() == "Mathlib" for item in imports),
        "declaration_counts": {
            kind: sum(1 for item in declarations if item["kind"] == kind)
            for kind in [
                "theorem",
                "lemma",
                "def",
                "abbrev",
                "structure",
                "class",
                "instance",
                "axiom",
                "opaque",
            ]
        },
        "declarations": (
            declarations[:120] if include_declaration_excerpts else declarations[:80]
        ),
        "has_sorry": bool(re.search(r"\bsorry\b", code)),
        "has_admit": bool(re.search(r"\badmit\b", code)),
        "has_axiom": any(item["kind"] == "axiom" for item in declarations),
        "source_anchor_surface": bool(
            re.search(
                r"source|anchor|original|informal|derivation", code, re.IGNORECASE
            )
        ),
        "unit_dimension_surface": bool(
            re.search(
                r"Unit|Dimension|Quantity|PhysDim|dimension|unit", code, re.IGNORECASE
            )
        ),
        "physics_context_surface": bool(
            re.search(
                r"PhysicsContext|Electromagnetism|Hilbert|Operator|Field|Vector", code
            )
        ),
    }


def read_text_if_exists(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def foundations_files(repo_root: Path) -> list[Path]:
    root_file = repo_root / "MathformerPhysicsLib" / "Lean" / "Foundations.lean"
    module_dir = repo_root / "MathformerPhysicsLib" / "Lean" / "Foundations"
    paths = []
    if root_file.exists():
        paths.append(root_file)
    if module_dir.exists():
        paths.extend(sorted(module_dir.glob("*.lean")))
    return paths


def build_foundations_inventory(repo_root: Path) -> dict[str, Any]:
    files = []
    totals = {
        "files": 0,
        "lines": 0,
        "theorems": 0,
        "lemmas": 0,
        "defs": 0,
        "structures": 0,
        "classes": 0,
        "axioms": 0,
        "sorries": 0,
        "admits": 0,
    }
    for path in foundations_files(repo_root):
        code = path.read_text(encoding="utf-8")
        analysis = analyze_lean_text(code, include_declaration_excerpts=True)
        counts = analysis["declaration_counts"]
        totals["files"] += 1
        totals["lines"] += analysis["line_count"]
        totals["theorems"] += counts.get("theorem", 0)
        totals["lemmas"] += counts.get("lemma", 0)
        totals["defs"] += counts.get("def", 0) + counts.get("abbrev", 0)
        totals["structures"] += counts.get("structure", 0)
        totals["classes"] += counts.get("class", 0)
        totals["axioms"] += counts.get("axiom", 0)
        totals["sorries"] += int(analysis["has_sorry"])
        totals["admits"] += int(analysis["has_admit"])
        files.append(
            {
                "path": str(path.relative_to(repo_root)),
                "analysis": analysis,
            }
        )
    return {
        "scope": "all_mathformerphysicslib_foundations_files",
        "files": files,
        "totals": totals,
    }


@dataclass(frozen=True)
class CandidatePath:
    id: str
    kind: str
    path: Path


def current_candidate_paths(repo_root: Path, index: int) -> list[CandidatePath]:
    cid = case_id(index)
    return [
        CandidatePath(
            id="current_mathformer_lean",
            kind="lean",
            path=repo_root
            / "MathformerPhysicsLib"
            / "Lean"
            / cid
            / "MathformerPhysics.lean",
        ),
    ]


def build_repo_candidate_packet(repo_root: Path, index: int) -> list[dict[str, Any]]:
    candidates = []
    for item in current_candidate_paths(repo_root, index):
        text = read_text_if_exists(item.path)
        if text is None:
            candidates.append(
                {
                    "candidate_id": item.id,
                    "kind": item.kind,
                    "available": False,
                    "path": str(item.path.relative_to(repo_root)),
                }
            )
            continue
        candidates.append(
            {
                "candidate_id": item.id,
                "kind": item.kind,
                "available": True,
                "path": str(item.path.relative_to(repo_root)),
                "analysis": analyze_lean_text(text),
                "comparison_role": "current_repo_artifact",
            }
        )
    return candidates


def build_external_candidate_packet(record: dict[str, Any]) -> list[dict[str, Any]]:
    code = str(record.get(EXTERNAL_FIELD) or "")
    if not code.strip():
        return []
    return [
        {
            "candidate_id": "external_formaldiscovery",
            "kind": "lean",
            "available": True,
            "source_field": EXTERNAL_FIELD,
            "analysis": analyze_lean_text(code),
            "comparison_role": "external_system_output",
        }
    ]


def clean_record(
    record: dict[str, Any], *, keep_obsolete_self_output: bool
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    cleaned = dict(record)
    removed: list[dict[str, str]] = []
    if not keep_obsolete_self_output and OBSOLETE_SELF_FIELD in cleaned:
        text = str(cleaned.pop(OBSOLETE_SELF_FIELD) or "")
        removed.append(
            {
                "field": OBSOLETE_SELF_FIELD,
                "reason": "obsolete_self_generation_excluded_from_comparison_inputs",
                "sha256": sha256_text(text) if text else "",
            }
        )
    return cleaned, removed


def build_manifest(
    records: list[dict[str, Any]],
    *,
    input_json: Path,
    output_dir: Path,
    repo_root: Path,
    keep_obsolete_self_output: bool,
) -> dict[str, Any]:
    foundations = build_foundations_inventory(repo_root)
    cases = []
    cleaned_records = []
    for position, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"record {position} is not an object")
        index = int(record.get("FS_index", position))
        cleaned, removed = clean_record(
            record, keep_obsolete_self_output=keep_obsolete_self_output
        )
        cleaned_records.append(cleaned)
        cases.append(
            {
                "case_id": case_id(index),
                "fs_index": index,
                "question_char_count": len(str(record.get("question") or "")),
                "reference_answer_char_count": len(str(record.get("answer") or "")),
                "reference_answer_role": REFERENCE_ROLE,
                "removed_obsolete_fields": removed,
                "candidates": build_external_candidate_packet(record)
                + build_repo_candidate_packet(repo_root, index),
                "foundations_dependency_scope": {
                    "included": True,
                    "scope": foundations["scope"],
                    "file_count": foundations["totals"]["files"],
                    "note": "All MathformerPhysicsLib Lean Foundations files are part of the Mathformer candidate context.",
                },
            }
        )
    write_json(output_dir / "selected_examples.cleaned.json", cleaned_records)
    return {
        "style": STYLE,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_json": str(input_json),
        "output_dir": str(output_dir),
        "policy": {
            "reference_answer_role": REFERENCE_ROLE,
            "obsolete_self_output_field": OBSOLETE_SELF_FIELD,
            "obsolete_self_output_removed_by_default": not keep_obsolete_self_output,
            "best_solution_policy": "hard_gates_first_scores_second",
        },
        "cases": cases,
        "foundations_inventory": foundations,
        "next_artifacts": {
            "cleaned_json": str(output_dir / "selected_examples.cleaned.json"),
            "manifest_json": str(output_dir / "comparison_manifest.json"),
            "todos_md": str(output_dir / "comparison_todos.md"),
        },
    }


def render_todos(manifest: dict[str, Any]) -> str:
    case_count = len(manifest["cases"])
    foundation_count = manifest["foundations_inventory"]["totals"]["files"]
    return "\n".join(
        [
            "# FormalPhysics Comparative Analysis Run TODOs",
            "",
            f"- [ ] Judge {case_count} cases with deterministic Lean compile checks.",
            f"- [ ] Include all {foundation_count} Foundations files in dependency analysis.",
            "- [ ] Compare `external_formaldiscovery` against current repo Mathformer artifacts.",
            "- [ ] Keep `answer` as non-gold reference evidence.",
            "- [ ] Confirm cleaned JSON excludes obsolete `mathformerphysics_output`.",
            "- [ ] Run physicist, Lean TP, Foundations dependency, and adversarial reference Codex-exec judges.",
            "- [ ] Aggregate hard gates before scored metrics.",
            "- [ ] Render the self-contained HTML report with side-by-side Lean highlighting.",
            "",
        ]
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=False)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/formalphysics_comparative_analysis/latest"),
    )
    parser.add_argument("--repo-root", type=Path, default=repo_root_from_script())
    parser.add_argument("--keep-obsolete-self-output", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_json is None:
        raise ValueError("--input-json is required unless --self-test is used")
    records = read_json(args.input_json)
    if not isinstance(records, list):
        raise ValueError("input JSON must contain a list of records")
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(
        records,
        input_json=args.input_json,
        output_dir=output_dir,
        repo_root=args.repo_root,
        keep_obsolete_self_output=args.keep_obsolete_self_output,
    )
    write_json(output_dir / "comparison_manifest.json", manifest)
    (output_dir / "comparison_todos.md").write_text(
        render_todos(manifest), encoding="utf-8"
    )
    return manifest


def self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        dataset = tmp_path / "selected_examples.json"
        dataset.write_text(
            json.dumps(
                [
                    {
                        "FS_index": 0,
                        "question": "Show a simple physics identity.",
                        "answer": "Reference derivation, not gold.",
                        OBSOLETE_SELF_FIELD: "theorem obsolete : True := by trivial",
                        EXTERNAL_FIELD: "import Mathlib\n\ntheorem external_solution : True := by trivial\n",
                    }
                ]
            ),
            encoding="utf-8",
        )
        out = tmp_path / "out"
        args = argparse.Namespace(
            input_json=dataset,
            output_dir=out,
            repo_root=repo_root_from_script(),
            keep_obsolete_self_output=False,
            self_test=False,
        )
        manifest = run(args)
        cleaned = read_json(out / "selected_examples.cleaned.json")
        assert OBSOLETE_SELF_FIELD not in cleaned[0]
        assert manifest["cases"][0]["reference_answer_role"] == REFERENCE_ROLE
        assert manifest["cases"][0]["foundations_dependency_scope"]["included"] is True
        assert any(
            item["candidate_id"] == "external_formaldiscovery"
            for item in manifest["cases"][0]["candidates"]
        )
        return {"ok": True, "style": STYLE, "output_dir": str(out)}


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        print(json.dumps(self_test(), indent=2))
        return 0
    manifest = run(args)
    print(
        json.dumps(
            {
                "ok": True,
                "style": STYLE,
                "case_count": len(manifest["cases"]),
                "foundations_file_count": manifest["foundations_inventory"]["totals"][
                    "files"
                ],
                "output_dir": manifest["output_dir"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
