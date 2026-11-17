# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402
"""Real MCP registration with a temporary repository mounted for tests."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from derivation_regression_tools import source, create_server
from derivation_regression_mount import configure

calls = configure(source(), sys.argv[1])
mcp = create_server()


@mcp.tool()
def fixture_ledger(clear: bool = False) -> dict:
    result = {"calls": list(calls)}
    if clear:
        calls.clear()
    return result


mcp.run(transport="stdio")
