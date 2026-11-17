# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only compiler process boundary; all validation and MCP code is real."""

from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
from backends.rocq.MathformerRocq import autoformalize as backend


def install(mode):
    # Discovery still executes the real explicit/PATH preference logic. Existing
    # files serve as executable identities; no external process is launched.
    def which(name):
        if mode == "rocq" and name == "rocq":
            return str(ROOT / "backends/rocq")
        if mode != "missing" and name == "coqc":
            return sys.executable
        return None

    backend.shutil = SimpleNamespace(which=which)

    def run(cmd, **kwargs):
        assert cmd[1:-1] == (["compile"] if mode == "rocq" else [])
        assert kwargs["timeout"] == 120
        assert kwargs["cwd"] == backend.REPO_ROOT
        assert kwargs["capture_output"] and kwargs["text"]
        file = Path(cmd[-1])
        text = file.read_text()
        if "RAISE" in text:
            raise OSError("fixture compiler transport error")
        if "TIMEOUT" in text:
            raise subprocess.TimeoutExpired(
                cmd, kwargs["timeout"], output="partial", stderr="fixture timeout"
            )
        if "WRITE" in text:
            file.with_suffix(".vo").write_text("compiler output")
        return SimpleNamespace(
            returncode=1 if "REJECT" in text else 0,
            stdout="compiled " + file.name,
            stderr="rejected" if "REJECT" in text else "",
        )

    backend.subprocess = SimpleNamespace(
        run=run, TimeoutExpired=subprocess.TimeoutExpired
    )


if __name__ == "__main__":
    install(sys.argv[1])
    from mcp_server import mcp

    mcp.run(transport="stdio")
