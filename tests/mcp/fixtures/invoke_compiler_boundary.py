# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only deterministic external compiler responses; no subprocess launches."""

import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import patch


class CompilerBoundary:
    def __init__(self, native):
        self.native = native
        self.mode = "success"
        self.calls = []

    def run(self, command, **kwargs):
        command = list(map(str, command))
        self.calls.append({"argv": command, "cwd": str(kwargs["cwd"])})
        if "verify-run" in command:
            assert command[-2:] == ["--mode", "offline"]
            code = 9 if self.mode == "verify_fail" else 0
        elif "run" in command and "--handler" in command:
            assert command[3:5] == ["--handler", "fake"]
            assert kwargs["env"]["PRISM_BIN"].endswith("to_prism/.venv/bin/prism")
            Path(command[-1]).write_text(
                json.dumps({"compiled": True, "entrypoint": command[2]})
            )
            code = 7 if self.mode == "run_fail" else 0
        else:
            assert any(
                arg.endswith("validate_skill_hooks.py") for arg in command
            ), command
            code = 4 if self.mode == "run_fail" else 0
        return subprocess.CompletedProcess(
            command, code, '{"compiler_fixture":true}\n', "fixture diagnostic\n"
        )

    def __enter__(self):
        from contextlib import ExitStack

        self.stack = ExitStack()
        original = Path.is_file
        executable = self.native.ROOT.parent / "to_prism/.venv/bin/prism"
        self.stack.enter_context(
            patch.object(
                Path,
                "is_file",
                lambda path: (
                    (self.mode != "missing") if path == executable else original(path)
                ),
            )
        )
        proxy = SimpleNamespace(
            **{
                name: getattr(subprocess, name)
                for name in dir(subprocess)
                if not name.startswith("__")
            }
        )
        proxy.run = self.run
        self.stack.enter_context(patch.object(self.native, "subprocess", proxy))
        hub = self.native.module_at(self.native.ROOT / "scripts/mathformer.py")
        self.stack.enter_context(patch.object(hub, "subprocess", proxy))
        # Supply an isolated repository fixture to the native write auditor.
        # The registry, preflight, snapshots, and audit algorithm remain real.
        directory = self.stack.enter_context(tempfile.TemporaryDirectory())
        root = Path(directory)
        for relative in hub.build_registry()[
            "control:workflow-contract"
        ].required_paths:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("compiler input fixture\n")
        self.stack.enter_context(patch.object(hub, "REPO_ROOT", root))
        return self

    def __exit__(self, *args):
        self.stack.close()


def serve():
    from catalog_check_tools import source
    from mcp_server import mcp

    with CompilerBoundary(source()) as boundary:

        @mcp.tool()
        def test_compiler_boundary(mode: str) -> dict:
            previous = list(boundary.calls)
            boundary.calls.clear()
            boundary.mode = mode
            return {"calls": previous}

        mcp.run(transport="stdio")
