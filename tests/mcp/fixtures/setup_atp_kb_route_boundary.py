# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline uv boundary. Real native installer/controller processes run unchanged.

Only uv's environment/provider boundary is substituted. All unexpected argv
fail closed, so no pip, Lean, compiler, credential or network access is possible.
"""

import json
import os
from pathlib import Path
import subprocess
import sys


def uv():
    root = Path.cwd().resolve()
    mode = (root.parent / "mode.txt").read_text()
    args = sys.argv[1:]
    with (root.parent / "uv.jsonl").open("a") as stream:
        stream.write(json.dumps(args) + "\n")
    if args == ["run", "python", "scripts/install_env.py", "--with-atp-kb"]:
        if mode == "launch_failure":
            print("fixture uv launcher failed", file=sys.stderr)
            return 9
        environment = dict(os.environ)
        if mode == "installer_missing_uv":
            environment["PATH"] = str(root.parent / "absent")
        return subprocess.run(
            [sys.executable, *args[2:]], env=environment, check=False
        ).returncode
    assert args == ["venv", str(root / ".venv")], args
    if mode == "venv_failure":
        print("fixture uv venv failed", file=sys.stderr)
        return 7
    if mode != "missing_python":
        path = (
            root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture interpreter placeholder; never executed")
    if mode == "undeclared_write":
        (root / "unexpected.txt").write_text("fixture uv write outside declared roots")
    print("fixture venv created")
    return 0


def serve(root, binary, readonly=False, deny_writes=False):
    """Load the production MCP registration, with isolated service roots/env."""
    os.environ.clear()
    os.environ.update(
        PATH=str(binary), PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1"
    )
    sys.dont_write_bytecode = True
    import mcp_server

    mcp_server._READONLY = readonly
    mcp_server._ALLOWED_WRITE_ROOTS = [
        Path(root) / "denied" if deny_writes else Path(root)
    ]
    mcp_server.mcp.run(transport="stdio")


if __name__ == "__main__":
    raise SystemExit(uv())
