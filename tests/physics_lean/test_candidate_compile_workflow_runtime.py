# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Exercise native steps, registered MCP interfaces and the real PRISM runtime."""

import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
if __name__ == "__main__" and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    # Use Lunar's installed PRISM/parser/runtime and backend dependencies.
    python = LUNAR / ".venv/bin/python"
    os.execv(str(python), [str(python), str(Path(__file__).resolve())])


sys.path.insert(0, str(LUNAR / "app/backend"))
sys.path.insert(0, str(ROOT / "scripts"))
# The two applications have separate dependency environments.
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import pytest
import yaml
from mcp_connections.client import MCPConnectionError
from mcp.server.fastmcp.exceptions import ToolError
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
from mcp_connections.workflow_contract.validator import validate
import mcp_server
from physics_candidate_compile_tools import native

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])


def document():
    return yaml.safe_load(CONTRACT.read_text())


def asset(path, text):
    return {
        "path": path,
        "content": text,
        "encoding": "text",
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


class RegisteredRemote:
    """Call the actual service's FastMCP dispatcher in process, without sockets."""

    def __init__(self):
        self.history = []

    async def tools(self):
        return await mcp_server.mcp.list_tools()

    async def call(self, name, arguments):
        self.history.append((name, deepcopy(arguments)))
        try:
            content, structured = await mcp_server.mcp.call_tool(name, arguments)
        except ToolError as error:
            raise MCPConnectionError(str(error)) from error
        assert structured is not None, content
        return structured


async def invoke(request, d=None):
    d = document() if d is None else d
    assets = [asset("workflow.yaml", json.dumps(d))]
    assets += [
        asset(src["path"], (ROOT / src["path"]).read_text())
        for src in {s["path"]: s for s in d["provenance"]["sources"]}.values()
    ]
    workflow = workflow_documents(["workflow.yaml"], assets)[0]
    remote = RegisteredRemote()
    compiled = compile_workflow(
        "mcp:mathformer",
        workflow,
        [t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()],
    )
    assert compiled["runnable"] is True, compiled["diagnostics"]
    assert compiled["runtime_source"] and compiled["prism_source"]
    assert set(compiled["bindings"]) == set(d["operations"])

    async def authorize():
        pass

    result = await execute(compiled, assets, {"request": request}, remote, authorize)
    return result, remote.history


@pytest.fixture
def compiler(tmp_path, monkeypatch):
    calls = []
    modes = {}

    def compile_boundary(command, **kwargs):
        calls.append((command[:], dict(kwargs)))
        assert command[:3] == ["lake", "env", "lean"]
        assert kwargs["cwd"] == tmp_path
        assert kwargs["text"] and kwargs["capture_output"]
        if command[-1] == "--version":
            if modes.get("version") == "exception":
                raise OSError("fixture version launch failed")
            assert "timeout" not in kwargs
            return subprocess.CompletedProcess(
                command, 9, "Lean fixture\n", "version warning\n"
            )
        assert kwargs["timeout"] == 7
        mode = modes.get(Path(command[-1]).parent.name, "ok")
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                command, 7, output=b"partial\xff", stderr=None
            )
        if mode == "exception":
            raise OSError("fixture compiler launch failed")
        return subprocess.CompletedProcess(
            command,
            1 if mode == "fail" else 0,
            "output\n",
            "error\n" if mode == "fail" else "",
        )

    monkeypatch.setattr(native.subprocess, "run", compile_boundary)

    def cases(count):
        for i in reversed(range(count)):
            p = (
                tmp_path
                / f"libraries/MathformerPhysicsLib/Lean/formalphysics_{i:04}/MathformerPhysics.lean"
            )
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"-- compiler fixture {i}\n")
        return {
            "repository_root": str(tmp_path),
            "output": str(tmp_path / "out/report.json"),
            "case_count": count,
            "timeout_seconds": 7,
        }

    return cases, modes, calls


