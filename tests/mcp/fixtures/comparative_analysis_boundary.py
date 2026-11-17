# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic external Lean boundary and disposable report repository.

No provider is called by this workflow: judge results are imported evidence.
Only lake/env/lean is substituted; parsing, traversal and report generation run.
"""

from pathlib import Path
import subprocess

SOURCE = "skills/physics-common/formalphysics-comparative-analysis-reporter/scripts/build_comparative_report.py"
SMOKE = "tests/physics_lean/run_formalphysics_comparative_report.py"
CODE = "import Mathlib\n\ntheorem force_identity (force : Real) : force = force := by rfl\n"


def put(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def populate(root, source):
    for name in [
        SOURCE,
        str(Path(SOURCE).with_name("prepare_comparison_inputs.py")),
        SMOKE,
    ]:
        put(root, name, (source / name).read_text())
    for base in ["MathformerPhysicsLib", "libraries/MathformerPhysicsLib"]:
        put(
            root,
            base + "/Lean/Foundations.lean",
            "import Mathlib\nnamespace Foundations\ndef force (x : Real) := x\nend Foundations\n",
        )
    for index in range(3):
        put(
            root,
            f"MathformerPhysicsLib/Lean/formalphysics_{index:04d}/MathformerPhysics.lean",
            CODE,
        )


class LeanCompiler:
    def __init__(self, modes, cwd, timeout):
        self.modes = list(modes)
        self.cwd, self.timeout = cwd, timeout
        self.calls = []

    def run(self, argv, **kwargs):
        assert argv[:3] == ["lake", "env", "lean"], argv
        assert kwargs == dict(
            cwd=self.cwd, text=True, capture_output=True, timeout=self.timeout
        ), kwargs
        assert Path(argv[3]).read_text() == CODE
        mode = self.modes[len(self.calls)]
        self.calls.append(mode)
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                argv, self.timeout, output="partial", stderr="deadline"
            )
        if mode == "crash":
            raise OSError("compiler fixture launch failed")
        return subprocess.CompletedProcess(
            argv,
            3 if mode == "fail" else 0,
            "error: rejected" if mode == "fail" else "warning: fixture",
            "",
        )


def serve(root):
    """Actual MCP registrations with a process allowlist on the isolated mount."""
    import sys
    import mathformer as hub
    import mcp_server
    from comparative_analysis_route_tools import ACTIONS

    root = Path(root).resolve()
    commands = {
        tuple(hub.resolve_command(hub.build_registry()[key].command)) for key in ACTIONS
    }

    def guard(event, args):
        if event in {"socket.connect", "socket.getaddrinfo", "os.system"}:
            raise AssertionError("unexpected external boundary: " + event)
        if event == "subprocess.Popen":
            assert tuple(args[1]) in commands and Path(args[2]).resolve() == root, args

    sys.addaudithook(guard)
    mcp_server._ALLOWED_WRITE_ROOTS = [root]
    mcp_server.mcp.run(transport="stdio")
