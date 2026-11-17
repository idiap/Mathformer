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

"""Search local Isabelle/HOL and optional IsarMathLib theory trees."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from typing import Any, Dict, Iterable, List, Optional
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]


def default_roots() -> List[Path]:
    """Document the responsibility of ``default_roots``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``default_roots`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    roots: List[Path] = []
    isabelle_home = os.environ.get("ISABELLE_HOME")
    if isabelle_home:
        roots.append(Path(isabelle_home).expanduser().resolve() / "src" / "HOL")
    external_root = os.environ.get("ISARMATHLIB_HOME")
    roots.append(
        Path(external_root).expanduser()
        if external_root
        else Path.home() / ".local" / "share" / "mathformer" / "IsarMathLib"
    )
    return roots


def iter_theories(roots: Iterable[Path]) -> Iterable[Path]:
    """Document the responsibility of ``iter_theories``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``iter_theories`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    seen = set()
    for raw_root in roots:
        root = raw_root if raw_root.is_absolute() else REPO_ROOT / raw_root
        if not root.exists():
            continue
        for path in root.rglob("*.thy"):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield path


def score_line(line: str, concept: str) -> int:
    """Document the responsibility of ``score_line``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``score_line`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    hay = line.lower()
    needle = concept.lower()
    if needle in hay:
        return 4
    tokens = re.split(r"[\s_\\<>'\"().,:;+-]+", needle)
    return sum(1 for token in tokens if token and token in hay)


def search(
    concepts: List[str], roots: List[Path], *, max_matches: int
) -> Dict[str, Any]:
    """Document the responsibility of ``search``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    theories = list(iter_theories(roots))
    concept_reports = []
    for concept in concepts:
        matches = []
        for theory in theories:
            try:
                lines = theory.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            theory_score = 0
            snippets = []
            for index, line in enumerate(lines, start=1):
                line_score = score_line(line, concept)
                if line_score <= 0:
                    continue
                theory_score += line_score
                if len(snippets) < 4:
                    snippets.append(
                        {"line": index, "text": line.strip(), "score": line_score}
                    )
            if theory_score:
                matches.append(
                    {
                        "theory_file": str(theory),
                        "theory_name": theory.stem,
                        "score": theory_score,
                        "snippets": snippets,
                    }
                )
        matches.sort(key=lambda item: (-int(item["score"]), item["theory_file"]))
        concept_reports.append(
            {
                "concept": concept,
                "match_count": len(matches),
                "matches": matches[:max_matches],
                "proposed_imports": [
                    item["theory_name"] for item in matches[: min(3, max_matches)]
                ],
            }
        )
    return {
        "schema_version": 1,
        "skill": "isarmathlib-grounding-navigator",
        "hook_id": "isabelle.grounding.search",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "roots": [str(root) for root in roots],
        "available_roots": [
            str(root)
            for root in roots
            if (root if root.is_absolute() else REPO_ROOT / root).exists()
        ],
        "theory_count": len(theories),
        "concepts": concept_reports,
        "ok": True,
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
    fixture_dir = REPO_ROOT / "artifacts/isabelle_wiki_level/grounding_fixture"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture = fixture_dir / "Fixture.thy"
    fixture.write_text(
        "theory Fixture imports Main begin\n\nlemma injective_composition: True by simp\n\nend\n",
        encoding="utf-8",
    )
    report = search(["injective composition"], [fixture_dir], max_matches=5)
    checks = {
        "found_fixture": bool(report["concepts"][0]["matches"]),
        "proposes_fixture": "Fixture" in report["concepts"][0]["proposed_imports"],
    }
    with TemporaryDirectory(prefix="mathformer-isarmathlib-") as directory:
        external_root = Path(directory)
        (external_root / "ExternalFixture.thy").write_text(
            "theory ExternalFixture imports ZF begin\nend\n", encoding="utf-8"
        )
        with patch.dict(os.environ, {"ISARMATHLIB_HOME": directory}):
            roots = default_roots()
            external_report = search(["ExternalFixture"], roots, max_matches=5)
        checks["configured_external_root"] = external_root in roots
        checks["finds_external_theory"] = any(
            Path(match["theory_file"]).parent == external_root
            for match in external_report["concepts"][0]["matches"]
        )
        checks["no_bundled_default_roots"] = all(
            root.is_absolute() and not root.is_relative_to(REPO_ROOT) for root in roots
        )
    return {"ok": all(checks.values()), "checks": checks, "report": report}


def main(argv: Optional[list[str]] = None) -> int:
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concept", action="append", default=[])
    parser.add_argument(
        "--root",
        type=Path,
        action="append",
        default=[],
        help="Theory root; defaults to installed Isabelle/HOL and external IsarMathLib.",
    )
    parser.add_argument("--max-matches", type=int, default=8)
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        payload = self_test()
    else:
        concepts = args.concept or ["injective", "composition"]
        roots = args.root or default_roots()
        payload = search(concepts, roots, max_matches=args.max_matches)
        if args.output_file is not None:
            args.output_file.parent.mkdir(parents=True, exist_ok=True)
            args.output_file.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )

    if args.json or args.self_test:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"searched {len(payload.get('concepts', []))} concepts")
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
