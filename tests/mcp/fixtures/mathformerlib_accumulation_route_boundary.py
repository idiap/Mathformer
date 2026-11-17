# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only external compiler/provider process boundary.

The comprehensive runner executes as a real Python process from
byte-identical source copies in temporary mounts. Only external compilers and
dependency discovery are substituted; no native controller step is replaced.
"""

import json
from pathlib import Path
import shutil
import subprocess


def install_external():
    native_run = subprocess.run

    def external(command, **kwargs):
        # Python's platform.platform() uses this standard-library host query.
        # It is neither a compiler nor a provider, so execute it unchanged.
        if list(command) == ["uname", "-p"] or (
            len(command) == 3 and command[:2] == ["file", "-b"]
        ):
            return native_run(command, **kwargs)
        root = Path(kwargs["cwd"]).resolve()
        # Dependency/provider availability is an external boundary. Never probe
        # installed providers, credentials or local theorem-prover binaries.
        if (
            len(command) == 3
            and command[1] == "-c"
            and command[2].startswith("import ")
        ):
            return subprocess.CompletedProcess(command, 1, "", "fixture unavailable")
        if command[0] == "fixture-accumulation-compiler":
            mode = command[1]
        elif (
            len(command) == 3
            and command[-1] == "--help"
            and "skills/mathformerlib/" in command[1]
        ):
            modes = json.loads((root.parent / "modes.json").read_text())
            mode = modes[0 if "manage_mathformerlib_registry" in command[1] else 1]
        else:
            raise AssertionError(f"unexpected external process: {command!r}")
        assert kwargs["text"] is True
        assert kwargs["stdout"] == subprocess.PIPE
        assert kwargs["stderr"] == subprocess.PIPE
        with (root.parent / "compiler.jsonl").open("a") as stream:
            stream.write(
                json.dumps({"command": command, "timeout": kwargs["timeout"]}) + "\n"
            )
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                command, kwargs["timeout"], output=b"partial"
            )
        if mode == "crash":
            raise OSError("fixture compiler launch failed")
        if mode == "write":
            (root / "undeclared.txt").write_text("compiler wrote outside its roots")
        if mode == "artifact":
            output = root / "artifacts/compiler.txt"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("compiled")
        return subprocess.CompletedProcess(
            command,
            7 if mode == "fail" else 0,
            "x" * 5000 + "TAIL" if mode == "large" else "compiled " + mode,
            "compiler stderr" if mode == "fail" else "",
        )

    subprocess.run = external
    shutil.which = lambda name: None


def serve(root, fixture_path):
    """Use the actual registered server with an explicit isolated write root."""
    import os
    import sys
    import mcp_server

    # Do not inherit credentials, client config or provider choices into the
    # real native child process. sitecustomize installs only external fixtures.
    os.environ.clear()
    os.environ.update(
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=os.pathsep.join(
            [str(Path(fixture_path) / "accumulation_route_startup"), fixture_path]
        ),
    )
    sys.dont_write_bytecode = True
    mcp_server._ALLOWED_WRITE_ROOTS = [Path(root).resolve()]
    mcp_server.mcp.run(transport="stdio")
