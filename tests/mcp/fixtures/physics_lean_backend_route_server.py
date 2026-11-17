# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Actual production registration with isolated native Python CLI dispatch."""

from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from mcp_server import mcp
import mathformer as hub
from backend_suite_boundary import install

root, mode = Path(sys.argv[1]).resolve(), sys.argv[2]
boundary = SimpleNamespace(subprocess=subprocess)
ledger = install(boundary, root, mode)
native_run = boundary.subprocess.run


def run(argv, **kwargs):
    if argv[1:] == ["tests/physics_lean/run_lean_physics_backend_suite.py", "--json"]:
        assert kwargs["timeout"] is None
        if mode == "launch_error":
            raise OSError("fixture launch failed")
    return native_run(argv, **kwargs)


boundary.subprocess.run = run
hub.subprocess = boundary.subprocess


@mcp.tool()
def fixture_ledger() -> dict:
    return {"calls": ledger}


mcp.run(transport="stdio")
