#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Convert structured feature evidence into a paper revision plan without
#   drafting unsupported manuscript claims.
#
# Intent:
#   Route supported claims, non-claims, paper sections, and figures/tables into
#   a compact Markdown and JSON plan for paper-writing agents.
#
# Function:
#   Reads a new-functionality evidence packet and writes an update plan.
#
# Maintenance Notes:
#   Keep output fields aligned with the paper-functionality-update-orchestrator
#   skill output shape.

"""Plan manuscript updates from a paper evidence packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]


def load_packet(path: Path) -> dict[str, Any]:
    """Load a new-functionality evidence packet."""

    return json.loads(path.read_text(encoding="utf-8"))


def feature_list(packet: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize evidence packets to a feature list."""

    if "features" in packet:
        return list(packet["features"])
    return [packet]


def collect_unique(features: list[dict[str, Any]], key: str) -> list[str]:
    """Collect stable unique string values from feature packet lists."""

    values: list[str] = []
    seen: set[str] = set()
    for feature in features:
        for value in feature.get(key, []):
            if isinstance(value, dict):
                value = (
                    value.get("claim")
                    or value.get("path")
                    or json.dumps(value, sort_keys=True)
                )
            if value not in seen:
                seen.add(str(value))
                values.append(str(value))
    return values


def build_plan(packet: dict[str, Any]) -> dict[str, Any]:
    """Build a structured paper revision plan from feature evidence."""

    features = feature_list(packet)
    return {
        "schema_version": 1,
        "plan_type": "paper_update_plan",
        "feature_count": len(features),
        "features": [
            {
                "feature_id": feature.get(
                    "feature_id", feature.get("feature_name", "unknown")
                ),
                "feature_name": feature.get("feature_name", "unknown"),
                "summary": feature.get("feature_summary", ""),
                "supported_claim_count": len(feature.get("supported_paper_claims", [])),
                "non_claim_count": len(feature.get("explicit_non_claims", [])),
                "target_sections": feature.get("target_paper_sections", []),
                "figure_table_implications": feature.get(
                    "figure_table_implications", []
                ),
            }
            for feature in features
        ],
        "paper_claim_delta": collect_unique(features, "supported_paper_claims"),
        "non_claims": collect_unique(features, "explicit_non_claims"),
        "section_patch_plan": collect_unique(features, "target_paper_sections"),
        "figure_table_plan": collect_unique(features, "figure_table_implications"),
        "validation_checklist": [
            "Run paper:evidence-packet.",
            "Run paper:update-plan.",
            "Run paper:claim-audit for each edited paper.",
            "Run docs and control gates.",
            "Compile changed LaTeX papers when a TeX engine is available.",
        ],
        "residual_risks": collect_unique(features, "limitations_and_blockers"),
    }


def markdown_plan(plan: dict[str, Any]) -> str:
    """Render the paper update plan as Markdown."""

    lines = [
        "<!--",
        "# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>",
        "#",
        "# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>",
        "# Neuro-symbolic AI Group",
        "#",
        # REUSE-IgnoreStart
        "# SPDX-License-Identifier: MIT",
        # REUSE-IgnoreEnd
        "-->",
        "",
        "# Paper Update Plan",
        "",
        f"Feature count: {plan['feature_count']}",
        "",
        "## Features",
        "",
    ]
    for feature in plan["features"]:
        lines.extend(
            [
                f"### {feature['feature_name']}",
                "",
                feature["summary"],
                "",
                f"- Supported claims: {feature['supported_claim_count']}",
                f"- Explicit non-claims: {feature['non_claim_count']}",
                "",
            ]
        )
    for title, key in [
        ("Paper Claim Delta", "paper_claim_delta"),
        ("Explicit Non-Claims", "non_claims"),
        ("Section Patch Plan", "section_patch_plan"),
        ("Figure/Table Plan", "figure_table_plan"),
        ("Validation Checklist", "validation_checklist"),
        ("Residual Risks", "residual_risks"),
    ]:
        lines.extend([f"## {title}", ""])
        values = plan.get(key, [])
        if values:
            lines.extend(f"- {value}" for value in values)
        else:
            lines.append("- None recorded.")
        lines.append("")
    return "\n".join(lines)


def parse_options(argv: list[str] | None = None) -> dict[str, Any]:
    """Parse the same native arguments for CLI and staged execution."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence-packet",
        default="artifacts/paper_skills/new_functionality_evidence_packet.json",
        help="Evidence packet JSON.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/paper_skills/paper_update_plan.md",
        help="Markdown output path.",
    )
    parser.add_argument("--json", action="store_true", help="Print a JSON summary.")
    return vars(parser.parse_args(argv))


def load_inputs(
    args: dict[str, Any], repository_root: Path | None = None
) -> dict[str, Any]:
    """Resolve paths and load JSON; parsing and I/O errors remain native errors."""
    root = REPO_ROOT if repository_root is None else repository_root
    packet_path = Path(args["evidence_packet"])
    if not packet_path.is_absolute():
        packet_path = root / packet_path
    output = Path(args["output"])
    if not output.is_absolute():
        output = root / output
    return {
        "packet": load_packet(packet_path),
        "output": str(output),
        "json": args["json"],
    }


def publish_plan(loaded: dict[str, Any], plan: dict[str, Any]) -> int:
    """Write Markdown, then JSON, then print the native summary in that order."""
    output = Path(loaded["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown_plan(plan), encoding="utf-8")

    json_output = output.with_suffix(".json")
    json_output.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    result = {
        "ok": True,
        "output": str(output),
        "json_output": str(json_output),
        "feature_count": plan["feature_count"],
        "section_target_count": len(plan["section_patch_plan"]),
        "figure_table_count": len(plan["figure_table_plan"]),
    }
    if loaded["json"]:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Wrote {output}")
    return 0


def main(argv: list[str] | None = None, *, repository_root: Path | None = None) -> int:
    """Read an evidence packet and write paper update plan artifacts."""
    loaded = load_inputs(parse_options(argv), repository_root)
    plan = build_plan(loaded["packet"])
    return publish_plan(loaded, plan)


if __name__ == "__main__":
    raise SystemExit(main())