def assert_report(result, request):
    assert result["status"] == "accepted", result
    report = result["outputs"]["report"]
    assert json.loads(Path(request["output"]).read_text()) == report
    assert report["artifact_status"] == "candidate" and report["release_ok"] is False
    assert report["lean_version"]["returncode"] == 9
    assert result["runtime"]["effect_records"] and result["replay_artifacts"]
    return report


@pytest.mark.parametrize(
    "modes", [{}, {"formalphysics_0000": "fail", "formalphysics_0001": "timeout"}]
)
def test_native_equivalence_and_continuation(compiler, modes):
    cases, outcomes, calls = compiler
    request = cases(3)
    outcomes.update(modes)
    (Path(request["repository_root"]) / "lake-manifest.json").write_text(
        '{"fixture":true}'
    )
    result, history = asyncio.run(invoke(request))
    report = assert_report(result, request)
    assert report["case_count"] == 3
    assert report["compiled_count"] == (1 if modes else 3)
    assert report["checks_passed"] == (not modes)
    assert report["library_status"] == ("blocked" if modes else "accepted")
    assert report["blockers"] == (["candidate_compile_failure"] if modes else [])
    assert report["terminal_states"] == (["compile_failed"] if modes else [])
    assert len(calls) == 4 and calls[-1][0][-1] == "--version"
    assert [x["case_id"] for x in report["results"]] == [
        f"formalphysics_{i:04}" for i in range(3)
    ]
    for entry in report["results"]:
        assert (
            entry["source_sha256"]
            == hashlib.sha256(
                (Path(request["repository_root"]) / entry["path"]).read_bytes()
            ).hexdigest()
        )
        assert (
            entry["diagnostic_sha256"]
            == hashlib.sha256(
                (entry["stdout"] + "\n" + entry["stderr"]).encode()
            ).hexdigest()
        )
    if modes:
        assert report["results"][1]["timeout"] is True
        assert report["results"][1]["returncode"] is None
        assert report["results"][1]["stdout"] == "partial\ufffd"
    advances = [args for name, args in history if name.endswith("_advance")]
    assert [a["state"]["index"] for a in advances] == [0, 1, 2]
    assert [len(a["state"]["results"]) for a in advances] == [0, 1, 2]
    # Independently load the frozen original implementation for report/command comparison.
    original = ROOT / "tests/physics_lean/fixtures/all_candidate_compile_original.py"
    spec = importlib.util.spec_from_file_location("_candidate_original", original)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.REPO_ROOT = Path(request["repository_root"])
    module.LEAN_ROOT = module.REPO_ROOT / "libraries/MathformerPhysicsLib/Lean"
    before_calls = deepcopy(calls)
    calls.clear()
    expected = module.run(Path(request["output"]), timeout_seconds=7)
    assert calls == before_calls
    assert {k: v for k, v in expected.items() if k != "generated_at_utc"} == {
        k: v for k, v in report.items() if k != "generated_at_utc"
    }
    current = native.run(
        Path(request["output"]), timeout_seconds=7, repository_root=module.REPO_ROOT
    )
    assert {k: v for k, v in current.items() if k != "generated_at_utc"} == {
        k: v for k, v in report.items() if k != "generated_at_utc"
    }


def test_empty_branch(compiler):
    cases, _, calls = compiler
    request = cases(0)
    result, history = asyncio.run(invoke(request))
    report = assert_report(result, request)
    assert not report["checks_passed"] and report["case_count"] == 0
    assert report["lake_manifest_sha256"] is None
    assert [name.rsplit("_", 1)[-1] for name, _ in history] == [
        "discover",
        "empty",
        "finish",
    ]
    assert len(calls) == 1


