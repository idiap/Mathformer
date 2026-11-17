# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic compiler/process boundary; all wrapper and matrix logic is native."""

from contextlib import redirect_stdout, redirect_stderr
import importlib.util
from io import StringIO
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]


def install(wrapper, root, mode):
    spec = importlib.util.spec_from_file_location(
        "_e2e_matrix_fixture", ROOT / "tests/test_program/run_comprehensive_tests.py"
    )
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    wrapper.REPO_ROOT = runner.REPO_ROOT = root
    wrapper.OUT = root / "artifacts/test_program/e2e_all_backends.json"
    runner.ARTIFACT_ROOT = wrapper.OUT.parent
    runner.MATRIX_FILE = root / "tests/test_matrix.json"
    runner.MATRIX_FILE.parent.mkdir(parents=True, exist_ok=True)
    cases = (
        ["pass"]
        if mode in ("success", "launch_error")
        else ["fail", "timeout", "skip", "expected", "audit", "pass"]
    )
    if mode == "empty":
        cases = []
    rows = []
    for index, case in enumerate(cases):
        row = {
            "id": case,
            "command": ["fixture-compiler", case],
            "module_family": "lean",
            "owner_skill": "fixture",
            "hook_id": "test.lean",
            "fixture_ids": ["compiler"],
            "write_set": [],
            "timeout_seconds": 7 if case == "timeout" else 120,
        }
        if case == "skip":
            row["optional_dependency"] = "lean"
        if case == "expected":
            row["expected_exit"] = 9
        rows.append(row)
    rows.append(
        {"id": "excluded", "command": ["must-never-run"], "module_family": "atp"}
    )
    runner.MATRIX_FILE.write_text(json.dumps({"schema_version": 2, "tests": rows}))
    calls = []
    # External dependency/provider environment probes are deterministic and never
    # inspect credentials or execute a real tool. Native snapshot formatting runs.
    runner.shutil = SimpleNamespace(which=lambda name: None)
    runner.os = SimpleNamespace(environ={})
    clock = SimpleNamespace(time=lambda: 100.125)
    runner.time = wrapper.time = clock

    def compiler(command, **kwargs):
        if command[0] != "fixture-compiler":
            # Python module probes in dependency_snapshot; unavailable everywhere.
            assert "-c" in command, command
            return subprocess.CompletedProcess(command, 1, "", "fixture unavailable")
        calls.append({"command": command, "timeout": kwargs["timeout"]})
        case = command[1]
        if case == "timeout":
            raise subprocess.TimeoutExpired(
                command, kwargs["timeout"], output=b"partial"
            )
        if case == "audit":
            (root / "unexpected.txt").write_text("compiler side effect")
        return subprocess.CompletedProcess(
            command,
            9 if case in ("fail", "expected") else 0,
            "compiled " + case,
            "diagnostic " + case,
        )

    def delegate(command, **kwargs):
        assert "timeout" not in kwargs
        assert kwargs == {
            "cwd": root,
            "text": True,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
        }
        if mode == "launch_error":
            raise OSError("fixture launch failed")
        assert command[1] == "tests/test_program/run_comprehensive_tests.py"
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = runner.main(command[2:])
        (root / "boundary_calls.json").write_text(json.dumps(calls))
        return subprocess.CompletedProcess(
            command, code, stdout.getvalue(), stderr.getvalue()
        )

    runner.subprocess = SimpleNamespace(
        run=compiler, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
    )
    wrapper.subprocess = SimpleNamespace(run=delegate, PIPE=subprocess.PIPE)
    return runner, calls
