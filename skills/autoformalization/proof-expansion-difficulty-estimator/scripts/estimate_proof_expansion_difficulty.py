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

"""Estimate difficulty of expanding proof parts and decide when web support is warranted."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

from reasoning_log import (
    append_reasoning_log_entry,
)

HARD_PATTERNS = [
    (r"\bstandard\b", 12, "standard result cited without details"),
    (r"\bwell[- ]known\b", 12, "well-known result cited without details"),
    (r"\bclearly\b|\bobvious(?:ly)?\b|\beasy to see\b", 10, "implicit proof step"),
    (
        r"\bfollows from\b|\bby (?:the )?(?:theorem|lemma|corollary)\b",
        10,
        "external lemma dependency",
    ),
    (
        r"\bcompactness\b|\btightness\b|\bweak convergence\b",
        9,
        "analysis/probability compactness machinery",
    ),
    (r"\bdual(?:ity)?\b|\bpolar\b|\bseminorm\b", 9, "functional-analytic structure"),
    (
        r"\bmeasure\b|\bprobability\b|\bgaussian\b|\bradon\b",
        8,
        "measure/probability concepts",
    ),
    (
        r"\btopolog(?:y|ical)\b|\bmetrizable\b|\bcomplete\b",
        7,
        "topological assumptions",
    ),
    (r"\bthere exists\b|\bchoose\b|\bconstruct\b", 5, "existence/construction step"),
    (r"\biff\b|\bequivalent\b|\bif and only if\b", 6, "bidirectional expansion needed"),
    (
        r"\\cite|\\ref|\\label|\\begin\{theorem\}|\\begin\{lemma\}",
        8,
        "citation or theorem environment",
    ),
]

LOW_PATTERNS = [
    (r"\bdefinition\b|\bdenote\b|\bwrite\b", -4, "mostly definitional"),
    (r"\bassume\b|\blet\b", -2, "explicit binder setup"),
    (r"\bdirect\b|\bimmediate\b", -2, "claimed direct step"),
]

SEARCH_TRIGGERS = [
    r"\bstandard\b",
    r"\bwell[- ]known\b",
    r"\\cite",
    r"\bfollows from\b",
    r"\bSazonov\b|\bMinlos\b|\bBochner\b|\bProkhorov\b|\bHille\b|\bYosida\b",
    r"\bgaussian\b|\bradon\b|\bcylindrical\b|\bnuclear\b",
]


@dataclass
class SegmentEstimate:
    """Document the responsibility of ``SegmentEstimate``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Group related state and behavior so callers can use this part of the skills/autoformalization/proof-expansion-difficulty-estimator/scripts workflow through a clear object boundary.

    Function:
        Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    index: int
    text: str
    token_count: int
    difficulty_score: int
    difficulty_band: str
    reasons: List[str]
    web_search_recommended: bool
    search_priority: str
    suggested_queries: List[str]


def normalize_latex(text: str) -> str:
    """Document the responsibility of ``normalize_latex``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_latex`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = re.sub(r"(?<!\\)%.*", " ", text)
    text = re.sub(r"\\begin\{proof\}|\\end\{proof\}", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text: str) -> List[str]:
    """Document the responsibility of ``split_sentences``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``split_sentences`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    normalized = normalize_latex(text)
    if not normalized:
        return []
    pieces = re.split(r"(?<=[.!?])\s+(?=[A-Z\\])|(?:\n\s*\n)+", normalized)
    out: List[str] = []
    for piece in pieces:
        stripped = piece.strip()
        if stripped:
            out.append(stripped)
    return out


def chunk_segments(sentences: Sequence[str], max_words: int) -> List[str]:
    """Document the responsibility of ``chunk_segments``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``chunk_segments`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    segments: List[str] = []
    current: List[str] = []
    current_words = 0
    for sentence in sentences:
        words = re.findall(r"\S+", sentence)
        if current and current_words + len(words) > max_words:
            segments.append(" ".join(current).strip())
            current = []
            current_words = 0
        current.append(sentence)
        current_words += len(words)
    if current:
        segments.append(" ".join(current).strip())
    return segments


def band(score: int) -> str:
    """Document the responsibility of ``band``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``band`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if score >= 80:
        return "research"
    if score >= 60:
        return "hard"
    if score >= 35:
        return "moderate"
    return "easy"


def priority(score: int, web_search_recommended: bool) -> str:
    """Document the responsibility of ``priority``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``priority`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not web_search_recommended:
        return "none"
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    return "medium"


def extract_query_terms(text: str) -> List[str]:
    """Document the responsibility of ``extract_query_terms``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_query_terms`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    raw_terms = re.findall(r"[A-Z][A-Za-z0-9-]+|[a-z][A-Za-z0-9-]{5,}", text)
    stop = {
        "Assume",
        "Then",
        "Since",
        "Therefore",
        "Suppose",
        "Let",
        "Proof",
        "Theorem",
        "Lemma",
    }
    terms: List[str] = []
    for term in raw_terms:
        clean = term.strip("-")
        if clean in stop:
            continue
        if clean.lower() in {"therefore", "suppose", "definition", "standard"}:
            continue
        if clean not in terms:
            terms.append(clean)
    return terms[:8]


