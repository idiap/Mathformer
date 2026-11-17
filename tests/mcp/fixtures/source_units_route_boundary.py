# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only compiler/provider fixtures; native Python steps execute unchanged.

The real hub launches the real comprehensive runner in a temporary repository.
Only named external compiler and dependency-discovery calls are substituted.
No production module imports this fixture or offers a mock-mode switch.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def install_external():
    native_run = subprocess.run
    # Fix clocks for reproducible native receipts, histories and report IDs.
    time.time = lambda: 1234567890.0
    shutil.which = lambda name: None

    def external(command, **kwargs):
        if list(command) == ["uname", "-p"] or list(command[:2]) == ["file", "-b"]:
            return native_run(command, **kwargs)
        if (
            len(command) == 3
            and command[1] == "-c"
            and command[2].startswith("import ")
        ):
            return subprocess.CompletedProcess(
                command, 1, "", "fixture provider unavailable"
            )
        root = Path(kwargs["cwd"]).resolve()
        if command[0] == "fixture-source-compiler":
            assert kwargs["text"] and kwargs["stdout"] == subprocess.PIPE
            assert kwargs["stderr"] == subprocess.PIPE
            with (root.parent / "compiler.jsonl").open("a") as stream:
                stream.write(
                    json.dumps({"command": command, "timeout": kwargs["timeout"]})
                    + "\n"
                )
            mode = command[1]
            if mode == "timeout":
                raise subprocess.TimeoutExpired(
                    command, kwargs["timeout"], output="partial"
                )
            if mode == "crash":
                raise OSError("fixture compiler launch failed")
            if mode == "write":
                (root / "undeclared.txt").write_text("undeclared compiler output")
            return subprocess.CompletedProcess(
                command, 7 if mode == "fail" else 0, "compiled " + mode, ""
            )
        # Permit only the actual native runner and canonical source self-tests.
        if len(command) >= 2 and command[1] in NATIVE_PYTHON_PATHS:
            with (root.parent / "native-launch.jsonl").open("a") as stream:
                stream.write(
                    json.dumps({"command": command, "timeout": kwargs["timeout"]})
                    + "\n"
                )
            return native_run(command, **kwargs)
        raise AssertionError(f"unexpected external process: {command!r}")

    subprocess.run = external


NATIVE_PYTHON_PATHS = {
    "tests/test_program/run_comprehensive_tests.py",
    "skills/autoformalization/source-formalizable-unit-extractor/scripts/extract_autoformalizable_units.py",
    "skills/autoformalization/source-line-translation-packet-builder/scripts/build_line_translation_packet.py",
    "skills/autoformalization/source-formalization-drift-guard/scripts/validate_source_formalization_alignment.py",
    "skills/lean/lean-line-annotation/scripts/validate_lean_line_comments.py",
}


def serve(root, fixture_path):
    import sys
    import mcp_server

    # Start without configuration/credential reads; child probes see no secrets.
    os.environ.clear()
    os.environ.update(
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=os.pathsep.join(
            [str(Path(fixture_path) / "source_units_route_startup"), fixture_path]
        ),
    )
    sys.dont_write_bytecode = True
    mcp_server._ALLOWED_WRITE_ROOTS = [Path(root).resolve()]
    install_external()
    mcp_server.mcp.run(transport="stdio")
