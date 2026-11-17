#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup

"""Canonicalize MathformerPhysicsLib declarations into concept records."""

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
    load_json,
    self_test_payload,
    write_json,
)


def emit_payload(payload: dict, output: Path | None = None) -> int:
    """Shared native output boundary for the CLI and staged MCP execution."""
    if output:
        write_json(payload, output)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        payload = canonicalize(self_test_payload())
    else:
        payload = canonicalize(
            load_json(args.input) if args.input else build_inventory()
        )
    return emit_payload(payload, args.output)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
