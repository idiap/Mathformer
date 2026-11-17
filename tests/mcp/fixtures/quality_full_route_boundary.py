# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test compiler/provider boundary; native comprehensive code runs unchanged.

No installed provider is imported or probed. Unexpected process commands fail
closed. The source runner and its reports/audits execute in an isolated mount.
"""

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
            [str(Path(fixtures) / "quality_full_route_startup"), fixtures]
        ),
    )
    sys.dont_write_bytecode = True
    import mcp_server

    native = subprocess.run
    mount = Path(root).resolve()

    def native_process(command, **kwargs):
        # The actual source delegate is the only permitted process in this
        # server scenario. All control leaves are preflight-only or absent.
        assert command[1:] == [
            "tests/test_program/run_comprehensive_tests.py",
            "--module-family",
            "all",
            "--write-jsonl",
            "--write-junit",
            "--json",
        ], command
        assert Path(kwargs["cwd"]) == mount
        assert kwargs["timeout"] == 3600
        with (mount.parent / "delegate.jsonl").open("a") as stream:
            stream.write(
                json.dumps({"command": command, "timeout": kwargs["timeout"]}) + "\n"
            )
        return native(command, **kwargs)

    subprocess.run = native_process
    mcp_server._ALLOWED_WRITE_ROOTS = [mount]
    mcp_server.mcp.run(transport="stdio")
