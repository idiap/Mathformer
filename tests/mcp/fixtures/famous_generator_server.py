# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated stdio server using exactly the production registration."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from mcp.server.fastmcp import FastMCP
from famous_generator_tools import register_famous_generator_tools

server = FastMCP("seed-generator")
register_famous_generator_tools(server)
if __name__ == "__main__":
    server.run(transport="stdio")
