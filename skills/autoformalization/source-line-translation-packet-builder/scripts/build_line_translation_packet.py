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

"""Build line-level NL/LaTeX-to-Lean translation packets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
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
except Exception:  # pragma: no cover - optional when script is copied standalone
    append_reasoning_log_entry = None  # type: ignore[assignment]


SKILL_NAME = "source-line-translation-packet-builder"
HOOK_ID = "preformalization.line_translation_packet"
MATH_RE = re.compile(r"(\\[A-Za-z]+|[_^{}=<>≤≥∈∀∃]|\\begin\{|\\end\{|\$|→|⇒|↔)")
THEOREM_RE = re.compile(
    r"\b(theorem|lemma|proposition|corollary|definition|def\.|proof|remark|example|notation)\b",
    re.IGNORECASE,
)
DECL_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_']+")


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


def utc_now() -> str:
    """Document the responsibility of ``utc_now``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``utc_now`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return datetime.now(timezone.utc).isoformat()


def stable_source_id(title: str, text: str) -> str:
    """Document the responsibility of ``stable_source_id``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``stable_source_id`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    basis = f"{title}\n{text}".encode("utf-8")
    return "src_" + hashlib.sha256(basis).hexdigest()[:12]


def line_id(line_no: int) -> str:
    """Document the responsibility of ``line_id``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``line_id`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return f"src_L{line_no:04d}"


def hash_text(text: str) -> str:
    """Document the responsibility of ``hash_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``hash_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def classify_line(text: str) -> str:
    """Document the responsibility of ``classify_line``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``classify_line`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    stripped = text.strip()
    if not stripped:
        return "blank"
    if stripped.startswith("%"):
        return "comment"
    if (
        "\\begin{proof}" in stripped
        or "\\end{proof}" in stripped
        or re.search(r"\bProof\b", stripped)
    ):
        return "proof"
    if re.search(
        r"\\begin\{(?:theorem|lemma|proposition|corollary|definition|example|remark)\}",
        stripped,
    ):
        return "environment"
    if re.search(
        r"\\\[|\\\]|\\begin\{(?:equation|align|displaymath|multline)\}", stripped
    ):
        return "display_math"
    if MATH_RE.search(stripped):
        return "math"
    if THEOREM_RE.search(stripped):
        return "statement"
    return "text"


def source_lines_from_text(text: str) -> List[Dict[str, Any]]:
    """Document the responsibility of ``source_lines_from_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``source_lines_from_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return [
        {
            "id": line_id(index),
            "line": index,
            "text": raw,
            "kind": classify_line(raw),
            "literal_sha256_16": hash_text(raw),
        }
        for index, raw in enumerate(text.splitlines(), start=1)
    ]


def should_split_before(
    previous: Optional[Dict[str, Any]], current: Dict[str, Any]
) -> bool:
    """Document the responsibility of ``should_split_before``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``should_split_before`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if previous is None:
        return False
    if previous["kind"] == "blank":
        return True
    if current["kind"] in {"environment", "proof", "display_math"}:
        return True
    if THEOREM_RE.search(current["text"]) and previous["kind"] not in {
        "environment",
        "proof",
    }:
        return True
    return False


def grouped_line_spans(
    source_lines: Sequence[Dict[str, Any]],
) -> List[List[Dict[str, Any]]]:
    """Document the responsibility of ``grouped_line_spans``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``grouped_line_spans`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    groups: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    previous: Optional[Dict[str, Any]] = None
    for item in source_lines:
        if item["kind"] == "blank":
            if current:
                groups.append(current)
                current = []
            previous = item
            continue
        if current and should_split_before(previous, item):
            groups.append(current)
            current = []
        current.append(item)
        previous = item
    if current:
        groups.append(current)
    return groups


def infer_kind(text: str, kinds: Sequence[str]) -> str:
    """Document the responsibility of ``infer_kind``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``infer_kind`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lower = text.lower()
    if "proof" in lower or "begin{proof}" in lower:
        return "proof"
    if "definition" in lower or "begin{definition}" in lower:
        return "definition"
    if "lemma" in lower or "begin{lemma}" in lower:
        return "lemma"
    if "corollary" in lower or "begin{corollary}" in lower:
        return "corollary"
    if "example" in lower or "begin{example}" in lower:
        return "example"
    if "theorem" in lower or "proposition" in lower or "begin{theorem}" in lower:
        return "theorem"
    if "display_math" in kinds or "math" in kinds:
        return "formula"
    return "context"


