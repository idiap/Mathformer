# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Run real registered MCP tools with only external execution replaced."""

from pathlib import Path
import os
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts")]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
import install_env as native
import mcp_server as server
from setup_all_boundary import Boundary

mode, directory = sys.argv[1], Path(sys.argv[2]).resolve()
native.ROOT_DIR = directory
os.environ["VENV_PATH"] = "environment"
boundary = Boundary(directory, mode)
server._READONLY = mode == "readonly"
server._ALLOWED_WRITE_ROOTS = [directory / ("denied" if mode == "write_denied" else "")]
with (
    patch.object(native.shutil, "which", boundary.which),
    patch.object(native.subprocess, "run", boundary.run),
):
    server.mcp.run(transport="stdio")
