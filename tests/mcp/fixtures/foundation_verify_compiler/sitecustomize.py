# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only compiler boundary; no production process or provider is invoked."""

import json
from pathlib import Path
import subprocess

native_run = subprocess.run


def compiler_boundary(args, *positional, **kwargs):
    if isinstance(args, (list, tuple)) and args and args[0] == "lake":
        root = Path(kwargs["cwd"])
        assert list(args) == ["lake", "build", "MathformerPhysicsLib.Lean.Foundations"]
        assert not positional
        assert kwargs == dict(
            cwd=kwargs["cwd"], text=True, capture_output=True, check=False
        )
        # A test-specific sentinel prevents accidentally touching a real checkout.
        assert (root / "fixture_repository").read_text() == "foundation-verifier-test"
        with (root / "compiler_calls.jsonl").open("a") as stream:
            stream.write(json.dumps({"argv": list(args), "cwd": str(root)}) + "\n")
        mode = (
            (root / "compiler_mode").read_text()
            if (root / "compiler_mode").exists()
            else "success"
        )
        if mode == "launch_error":
            raise FileNotFoundError("deterministic Lake launch failure")
        return subprocess.CompletedProcess(
            args,
            7 if mode == "failure" else 0,
            "fixture stdout " + "o" * 2100,
            "fixture stderr " + "e" * 2100,
        )
    return native_run(args, *positional, **kwargs)


subprocess.run = compiler_boundary
