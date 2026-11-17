# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Named compiler and unavailable-provider fixtures; forbid other processes."""

from pathlib import Path
import subprocess
from types import SimpleNamespace
from comprehensive_strict_boundary import install as install_base


def install(native, root):
    install_base(native, root)
    compiler = native.subprocess.run

    def external(command, **kwargs):
        if command[0] == "fixture-compiler":
            if command[1] == "large":
                return subprocess.CompletedProcess(command, 0, "a" * 5000 + "TAIL", "")
            return compiler(command, **kwargs)
        if (
            len(command) == 3
            and command[1] == "-c"
            and command[2].startswith("import ")
        ):
            # Executable/provider dependency discovery is a deterministic boundary.
            return subprocess.CompletedProcess(command, 1, "", "fixture: unavailable")
        raise AssertionError(f"unexpected external process: {command!r}")

    native.subprocess = SimpleNamespace(
        run=external, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
    )


def serve(root):
    from mcp_server import mcp
    from comprehensive_strict_tools import source_runner

    install(source_runner(), Path(root))
    mcp.run(transport="stdio")
