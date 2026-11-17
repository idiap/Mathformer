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

"""Build a paper-level main-theory autoformalization plan."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
LAYOUT_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "paper"
    / "paper-docling-layout-extractor"
    / "scripts"
    / "extract_paper_layout.py"
)
LOCALIZER_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "paper"
    / "paper-main-theory-localizer"
    / "scripts"
    / "localize_paper_theory.py"
)


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


def run_json(cmd: Sequence[str], *, allow_failure: bool = False) -> Dict[str, Any]:
    """Document the responsibility of ``run_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    proc = subprocess.run(
        list(cmd),
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=120,
    )
    if proc.returncode != 0 and not allow_failure:
        raise SystemExit(proc.stderr or proc.stdout)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "error": "command did not emit JSON",
            "cmd": list(cmd),
            "returncode": proc.returncode,
            "stdout": proc.stdout[-2000:],
            "stderr": proc.stderr[-2000:],
        }


def extract_layout(args: argparse.Namespace) -> Dict[str, Any]:
    """Document the responsibility of ``extract_layout``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_layout`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    cmd = [sys.executable, str(LAYOUT_SCRIPT), "--json"]
    if args.url:
        cmd.extend(["--url", args.url])
    elif args.pdf_file:
        cmd.extend(["--pdf-file", args.pdf_file])
    elif args.text_file:
        cmd.extend(["--text-file", args.text_file])
    elif args.text:
        cmd.extend(["--text", args.text])
    else:
        raise SystemExit(
            "Provide --url, --pdf-file, --text-file, --text, or --self-test."
        )
    if args.title:
        cmd.extend(["--title", args.title])
    return run_json(cmd, allow_failure=True)


def localize_theory(layout: Dict[str, Any]) -> Dict[str, Any]:
    """Document the responsibility of ``localize_theory``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``localize_theory`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".json", delete=False
    ) as handle:
        json.dump(layout, handle)
        path = Path(handle.name)
    try:
        return run_json(
            [
                sys.executable,
                str(LOCALIZER_SCRIPT),
                "--layout-json",
                str(path),
                "--json",
            ]
        )
    finally:
        path.unlink(missing_ok=True)


def expansion_kind_route(kind: str) -> List[str]:
    """Document the responsibility of ``expansion_kind_route``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``expansion_kind_route`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if kind == "main_result":
        return [
            "result-existence-precheck-orchestrator",
            "source-formalizable-unit-extractor",
            "mathlib-concept-candidate-mapper",
            "latex-prerequisite-expander",
        ]
    if kind == "proof":
        return [
            "proof-expansion-difficulty-estimator",
            "proof-expansion-support-orchestrator",
        ]
    if kind in {"definition", "assumption", "lemma", "proposition", "corollary"}:
        return ["latex-prerequisite-expander", "mathlib-concept-candidate-mapper"]
    return ["latex-prerequisite-expander"]


