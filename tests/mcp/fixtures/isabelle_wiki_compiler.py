# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only compiler boundary. Native grounding/drafting/checker remain real."""

from tempfile import gettempdir

import importlib.util
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
CHECKER = (
    ROOT / "skills/isabelle/isabelle-execution-runner/scripts/check_isabelle_theory.py"
)


def compiler_main(mode, argv):
    spec = importlib.util.spec_from_file_location("fixture_checker", CHECKER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    theory = Path(argv[argv.index("--theory-file") + 1])
    if mode == "placeholder":
        theory.write_text(theory.read_text() + "\nsorry\n")

    def build(cmd, **kwargs):
        assert cmd == [
            str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/isabelle"),
            "build",
            "-D",
            argv[argv.index("--session-dir") + 1],
        ]
        assert kwargs["timeout"] == int(argv[argv.index("--timeout-sec") + 1])
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                cmd, kwargs["timeout"], output=b"partial build"
            )
        return subprocess.CompletedProcess(
            cmd, 1 if mode == "failed" else 0, "fixture compiler output", ""
        )

    with (
        patch.object(
            checker,
            "find_isabelle",
            return_value=(
                None
                if mode == "missing"
                else Path(
                    str(
                        Path(gettempdir()) / "mathformer-test-fixtures/fixture/isabelle"
                    )
                )
            ),
        ),
        patch.object(checker.subprocess, "run", side_effect=build),
    ):
        code = checker.main(argv)
    return 9 if mode == "exit-disagrees" else code


def install(mode):
    """Route only the compiler-owning Python CLI through the test bootstrap."""
    original = subprocess.run

    def dispatch(cmd, **kwargs):
        if len(cmd) > 1 and cmd[1].endswith("check_isabelle_theory.py"):
            cmd = [cmd[0], str(Path(__file__).resolve()), "--checker", mode, *cmd[2:]]
        return original(cmd, **kwargs)

    subprocess.run = dispatch


if __name__ == "__main__":
    if sys.argv[1] == "--checker":
        raise SystemExit(compiler_main(sys.argv[2], sys.argv[3:]))
    install(sys.argv[1])
    sys.path.insert(0, str(ROOT / "scripts"))
    from mcp_server import mcp

    mcp.run(transport="stdio")
