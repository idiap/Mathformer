# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only external compiler boundary for generic native controller checks.

The selected ERFL gates have no external model/compiler. They are exercised
through real MCP with dry-run and isolated preflight inputs. These separate
compiler actions test native process capture, audits and exception propagation
without launching either production gate or changing its registry binding.
"""

import json
import subprocess
from types import SimpleNamespace


def install(native, root):
    calls = []

    def run(command, **kwargs):
        if command[:1] != ["fixture-reasoning-compiler"]:
            raise AssertionError(f"Unexpected process: {command!r}")
        assert kwargs["cwd"] == root
        assert kwargs["text"] is True
        assert kwargs["stdout"] == subprocess.PIPE
        assert kwargs["stderr"] == subprocess.PIPE
        mode = command[1]
        calls.append({"argv": list(command), "timeout": kwargs["timeout"]})
        if mode == "launch_error":
            raise OSError("fixture compiler launch failed")
        if mode == "write":
            (root / "undeclared.txt").write_text("compiler output\n")
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                command, kwargs["timeout"], output="partial", stderr="deadline"
            )
        return subprocess.CompletedProcess(
            command,
            7 if mode == "reject" else 0,
            json.dumps(
                {
                    "ok": False,
                    "diagnostics": [{"code": "fixture_type_error", "line": 3}],
                    "artifact": {"kind": "typed_ir", "nodes": ["input", "check"]},
                }
            ),
            "fixture compiler diagnostic",
        )

    native.subprocess = SimpleNamespace(
        run=run, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
    )
    return calls