@pytest.mark.parametrize("count", [1, 257])
def test_admission_failure_never_compiles(compiler, count):
    cases, _, calls = compiler
    request = cases(count)
    if count == 1:
        request["case_count"] = 0
    else:
        request["case_count"] = 256
    result, history = asyncio.run(invoke(request))
    assert result["status"] == "failed" and result["outputs"] is None
    assert len(history) == 1 and not calls
    assert not Path(request["output"]).exists()


def test_unexpected_exception_stops_remaining_candidates(compiler):
    cases, modes, calls = compiler
    request = cases(3)
    modes["formalphysics_0001"] = "exception"
    result, history = asyncio.run(invoke(request))
    assert result["status"] == "failed" and result["outputs"] is None
    assert len(calls) == 2
    assert [name.rsplit("_", 1)[-1] for name, _ in history] == [
        "discover",
        "compile",
        "advance",
        "compile",
    ]
    assert not Path(request["output"]).exists()


def test_exact_bound_and_runtime_exhaustion(compiler):
    cases, _, calls = compiler
    request = cases(256)
    result, history = asyncio.run(invoke(request))
    report = assert_report(result, request)
    assert report["case_count"] == report["compiled_count"] == 256
    assert len(history) == 514 and len(calls) == 257
    # Exhaustion is unreachable under admission. A deliberately smaller test-only
    # descriptor proves the real PRISM runtime fails, rather than writing a report.
    calls.clear()
    Path(request["output"]).unlink()
    reduced = document()
    reduced["flow"]["steps"][1]["max_iterations"] = 2
    result, history = asyncio.run(invoke(request, reduced))
    assert result["status"] == "failed" and result["failure_disposition"] == "fail"
    assert result["outputs"] is None and len(calls) == 2
    assert not Path(request["output"]).exists()


def test_report_write_failure_and_service_policy(compiler, monkeypatch):
    cases, _, calls = compiler
    request = cases(1)
    blocked = Path(request["repository_root"]) / "file"
    blocked.write_text("not a directory")
    request["output"] = str(blocked / "report.json")
    result, history = asyncio.run(invoke(request))
    assert result["status"] == "failed" and len(calls) == 2
    assert history[-1][0].endswith("_finish")
    calls.clear()
    monkeypatch.setattr(mcp_server, "_READONLY", True)
    result, history = asyncio.run(invoke(request))
    assert result["status"] == "failed" and not calls
    assert history[-1][0].endswith("_compile")


@pytest.mark.parametrize("count", [0, 1])
def test_cli_exit_and_json_output(compiler, monkeypatch, capsys, count):
    cases, _, calls = compiler
    request = cases(count)
    monkeypatch.setattr(native, "REPO_ROOT", Path(request["repository_root"]))
    monkeypatch.setattr(
        native,
        "LEAN_ROOT",
        Path(request["repository_root"]) / "libraries/MathformerPhysicsLib/Lean",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "candidate-compile",
            "--output",
            request["output"],
            "--timeout-seconds",
            "7",
            "--json",
        ],
    )
    assert native.main() == (0 if count else 1)
    report = json.loads(capsys.readouterr().out)
    assert report == json.loads(Path(request["output"]).read_text())
    assert report["checks_passed"] == bool(count)
    assert len(calls) == count + 1


def test_version_exception_prevents_report(compiler):
    cases, modes, calls = compiler
    request = cases(2)
    modes["version"] = "exception"
    result, history = asyncio.run(invoke(request))
    assert result["status"] == "failed" and result["outputs"] is None
    assert len(calls) == 3 and calls[-1][0][-1] == "--version"
    assert history[-1][0].endswith("_finish")
    assert not Path(request["output"]).exists()


