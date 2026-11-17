# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated native source trees; no scientific implementation is replaced."""

import json
from pathlib import Path
import shutil
import sys

FILES = (
    "tests/physics_sympy/run_controlled_suite.py",
    "backends/sympy/MathformerPhysicsSympy/pipeline.py",
    "libraries/MathformerPhysicsLib/physics_ir.py",
)


def populate(root, source):
    for name in FILES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    python = root / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    return root


def serve(base):
    import socket
    import subprocess
    import mathformer as hub
    from mcp_server import mcp, apply_runtime_config

    base = Path(base).resolve()
    original = subprocess.Popen

    def guarded(command, **kwargs):
        root = Path(kwargs["cwd"]).resolve()
        assert root.is_relative_to(base) and root != hub.REPO_ROOT
        assert command == [".venv/bin/python", FILES[0], "--json"]
        assert kwargs["pass_fds"]
        with (base / "launches.jsonl").open("a") as log:
            log.write(
                json.dumps(
                    {
                        "argv": command,
                        "cwd": str(root),
                        "stage_fds": len(kwargs["pass_fds"]),
                    }
                )
                + "\n"
            )
        return original(command, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected external provider/network call")

    subprocess.Popen = guarded
    socket.create_connection = forbidden
    apply_runtime_config(allowed_write_roots=[str(base)])
    mcp.run(transport="stdio")
