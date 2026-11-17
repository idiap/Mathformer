#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only package manager boundary; run executes the real installer process."""

import json
import os
from pathlib import Path
import subprocess
import sys

args = sys.argv[1:]
mode = os.environ["SYMPY_FIXTURE_MODE"]
root = Path.cwd()
ledger = root / ".venv/commands.jsonl"
ledger.parent.mkdir(exist_ok=True)
with ledger.open("a") as stream:
    stream.write(json.dumps(args) + "\n")
if args[:2] == ["run", "python"]:
    if mode == "launch_failure":
        print("uv launcher failed", file=sys.stderr)
        raise SystemExit(9)
    raise SystemExit(
        subprocess.run([sys.executable, *args[2:]], check=False).returncode
    )
if args[:1] == ["venv"]:
    assert len(args) == 2
    if mode == "venv_failure":
        raise SystemExit(7)
    if mode != "missing_python":
        path = Path(args[1]) / (
            "Scripts/python.exe" if os.name == "nt" else "bin/python"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test-only interpreter placeholder")
    print("fixture venv output")
elif args[:3] == ["pip", "install", "--python"]:
    assert Path(args[3]).is_file()
    assert args[4:] == ["sympy>=1.12,<2", "numpy>=1.26,<3"]
    print("fixture pip output")
    if mode == "pip_failure":
        raise SystemExit(8)
    if mode == "undeclared_write":
        (root / "unexpected.txt").write_text("fixture write")
else:
    raise AssertionError(args)
