# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only server: actual production registration, isolated process boundaries."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(Path(__file__).parent)]
from e2e_all_backends_boundary import install
from e2e_all_backends_tools import source

install(source(), Path(sys.argv[1]), sys.argv[2])
from mcp_server import mcp

mcp.run(transport="stdio")
