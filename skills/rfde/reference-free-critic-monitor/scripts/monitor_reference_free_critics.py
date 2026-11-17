#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

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

"""Monitor reference-free critic measures for Lean artifacts."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
GATE_POLICY_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "gate-policy-controller" / "scripts"
)
for script_dir in (REASONING_LOG_SCRIPTS, GATE_POLICY_SCRIPTS):
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

from gate_policy import decide_gate
from reasoning_log import (
    append_reasoning_log_entry,
)

SKILL_NAME = "reference-free-critic-monitor"
HOOK_ID = "critique.reference_free_monitor"

DECL_RE = re.compile(
    r"^\s*(?:@[A-Za-z0-9_'.`,\s\[\]=:-]+\s*)*"
    r"(?:private\s+|protected\s+|noncomputable\s+)*"
    r"(def|theorem|lemma|axiom|structure|class|instance|abbrev|inductive|coinductive)\s+"
    r"([A-Za-z0-9_'.`]+)?"
)
IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s*$")
THEOREM_KINDS = {"theorem", "lemma"}
PLACEHOLDER_PATTERNS: List[Tuple[str, str]] = [
    ("sorry", r"(?<![A-Za-z0-9_])sorry(?![A-Za-z0-9_])"),
    ("admit", r"(?<![A-Za-z0-9_])admit(?![A-Za-z0-9_])"),
    ("exact_query", r"(?<![A-Za-z0-9_])exact\?"),
    ("mock_marker", r"(?i)\b(mock|mocked|stub|fake|simulated)\b"),
    ("placeholder_marker", r"(?i)\bplaceholder\b"),
    ("todo_marker", r"\b(TODO|FIXME)\b"),
    ("scaffold_marker", r"(?i)\bscaffold\b"),
]
SEMANTIC_COMMENT_RE = re.compile(
    r"\b(?:"
    r"Original source|Source theorem|Source statement|Natural language|LaTeX|"
    r"Generated note|Generated equivalent|Formalization note|Mathlib grounding|"
    r"Interface note|Operational note|Draft note"
    r")\b",
    re.IGNORECASE,
)
ORIGINAL_SOURCE_RE = re.compile(r"\bOriginal source\b", re.IGNORECASE)
GENERATED_NOTE_RE = re.compile(r"\bGenerated note\b", re.IGNORECASE)
MATHLIB_NATIVE_TOKENS = (
    "Set",
    "Finset",
    "Nat",
    "Int",
    "Rat",
    "Real",
    "Metric",
    "MetricSpace",
    "TopologicalSpace",
    "Continuous",
    "UniformContinuous",
    "Convex",
    "Measure",
    "ProbabilityMeasure",
    "LinearMap",
    "AffineMap",
    "InnerProductSpace",
    "Normed",
    "Filter",
    "Tendsto",
    "IsClosed",
    "IsCompact",
)


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


def clamp_score(value: float) -> int:
    """Document the responsibility of ``clamp_score``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``clamp_score`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return int(round(max(0.0, min(100.0, value))))


def load_json(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    """Document the responsibility of ``load_json``.

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
        return None
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return parsed


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    """Document the responsibility of ``write_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
    if reasoning_log is None:
        return
    append_reasoning_log_entry(
        reasoning_log,
        step=step,
        payload={"skill": SKILL_NAME, "hook_id": HOOK_ID, **payload},
    )


def file_hash(text: str, *, length: int = 12) -> str:
    """Document the responsibility of ``file_hash``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``file_hash`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def strip_line_comment(line: str) -> str:
    """Document the responsibility of ``strip_line_comment``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``strip_line_comment`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return line.split("--", 1)[0] if "--" in line else line


def collect_declarations(lines: Sequence[str]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``collect_declarations``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``collect_declarations`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    declarations: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for line_no, raw in enumerate(lines, start=1):
        code = strip_line_comment(raw)
        match = DECL_RE.match(code)
        if match is not None and not raw.startswith((" ", "\t")):
            if current is not None:
                declarations.append(current)
            current = {
                "kind": match.group(1),
                "name": match.group(2),
                "line": line_no,
                "lines": [raw],
            }
            continue
        if current is not None:
            current["lines"].append(raw)
    if current is not None:
        declarations.append(current)
    return declarations


def declaration_signature(block_lines: Sequence[str]) -> str:
    """Document the responsibility of ``declaration_signature``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``declaration_signature`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    cleaned: List[str] = []
    for raw in block_lines:
        code = strip_line_comment(raw).strip()
        if not code:
            continue
        cleaned.append(code)
        joined = " ".join(cleaned)
        if ":=" in joined or " where" in joined:
            break
    return " ".join(cleaned)


def count_pattern(pattern: str | re.Pattern[str], text: str) -> int:
    """Document the responsibility of ``count_pattern``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``count_pattern`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if isinstance(pattern, str):
        return len(re.findall(pattern, text))
    return len(pattern.findall(text))


