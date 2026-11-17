# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test interpreter startup: replace only Lake's external compiler boundary.

All native Python JSON helpers still execute as real child processes with their
original argv/cwd. Unknown external commands fail closed in this test process.
"""

import json
from pathlib import Path
import subprocess

_original_run = subprocess.run
_HELPERS = {
    "skills/physics-common/physics-foundation-object-intake/scripts/intake_physics_foundation_objects.py",
    "skills/mathformerphysicslib/mathformerphysicslib-foundation-surface-designer/scripts/design_foundation_surfaces.py",
    "skills/mathformerphysicslib/mathformerphysicslib-object-workbench/scripts/build_mathformerphysicslib_object_workbench.py",
    "skills/mathformerphysicslib/mathformerphysicslib-foundation-verifier/scripts/verify_foundation_modules.py",
    "skills/autoformalization/mathematical-final-hypothesis-reviewer/scripts/review_mathematical_final_hypotheses.py",
    "skills/physics-common/physics-final-hypothesis-reviewer/scripts/review_physics_final_hypotheses.py",
    "skills/physics-lean/physics-lean-derivation-completeness-checker/scripts/check_derivation_completeness.py",
}


def compiler_boundary(argv, *args, **kwargs):
    if argv[0] != "lake":
        # These workflows have no model/provider calls. Only their Python helper
        # subprocesses are admitted; every helper implementation remains real.
        if Path(argv[0]).name.startswith("python"):
            assert len(argv) > 1 and argv[1] in _HELPERS, argv
            root = Path(kwargs["cwd"])
            with (root / "native_process_calls.jsonl").open("a") as stream:
                stream.write(json.dumps(argv[1:]) + "\n")
            return _original_run(argv, *args, **kwargs)
        raise AssertionError(f"unexpected process in deterministic fixture: {argv}")
    assert not args
    root = Path(kwargs["cwd"])
    settings = json.loads((root / "compiler-fixture.json").read_text())
    assert "timeout" not in kwargs  # Native source specifies none.
    assert kwargs["text"] is True
    assert argv == ["lake", "build", "MathformerPhysicsLib.Lean.Foundations"] or (
        len(argv) == 4 and argv[:3] == ["lake", "env", "lean"]
    ), argv
    with (root / "compiler_calls.jsonl").open("a") as stream:
        stream.write(json.dumps({"argv": argv, "cwd": str(root)}) + "\n")
    is_foundation = argv[1] == "build"
    case = None if is_foundation else Path(argv[-1]).parent.name
    if not is_foundation:
        assert Path(argv[-1]).is_file()
        assert "import Mathlib" in Path(argv[-1]).read_text()
    mode = settings["mode"]
    if mode == "launch_error" and case == "formalphysics_0021":
        raise OSError("deterministic compiler launch failure")
    code = (
        2
        if (mode == "foundation_failure" and is_foundation)
        or (mode == "lean_failure" and case == "formalphysics_0015")
        else 0
    )
    return subprocess.CompletedProcess(
        argv, code, "fixture compiler stdout\n", "fixture compiler diagnostic\n"
    )


subprocess.run = compiler_boundary
