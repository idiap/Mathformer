# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic Lake compiler boundary; only imported by offline tests."""

import json
import os
from pathlib import Path
import sys


def boundary():
    root = Path.cwd().resolve()
    args = sys.argv[1:]
    assert args in [["update"], ["build"]], args
    mode = (root.parent / "mode.txt").read_text()
    with (root.parent / "lake.jsonl").open("a") as stream:
        stream.write(
            json.dumps({"argv": [sys.argv[0], *args], "cwd": str(root)}) + "\n"
        )
    if mode == args[0] + "_failure":
        print("fixture lake " + args[0] + " failed", file=sys.stderr)
        return 8
    path = root / ".lake" / args[0]
    path.parent.mkdir(exist_ok=True)
    path.write_text("deterministic compiler receipt")
    if mode == "undeclared_write":
        (root / "unexpected.txt").write_text("fixture unexpected write")
    print("fixture lake " + args[0] + " succeeded")
    return 0


def serve(root, binary):
    """Use real production MCP registration with no credentials or providers."""
    os.environ.clear()
    os.environ.update(
        PATH=str(binary), PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1"
    )
    sys.dont_write_bytecode = True
    import mcp_server

    mcp_server._READONLY = False
    mcp_server._ALLOWED_WRITE_ROOTS = [Path(root)]
    mcp_server.mcp.run(transport="stdio")
