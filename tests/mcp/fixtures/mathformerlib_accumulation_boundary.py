# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only process/provider boundaries; execute all native runner steps unchanged."""

import json
from pathlib import Path
import subprocess
from types import SimpleNamespace


def install(native, root):
    root = Path(root)
    native.REPO_ROOT = root
    native.MATRIX_FILE = root / "tests/test_matrix.json"
    native.ARTIFACT_ROOT = root / "artifacts/test_program"
    # External executable/provider discovery has no access to host credentials.
    native.os = SimpleNamespace(environ={})
    native.shutil = SimpleNamespace(which=lambda name: None)

    def external(command, **kwargs):
        if (
            len(command) == 3
            and command[1] == "-c"
            and command[2].startswith("import ")
        ):
            return subprocess.CompletedProcess(command, 1, "", "fixture: unavailable")
        if command[0] == "fixture-compiler":
            mode = command[1]
        elif (
            len(command) == 3
            and command[-1] == "--help"
            and "skills/mathformerlib/" in command[1]
        ):
            modes = json.loads((root / "boundary.json").read_text())
            mode = modes[0 if "manage_mathformerlib_registry" in command[1] else 1]
        else:
            raise AssertionError(f"unexpected external process: {command!r}")
        assert kwargs["cwd"] == root
        assert kwargs["text"] is True
        assert kwargs["stdout"] == subprocess.PIPE
        assert kwargs["stderr"] == subprocess.PIPE
        with (root.parent / (root.name + "-compiler.jsonl")).open("a") as ledger:
            ledger.write(
                json.dumps(dict(command=command, timeout=kwargs["timeout"])) + "\n"
            )
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                command, kwargs["timeout"], output="partial"
            )
        if mode == "crash":
            raise OSError("fixture compiler launch failed")
        if mode == "write":
            (root / "undeclared.txt").write_text("compiler output")
        return subprocess.CompletedProcess(
            command,
            7 if mode == "fail" else 0,
            "a" * 5000 + "TAIL" if mode == "large" else "compiled " + mode,
            "",
        )

    native.subprocess = SimpleNamespace(
        run=external, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
    )


def serve(root):
    from mcp_server import mcp
    from comprehensive_strict_tools import source_runner

    install(source_runner(), root)
    mcp.run(transport="stdio")
