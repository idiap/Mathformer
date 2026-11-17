# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Serve actual registered tools with a test-only Lake compiler boundary."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(Path(__file__).resolve().parent)]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
import mcp_server
from mcp_server import mcp
from physics_release_gate_tools import native
from physics_release_boundary import boundaries

mode, directory = sys.argv[1:]
if mode == "readonly":
    mcp_server._READONLY = True
with boundaries(native, Path(directory), mode, []):
    mcp.run(transport="stdio")
