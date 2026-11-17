# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic substitute at the external Codex executable boundary only."""

from tempfile import gettempdir

import json
from pathlib import Path
import subprocess
from threading import Lock

LOCK = Lock()


def run(command, *, cwd, input, text, capture_output, timeout):
    assert command[0] == "fixture-codex", command
    assert command[1] == "exec" and command[-1] == "-"
    assert text is True and capture_output is True
    assert timeout == 17
    final = Path(command[command.index("--output-last-message") + 1])
    record = dict(command=command, cwd=str(cwd), input=input, timeout=timeout)
    with LOCK:
        with (final.parent.parent / "provider_calls.jsonl").open("a") as stream:
            stream.write(json.dumps(record) + "\n")
    if input == "timeout":
        raise subprocess.TimeoutExpired(command, timeout)
    if input != "missing":
        final.write_text(
            {
                "invalid": "not JSON",
                "embedded": 'prefix {"score": 7} suffix',
                "failed": '{"score": 0}',
            }.get(input, '{"score": 7}')
        )
    return subprocess.CompletedProcess(
        command,
        9 if input == "failed" else 0,
        stdout="provider stdout",
        stderr="E" * 4100,
    )


def install(native):
    original_which = native.shutil.which
    native.shutil.which = lambda name: (
        str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/codex")
        if name == "fixture-codex"
        else None if name == "unavailable-codex" else original_which(name)
    )
    native.subprocess.run = run
