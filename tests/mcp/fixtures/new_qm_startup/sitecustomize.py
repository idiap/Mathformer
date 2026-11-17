# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only external compiler boundary; all native Python helpers run for real.

This workflow has no model/provider calls. Unknown processes fail closed. No
production module imports this fixture or offers a mock-mode switch.
"""

import json
from pathlib import Path
import subprocess

_original_run = subprocess.run
HELPERS = {
    "plan_goal_sample_autoformalization.py",
    "check_derivation_completeness.py",
    "map_repair_expansion.py",
    "control_recursive_repair_loop.py",
    "audit_mathlib_grounding.py",
    "run_grounded_sample_thoroughness.py",
}


def compiler_boundary(argv, *args, **kwargs):
    root = Path(kwargs["cwd"]).resolve()
    assert (root / "compiler-fixture.json").is_file(), "fixture context required"
    assert kwargs["timeout"] == 240
    assert kwargs["text"] is True
    if argv[0] != "lake":
        assert Path(argv[0]).name.startswith("python"), argv
        assert Path(argv[1]).name in HELPERS, argv
        helper = root / argv[1]
        assert helper.resolve().is_relative_to(root), argv
        with (root / "native_process_calls.jsonl").open("a") as stream:
            stream.write(json.dumps(argv[1:]) + "\n")
        return _original_run(argv, *args, **kwargs)
    assert not args
    assert len(argv) == 4 and argv[:3] == ["lake", "env", "lean"], argv
    lean = root / argv[-1]
    assert lean.is_file()
    assert "import Mathlib" in lean.read_text()
    with (root / "compiler_calls.jsonl").open("a") as stream:
        stream.write(json.dumps({"argv": argv, "timeout": kwargs["timeout"]}) + "\n")
    mode = json.loads((root / "compiler-fixture.json").read_text())["mode"]
    if mode == "timeout":
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
    if mode == "launch_error":
        raise OSError("deterministic compiler launch failure")
    code = (
        1
        if mode == "compile_failure" and lean.parent.name == "formalphysics_0004"
        else 0
    )
    return subprocess.CompletedProcess(
        argv, code, "deterministic compiler stdout\n", "deterministic compiler stderr\n"
    )


subprocess.run = compiler_boundary
