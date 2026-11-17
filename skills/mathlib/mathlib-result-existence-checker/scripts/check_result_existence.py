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

"""Check whether a target result already exists before autoformalization."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
MATHFORMERLIB_REGISTRY_SCRIPTS = (
    REPO_ROOT
    / "skills"
    / "mathformerlib"
    / "mathformerlib-registry-manager"
    / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))
if str(MATHFORMERLIB_REGISTRY_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(MATHFORMERLIB_REGISTRY_SCRIPTS))

from reasoning_log import (
    append_reasoning_log_entry,
)
from manage_mathformerlib_registry import (
    build_registry,
)

SKILL_NAME = "mathlib-result-existence-checker"
HOOK_ID = "mathlib.result_existence_search"
WEB_HOOK_ID = "mathlib.web_strategy"

STOPWORDS = {
    "about",
    "after",
    "all",
    "also",
    "and",
    "any",
    "are",
    "assume",
    "before",
    "being",
    "begin",
    "between",
    "can",
    "date",
    "document",
    "documentclass",
    "each",
    "end",
    "every",
    "exists",
    "finite",
    "fontenc",
    "for",
    "from",
    "geometry",
    "given",
    "have",
    "hyperref",
    "inputenc",
    "into",
    "item",
    "itemize",
    "let",
    "lmodern",
    "maketitle",
    "margin",
    "mathlib",
    "only",
    "proof",
    "result",
    "section",
    "sets",
    "show",
    "subsection",
    "such",
    "that",
    "the",
    "then",
    "theorem",
    "there",
    "this",
    "title",
    "usepackage",
    "utf8",
    "with",
}


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


def read_inputs(args: argparse.Namespace) -> str:
    """Document the responsibility of ``read_inputs``.

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
    for path in args.statement_file or []:
        chunks.append((REPO_ROOT / path).read_text(encoding="utf-8"))
    chunks.extend(args.statement or [])
    if not chunks and args.concept:
        chunks.append(" ".join(args.concept))
    if not chunks and args.expected_name:
        chunks.append(" ".join(args.expected_name))
    return "\n".join(chunk.strip() for chunk in chunks if chunk.strip())


