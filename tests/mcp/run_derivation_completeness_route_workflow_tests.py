#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated native checker, registered MCP and real Lunar/PRISM execution."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import subprocess
from types import SimpleNamespace
import pytest
import yaml
import mathformer as hub
import mcp_server
from derivation_completeness_route_tools import (
    ACTION,
    ROUTE,
    LEAF,
    COMMAND,
    selected_match,
    checked_registry,
    check_state,
)
from mcp.server.fastmcp.exceptions import ToolError
from mcp_connections.client import MCPConnectionError
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
from mcp_connections.workflow_contract.validator import validate

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
BASE = "skills/control/workflow-contract-validator/references/normalized-workflows/"
DESCRIPTOR = (
    BASE
    + "route/route_validate_physics_lean_derivation_completeness_workflow/workflow.yaml"
)
SCHEMA = BASE + "hub-interface.schema.json"
GOOD = "theorem target (x y : Nat) (h : x = y) : y = x := by\n  exact h.symm\n"
BAD = """structure PhysicalLawWitness (P : Prop) : Type where holds : P
theorem physicalLawHolds {P : Prop} (law : PhysicalLawWitness P) : P := law.holds
theorem target (x y : Nat) (h : PhysicalLawWitness (x = y)) : x = y := by
  exact physicalLawHolds h
"""
MATCH = {"score": 7, "matched_terms": ["derivation", "completeness"]}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def document():
    return yaml.safe_load(CONTRACT.read_text())


def asset(path, text):
    return dict(
        path=path,
        content=text,
        encoding="text",
        sha256=hashlib.sha256(text.encode()).hexdigest(),
    )


class RegisteredRemote:
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


