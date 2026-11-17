# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Only external compiler boundaries are substituted; native Python runs unchanged."""

from tempfile import gettempdir

import json
from pathlib import Path
import shutil
import subprocess

RELEASE = ["tests/physics_lean/run_mathformerphysicslib_release_gate.py", "--json"]
COHERENCE = [
    "skills/mathformerphysicslib/mathformerphysicslib-coherence-gate/scripts/gate_coherence.py",
    "--require-release",
    "--json",
]


def install():
    native = subprocess.run
    native_which = shutil.which

    def run(command, **kwargs):
        # Standard-library host queries execute unchanged. Provider availability
        # and external compiler version probes never load installed providers.
        if list(command) == ["uname", "-p"] or (
            len(command) == 3 and command[:2] == ["file", "-b"]
        ):
            return native(command, **kwargs)
        if (
            len(command) == 3
            and command[1] == "-c"
            and command[2].startswith("import ")
        ):
            return subprocess.CompletedProcess(
                command, 1, "", "fixture provider unavailable"
            )
        if list(command) == ["lake", "--version"]:
            return subprocess.CompletedProcess(command, 0, "fixture lake version", "")
        root = Path(kwargs["cwd"]).resolve()
        mode_path = root.parent / "compiler-mode.json"
        modes = json.loads(mode_path.read_text())
        with (root.parent / "processes.jsonl").open("a") as stream:
            stream.write(
                json.dumps({"command": command, "timeout": kwargs.get("timeout")})
                + "\n"
            )
        # These are real source subprocesses, not substitutes. Docs' native
        # subprocess.call delegate also runs the unchanged comprehensive source.
        if command[1:] in [RELEASE, COHERENCE, ["tests/run_docs.py", "--json"]]:
            if command[1:] == RELEASE:
                assert kwargs["timeout"] == 1200
            if command[1:] == COHERENCE:
                assert kwargs["timeout"] == 180
            return native(command, **kwargs)
        if command == ["lake", "build", "MathformerPhysicsLib"]:
            assert kwargs["timeout"] == 900
            mode = modes["build"]
        elif command == ["lake", "env", "lean", "--version"]:
            assert kwargs["timeout"] == 30
            mode = modes["version"]
        elif command[:1] == ["fixture-framework-provider"]:
            assert kwargs["timeout"] == 17
            mode = modes["docs"]
        else:
            raise AssertionError(f"unexpected process: {command!r}")
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                command,
                kwargs["timeout"],
                output=b"partial compiler output",
                stderr=b"fixture timeout",
            )
        if mode == "crash":
            raise OSError("fixture compiler launch failed")
        if mode == "write":
            (root / "undeclared.txt").write_text("external compiler output")
        if mode == "artifact":
            output = root / ".lake/fixture.olean"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("fixture compiler output")
        return subprocess.CompletedProcess(
            command,
            7 if mode == "fail" else 0,
            "deterministic compiler evidence",
            "fixture diagnostic" if mode == "fail" else "",
        )

    subprocess.run = run
    # Discovery of the external compiler is also a test boundary. Never inspect
    # installed provers/providers or credentials.
    shutil.which = lambda name: (
        str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/lake")
        if name == "lake"
        else native_which(name) if name == "git" else None
    )


def serve(root, fixtures):
    import os
    import sys

    os.environ.clear()
    os.environ.update(
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=os.pathsep.join(
            [str(Path(fixtures) / "framework_review_startup"), fixtures]
        ),
    )
    sys.dont_write_bytecode = True
    install()
    import mcp_server

    mcp_server._ALLOWED_WRITE_ROOTS = [Path(root).resolve()]
    mcp_server.mcp.run(transport="stdio")
