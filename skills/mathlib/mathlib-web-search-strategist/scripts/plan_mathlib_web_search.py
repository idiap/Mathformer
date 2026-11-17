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

"""Plan official-source web searches that complement local mathlib search."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import quote_plus

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_NAME = "mathlib-web-search-strategist"
HOOK_ID = "mathlib.web_strategy"

STOPWORDS = {
    "about",
    "after",
    "all",
    "and",
    "are",
    "for",
    "from",
    "have",
    "into",
    "let",
    "mathlib",
    "proof",
    "show",
    "that",
    "then",
    "there",
    "theorem",
    "this",
    "with",
}

SOURCE_PRIORITY = [
    {
        "kind": "official_docs",
        "domain": "leanprover-community.github.io/mathlib4_docs",
        "use": "Confirm declarations, modules, imports, notation, theorem statements, and docstrings.",
    },
    {
        "kind": "official_source",
        "domain": "github.com/leanprover-community/mathlib4",
        "use": "Confirm source location, namespace, theorem shape, imports, and nearby declarations.",
    },
    {
        "kind": "retrieval_aid",
        "domain": "loogle.lean-lang.org",
        "use": "Discover candidate declarations only; corroborate elsewhere.",
    },
    {
        "kind": "retrieval_aid",
        "domain": "leansearch.net",
        "use": "Discover candidate declarations only; corroborate elsewhere.",
    },
]


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


def load_text(path: Optional[Path], inline_text: Optional[str]) -> str:
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
    chunks: List[str] = []
    if path:
        chunks.append(path.read_text(encoding="utf-8"))
    if inline_text:
        chunks.append(inline_text)
    return "\n".join(chunks)


def extract_terms(text: str, limit: int = 8) -> List[str]:
    """Document the responsibility of ``extract_terms``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_terms`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_'.-]{2,}", text)
    counts: Dict[str, int] = {}
    original: Dict[str, str] = {}
    for token in tokens:
        normalized = token.strip(".,;:()[]{}").lower()
        if normalized in STOPWORDS or len(normalized) < 3:
            continue
        counts[normalized] = counts.get(normalized, 0) + 1
        original.setdefault(normalized, token.strip(".,;:()[]{}"))
    ranked = sorted(counts, key=lambda key: (-counts[key], key))
    return [original[key] for key in ranked[:limit]]


def candidate_names(value: Any) -> List[str]:
    """Document the responsibility of ``candidate_names``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``candidate_names`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    names: List[str] = []
    if isinstance(value, dict):
        for key in ("qualified_name", "name", "declaration", "decl", "candidate"):
            item = value.get(key)
            if isinstance(item, str) and item:
                names.append(item)
        for key in ("candidates", "verified_candidates", "ranked_candidates"):
            item = value.get(key)
            if isinstance(item, list):
                for child in item:
                    names.extend(candidate_names(child))
    elif isinstance(value, list):
        for item in value:
            names.extend(candidate_names(item))
    return sorted(set(names))


