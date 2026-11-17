# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic external compiler fixture; never installed in production.

The route itself uses a local SymPy writer rather than a model or external
compiler. This boundary checks native process capture and failure propagation
separately. PRISM parsing, checking, compilation and execution remain real.
"""

import json
import subprocess
from types import SimpleNamespace


def install(native, root):
    source = root / "compiler-input.json"
    source.write_text(
        json.dumps(
            {
                "kind": "equality",
                "left": {"type": "Real", "value": 2},
                "right": {"type": "Real", "value": 2},
            }
        )
    )
    calls = []

    def run(command, **kwargs):
        if command[:1] != ["fixture-physics-compiler"]:
            raise AssertionError(f"Unexpected compiler process: {command!r}")
        assert kwargs["cwd"] == root
        assert kwargs["text"] is True
        assert kwargs["stdout"] == subprocess.PIPE
        assert kwargs["stderr"] == subprocess.PIPE
        mode = command[1]
        expression = json.loads(source.read_text())
        assert expression["kind"] == "equality"
        valid = expression["left"]["type"] == expression["right"]["type"]
        calls.append(
            {"argv": list(command), "timeout": kwargs["timeout"], "source": expression}
        )
        if mode == "launch_error":
            raise OSError("fixture compiler launch failed")
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                command, kwargs["timeout"], output="partial", stderr="deadline"
            )
        if mode == "write":
            (root / "undeclared.txt").write_text("compiler output\n")
        rejected = mode == "reject" or not valid
        report = {
            "ok": not rejected,
            "artifact": {"kind": "typed_ir", "expression": expression},
            "diagnostics": (
                [{"code": "fixture_type_error", "line": 3}] if rejected else []
            ),
        }
        return subprocess.CompletedProcess(
            command,
            7 if rejected else 0,
            json.dumps(report),
            "fixture compiler diagnostic",
        )

    native.subprocess = SimpleNamespace(
        run=run, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
    )
    return calls
