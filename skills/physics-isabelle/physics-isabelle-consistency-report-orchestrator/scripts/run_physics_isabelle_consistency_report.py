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

"""Aggregate Isabelle/HOL physics consistency evidence."""

from __future__ import annotations
from tempfile import gettempdir

import argparse
import json
from pathlib import Path
from typing import Any, Sequence


def load_json(path: Path | None) -> dict[str, Any]:
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
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_report(
    *,
    execution_report: dict[str, Any],
    type_packet: dict[str, Any],
    assumption_packet: dict[str, Any],
    background_packet: dict[str, Any] | None = None,
    physics_review: dict[str, Any],
    mathematical_review: dict[str, Any],
    realness_ok: bool,
    anchor_ok: bool,
) -> dict[str, Any]:
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
    blockers: list[str] = []
    warnings: list[str] = []
    execution_ok = (
        bool(execution_report.get("ok", False)) if execution_report else False
    )
    placeholder = (
        execution_report.get("placeholder_report", {}) if execution_report else {}
    )
    placeholder_free = (
        bool(placeholder.get("placeholder_free", False)) if placeholder else False
    )
    if not execution_ok:
        blockers.append("isabelle_execution_failed")
    if execution_report and not placeholder_free:
        blockers.append("isabelle_placeholders_present")
    if not realness_ok:
        blockers.append("realness_failed")
    if not anchor_ok:
        blockers.append("source_anchor_failed")
    if not type_packet:
        blockers.append("missing_physics_isabelle_type_packet")
    if not assumption_packet:
        blockers.append("missing_physics_isabelle_assumption_packet")
    background_items = []
    open_background = []
    if background_packet:
        background_items = background_packet.get("background_items", [])
        if not isinstance(background_items, list):
            background_items = []
        open_background = [
            item
            for item in background_items
            if isinstance(item, dict)
            and str(item.get("formalization_status", "needs_autoformalization"))
            not in {
                "formalized",
                "isabelle_reused",
                "isarmathlib_reused",
                "mathformer_reused",
                "blocked",
                "not_required",
                "complete",
            }
        ]
        if open_background:
            blockers.append("open_isabelle_background_formalization_obligations")
    physics_status = (
        physics_review.get("status", "missing") if physics_review else "missing"
    )
    math_status = (
        mathematical_review.get("status", "missing")
        if mathematical_review
        else "missing"
    )
    if physics_status in {"fail", "missing"}:
        blockers.append(f"physics_review_{physics_status}")
    elif physics_status == "warn":
        warnings.append("physics_review_warn")
    if math_status in {"fail", "missing"}:
        blockers.append(f"mathematical_review_{math_status}")
    elif math_status == "warn":
        warnings.append("mathematical_review_warn")
    physics_properties = (
        physics_review.get("reviewed_properties", {}) if physics_review else {}
    )
    grounding_level = physics_properties.get(
        "isabelle_library_grounding_level", "missing"
    )
    if physics_review.get("style") == "physics_isabelle_final_hypothesis_review":
        if grounding_level in {"low", "medium"}:
            blockers.append(f"isabelle_library_grounding_{grounding_level}")
        elif grounding_level == "missing":
            blockers.append("isabelle_library_grounding_missing")
    if execution_report and execution_report.get("isabelle_bin") is None:
        warnings.append("isabelle_binary_missing_or_unavailable")
    status = "complete" if not blockers else "blocked"
    if (
        blockers
        and anchor_ok
        and realness_ok
        and (execution_report or type_packet or assumption_packet)
    ):
        status = "draft"
    return {
        "style": "isabelle_physics_consistency_report",
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "evidence": {
            "execution_ok": execution_ok,
            "placeholder_free": placeholder_free,
            "realness_ok": realness_ok,
            "anchor_ok": anchor_ok,
            "type_packet_present": bool(type_packet),
            "assumption_packet_present": bool(assumption_packet),
            "background_packet_present": bool(background_packet),
            "background_item_count": len(background_items),
            "open_background_item_count": len(open_background),
            "physics_review_status": physics_status,
            "mathematical_review_status": math_status,
            "isabelle_library_grounding_level": grounding_level,
            "isabelle_native_surface_count": physics_properties.get(
                "isabelle_native_surface_count"
            ),
            "local_scaffold_count": physics_properties.get("local_scaffold_count"),
            "isabelle_bin": (
                execution_report.get("isabelle_bin") if execution_report else None
            ),
        },
        "lean_flow_isolation": {
            "status": "no_lean_hook_or_artifact_required",
            "protected_lean_outputs": [
                "artifacts/physics_lean",
                "backends/lean/Mathformer/*.lean",
                "skills/physics-lean-*",
            ],
        },
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
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
    parser.add_argument("--execution-report", type=Path)
    parser.add_argument("--type-packet", type=Path)
    parser.add_argument("--assumption-packet", type=Path)
    parser.add_argument("--background-packet", type=Path)
    parser.add_argument("--physics-review", type=Path)
    parser.add_argument("--mathematical-review", type=Path)
    parser.add_argument("--realness-ok", action="store_true")
    parser.add_argument("--anchor-ok", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
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
        report = build_report(
            execution_report={
                "ok": True,
                "placeholder_report": {"placeholder_free": True},
                "isabelle_bin": str(
                    Path(gettempdir()) / "mathformer-test-fixtures/usr/bin/isabelle"
                ),
            },
            type_packet={"style": "isabelle_physics_type_system_packet"},
            assumption_packet={"style": "isabelle_physics_assumption_context_packet"},
            background_packet={},
            physics_review={
                "style": "physics_isabelle_final_hypothesis_review",
                "status": "pass",
                "reviewed_properties": {"isabelle_library_grounding_level": "high"},
            },
            mathematical_review={
                "style": "mathematical_isabelle_final_hypothesis_review",
                "status": "pass",
            },
            realness_ok=True,
            anchor_ok=True,
        )
        assert report["status"] == "complete"
        grounding_report = build_report(
            execution_report={
                "ok": True,
                "placeholder_report": {"placeholder_free": True},
                "isabelle_bin": str(
                    Path(gettempdir()) / "mathformer-test-fixtures/usr/bin/isabelle"
                ),
            },
            type_packet={"style": "isabelle_physics_type_system_packet"},
            assumption_packet={"style": "isabelle_physics_assumption_context_packet"},
            background_packet={},
            physics_review={
                "style": "physics_isabelle_final_hypothesis_review",
                "status": "pass",
                "reviewed_properties": {"isabelle_library_grounding_level": "medium"},
            },
            mathematical_review={
                "style": "mathematical_isabelle_final_hypothesis_review",
                "status": "pass",
            },
            realness_ok=True,
            anchor_ok=True,
        )
        assert grounding_report["status"] == "draft"
        assert "isabelle_library_grounding_medium" in grounding_report["blockers"]
        background_report = build_report(
            execution_report={
                "ok": True,
                "placeholder_report": {"placeholder_free": True},
                "isabelle_bin": str(
                    Path(gettempdir()) / "mathformer-test-fixtures/usr/bin/isabelle"
                ),
            },
            type_packet={"style": "isabelle_physics_type_system_packet"},
            assumption_packet={"style": "isabelle_physics_assumption_context_packet"},
            background_packet={
                "background_items": [
                    {
                        "id": "bg.isabelle_calculus_rules",
                        "formalization_status": "needs_autoformalization",
                    }
                ]
            },
            physics_review={
                "style": "physics_isabelle_final_hypothesis_review",
                "status": "pass",
                "reviewed_properties": {"isabelle_library_grounding_level": "high"},
            },
            mathematical_review={
                "style": "mathematical_isabelle_final_hypothesis_review",
                "status": "pass",
            },
            realness_ok=True,
            anchor_ok=True,
        )
        assert background_report["status"] == "draft"
        assert (
            "open_isabelle_background_formalization_obligations"
            in background_report["blockers"]
        )
    else:
        report = build_report(
            execution_report=load_json(args.execution_report),
            type_packet=load_json(args.type_packet),
            assumption_packet=load_json(args.assumption_packet),
            background_packet=load_json(args.background_packet),
            physics_review=load_json(args.physics_review),
            mathematical_review=load_json(args.mathematical_review),
            realness_ok=args.realness_ok,
            anchor_ok=args.anchor_ok,
        )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