def analyze_lean_text(*, text: str, name: str) -> Dict[str, Any]:
    """Document the responsibility of ``analyze_lean_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``analyze_lean_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = text.splitlines()
    imports = [
        match.group(1).strip()
        for raw in lines
        for match in [IMPORT_RE.match(raw)]
        if match is not None
    ]
    declarations = collect_declarations(lines)
    kind_counts = Counter(str(item.get("kind")) for item in declarations)
    theorem_like = [
        item for item in declarations if str(item.get("kind")) in THEOREM_KINDS
    ]
    signatures = [declaration_signature(item["lines"]) for item in theorem_like]
    trivial_statement_count = sum(
        1 for signature in signatures if re.search(r":\s*(?:True|False)\b", signature)
    )
    false_assumption_count = sum(
        1
        for signature in signatures
        if re.search(r"\(\s*[A-Za-z0-9_']+\s*:\s*False\s*\)", signature)
    )
    trivial_proof_count = sum(
        1
        for item in theorem_like
        if re.search(
            r":=\s*by\s+(?:trivial|exact\s+trivial)\b", " ".join(item["lines"])
        )
    )
    placeholder_counts = {
        code: count_pattern(pattern, text) for code, pattern in PLACEHOLDER_PATTERNS
    }
    semantic_comment_count = count_pattern(SEMANTIC_COMMENT_RE, text)
    original_source_comment_count = count_pattern(ORIGINAL_SOURCE_RE, text)
    generated_note_count = count_pattern(GENERATED_NOTE_RE, text)
    mathlib_native_token_count = sum(
        len(re.findall(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])", text))
        for token in MATHLIB_NATIVE_TOKENS
    )
    theorem_statement_char_count = sum(len(signature) for signature in signatures)
    avg_theorem_signature_chars = (
        0.0
        if not signatures
        else round(theorem_statement_char_count / len(signatures), 3)
    )
    narrow_mathlib_import_count = sum(
        1 for item in imports if item.startswith("Mathlib.") and item != "Mathlib"
    )
    broad_import_count = sum(1 for item in imports if item == "Mathlib")

    return {
        "name": name,
        "hash": file_hash(text),
        "line_count": len(lines),
        "nonempty_line_count": sum(1 for line in lines if line.strip()),
        "import_count": len(imports),
        "imports": imports,
        "broad_mathlib_import_count": broad_import_count,
        "narrow_mathlib_import_count": narrow_mathlib_import_count,
        "declaration_count": len(declarations),
        "declaration_kind_counts": dict(kind_counts),
        "theorem_like_count": len(theorem_like),
        "axiom_count": kind_counts.get("axiom", 0),
        "structure_or_class_count": kind_counts.get("structure", 0)
        + kind_counts.get("class", 0),
        "placeholder_counts": placeholder_counts,
        "semantic_comment_count": semantic_comment_count,
        "original_source_comment_count": original_source_comment_count,
        "generated_note_count": generated_note_count,
        "semantic_comment_to_decl_ratio": round(
            semantic_comment_count / max(1, len(declarations)), 4
        ),
        "original_source_to_theorem_ratio": round(
            original_source_comment_count / max(1, len(theorem_like)), 4
        ),
        "mathlib_native_token_count": mathlib_native_token_count,
        "trivial_statement_count": trivial_statement_count,
        "trivial_proof_count": trivial_proof_count,
        "false_assumption_count": false_assumption_count,
        "avg_theorem_signature_chars": avg_theorem_signature_chars,
    }


def aggregate_file_stats(file_stats: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Document the responsibility of ``aggregate_file_stats``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``aggregate_file_stats`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    counts = Counter()
    placeholders = Counter()
    imports: List[str] = []
    hashes: Dict[str, str] = {}
    for item in file_stats:
        hashes[str(item["name"])] = str(item["hash"])
        for key in (
            "line_count",
            "nonempty_line_count",
            "import_count",
            "broad_mathlib_import_count",
            "narrow_mathlib_import_count",
            "declaration_count",
            "theorem_like_count",
            "axiom_count",
            "structure_or_class_count",
            "semantic_comment_count",
            "original_source_comment_count",
            "generated_note_count",
            "mathlib_native_token_count",
            "trivial_statement_count",
            "trivial_proof_count",
            "false_assumption_count",
        ):
            counts[key] += int(item.get(key, 0) or 0)
        placeholders.update(item.get("placeholder_counts", {}))
        imports.extend(item.get("imports", []))
    theorem_like_count = counts["theorem_like_count"]
    declaration_count = counts["declaration_count"]
    return {
        **dict(counts),
        "placeholder_counts": dict(placeholders),
        "imports": imports,
        "artifact_hashes": hashes,
        "semantic_comment_to_decl_ratio": round(
            counts["semantic_comment_count"] / max(1, declaration_count), 4
        ),
        "original_source_to_theorem_ratio": round(
            counts["original_source_comment_count"] / max(1, theorem_like_count), 4
        ),
    }


def read_reasoning_events(paths: Sequence[Path]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``read_reasoning_events``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    events: List[Dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                events.append(parsed)
    return events


def summarize_reasoning_events(events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Document the responsibility of ``summarize_reasoning_events``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``summarize_reasoning_events`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    steps = Counter()
    hooks = Counter()
    hard_true = 0
    hard_false = 0
    soft_true = 0
    soft_false = 0
    for event in events:
        step = event.get("step")
        if isinstance(step, str):
            steps[step] += 1
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        hook_id = payload.get("hook_id")
        if isinstance(hook_id, str):
            hooks[hook_id] += 1
        correctness = payload.get("correctness")
        if isinstance(correctness, bool):
            if correctness:
                hard_true += 1
            else:
                hard_false += 1
        judgement = payload.get("judgement")
        if isinstance(judgement, bool):
            if judgement:
                soft_true += 1
            else:
                soft_false += 1
        elif isinstance(judgement, str):
            if re.search(r"\bTrue\b", judgement):
                soft_true += 1
            if re.search(r"\bFalse\b", judgement):
                soft_false += 1
    return {
        "event_count": len(events),
        "top_steps": steps.most_common(12),
        "top_hooks": hooks.most_common(12),
        "hard_true_count": hard_true,
        "hard_false_count": hard_false,
        "soft_true_count": soft_true,
        "soft_false_count": soft_false,
    }


def report_bool_values(report: Optional[Dict[str, Any]]) -> List[bool]:
    """Document the responsibility of ``report_bool_values``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``report_bool_values`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if report is None:
        return []
    values: List[bool] = []
    summary = report.get("summary")
    if isinstance(summary, dict):
        for key in (
            "passed",
            "lean_execution_ok",
            "compatibility_audit_ok",
            "expected_declaration_checks_ok",
            "compatibility_target_met",
        ):
            value = summary.get(key)
            if isinstance(value, bool):
                values.append(value)
    for key in ("ok", "passed"):
        value = report.get(key)
        if isinstance(value, bool):
            values.append(value)
    passes = report.get("passes")
    if isinstance(passes, list):
        for item in passes:
            if not isinstance(item, dict):
                continue
            judgement = item.get("judgement")
            if isinstance(judgement, bool):
                values.append(judgement)
            elif isinstance(judgement, str):
                if judgement.lower() == "true":
                    values.append(True)
                elif judgement.lower() == "false":
                    values.append(False)
    return values


def report_numeric_scores(report: Optional[Dict[str, Any]]) -> List[float]:
    """Document the responsibility of ``report_numeric_scores``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``report_numeric_scores`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if report is None:
        return []
    scores: List[float] = []
    summary = report.get("summary")
    candidates: List[Any] = []
    if isinstance(summary, dict):
        candidates.extend(
            summary.get(key)
            for key in (
                "compatibility_score",
                "critical_review_score",
                "mathlib_concept_coverage_score",
            )
        )
    candidates.extend(
        report.get(key)
        for key in (
            "compatibility_score",
            "critical_review_score",
            "reference_free_confidence_score",
        )
    )
    for value in candidates:
        if isinstance(value, (int, float)):
            scores.append(float(value))
    return [max(0.0, min(100.0, score)) for score in scores]


