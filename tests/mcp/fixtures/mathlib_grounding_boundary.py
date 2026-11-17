# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Start the production MCP registration with temporary filesystem policy only."""

from pathlib import Path


def serve(directory):
    import mcp_server

    root = Path(directory).resolve()
    mcp_server._ALLOWED_WRITE_ROOTS = [root]
    mcp_server.CALL_LOG_PATH = root / "server-calls.jsonl"
    mcp_server.mcp.run(transport="stdio")
