#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.
#
# Intent:
#   Encode regression checks that catch parser breakage, semantic drift, and missing workflow evidence.
#
# Function:
#   Contains executable tests, fixtures, and manifests used for local and CI validation.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Run backend-specific Mathformer tests."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_backend_args(argv=None) -> dict:
    """Parse the native CLI, retaining its defaults and argparse failures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-warning", action="store_true")
    parser.add_argument(
        "--backend",
        action="append",
        choices=["lean", "isabelle", "sympy", "physics_sympy", "all"],
        default=[],
    )
    args = parser.parse_args(argv)
    backends = set(args.backend or ["all"])
    return {
        "backends": sorted(backends),
        "all": "all" in backends,
        "json": args.json,
        "fail_on_warning": args.fail_on_warning,
    }


def select_all(args: dict) -> list[str]:
    return ["lean", "isabelle", "sympy", "physics_sympy"]


def select_sorted(args: dict) -> list[str]:
    return sorted(args["backends"])


def pack(families: list[str]) -> dict:
    return {
        "families": list(families),
        "index": 0,
        "command": [sys.executable, "tests/test_program/run_comprehensive_tests.py"],
    }


def append_family(state: dict) -> dict:
    command = list(state["command"])
    command.extend(["--module-family", state["families"][state["index"]]])
    index = state["index"] + 1
    return {
        "state": {
            "families": list(state["families"]),
            "command": command,
            "index": index,
        },
        "done": index == len(state["families"]),
    }


def finalize(state: dict, args: dict) -> list[str]:
    command = list(state["command"])
    command.extend(["--write-jsonl", "--write-junit"])
    if args["json"]:
        command.append("--json")
    if args["fail_on_warning"]:
        command.append("--fail-on-warning")
    return command


def launch(command: list[str]) -> int:
    return subprocess.call(command, cwd=REPO_ROOT)


def main() -> int:
    args = parse_backend_args()
    families = select_all(args) if args["all"] else select_sorted(args)
    state = pack(families)
    for _ in families:
        state = append_family(state)["state"]
    return launch(finalize(state, args))


if __name__ == "__main__":
    raise SystemExit(main())
