# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only compiler/provider discovery boundaries; native Python runs for real.

The fixture refuses every other process and network connection. Process records
live beside the temporary repository so they cannot alter native write audits.
No production module imports this fixture or offers a mock-mode switch.
"""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess

_run = subprocess.run
_popen = subprocess.Popen
_which = shutil.which
LEAF = "tests/test_program/run_comprehensive_tests.py"


def forbidden(*args, **kwargs):
    raise AssertionError("unexpected external boundary in offline mathlib fixture")


def configuration(cwd=None):
    root = Path.cwd() if cwd is None else Path(cwd)
    return root, (root / ".mathlib-route-fixture").is_file()


def host_query(command):
    return (
        command == ["uname", "-p"]
        or len(command) == 3
        and command[:2] == ["file", "-b"]
        and Path(command[2]).resolve() == Path(os.sys.executable).resolve()
    )


def which(command, *args, **kwargs):
    _, fixture = configuration()
    # Dependency availability is an external environment/provider boundary.
    return None if fixture else _which(command, *args, **kwargs)


class Popen(_popen):
    def __init__(self, argv, *args, **kwargs):
        root, fixture = configuration(kwargs.get("cwd"))
        if fixture and host_query(list(argv)):
            # Python's platform.platform() performs this harmless host query on
            # macOS; preserve it rather than substituting source observability.
            super().__init__(argv, *args, **kwargs)
            return
        assert fixture and list(argv)[1:] == [
            LEAF,
            "--module-family",
            "mathlib",
            "--json",
        ], argv
        assert Path(argv[0]).resolve() == Path(os.sys.executable).resolve(), argv
        super().__init__(argv, *args, **kwargs)


def run(argv, *args, **kwargs):
    root, fixture = configuration(kwargs.get("cwd"))
    assert fixture, ("refusing process outside fixture repository", argv)
    command = list(argv)
    with root.with_suffix(".calls.jsonl").open("a") as log:
        log.write(
            json.dumps({"argv": command, "timeout": kwargs.get("timeout")}) + "\n"
        )
    if host_query(command):
        return _run(argv, *args, **kwargs)
    if command[1:] == [LEAF, "--module-family", "mathlib", "--json"]:
        assert kwargs["timeout"] == 900
        return _run(argv, *args, **kwargs)
    if len(command) == 3 and command[1] == "-c" and command[2].startswith("import "):
        # Deterministic unavailable provider/packages, without importing SDKs.
        assert kwargs["timeout"] == 15
        return subprocess.CompletedProcess(argv, 1, "", "fixture: unavailable")
    assert command[0] == "fixture-compiler" and len(command) == 2, command
    assert (
        kwargs["text"]
        and kwargs["stdout"] == subprocess.PIPE
        and kwargs["stderr"] == subprocess.PIPE
    )
    mode = command[1]
    if mode == "timeout":
        raise subprocess.TimeoutExpired(
            argv, kwargs["timeout"], output="partial compile"
        )
    if mode == "crash":
        raise OSError("fixture compiler launch failed")
    if mode == "write":
        (root / "undeclared.txt").write_text("compiler output outside declared roots")
    assert mode in {"pass", "fail", "large", "write"}, mode
    return subprocess.CompletedProcess(
        argv,
        7 if mode == "fail" else 0,
        "x" * 5000 if mode == "large" else "compiled " + mode,
        "",
    )


# Remove names before the native dependency snapshot can inspect them; no value
# is read, copied, or logged. There is no service config or provider selection.
for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
    os.environ.pop(name, None)
shutil.which = which
subprocess.Popen = Popen
subprocess.run = run
socket.create_connection = forbidden
socket.socket.connect = forbidden
