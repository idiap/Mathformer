# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only external compiler boundary; every Python suite process stays real."""

from tempfile import gettempdir

import json
import os
from pathlib import Path
import subprocess
import time
from backends.rocq.MathformerRocq import autoformalize as native

mode = os.environ["ROCQ_WIKI_COMPILER_FIXTURE"]
original_run = subprocess.run


def find(explicit=None):
    if mode == "missing":
        return None
    return {
        "kind": "coqc",
        "path": str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/coqc"),
        "prefix": [str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/coqc")],
    }


def run(cmd, **kwargs):
    if cmd[0] != str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/coqc"):
        return original_run(cmd, **kwargs)
    with Path(os.environ["ROCQ_WIKI_LEDGER"]).open("a") as stream:
        stream.write(
            json.dumps({"cmd": list(cmd), "timeout": kwargs["timeout"]}) + "\n"
        )
    if mode == "raise":
        raise OSError("fixture compiler launch failure")
    if mode == "slow":
        time.sleep(3)
    first = "Contrapositive" in cmd[-1]
    if mode == "timeout" and first:
        raise subprocess.TimeoutExpired(
            cmd, kwargs["timeout"], output="", stderr="fixture timeout"
        )
    return subprocess.CompletedProcess(
        cmd,
        1 if mode == "reject" and first else 0,
        stdout="fixture compiler",
        stderr="",
    )


native.find_rocq_compiler = find
subprocess.run = run
