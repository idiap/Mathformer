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

"""Localize main theoretical results and support units in a paper layout packet."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Sequence

THEORY_SECTIONS = re.compile(
    r"\b(theor|analysis|main result|method|preliminar|guarantee|bound|scaling)\b", re.I
)
RESULT_ROLES = {"theorem", "proposition", "corollary"}
SUPPORT_ROLES = {"definition", "assumption", "lemma", "equation", "proof"}
CONCEPT_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_\-]{3,}\b")
STOPWORDS = {
    "assumption",
    "bounded",
    "combining",
    "definition",
    "enough",
    "follows",
    "lemma",
    "network",
    "paper",
    "proof",
    "result",
    "theorem",
    "under",
    "when",
    "with",
}


def now() -> str:
    """Document the responsibility of ``now``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``now`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return datetime.now(timezone.utc).isoformat()


def label_for(block: Dict[str, Any]) -> str:
    """Document the responsibility of ``label_for``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``label_for`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = str(block.get("text", ""))
    match = re.search(
        r"\b(Definition|Assumption|Theorem|Proposition|Lemma|Corollary)\s+([A-Z]?[0-9]+(?:\.[0-9]+)*)",
        text,
        re.I,
    )
    if match:
        return f"{match.group(1).title()} {match.group(2)}"
    roles = block.get("role_hints") or []
    return str(roles[0]).title() if roles else "Unit"


def concept_terms(text: str, limit: int = 12) -> List[str]:
    """Document the responsibility of ``concept_terms``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``concept_terms`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    counts = Counter(
        token.lower()
        for token in CONCEPT_RE.findall(text)
        if token.lower() not in STOPWORDS and not token.isdigit()
    )
    return [term for term, _ in counts.most_common(limit)]


def result_score(block: Dict[str, Any], index: int, total: int) -> int:
    """Document the responsibility of ``result_score``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``result_score`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    roles = set(block.get("role_hints") or [])
    text = str(block.get("text", ""))
    section = str(block.get("section", ""))
    score = 0
    if roles & RESULT_ROLES:
        score += 50
    if "theorem" in roles:
        score += 20
    if THEORY_SECTIONS.search(section):
        score += 15
    if re.search(
        r"\b(rate|risk|bound|convergen|sample|complexity|scaling|guarantee|minimax|approximation)\b",
        text,
        re.I,
    ):
        score += 15
    if re.search(r"\bmain\b", text + " " + section, re.I):
        score += 10
    if total and index / max(total, 1) < 0.75:
        score += 5
    return score


def cited_references(
    citations: Sequence[str], references: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``cited_references``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``cited_references`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    result: List[Dict[str, Any]] = []
    for citation in citations:
        needle = citation.strip("[] ")
        for ref in references:
            text = str(ref.get("text", ""))
            if needle and (
                text.startswith(f"[{needle}]")
                or needle in str(ref.get("citations", []))
            ):
                result.append({"citation": citation, "reference": ref})
                break
        else:
            result.append(
                {
                    "citation": citation,
                    "reference": None,
                    "warning": "citation not resolved",
                }
            )
    return result


