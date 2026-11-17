# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only process boundary: real native Python helpers, deterministic Lake.

No model is selected or contacted. Unknown external executables and network
connections fail closed. This file is enabled only by the fixture PYTHONPATH.
"""

import json
from pathlib import Path
import socket
import subprocess

_original_run = subprocess.run


def deny_network(*args, **kwargs):
    raise AssertionError("network access forbidden in goal fixtures")


socket.socket.connect = deny_network
socket.create_connection = deny_network


def compiler_boundary(argv, *args, **kwargs):
    root = Path(kwargs.get("cwd", Path.cwd()))
    if argv[0] == "lake":
        settings = json.loads((root / "compiler-fixture.json").read_text())
        assert argv[:3] == ["lake", "env", "lean"], argv
        assert "timeout" not in kwargs or settings["mode"] == "timeout"
        with (root / "compiler_calls.jsonl").open("a") as stream:
            stream.write(
                json.dumps({"argv": argv, "timeout": kwargs.get("timeout")}) + "\n"
            )
        mode = settings["mode"]
        if mode == "launch_error":
            raise OSError("fixture compiler launch error")
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                argv,
                kwargs.get("timeout", 240),
                output="compiler timeout",
                stderr="timed out",
            )
        return subprocess.CompletedProcess(
            argv,
            int(mode == "failure"),
            (
                "Fixture.lean:1:1: warning: declaration uses sorry\n"
                if mode == "warning"
                else ""
            ),
            (
                "Fixture.lean:1:1: error: unknown identifier\n"
                if mode == "failure"
                else ""
            ),
        )
    if not Path(argv[0]).name.startswith("python"):
        raise AssertionError(f"unexpected external process: {argv}")
    with (root / "native_process_calls.jsonl").open("a") as stream:
        stream.write(
            json.dumps({"argv": argv[1:], "timeout": kwargs.get("timeout")}) + "\n"
        )
    return _original_run(argv, *args, **kwargs)


subprocess.run = compiler_boundary
