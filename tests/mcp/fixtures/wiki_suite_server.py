# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real production MCP registration with only external subprocesses substituted."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(Path(__file__).parent)]
from wiki_suite_boundary import install
from wiki_suite_tools import source, create_server

mcp = create_server()
ledger = install(source(), sys.argv[1])


@mcp.tool()
def fixture_ledger() -> dict:
    return {"calls": ledger}


mcp.run(transport="stdio")