def target_surface(kind: str) -> str:
    """Document the responsibility of ``target_surface``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``target_surface`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {
        "definition": "def_or_structure",
        "lemma": "lemma",
        "corollary": "theorem",
        "theorem": "theorem",
        "proof": "proof_block_or_by_term",
        "formula": "def_or_theorem",
        "example": "example",
    }.get(kind, "comment_or_support")


def candidate_name(text: str, kind: str, index: int) -> str:
    """Document the responsibility of ``candidate_name``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``candidate_name`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    words = [
        word.lower()
        for word in DECL_NAME_RE.findall(re.sub(r"\\[A-Za-z]+", " ", text))
        if len(word) > 2
        and word.lower() not in {"the", "and", "for", "with", "that", "then", "proof"}
    ]
    stem = "_".join(words[:5]) or kind
    return re.sub(r"[^a-z0-9_]+", "_", f"{kind}_{stem}_{index:03d}").strip("_")


def latex_fragments(lines: Sequence[Dict[str, Any]]) -> List[str]:
    """Document the responsibility of ``latex_fragments``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``latex_fragments`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    fragments: List[str] = []
    for item in lines:
        text = item["text"].strip()
        if not text:
            continue
        fragments.extend(
            match.strip() for match in re.findall(r"`([^`]+)`", text) if match.strip()
        )
        fragments.extend(
            match.strip() for match in re.findall(r"\$([^$]+)\$", text) if match.strip()
        )
        if MATH_RE.search(text) and text not in fragments:
            fragments.append(text)
    seen: set[str] = set()
    unique: List[str] = []
    for fragment in fragments:
        if fragment not in seen:
            seen.add(fragment)
            unique.append(fragment)
    return unique[:6]


def anchor_range(ids: Sequence[str]) -> str:
    """Document the responsibility of ``anchor_range``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``anchor_range`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not ids:
        return ""
    if len(ids) == 1:
        return ids[0]
    return f"{ids[0]}-{ids[-1]}"


def build_units_from_lines(
    source_lines: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``build_units_from_lines``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    units: List[Dict[str, Any]] = []
    for index, group in enumerate(grouped_line_spans(source_lines), start=1):
        literal = "\n".join(item["text"] for item in group).strip()
        if not literal:
            continue
        ids = [item["id"] for item in group]
        kinds = [item["kind"] for item in group]
        kind = infer_kind(literal, kinds)
        formalizable = kind not in {"context"} or bool(MATH_RE.search(literal))
        units.append(
            {
                "id": f"lt_{index:03d}",
                "source_line_ids": ids,
                "source_anchor": anchor_range(ids),
                "literal_text": literal,
                "literal_sha256_16": hash_text(literal),
                "informal_kind": kind,
                "formalizable": formalizable,
                "latex_fragments": latex_fragments(group),
                "target_lean_surface": target_surface(kind),
                "candidate_declaration_name": candidate_name(literal, kind, index),
                "dependencies": [],
                "mathlib_concepts": [],
                "drafting_instruction": (
                    "Map this literal NL/LaTeX unit to the stated Lean surface. "
                    f"If formalized, include `Source anchors: {anchor_range(ids)}` "
                    "in the nearest module or declaration doc comment."
                ),
            }
        )
    return units


def units_from_inventory(payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    """Document the responsibility of ``units_from_inventory``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``units_from_inventory`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines: List[str] = []
    for unit in payload.get("units", []):
        span = str(unit.get("source_span") or unit.get("statement") or "").strip()
        if span:
            lines.extend(span.splitlines() or [span])
            lines.append("")
    return build_units_from_lines(source_lines_from_text("\n".join(lines))), "\n".join(
        lines
    )


def units_from_theory_units(
    payload: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], str]:
    """Document the responsibility of ``units_from_theory_units``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``units_from_theory_units`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    raw_units = (
        payload.get("units")
        or payload.get("theory_units")
        or payload.get("items")
        or []
    )
    lines: List[str] = []
    for unit in raw_units:
        parts = [
            unit.get("source_statement_latex"),
            unit.get("statement_latex"),
            unit.get("statement"),
            unit.get("source_span"),
            unit.get("paired_proof_latex"),
            unit.get("proof_latex"),
        ]
        text = "\n".join(str(part).strip() for part in parts if part)
        if text:
            lines.extend(text.splitlines())
            lines.append("")
    return build_units_from_lines(source_lines_from_text("\n".join(lines))), "\n".join(
        lines
    )


