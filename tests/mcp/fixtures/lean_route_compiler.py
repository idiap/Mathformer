# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only Lake discovery and compiler boundary; all hub code runs unchanged."""

from tempfile import gettempdir

import json
from pathlib import Path
import subprocess
from types import SimpleNamespace


def populate(root, mode="success", ready=True):
    root.mkdir(parents=True, exist_ok=True)
    (root / ".compiler-fixture.json").write_text(json.dumps({"mode": mode}))
    for name in ("lakefile.toml", "lean-toolchain"):
        path = root / name
        if ready:
            path.write_text("fixture input\n")
        else:
            path.unlink(missing_ok=True)
    (root / "undeclared.txt").unlink(missing_ok=True)
    (root.parent / "compiler-calls.jsonl").unlink(missing_ok=True)


def install(native, root):
    root = Path(root).resolve()

    def mode():
        return json.loads((root / ".compiler-fixture.json").read_text())["mode"]

    def which(command):
        assert command == "lake", command
        return (
            None
            if mode() == "missing"
            else str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/lake")
        )

    def run(argv, **kwargs):
        assert argv == ["lake", "build"], argv
        assert kwargs == dict(
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=1200,
        ), kwargs
        with (root.parent / "compiler-calls.jsonl").open("a") as stream:
            stream.write(
                json.dumps({"argv": argv, "cwd": str(root), "timeout": 1200}) + "\n"
            )
        outcome = mode()
        if outcome == "crash":
            raise OSError("fixture Lake launch failed")
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(
                argv, 1200, output=b"partial\xff", stderr=b"deadline"
            )
        cache = root / ".lake/build/lib/Fixture.olean"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(b"fixture compiler artifact")
        if outcome == "write":
            (root / "undeclared.txt").write_text("undeclared compiler output")
        return subprocess.CompletedProcess(
            argv,
            7 if outcome == "reject" else 0,
            "Fixture.lean: compiled\n",
            "Fixture.lean:3: type mismatch" if outcome == "reject" else "",
        )

    native.shutil = SimpleNamespace(which=which)
    native.subprocess = SimpleNamespace(
        run=run, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
    )


def serve(root):
    """Run the actual project MCP registration, never an alternate test server."""
    import mathformer as hub
    import mcp_server

    install(hub, root)
    mcp_server._ALLOWED_WRITE_ROOTS = [Path(root).resolve()]
    mcp_server.mcp.run(transport="stdio")
