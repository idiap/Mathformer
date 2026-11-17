# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic compiler/provider process boundary; never a production mode.

Installed only in tests on a supplied module's subprocess API. Native preflight,
controller transitions, captured output handling and write audits run unchanged.
"""

import subprocess
from types import SimpleNamespace


def install(native, root):
    calls = []

    def run(command, **kwargs):
        if command[:1] != ["fixture-control-compiler"]:
            raise AssertionError(f"Unexpected process: {command!r}")
        assert kwargs["cwd"] == root
        assert kwargs["text"] is True
        assert kwargs["stdout"] == subprocess.PIPE
        assert kwargs["stderr"] == subprocess.PIPE
        mode = command[1]
        calls.append({"command": list(command), "timeout": kwargs["timeout"]})
        if mode == "crash":
            raise OSError("compiler launch failed")
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                command,
                kwargs["timeout"],
                output="partial",
                stderr="timeout diagnostic",
            )
        if mode == "write":
            (root / "undeclared.txt").write_text("compiler output\n")
        # The audit caveat: an embedded negative finding with exit zero is
        # source success. A failing exit takes precedence over embedded JSON.
        return subprocess.CompletedProcess(
            command,
            7 if mode == "fail" else 0,
            '{"ok":false,"finding":"fixture compiler diagnostic"}',
            "compiler stderr",
        )

    native.subprocess = SimpleNamespace(
        run=run, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
    )
    return calls
