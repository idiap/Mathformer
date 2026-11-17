#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Gate MathformerPhysicsLib coherence using deterministic and generative critics."""

from __future__ import annotations

from typing import Any

import argparse
import json
from pathlib import Path
import sys

SCRIPT_ROOT = (
    Path(__file__).resolve().parents[2]
    / "mathformerphysicslib-coherence-inventory-builder"
    / "scripts"
)
sys.path.insert(0, str(SCRIPT_ROOT))

from coherence_common import (  # noqa: E402 - direct-script path setup above
    audit_grounding,
    build_inventory,
    canonicalize,
    coherence_gate,
    critic_api,
    critic_integration,
    critic_redefinitions,
    load_json,
    markdown_report,
    repair_plan,
    self_test_payload,
    write_json,
)


def default_reports(self_test: bool = False) -> list[dict[str, Any]]:
    inventory = self_test_payload() if self_test else build_inventory()
    graph = canonicalize(inventory)
    grounding = audit_grounding(graph)
    return [
        grounding,
        critic_redefinitions(graph, grounding),
        critic_integration(inventory, graph),
        critic_api(graph),
    ]


def parse_options(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", type=Path, default=[])
    parser.add_argument("--repair-plan", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--require-release",
        action="store_true",
        help="Exit nonzero unless the diagnostic gate also authorizes release.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    return {
        key: (
            [str(p) for p in value]
            if key == "report"
            else str(value) if isinstance(value, Path) else value
        )
        for key, value in vars(args).items()
    }


def load_reports(args: dict[str, Any]) -> list[dict[str, Any]]:
    return [load_json(Path(path)) for path in args["report"]]


def load_repairs(args: dict[str, Any]) -> dict[str, Any]:
    return load_json(Path(args["repair_plan"]))


def aggregate(reports: list[dict[str, Any]], repairs: dict[str, Any]) -> dict[str, Any]:
    payload = coherence_gate(reports)
    payload["repair_plan_status"] = repairs.get("status")
    payload["repair_action_count"] = len(repairs.get("actions", []))
    return payload


def emit_return(
    args: dict[str, Any], repairs: dict[str, Any], payload: dict[str, Any]
) -> int:
    if args["output"]:
        write_json(payload, Path(args["output"]))
    if args["markdown_output"]:
        output = Path(args["markdown_output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown_report(payload, repairs), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return (
        0 if (not args["require_release"] or payload.get("release_ok") is True) else 3
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_options(argv)
    reports = (
        load_reports(args) if args["report"] else default_reports(args["self_test"])
    )
    repairs = load_repairs(args) if args["repair_plan"] else repair_plan(reports)
    payload = aggregate(reports, repairs)
    return emit_return(args, repairs, payload)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
