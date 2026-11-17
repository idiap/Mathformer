# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Production registrations with fail-closed external boundaries for tests.

This dependency-free leaf has no provider or theorem compiler. Do not invent
one: forbid network and scientific processes. Only the real planner's invalid
CLI fixture is admitted; it exits before reading a scientific case or gates.
"""

from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
from sympy_expansion_tools import source

native_run = subprocess.run


def deny(*args, **kwargs):
    raise AssertionError("external provider/compiler access forbidden in map fixtures")


def guarded_run(argv, *args, **kwargs):
    assert argv == [
        sys.executable,
        str(source().PLANNER),
        "--case",
        "invalid-fixture-case",
        "--run-gates",
        "--json",
    ], argv
    assert kwargs["timeout"] == 240
    assert kwargs["cwd"] == ROOT
    return native_run(argv, *args, **kwargs)


socket.create_connection = deny
socket.socket.connect = deny
subprocess.run = guarded_run

from mcp_server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
