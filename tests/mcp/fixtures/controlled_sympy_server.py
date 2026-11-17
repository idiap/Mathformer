# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Scratch filesystem mount; all source computations and registrations are real."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from controlled_sympy_tools import source

source().REPO_ROOT = Path(sys.argv[1])
from mcp_server import mcp

# Observe native write ordering, without replacing any source operation.
writes = []


def observe(event, args):
    if (
        event == "open"
        and isinstance(args[0], str)
        and args[1]
        and any(c in args[1] for c in "wax")
    ):
        path = Path(args[0])
        if path.is_relative_to(source().REPO_ROOT / "out"):
            writes.append(str(path.relative_to(source().REPO_ROOT)))


sys.addaudithook(observe)


@mcp.tool()
def fixture_writes() -> dict:
    result = list(writes)
    writes.clear()
    return {"writes": result}


mcp.run(transport="stdio")
