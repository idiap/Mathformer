# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only repository mount using the actual production MCP registrations."""

from pathlib import Path
from contextlib import redirect_stderr
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import mathformer as hub

hub.REPO_ROOT = Path(sys.argv[1]).resolve()
import mcp_server

mcp_server.apply_runtime_config(allowed_write_roots=[str(hub.REPO_ROOT)])
with (hub.REPO_ROOT / "mcp-diagnostics.log").open("w", buffering=1) as diagnostics:
    with redirect_stderr(diagnostics):
        mcp_server.mcp.run(transport="stdio")
