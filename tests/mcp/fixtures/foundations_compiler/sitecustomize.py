# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only Lake boundary. Real native Python subprocesses remain unchanged."""

import json
import os
from pathlib import Path
import subprocess
import sys

_native_run = subprocess.run


def compiler_boundary(args, *positional, **kwargs):
    if isinstance(args, (list, tuple)) and args and args[0] == "lake":
        root = Path(os.environ["FOUNDATIONS_FIXTURE_ROOT"])
        assert list(args) == [
            "lake",
            "build",
            "MathformerPhysicsLib.Lean.Foundations",
        ], args
        assert Path(kwargs["cwd"]).resolve() == root.resolve()
        assert not positional and kwargs == dict(
            cwd=kwargs["cwd"], text=True, capture_output=True, check=False
        )
        with (root / "compiler_calls.jsonl").open("a") as stream:
            stream.write(json.dumps({"argv": list(args), "cwd": str(root)}) + "\n")
        code_file = root / "compiler_code"
        mode = code_file.read_text() if code_file.exists() else "0"
        if mode == "launch_error":
            raise FileNotFoundError("fixture: lake executable unavailable")
        code = int(mode)
        return subprocess.CompletedProcess(
            args, code, "compiler fixture " + "o" * 2100, "e" * 2100 if code else ""
        )
    # The source stages are real Python subprocesses. Fail closed if a future
    # stage tries to launch another external tool under this offline fixture.
    assert isinstance(args, (list, tuple)) and args and args[0] == sys.executable, args
    return _native_run(args, *positional, **kwargs)


subprocess.run = compiler_boundary
