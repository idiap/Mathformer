# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only Python process boundary, running real native sources in temp roots.

The suite and every stage execute their real entrypoints. The existing local
Python transport fixture runs SymPy checks in-process; it never launches an
external compiler, prover, provider, or production workflow. No production
binding or registry entry is changed. Faults exist only at the Python launch
boundary. There is no model/provider in the selected source.
"""

from contextlib import chdir, redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
from types import SimpleNamespace
from unittest.mock import patch

from sympy_controlled_suite_tools import source
from sympy_equational_trace_boundary import install as install_stages, forbidden

SCRIPT = "tests/sympy/run_controlled_suite.py"
OUTPUT = "artifacts/sympy/controlled_suite"


def populate(root, project, mode=None):
    root.mkdir(parents=True)
    for relative in [Path(SCRIPT), *source().SOURCES]:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(project / relative, target)
    if mode:
        (root / "boundary.json").write_text(json.dumps(mode))
    return root


def install(hub, base):
    native = source()
    install_stages(native)
    launches = []

    def run(command, *, cwd, text, stdout, stderr, timeout):
        root = Path(cwd).resolve()
        assert root.is_relative_to(base) and root != hub.REPO_ROOT
        assert command == [
            *hub.resolve_command(hub.build_registry()["sympy:controlled"].command)
        ]
        assert command[1:] == [SCRIPT, "--json"]
        assert text and stdout == subprocess.PIPE and stderr == subprocess.PIPE
        assert timeout is None  # no invented outer native timeout
        launches.append({"argv": command, "cwd": str(root), "timeout": timeout})
        mode_path = root / "boundary.json"
        mode = json.loads(mode_path.read_text()) if mode_path.exists() else {}
        if mode.get("outer") == "launch":
            raise OSError("fixture Python launch failed")
        out, err = io.StringIO(), io.StringIO()
        token = native.WORKING_DIRECTORY.set(root)
        try:
            with (
                chdir(root),
                patch.object(sys, "argv", command[1:]),
                redirect_stdout(out),
                redirect_stderr(err),
            ):
                try:
                    code = native.main()
                except Exception:
                    traceback.print_exc()
                    code = 1
        finally:
            native.WORKING_DIRECTORY.reset(token)
            ledger = root / "commands.jsonl"
            if ledger.exists():
                destination = root / "artifacts/sympy/commands.jsonl"
                destination.parent.mkdir(parents=True, exist_ok=True)
                ledger.replace(destination)
        if mode.get("outer") == "write":
            (root / "unexpected.txt").write_text("undeclared compiler output")
        return subprocess.CompletedProcess(
            command, code, out.getvalue(), err.getvalue()
        )

    hub.subprocess = SimpleNamespace(
        run=run, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
    )
    return launches


def serve(base):
    import socket
    import mathformer as hub
    from mcp_server import mcp, apply_runtime_config

    base = Path(base).resolve()
    install(hub, base)
    socket.create_connection = forbidden
    # All other OS process launches fail closed. MCP stdio is already running.
    subprocess.Popen = forbidden
    apply_runtime_config(allowed_write_roots=[str(base)])

    @mcp.tool()
    def fixture_sympy_route_original(
        context: dict, match: dict, registry: dict, repository_root: str
    ) -> dict:
        """Frozen original entrypoint in the same interpreter/dependency context."""
        from sympy_route_tools import selected_match, checked_registry

        root = Path(repository_root).resolve()
        assert root.is_relative_to(base) and root != hub.REPO_ROOT
        scope = dict(vars(hub))
        exec(Path(__file__).with_name("sympy_route_original.py.txt").read_text(), scope)
        return scope["run_intent_match"](
            selected_match(match),
            checked_registry(registry),
            hub.RunContext(**context),
            repository_root=root,
        )

    mcp.run(transport="stdio")
