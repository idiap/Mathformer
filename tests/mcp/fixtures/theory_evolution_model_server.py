# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Serve the real aggregate registrations with explicit, credential-free policy.

Bypass only CLI configuration discovery: no provider or compiler is replaced.
All tool implementations, service guards and MCP transport are production code.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import mcp_server

mcp_server.apply_runtime_config(allowed_write_roots=[sys.argv[1]])
mcp_server.mathformer_serve_apply_policy(
    {"runtime": {"readonly": "--readonly" in sys.argv[2:]}}
)
mcp_server.mcp.run(transport="stdio")
