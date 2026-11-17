# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline compiler fixture; all repository Python processes execute unchanged."""

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


def install_external():
    native = subprocess.run

    def run(command, **kwargs):
        command = list(command)
        root = Path(kwargs.get("cwd", Path.cwd())).resolve()
        if len(command) >= 4 and command[1:3] == ["env", "lean"]:
            assert Path(command[0]).name == "lake", command
            path = Path(command[3]).resolve()
            assert path.is_relative_to(root), (path, root)
            mode = (root.parent / "compiler-mode").read_text()
            with (root.parent / "compiler.jsonl").open("a") as stream:
                stream.write(
                    json.dumps(
                        {
                            "path": str(path.relative_to(root)),
                            "timeout": kwargs.get("timeout"),
                        }
                    )
                    + "\n"
                )
            if mode == "crash":
                raise OSError("fixture compiler launch failed")
            if mode == "timeout" and path.name == "gold.lean":
                raise subprocess.TimeoutExpired(
                    command, kwargs.get("timeout"), output="partial"
                )
            if mode == "write":
                (root / "undeclared.txt").write_text("fixture compiler side effect")
            checks = re.findall(r"^#check\s+(.+)$", path.read_text(), re.MULTILINE)
            stdout = "\n".join(name + " : Prop" for name in checks)
            if (
                mode == "declaration-missing"
                and path.name == "expected_declaration_checks.lean"
            ):
                stdout = ""
            failed = mode == "fail"
            return subprocess.CompletedProcess(
                command,
                1 if failed else 0,
                stdout,
                f"{path}:1:1: error: deterministic compiler failure" if failed else "",
            )
        if command[0] == "rg":
            assert Path(command[-1]).resolve().is_relative_to(root), command
            return native(command, **kwargs)
        if (
            command[0] == sys.executable
            and len(command) > 1
            and command[1].endswith(".py")
        ):
            path = (root / command[1]).resolve()
            assert path.is_relative_to(root), command
            assert path.is_file(), command
            with (root.parent / "native.jsonl").open("a") as stream:
                stream.write(
                    json.dumps({"script": command[1], "timeout": kwargs.get("timeout")})
                    + "\n"
                )
            return native(command, **kwargs)
        raise AssertionError(f"unexpected process boundary: {command!r}")

    subprocess.run = run
    # Compiler discovery is external; prevent any installed prover lookup.
    shutil.which = lambda name, *a, **kw: "lake" if name == "lake" else None


def serve(root, fixtures):
    import os

    native_path = os.environ.get("PATH", os.defpath)
    os.environ.clear()
    os.environ.update(
        PATH=native_path,
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=os.pathsep.join(
            [str(Path(fixtures) / "lean_fixture_startup"), fixtures]
        ),
    )
    sys.dont_write_bytecode = True
    import mcp_server

    install_external()
    mcp_server._ALLOWED_WRITE_ROOTS = [Path(root).resolve()]
    mcp_server.mcp.run(transport="stdio")
