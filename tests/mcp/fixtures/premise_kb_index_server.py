# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated server with the production registrations and real local KB backend."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from mcp.server.fastmcp import FastMCP
from premise_kb_index_tools import register_premise_kb_index_tools

mcp = FastMCP("kb-index-fixture")
register_premise_kb_index_tools(mcp)
if __name__ == "__main__":
    mcp.run(transport="stdio")
