# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""External compiler-only responses around the real adoption suite and tools."""

from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/control/workflow-contract-validator/scripts"))
import portable_adoption as native
from invoke_compiler_boundary import CompilerBoundary


class SuiteBoundary:
    def __enter__(self):
        self.stack = ExitStack()
        self.compiler = self.stack.enter_context(CompilerBoundary(native))
        # Import after providing the optional compiler executable boundary, so
        # skipUnless observes the same compiler fixture as actual dispatch.
        from adoption_test_contracts_tools import source_suite

        self.module = source_suite()
        import mathformer as hub

        directory = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.root = Path(directory)
        # Outer hub snapshots use actual files in a temporary repository.
        self.stack.enter_context(patch.object(hub, "REPO_ROOT", self.root))
        self.stack.enter_context(
            patch.object(
                sys.modules["adoption_test_contracts_tools"],
                "source_suite",
                lambda: self.module,
            )
        )
        self.valid = native.load_contract.__defaults__
        self.bad = self.root / "bad-contract.json"
        self.bad.write_text("{}")
        return self

    def mode(self, mode):
        self.compiler.mode = "run_fail" if mode == "compiler_failure" else "success"
        native.load_contract.__defaults__ = (
            (self.bad,) if mode == "setup_failure" else self.valid
        )

    def __exit__(self, *args):
        native.load_contract.__defaults__ = self.valid
        self.stack.close()


def serve():
    from mcp_server import mcp

    with SuiteBoundary() as boundary:

        @mcp.tool()
        def test_adoption_suite_boundary(mode: str) -> dict:
            boundary.mode(mode)
            if mode == "write":
                (boundary.root / "undeclared.txt").write_text(
                    "unexpected compiler artifact"
                )
            return {"mode": mode}

        mcp.run(transport="stdio")
