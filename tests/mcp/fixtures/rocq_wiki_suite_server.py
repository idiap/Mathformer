# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Serve production suite registrations, with compiler fixtures inherited by CLIs."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from mcp.server.fastmcp import FastMCP
from rocq_wiki_suite_tools import register_rocq_wiki_suite_tools

mcp = FastMCP("rocq-wiki-fixture")
register_rocq_wiki_suite_tools(mcp)
if __name__ == "__main__":
    mcp.run(transport="stdio")
