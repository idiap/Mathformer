# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only external compiler fixture and passive native process recording.

Real Python source steps run unchanged. Only compiler discovery and compiler
launch are substituted. Fixture configuration exists only in temporary trees.
"""

import json
from pathlib import Path
import shutil
import subprocess

_run = subprocess.run
_which = shutil.which


def configuration(cwd=None):
    root = Path.cwd() if cwd is None else Path(cwd)
    path = root / ".rocq-route-fixture.json"
    return (root, json.loads(path.read_text())) if path.is_file() else (root, None)


def which(command, *args, **kwargs):
    root, config = configuration()
    if config is not None and command in {"rocq", "coqc"}:
        if config["compiler"] == "missing" or command == "coqc":
            return None
        return str(root / "fixture-bin/rocq")
    return _which(command, *args, **kwargs)


def run(argv, *args, **kwargs):
    root, config = configuration(kwargs.get("cwd"))
    if config is None:
        return _run(argv, *args, **kwargs)
    log = root / "artifacts/rocq_wiki_level/fixture-calls.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as stream:
        stream.write(
            json.dumps({"argv": list(argv), "timeout": kwargs.get("timeout")}) + "\n"
        )
    if str(argv[0]) != str(root / "fixture-bin/rocq"):
        assert len(argv) > 1 and argv[1] in {
            "tests/rocq/run_wiki_suite.py",
            "skills/rocq/rocq-autoformalization-drafter/scripts/draft_rocq_wiki_case.py",
            "skills/rocq/rocq-execution-runner/scripts/check_rocq_file.py",
        }, argv
        return _run(argv, *args, **kwargs)
    assert argv[1] == "compile" and str(argv[2]).endswith(".v"), argv
    mode = config["compiler"]
    if mode == "timeout":
        raise subprocess.TimeoutExpired(
            argv, kwargs["timeout"], output="partial compile", stderr="deadline"
        )
    if mode == "crash":
        raise OSError("fixture compiler launch failed")
    if mode == "write":
        (root / "undeclared.txt").write_text("compiler side effect")
    if mode == "success":
        Path(argv[2]).with_suffix(".vo").write_text("fixture object")
    return subprocess.CompletedProcess(
        argv, 7 if mode == "reject" else 0, "fixture compiler output", ""
    )


shutil.which = which
subprocess.run = run
