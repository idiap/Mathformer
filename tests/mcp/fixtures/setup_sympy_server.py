# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Actual MCP server on a temporary repository and offline uv executable."""

from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts")]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
import mathformer as hub
import mcp_server as server

mode, directory = sys.argv[1], Path(sys.argv[2]).resolve()
os.environ["PATH"] = str(
    directory.parent / ("empty" if mode == "missing_uv" else "bin")
)
os.environ["SYMPY_FIXTURE_MODE"] = mode
os.environ["VENV_PATH"] = ".venv"
hub.REPO_ROOT = directory
server._READONLY = mode == "readonly"
server._ALLOWED_WRITE_ROOTS = [directory / ("denied" if mode == "write_denied" else "")]
server.mcp.run(transport="stdio")