def enrich_expansion_queue(localization: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``enrich_expansion_queue``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``enrich_expansion_queue`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    queue: List[Dict[str, Any]] = []
    seen = set()
    for index, item in enumerate(
        localization.get("intermediate_expansion_queue", []), start=1
    ):
        key = (item.get("unit_id"), item.get("kind"), item.get("source_span"))
        if key in seen:
            continue
        seen.add(key)
        kind = str(item.get("kind", "context"))
        text = str(item.get("source_span", ""))
        queue.append(
            {
                "order": index,
                "unit_id": item.get("unit_id"),
                "label": item.get("label"),
                "kind": kind,
                "source_span": text,
                "expansion_status": "pending_expansion",
                "requires_latex_expansion": kind != "proof",
                "requires_proof_support": kind == "proof" or "Proof" in text,
                "requires_result_existence_precheck": kind == "main_result",
                "requires_mathlib_grounding": kind != "proof",
                "downstream_routes": sorted(
                    set(item.get("downstream_routes", []) + expansion_kind_route(kind))
                ),
            }
        )
    return queue


def build_reference_packet(localization: Dict[str, Any]) -> Dict[str, Any]:
    """Document the responsibility of ``build_reference_packet``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    refs = localization.get("reference_support", [])
    unresolved = [
        ref for ref in refs if ref.get("reference") is None or ref.get("warning")
    ]
    return {
        "status": "complete" if not unresolved else "needs_reference_research",
        "reference_count": len(refs),
        "resolved_count": len(refs) - len(unresolved),
        "unresolved_count": len(unresolved),
        "items": refs,
        "downstream_routes": (
            [
                "proof-expansion-web-researcher",
                "proof-expansion-support-orchestrator",
            ]
            if refs
            else []
        ),
    }


def build_main_result_queue(
    localization: Dict[str, Any], expansion_queue: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``build_main_result_queue``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    dependencies = [
        item["unit_id"] for item in expansion_queue if item.get("kind") != "main_result"
    ]
    result_queue = []
    for index, result in enumerate(localization.get("main_results", []), start=1):
        result_queue.append(
            {
                "order": index,
                "unit_id": result.get("id"),
                "label": result.get("label"),
                "source_span": result.get("source_span"),
                "dependency_unit_ids": dependencies,
                "mathlib_concepts": result.get("mathlib_concepts", []),
                "citations": result.get("citations", []),
                "drafting_status": "blocked_until_intermediate_queue_expanded",
                "required_gates": [
                    "preformalization.result_existence_precheck",
                    "mathlib.discovery",
                    "mathlib.api_plan",
                    "preformalization.review.suite",
                    "draft.initial",
                    "execute.initial",
                ],
            }
        )
    return result_queue


def build_plan(
    layout: Dict[str, Any], localization: Optional[Dict[str, Any]] = None
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
    engine = layout.get("engine", {})
    if not engine.get("ok"):
        return {
            "generated_at_utc": now(),
            "status": "blocked",
            "layout_packet": layout,
            "theory_localization_packet": None,
            "expanded_intermediate_queue": [],
            "reference_support_packet": {
                "status": "blocked_until_layout_extraction",
                "items": [],
                "downstream_routes": [],
            },
            "main_result_drafting_queue": [],
            "blocked_or_unresolved_dependencies": [
                {
                    "kind": "paper_layout_extraction",
                    "reason": engine.get("details", "layout extraction failed"),
                    "warnings": layout.get("warnings", []),
                    "resolution": "Install docling for PDF layout extraction or provide extracted text with --text-file.",
                }
            ],
        }
    localization = localization or localize_theory(layout)
    expansion_queue = enrich_expansion_queue(localization)
    reference_packet = build_reference_packet(localization)
    main_queue = build_main_result_queue(localization, expansion_queue)
    unresolved = []
    if not main_queue:
        unresolved.append(
            {
                "kind": "main_result_localization",
                "reason": "no theorem-like main result was selected",
                "resolution": "Review layout sections and theorem-role detection.",
            }
        )
    if reference_packet["status"] != "complete":
        unresolved.append(
            {
                "kind": "reference_support",
                "reason": "some citations used by theory units were not resolved",
                "resolution": "Run proof-expansion-web-researcher or provide bibliography metadata.",
            }
        )
    return {
        "generated_at_utc": now(),
        "status": "ready_for_expansion" if not unresolved else "needs_support",
        "layout_packet": layout,
        "theory_localization_packet": localization,
        "expanded_intermediate_queue": expansion_queue,
        "reference_support_packet": reference_packet,
        "main_result_drafting_queue": main_queue,
        "blocked_or_unresolved_dependencies": unresolved,
    }


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
Paper Title

Abstract
We establish a statistical scaling law for transformer estimators.

3 Main Results
Definition 3.1. A data distribution has intrinsic dimension d when its support admits a d-dimensional parametrization.

Assumption 3.2. Samples are independent and the target function is smooth.

Theorem 3.3. Under Assumption 3.2, the excess risk is bounded by C n^{-2s/(2s+d)} up to logarithmic factors.

Proof. The result follows from Lemma 3.4 and the approximation theorem of Yarotsky [1].

Lemma 3.4. The approximation error is at most epsilon for sufficiently large width.

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

    class Args(argparse.Namespace):
        """Document the responsibility of ``self_test_report.Args``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Group related state and behavior so callers can use this part of the skills/paper/paper-theory-autoformalization-orchestrator/scripts workflow through a clear object boundary.

        Function:
            Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

        Maintenance:
            Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
        """

        url = None
        pdf_file = None
        text_file = None
        text = sample_text()
        title = "Self-test paper"

    layout = extract_layout(Args())
    plan = build_plan(layout)
    ok = (
        plan["status"] in {"ready_for_expansion", "needs_support"}
        and bool(plan["main_result_drafting_queue"])
        and any(
            item["kind"] == "definition" for item in plan["expanded_intermediate_queue"]
        )
        and any(item["kind"] == "lemma" for item in plan["expanded_intermediate_queue"])
        and plan["reference_support_packet"]["reference_count"] >= 1
    )
    plan["self_test"] = {"ok": ok}
    return plan


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
    parser.add_argument("--pdf-file")
    parser.add_argument("--text-file")
    parser.add_argument("--text")
    parser.add_argument("--title")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def render_text(plan: Dict[str, Any]) -> str:
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
            f"status: {plan['status']}",
            f"layout_engine: {plan['layout_packet'].get('engine', {}).get('name')}",
            f"main_results: {len(plan['main_result_drafting_queue'])}",
            f"intermediate_units: {len(plan['expanded_intermediate_queue'])}",
            f"references: {plan['reference_support_packet'].get('reference_count', 0)}",
            f"unresolved: {len(plan['blocked_or_unresolved_dependencies'])}",
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
    plan = self_test_report() if args.self_test else build_plan(extract_layout(args))
    ok = bool(plan.get("self_test", {}).get("ok", True)) and plan["status"] != "blocked"
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(render_text(plan))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
