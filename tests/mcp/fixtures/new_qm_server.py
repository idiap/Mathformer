# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Production MCP registration; startup installs only the compiler fixture."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from mcp_server import mcp, apply_runtime_config

apply_runtime_config(allowed_write_roots=[sys.argv[1]])
if __name__ == "__main__":
    mcp.run(transport="stdio")