def compute_scores(
    aggregate: Dict[str, Any],
    *,
    report: Optional[Dict[str, Any]],
    reasoning_summary: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """Document the responsibility of ``compute_scores``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``compute_scores`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    placeholders = aggregate.get("placeholder_counts", {})
    placeholder_total = sum(int(value) for value in placeholders.values())
    unresolved_proof_count = (
        int(placeholders.get("sorry", 0))
        + int(placeholders.get("admit", 0))
        + int(placeholders.get("exact_query", 0))
    )
    report_bools = report_bool_values(report)
    report_scores = report_numeric_scores(report)

    hard_true = int(reasoning_summary.get("hard_true_count", 0) or 0)
    hard_false = int(reasoning_summary.get("hard_false_count", 0) or 0)
    if report_bools:
        prover_base = 100.0 * (
            sum(1 for value in report_bools if value) / len(report_bools)
        )
    elif hard_true or hard_false:
        prover_base = 100.0 * hard_true / max(1, hard_true + hard_false)
    else:
        prover_base = 70.0
    prover_health = clamp_score(prover_base - 18 * hard_false)

    placeholder_freedom = clamp_score(
        100 - 28 * unresolved_proof_count - 10 * placeholder_total
    )

    axiom_count = int(aggregate.get("axiom_count", 0) or 0)
    trivial_statement_count = int(aggregate.get("trivial_statement_count", 0) or 0)
    false_assumption_count = int(aggregate.get("false_assumption_count", 0) or 0)
    theorem_like_count = int(aggregate.get("theorem_like_count", 0) or 0)
    logical_nonvacuity = clamp_score(
        100
        - 35 * axiom_count
        - 22 * trivial_statement_count
        - 18 * false_assumption_count
        - (20 if theorem_like_count == 0 else 0)
    )

    source_ratio = min(
        1.0, float(aggregate.get("original_source_to_theorem_ratio", 0.0) or 0.0)
    )
    semantic_ratio = min(
        1.0, float(aggregate.get("semantic_comment_to_decl_ratio", 0.0) or 0.0)
    )
    semantic_anchor_coverage = clamp_score(70 * source_ratio + 30 * semantic_ratio)

    narrow_imports = int(aggregate.get("narrow_mathlib_import_count", 0) or 0)
    broad_imports = int(aggregate.get("broad_mathlib_import_count", 0) or 0)
    mathlib_tokens = int(aggregate.get("mathlib_native_token_count", 0) or 0)
    mathlib_grounding = clamp_score(
        40
        + min(30, 8 * narrow_imports)
        + min(25, 2 * mathlib_tokens)
        - 18 * broad_imports
    )

    soft_true = int(reasoning_summary.get("soft_true_count", 0) or 0)
    soft_false = int(reasoning_summary.get("soft_false_count", 0) or 0)
    agreement_values: List[float] = []
    agreement_values.extend(100.0 if value else 0.0 for value in report_bools)
    agreement_values.extend(report_scores)
    if hard_true or hard_false:
        agreement_values.append(100.0 * hard_true / max(1, hard_true + hard_false))
    if soft_true or soft_false:
        agreement_values.append(100.0 * soft_true / max(1, soft_true + soft_false))
    critic_agreement = clamp_score(
        50.0 if not agreement_values else sum(agreement_values) / len(agreement_values)
    )

    declaration_count = int(aggregate.get("declaration_count", 0) or 0)
    avg_chars = float(aggregate.get("avg_theorem_signature_chars", 0.0) or 0.0)
    artifact_substance = clamp_score(
        35
        + min(25, 5 * theorem_like_count)
        + min(15, 2 * declaration_count)
        + min(15, avg_chars / 8)
        + min(10, 4 * int(aggregate.get("generated_note_count", 0) or 0))
        - 18 * trivial_statement_count
    )

    weighted = {
        "prover_health": (prover_health, 0.20),
        "placeholder_freedom": (placeholder_freedom, 0.18),
        "logical_nonvacuity": (logical_nonvacuity, 0.18),
        "semantic_anchor_coverage": (semantic_anchor_coverage, 0.15),
        "mathlib_grounding": (mathlib_grounding, 0.12),
        "critic_agreement": (critic_agreement, 0.10),
        "artifact_substance": (artifact_substance, 0.07),
    }
    composite = clamp_score(sum(score * weight for score, weight in weighted.values()))

    def measure(score: int, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Document the responsibility of ``compute_scores.measure``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Provide the local operation named ``compute_scores.measure`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return {
            "score": score,
            "orientation": "nondecreasing",
            "evidence": evidence,
        }

    return {
        "reference_free_confidence": measure(
            composite,
            {"weights": {name: weight for name, (_, weight) in weighted.items()}},
        ),
        "prover_health": measure(
            prover_health,
            {
                "report_bool_count": len(report_bools),
                "hard_true_count": hard_true,
                "hard_false_count": hard_false,
            },
        ),
        "placeholder_freedom": measure(
            placeholder_freedom,
            {
                "placeholder_counts": placeholders,
                "unresolved_proof_count": unresolved_proof_count,
            },
        ),
        "logical_nonvacuity": measure(
            logical_nonvacuity,
            {
                "axiom_count": axiom_count,
                "trivial_statement_count": trivial_statement_count,
                "false_assumption_count": false_assumption_count,
                "theorem_like_count": theorem_like_count,
            },
        ),
        "semantic_anchor_coverage": measure(
            semantic_anchor_coverage,
            {
                "original_source_to_theorem_ratio": source_ratio,
                "semantic_comment_to_decl_ratio": semantic_ratio,
                "original_source_comment_count": aggregate.get(
                    "original_source_comment_count", 0
                ),
                "semantic_comment_count": aggregate.get("semantic_comment_count", 0),
            },
        ),
        "mathlib_grounding": measure(
            mathlib_grounding,
            {
                "narrow_mathlib_import_count": narrow_imports,
                "broad_mathlib_import_count": broad_imports,
                "mathlib_native_token_count": mathlib_tokens,
            },
        ),
        "critic_agreement": measure(
            critic_agreement,
            {
                "report_bool_values": report_bools,
                "report_numeric_scores": report_scores,
                "soft_true_count": soft_true,
                "soft_false_count": soft_false,
            },
        ),
        "artifact_substance": measure(
            artifact_substance,
            {
                "declaration_count": declaration_count,
                "theorem_like_count": theorem_like_count,
                "avg_theorem_signature_chars": avg_chars,
            },
        ),
    }


def risk_counts(
    aggregate: Dict[str, Any], measures: Dict[str, Dict[str, Any]]
) -> Dict[str, int]:
    """Document the responsibility of ``risk_counts``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``risk_counts`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    placeholders = aggregate.get("placeholder_counts", {})
    return {
        "unresolved_proof_count": int(placeholders.get("sorry", 0))
        + int(placeholders.get("admit", 0))
        + int(placeholders.get("exact_query", 0)),
        "target_axiom_count": int(aggregate.get("axiom_count", 0) or 0),
        "placeholder_marker_count": int(placeholders.get("placeholder_marker", 0))
        + int(placeholders.get("mock_marker", 0))
        + int(placeholders.get("scaffold_marker", 0)),
        "trivial_statement_count": int(
            aggregate.get("trivial_statement_count", 0) or 0
        ),
        "low_score_dimension_count": sum(
            1 for item in measures.values() if int(item.get("score", 0)) < 65
        ),
    }


def make_snapshot(
    *,
    file_stats: Sequence[Dict[str, Any]],
    aggregate: Dict[str, Any],
    measures: Dict[str, Dict[str, Any]],
    risks: Dict[str, int],
) -> Dict[str, Any]:
    """Document the responsibility of ``make_snapshot``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark_used": False,
        "artifact_hashes": aggregate.get("artifact_hashes", {}),
        "scores": {name: int(item["score"]) for name, item in measures.items()},
        "risk_counts": risks,
        "structure": {
            "file_count": len(file_stats),
            "line_count": aggregate.get("line_count", 0),
            "declaration_count": aggregate.get("declaration_count", 0),
            "theorem_like_count": aggregate.get("theorem_like_count", 0),
            "original_source_comment_count": aggregate.get(
                "original_source_comment_count", 0
            ),
            "semantic_comment_count": aggregate.get("semantic_comment_count", 0),
            "narrow_mathlib_import_count": aggregate.get(
                "narrow_mathlib_import_count", 0
            ),
            "broad_mathlib_import_count": aggregate.get(
                "broad_mathlib_import_count", 0
            ),
        },
    }


def extract_snapshot(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Document the responsibility of ``extract_snapshot``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_snapshot`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if payload is None:
        return None
    snapshot = payload.get("reference_free_snapshot")
    if isinstance(snapshot, dict):
        return snapshot
    if "scores" in payload and "risk_counts" in payload:
        return payload
    return None


def compare_snapshots(
    current: Dict[str, Any],
    baseline_payload: Optional[Dict[str, Any]],
    *,
    score_tolerance: int = 0,
) -> Dict[str, Any]:
    """Document the responsibility of ``compare_snapshots``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``compare_snapshots`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    baseline = extract_snapshot(baseline_payload)
    if baseline is None:
        return {
            "baseline_present": False,
            "ok": True,
            "regressions": [],
            "warnings": [],
            "improvements": [],
        }

    current_scores = current.get("scores", {})
    baseline_scores = baseline.get("scores", {})
    regressions: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    improvements: List[Dict[str, Any]] = []

    for name, before in baseline_scores.items():
        after = current_scores.get(name)
        if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
            continue
        if after + score_tolerance < before:
            regressions.append(
                {
                    "kind": "score_decrease",
                    "measure": name,
                    "baseline": before,
                    "current": after,
                    "message": "Reference-free score decreased below accepted baseline.",
                }
            )
        elif after > before:
            improvements.append(
                {
                    "kind": "score_increase",
                    "measure": name,
                    "baseline": before,
                    "current": after,
                }
            )

    current_risks = current.get("risk_counts", {})
    baseline_risks = baseline.get("risk_counts", {})
    for name, before in baseline_risks.items():
        after = current_risks.get(name)
        if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
            continue
        if after > before:
            regressions.append(
                {
                    "kind": "risk_increase",
                    "measure": name,
                    "baseline": before,
                    "current": after,
                    "message": "Reference-free risk count increased over accepted baseline.",
                }
            )
        elif after < before:
            improvements.append(
                {
                    "kind": "risk_decrease",
                    "measure": name,
                    "baseline": before,
                    "current": after,
                }
            )

    current_structure = current.get("structure", {})
    baseline_structure = baseline.get("structure", {})
    for name in ("theorem_like_count", "original_source_comment_count"):
        before = baseline_structure.get(name)
        after = current_structure.get(name)
        if (
            isinstance(before, (int, float))
            and isinstance(after, (int, float))
            and after < before
        ):
            regressions.append(
                {
                    "kind": "surface_shrinkage",
                    "measure": name,
                    "baseline": before,
                    "current": after,
                    "message": "The formal/source-alignment surface shrank relative to the accepted baseline.",
                }
            )

    before_decl = baseline_structure.get("declaration_count")
    after_decl = current_structure.get("declaration_count")
    if isinstance(before_decl, (int, float)) and isinstance(after_decl, (int, float)):
        if before_decl > 0 and after_decl < 0.8 * before_decl:
            warnings.append(
                {
                    "kind": "large_artifact_shrinkage",
                    "measure": "declaration_count",
                    "baseline": before_decl,
                    "current": after_decl,
                    "message": "Declaration count dropped by more than 20%; require semantic-preservation justification.",
                }
            )

    return {
        "baseline_present": True,
        "ok": not regressions,
        "regressions": regressions,
        "warnings": warnings,
        "improvements": improvements,
    }


def build_todos(
    measures: Dict[str, Dict[str, Any]],
    comparison: Dict[str, Any],
    risks: Dict[str, int],
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``build_todos``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    todos: List[Dict[str, Any]] = []
    for item in comparison.get("regressions", []):
        todos.append(
            {
                "status": "todo",
                "priority": "P0",
                "task": f"Repair reference-free regression in `{item.get('measure')}`.",
                "evidence": item,
            }
        )
    for name, measure in measures.items():
        score = int(measure.get("score", 0))
        if score < 65:
            todos.append(
                {
                    "status": "todo",
                    "priority": "P1",
                    "task": f"Raise weak reference-free dimension `{name}` before accepting prompt changes.",
                    "evidence": measure.get("evidence", {}),
                }
            )
    for name, count in risks.items():
        if count > 0 and name in {
            "unresolved_proof_count",
            "target_axiom_count",
            "placeholder_marker_count",
        }:
            todos.append(
                {
                    "status": "todo",
                    "priority": "P0",
                    "task": f"Eliminate `{name}` before treating the artifact as a completed result.",
                    "evidence": {"count": count},
                }
            )
    if not todos:
        todos.append(
            {
                "status": "todo",
                "priority": "P2",
                "task": "Accept this snapshot as a baseline only after the Lean artifact and critique packet are reviewed.",
                "evidence": {
                    "reason": "No reference-free regression or weak dimension was detected."
                },
            }
        )
    return todos


def method_notes() -> List[str]:
    """Document the responsibility of ``method_notes``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``method_notes`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return [
        "No gold formalization or benchmark target is used by this monitor.",
        "Scores are correctness proxies, not a mathematical proof of semantic correctness.",
        "The method relies on independent failure surfaces: Lean/prover health, placeholder absence, non-vacuity, source anchors, mathlib grounding, critic agreement, and artifact substance.",
        "Monotonic acceptance is blocked when a refinement improves an aggregate score while increasing hard risks or shrinking theorem/source-anchor surfaces.",
    ]


def build_packet(
    *,
    texts: Sequence[Tuple[str, str]],
    report: Optional[Dict[str, Any]],
    reasoning_events: Sequence[Dict[str, Any]],
    baseline: Optional[Dict[str, Any]],
    min_composite_score: int,
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
    file_stats = [analyze_lean_text(text=text, name=name) for name, text in texts]
    aggregate = aggregate_file_stats(file_stats)
    if file_stats:
        aggregate["avg_theorem_signature_chars"] = round(
            sum(
                float(item.get("avg_theorem_signature_chars", 0.0) or 0.0)
                for item in file_stats
            )
            / max(1, len(file_stats)),
            3,
        )
    reasoning_summary = summarize_reasoning_events(reasoning_events)
    measures = compute_scores(
        aggregate, report=report, reasoning_summary=reasoning_summary
    )
    risks = risk_counts(aggregate, measures)
    snapshot = make_snapshot(
        file_stats=file_stats,
        aggregate=aggregate,
        measures=measures,
        risks=risks,
    )
    comparison = compare_snapshots(snapshot, baseline)
    composite = int(measures["reference_free_confidence"]["score"])
    hard_risk_clean = (
        risks["unresolved_proof_count"] == 0
        and risks["target_axiom_count"] == 0
        and risks["placeholder_marker_count"] == 0
    )
    gate_decision = decide_gate(
        gate_id="reference-free-critic-monitor",
        hook_id=HOOK_ID,
        checks=[
            {
                "id": "composite_floor",
                "passed": composite >= min_composite_score,
                "severity": "medium",
                "blocking": False,
                "message": f"Reference-free confidence should be at least {min_composite_score}.",
            },
            {
                "id": "hard_risk_clean",
                "passed": hard_risk_clean,
                "severity": "high",
                "blocking": True,
                "message": "No unresolved proof placeholders, target axioms, or mock/scaffold markers may remain.",
            },
            {
                "id": "monotonic_comparison",
                "passed": bool(comparison.get("ok", True)),
                "severity": "high",
                "blocking": True,
                "message": "No accepted baseline score or risk may regress.",
            },
        ],
    )
    todos = build_todos(measures, comparison, risks)
    return {
        "ok": bool(gate_decision["ok"]),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "reference_free_confidence_score": composite,
            "benchmark_used": False,
            "baseline_present": comparison.get("baseline_present", False),
            "regression_count": len(comparison.get("regressions", [])),
            "weak_dimension_count": sum(
                1 for item in measures.values() if int(item.get("score", 0)) < 65
            ),
            "hard_risk_clean": hard_risk_clean,
            "todo_count": len(todos),
        },
        "reference_free_snapshot": snapshot,
        "measures": measures,
        "risk_counts": risks,
        "file_stats": file_stats,
        "reasoning_event_summary": reasoning_summary,
        "monotonicity_comparison": comparison,
        "method_notes": method_notes(),
        "todos": todos,
        "gate_decision": gate_decision,
    }


def collect_text_inputs(args: argparse.Namespace) -> List[Tuple[str, str]]:
    """Document the responsibility of ``collect_text_inputs``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``collect_text_inputs`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    texts: List[Tuple[str, str]] = []
    for raw_path in args.lean_file or []:
        path = (
            (REPO_ROOT / raw_path).resolve() if not raw_path.is_absolute() else raw_path
        )
        texts.append((rel(path), path.read_text(encoding="utf-8")))
    if args.text is not None:
        texts.append((args.name, args.text))
    if not texts:
        raise ValueError("Provide at least one --lean-file or --text input.")
    return texts


def append_ledger(path: Path, snapshot: Dict[str, Any]) -> None:
    """Document the responsibility of ``append_ledger``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``append_ledger`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False, sort_keys=True) + "\n")


def load_snapshot_history(path: Optional[Path]) -> List[Dict[str, Any]]:
    """Load previously accepted reference-free snapshots from a JSONL ledger.

    Motivation:
        Treat the monitor as an evolutionary instrument, not only a terminal
        score card.

    Intent:
        Recover prior accepted states so plots and trend statistics can show
        how a formalization changed over time.

    Inputs:
        `path` points to a JSONL ledger whose rows are snapshots or full monitor
        packets.

    Outputs:
        Returns normalized snapshot payloads with malformed rows skipped rather
        than treated as hard failures.
    """

    if path is None or not path.exists():
        return []
    snapshots: List[Dict[str, Any]] = []
    for line_no, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw.strip():
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        snapshot = extract_snapshot(parsed if isinstance(parsed, dict) else None)
        if snapshot is not None:
            snapshot = dict(snapshot)
            snapshot["_history_source"] = f"{rel(path)}:{line_no}"
            snapshots.append(snapshot)
    return snapshots


def snapshot_key(snapshot: Dict[str, Any]) -> str:
    """Build a stable duplicate key for snapshot timeline de-duplication."""

    return json.dumps(
        {
            "hashes": snapshot.get("artifact_hashes", {}),
            "scores": snapshot.get("scores", {}),
            "risks": snapshot.get("risk_counts", {}),
            "created": snapshot.get("created_at_utc"),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def normalize_evolution_timeline(
    *,
    baseline: Optional[Dict[str, Any]],
    history: Sequence[Dict[str, Any]],
    current: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Create a chronological formalization-evolution timeline.

    Motivation:
        Make the formalization trajectory inspectable even when there is no
        benchmark reference or gold target.

    Intent:
        Combine accepted baseline state, accepted ledger states, and the current
        monitor snapshot into one typed timeline.

    Inputs:
        `baseline` may be a snapshot or packet, `history` is accepted ledger
        history, and `current` is the just-computed snapshot.

    Outputs:
        Returns timeline points with scores, risk counts, structure, and labels.
    """

    candidates: List[Tuple[str, Dict[str, Any]]] = []
    baseline_snapshot = extract_snapshot(baseline)
    if baseline_snapshot is not None:
        candidates.append(("baseline", baseline_snapshot))
    for index, item in enumerate(history, start=1):
        snapshot = extract_snapshot(item)
        if snapshot is not None:
            candidates.append((f"ledger_{index:03d}", snapshot))
    candidates.append(("current", current))

    seen: set[str] = set()
    timeline: List[Dict[str, Any]] = []
    for label, raw_snapshot in candidates:
        snapshot = dict(raw_snapshot)
        key = snapshot_key(snapshot)
        if key in seen and label != "current":
            continue
        seen.add(key)
        timeline.append(
            {
                "index": len(timeline),
                "label": label,
                "created_at_utc": snapshot.get("created_at_utc"),
                "source": snapshot.get("_history_source"),
                "scores": dict(snapshot.get("scores", {})),
                "risk_counts": dict(snapshot.get("risk_counts", {})),
                "structure": dict(snapshot.get("structure", {})),
                "artifact_hashes": dict(snapshot.get("artifact_hashes", {})),
            }
        )
    return timeline


def numeric_series(
    timeline: Sequence[Dict[str, Any]], section: str
) -> Dict[str, List[float]]:
    """Collect numeric series from a timeline section such as scores or risks."""

    series: Dict[str, List[float]] = {}
    keys = sorted(
        {
            key
            for point in timeline
            for key, value in dict(point.get(section, {})).items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
    )
    for key in keys:
        values: List[float] = []
        for point in timeline:
            value = dict(point.get(section, {})).get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                values.append(float(value))
            else:
                values.append(0.0)
        series[key] = values
    return series


def series_statistics(values: Sequence[float], *, orientation: str) -> Dict[str, Any]:
    """Compute compact trend statistics for a scalar evolution series."""

    if not values:
        return {
            "count": 0,
            "first": None,
            "last": None,
            "delta": 0.0,
            "slope_per_step": 0.0,
            "min": None,
            "max": None,
            "regression_count": 0,
            "improvement_count": 0,
            "monotone": True,
        }
    deltas = [right - left for left, right in zip(values, values[1:])]
    if orientation == "nondecreasing":
        regressions = [delta for delta in deltas if delta < 0]
        improvements = [delta for delta in deltas if delta > 0]
    elif orientation == "nonincreasing":
        regressions = [delta for delta in deltas if delta > 0]
        improvements = [delta for delta in deltas if delta < 0]
    else:
        regressions = []
        improvements = [delta for delta in deltas if delta != 0]
    return {
        "count": len(values),
        "first": round(values[0], 4),
        "last": round(values[-1], 4),
        "delta": round(values[-1] - values[0], 4),
        "slope_per_step": round((values[-1] - values[0]) / max(1, len(values) - 1), 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "regression_count": len(regressions),
        "improvement_count": len(improvements),
        "monotone": not regressions,
    }


def build_evolution_statistics(timeline: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize score, risk, and structure evolution across snapshots."""

    score_series = numeric_series(timeline, "scores")
    risk_series = numeric_series(timeline, "risk_counts")
    structure_series = numeric_series(timeline, "structure")
    score_stats = {
        key: series_statistics(values, orientation="nondecreasing")
        for key, values in score_series.items()
    }
    risk_stats = {
        key: series_statistics(values, orientation="nonincreasing")
        for key, values in risk_series.items()
    }
    structure_stats = {
        key: series_statistics(values, orientation="observed")
        for key, values in structure_series.items()
    }
    confidence = score_stats.get("reference_free_confidence", {})
    hard_risk_keys = (
        "unresolved_proof_count",
        "target_axiom_count",
        "placeholder_marker_count",
    )
    first_hard_risk = sum(
        risk_series.get(key, [0.0])[0] for key in hard_risk_keys if risk_series.get(key)
    )
    last_hard_risk = sum(
        risk_series.get(key, [0.0])[-1]
        for key in hard_risk_keys
        if risk_series.get(key)
    )
    return {
        "observation_count": len(timeline),
        "score_metric_count": len(score_series),
        "risk_metric_count": len(risk_series),
        "structure_metric_count": len(structure_series),
        "reference_free_confidence_delta": confidence.get("delta", 0.0),
        "reference_free_confidence_slope_per_step": confidence.get(
            "slope_per_step", 0.0
        ),
        "score_regression_event_count": sum(
            int(item.get("regression_count", 0)) for item in score_stats.values()
        ),
        "risk_regression_event_count": sum(
            int(item.get("regression_count", 0)) for item in risk_stats.values()
        ),
        "hard_risk_delta": round(last_hard_risk - first_hard_risk, 4),
        "latest_scores": dict(timeline[-1].get("scores", {})) if timeline else {},
        "latest_risks": dict(timeline[-1].get("risk_counts", {})) if timeline else {},
        "score_statistics": score_stats,
        "risk_statistics": risk_stats,
        "structure_statistics": structure_stats,
    }


def build_formalization_evolution(
    *,
    baseline: Optional[Dict[str, Any]],
    history: Sequence[Dict[str, Any]],
    current: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the monitor's reference-free formalization-evolution model."""

    timeline = normalize_evolution_timeline(
        baseline=baseline,
        history=history,
        current=current,
    )
    return {
        "schema_version": 1,
        "reference_free": True,
        "interpretation": (
            "Evolution is measured from local correctness proxies rather than a "
            "gold formalization: scores should not decrease and hard risks "
            "should not increase across accepted snapshots."
        ),
        "timeline": timeline,
        "statistics": build_evolution_statistics(timeline),
        "plots": {},
    }


def render_evolution_svg(
    evolution: Dict[str, Any], *, width: int = 1180, height: int = 680
) -> str:
    """Render a dependency-free SVG plot for score and risk evolution."""

    timeline = list(evolution.get("timeline", []))
    score_series = numeric_series(timeline, "scores")
    _risk_series = numeric_series(timeline, "risk_counts")
    priority = [
        "reference_free_confidence",
        "prover_health",
        "placeholder_freedom",
        "logical_nonvacuity",
        "semantic_anchor_coverage",
        "mathlib_grounding",
        "critic_agreement",
        "artifact_substance",
    ]
    selected_scores = [name for name in priority if name in score_series][:6]
    if not selected_scores:
        selected_scores = sorted(score_series)[:6]
    risk_totals = [
        sum(float(value) for value in dict(point.get("risk_counts", {})).values())
        for point in timeline
    ]
    colors = ["#2563EB", "#059669", "#7C3AED", "#DC2626", "#EA580C", "#0891B2"]
    left, right = 86.0, width - 42.0
    score_top, score_bottom = 82.0, 392.0
    risk_top, risk_bottom = 462.0, 610.0
    plot_width = right - left
    steps = max(1, len(timeline) - 1)

    def x(index: int) -> float:
        return left + plot_width * (index / steps)

    def y_score(value: float) -> float:
        return score_bottom - (score_bottom - score_top) * (
            max(0.0, min(100.0, value)) / 100.0
        )

    max_risk = max([1.0, *risk_totals])

    def y_risk(value: float) -> float:
        return risk_bottom - (risk_bottom - risk_top) * (max(0.0, value) / max_risk)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Reference-free formalization evolution">',
        "<style>",
        ".title{font:700 22px Arial,sans-serif;fill:#0f172a}.subtitle{font:12px Arial,sans-serif;fill:#475569}.axis{stroke:#94A3B8;stroke-width:1.2}.grid{stroke:#E2E8F0;stroke-width:1}.tick{font:11px Arial,sans-serif;fill:#64748B}.label{font:700 12px Arial,sans-serif;fill:#334155}.legend{font:12px Arial,sans-serif;fill:#334155}",
        "</style>",
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        '<text x="34" y="34" class="title">Reference-free formalization evolution</text>',
        '<text x="34" y="56" class="subtitle">Scores should move upward; hard-risk counts should move downward or stay flat. No gold formalization is used.</text>',
        f'<rect x="{left}" y="{score_top}" width="{plot_width}" height="{score_bottom-score_top}" rx="8" fill="#F8FAFC" stroke="#CBD5E1"/>',
        f'<rect x="{left}" y="{risk_top}" width="{plot_width}" height="{risk_bottom-risk_top}" rx="8" fill="#FFF7ED" stroke="#FED7AA"/>',
    ]
    for value in (0, 25, 50, 75, 100):
        yy = y_score(value)
        parts.append(
            f'<line x1="{left}" y1="{yy:.2f}" x2="{right}" y2="{yy:.2f}" class="grid"/>'
        )
        parts.append(
            f'<text x="{left-14}" y="{yy+4:.2f}" text-anchor="end" class="tick">{value}</text>'
        )
    parts.append(f'<text x="34" y="{score_top+8}" class="label">scores</text>')
    parts.append(f'<text x="34" y="{risk_top+8}" class="label">risk counts</text>')
    for idx, point in enumerate(timeline):
        xx = x(idx)
        label = str(point.get("label") or idx)
        parts.append(
            f'<line x1="{xx:.2f}" y1="{score_bottom}" x2="{xx:.2f}" y2="{risk_bottom+8}" class="grid"/>'
        )
        parts.append(
            f'<text x="{xx:.2f}" y="{risk_bottom+30}" text-anchor="middle" class="tick">{html.escape(label)}</text>'
        )
    for color, name in zip(colors, selected_scores):
        values = score_series[name]
        points = " ".join(
            f"{x(index):.2f},{y_score(value):.2f}" for index, value in enumerate(values)
        )
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.6"/>'
        )
        for index, value in enumerate(values):
            xx, yy = x(index), y_score(value)
            title = f"{name}: {value:.1f}"
            parts.append(
                f'<circle cx="{xx:.2f}" cy="{yy:.2f}" r="4" fill="{color}"><title>{html.escape(title)}</title></circle>'
            )
    legend_x, legend_y = left, score_bottom + 32
    for offset, (color, name) in enumerate(zip(colors, selected_scores)):
        lx = legend_x + (offset % 3) * 310
        ly = legend_y + (offset // 3) * 20
        parts.append(
            f'<rect x="{lx:.2f}" y="{ly-10:.2f}" width="12" height="12" fill="{color}" rx="2"/>'
        )
        parts.append(
            f'<text x="{lx+18:.2f}" y="{ly:.2f}" class="legend">{html.escape(name.replace("_", " "))}</text>'
        )
    bar_width = min(72.0, plot_width / max(1, len(timeline)) * 0.42)
    for index, total in enumerate(risk_totals):
        xx = x(index) - bar_width / 2
        yy = y_risk(total)
        parts.append(
            f'<rect x="{xx:.2f}" y="{yy:.2f}" width="{bar_width:.2f}" height="{risk_bottom-yy:.2f}" rx="4" fill="#F97316" opacity="0.82"><title>total risk count: {total:.1f}</title></rect>'
        )
    for value in (0, max_risk / 2, max_risk):
        yy = y_risk(value)
        parts.append(
            f'<line x1="{left}" y1="{yy:.2f}" x2="{right}" y2="{yy:.2f}" class="grid"/>'
        )
        parts.append(
            f'<text x="{left-14}" y="{yy+4:.2f}" text-anchor="end" class="tick">{value:.1f}</text>'
        )
    stats = evolution.get("statistics", {})
    footer = (
        f"observations={stats.get('observation_count', 0)}; "
        f"confidence_delta={stats.get('reference_free_confidence_delta', 0)}; "
        f"score_regressions={stats.get('score_regression_event_count', 0)}; "
        f"risk_regressions={stats.get('risk_regression_event_count', 0)}"
    )
    parts.append(
        f'<text x="{left}" y="{height-22}" class="subtitle">{html.escape(footer)}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def write_evolution_csv(path: Path, evolution: Dict[str, Any]) -> None:
    """Write the evolution timeline as a compact CSV table."""

    timeline = list(evolution.get("timeline", []))
    score_keys = sorted(
        {
            key
            for point in timeline
            for key, value in dict(point.get("scores", {})).items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
    )
    risk_keys = sorted(
        {
            key
            for point in timeline
            for key, value in dict(point.get("risk_counts", {})).items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
    )
    columns = (
        ["index", "label", "created_at_utc"]
        + [f"score_{key}" for key in score_keys]
        + [f"risk_{key}" for key in risk_keys]
    )

    def csv_cell(value: Any) -> str:
        text = "" if value is None else str(value)
        if any(char in text for char in [",", "\n", '"']):
            return '"' + text.replace('"', '""') + '"'
        return text

    rows = [",".join(columns)]
    for point in timeline:
        values: List[Any] = [
            point.get("index"),
            point.get("label"),
            point.get("created_at_utc"),
        ]
        scores = dict(point.get("scores", {}))
        risks = dict(point.get("risk_counts", {}))
        values.extend(scores.get(key, "") for key in score_keys)
        values.extend(risks.get(key, "") for key in risk_keys)
        rows.append(",".join(csv_cell(value) for value in values))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_evolution_artifacts(
    output_dir: Path, evolution: Dict[str, Any]
) -> Dict[str, str]:
    """Persist evolution plots and statistics next to monitor outputs."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "formalization_evolution.json"
    csv_path = output_dir / "formalization_evolution.csv"
    svg_path = output_dir / "formalization_evolution.svg"
    write_evolution_csv(csv_path, evolution)
    svg_path.write_text(render_evolution_svg(evolution), encoding="utf-8")
    plots = {
        "evolution_json": rel(json_path),
        "evolution_csv": rel(csv_path),
        "evolution_svg": rel(svg_path),
    }
    json_payload = {**evolution, "plots": plots}
    json_path.write_text(
        json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return plots


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
    weak = "theorem weak : True := by trivial"
    improved = (
        "import Mathlib.Data.Nat.Basic\n\n"
        "/--\n"
        "Original source (NL): Adding zero to a natural number gives the same number.\n"
        "Original source (LaTeX): `n + 0 = n`.\n"
        "-/\n"
        "theorem add_zero_source (n : Nat) : n + 0 = n := by\n"
        "  simpa using Nat.add_zero n\n"
    )
    baseline_packet = build_packet(
        texts=[("weak", weak)],
        report=None,
        reasoning_events=[],
        baseline=None,
        min_composite_score=50,
    )
    packet = build_packet(
        texts=[("improved", improved)],
        report={"summary": {"passed": True, "lean_execution_ok": True}},
        reasoning_events=[],
        baseline=baseline_packet["reference_free_snapshot"],
        min_composite_score=50,
    )
    before = baseline_packet["summary"]["reference_free_confidence_score"]
    after = packet["summary"]["reference_free_confidence_score"]
    evolution = build_formalization_evolution(
        baseline=baseline_packet["reference_free_snapshot"],
        history=[],
        current=packet["reference_free_snapshot"],
    )
    packet["formalization_evolution"] = evolution
    packet["self_test"] = {
        "ok": (
            packet["ok"]
            and after > before
            and evolution["statistics"]["observation_count"] >= 2
            and evolution["statistics"]["reference_free_confidence_delta"] > 0
        ),
        "baseline_score": before,
        "improved_score": after,
        "evolution_observation_count": evolution["statistics"]["observation_count"],
        "evolution_confidence_delta": evolution["statistics"][
            "reference_free_confidence_delta"
        ],
    }
    packet["ok"] = bool(packet["self_test"]["ok"])
    return packet


def render_text(packet: Dict[str, Any]) -> str:
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
    summary = packet["summary"]
    lines = [
        f"ok: {packet['ok']}",
        f"reference_free_confidence: {summary['reference_free_confidence_score']}",
        f"baseline_present: {summary['baseline_present']}",
        f"regressions: {summary['regression_count']}",
        f"hard_risk_clean: {summary['hard_risk_clean']}",
    ]
    evolution = packet.get("formalization_evolution")
    if isinstance(evolution, dict):
        stats = evolution.get("statistics", {})
        lines.append(f"evolution_observations: {stats.get('observation_count', 0)}")
        lines.append(
            f"evolution_confidence_delta: {stats.get('reference_free_confidence_delta', 0)}"
        )
        plots = evolution.get("plots", {})
        if isinstance(plots, dict) and plots.get("evolution_svg"):
            lines.append(f"evolution_plot: {plots['evolution_svg']}")
    for item in packet["todos"][:8]:
        lines.append(f"- {item['priority']} {item['task']}")
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
    parser.add_argument("--lean-file", type=Path, action="append", default=[])
    parser.add_argument("--text")
    parser.add_argument("--name", default="inline_text")
    parser.add_argument("--report-file", type=Path)
    parser.add_argument("--reasoning-log-file", type=Path, action="append", default=[])
    parser.add_argument("--baseline-file", type=Path)
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("artifacts/reference_free_critic_monitor/latest.json"),
    )
    parser.add_argument(
        "--ledger-file",
        type=Path,
        default=Path("artifacts/reference_free_critic_monitor/ledger.jsonl"),
    )
    parser.add_argument("--append-ledger", action="store_true")
    parser.add_argument(
        "--evolution-output-dir",
        type=Path,
        default=Path("artifacts/reference_free_critic_monitor/evolution"),
    )
    parser.add_argument("--no-evolution-plots", action="store_true")
    parser.add_argument(
        "--reasoning-log-output-file",
        type=Path,
        default=Path("artifacts/reference_free_critic_monitor/reasoning.jsonl"),
    )
    parser.add_argument("--no-reasoning-log", action="store_true")
    parser.add_argument("--min-composite-score", type=int, default=60)
    parser.add_argument("--expect-ok", action="store_true")
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
        packet = run_self_test()
        if args.json:
            print(json.dumps(packet, ensure_ascii=False, indent=2))
        else:
            print(render_text(packet))
        return 0 if packet["ok"] else 3

    output_file = (REPO_ROOT / args.output_file).resolve()
    reasoning_log = (
        None
        if args.no_reasoning_log
        else (REPO_ROOT / args.reasoning_log_output_file).resolve()
    )
    append_event(
        reasoning_log,
        "reference_free_critic_monitor_start",
        {
            "lean_file_count": len(args.lean_file or []),
            "has_text": args.text is not None,
            "report_file": None if args.report_file is None else str(args.report_file),
            "baseline_file": (
                None if args.baseline_file is None else str(args.baseline_file)
            ),
        },
    )
    try:
        texts = collect_text_inputs(args)
        report_file = (
            None
            if args.report_file is None
            else (
                (REPO_ROOT / args.report_file).resolve()
                if not args.report_file.is_absolute()
                else args.report_file
            )
        )
        baseline_file = (
            None
            if args.baseline_file is None
            else (
                (REPO_ROOT / args.baseline_file).resolve()
                if not args.baseline_file.is_absolute()
                else args.baseline_file
            )
        )
        reasoning_log_files = [
            (REPO_ROOT / path).resolve() if not path.is_absolute() else path
            for path in args.reasoning_log_file
        ]
        report = load_json(report_file)
        baseline = load_json(baseline_file)
        reasoning_events = read_reasoning_events(reasoning_log_files)
        ledger_file = (
            (REPO_ROOT / args.ledger_file).resolve()
            if not args.ledger_file.is_absolute()
            else args.ledger_file
        )
        snapshot_history = load_snapshot_history(ledger_file)
        packet = build_packet(
            texts=texts,
            report=report,
            reasoning_events=reasoning_events,
            baseline=baseline,
            min_composite_score=args.min_composite_score,
        )
        packet["output_file"] = rel(output_file)
        packet["report_file"] = None if report_file is None else rel(report_file)
        packet["baseline_file"] = None if baseline_file is None else rel(baseline_file)
        packet["lean_files"] = [name for name, _ in texts]
        evolution = build_formalization_evolution(
            baseline=baseline,
            history=snapshot_history,
            current=packet["reference_free_snapshot"],
        )
        if not args.no_evolution_plots:
            evolution_output_dir = (
                (REPO_ROOT / args.evolution_output_dir).resolve()
                if not args.evolution_output_dir.is_absolute()
                else args.evolution_output_dir
            )
            evolution["plots"] = write_evolution_artifacts(
                evolution_output_dir, evolution
            )
        packet["formalization_evolution"] = evolution
        append_event(
            reasoning_log,
            "reference_free_critic_measurement_complete",
            {
                "reference_free_confidence_score": packet["summary"][
                    "reference_free_confidence_score"
                ],
                "weak_dimension_count": packet["summary"]["weak_dimension_count"],
                "hard_risk_clean": packet["summary"]["hard_risk_clean"],
                "evolution_observation_count": evolution["statistics"][
                    "observation_count"
                ],
            },
        )
        append_event(
            reasoning_log,
            "reference_free_critic_monotonicity_complete",
            {
                "baseline_present": packet["summary"]["baseline_present"],
                "regression_count": packet["summary"]["regression_count"],
                "ok": packet["monotonicity_comparison"]["ok"],
            },
        )
        write_json(output_file, packet)
        if args.write_baseline:
            if baseline_file is None:
                raise ValueError("--write-baseline requires --baseline-file")
            write_json(baseline_file, packet["reference_free_snapshot"])
        if args.append_ledger:
            ledger_file = (
                (REPO_ROOT / args.ledger_file).resolve()
                if not args.ledger_file.is_absolute()
                else args.ledger_file
            )
            append_ledger(ledger_file, packet["reference_free_snapshot"])
        append_event(
            reasoning_log,
            "reference_free_critic_monitor_complete",
            {"ok": packet["ok"], "output_file": rel(output_file)},
        )
    except Exception as exc:
        append_event(
            reasoning_log,
            "reference_free_critic_monitor_error",
            {"error": str(exc)},
        )
        raise

    if args.expect_ok and not packet["ok"]:
        if args.json:
            print(json.dumps(packet, ensure_ascii=False, indent=2))
        else:
            print(render_text(packet))
        return 3
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    else:
        print(render_text(packet))
    return 0 if packet["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
