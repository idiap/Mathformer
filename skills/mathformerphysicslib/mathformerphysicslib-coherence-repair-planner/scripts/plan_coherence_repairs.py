#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Plan controlled MathformerPhysicsLib coherence repairs."""

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
    critic_api,
    critic_integration,
    critic_redefinitions,
    load_json,
    repair_plan,
    self_test_payload,
    write_json,
)


def default_reports(
    self_test: bool = False, repository_root: Path | None = None
) -> list[dict[str, Any]]:
    inventory = (
        self_test_payload(repository_root)
        if self_test
        else build_inventory(repository_root)
    )
    graph = canonicalize(inventory)
    grounding = audit_grounding(graph)
    return [
        grounding,
        critic_redefinitions(graph, grounding),
        critic_integration(inventory, graph, repository_root),
        critic_api(graph, repository_root),
    ]


def parse_arguments(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    return {
        "reports": [str(path) for path in args.report],
        "output": str(args.output) if args.output else None,
        "self_test": args.self_test,
        "json": args.json,
        "has_reports": bool(args.report),
        "has_output": bool(args.output),
    }


def load_reports(args: dict[str, Any]) -> list[dict[str, Any]]:
    return [load_json(Path(path)) for path in args["reports"]]


def write_output(args: dict[str, Any], payload: dict[str, Any]) -> None:
    write_json(payload, Path(args["output"]))


def emit(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    reports = (
        load_reports(args)
        if args["has_reports"]
        else default_reports(args["self_test"])
    )
    payload = repair_plan(reports)
    if args["has_output"]:
        write_output(args, payload)
    return emit(payload)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
