# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only compiler discovery/launch boundary and passive process recording.

Native Python subprocesses execute unchanged. No Isabelle process is launched.
Only temporary trees with an explicit fixture manifest are instrumented.
"""

from tempfile import gettempdir

import json
import os
from pathlib import Path
import shutil
import subprocess

_run = subprocess.run
_which = shutil.which


def configuration(cwd=None):
    root = Path.cwd() if cwd is None else Path(cwd)
    path = root / ".isabelle-route-fixture.json"
    return (root, json.loads(path.read_text())) if path.is_file() else (root, None)


def which(command, *args, **kwargs):
    _, config = configuration()
    if config is not None and command == "isabelle":
        return (
            None
            if config["compiler"] == "missing"
            else str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/isabelle")
        )
    return _which(command, *args, **kwargs)


def run(argv, *args, **kwargs):
    root, config = configuration(kwargs.get("cwd"))
    if config is None:
        return _run(argv, *args, **kwargs)
    log = root / "artifacts/isabelle/fixture-calls.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as stream:
        stream.write(
            json.dumps({"argv": list(argv), "timeout": kwargs.get("timeout")}) + "\n"
        )
    if argv[0] != str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/isabelle"):
        return _run(argv, *args, **kwargs)
    assert argv[1:3] == ["build", "-D"], argv
    mode = config["compiler"]
    if mode == "timeout":
        raise subprocess.TimeoutExpired(
            argv, kwargs["timeout"], output=b"partial build", stderr=b"deadline"
        )
    if mode == "crash":
        raise OSError("fixture compiler launch failed")
    if mode == "write":
        (root / "undeclared.txt").write_text("compiler side effect")
    return subprocess.CompletedProcess(
        argv, 7 if mode == "reject" else 0, "fixture build output", ""
    )


shutil.which = which
subprocess.run = run

# Keep external grounding data and application discovery confined to the tree.

_root, _config = configuration()
if _config is not None:
    os.environ["ISARMATHLIB_HOME"] = str(_root / "library")
