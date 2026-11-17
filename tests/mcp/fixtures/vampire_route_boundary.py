# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Only the external Vampire compiler is replaced; native Python leaf runs normally.

sitecustomize installs this fixture in child Python processes. Neither the hub
launcher nor the route/source/scientific functions are substituted.
"""

import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(Path(__file__).parent)]
from backends.atp.MathformerATP import vampire as v
from atp_demo_boundary import compiler as szs_compiler


def compiler(command, **kwargs):
    assert command[0] == "fixture-vampire", command
    if "--version" not in command:
        path = Path(command[-1])
        root = next(p for p in path.parents if p.name == "atp_function_demo")
        mount = root.parents[2]
        mode = (mount / "fixture-mode").read_text()
        if mode == "write":
            (mount / "undeclared.txt").write_text(
                "compiler boundary wrote outside declared artifacts"
            )
        if mode == "launch_error":
            raise OSError("deterministic compiler launch error")
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                command, 3, output="partial compiler output", stderr="compiler deadline"
            )
    result = szs_compiler(command, **kwargs)
    if (
        "--version" not in command
        and mode == "late"
        and path.name.startswith("candidate_01_")
    ):
        return subprocess.CompletedProcess(
            command, 0, "% SZS status GaveUp\n", "fixture first candidate failed"
        )
    return result


def install():
    # Explicit binary is a compiler fixture parameter, with no environment lookup.
    original = v.VampireRunner

    class FixtureRunner(original):
        def __init__(self, binary=None):
            super().__init__(binary="fixture-vampire")

    v.VampireRunner = FixtureRunner
    # Avoid changing Python's global subprocess module (the hub uses the real one).
    v.subprocess = SimpleNamespace(run=compiler, PIPE=subprocess.PIPE)


def serve(root):
    root = Path(root)
    bootstrap = root / "compiler-bootstrap"
    bootstrap.mkdir()
    (bootstrap / "sitecustomize.py").write_text(
        "from vampire_route_boundary import install\ninstall()\n"
    )
    os.environ["PYTHONPATH"] = os.pathsep.join(
        [
            str(bootstrap),
            str(ROOT / "tests/mcp/fixtures"),
            str(ROOT / "scripts"),
            str(ROOT),
            os.environ.get("PYTHONPATH", ""),
        ]
    )
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    import mcp_server

    mcp_server.mcp.run(transport="stdio")


if __name__ == "__main__":
    serve(sys.argv[1])
