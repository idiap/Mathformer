# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Observe native Python subprocesses; prohibit all other process boundaries.

Used only by fixture subprocesses. Every selected CLI runs its real source with
its original argv and timeout. The ledger is outside the audited fixture tree.
"""

import json
import os
from pathlib import Path
import subprocess

ROOT = Path(os.environ["TEXTBOOK_ROUTE_ROOT"]).resolve()
real_run = subprocess.run


def run(command, **kwargs):
    command = [str(v) for v in command]
    if command == ["uname", "-p"] or command[:2] == ["file", "-b"]:
        return real_run(command, **kwargs)
    assert Path(command[0]).name.startswith("python"), command
    if command[1] == "-c":
        assert len(command) == 3 and command[2] in {
            "import docling",
            "import mcp",
            "import httpx",
            "import uvicorn",
            "import sympy",
            "import sympy.physics.units",
            "import sympy.physics.mechanics",
            "import bs4",
            "import matplotlib",
        }, command
    else:
        script = (Path(kwargs["cwd"]) / command[1]).resolve()
        assert script.is_relative_to(ROOT), command
        assert command[2:] == ["--self-test", "--json"], command
    with (ROOT.parent / "processes.jsonl").open("a") as ledger:
        ledger.write(
            json.dumps({"command": command, "timeout": kwargs["timeout"]}) + "\n"
        )
    return real_run(command, **kwargs)


subprocess.run = run