def localize(layout: Dict[str, Any], *, max_main_results: int = 5) -> Dict[str, Any]:
    """Document the responsibility of ``localize``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``localize`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    blocks = list(layout.get("blocks") or [])
    references = list(layout.get("references") or [])
    total = len(blocks)
    candidates: List[Dict[str, Any]] = []
    support_units: List[Dict[str, Any]] = []
    warnings: List[str] = list(layout.get("warnings") or [])

    for idx, block in enumerate(blocks):
        roles = set(block.get("role_hints") or [])
        score = result_score(block, idx, total)
        base = {
            "id": block.get("id"),
            "label": label_for(block),
            "section": block.get("section"),
            "source_span": block.get("text"),
            "role_hints": sorted(roles),
            "citations": block.get("citations") or [],
            "mathlib_concepts": concept_terms(str(block.get("text", ""))),
        }
        if roles & RESULT_ROLES:
            candidates.append(
                {
                    **base,
                    "main_theory_score": score,
                    "selected_as_main": False,
                    "downstream_routes": [
                        "result-existence-precheck-orchestrator",
                        "source-formalizable-unit-extractor",
                        "mathlib-concept-candidate-mapper",
                    ],
                }
            )
        elif roles & SUPPORT_ROLES:
            support_kind = (
                "proof" if "proof" in roles else sorted(roles & SUPPORT_ROLES)[0]
            )
            support_units.append(
                {
                    **base,
                    "support_kind": support_kind,
                    "downstream_routes": [
                        "latex-prerequisite-expander",
                        (
                            "proof-expansion-support-orchestrator"
                            if "proof" in roles
                            else "mathlib-concept-candidate-mapper"
                        ),
                    ],
                }
            )

    candidates.sort(key=lambda item: (-int(item["main_theory_score"]), str(item["id"])))
    main_results = candidates[:max_main_results]
    selected_ids = {item["id"] for item in main_results}
    for item in main_results:
        item["selected_as_main"] = True

    selected_positions = [
        idx for idx, block in enumerate(blocks) if block.get("id") in selected_ids
    ]
    cutoff = max(selected_positions) if selected_positions else min(len(blocks), 12)
    expansion_queue: List[Dict[str, Any]] = []
    for unit in support_units:
        try:
            pos = next(
                idx for idx, block in enumerate(blocks) if block.get("id") == unit["id"]
            )
        except StopIteration:
            pos = 0
        if pos <= cutoff or unit["support_kind"] in {
            "proof",
            "lemma",
            "assumption",
            "definition",
        }:
            expansion_queue.append(
                {
                    "unit_id": unit["id"],
                    "label": unit["label"],
                    "kind": unit["support_kind"],
                    "reason": "needed before selected main result or proof support",
                    "source_span": unit["source_span"],
                    "downstream_routes": unit["downstream_routes"],
                }
            )
    for result in main_results:
        expansion_queue.append(
            {
                "unit_id": result["id"],
                "label": result["label"],
                "kind": "main_result",
                "reason": "selected paper-level theorem-like drafting target",
                "source_span": result["source_span"],
                "downstream_routes": result["downstream_routes"],
            }
        )

    all_citations: List[str] = []
    for item in [*main_results, *support_units]:
        for citation in item.get("citations", []):
            if citation not in all_citations:
                all_citations.append(citation)
    reference_support = cited_references(all_citations, references)
    concepts: List[str] = []
    for item in [*main_results, *support_units]:
        for concept in item.get("mathlib_concepts", []):
            if concept not in concepts:
                concepts.append(concept)

    if not main_results:
        warnings.append("no theorem-like main result was localized")
    return {
        "generated_at_utc": now(),
        "source": layout.get("source", {}),
        "main_results": main_results,
        "support_units": support_units,
        "intermediate_expansion_queue": expansion_queue,
        "reference_support": reference_support,
        "mathlib_concepts": concepts[:40],
        "downstream_routes": sorted(
            {
                route
                for item in [*main_results, *support_units]
                for route in item.get("downstream_routes", [])
            }
        ),
        "warnings": warnings,
    }


def layout_from_text(text: str) -> Dict[str, Any]:
    """Document the responsibility of ``layout_from_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``layout_from_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".txt", delete=False
    ) as handle:
        handle.write(text)
        path = Path(handle.name)
    try:
        script = (
            Path(__file__).resolve().parents[2]
            / "paper-docling-layout-extractor"
            / "scripts"
            / "extract_paper_layout.py"
        )
        proc = subprocess.run(
            [sys.executable, str(script), "--text-file", str(path), "--json"],
            text=True,
            capture_output=True,
            timeout=30,
        )
        if proc.returncode != 0:
            raise SystemExit(proc.stderr or proc.stdout)
        return json.loads(proc.stdout)
    finally:
        path.unlink(missing_ok=True)


def sample_text() -> str:
    """Document the responsibility of ``sample_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``sample_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return """
Scaling Laws for Transformer Neural Networks

Abstract
We study statistical and approximation rates.

3 Main theoretical results
Definition 3.1. A distribution has intrinsic dimension d when its support has a d-dimensional parametrization.

Assumption 3.2. The regression function is smooth and the data are independent.

Theorem 3.3. Under Assumption 3.2, the excess risk is bounded by C n^{-2s/(2s+d)} up to logarithmic factors.

Proof. Combine Lemma 3.4 with the approximation theorem of Yarotsky [1].

Lemma 3.4. The transformer approximation error is bounded by epsilon for sufficiently large width.

References
[1] Yarotsky. Error bounds for approximations with deep ReLU networks. Neural Networks, 2017.
"""


def self_test_report() -> Dict[str, Any]:
    """Document the responsibility of ``self_test_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``self_test_report`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    report = localize(layout_from_text(sample_text()))
    ok = (
        bool(report["main_results"])
        and bool(report["intermediate_expansion_queue"])
        and any(
            item["kind"] == "lemma" for item in report["intermediate_expansion_queue"]
        )
    )
    report["self_test"] = {"ok": ok}
    return report


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
    parser.add_argument("--layout-json")
    parser.add_argument("--text")
    parser.add_argument("--text-file")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--expect-main-kind", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


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
    return "\n".join(
        [
            f"main_results: {len(report['main_results'])}",
            f"support_units: {len(report['support_units'])}",
            f"intermediate_expansion_queue: {len(report['intermediate_expansion_queue'])}",
            f"reference_support: {len(report['reference_support'])}",
        ]
    )


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
        report = self_test_report()
    elif args.layout_json:
        report = localize(
            json.loads(Path(args.layout_json).read_text(encoding="utf-8"))
        )
    elif args.text_file:
        report = localize(
            layout_from_text(Path(args.text_file).read_text(encoding="utf-8"))
        )
    elif args.text:
        report = localize(layout_from_text(args.text))
    else:
        raise SystemExit("Provide --layout-json, --text-file, --text, or --self-test.")

    if args.expect_main_kind:
        found = {
            role
            for result in report["main_results"]
            for role in result.get("role_hints", [])
        }
        expected = set(args.expect_main_kind)
        report["expected_main_kind_check"] = {
            "expected": sorted(expected),
            "found": sorted(found),
            "ok": expected <= found,
            "missing": sorted(expected - found),
        }
    ok = bool(report.get("self_test", {}).get("ok", True)) and bool(
        report.get("expected_main_kind_check", {}).get("ok", True)
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
