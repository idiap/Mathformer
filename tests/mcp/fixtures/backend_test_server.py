# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only child-process bridge: execute the real runner with compiler fixtures."""

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from backend_test_tools import source, register_backend_test_tools
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("backend-test-fixture")


def write_policy(path):
    assert path == ROOT / "artifacts"


register_backend_test_tools(mcp, write_policy)

spec = importlib.util.spec_from_file_location(
    "backend_comprehensive_fixture",
    ROOT / "tests/test_program/run_comprehensive_tests.py",
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
temporary = tempfile.TemporaryDirectory(prefix="backend-contract-")
fixture = Path(temporary.name)
runner.REPO_ROOT = fixture
runner.ARTIFACT_ROOT = fixture / "artifacts/test_program"
runner.MATRIX_FILE = fixture / "matrix.json"
# No credential reads: the dependency snapshot sees an explicitly empty fixture
# environment. The production implementation and its output generation run intact.
runner.os = SimpleNamespace(environ={})
runner.shutil = SimpleNamespace(which=lambda name: None)
checks = []
for family, outcome in [
    ("lean", "fail"),
    ("isabelle", "timeout"),
    ("sympy", "pass"),
    ("physics_sympy", "pass"),
]:
    checks.append(
        dict(
            id=family,
            module_family=family,
            command=["fixture-compiler", outcome],
            expected_exit=0,
            owner_skill="fixture",
            hook_id="test.backend",
            fixture_ids=["deterministic"],
            write_set=["artifacts/"],
            timeout_seconds=7,
        )
    )
checks[-1].pop("timeout_seconds")
checks.append(
    dict(
        id="optional",
        module_family="sympy",
        command=["fixture-compiler", "never"],
        optional_dependency="lean",
        owner_skill="fixture",
        hook_id="test.backend",
    )
)
checks.append(
    dict(id="unselected", module_family="docs", command=["fixture-compiler", "never"])
)
runner.MATRIX_FILE.write_text(json.dumps({"schema_version": 2, "tests": checks}))
ledger = []
reports = []
attempts = []
mode = sys.argv[1] if len(sys.argv) > 1 else "normal"


def compiler(command, **kwargs):
    if command[0] != "fixture-compiler":
        # Dependency probe process boundary, no imports or compiler launches.
        return subprocess.CompletedProcess(
            command, 1, "", "fixture dependency unavailable"
        )
    ledger.append({"command": command, "timeout": kwargs["timeout"]})
    if mode == "error":
        raise OSError("fixture compiler process unavailable")
    assert kwargs["cwd"] == fixture
    if command[1] == "timeout":
        raise subprocess.TimeoutExpired(
            command, kwargs["timeout"], output="partial compiler output"
        )
    assert command[1] != "never"
    return subprocess.CompletedProcess(
        command, 2 if command[1] == "fail" else 0, "deterministic compiler output", ""
    )


runner.subprocess = SimpleNamespace(
    run=compiler, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
)


def child(command, cwd):
    attempts.append(command)
    assert cwd == ROOT
    assert command[:2] == [
        sys.executable,
        "tests/test_program/run_comprehensive_tests.py",
    ]
    stream = io.StringIO()
    start = len(ledger)
    # In-process bridge substitutes the OS process boundary, not the runner.
    with redirect_stdout(stream):
        code = runner.main(command[2:])
    report = json.loads((runner.ARTIFACT_ROOT / "deterministic_tests.json").read_text())
    reports.append(
        {
            "command": command,
            "exit_code": code,
            "report": report,
            "stdout": stream.getvalue(),
            "compiler_calls": ledger[start:],
            "jsonl": (runner.ARTIFACT_ROOT / "deterministic_tests.jsonl").read_text(),
            "junit": (runner.ARTIFACT_ROOT / "deterministic_tests.xml").read_text(),
            "dependency": json.loads(
                (runner.ARTIFACT_ROOT / "dependency_map.json").read_text()
            ),
        }
    )
    return code


source().subprocess = SimpleNamespace(call=child)


@mcp.tool()
def backend_test_fixture_evidence() -> dict:
    return {"launches": reports, "attempts": attempts, "compiler_calls": ledger}


try:
    mcp.run(transport="stdio")
finally:
    temporary.cleanup()
