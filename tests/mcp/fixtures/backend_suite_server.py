# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - explicit test runtime and module path setup
"""Test transport using exactly the production registration and native steps."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from physics_backend_suite_tools import source, create_server
from backend_suite_boundary import install

ledger = install(source(), sys.argv[1], sys.argv[2])
mcp = create_server()


@mcp.tool()
def fixture_ledger() -> dict:
    return {"calls": ledger}


mcp.run(transport="stdio")
