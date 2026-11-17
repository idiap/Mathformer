# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Expose the production registration for isolated regression tests."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from mcp.server.fastmcp import FastMCP
from famous_corpus_tools import register_famous_corpus_tools

mcp = FastMCP("famous-corpus-regression")
register_famous_corpus_tools(mcp)
if __name__ == "__main__":
    mcp.run(transport="stdio")
