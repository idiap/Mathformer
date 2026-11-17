# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test server: real native delegate, external compiler/provider fixtures only."""

import json
from pathlib import Path
import subprocess


def serve(root, fixtures):
    import os
    import sys

    os.environ.clear()
    os.environ.update(
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=os.pathsep.join(
            [str(Path(fixtures) / "environment_route_startup"), fixtures]
        ),
    )
    sys.dont_write_bytecode = True
    import mcp_server

    native = subprocess.run
    mount = Path(root).resolve()

    def delegate(command, **kwargs):
        assert command == [
            sys.executable,
            "tests/test_program/run_comprehensive_tests.py",
            "--module-family",
            "atp",
            "--json",
        ], command
        assert Path(kwargs["cwd"]) == mount
        assert kwargs["timeout"] == 900
        with (mount.parent / "delegate.jsonl").open("a") as stream:
            stream.write(
                json.dumps({"command": command, "timeout": kwargs["timeout"]}) + "\n"
            )
        return native(command, **kwargs)

    # This observer always calls the real native subprocess; child startup
    # substitutes only external provider discovery and compiler commands.
    subprocess.run = delegate
    mcp_server._ALLOWED_WRITE_ROOTS = [mount]
    mcp_server.mcp.run(transport="stdio")
