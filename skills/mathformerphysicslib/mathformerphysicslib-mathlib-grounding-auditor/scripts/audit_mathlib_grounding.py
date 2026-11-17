#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup

"""Audit whether MathformerPhysicsLib concepts are grounded in Mathlib."""

from __future__ import annotations

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

from coherence_common import (
    audit_grounding,
    build_inventory,
    canonicalize,
    load_json,
    self_test_payload,
    write_json,
)


def jsonable(value):
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): jsonable(child) for key, child in value.items()}
    if isinstance(value, list):
        return [jsonable(child) for child in value]
    if isinstance(value, tuple):
        return [jsonable(child) for child in value]
    if isinstance(value, set):
        return sorted(jsonable(child) for child in value)
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value


def parse_options(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concept-graph", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    return {
        "self_test": args.self_test,
        "has_concept_graph": bool(args.concept_graph),
        "concept_graph": str(args.concept_graph) if args.concept_graph else None,
        "output": str(args.output) if args.output else None,
        "json": args.json,
        "has_output": bool(args.output),
    }


def self_test_graph() -> dict:
    return canonicalize(self_test_payload())


def load_graph(options: dict) -> dict:
    return load_json(Path(options["concept_graph"]))


def inventory_graph(repository_root: Path | None = None) -> dict:
    return canonicalize(build_inventory(repository_root))


def audit_report(graph: dict) -> dict:
    payload = jsonable(audit_grounding(graph))
    assert isinstance(payload, dict)
    return payload


def write_report(options: dict, report: dict) -> None:
    write_json(report, Path(options["output"]))


def print_report(report: dict) -> int:
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    options = parse_options(argv)
    if options["self_test"]:
        graph = self_test_graph()
    else:
        graph = (
            load_graph(options) if options["has_concept_graph"] else inventory_graph()
        )
    payload = audit_report(graph)
    if options["has_output"]:
        write_report(options, payload)
    return print_report(payload)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
