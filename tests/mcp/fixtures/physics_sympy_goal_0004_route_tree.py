# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated native 0004 source inputs; no generated production artifact is used.

Generation uses the real deterministic pipeline writer. There is no model or
external compiler in this route. Network is forbidden and source processes are
restricted to the scratch mount. Compiler failures have a separate test fixture.
"""

import json
import shutil
import sys


def populate(root, source, *, missing_writer=False):
    sys.path.insert(0, str(source / "tests/mcp"))
    from run_sympy_source_only_workflow_tests import mount

    mount(root)
    (root / "MathformerPhysicsLib").symlink_to(
        "libraries/MathformerPhysicsLib", target_is_directory=True
    )
    artifact = (
        root
        / "libraries/MathformerPhysicsLib/SymPy/formalphysics_0004/MathformerPhysics.py"
    )
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Sentinel input: native regeneration must replace this.\n")
    lean = (
        root
        / "libraries/MathformerPhysicsLib/Lean/formalphysics_0004/MathformerPhysics.lean"
    )
    lean.parent.mkdir(parents=True)
    lean.write_text(
        "-- Synthetic alignment input only, never compiled.\ntheorem local_identity : True := True.intro\n"
    )
    for name in (
        "libraries/MathformerPhysicsLib/physics_ir.py",
        "backends/sympy/MathformerPhysicsSympy/pipeline.py",
    ):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not (missing_writer and name.endswith("pipeline.py")):
            shutil.copyfile(source / name, target)
    record = (
        root
        / "artifacts/physics_sympy/source_only/formalphysics_0004/source_record.json"
    )
    record.parent.mkdir(parents=True)
    record.write_text(
        json.dumps(
            {
                "case_id": "formalphysics_0004",
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
    from physics_sympy_goal_route_tree import serve as native_service

    native_service(base)
