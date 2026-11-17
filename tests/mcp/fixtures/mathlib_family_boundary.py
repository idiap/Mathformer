# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline compiler/provider boundary for the mathlib source traversal.

Reuse the strict process allowlist: dependency import probes return unavailable,
only fixture-compiler commands execute (in Python), and every compiler request
is recorded outside the audited repository. No native step or clock is replaced.
"""

from pathlib import Path
from rfde_family_boundary import install


def serve(root):
    from mcp_server import mcp
    from comprehensive_strict_tools import source_runner

    install(source_runner(), Path(root))
    mcp.run(transport="stdio")