async def invoke(inputs, d=None, tools_missing=False):
    d = document() if d is None else d
    values = {
        s["path"]: (ROOT / s["path"]).read_text() for s in d["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    values[DESCRIPTOR] = json.dumps(d)
    assets = [asset(p, t) for p, t in values.items()]
    workflows = workflow_documents([DESCRIPTOR], assets)
    assert workflows[0]["validation"]["valid"], workflows[0]
    remote = RegisteredRemote()
    tools = [
        t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
    ]
    compiled = compile_workflow(
        "mcp:mathformer", workflows[0], [] if tools_missing else tools
    )
    if tools_missing:
        assert not compiled["runnable"]
        return
    assert compiled["runnable"], compiled["diagnostics"]
    assert compiled["runtime_status"] == "ready"
    assert compiled["prism_source"] and compiled["runtime_source"] and compiled["graph"]

    async def authorize():
        pass

    result = await execute(compiled, assets, inputs, remote, authorize)
    return result, remote.history


@pytest.fixture
def tree(tmp_path):
    # The native checker has no provider, compiler or theorem-prover dependency.
    # Run its identical source bytes in an isolated repository, never production data.
    for relative in hub.build_registry()[ACTION].required_paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(
            (ROOT / LEAF).read_bytes() if relative == LEAF else GOOD.encode()
        )
    for flag in ["--source-record", "--recursive-plan"]:
        target = tmp_path / COMMAND[COMMAND.index(flag) + 1]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{}")
    return tmp_path


def inputs(root, **context):
    return dict(
        context=vars(hub.RunContext(**context)),
        match=MATCH,
        registry=REGISTRY,
        repository_root=str(root),
    )


def run(root, d=None, **context):
    return asyncio.run(invoke(inputs(root, **context), d))


@pytest.mark.parametrize(
    "text,frontier,expected",
    [
        (GOOD, 0, "complete_autoformalization"),
        (BAD, 0, "blocked_target_restating_assumption"),
        (GOOD, 2, "derivation_partial"),
    ],
)
@pytest.mark.parametrize("keep", [False, True])
def test_real_checker_route_and_original_parity(tree, text, frontier, expected, keep):
    lean = tree / COMMAND[COMMAND.index("--lean-file") + 1]
    lean.write_text(text)
    plan = tree / COMMAND[COMMAND.index("--recursive-plan") + 1]
    # Native plan frontier shape, rather than a made-up loop counter.
    plan.write_text(json.dumps({"recursive_frontier": [{}] * frontier}))
    result, history = run(tree, keep_going=keep)
    assert result["status"] == "accepted", result
    output = result["outputs"]["result"]
    assert output["ok"] and output["status"] == "intent_run_completed"
    assert len(output["children"]) == 1
    child = output["children"][0]
    assert child["argv"] == [sys.executable, *COMMAND[1:]]
    assert child["write_audit"]["ok"] and child["returncode"] == 0
    report = json.loads(child["stdout"])
    assert report["status"] == expected
    assert report["ok"] == (expected == "complete_autoformalization")
    assert report["summary"]["file_count"] == 1
    assert report["summary"]["recursive_frontier_count"] == frontier
    assert (
        json.loads((tree / COMMAND[COMMAND.index("--output") + 1]).read_text())
        == report
    )
    assert [name.rsplit("_", 1)[-1] for name, _ in history] == [
        "initialize",
        "select",
        "execute",
        "advance",
        "finish",
    ]
    assert history[1][1]["state"] == {"ok": True, "children": []}
    assert history[-1][1]["state"] == {"ok": True, "children": [child]}
    # Compare with the selected source frozen before this implementation pass.
    original = load(
        ROOT / "tests/mcp/fixtures/derivation_completeness_route_original.py",
        "_derivation_original",
    )
    (tree / COMMAND[COMMAND.index("--output") + 1]).unlink()
    expected_result = original.run_intent_match(
        selected_match(MATCH),
        checked_registry(REGISTRY),
        original.RunContext(keep_going=keep),
        repository_root=tree,
    )
    assert output == expected_result
    assert result["replay_artifacts"] and result["runtime"]["effect_records"]


def test_preflight_dry_run_failure_data_and_bound(tree):
    result, history = run(tree, dry_run=True)
    assert result["outputs"]["result"]["children"][0]["status"] == "dry_run"
    assert not (tree / COMMAND[COMMAND.index("--output") + 1]).exists()
    (tree / LEAF).unlink()
    result, history = run(tree)
    assert result["status"] == "accepted"
    output = result["outputs"]["result"]
    assert not output["ok"] and output["status"] == "intent_run_failed"
    assert output["children"][0]["preflight_errors"] == [
        "missing required path: " + LEAF
    ]
    assert len(history) == 5  # Failure is data; the single iteration still finishes.
    for kind in ["exhaustion", "budget"]:
        d = document()
        if kind == "exhaustion":
            d["flow"]["steps"][1]["until"] = {"literal": False}
        else:
            d["policy"]["limits"]["max_operation_calls"] = 3
        result, history = run(tree, d, dry_run=True)
        assert result["status"] == "failed" and result["outputs"] is None
        assert len(history) == (4 if kind == "exhaustion" else 3)
        assert all(not name.endswith("_finish") for name, _ in history)


def test_process_error_preserves_stdout_stderr_and_no_retry(tree):
    (tree / COMMAND[COMMAND.index("--source-record") + 1]).write_text("invalid JSON")
    result, history = run(tree)
    assert result["status"] == "accepted"
    output = result["outputs"]["result"]
    assert not output["ok"]
    child = output["children"][0]
    assert child["returncode"] != 0 and child["stdout"] == ""
    assert "JSONDecodeError" in child["stderr"] and child["write_audit"]["ok"]
    assert sum(name.endswith("_execute") for name, _ in history) == 1


def test_service_authority_and_forged_registry(tree, monkeypatch):
    monkeypatch.setattr(mcp_server, "_READONLY", True)
    result, history = run(tree)
    assert result["status"] == "failed" and len(history) == 3
    monkeypatch.setattr(mcp_server, "_READONLY", False)
    monkeypatch.setattr(mcp_server, "_ALLOWED_WRITE_ROOTS", [tree / "elsewhere"])
    result, history = run(tree)
    assert result["status"] == "failed" and len(history) == 3
    assert not (tree / COMMAND[COMMAND.index("--output") + 1]).exists()
    request = inputs(tree, dry_run=True)
    request["registry"] = deepcopy(REGISTRY)
    request["registry"][ACTION]["command"] = ["untrusted"]
    result, history = asyncio.run(invoke(request))
    assert result["status"] == "failed" and len(history) == 3


def test_native_leaf_traversal_cli_exit_and_worst_status(tree, monkeypatch, capsys):
    native = load(ROOT / LEAF, "_derivation_checker")
    good, bad, missing = tree / "good.lean", tree / "bad.lean", tree / "missing.lean"
    good.write_text(GOOD)
    bad.write_text(BAD)
    missing.write_text(GOOD)
    args = native.parse_args(
        ["--lean-file", str(bad), "--lean-file", str(good), "--lean-file", str(missing)]
    )
    state = native.initialize_report(args)
    for i in range(3):
        assert state["index"] == i and len(state["artifacts"]) == i
        transition = native.advance_report(state, native.analyze_current(state))
        assert transition["done"] == (i == 2)
        state = transition["state"]
    report = native.aggregate_report(state)
    assert report == native.build_report(args)
    assert (
        report["status"] == "blocked_target_restating_assumption"
        and len(report["artifacts"]) == 3
    )
    assert [a["status"] for a in report["artifacts"]] == [
        "blocked_target_restating_assumption",
        "complete_autoformalization",
        "complete_autoformalization",
    ]
    for expect in [False, True]:
        argv = ["--lean-file", str(bad), "--json"] + (
            ["--expect-complete"] if expect else []
        )
        assert native.main(argv) == int(expect)
        assert not json.loads(capsys.readouterr().out)["ok"]
    with pytest.raises(SystemExit, match="--lean-file is required"):
        native.main([])
    missing.unlink()
    with pytest.raises(FileNotFoundError):
        native.build_report(args)
    # Execute the real self-test branch with its artifacts confined to the fixture tree.
    monkeypatch.setattr(native, "REPO_ROOT", tree)
    assert native.main(["--self-test", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]


def test_deterministic_external_compiler_failure_and_write_audit(tree, monkeypatch):
    # Only this generic launcher test substitutes an external compiler boundary.
    # The selected checker above executes as a real isolated Python process.
    calls = []

    def compiler(command, **kw):
        calls.append((command, kw))
        assert command == ["fixture-compiler"] and kw["timeout"] is None
        assert kw["cwd"] == tree and kw["text"]
        (tree / "undeclared.txt").write_text("compiler output")
        return subprocess.CompletedProcess(
            command, 7, "rejected fixture\n", "compiler diagnostic\n"
        )

    monkeypatch.setattr(
        hub,
        "subprocess",
        SimpleNamespace(
            run=compiler, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
        ),
    )
    item = replace(
        hub.build_registry()[ACTION], command=("fixture-compiler",), required_paths=()
    )
    result = hub.run_action(
        ACTION, {ACTION: item}, hub.RunContext(), repository_root=tree
    )
    assert not result["ok"] and result["status"] == "undeclared_writes"
    assert result["returncode"] == 7 and result["stdout"] == "rejected fixture\n"
    assert "compiler diagnostic" in result["stderr"]
    assert (
        result["write_audit"]["unexpected_paths"] == ["undeclared.txt"]
        and len(calls) == 1
    )


def test_contract_generator_provenance_interfaces_and_unavailable_bindings(tree):
    d = document()
    generator = load(
        ROOT
        / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        "_derivation_generator",
    )
    assert generator.derivation_completeness_route_descriptor() == d
    assert d["id"] == "route_validate_physics_lean_derivation_completeness_workflow"
    assert d["aliases"] == [ROUTE] and d["lifecycle"] == "active"
    assert d["policy"]["limits"] == {
        "wall_time_seconds": 3600,
        "max_operation_calls": 5,
    }
    assert d["policy"]["failure"]["retry"] == {"max_attempts": 1, "retryable_codes": []}
    for row in d["provenance"]["sources"]:
        assert (
            row["digest"]
            == "sha256:" + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest()
        )
    assert any(
        s["path"] == "scripts/mathformer.py" and s["selector"] == "run_intent_match"
        for s in d["provenance"]["sources"]
    )
    # Validate with the installed schema base even when candidate is outside repo.
    # workflow_documents above validates with exact installed paths, including
    # source digests and external schemas, even for an out-of-tree candidate.
    if CONTRACT.is_relative_to(ROOT):
        validation = validate(
            CONTRACT, repository_root=ROOT, require_declared_bindings=True
        )
        assert not validation["errors"], validation
    tools = {
        t.name: t.model_dump(by_alias=True, exclude_none=True)
        for t in asyncio.run(RegisteredRemote().tools())
    }
    for op in d["operations"].values():
        binding = op["execution"]["binding"]
        assert binding["operation"] == binding["target"]
        tool = tools[binding["target"]]
        assert set(tool["inputSchema"]["properties"]) == set(op["inputs"])
        assert set(tool["outputSchema"]["properties"]) == set(op["outputs"])
    asyncio.run(invoke(inputs(tree, dry_run=True), tools_missing=True))
    for keep in [True, False]:
        updated, done = hub.advance_intent_state(
            {"ok": False, "children": []},
            {"ok": True},
            hub.RunContext(keep_going=keep),
            1,
        )
        assert done and not updated["ok"]
    with pytest.raises(ValueError):
        check_state({"ok": True, "children": [{"ok": False}]})
    with pytest.raises(ValueError):
        check_state({"ok": True, "children": [{"ok": True}]}, selecting=True)


if __name__ == "__main__":

    class RequiredPasses:
        passed = 0

        def pytest_runtest_logreport(self, report):
            if report.when == "call" and report.passed:
                self.passed += 1

    results = RequiredPasses()
    code = pytest.main(["-q", str(Path(__file__).resolve())], plugins=[results])
    raise SystemExit(int(code) if code else (0 if results.passed else 1))
