# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - test entrypoint configures import paths before dependencies.
"""Test-only mount: real registered tools and child CLIs, scratch artifacts."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
from sympy_source_only_tools import source
from mcp_server import mcp, apply_runtime_config

root = Path(sys.argv[1])
native = source()
native.REPO_ROOT = root
native.SYMPY_ROOT = root / "MathformerPhysicsLib/SymPy"
for name in (
    "GOAL_PLANNER",
    "DESIGN_GUARD",
    "CARTOGRAPHER",
    "CONTROLLER",
    "THOROUGHNESS",
):
    setattr(native, name, root / getattr(native, name).relative_to(ROOT))
apply_runtime_config(allowed_write_roots=[str(root)])
mcp.run(transport="stdio")