def suggested_queries(text: str) -> List[str]:
    """Document the responsibility of ``suggested_queries``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``suggested_queries`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    terms = extract_query_terms(text)
    quoted = " ".join(terms[:5]).strip()
    queries: List[str] = []
    if quoted:
        queries.append(f"{quoted} theorem proof")
        queries.append(f"{quoted} definition assumptions")
    title_like = re.findall(
        r"\b(?:Sazonov|Minlos|Bochner|Prokhorov|Hille|Yosida)\b", text
    )
    for name in title_like:
        q = f"{name} theorem proof statement"
        if q not in queries:
            queries.insert(0, q)
    if not queries:
        compact = " ".join(re.findall(r"[A-Za-z][A-Za-z0-9-]+", text)[:8])
        if compact:
            queries.append(f"{compact} proof details")
    return queries[:4]


def estimate_segment(index: int, text: str) -> SegmentEstimate:
    """Document the responsibility of ``estimate_segment``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``estimate_segment`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    token_count = len(re.findall(r"\S+", text))
    score = min(30, token_count // 4)
    reasons: List[str] = []
    _lower_text = text.lower()

    for pattern, delta, reason in HARD_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            score += delta
            reasons.append(reason)
    for pattern, delta, reason in LOW_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            score += delta
            reasons.append(reason)

    symbol_count = len(
        re.findall(r"[∀∃∑∫≤≥→↔]|\\(?:forall|exists|sum|int|le|ge|to|iff)\b", text)
    )
    if symbol_count >= 4:
        score += min(16, symbol_count * 2)
        reasons.append("dense symbolic content")

    citation_count = len(re.findall(r"\\cite|\\ref|\[[0-9, ]+\]", text))
    if citation_count:
        score += min(15, citation_count * 5)
        reasons.append("citation/reference lookup likely needed")

    search_triggered = any(
        re.search(pattern, text, flags=re.IGNORECASE) for pattern in SEARCH_TRIGGERS
    )
    score = max(0, min(100, score))
    web_search_recommended = search_triggered or score >= 65
    if not reasons:
        reasons.append("low-risk explicit proof text")

    return SegmentEstimate(
        index=index,
        text=text,
        token_count=token_count,
        difficulty_score=score,
        difficulty_band=band(score),
        reasons=sorted(set(reasons)),
        web_search_recommended=web_search_recommended,
        search_priority=priority(score, web_search_recommended),
        suggested_queries=suggested_queries(text) if web_search_recommended else [],
    )


def estimate_proof(text: str, *, max_words_per_segment: int) -> Dict[str, Any]:
    """Document the responsibility of ``estimate_proof``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``estimate_proof`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    segments = chunk_segments(split_sentences(text), max_words_per_segment)
    estimates = [
        estimate_segment(index=idx, text=segment)
        for idx, segment in enumerate(segments, start=1)
    ]
    if not estimates:
        return {
            "segment_count": 0,
            "max_difficulty_score": 0,
            "mean_difficulty_score": None,
            "web_search_recommended_count": 0,
            "segments": [],
        }
    scores = [item.difficulty_score for item in estimates]
    return {
        "segment_count": len(estimates),
        "max_difficulty_score": max(scores),
        "mean_difficulty_score": round(sum(scores) / len(scores), 2),
        "web_search_recommended_count": sum(
            1 for item in estimates if item.web_search_recommended
        ),
        "segments": [asdict(item) for item in estimates],
    }


def append_reasoning_event(
    path: Optional[Path],
    *,
    step: str,
    payload: Dict[str, Any],
) -> None:
    """Document the responsibility of ``append_reasoning_event``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``append_reasoning_event`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if path is None:
        return
    append_reasoning_log_entry(path, step=step, payload=payload)


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
    parser.add_argument("--proof-file", type=Path)
    parser.add_argument("--proof-text")
    parser.add_argument("--max-words-per-segment", type=int, default=80)
    parser.add_argument("--reasoning-log-file", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def read_text(args: argparse.Namespace) -> str:
    """Document the responsibility of ``read_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if args.proof_text:
        return args.proof_text
    if args.proof_file is not None:
        return args.proof_file.read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def render_text(report: Dict[str, Any]) -> str:
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
    lines = [
        f"Segments: {report['segment_count']}",
        f"Max difficulty: {report['max_difficulty_score']}",
        f"Mean difficulty: {report['mean_difficulty_score']}",
        f"Web-search recommended: {report['web_search_recommended_count']}",
    ]
    for segment in report["segments"]:
        lines.append(
            f"\n[{segment['index']}] {segment['difficulty_band']} "
            f"({segment['difficulty_score']}/100), search={segment['search_priority']}"
        )
        lines.append(segment["text"])
        lines.append("Reasons: " + "; ".join(segment["reasons"]))
        if segment["suggested_queries"]:
            lines.append("Queries:")
            lines.extend(f"- {query}" for query in segment["suggested_queries"])
    return "\n".join(lines)


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
    text = read_text(args)
    append_reasoning_event(
        args.reasoning_log_file,
        step="proof_expansion_difficulty_start",
        payload={
            "skill": "proof-expansion-difficulty-estimator",
            "hook_id": "preformalization.expansion_difficulty",
            "has_proof_text": bool(text.strip()),
            "max_words_per_segment": args.max_words_per_segment,
        },
    )
    report = estimate_proof(text, max_words_per_segment=args.max_words_per_segment)
    append_reasoning_event(
        args.reasoning_log_file,
        step="proof_expansion_difficulty_complete",
        payload={
            "skill": "proof-expansion-difficulty-estimator",
            "hook_id": "preformalization.expansion_difficulty",
            "summary": {
                "segment_count": report["segment_count"],
                "max_difficulty_score": report["max_difficulty_score"],
                "web_search_recommended_count": report["web_search_recommended_count"],
            },
        },
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
