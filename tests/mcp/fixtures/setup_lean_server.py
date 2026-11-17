# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Replace only toolchain discovery/execution, retaining real MCP registration."""

from tempfile import gettempdir

from pathlib import Path
import json
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
import install_env as native
import mcp_server as server

mode, root = sys.argv[1], Path(sys.argv[2]).resolve()
native.ROOT_DIR = root
server._READONLY = mode == "readonly"
server._ALLOWED_WRITE_ROOTS = [root / "denied" if mode == "write_denied" else root]


def which(name):
    assert name == "lake", name
    return (
        None
        if mode == "missing"
        else str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/lake")
    )


def compiler(command, **kw):
    assert command[0] == str(
        Path(gettempdir()) / "mathformer-test-fixtures/fixture/lake"
    )
    assert command[1] in ("update", "build")
    assert kw == dict(cwd=root, check=True, stdout=sys.stderr), kw
    with (root / "calls.jsonl").open("a") as stream:
        stream.write(json.dumps(command) + "\n")
    if mode == command[1] + "_failure":
        raise subprocess.CalledProcessError(7, command)
    if mode == "launch_error":
        raise OSError("fixture launch failure")
    return subprocess.CompletedProcess(command, 0)


with (
    patch.object(native.shutil, "which", which),
    patch.object(native.subprocess, "run", compiler),
):
    server.mcp.run(transport="stdio")
