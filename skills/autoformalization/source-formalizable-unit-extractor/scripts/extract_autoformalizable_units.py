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

"""Extract formalizable mathematical units from source text or a URL."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.request import Request, urlopen

SECTION_RE = re.compile(r"^\s{0,3}(?:#{1,6}\s*)?([A-Z][A-Za-z0-9 ,:;'\-/()]+)\s*$")
FORMULA_RE = re.compile(r"(\\\(|\\\[|\$\$?|≤|≥|∀|∃|∑|∫|:=|=|<|>|\\[a-zA-Z]+)")
TOKEN_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_\-]{2,}\b")

KIND_PATTERNS: List[Tuple[str, re.Pattern[str], str]] = [
    (
        "definition",
        re.compile(
            r"\b(is called|are called|called|defined|definition|denote|if and only if|iff)\b",
            re.I,
        ),
        "definition cue",
    ),
    (
        "theorem",
        re.compile(
            r"\b(theorem|proposition|criterion|states that|asserts that|holds iff)\b|^(Every|All)\b.+\b(is|are)\b",
            re.I,
        ),
        "theorem cue",
    ),
    (
        "lemma",
        re.compile(
            r"\b(lemma|property|satisfies|implies|equivalent|bounded by|closed under)\b",
            re.I,
        ),
        "lemma/property cue",
    ),
    (
        "corollary",
        re.compile(r"\b(corollary|therefore|hence|as a consequence)\b", re.I),
        "corollary cue",
    ),
    (
        "proof",
        re.compile(
            r"\b(proof|to prove|we prove|it follows|suppose|choose|let us show)\b", re.I
        ),
        "proof cue",
    ),
    (
        "example",
        re.compile(
            r"\b(example|counterexample|for instance|special case|non-example)\b", re.I
        ),
        "example cue",
    ),
    (
        "notation",
        re.compile(r"\b(notation|written|denoted|symbol|where)\b", re.I),
        "notation cue",
    ),
]

CONCEPT_STOPWORDS = {
    "and",
    "are",
    "called",
    "can",
    "defined",
    "every",
    "for",
    "from",
    "has",
    "have",
    "iff",
    "into",
    "let",
    "one",
    "only",
    "over",
    "proof",
    "such",
    "that",
    "the",
    "then",
    "there",
    "this",
    "was",
    "when",
    "where",
    "with",
}

NON_CONTENT_RE = re.compile(
    r"^(?:\^|Retrieved from|This page was last edited|Text is available|By using this site|Wikipedia"
    r"|Privacy policy|Terms of Use|Developers|Statistics|Cookie statement)"
    r"|(?:ISBN|doi\s*:|MR\s+[0-9]|arXiv|JSTOR|Springer-Verlag|American Mathematical Society)",
    re.I,
)

NON_CONTENT_SECTIONS = {
    "References",
    "Further reading",
    "External links",
    "See also",
    "Notes",
}


class TextHTMLParser(HTMLParser):
    """Document the responsibility of ``TextHTMLParser``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Group related state and behavior so callers can use this part of the skills/autoformalization/source-formalizable-unit-extractor/scripts workflow through a clear object boundary.

    Function:
        Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    def __init__(self) -> None:
        """Document the responsibility of ``TextHTMLParser.__init__``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Initialize instance state while keeping constructor assumptions explicit for future maintainers.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        super().__init__()
        self.parts: List[str] = []
        self.skip_depth = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        """Document the responsibility of ``TextHTMLParser.handle_starttag``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Parse caller-provided input into the structured representation expected by downstream code.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        _ = attrs  # HTMLParser requires this callback parameter.
        if tag in {"script", "style", "noscript", "table"}:
            self.skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in {"h1", "h2", "h3", "p", "li", "dt", "dd", "div"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        """Document the responsibility of ``TextHTMLParser.handle_endtag``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Parse caller-provided input into the structured representation expected by downstream code.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if tag in {"script", "style", "noscript", "table"} and self.skip_depth > 0:
            self.skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag in {"h1", "h2", "h3", "p", "li", "dt", "dd", "div"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        """Document the responsibility of ``TextHTMLParser.handle_data``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Parse caller-provided input into the structured representation expected by downstream code.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if self.skip_depth:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title:
            self.title += text
        self.parts.append(text)

    def text(self) -> str:
        """Document the responsibility of ``TextHTMLParser.text``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Parse caller-provided input into the structured representation expected by downstream code.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return re.sub(r"\n{3,}", "\n\n", " ".join(self.parts))


@dataclass
class Unit:
    """Document the responsibility of ``Unit``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Group related state and behavior so callers can use this part of the skills/autoformalization/source-formalizable-unit-extractor/scripts workflow through a clear object boundary.

    Function:
        Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    id: str
    kind: str
    section: str
    source_span: str
    statement: str
    formalization_signal: str
    proof_present: bool
    dependencies: List[str]
    mathlib_concepts: List[str]
    suggested_lean_surface: str
    priority: str
    downstream_routes: List[str]


def fetch_url(url: str, timeout: int = 20) -> Tuple[str, str]:
    """Document the responsibility of ``fetch_url``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``fetch_url`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    request = Request(url, headers={"User-Agent": "MathformerSourceUnitExtractor/1.0"})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        content_type = response.headers.get("content-type", "")
    text = raw.decode("utf-8", errors="replace")
    if "html" in content_type or "<html" in text[:1000].lower():
        parser = TextHTMLParser()
        parser.feed(text)
        title = parser.title.replace(" - Wikipedia", "").strip()
        return parser.text(), title
    return text, ""


def split_candidates(text: str) -> List[Tuple[str, str]]:
    """Document the responsibility of ``split_candidates``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``split_candidates`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    normalized = re.sub(r"\r\n?", "\n", text)
    raw_blocks = [
        block.strip()
        for block in re.split(r"\n\s*\n|(?<=[.!?])\s+(?=[A-Z])", normalized)
    ]
    section = "Lead"
    blocks: List[Tuple[str, str]] = []
    for block in raw_blocks:
        block = re.sub(r"\s+", " ", block).strip()
        if not block:
            continue
        if (
            len(block) <= 80
            and SECTION_RE.match(block)
            and not FORMULA_RE.search(block)
        ):
            section = block
            continue
        if section in NON_CONTENT_SECTIONS or NON_CONTENT_RE.search(block):
            continue
        if len(block) < 25:
            continue
        blocks.append((section, block))
    return blocks


def classify(block: str) -> Tuple[str, str]:
    """Document the responsibility of ``classify``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``classify`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    scores: Counter[str] = Counter()
    signals: List[str] = []
    for kind, pattern, signal in KIND_PATTERNS:
        if pattern.search(block):
            scores[kind] += 1
            signals.append(signal)
    if FORMULA_RE.search(block):
        scores["formula"] += 1
        signals.append("formula cue")
    if re.search(
        r"\b(if|whenever)\b.+\b(then|implies|there exists|there is)\b", block, re.I
    ):
        scores["theorem"] += 1
        signals.append("conditional statement cue")
    if re.search(
        r"\bcontinuous|compact|convex|metric|function|space|set|map|sequence\b",
        block,
        re.I,
    ):
        scores["prerequisite"] += 1
        signals.append("mathematical concept cue")
    if not scores:
        return "prerequisite", "mathematical context cue"
    order = [
        "definition",
        "theorem",
        "lemma",
        "corollary",
        "proof",
        "example",
        "formula",
        "notation",
        "prerequisite",
    ]
    best = max(order, key=lambda item: (scores[item], -order.index(item)))
    return best, ", ".join(dict.fromkeys(signals))


def concept_terms(block: str, limit: int = 10) -> List[str]:
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
    candidates = []
    for token in TOKEN_RE.findall(block):
        lower = token.lower().strip("-")
        if lower in CONCEPT_STOPWORDS or lower.isdigit():
            continue
        if lower.endswith("ly") and lower not in {"strongly", "weakly"}:
            continue
        candidates.append(lower)
    counts = Counter(candidates)
    ranked = sorted(
        counts, key=lambda item: (-counts[item], block.lower().find(item), item)
    )
    return ranked[:limit]


def lean_surface(kind: str) -> str:
    """Document the responsibility of ``lean_surface``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``lean_surface`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {
        "definition": "def",
        "theorem": "theorem",
        "lemma": "lemma",
        "corollary": "theorem",
        "proof": "context",
        "example": "example",
        "formula": "lemma",
        "notation": "context",
        "prerequisite": "context",
    }[kind]


def priority(kind: str, proof_present: bool, block: str) -> str:
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
    if kind in {"definition", "theorem"}:
        return "high"
    if kind in {"lemma", "corollary", "formula"}:
        return "high" if proof_present or len(block) < 350 else "medium"
    if kind in {"proof", "notation"}:
        return "medium"
    return "low"


def routes(kind: str) -> List[str]:
    """Document the responsibility of ``routes``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``routes`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    route_map = {
        "definition": [
            "latex-prerequisite-expander",
            "mathlib-concept-candidate-mapper",
        ],
        "theorem": [
            "result-existence-precheck-orchestrator",
            "mathlib-concept-candidate-mapper",
        ],
        "lemma": [
            "result-existence-precheck-orchestrator",
            "mathlib-concept-candidate-mapper",
        ],
        "corollary": [
            "result-existence-precheck-orchestrator",
            "mathlib-concept-candidate-mapper",
        ],
        "proof": [
            "proof-expansion-support-orchestrator",
            "proof-expansion-difficulty-estimator",
        ],
        "formula": ["latex-prerequisite-expander", "mathlib-concept-candidate-mapper"],
        "notation": ["latex-prerequisite-expander"],
        "example": ["latex-prerequisite-expander"],
        "prerequisite": [
            "latex-prerequisite-expander",
            "mathlib-concept-candidate-mapper",
        ],
    }
    return route_map[kind]


def dependencies_for(
    kind: str, units: Sequence[Unit], concepts: Sequence[str]
) -> List[str]:
    """Document the responsibility of ``dependencies_for``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``dependencies_for`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    deps: List[str] = []
    if kind in {"theorem", "lemma", "corollary", "proof", "formula"}:
        defs = [unit.id for unit in units if unit.kind == "definition"]
        deps.extend(defs[-3:])
    for concept in concepts[:4]:
        if concept not in deps:
            deps.append(concept)
    return deps[:8]


def extract_units(text: str, *, title: str, url: str) -> Dict[str, Any]:
    """Document the responsibility of ``extract_units``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_units`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    units: List[Unit] = []
    for section, block in split_candidates(text):
        kind, signal = classify(block)
        if kind == "prerequisite" and len(block) > 500 and not FORMULA_RE.search(block):
            continue
        proof_present = kind == "proof" or bool(
            re.search(
                r"\b(proof|it follows|suppose|choose|therefore|hence)\b", block, re.I
            )
        )
        concepts = concept_terms(block)
        unit = Unit(
            id=f"unit_{len(units) + 1:03d}",
            kind=kind,
            section=section,
            source_span=block[:900],
            statement=block[:500],
            formalization_signal=signal,
            proof_present=proof_present,
            dependencies=[],
            mathlib_concepts=concepts,
            suggested_lean_surface=lean_surface(kind),
            priority=priority(kind, proof_present, block),
            downstream_routes=routes(kind),
        )
        unit.dependencies = dependencies_for(kind, units, concepts)
        units.append(unit)

    kind_counts = Counter(unit.kind for unit in units)
    return {
        "source": {
            "title": title,
            "url": url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "summary": {
            "unit_count": len(units),
            "kind_counts": dict(sorted(kind_counts.items())),
            "high_priority_count": sum(1 for unit in units if unit.priority == "high"),
        },
        "units": [asdict(unit) for unit in units],
    }


def self_test() -> Dict[str, Any]:
    """Document the responsibility of ``self_test``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``self_test`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    sample = """
Lipschitz continuity

A function f from a metric space X to a metric space Y is called Lipschitz continuous if there exists a real constant K >= 0 such that d_Y(f(x), f(y)) <= K d_X(x, y) for all x and y in X.

Every Lipschitz continuous map between metric spaces is uniformly continuous.

Proof. If epsilon > 0, choose delta = epsilon / K when K is positive. Then d_X(x, y) < delta implies d_Y(f(x), f(y)) < epsilon.
"""
    report = extract_units(sample, title="Lipschitz continuity", url="self-test")
    kinds = {unit["kind"] for unit in report["units"]}
    text = " ".join(unit["source_span"].lower() for unit in report["units"])
    ok = (
        "definition" in kinds
        and "theorem" in kinds
        and "proof" in kinds
        and "lipschitz" in text
        and report["summary"]["high_priority_count"] >= 2
    )
    report["self_test"] = {"ok": ok}
    return report


def read_input(args: argparse.Namespace) -> Tuple[str, str, str]:
    """Document the responsibility of ``read_input``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    title = args.title or ""
    url = args.url or ""
    if args.self_test:
        return "", "self-test", "self-test"
    if args.url:
        text, fetched_title = fetch_url(args.url)
        return text, title or fetched_title or args.url, args.url
    if args.text_file:
        path = Path(args.text_file)
        return path.read_text(encoding="utf-8"), title or path.stem, url
    if args.text:
        return args.text, title, url
    raise SystemExit("Provide --url, --text-file, --text, or --self-test.")


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
        f"source: {report['source'].get('title') or report['source'].get('url')}",
        f"units: {report['summary']['unit_count']}",
        f"kinds: {report['summary']['kind_counts']}",
    ]
    for unit in report["units"]:
        lines.append(
            f"- {unit['id']} {unit['kind']} {unit['priority']} "
            f"[{unit['section']}]: {unit['source_span'][:120]}"
        )
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
    parser.add_argument("--url")
    parser.add_argument("--text-file")
    parser.add_argument("--text")
    parser.add_argument("--title")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--expect-kind", action="append", default=[])
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
        report = self_test()
    else:
        text, title, url = read_input(args)
        report = extract_units(text, title=title, url=url)
    expected = set(args.expect_kind)
    if expected:
        found = {unit["kind"] for unit in report["units"]}
        report["expected_kind_check"] = {
            "expected": sorted(expected),
            "found": sorted(found),
            "ok": expected <= found,
            "missing": sorted(expected - found),
        }
    ok = report.get("self_test", {}).get("ok", True)
    ok = ok and report.get("expected_kind_check", {}).get("ok", True)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
