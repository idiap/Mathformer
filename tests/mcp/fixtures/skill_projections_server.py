# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Fixture transport for unmodified production registrations; all IO is temporary."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from mcp.server.fastmcp import FastMCP
from skill_projection_tools import register_skill_projection_tools

mcp = FastMCP("projection-fixture")
register_skill_projection_tools(mcp)
mcp.run(transport="stdio")
