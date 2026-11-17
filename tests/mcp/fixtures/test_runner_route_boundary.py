# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Only external provider discovery/compiler calls are substituted in tests.

The two Python delegates execute unchanged source in temporary repositories.
Unknown external processes fail closed. This module is never imported by the
production service, and no native step or report writer is replaced.
"""

import json
from pathlib import Path
import shutil
import subprocess
import sys


def install_external():
    native_run = subprocess.run

    def external(command, **kwargs):
        if list(command) == ["uname", "-p"] or list(command[:2]) == ["file", "-b"]:
            return native_run(command, **kwargs)
        root = Path(kwargs["cwd"]).resolve()
        if (
            len(command) == 3
            and command[1] == "-c"
            and command[2].startswith("import ")
        ):
            return subprocess.CompletedProcess(
                command, 1, "", "fixture provider unavailable"
            )
        if command[0] == sys.executable and command[1] in (
            "tests/run_quick.py",
            "tests/test_program/run_comprehensive_tests.py",
        ):
            trace = root.parent / "delegates.jsonl"
            with trace.open("a") as stream:
                stream.write(
                    json.dumps({"argv": command, "timeout": kwargs.get("timeout")})
                    + "\n"
                )
            return native_run(command, **kwargs)
        if command[0] != "fixture-test-runner-compiler":
            raise AssertionError(f"unexpected external process: {command!r}")
        assert kwargs["text"] is True
        assert kwargs["stdout"] == subprocess.PIPE
        assert kwargs["stderr"] == subprocess.PIPE
        with (root.parent / "compiler.jsonl").open("a") as stream:
            stream.write(
                json.dumps({"argv": command, "timeout": kwargs["timeout"]}) + "\n"
            )
        mode = command[1]
        if mode == "crash":
            raise OSError("fixture compiler launch failed")
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                command, kwargs["timeout"], output=b"partial"
            )
        if mode == "write":
            (root / "undeclared.txt").write_text(
                "compiler wrote outside declared roots"
            )
        if mode == "artifact":
            (root / "artifacts").mkdir(exist_ok=True)
            (root / "artifacts/compiler.json").write_text('{"compiled":true}')
        return subprocess.CompletedProcess(
            command,
            7 if mode == "fail" else 0,
            json.dumps({"ok": False, "diagnostic": mode}),
            "compiler stderr",
        )

    subprocess.run = external
    # Provider/compiler availability is deterministic and cannot launch a local
    # prover, CLI or provider during dependency-map generation.
    shutil.which = lambda name: None


def serve(root, fixtures):
    import os

    os.environ.clear()
    os.environ.update(
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=os.pathsep.join(
            [str(Path(fixtures) / "test_runner_route_startup"), fixtures]
        ),
    )
    sys.dont_write_bytecode = True
    install_external()
    import mcp_server

    mcp_server._ALLOWED_WRITE_ROOTS = [Path(root).resolve()]
    mcp_server.mcp.run(transport="stdio")
