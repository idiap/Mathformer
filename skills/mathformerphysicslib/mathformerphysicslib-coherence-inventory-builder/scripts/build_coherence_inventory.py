#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Build a declaration and concept inventory for MathformerPhysicsLib."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from coherence_common import build_inventory, self_test_payload, write_json


def parse_options(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    return {
        "self_test": args.self_test,
        "output": str(args.output) if args.output is not None else None,
        "json": args.json,
    }


def emit_payload(options: dict, payload: dict) -> int:
    if options["output"]:
        write_json(payload, Path(options["output"]))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    options = parse_options(argv)
    payload = self_test_payload() if options["self_test"] else build_inventory()
    return emit_payload(options, payload)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
