# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Synthetic artifact inputs and relocated, unchanged native Python steps.

No source step or report is substituted. There is no model/provider call or
external compiler in this route: supplied executable artifact inputs are its
deterministic boundary. A separate compiler fixture tests hub process failures.
"""

import json
from pathlib import Path
import shutil
import sys


def populate(root, source, mode="complete", *, audit_fault=False):
    sys.path.insert(0, str(source / "tests/mcp"))
    from run_sympy_source_only_workflow_tests import mount, artifact

    mount(root)
    # Keep callback observations outside the audited mount, unless specifically
    # testing a successful process overridden by the native write audit.
    text = artifact(mode)
    if not audit_fault:
        text = text.replace(
            "Path(__file__).with_suffix('.history.jsonl')",
            "Path(" + repr(str(root.parent / "callbacks.jsonl")) + ")",
        )
    path = (
        root
        / "libraries/MathformerPhysicsLib/SymPy/formalphysics_0000/MathformerPhysics.py"
    )
    path.parent.mkdir(parents=True)
    path.write_text(text)
    # Preserve the native legacy and current artifact paths without modifying
    # either the hub's required_paths or the source scripts' path resolution.
    (root / "MathformerPhysicsLib").symlink_to(
        "libraries/MathformerPhysicsLib", target_is_directory=True
    )
    lean = (
        root
        / "libraries/MathformerPhysicsLib/Lean/formalphysics_0000/MathformerPhysics.lean"
    )
    lean.parent.mkdir(parents=True)
    lean.write_text(
        "-- Synthetic alignment input only; never compiled.\ntheorem local_identity : True := True.intro\n"
    )
    for name in (
        "libraries/MathformerPhysicsLib/physics_ir.py",
        "backends/sympy/MathformerPhysicsSympy/pipeline.py",
    ):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    record = (
        root
        / "artifacts/physics_sympy/source_only/formalphysics_0000/source_record.json"
    )
    record.parent.mkdir(parents=True)
    record.write_text(
        json.dumps(
            {
                "case_id": "formalphysics_0000",
                "statement_nl": "Local source",
                "statement_latex": "x=x",
                "source_anchors": ["L1"],
            }
        )
    )
    python = root / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    return root


def serve(base):
    """Real service registration, restricted to temporary repository mounts."""
    import socket
    import subprocess
    import mathformer as hub
    from mcp_server import mcp, apply_runtime_config

    base = Path(base).resolve()
    run = subprocess.run

    def guarded(command, **kwargs):
        cwd = Path(kwargs["cwd"]).resolve()
        assert cwd.is_relative_to(base) and cwd != hub.REPO_ROOT
        script = (cwd / command[1]).resolve()
        assert script.is_relative_to(cwd) and script.suffix == ".py"
        assert command[0] == ".venv/bin/python"
        with (base / "commands.jsonl").open("a") as ledger:
            ledger.write(
                json.dumps({"command": command, "timeout": kwargs["timeout"]}) + "\n"
            )
        return run(command, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected network/provider boundary")

    subprocess.run = guarded
    socket.create_connection = forbidden
    apply_runtime_config(allowed_write_roots=[str(base)])
    mcp.run(transport="stdio")
