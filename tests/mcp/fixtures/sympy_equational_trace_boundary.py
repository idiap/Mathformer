# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only Python command transport; native stage implementations run in-process.

There is no model/provider in this suite. This fixture replaces the OS process
boundary, dispatching only the eleven declared local Python entrypoints. Parsing,
assumptions, API indexing/grounding, drafting, SymPy checks and reporting remain
real. Faults are deterministic process outcomes, never production mock modes.
All inputs and generated artifacts live in a temporary repository. No external
compiler, theorem prover, model, credentials or network service is used.
"""

from contextlib import chdir, redirect_stdout, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import traceback
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
STAGES = {
    "probe_sympy_dependencies.py": "dependency_probe",
    "index_sympy_api.py": "api_index",
    "parse_sympy_expressions.py": "parse",
    "model_sympy_assumptions.py": "assumptions",
    "ground_sympy_concepts.py": "grounding",
    "draft_sympy_case.py": "draft",
    "run_sympy_artifact.py": "execute",
    "validate_sympy_identity.py": "identity",
    "search_sympy_counterexamples.py": "counterexamples",
    "verify_sympy_trace.py": "trace",
    "run_sympy_consistency_report.py": "consistency",
}


def forbidden(*args, **kwargs):
    raise AssertionError("Unexpected external process or network call")


def install(native):
    """Replace subprocess transport only; keep run/run_required and all steps."""

    def dispatch(command, *, cwd, text, capture_output, timeout):
        cwd = Path(cwd)
        assert text is True and capture_output is True and timeout == 180
        assert command[0] == str(native.PYTHON)
        script = ROOT / command[1]
        assert script.name in STAGES and script.is_relative_to(ROOT / "skills/sympy")
        mode_path = cwd / "boundary.json"
        mode = json.loads(mode_path.read_text()) if mode_path.exists() else {}
        stage = STAGES[script.name]
        # Identify the source case from the command's source or packet path.
        case = next(
            (
                part
                for part in command
                if any(source.stem in part for source in native.SOURCES)
            ),
            "",
        )
        target = mode.get("stage") == stage and (
            not mode.get("case") or mode["case"] in case
        )
        with (cwd / "commands.jsonl").open("a") as ledger:
            ledger.write(
                json.dumps(
                    {
                        "cmd": command,
                        "cwd": str(cwd),
                        "timeout": timeout,
                        "stage": stage,
                    }
                )
                + "\n"
            )
        if target and mode.get("fault") == "timeout":
            raise subprocess.TimeoutExpired(
                command, timeout, output="partial compiler output"
            )
        if target and mode.get("fault") == "launch":
            raise OSError("fixture Python command launch failed")
        if target and mode.get("fault") == "nonzero":
            return subprocess.CompletedProcess(
                command, 7, "x" * 5000 + "TAIL", "e" * 5000 + "TAIL"
            )

        spec = importlib.util.spec_from_file_location("fixture_stage_" + stage, script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Self-test fallback paths must never launch another process.
        module.subprocess = SimpleNamespace(run=forbidden)
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            chdir(cwd),
            patch.object(sys, "argv", command[1:]),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            try:
                code = module.main()
            except SystemExit as error:
                code = error.code
            except Exception:
                traceback.print_exc()
                code = 1
        return subprocess.CompletedProcess(
            command, code, stdout.getvalue(), stderr.getvalue()
        )

    native.subprocess = SimpleNamespace(run=dispatch)


def serve(base):
    import socket
    from mcp.server.fastmcp import FastMCP
    from sympy_controlled_suite_tools import (
        source,
        register_sympy_controlled_suite_tools,
    )

    install(source())
    socket.create_connection = forbidden
    server = FastMCP("SymPy equational trace fixture")
    register_sympy_controlled_suite_tools(
        server,
        lambda: None,
        lambda path: path.resolve().is_relative_to(Path(base).resolve()),
    )
    server.run(transport="stdio")
