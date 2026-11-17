# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only external compiler boundary, used with real aggregate registration."""

from tempfile import gettempdir

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))


def compiler_fixture(mode, ledger):
    def which(name):
        assert name == "tectonic", name
        return (
            None
            if mode == "missing"
            else str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/tectonic")
        )

    def run(argv, **kwargs):
        assert kwargs == {"check": True}, kwargs  # no invented native timeout
        assert (
            argv[0]
            == str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/tectonic")
            and argv[2] == "--outdir"
        ), argv
        tex = Path(argv[1])
        assert argv[3] == str(tex.parent) and tex.exists(), argv
        with Path(ledger).open("a") as stream:
            stream.write(
                json.dumps({"argv": argv, "kwargs": kwargs, "cwd": str(Path.cwd())})
                + "\n"
            )
        if mode == "fail":
            raise subprocess.CalledProcessError(7, argv)
        tex.with_suffix(".pdf").write_bytes(
            b"%PDF-fixture\n" + hashlib.sha256(tex.read_bytes()).hexdigest().encode()
        )
        return subprocess.CompletedProcess(argv, 0)

    return which, run


if __name__ == "__main__":
    import mcp_server
    from mechanistic_figure_tools import source

    native = source()
    which, run = compiler_fixture(sys.argv[1], sys.argv[2])
    with (
        patch.object(native.shutil, "which", which),
        patch.object(native.subprocess, "run", run),
    ):
        mcp_server.mcp.run(transport="stdio")