def split_camel(text: str) -> str:
    """Document the responsibility of ``split_camel``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``split_camel`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    return text


def tokens(text: str) -> List[str]:
    """Document the responsibility of ``tokens``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``tokens`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    expanded = split_camel(text.replace("_", " ").replace(".", " "))
    found = re.findall(r"[A-Za-z][A-Za-z0-9'-]{1,}", expanded)
    normalized: List[str] = []
    for token in found:
        item = token.strip("'-").lower()
        if len(item) < 3 or item in STOPWORDS:
            continue
        normalized.append(item)
    return normalized


def target_tokens(
    statement: str,
    concepts: Sequence[str],
    expected_names: Sequence[str],
) -> List[str]:
    """Document the responsibility of ``target_tokens``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``target_tokens`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    all_tokens = tokens(" ".join([statement, *concepts, *expected_names]))
    seen: set[str] = set()
    ordered: List[str] = []
    for token in all_tokens:
        if token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def command_json(
    cmd: Sequence[str], *, timeout_sec: int
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Document the responsibility of ``command_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``command_json`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            list(cmd),
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        meta = {
            "cmd": list(cmd),
            "returncode": proc.returncode,
            "duration_ms": duration_ms,
            "stderr": proc.stderr[-2000:],
        }
        if proc.returncode != 0:
            return None, {**meta, "ok": False, "stdout": proc.stdout[-2000:]}
        return json.loads(proc.stdout), {**meta, "ok": True}
    except subprocess.TimeoutExpired as exc:
        return None, {
            "cmd": list(cmd),
            "returncode": None,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "ok": False,
            "timeout": True,
            "stderr": (exc.stderr or f"timeout after {timeout_sec}s")[-2000:],
        }
    except Exception as exc:
        return None, {
            "cmd": list(cmd),
            "returncode": None,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "ok": False,
            "error": str(exc),
        }


def run_mathlib_search(
    *,
    statement: str,
    concepts: Sequence[str],
    top_k: int,
    top_modules: int,
    timeout_sec: int,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Document the responsibility of ``run_mathlib_search``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    script = (
        REPO_ROOT
        / "skills"
        / "mathlib"
        / "informal-proof-mathlib-concepts"
        / "scripts"
        / "map_mathlib_concepts.py"
    )
    cmd = [
        "python3",
        rel(script),
        "--top-k",
        str(top_k),
        "--top-modules",
        str(top_modules),
        "--json",
    ]
    for concept in concepts:
        cmd.extend(["--concept", concept])
    if statement:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            suffix=".txt",
            prefix="mathformer-result-existence-",
            delete=False,
        ) as handle:
            handle.write(statement)
            proof_path = Path(handle.name)
        try:
            cmd.extend(["--proof-file", str(proof_path)])
            return command_json(cmd, timeout_sec=timeout_sec)
        finally:
            proof_path.unlink(missing_ok=True)
    return command_json(cmd, timeout_sec=timeout_sec)


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


def collect_mathlib_candidates(
    map_json: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``collect_mathlib_candidates``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``collect_mathlib_candidates`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not isinstance(map_json, dict):
        return []
    rows: List[Dict[str, Any]] = []
    for node in walk_json(map_json):
        if not isinstance(node, dict):
            continue
        qualified = node.get("qualified_name")
        if not isinstance(qualified, str) or not qualified:
            continue
        rows.append(
            {
                "library": "mathlib",
                "name": str(node.get("name") or qualified),
                "qualified_name": qualified,
                "kind": str(node.get("kind") or ""),
                "module": str(node.get("module") or node.get("import") or ""),
                "import": str(node.get("import") or ""),
                "source_ref": str(node.get("source_ref") or ""),
                "signature": str(node.get("signature") or ""),
                "source_excerpt": str(node.get("source_excerpt") or ""),
                "raw_score": node.get("score"),
            }
        )
    return dedupe_candidates(rows)


def dedupe_candidates(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``dedupe_candidates``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``dedupe_candidates`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    seen: set[Tuple[str, str]] = set()
    deduped: List[Dict[str, Any]] = []
    for row in rows:
        key = (str(row.get("library", "")), str(row.get("qualified_name", "")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(dict(row))
    return deduped


def run_mathformerlib_search(
    roots: Sequence[Path],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Document the responsibility of ``run_mathformerlib_search``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    started = time.perf_counter()
    try:
        registry = build_registry(roots)
        rows: List[Dict[str, Any]] = []
        status_by_path = {
            module["path"]: module["status"]
            for module in registry.get("modules", [])
            if isinstance(module, dict)
        }
        for module in registry.get("modules", []):
            if not isinstance(module, dict):
                continue
            status = str(module.get("status") or "")
            for decl in module.get("declarations", []):
                if not isinstance(decl, dict):
                    continue
                rows.append(
                    {
                        "library": "MathformerLib",
                        "status": status_by_path.get(str(decl.get("path")), status),
                        "name": str(decl.get("name") or ""),
                        "qualified_name": str(decl.get("qualified_name") or ""),
                        "kind": str(decl.get("kind") or ""),
                        "module": str(decl.get("module") or ""),
                        "import": str(decl.get("module") or ""),
                        "source_ref": str(decl.get("source_ref") or ""),
                        "signature": str(decl.get("signature") or ""),
                    }
                )
        return rows, {
            "ok": True,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "registry_summary": registry.get("summary", {}),
        }
    except Exception as exc:
        return [], {
            "ok": False,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "error": str(exc),
        }


def normalized_name(name: str) -> str:
    """Document the responsibility of ``normalized_name``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalized_name`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return re.sub(r"\s+", "", name.strip().lower())


def score_candidate(
    row: Dict[str, Any],
    *,
    target: Sequence[str],
    expected_names: Sequence[str],
) -> Dict[str, Any]:
    """Document the responsibility of ``score_candidate``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``score_candidate`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    qname = str(row.get("qualified_name") or row.get("name") or "")
    text = " ".join(
        str(row.get(key) or "")
        for key in ("qualified_name", "name", "signature", "source_excerpt", "module")
    )
    row_tokens = set(tokens(text))
    target_set = set(target)
    overlap = sorted(row_tokens & target_set)
    exact = False
    suffix = False
    qnorm = normalized_name(qname)
    for expected in expected_names:
        enorm = normalized_name(expected)
        if qnorm == enorm:
            exact = True
            break
        if qnorm.endswith("." + enorm) or qnorm.endswith(enorm):
            suffix = True
    raw = row.get("raw_score")
    raw_bonus = 0
    if isinstance(raw, (int, float)):
        raw_bonus = min(int(raw) // 8, 12)
    name_tokens = set(tokens(qname))
    name_overlap = sorted(name_tokens & target_set)
    score = len(overlap) * 4 + len(name_overlap) * 6 + raw_bonus
    match_kind = "token_overlap" if overlap else "weak_candidate"
    if suffix:
        score += 75
        match_kind = "expected_name_suffix"
    if exact:
        score += 100
        match_kind = "exact_expected_name"
    confidence = min(round(score / 100, 3), 0.99)
    if exact:
        confidence = 0.99
    elif suffix:
        confidence = max(confidence, 0.9)
    elif score >= 45:
        confidence = max(confidence, 0.7)
    return {
        **row,
        "score": score,
        "confidence": confidence,
        "match_kind": match_kind,
        "matched_target_tokens": overlap[:12],
    }


def rank_candidates(
    rows: Sequence[Dict[str, Any]],
    *,
    target: Sequence[str],
    expected_names: Sequence[str],
    top_k: int,
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``rank_candidates``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``rank_candidates`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    scored = [
        score_candidate(row, target=target, expected_names=expected_names)
        for row in rows
    ]
    useful = [
        row
        for row in scored
        if row["match_kind"] != "weak_candidate" or row["score"] >= 20
    ]
    useful.sort(
        key=lambda row: (
            -int(row.get("score", 0)),
            str(row.get("library") or ""),
            str(row.get("qualified_name") or ""),
        )
    )
    return useful[:top_k]


def run_web_plan(
    *,
    statement: str,
    concepts: Sequence[str],
    timeout_sec: int,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Document the responsibility of ``run_web_plan``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    script = (
        REPO_ROOT
        / "skills"
        / "mathlib"
        / "mathlib-web-search-strategist"
        / "scripts"
        / "plan_mathlib_web_search.py"
    )
    cmd = [sys.executable, rel(script), "--json"]
    for concept in concepts:
        cmd.extend(["--concept", concept])
    if statement:
        cmd.extend(["--text", statement])
    return command_json(cmd, timeout_sec=timeout_sec)


def decide_gate(
    candidates: Sequence[Dict[str, Any]],
    *,
    web_enabled: bool,
    web_confirmed_absent: bool,
) -> Dict[str, Any]:
    """Document the responsibility of ``decide_gate``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``decide_gate`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    exact = [
        item
        for item in candidates
        if item.get("match_kind") in {"exact_expected_name", "expected_name_suffix"}
    ]
    strong = [item for item in candidates if int(item.get("score", 0)) >= 45]
    if exact:
        return {
            "status": "likely_existing",
            "decision": "reuse_existing_result",
            "drafting_allowed": False,
            "reason": "An expected declaration name already resolves in a searched library.",
        }
    if strong:
        return {
            "status": "candidate_overlap",
            "decision": "manual_verify_before_drafting",
            "drafting_allowed": False,
            "reason": "Local search found overlapping declaration candidates that must be ruled out.",
        }
    if web_enabled and not web_confirmed_absent:
        return {
            "status": "needs_web_confirmation",
            "decision": "run_mathlib_web_search_before_drafting",
            "drafting_allowed": False,
            "reason": "Local search found no strong duplicate, but official-source web search has not been confirmed absent.",
        }
    return {
        "status": "not_found",
        "decision": "proceed_to_autoformalization",
        "drafting_allowed": True,
        "reason": "No duplicate candidates were found in the configured search surfaces.",
    }


def build_report(
    *,
    statement: str,
    concepts: Sequence[str],
    expected_names: Sequence[str],
    include_mathlib: bool,
    include_mathformerlib: bool,
    include_web_plan: bool,
    web_confirmed_absent: bool,
    include_roots: Sequence[Path],
    top_k: int,
    top_modules: int,
    timeout_sec: int,
    reasoning_log: Optional[Path],
) -> Dict[str, Any]:
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
    append_event(
        reasoning_log,
        "result_existence_search_start",
        {
            "concept_count": len(concepts),
            "expected_name_count": len(expected_names),
            "include_mathlib": include_mathlib,
            "include_mathformerlib": include_mathformerlib,
            "include_web_plan": include_web_plan,
        },
    )
    findings: List[Dict[str, Any]] = []
    all_rows: List[Dict[str, Any]] = []
    mathlib_map: Optional[Dict[str, Any]] = None
    mathlib_meta: Dict[str, Any] = {"enabled": include_mathlib}
    if include_mathlib:
        mathlib_map, mathlib_meta = run_mathlib_search(
            statement=statement,
            concepts=concepts,
            top_k=max(top_k, 8),
            top_modules=top_modules,
            timeout_sec=timeout_sec,
        )
        if not mathlib_meta.get("ok"):
            findings.append(
                {
                    "severity": "medium",
                    "code": "mathlib_internal_search_failed",
                    "message": "Local mathlib concept search failed; use web and manual verification before drafting.",
                    "detail": mathlib_meta.get("error") or mathlib_meta.get("stderr"),
                }
            )
        mathlib_rows = collect_mathlib_candidates(mathlib_map)
        all_rows.extend(mathlib_rows)
        append_event(
            reasoning_log,
            "result_existence_mathlib_search_complete",
            {"ok": bool(mathlib_meta.get("ok")), "candidate_count": len(mathlib_rows)},
        )
    mathformerlib_rows: List[Dict[str, Any]] = []
    mathformerlib_meta: Dict[str, Any] = {"enabled": include_mathformerlib}
    if include_mathformerlib:
        mathformerlib_rows, mathformerlib_meta = run_mathformerlib_search(include_roots)
        if not mathformerlib_meta.get("ok"):
            findings.append(
                {
                    "severity": "medium",
                    "code": "mathformerlib_registry_search_failed",
                    "message": "MathformerLib registry search failed; do not claim absence from MathformerLib.",
                    "detail": mathformerlib_meta.get("error"),
                }
            )
        all_rows.extend(mathformerlib_rows)
        append_event(
            reasoning_log,
            "result_existence_mathformerlib_search_complete",
            {
                "ok": bool(mathformerlib_meta.get("ok")),
                "candidate_count": len(mathformerlib_rows),
            },
        )
    target = target_tokens(statement, concepts, expected_names)
    ranked = rank_candidates(
        all_rows,
        target=target,
        expected_names=expected_names,
        top_k=top_k,
    )
    web_plan: Optional[Dict[str, Any]] = None
    web_meta: Dict[str, Any] = {"enabled": include_web_plan}
    if include_web_plan:
        web_plan, web_meta = run_web_plan(
            statement=statement,
            concepts=concepts or target[:6],
            timeout_sec=timeout_sec,
        )
        if not web_meta.get("ok"):
            findings.append(
                {
                    "severity": "medium",
                    "code": "mathlib_web_plan_failed",
                    "message": "Web-search plan generation failed; actual official-source search is still required before drafting.",
                    "detail": web_meta.get("error") or web_meta.get("stderr"),
                }
            )
        append_event(
            reasoning_log,
            "result_existence_web_plan_complete",
            {
                "ok": bool(web_meta.get("ok")),
                "task_count": ((web_plan or {}).get("summary") or {}).get("task_count"),
            },
        )
    gate = decide_gate(
        ranked,
        web_enabled=include_web_plan,
        web_confirmed_absent=web_confirmed_absent,
    )
    blocking_findings = [
        item for item in findings if str(item.get("severity")) in {"high", "critical"}
    ]
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": not blocking_findings,
        "status": gate["status"],
        "gate": gate,
        "inputs": {
            "statement_preview": statement[:500],
            "concepts": list(concepts),
            "expected_names": list(expected_names),
            "target_tokens": target[:24],
            "web_confirmed_absent": web_confirmed_absent,
        },
        "summary": {
            "mathlib_candidate_count": len(collect_mathlib_candidates(mathlib_map)),
            "mathformerlib_declaration_count": len(mathformerlib_rows),
            "ranked_candidate_count": len(ranked),
            "web_plan_task_count": ((web_plan or {}).get("summary") or {}).get(
                "task_count", 0
            ),
            "finding_count": len(findings),
            "drafting_allowed": gate["drafting_allowed"],
        },
        "mathlib_internal_search": {
            "enabled": include_mathlib,
            "meta": mathlib_meta,
            "candidate_count": len(collect_mathlib_candidates(mathlib_map)),
        },
        "mathformerlib_search": {
            "enabled": include_mathformerlib,
            "meta": mathformerlib_meta,
            "declaration_count": len(mathformerlib_rows),
        },
        "top_candidates": ranked,
        "web_search_plan": {
            "enabled": include_web_plan,
            "hook_id": WEB_HOOK_ID,
            "meta": web_meta,
            "source_priority": (web_plan or {}).get("source_priority", []),
            "search_tasks": (web_plan or {}).get("search_tasks", [])[:8],
            "acceptance": {
                "retrieval_aids_are_candidate_only": True,
                "official_docs_or_source_required": True,
                "local_lean_verification_required_before_reuse": True,
            },
        },
        "findings": findings,
    }
    append_event(
        reasoning_log,
        "result_existence_search_complete",
        {
            "status": report["status"],
            "decision": gate["decision"],
            "drafting_allowed": gate["drafting_allowed"],
            "ranked_candidate_count": len(ranked),
        },
    )
    return report


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
    common = {
        "include_mathlib": False,
        "include_mathformerlib": True,
        "include_roots": [Path("MathformerLib"), Path("libraries/MathformerLib.lean")],
        "top_k": 8,
        "top_modules": 8,
        "timeout_sec": 30,
        "reasoning_log": None,
    }
    existing = build_report(
        statement="Truth is derivable in the MathformerLib seed library.",
        concepts=[],
        expected_names=["MathformerLib.true_intro"],
        include_web_plan=False,
        web_confirmed_absent=False,
        **common,
    )
    absent = build_report(
        statement="Every zorbledorf manifold is chromatic over a glim field.",
        concepts=["zorbledorf manifold", "glim field"],
        expected_names=[],
        include_web_plan=False,
        web_confirmed_absent=False,
        **common,
    )
    web_required = build_report(
        statement="Every zorbledorf manifold is chromatic over a glim field.",
        concepts=["zorbledorf manifold", "glim field"],
        expected_names=[],
        include_web_plan=True,
        web_confirmed_absent=False,
        **common,
    )
    checks = [
        {
            "id": "detects_mathformerlib_existing_result",
            "ok": existing["status"] == "likely_existing"
            and existing["gate"]["decision"] == "reuse_existing_result",
        },
        {
            "id": "allows_absent_when_web_disabled",
            "ok": absent["status"] == "not_found"
            and absent["gate"]["drafting_allowed"] is True,
        },
        {
            "id": "requires_web_confirmation_by_default",
            "ok": web_required["status"] == "needs_web_confirmation"
            and web_required["gate"]["drafting_allowed"] is False,
        },
    ]
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": all(item["ok"] for item in checks),
        "checks": checks,
        "reports": {
            "existing_status": existing["status"],
            "absent_status": absent["status"],
            "web_required_status": web_required["status"],
        },
    }


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
    if "checks" in report:
        lines = [f"ok: {report['ok']}"]
        for check in report["checks"]:
            status = "PASS" if check["ok"] else "FAIL"
            lines.append(f"- {status} {check['id']}")
        return "\n".join(lines)
    lines = [
        f"ok: {report['ok']}",
        f"status: {report['status']}",
        f"decision: {report['gate']['decision']}",
        f"drafting_allowed: {report['gate']['drafting_allowed']}",
    ]
    for candidate in report["top_candidates"][:10]:
        lines.append(
            "- {library} {qualified_name} score={score} match={match_kind} ref={source_ref}".format(
                **candidate
            )
        )
    for finding in report["findings"]:
        lines.append(f"! {finding['severity']} {finding['code']}: {finding['message']}")
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
    parser.add_argument("--statement", action="append", default=[])
    parser.add_argument("--statement-file", action="append", type=Path, default=[])
    parser.add_argument("--concept", action="append", default=[])
    parser.add_argument("--expected-name", action="append", default=[])
    parser.add_argument("--include-root", action="append", type=Path, default=[])
    parser.add_argument("--top-k", type=int, default=12)
    parser.add_argument("--top-modules", type=int, default=12)
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--no-mathlib", action="store_true")
    parser.add_argument("--no-mathformerlib", action="store_true")
    parser.add_argument("--no-web-plan", action="store_true")
    parser.add_argument(
        "--web-confirmed-absent",
        action="store_true",
        help="Set only after official mathlib docs/source web search found no duplicate result.",
    )
    parser.add_argument("--expect-existing", action="store_true")
    parser.add_argument("--expect-not-found", action="store_true")
    parser.add_argument("--expect-web-required", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--reasoning-log-file", type=Path)
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
        report = run_self_test()
    else:
        statement = read_inputs(args)
        roots = args.include_root or [
            Path("MathformerLib"),
            Path("libraries/MathformerLib.lean"),
        ]
        reasoning_log = (
            (REPO_ROOT / args.reasoning_log_file).resolve()
            if args.reasoning_log_file
            else None
        )
        try:
            report = build_report(
                statement=statement,
                concepts=args.concept,
                expected_names=args.expected_name,
                include_mathlib=not args.no_mathlib,
                include_mathformerlib=not args.no_mathformerlib,
                include_web_plan=not args.no_web_plan,
                web_confirmed_absent=args.web_confirmed_absent,
                include_roots=roots,
                top_k=args.top_k,
                top_modules=args.top_modules,
                timeout_sec=args.timeout_sec,
                reasoning_log=reasoning_log,
            )
        except Exception as exc:
            append_event(
                reasoning_log,
                "result_existence_search_error",
                {"error": str(exc)},
            )
            raise
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    if args.expect_existing and report.get("status") != "likely_existing":
        return 4
    if args.expect_not_found and report.get("status") != "not_found":
        return 5
    if args.expect_web_required and report.get("status") != "needs_web_confirmation":
        return 6
    return 0 if report.get("ok") else 3


if __name__ == "__main__":
    sys.exit(main())
