# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only external provider/compiler boundaries; all native Python CLIs run.

Loaded solely via the fixture subprocess PYTHONPATH. Nothing in production
imports this module. The log records original argv and timeout before execution.
"""

from tempfile import gettempdir

import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(os.environ["TEXTBOOK_FIXTURE_ROOT"])
_real_run = subprocess.run
_real_which = shutil.which
GOOD = r"""import Mathlib.Data.Nat.Basic

/--
Original source (NL): Adding zero preserves a natural number.
Original source (LaTeX): `n + 0 = n` for every natural number n.
Mathlib grounding: Nat.add_zero.
-/
theorem add_zero_identity (n : Nat) : n + 0 = n := by
  exact Nat.add_zero n
"""


def mode():
    return json.loads((ROOT / "case.json").read_text()).get("mode", "good")


def which(command, *args, **kwargs):
    if command == "codex":
        return (
            None
            if mode() == "unavailable"
            else str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/codex")
        )
    return _real_which(command, *args, **kwargs)


def run(command, **kwargs):
    command = [str(v) for v in command]
    name = Path(command[0]).name
    with (ROOT / "processes.jsonl").open("a") as stream:
        stream.write(
            json.dumps(
                dict(
                    cmd=command,
                    timeout=kwargs.get("timeout"),
                    cwd=str(kwargs.get("cwd", "")),
                )
            )
            + "\n"
        )
    if name == "codex":
        assert kwargs["timeout"] == 900
        assert "-m" not in command  # no production model is selected
        assert kwargs["input"]
        selected = mode()
        # Object 1 may block; later objects must still execute.
        if selected == "mixed":
            selected = (
                "timeout"
                if "00001" in command[command.index("--output-last-message") + 1]
                else "good"
            )
        if selected == "outer_timeout":
            import time

            time.sleep(5)
        if selected == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        if selected == "provider_crash":
            raise OSError("deterministic provider launch failure")
        code = "" if selected in {"empty", "blocked"} else GOOD
        if selected == "realness_fail":
            code = GOOD.replace("exact Nat.add_zero n", "sorry")
        response = dict(
            status="blocked" if selected == "blocked" else "draft_generated",
            lean_code=code,
            notes="deterministic provider result",
            unresolved_dependencies=[],
        )
        Path(command[command.index("--output-last-message") + 1]).write_text(
            json.dumps(response)
        )
        return subprocess.CompletedProcess(
            command,
            1 if selected == "provider_fail" else 0,
            '{"event":"provider_completed"}\n',
            "",
        )
    if name in {"lake", "lean"}:
        assert command[:3] == ["lake", "env", "lean"]
        assert kwargs["timeout"] == 240
        assert (
            Path(command[-1]).is_file() or (Path(kwargs["cwd"]) / command[-1]).is_file()
        )
        if mode() == "compiler_timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        if mode() == "compiler_crash":
            raise OSError("deterministic compiler launch failure")
        failed = mode() == "compiler_fail"
        return subprocess.CompletedProcess(
            command, int(failed), "", "fixture compiler diagnostic" if failed else ""
        )
    # Native step execution is unchanged and confined to the copied repository.
    assert name.startswith("python"), command
    assert len(command) > 1 and Path(command[1]).resolve().is_relative_to(ROOT), command
    return _real_run(command, **kwargs)


shutil.which = which
subprocess.run = run
