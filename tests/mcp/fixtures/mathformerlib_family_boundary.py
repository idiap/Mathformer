# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only external process/provider boundary; native orchestration stays real."""

import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from comprehensive_workflow_boundary import install as install_base


def install(native, root):
    install_base(native, root)
    compiler = native.subprocess.run

    def external(command, **kwargs):
        if (
            len(command) == 3
            and command[-1] == "--help"
            and "skills/mathformerlib/" in command[1]
        ):
            modes = json.loads((Path(root) / "boundary.json").read_text())
            mode = modes[0 if "manage_mathformerlib_registry" in command[1] else 1]
            assert kwargs["timeout"] == 120
            return compiler(["fixture-compiler", mode], **kwargs)
        return compiler(command, **kwargs)

    native.subprocess = SimpleNamespace(
        run=external, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
    )


def serve(root):
    from mcp_server import mcp
    from comprehensive_strict_tools import source_runner

    install(source_runner(), Path(root))
    mcp.run(transport="stdio")
