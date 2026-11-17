# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic test-only uv/package-manager and Lake compiler boundaries."""

from tempfile import gettempdir

import json
from pathlib import Path
import subprocess

DEPS = [
    "huggingface_hub>=0.23,<1",
    "sympy>=1.12,<2",
    "numpy>=1.26,<3",
    "docling>=2",
    "mcp>=1.6,<2",
]


class Boundary:
    def __init__(self, root, mode="success"):
        self.root = Path(root)
        self.mode = mode
        self.calls = []

    def which(self, name):
        assert name in ("uv", "lake"), name
        return (
            None
            if self.mode == "missing_" + name
            else str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/") + name
        )

    def run(self, command, *, cwd=None, check, stdout=None):
        assert check is True
        if stdout is not None:
            assert hasattr(stdout, "write")
        row = {"command": command, "cwd": str(cwd) if cwd else None, "check": check}
        self.calls.append(row)
        with (self.root / "launches.jsonl").open("a") as stream:
            stream.write(json.dumps(row) + "\n")
        if command[:2] == [
            str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/uv"),
            "venv",
        ]:
            assert len(command) == 3 and cwd is None
            path = Path(command[2])
            assert path.is_relative_to(self.root)
            if self.mode != "missing_python":
                from install_env import venv_python

                python = venv_python(path)
                python.parent.mkdir(parents=True, exist_ok=True)
                python.write_text("fixture interpreter; never executed")
        elif command[:3] == [
            str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/uv"),
            "pip",
            "install",
        ]:
            assert cwd is None and command[3] == "--python"
            assert Path(command[4]).exists()
            assert command[5:] == DEPS
        else:
            assert command in (
                [
                    str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/lake"),
                    "update",
                ],
                [
                    str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/lake"),
                    "build",
                ],
            ), command
            assert cwd == self.root
            (self.root / ".lake").mkdir(exist_ok=True)
            (self.root / ".lake" / command[1]).write_text("compiler boundary result")
        print("[fixture] external command output", file=stdout)
        if self.mode == "fail_" + str(len(self.calls)):
            raise subprocess.CalledProcessError(7, command)
        return subprocess.CompletedProcess(command, 0)
