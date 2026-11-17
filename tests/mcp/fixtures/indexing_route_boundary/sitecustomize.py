# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline compiler metadata fixture. All native Python subprocesses run for real.

Reject every process except the fixed native suite commands and host metadata.
The test log lives outside the audited fixture tree. No production imports this.
"""

import json
from pathlib import Path
import socket
import subprocess
import sys

_run, _popen = subprocess.run, subprocess.Popen
LEAF = "tests/mathlib/run_indexing_control_suite.py"
COMMANDS = [
    [LEAF, "--json"],
    [
        "skills/mathlib/mathlib-index-builder/scripts/build_mathlib_index.py",
        "--max-files",
        "220",
        "--json",
    ],
    [
        "skills/mathlib/mathlib-index-builder/scripts/build_mathlib_index.py",
        "--validate-existing",
        "--json",
    ],
    [
        "skills/mathlib/mathlib-concept-ontology-manager/scripts/validate_concept_ontology.py",
        "--json",
    ],
    [
        "skills/mathlib/mathlib-term-expansion-annotator/scripts/annotate_mathlib_terms.py",
        "--self-test",
        "--json",
    ],
    [
        "skills/mathlib/mathlib-navigation-state-planner/scripts/plan_mathlib_navigation_state.py",
        "--self-test",
        "--json",
    ],
    [
        "skills/mathlib/mathlib-navigation-state-planner/scripts/plan_mathlib_navigation_state.py",
        "--monotonic-check",
        "--json",
    ],
]


def host_query(argv):
    return argv == ["uname", "-p"] or (
        len(argv) == 3
        and argv[:2] == ["file", "-b"]
        and Path(argv[2]).resolve() == Path(sys.executable).resolve()
    )


def native(argv, cwd):
    root = Path(cwd or Path.cwd()).resolve()
    assert (root / ".indexing-route-fixture").exists(), (root, argv)
    assert Path(argv[0]).resolve() == Path(sys.executable).resolve(), argv
    assert argv[1:] in COMMANDS, argv
    return root


class Popen(_popen):
    def __init__(self, argv, *args, **kwargs):
        if not host_query(list(argv)):
            native(list(argv), kwargs.get("cwd"))
        super().__init__(argv, *args, **kwargs)


def run(argv, *args, **kwargs):
    command = list(argv)
    if host_query(command):
        return _run(argv, *args, **kwargs)
    root = Path(kwargs.get("cwd") or Path.cwd()).resolve()
    # These are the only external compiler/provider queries in this workflow.
    if command in [["lean", "--version"], ["git", "rev-parse", "HEAD"]]:
        assert (root / ".indexing-route-fixture").exists() or (root / ".git").exists()
        assert kwargs["timeout"] == 20
        return subprocess.CompletedProcess(
            argv,
            0,
            "fixture-lean-4\n" if command[0] == "lean" else "fixture-revision\n",
            "",
        )
    root = native(command, kwargs.get("cwd"))
    assert kwargs["timeout"] == (480 if command[1] == LEAF else 240)
    with root.with_suffix(".calls.jsonl").open("a") as stream:
        stream.write(
            json.dumps(
                {"argv": command, "timeout": kwargs["timeout"], "cwd": str(root)}
            )
            + "\n"
        )
    return _run(argv, *args, **kwargs)


def forbidden(*args, **kwargs):
    raise AssertionError("offline indexing fixture forbids network access")


subprocess.run = run
subprocess.Popen = Popen
socket.create_connection = forbidden
socket.socket.connect = forbidden
