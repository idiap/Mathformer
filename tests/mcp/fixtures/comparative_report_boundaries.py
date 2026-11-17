# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Only external boundaries: deterministic lake results, and denied providers."""

from pathlib import Path
import socket
import subprocess


def compiler(command, *args, **kwargs):
    if not (
        isinstance(command, list)
        and command[:3] == ["lake", "env", "lean"]
        and len(command) == 4
    ):
        raise AssertionError("Unapproved external process: " + repr(command))
    assert not args
    assert kwargs == dict(cwd=kwargs["cwd"], text=True, capture_output=True, timeout=7)
    assert Path(kwargs["cwd"]).is_dir()
    text = Path(command[3]).read_text()
    if "fixture-timeout" in text:
        raise subprocess.TimeoutExpired(
            command, 7, output="fixture partial stdout", stderr="fixture timeout"
        )
    if "fixture-error" in text:
        return subprocess.CompletedProcess(
            command, 1, stdout="error: deterministic compiler failure", stderr=""
        )
    if "fixture-crash" in text:
        raise OSError("fixture compiler unavailable")
    return subprocess.CompletedProcess(
        command, 0, stdout="warning: fixture compiler evidence", stderr=""
    )


def no_provider(*args, **kwargs):
    raise AssertionError("Live provider/network forbidden in this test")


def install():
    subprocess.run = compiler
    socket.create_connection = no_provider
    socket.socket.connect = no_provider