def render_prompt_context(units: Sequence[Dict[str, Any]], max_units: int = 24) -> str:
    """Document the responsibility of ``render_prompt_context``.

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
        "Line-by-line source translation packet. Preserve literal source anchors in Lean comments.",
        "For declarations generated from source material, add `Source anchors: ...` in the doc comment.",
        "Do not add per-line Lean comments.",
    ]
    for unit in units[:max_units]:
        if not unit.get("formalizable", True):
            continue
        lines.append(
            f"- {unit['id']} [{unit['source_anchor']}] "
            f"{unit['informal_kind']} -> {unit['target_lean_surface']} "
            f"candidate `{unit['candidate_declaration_name']}`: "
            f"{unit['literal_text'].replace(chr(10), ' ')}"
        )
        if unit.get("latex_fragments"):
            lines.append(f"  LaTeX: {' ; '.join(unit['latex_fragments'])}")
    return "\n".join(lines)


def build_packet(
    *,
    text: str,
    title: str,
    source_id: Optional[str],
    input_kind: str,
    units: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Document the responsibility of ``build_packet``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    source_lines = source_lines_from_text(text)
    translation_units = (
        units if units is not None else build_units_from_lines(source_lines)
    )
    formalizable_count = sum(
        1 for unit in translation_units if unit.get("formalizable", True)
    )
    packet = {
        "schema_version": 1,
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "created_at_utc": utc_now(),
        "ok": bool(translation_units),
        "source": {
            "title": title,
            "source_id": source_id or stable_source_id(title, text),
            "input_kind": input_kind,
            "line_count": len(source_lines),
        },
        "source_lines": source_lines,
        "translation_units": translation_units,
        "lean_prompt_context": render_prompt_context(translation_units),
        "summary": {
            "source_line_count": len(source_lines),
            "translation_unit_count": len(translation_units),
            "formalizable_unit_count": formalizable_count,
            "latex_fragment_count": sum(
                len(unit.get("latex_fragments", [])) for unit in translation_units
            ),
        },
    }
    return packet


def load_input(
    args: argparse.Namespace,
) -> Tuple[str, str, Optional[List[Dict[str, Any]]], str]:
    """Document the responsibility of ``load_input``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if args.text is not None:
        return args.text, "text", None, args.title or "Inline source"
    if args.source_file is not None:
        path = (
            (REPO_ROOT / args.source_file).resolve()
            if not args.source_file.is_absolute()
            else args.source_file
        )
        return (
            path.read_text(encoding="utf-8"),
            "source_file",
            None,
            args.title or path.name,
        )
    if args.unit_inventory is not None:
        path = (
            (REPO_ROOT / args.unit_inventory).resolve()
            if not args.unit_inventory.is_absolute()
            else args.unit_inventory
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        units, text = units_from_inventory(payload)
        title = args.title or payload.get("source", {}).get("title") or path.name
        return text, "unit_inventory", units, str(title)
    if args.theory_units is not None:
        path = (
            (REPO_ROOT / args.theory_units).resolve()
            if not args.theory_units.is_absolute()
            else args.theory_units
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        units, text = units_from_theory_units(payload)
        return text, "theory_units", units, args.title or path.name
    raise SystemExit(
        "provide --text, --source-file, --unit-inventory, or --theory-units"
    )


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
    text = (
        "\\begin{theorem}\\label{thm:true} If $n=0$, then $n=n$.\\end{theorem}\n"
        "\\begin{proof} By reflexivity.\\end{proof}\n"
    )
    packet = build_packet(
        text=text, title="Toy theorem", source_id="toy", input_kind="text"
    )
    checks = {
        "has_units": packet["summary"]["translation_unit_count"] >= 2,
        "has_anchor": packet["translation_units"][0]["source_anchor"].startswith(
            "src_L0001"
        ),
        "has_latex": bool(packet["translation_units"][0]["latex_fragments"]),
        "has_prompt_context": "Source anchors:" in packet["lean_prompt_context"],
        "has_candidate": packet["translation_units"][0][
            "candidate_declaration_name"
        ].startswith("theorem_"),
    }
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "packet.json"
        out.write_text(json.dumps(packet, indent=2), encoding="utf-8")
        checks["writes_json"] = out.exists()
    return {"ok": all(checks.values()), "checks": checks, "summary": packet["summary"]}


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
    source.add_argument("--text")
    source.add_argument("--source-file", type=Path)
    source.add_argument("--unit-inventory", type=Path)
    source.add_argument("--theory-units", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--source-id")
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--reasoning-log-file", type=Path)
    parser.add_argument("--expect-nonempty", action="store_true")
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
    text, input_kind, units, title = load_input(args)
    append_event(
        args.reasoning_log_file,
        "source_line_translation_packet_start",
        {"input_kind": input_kind, "title": title},
    )
    packet = build_packet(
        text=text,
        title=title,
        source_id=args.source_id,
        input_kind=input_kind,
        units=units,
    )
    if args.output_file is not None:
        output = (
            (REPO_ROOT / args.output_file).resolve()
            if not args.output_file.is_absolute()
            else args.output_file
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        packet["output_file"] = rel(output)
    append_event(
        args.reasoning_log_file,
        "source_line_translation_packet_complete",
        packet["summary"],
    )
    if args.expect_nonempty and not packet["ok"]:
        append_event(
            args.reasoning_log_file,
            "source_line_translation_packet_error",
            {"reason": "empty packet"},
        )
        print(json.dumps(packet, ensure_ascii=False, indent=2))
        return 3
    print(
        json.dumps(packet, ensure_ascii=False, indent=2)
        if args.json
        else packet["lean_prompt_context"]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
