# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only external compiler boundary; all controller and MCP code is real."""

from tempfile import gettempdir

from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parents[3] / "scripts")]
sys.path.extend(
    str(path)
    for path in (Path(__file__).resolve().parents[3] / ".venv/lib").glob(
        "python*/site-packages"
    )
)
import mathformer as hub
from mcp_server import mcp

mode, root = sys.argv[1], Path(sys.argv[2])
hub.REPO_ROOT = root
real_run = subprocess.run
real_which = hub.shutil.which


def compiler(argv, **kwargs):
    if argv != ["lake", "build"]:
        return real_run(argv, **kwargs)
    assert kwargs == dict(
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=1200,
    )
    ledger = root.parent / "launches.txt"
    with ledger.open("a") as stream:
        stream.write("lake build\n")
    if mode == "launch_error":
        raise OSError("fixture launch error")
    if mode in ("write", "timeout_write"):
        (root / "unexpected.txt").write_text("compiler output")
    if mode.startswith("timeout"):
        raise subprocess.TimeoutExpired(
            argv,
            1200,
            output=b"partial\xff",
            stderr=b"compiler timeout" if mode == "timeout" else None,
        )
    (root / ".lake").mkdir(exist_ok=True)
    (root / ".lake" / "fixture").write_text("cache")
    return subprocess.CompletedProcess(
        argv, 2 if mode == "nonzero" else 0, "compiled\n", "diagnostic\n"
    )


with (
    patch.object(hub.subprocess, "run", compiler),
    patch.object(
        hub.shutil,
        "which",
        lambda name: (
            None
            if mode == "missing_tool" and name == "lake"
            else (
                str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/lake")
                if name == "lake"
                else real_which(name)
            )
        ),
    ),
):
    mcp.run(transport="stdio")
