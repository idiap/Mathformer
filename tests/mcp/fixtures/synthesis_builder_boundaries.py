# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only external provider/compiler fences; the reporter has neither."""

import socket
import subprocess
import sys


def forbidden(*args, **kwargs):
    raise AssertionError(
        "synthesis must not call a provider or external compiler/prover"
    )


def install():
    saved = (
        subprocess.run,
        subprocess.Popen,
        socket.create_connection,
        socket.socket.connect,
    )
    original_popen = subprocess.Popen

    class StdioOnly(original_popen):
        def __init__(self, command, *args, **kwargs):
            # The sole allowed process boundary is the real MCP server.
            if (
                not isinstance(command, (tuple, list))
                or len(command) != 3
                or command[0] != sys.executable
                or command[1] != "-c"
                or 'mcp.run(transport="stdio")' not in command[2]
            ):
                forbidden(command)
            super().__init__(command, *args, **kwargs)

    subprocess.run = forbidden
    subprocess.Popen = StdioOnly
    socket.create_connection = forbidden
    socket.socket.connect = forbidden
    return saved


def restore(saved):
    (
        subprocess.run,
        subprocess.Popen,
        socket.create_connection,
        socket.socket.connect,
    ) = saved
