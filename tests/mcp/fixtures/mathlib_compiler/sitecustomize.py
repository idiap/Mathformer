# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only compiler process boundary, inherited by real mapper subprocesses.

Every non-compiler process is executed normally. This fixture never supplies
mapping, coverage, reports, guards, or workflow step results.
"""

import json
import os
from pathlib import Path
import subprocess

_real_run = subprocess.run


def _run(command, *args, **kwargs):
    if isinstance(command, (list, tuple)) and list(command[1:3]) == ["env", "lean"]:
        assert kwargs["timeout"] == 17, kwargs
        root = Path(kwargs["cwd"])
        mode = os.environ["MATHLIB_COMPILER_CASE"]
        ledger = root / "compiler.jsonl"
        count = len(ledger.read_text().splitlines()) + 1 if ledger.exists() else 1
        content = Path(command[-1]).read_text()
        entry = {"round": count, "content": content, "timeout": kwargs["timeout"]}
        with ledger.open("a") as stream:
            stream.write(json.dumps(entry) + "\n")
        if mode == "first_error" or mode == "later_error" and count == 2:
            raise OSError("fixture compiler launch error")
        if mode == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        if mode == "missing_compiler":
            raise FileNotFoundError("fixture compiler missing")
        success = (
            mode == "success"
            or mode == "widen"
            and count >= 2
            or mode == "later_error"
            and count >= 3
        )
        if success:
            return subprocess.CompletedProcess(command, 0, "", "")
        errors = []
        for i, line in enumerate(content.splitlines(), 1):
            if line.startswith("#check "):
                # Partial coverage improves, declines, then ties. Identity checks
                # remain unsuccessful, while commutativity succeeds in rounds 1/3.
                if mode == "partial" and count != 2 and "comm" in line:
                    continue
                errors.append(
                    f"{command[-1]}:{i}:1: error: fixture round {count} rejected {line[7:]}"
                )
        return subprocess.CompletedProcess(command, 1, "\n".join(errors), "")
    return _real_run(command, *args, **kwargs)


subprocess.run = _run
