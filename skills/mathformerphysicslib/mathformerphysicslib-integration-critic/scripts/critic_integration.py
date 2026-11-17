#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup

"""Criticize import integration and canonical index coverage."""

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
    build_inventory,
    canonicalize,
    critic_integration,
    load_json,
    self_test_payload,
    write_json,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--concept-graph", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        inventory = self_test_payload()
        graph = canonicalize(inventory)
    else:
        inventory = load_json(args.inventory) if args.inventory else build_inventory()
        graph = (
            load_json(args.concept_graph)
            if args.concept_graph
            else canonicalize(inventory)
        )
    payload = critic_integration(inventory, graph)
    if args.output:
        write_json(payload, args.output)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
