# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only process dispatcher: run the real delegate on isolated fixture inputs.

The comprehensive runner, its loop, schemas, ledgers, publication and audits are
unchanged. Only external dependency/provider probes and compiler processes are
replaced. No unknown process is launched and no credentials are consulted.
"""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from comprehensive_strict_tools import source_runner
from rfde_family_boundary import install


class NativeProcess:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.native = source_runner()
        install(self.native, self.root)
        self.calls = []

    def __call__(self, command, **kwargs):
        assert command == [
            sys.executable,
            "tests/test_program/run_comprehensive_tests.py",
            "--module-family",
            "rfde",
            "--json",
        ], command
        assert kwargs == dict(
            cwd=self.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=900,
        ), kwargs
        self.calls.append(list(command))
        with (self.root.parent / "delegate.jsonl").open("a") as ledger:
            ledger.write(
                json.dumps({"command": command, "timeout": kwargs["timeout"]}) + "\n"
            )
        mode = json.loads((self.root.parent / "boundary.json").read_text())["outer"]
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                command, 900, output="partial RFDE", stderr="deadline"
            )
        if mode == "crash":
            raise OSError("fixture process launch failed")
        assert mode == "delegate", mode
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = self.native.main(command[2:])
        return subprocess.CompletedProcess(command, code, stream.getvalue(), "")


def install_hub(hub, root):
    process = NativeProcess(root)
    # Module-local replacement avoids intercepting MCP's transport processes.
    hub.subprocess = SimpleNamespace(
        run=process, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
    )
    return process


def serve(root):
    import os

    os.environ.clear()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    import mcp_server

    install_hub(mcp_server.hub, root)
    mcp_server._ALLOWED_WRITE_ROOTS = [Path(root).resolve()]
    mcp_server.mcp.run(transport="stdio")
