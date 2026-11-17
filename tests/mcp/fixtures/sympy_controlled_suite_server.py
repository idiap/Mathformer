# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated write mount; all registered source operations execute unchanged."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
from mcp.server.fastmcp import FastMCP
from sympy_controlled_suite_tools import register_sympy_controlled_suite_tools

root = Path(sys.argv[1]).resolve()
server = FastMCP("controlled-suite-fixture")


def before_write():
    if len(sys.argv) > 2 and sys.argv[2] == "readonly":
        raise ValueError("Fixture service is read-only")


register_sympy_controlled_suite_tools(
    server, before_write, lambda path: path.resolve().is_relative_to(root)
)
server.run(transport="stdio")
