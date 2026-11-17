# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic external compiler/provider boundaries in an isolated repository.

Only dependency discovery and compiler process calls are substituted. The runner
loader, cursor, audits, ledger, reports and CLI publication execute unchanged.
Fixture matrices are inputs, never replacements for source step algorithms.
"""

import json
from pathlib import Path
import subprocess
from types import SimpleNamespace


def install(native, root):
    root = Path(root)
    native.REPO_ROOT = root
    native.MATRIX_FILE = root / "tests/test_matrix.json"
    native.ARTIFACT_ROOT = root / "artifacts/test_program"
    native.os = SimpleNamespace(environ={})
    native.shutil = SimpleNamespace(which=lambda name: None)

    def external(command, **kwargs):
        if (
            len(command) == 3
            and command[1] == "-c"
            and command[2].startswith("import ")
        ):
            return subprocess.CompletedProcess(command, 1, "", "fixture: unavailable")
        if command[0] != "fixture-compiler":
            raise AssertionError(f"unexpected external process: {command!r}")
        assert kwargs["cwd"] == root
        assert kwargs["text"] is True
        assert kwargs["stdout"] == subprocess.PIPE
        assert kwargs["stderr"] == subprocess.PIPE
        with (root.parent / (root.name + "-compiler.jsonl")).open("a") as ledger:
            ledger.write(
                json.dumps({"command": command, "timeout": kwargs["timeout"]}) + "\n"
            )
        mode = command[1]
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                command, kwargs["timeout"], output="partial"
            )
        if mode == "crash":
            raise OSError("fixture compiler launch failed")
        if mode == "write":
            (root / "undeclared.txt").write_text("unexpected compiler output")
        return subprocess.CompletedProcess(
            command,
            7 if mode == "fail" else 0,
            "x" * 5000 + "TAIL" if mode == "large" else "compiled " + mode,
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
