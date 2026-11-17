# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic external compiler and provider-discovery boundaries for tests.

All orchestration, check classification, snapshots, ledger and report writes
remain native. Only named compiler invocations and executable discovery are
substituted. Python dependency probes execute in an empty credential environment.
"""

from pathlib import Path
import subprocess
import os
from types import SimpleNamespace


def install(native, root):
    native.REPO_ROOT = Path(root)
    native.MATRIX_FILE = Path(root) / "tests/test_matrix.json"
    native.ARTIFACT_ROOT = Path(root) / "artifacts/test_program"
    native.time = SimpleNamespace(time=lambda: 1234567890.0)
    native.shutil = SimpleNamespace(which=lambda name: None)
    # Provider configuration is an empty fixture; never inspect host credentials.
    native.os = SimpleNamespace(environ={})
    real_run = subprocess.run

    def compiler(command, **kwargs):
        if command[0] != "fixture-compiler":
            # Dependency import probes are harmless real Python subprocesses.
            return real_run(
                command,
                env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
                **kwargs,
            )
        mode = command[1]
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                command, kwargs["timeout"], output="partial"
            )
        if mode == "crash":
            raise OSError("fixture compiler launch failed")
        if mode == "write":
            (Path(root) / "undeclared.txt").write_text("compiler output")
        return subprocess.CompletedProcess(
            command, 7 if mode == "fail" else 0, "compiled " + mode, ""
        )

    native.subprocess = SimpleNamespace(
        run=compiler, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
    )


def serve(root):
    from mcp_server import mcp
    from comprehensive_strict_tools import source_runner

    install(source_runner(), root)
    mcp.run(transport="stdio")
