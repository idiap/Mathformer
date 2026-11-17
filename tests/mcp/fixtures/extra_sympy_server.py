# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only filesystem mount for the production MCP registrations.

No source step is replaced. All generated files, helper subprocess outputs,
source fixtures, snapshots and library paths are confined to the scratch root.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import mathformer as hub
import generate_formalphysics_original_two_sympy as helper

root = Path(sys.argv[1])
hub.REPO_ROOT = root
helper.REPO_ROOT = root
helper.SOURCE_ROOT = root / "data/benchmarks/formal_science/physics_top10_sources"
helper.ARTIFACT_ROOT = root / "artifacts/physics_sympy/from_scratch_sympy"
helper.LIB_ROOT = root / "libraries/MathformerPhysicsLib/SymPy"
if len(sys.argv) > 2 and sys.argv[2] == "incomplete":
    helper.pipeline.REPO_ROOT = root
from mcp_server import mcp

mcp.run(transport="stdio")
