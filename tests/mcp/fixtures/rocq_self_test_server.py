# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real MCP registrations with a forbidden external compiler boundary."""

from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
from backends.rocq.MathformerRocq import autoformalize as native


def forbidden(*args, **kwargs):
    raise AssertionError("self_test must never invoke an external compiler")


native.subprocess = SimpleNamespace(run=forbidden)
from mcp_server import mcp

mcp.run(transport="stdio")
