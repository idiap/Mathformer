# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated native textbook inputs; no replacement of the runner or its checks."""

import json
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

STARTUP = Path(__file__).parent / "textbook_route_startup"


def populate(root, project, case="success"):
    root, project = Path(root), Path(project)
    files = [
        "tests/test_program/run_comprehensive_tests.py",
        "scripts/workflow_write_audit.py",
    ]
    folders = [
        "skills/latex-textbook",
        "skills/autoformalization/source-line-translation-packet-builder",
        "skills/control/reasoning-log-schema-guardian",
    ]
    for folder in folders:
        files.extend(
            p.relative_to(project).as_posix() for p in (project / folder).rglob("*.py")
        )
    for relative in files:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(project / relative, target)
    matrix = json.loads((project / "tests/test_matrix.json").read_text())
    rows = [r for r in matrix["tests"] if r["module_family"] == "textbook"]
    assert len(rows) == 4
    assert [r["timeout_seconds"] for r in rows] == [120, 120, 120, 180]
    assert all(r["optional_dependency"] is None for r in rows)
    # Source commands/arguments stay unchanged. Failure comes from the oracle
    # input, empty selection from the family input; neither replaces a step.
    if case == "failure":
        rows[0]["expected_exit"] = 7
    matrix["tests"] = [
        *rows,
        {
            **rows[0],
            "id": "fixture.unselected",
            "module_family": "atp",
            "command": ["forbidden-unselected-process"],
        },
    ]
    if case == "empty":
        matrix["tests"] = matrix["tests"][-1:]
    (root / "tests/test_matrix.json").write_text(json.dumps(matrix))
    if case == "invalid":
        (root / "tests/test_matrix.json").write_text("[]")
    return rows


def environment(root):
    # No inherited credentials or executable search path. Dependency discovery
    # sees no installed command-line provider/compiler. Python imports are real.
    return {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PATH": "",
        "PYTHONPATH": str(STARTUP),
        "TEXTBOOK_ROUTE_ROOT": str(root),
    }


def serve(root):
    os.environ.clear()
    os.environ.update(environment(root))
    import mcp_server

    mcp_server._ALLOWED_WRITE_ROOTS = [Path(root).resolve()]
    mcp_server.CALL_LOG_PATH = Path(root).parent / "service-calls.jsonl"
    mcp_server.mcp.run(transport="stdio")


def external_process(native, root, mode):
    """Only provider/compiler calls are substituted, never a Python step."""
    calls = []

    def run(command, **kwargs):
        calls.append({"command": list(command), "timeout": kwargs["timeout"]})
        if command[0] == "codex":
            assert "-m" not in command  # no production model selected
            assert kwargs["input"] and kwargs["cwd"] == root
            schema = Path(command[command.index("--output-schema") + 1])
            assert json.loads(schema.read_text())["type"] == "object"
            if mode == "timeout":
                raise subprocess.TimeoutExpired(command, kwargs["timeout"])
            if mode == "crash":
                raise OSError("fixture provider launch failure")
            response = {
                "status": "draft_generated",
                "lean_code": "theorem fixture : True := by trivial",
                "notes": "deterministic provider boundary",
                "unresolved_dependencies": [],
            }
            Path(command[command.index("--output-last-message") + 1]).write_text(
                json.dumps(response)
            )
            return subprocess.CompletedProcess(
                command, 7 if mode == "reject" else 0, '{"event":"generated"}\n', ""
            )
        assert command == ["fixture-compiler"], command
        assert kwargs["cwd"] == root
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                command, kwargs["timeout"], output="partial", stderr="deadline"
            )
        if mode == "crash":
            raise OSError("fixture compiler launch failure")
        if mode == "write":
            (root / "undeclared.txt").write_text("compiler output")
        return subprocess.CompletedProcess(
            command,
            7 if mode == "reject" else 0,
            "typed fixture IR",
            "fixture diagnostic",
        )

    native.subprocess = SimpleNamespace(
        run=run, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
    )
    return calls
