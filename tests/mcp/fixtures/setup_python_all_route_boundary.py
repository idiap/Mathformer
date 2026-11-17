# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline uv/package-manager boundaries; run the unchanged installer and hub controller.

Unknown argv fail closed. No real environment creation, package installation,
provider, compiler, prover, credentials or network is used.
"""

import json
import os
from pathlib import Path
import subprocess
import sys

DEPS = [
    "huggingface_hub>=0.23,<1",
    "sympy>=1.12,<2",
    "numpy>=1.26,<3",
    "docling>=2",
    "mcp>=1.6,<2",
]
INSTALL = ["run", "python", "scripts/install_env.py", "--all-extras"]


def boundary(kind):
    root = Path.cwd().resolve()
    mode = (root.parent / "mode.txt").read_text()
    args = sys.argv[1:]
    with (root.parent / "uv.jsonl").open("a") as stream:
        stream.write(json.dumps(args) + "\n")
    assert kind == "uv"
    if args == INSTALL:
        if mode == "launch_failure":
            print("fixture uv launcher failed", file=sys.stderr)
            return 9
        environment = dict(os.environ)
        if mode == "installer_missing_uv":
            environment["PATH"] = str(root.parent / "absent")
        return subprocess.run(
            [sys.executable, *args[2:]], env=environment, check=False
        ).returncode
    if args[:2] == ["pip", "install"]:
        expected = ["pip", "install", "--python", str(root / ".venv/bin/python"), *DEPS]
        assert args == expected, args
        if mode == "pip_failure":
            print("fixture pip failed", file=sys.stderr)
            return 6
        print("fixture dependencies installed")
        return 0
    assert args == ["venv", str(root / ".venv")], args
    if mode == "venv_failure":
        print("fixture uv venv failed", file=sys.stderr)
        return 7
    if mode != "missing_python":
        path = (
            root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture interpreter placeholder; never executed")
    if mode == "undeclared_write":
        (root / "unexpected.txt").write_text("fixture write outside declared roots")
    print("fixture venv created")
    return 0


def serve(root, binary, readonly=False, deny_writes=False):
    """Production MCP registration, isolated service roots and environment."""
    os.environ.clear()
    os.environ.update(
        PATH=str(binary), PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1"
    )
    sys.dont_write_bytecode = True
    actual_run = subprocess.run

    def launch(command, **kwargs):
        if (
            command == ["uv", *INSTALL]
            and (Path(root).parent / "mode.txt").read_text() == "timeout"
        ):
            assert kwargs["cwd"] == Path(root)
            assert kwargs["timeout"] == 7
            raise subprocess.TimeoutExpired(
                command,
                kwargs["timeout"],
                output="partial stdout",
                stderr="partial stderr",
            )
        return actual_run(command, **kwargs)

    subprocess.run = launch
    import mcp_server

    mcp_server._READONLY = readonly
    mcp_server._ALLOWED_WRITE_ROOTS = [
        Path(root) / "denied" if deny_writes else Path(root)
    ]
    mcp_server.mcp.run(transport="stdio")
