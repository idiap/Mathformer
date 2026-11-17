# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Serve the production KB registration with no unrelated optional backends."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from mcp.server.fastmcp import FastMCP
from premise_kb_e2e_tools import register_premise_kb_e2e_tools

mcp = FastMCP("mathformer-kb-regression")
register_premise_kb_e2e_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")