def concept_from_item(item: Any) -> Optional[str]:
    """Document the responsibility of ``concept_from_item``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``concept_from_item`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("concept", "name", "term", "label", "surface"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def has_verified_candidate(item: Dict[str, Any]) -> bool:
    """Document the responsibility of ``has_verified_candidate``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_verified_candidate`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    candidates = item.get("candidates") or item.get("verified_candidates") or []
    if not isinstance(candidates, list):
        return False
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("check_ok") is True:
            return True
        local = candidate.get("local_verification")
        if isinstance(local, dict) and (
            local.get("check_ok") is True
            or local.get("verified") is True
            or str(local.get("status", "")).lower() in {"passed", "ok", "verified"}
        ):
            return True
    return False


def walk_json(value: Any) -> Iterable[Any]:
    """Document the responsibility of ``walk_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``walk_json`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def concepts_from_local_json(
    path: Optional[Path],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Document the responsibility of ``concepts_from_local_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``concepts_from_local_json`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not path:
        return [], []
    parsed = json.loads(path.read_text(encoding="utf-8"))
    records: List[Dict[str, Any]] = []
    findings: List[str] = []
    for node in walk_json(parsed):
        if not isinstance(node, dict):
            continue
        concept = concept_from_item(node)
        if not concept:
            continue
        looks_like_gap = any(
            key in node
            for key in (
                "candidates",
                "coverage_status",
                "gap",
                "gap_reason",
                "verified_candidates",
                "check_ok",
            )
        )
        if not looks_like_gap:
            continue
        status = str(node.get("coverage_status") or node.get("status") or "").lower()
        gap_reason = str(node.get("gap_reason") or node.get("gap") or "")
        verified = has_verified_candidate(node)
        if verified and status not in {
            "gap",
            "candidate_only",
            "unverified",
            "needs_web",
        }:
            continue
        records.append(
            {
                "concept": concept,
                "reason": gap_reason
                or status
                or "local search did not produce a verified candidate",
                "local_candidates": candidate_names(node)[:8],
            }
        )
    if not records:
        findings.append(f"No unresolved concept records found in {rel(path)}.")
    return records, findings


def search_urls(query: str) -> Dict[str, str]:
    """Document the responsibility of ``search_urls``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    encoded = quote_plus(query)
    github_query = quote_plus(f'repo:leanprover-community/mathlib4 "{query}"')
    return {
        "mathlib_docs_root": "https://leanprover-community.github.io/mathlib4_docs/",
        "github_code_search": f"https://github.com/search?q={github_query}&type=code",
        "loogle": f"https://loogle.lean-lang.org/?q={encoded}",
        "leansearch": f"https://leansearch.net/?q={encoded}",
    }


def candidate_evidence_targets(candidates: Sequence[str]) -> List[Dict[str, str]]:
    """Document the responsibility of ``candidate_evidence_targets``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``candidate_evidence_targets`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    targets: List[Dict[str, str]] = []
    for candidate in candidates[:8]:
        lean_name = candidate.strip()
        if not lean_name:
            continue
        targets.append(
            {
                "candidate": lean_name,
                "official_docs_query": (
                    f'site:leanprover-community.github.io/mathlib4_docs "{lean_name}"'
                ),
                "official_source_query": (
                    f'repo:leanprover-community/mathlib4 "{lean_name}"'
                ),
                "local_check": f"#check {lean_name}",
                "accept_as_grounded_only_if": (
                    "official docs/source corroborates the candidate and local Lean verification passes"
                ),
            }
        )
    return targets


def build_queries(concept: str, candidates: Sequence[str]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``build_queries``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    query_rows: List[Dict[str, Any]] = []
    base_queries = [
        f'site:leanprover-community.github.io/mathlib4_docs "{concept}" Mathlib',
        f'site:leanprover-community.github.io/mathlib4_docs "{concept}" "import Mathlib"',
        f'repo:leanprover-community/mathlib4 "{concept}"',
    ]
    for query in base_queries:
        query_rows.append(
            {
                "query": query,
                "domains": [
                    "leanprover-community.github.io",
                    "github.com",
                ],
                "urls": search_urls(concept),
            }
        )
    for candidate in candidates[:5]:
        exact_query = f'site:leanprover-community.github.io/mathlib4_docs "{candidate}"'
        query_rows.append(
            {
                "query": exact_query,
                "domains": ["leanprover-community.github.io"],
                "urls": search_urls(candidate),
            }
        )
    return query_rows


def build_plan(
    *,
    concepts: Sequence[str],
    text: str,
    local_records: Sequence[Dict[str, Any]],
    target: str,
) -> Dict[str, Any]:
    """Document the responsibility of ``build_plan``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    concept_records: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for record in local_records:
        concept = str(record["concept"]).strip()
        key = concept.lower()
        if key in seen:
            continue
        seen.add(key)
        concept_records.append(record)
    for concept in concepts:
        key = concept.lower()
        if key not in seen:
            seen.add(key)
            concept_records.append(
                {
                    "concept": concept,
                    "reason": "explicit user or workflow concept",
                    "local_candidates": [],
                }
            )
    if text and not concept_records:
        for term in extract_terms(text):
            key = term.lower()
            if key not in seen:
                seen.add(key)
                concept_records.append(
                    {
                        "concept": term,
                        "reason": "extracted from proof text",
                        "local_candidates": [],
                    }
                )

    tasks: List[Dict[str, Any]] = []
    for index, record in enumerate(concept_records, 1):
        concept = record["concept"]
        candidates = record.get("local_candidates") or []
        tasks.append(
            {
                "id": f"mathlib-web-{index:02d}",
                "concept": concept,
                "target": target,
                "priority": "P1" if candidates else "P2",
                "local_gap_reason": record.get("reason", ""),
                "local_candidate_names": candidates,
                "candidate_evidence_targets": candidate_evidence_targets(candidates),
                "queries": build_queries(concept, candidates),
                "acceptance_criteria": [
                    "An API claim is backed by official mathlib docs or official mathlib source.",
                    "Candidate declarations are locally checked with Lean before prompt injection.",
                    "Candidate imports pass import-context verification before final use.",
                    "Retrieval-aid hits are marked candidate-only until corroborated.",
                ],
                "local_verification_handoff": {
                    "candidate_verifier": "mathlib-candidate-verifier",
                    "import_context_verifier": "lean-import-context-verifier",
                    "import_planner": "mathlib-import-set-builder",
                },
            }
        )

    findings: List[Dict[str, Any]] = []
    if not tasks:
        findings.append(
            {
                "severity": "medium",
                "code": "no_web_search_targets",
                "message": "No concepts, local gaps, or useful proof terms were available for web planning.",
            }
        )
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": not any(item["severity"] == "high" for item in findings),
        "target": target,
        "source_priority": SOURCE_PRIORITY,
        "summary": {
            "task_count": len(tasks),
            "concept_count": len(concept_records),
            "finding_count": len(findings),
        },
        "search_tasks": tasks,
        "findings": findings,
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
    report = build_plan(
        concepts=["monotone composition"],
        text="",
        local_records=[
            {
                "concept": "compactness",
                "reason": "coverage gap",
                "local_candidates": ["IsCompact", "CompactSpace"],
            }
        ],
        target="declaration",
    )
    ok = (
        report["summary"]["task_count"] == 2
        and "leanprover-community.github.io"
        in report["search_tasks"][0]["queries"][0]["domains"]
        and report["search_tasks"][0]["candidate_evidence_targets"][0]["local_check"]
        == "#check IsCompact"
        and report["search_tasks"][0]["local_verification_handoff"][
            "candidate_verifier"
        ]
        == "mathlib-candidate-verifier"
    )
    report["self_test_ok"] = ok
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
    parser.add_argument(
        "--concept", action="append", default=[], help="Concept or API term to ground."
    )
    parser.add_argument(
        "--proof-file", type=Path, help="Proof or statement text to mine for terms."
    )
    parser.add_argument(
        "--text", help="Inline proof or statement text to mine for terms."
    )
    parser.add_argument(
        "--local-map-json",
        type=Path,
        help="Local concept-map, coverage, or gap report.",
    )
    parser.add_argument(
        "--target",
        default="declaration",
        choices=[
            "declaration",
            "module",
            "import",
            "notation",
            "theorem_shape",
            "api_convention",
        ],
    )
    parser.add_argument("--self-test", action="store_true")
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
    lines = [
        f"ok: {report['ok']}",
        f"tasks: {report['summary']['task_count']}",
        f"target: {report.get('target', 'declaration')}",
    ]
    for task in report.get("search_tasks", []):
        lines.append(f"- {task['id']} {task['concept']} ({task['priority']})")
        for query in task.get("queries", [])[:2]:
            lines.append(f"  query: {query['query']}")
    for finding in report.get("findings", []):
        lines.append(f"! {finding['severity']} {finding['code']}: {finding['message']}")
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
    if args.self_test:
        report = self_test()
    else:
        local_records, local_findings = concepts_from_local_json(args.local_map_json)
        text = load_text(args.proof_file, args.text)
        report = build_plan(
            concepts=args.concept,
            text=text,
            local_records=local_records,
            target=args.target,
        )
        for message in local_findings:
            report["findings"].append(
                {"severity": "low", "code": "local_map_note", "message": message}
            )
        report["summary"]["finding_count"] = len(report["findings"])
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    return 0 if report.get("ok") and report.get("self_test_ok", True) else 3


if __name__ == "__main__":
    sys.exit(main())
