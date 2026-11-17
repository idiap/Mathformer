# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Disposable native report inputs and fail-closed external boundaries.

This route consumes recorded compiler/judge evidence and never invokes either.
Every allowed subprocess executes the actual source, without substitutions.
"""

import json
import os
from pathlib import Path
import subprocess
import sys

SOURCE = "skills/physics-common/formalphysics-judge-synthesis-reporter/scripts/build_synthesis_report.py"
SMOKE = "tests/physics_lean/run_formalphysics_judge_synthesis_report.py"
PROTOCOL = "skills/physics-common/formalphysics-judge-synthesis-reporter/references/synthesis_protocol.md"
INPUT = "artifacts/formalphysics_comparative_analysis/hub_selected_examples_report/comparative_report.json"
OUTPUT = "artifacts/formalphysics_judge_synthesis/hub_selected_examples"


def put(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def populate(root, project):
    from judge_synthesis_report_tools import source

    for name in [SOURCE, SMOKE, PROTOCOL]:
        put(root, name, (project / name).read_text())
    path = root / INPUT
    path.parent.mkdir(parents=True, exist_ok=True)
    # The native synthetic fixture includes accepted/blocked compiler receipts,
    # deterministic scores, expert reviews and pending external judges.
    source().write_comparative_report(path)


def install():
    """Observe real subprocess timeout arguments; deny provider/prover launches."""
    root = Path(os.environ["JUDGE_SYNTHESIS_TEST_ROOT"]).resolve()
    native_run = subprocess.run
    log = root.parent / "native-processes.jsonl"

    def observed(command, *args, **kwargs):
        with log.open("a") as stream:
            stream.write(
                json.dumps(
                    {
                        "argv": list(command),
                        "timeout": kwargs.get("timeout"),
                        "cwd": str(kwargs.get("cwd")),
                    }
                )
                + "\n"
            )
        return native_run(command, *args, **kwargs)

    def guard(event, args):
        if event in {"socket.connect", "socket.getaddrinfo", "os.system"}:
            raise AssertionError(
                "unexpected external provider/compiler boundary: " + event
            )
        if event == "subprocess.Popen":
            argv = args[1]
            if (
                len(argv) < 2
                or Path(argv[0]).resolve() != Path(sys.executable).resolve()
                or Path(argv[1]).suffix != ".py"
            ):
                raise AssertionError("unexpected external provider/compiler process")
            cwd = Path(args[2] or Path.cwd()).resolve()
            script = (cwd / argv[1]).resolve()
            if script not in {(root / SMOKE).resolve(), (root / SOURCE).resolve()}:
                raise AssertionError(
                    "process is outside native disposable report source"
                )
            if cwd != root:
                raise AssertionError("native process cwd changed")

    subprocess.run = observed
    sys.addaudithook(guard)


def serve(root, startup, fixtures):
    """Import production MCP registration without service config or credentials."""
    os.environ.clear()
    os.environ.update(
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=os.pathsep.join([startup, fixtures]),
        JUDGE_SYNTHESIS_TEST_ROOT=root,
    )
    sys.dont_write_bytecode = True
    install()
    import mcp_server

    mcp_server._ALLOWED_WRITE_ROOTS = [Path(root).resolve()]
    mcp_server.mcp.run(transport="stdio")