def test_identity_provenance_and_advertised_interfaces():
    d = document()
    # The host may supply the candidate outside the repository. Validate its
    # contents with the same repository-relative source resolution as installation.
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", dir=ROOT) as candidate:
        candidate.write(json.dumps(d))
        candidate.flush()
        validation = validate(
            candidate.name, repository_root=ROOT, require_declared_bindings=True
        )
    assert not validation["errors"], validation
    assert d["id"] == "hub_physics_lib_all_candidate_compile_workflow"
    assert d["aliases"] == ["physics-lib:all-candidate-compile"]
    assert d["version"] == "1.0.0" and d["lifecycle"] == "active"
    assert d["policy"]["limits"] == {
        "wall_time_seconds": 3600,
        "max_operation_calls": 514,
    }
    assert d["policy"]["failure"]["retry"]["max_attempts"] == 1
    for source in d["provenance"]["sources"]:
        assert (
            source["digest"]
            == "sha256:"
            + hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest()
        )
    tools = [
        t.model_dump(by_alias=True, exclude_none=True)
        for t in asyncio.run(RegisteredRemote().tools())
    ]
    advertised = {t["name"]: t for t in tools}
    for operation in d["operations"].values():
        binding = operation["execution"]["binding"]
        assert binding["operation"] == binding["target"]
        tool = advertised[binding["target"]]
        assert set(tool["inputSchema"]["properties"]) == set(operation["inputs"])
        assert set(tool["outputSchema"]["properties"]) == set(operation["outputs"])
    absent = deepcopy(d)
    absent["operations"]["compile_next"]["execution"]["binding"][
        "target"
    ] = "absent_compiler"
    absent["operations"]["compile_next"]["execution"]["binding"][
        "operation"
    ] = "absent_compiler"
    assets = [asset("workflow.yaml", json.dumps(absent))]
    assets += [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in absent["provenance"]["sources"]
    ]
    compiled = compile_workflow(
        "mcp:mathformer", workflow_documents(["workflow.yaml"], assets)[0], tools
    )
    assert compiled["runnable"] is False


def test_budget_failure_propagates_before_report(compiler):
    cases, _, calls = compiler
    request = cases(3)
    reduced = document()
    reduced["policy"]["limits"]["max_operation_calls"] = 2
    result, history = asyncio.run(invoke(request, reduced))
    assert result["status"] == "failed" and result["outputs"] is None
    assert len(history) == 2 and len(calls) == 1
    assert "budget" in json.dumps(result).lower()
    assert not Path(request["output"]).exists()


@pytest.mark.parametrize("count", [0, 1])
def test_service_mount_restrictions(compiler, monkeypatch, count):
    cases, _, calls = compiler
    request = cases(count)
    monkeypatch.setattr(
        mcp_server,
        "_ALLOWED_WRITE_ROOTS",
        [Path(request["repository_root"]) / "elsewhere"],
    )
    result, history = asyncio.run(invoke(request))
    assert result["status"] == "failed" and result["outputs"] is None
    assert not calls and not Path(request["output"]).exists()
    assert history[-1][0].endswith("_compile" if count else "_finish")


def test_relative_output_uses_execution_context(compiler):
    cases, _, calls = compiler
    request = cases(1)
    request["output"] = "out/relative.json"
    result, _ = asyncio.run(invoke(request))
    assert result["status"] == "accepted", result
    assert (
        json.loads((Path(request["repository_root"]) / request["output"]).read_text())
        == result["outputs"]["report"]
    )
    assert len(calls) == 2


def test_native_entrypoint_retains_uncapped_discovery(compiler):
    cases, _, calls = compiler
    request = cases(257)
    report = native.run(
        Path(request["output"]),
        timeout_seconds=7,
        repository_root=Path(request["repository_root"]),
    )
    assert report["checks_passed"] and report["case_count"] == 257
    assert len(calls) == 258


if __name__ == "__main__":

    class RequiredPasses:
        passed = 0

        def pytest_runtest_logreport(self, report):
            if report.when == "call" and report.passed:
                self.passed += 1

    results = RequiredPasses()
    code = pytest.main(["-q", str(Path(__file__).resolve())], plugins=[results])
    raise SystemExit(int(code) if code else (0 if results.passed else 1))
