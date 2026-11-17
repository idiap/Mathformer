# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated Python process/compiler transport fixture, using real tool mains.

No model/provider is used by this controlled case. Every Python tool executes
its real implementation in-process; no scientific algorithm or output is faked.
Timeout, launch failure and nonzero compiler status are injected at this sole
external-process boundary. All outputs stay in the temporary fixture directory.
"""

from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 1, 1, tzinfo=timezone.utc)


def install(native):
    # The Lunar environment supplies PRISM/MCP; the repository environment
    # supplies its pinned scientific dependencies. Both use the same CPython.
    site = (
        native.REPO_ROOT
        / ".venv/lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )
    if str(site) not in sys.path:
        sys.path.append(str(site))
    calls = []
    counts = {}

    def run(argv, *, cwd, text, capture_output, timeout):
        assert Path(cwd) == native.REPO_ROOT
        assert text and capture_output and timeout == 120
        root = Path(argv[argv.index("--output") + 1]).parent
        assert "wiki-fixture-" in str(root), "fixture must be isolated"
        index = counts.get(str(root), 0)
        counts[str(root)] = index + 1
        calls.append(list(argv))
        mode = root.name
        if "timeout" in mode and index == 2:
            raise subprocess.TimeoutExpired(argv, timeout)
        if "launch" in mode and index == 1:
            raise OSError("fixture compiler could not launch")
        if "fail" in mode and index == 3:
            return SimpleNamespace(returncode=7, stdout="x" * 4100, stderr="e" * 4200)
        path = native.REPO_ROOT / argv[1]
        spec = importlib.util.spec_from_file_location(f"wiki_step_{index}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "datetime"):
            module.datetime = Clock
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch.object(sys, "argv", argv[1:]),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            status = module.main()
        return SimpleNamespace(
            returncode=status, stdout=stdout.getvalue(), stderr=stderr.getvalue()
        )

    native.subprocess = SimpleNamespace(run=run)
    native.time = SimpleNamespace(perf_counter=lambda: 1.0)
    return calls
