#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline source parity and real MCP/PRISM compile-execute tests for setup.lean."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
FIXTURES = ROOT / "tests/mcp/fixtures"
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(FIXTURES),
    str(ROOT),
    *SITES,
]

import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from setup_lean_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    register_setup_lean_route_tools,
)
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_setup_lean_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
AUTHORED = "skills/control/workflow-contract-validator/references/setup-lean-route.workflow.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 17.5,
    "matched_terms": ["setup", "lean"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select_action", "run_action", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "setup_lean_route_original.py.txt").read_text(), scope)
    return SimpleNamespace(**scope)


def populate(root):
    path = root / "scripts/install_env.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "scripts/install_env.py", path)


def binary(root):
    directory = root.parent / "bin"
    directory.mkdir(exist_ok=True)
    launcher = directory / "lake"
    launcher.write_text(
        "#!"
        + sys.executable
        + "\nimport sys\nsys.path.insert(0, "
        + repr(str(FIXTURES))
        + ")\nfrom setup_lean_route_boundary import boundary\nraise SystemExit(boundary())\n"
    )
    launcher.chmod(0o755)
    return directory


def reset(root, mode="success"):
    shutil.rmtree(root / ".lake", ignore_errors=True)
    (root / "unexpected.txt").unlink(missing_ok=True)
    (root.parent / "lake.jsonl").unlink(missing_ok=True)
    (root.parent / "mode.txt").write_text(mode)


def launches(root):
    path = root.parent / "lake.jsonl"
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def snapshot(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=p,
            content=s,
            encoding="text",
            sha256=hashlib.sha256(s.encode()).hexdigest(),
        )
        for p, s in values.items()
    ]


class SetupLeanTests(unittest.TestCase):
    maxDiff = None

    def test_contract_generator_and_provenance(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        spec = importlib.util.spec_from_file_location(
            "setup_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(generator.setup_lean_route_descriptor(), doc)
        self.assertEqual(json.loads((ROOT / AUTHORED).read_text()), doc)
        self.assertEqual(doc["id"], "route_setup_lean_workflow")
        self.assertEqual(doc["aliases"], [ROUTE])
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            doc["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertEqual(list(doc["operations"]), ORDER)
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertTrue(
            any(
                row["path"] == "scripts/mathformer.py"
                and row["selector"] == "run_intent_match"
                for row in doc["provenance"]["sources"]
            )
        )
        self.assertIsNone(checked_registry(REGISTRY)[ACTION].timeout_seconds)
        audit = hub.audit_control(hub.build_registry())
        for path in [
            "scripts/setup_lean_route_tools.py",
            "tests/mcp/run_setup_lean_route_workflow_tests.py",
            "tests/mcp/fixtures/setup_lean_route_boundary.py",
        ]:
            self.assertNotIn(path, audit["uncontrolled_entrypoints"])

    def test_state_history_and_stopping(self):
        for keep in [False, True]:
            for ok in [False, True]:
                state = hub.initialize_intent_state()
                before = deepcopy(state)
                child = {"ok": ok, "stdout": "source evidence"}
                updated, done = hub.advance_intent_state(
                    state, child, hub.RunContext(keep_going=keep), 1
                )
                self.assertEqual(state, before)
                self.assertEqual(updated, {"ok": ok, "children": [child]})
                self.assertTrue(done)
                self.assertEqual(
                    hub.select_intent_action(state, selected_match(MATCH)), ACTION
                )
        state, done = hub.advance_intent_state(
            {"ok": True, "children": []},
            {"ok": False},
            hub.RunContext(keep_going=True),
            2,
        )
        self.assertFalse(done)
        state, done = hub.advance_intent_state(
            state, {"ok": True}, hub.RunContext(keep_going=True), 2
        )
        self.assertFalse(state["ok"])
        self.assertTrue(done)
        self.assertEqual(state["children"], [{"ok": False}, {"ok": True}])

    def test_real_mcp_lunar_and_native_parity(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "repo"
            populate(root)
            bin_dir = binary(root)
            reset(root)
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr([str(ROOT / "scripts"), str(FIXTURES), str(ROOT), *SITES])
                + ";from setup_lean_route_boundary import serve;serve("
                + repr(str(root))
                + ","
                + repr(str(bin_dir))
                + ")"
            )
            manager = SessionManager()
            async with manager.open(
                "setup-lean",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(document, inventory=None):
                    assets = snapshot(document)
                    bound = compile_workflow(
                        "mcp:setup-lean",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools if inventory is None else inventory,
                    )
                    return bound, assets

                bound, assets = compile(doc)
                self.assertTrue(bound["runnable"], bound["diagnostics"])
                self.assertEqual(bound["runtime_status"], "ready")
                self.assertTrue(bound["prism_source"])
                self.assertTrue(bound["runtime_source"])
                self.assertEqual(set(bound["bindings"]), set(ORDER))
                self.assertFalse(compile(doc, [])[0]["runnable"])
                broken = deepcopy(doc)
                broken["operations"]["run_action"]["execution"]["binding"][
                    "target"
                ] = "absent_tool"
                self.assertFalse(compile(broken)[0]["runnable"])
                inventory = {t["name"]: t for t in tools}
                for op in doc["operations"].values():
                    binding = op["execution"]["binding"]
                    self.assertEqual(binding["target"], binding["operation"])
                    tool = inventory[binding["target"]]
                    self.assertEqual(
                        set(tool["inputSchema"]["properties"]), set(op["inputs"])
                    )
                    self.assertEqual(
                        set(tool["outputSchema"]["properties"]), set(op["outputs"])
                    )

                async def authorize():
                    pass

                base = dict(
                    match=MATCH,
                    registry=REGISTRY,
                    repository_root=str(root),
                    context=vars(hub.RunContext(allow_mutating=True)),
                )

                async def run(inputs=None, document=None):
                    c, a = (
                        compile(document) if document is not None else (bound, assets)
                    )
                    self.assertTrue(c["runnable"], c["diagnostics"])
                    return await execute(
                        c, a, base if inputs is None else inputs, remote, authorize
                    )

                for mode in [
                    "success",
                    "missing_lake",
                    "update_failure",
                    "build_failure",
                    "undeclared_write",
                ]:
                    for keep in [False, True]:
                        reset(root, mode)
                        lake = bin_dir / "lake"
                        if mode == "missing_lake":
                            lake.rename(bin_dir / "hidden")
                        try:
                            inputs = deepcopy(base)
                            inputs["context"]["keep_going"] = keep
                            result = await run(inputs)
                            self.assertEqual(result["status"], "accepted", result)
                            route = result["outputs"]["result"]
                            child = route["children"][0]
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]], ORDER
                            )
                            self.assertEqual(
                                [c["tool"] for c in result["calls"]],
                                ["mathformer_setup_lean_route_" + op for op in ORDER],
                            )
                            self.assertEqual(len(route["children"]), 1)
                            self.assertEqual(route["route"]["score"], MATCH["score"])
                            self.assertEqual(
                                route["route"]["matched_terms"], MATCH["matched_terms"]
                            )
                            self.assertEqual(route["ok"], mode == "success")
                            self.assertEqual(
                                route["status"],
                                (
                                    "intent_run_completed"
                                    if mode == "success"
                                    else "intent_run_failed"
                                ),
                            )
                            self.assertEqual(
                                child["argv"],
                                [
                                    sys.executable,
                                    "scripts/install_env.py",
                                    "--skip-python",
                                    "--with-lean",
                                ],
                            )
                            calls = launches(root)
                            expected = (
                                []
                                if mode == "missing_lake"
                                else [dict(argv=[str(lake), "update"], cwd=str(root))]
                            )
                            if mode not in ["missing_lake", "update_failure"]:
                                expected.append(
                                    dict(argv=[str(lake), "build"], cwd=str(root))
                                )
                            self.assertEqual(calls, expected)
                            self.assertEqual(
                                (root / ".lake/update").exists(),
                                mode
                                in ["success", "build_failure", "undeclared_write"],
                            )
                            self.assertEqual(
                                (root / ".lake/build").exists(),
                                mode in ["success", "undeclared_write"],
                            )
                            self.assertFalse((root / ".venv").exists())
                            if mode == "success":
                                self.assertEqual(child["returncode"], 0)
                                self.assertIn("Running lake update", child["stdout"])
                                self.assertIn("Running lake build", child["stdout"])
                                self.assertIn(
                                    "Environment setup complete.", child["stdout"]
                                )
                                self.assertNotIn("Python dependencies", child["stdout"])
                            elif mode == "undeclared_write":
                                self.assertEqual(child["returncode"], 0)
                                self.assertEqual(child["status"], "undeclared_writes")
                                self.assertEqual(
                                    child["write_audit"]["unexpected_paths"],
                                    ["unexpected.txt"],
                                )
                            else:
                                self.assertNotEqual(child["returncode"], 0)
                                self.assertNotIn(
                                    "Environment setup complete.", child["stdout"]
                                )
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                            reset(root, mode)
                            with patch.dict(
                                os.environ,
                                {
                                    "PATH": str(bin_dir),
                                    "PYTHONDONTWRITEBYTECODE": "1",
                                    "PYTHONUNBUFFERED": "1",
                                },
                                clear=True,
                            ):
                                native = original().run_intent_match(
                                    selected_match(MATCH),
                                    checked_registry(REGISTRY),
                                    hub.RunContext(**inputs["context"]),
                                    repository_root=root,
                                )
                            self.assertEqual(route, native)
                            self.assertEqual(launches(root), calls)
                        finally:
                            if mode == "missing_lake":
                                (bin_dir / "hidden").rename(lake)
                reset(root)
                for missing in [False, True]:
                    if missing:
                        (root / "scripts/install_env.py").unlink()
                    for dry in [False, True]:
                        for allow in [False, True]:
                            if not missing and not dry and allow:
                                continue
                            for keep in [False, True]:
                                inputs = deepcopy(base)
                                inputs["context"].update(
                                    dry_run=dry, allow_mutating=allow, keep_going=keep
                                )
                                result = await run(inputs)
                                native = original().run_intent_match(
                                    selected_match(MATCH),
                                    checked_registry(REGISTRY),
                                    hub.RunContext(**inputs["context"]),
                                    repository_root=root,
                                )
                                self.assertEqual(result["outputs"], {"result": native})
                                self.assertEqual(len(result["calls"]), 5)
                                self.assertEqual(launches(root), [])
                populate(root)
                inputs = deepcopy(base)
                inputs["context"]["dry_run"] = True
                inputs["repository_root"] = None
                result = await run(inputs)
                self.assertEqual(
                    result["outputs"]["result"]["children"][0]["status"], "dry_run"
                )
                inputs["repository_root"] = str(root)
                for port in ["match", "registry"]:
                    forged = deepcopy(inputs)
                    if port == "match":
                        forged[port]["route"]["title"] = "forged title"
                    else:
                        forged[port][ACTION]["command"] = ["arbitrary-command"]
                    result = await run(forged)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 2 if port == "match" else 3)
                for budget in [1, 4]:
                    changed = deepcopy(doc)
                    changed["policy"]["limits"]["max_operation_calls"] = budget
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        budget,
                    )
                changed = deepcopy(doc)
                changed["flow"]["steps"][1]["until"] = {"literal": False}
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:-1])
                self.assertIsNone(result["outputs"])
                self.assertIn("exhaust", str(result).lower())
                changed = deepcopy(doc)
                changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                    "state"
                ] = {"literal": {"ok": True, "children": [{"ok": True}]}}
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 2)
                inputs["context"]["dry_run"] = False
                inputs["repository_root"] = str(root.parent / "outside")
                result = await run(inputs)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 3)
                timed = deepcopy(doc)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                c, a = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(c, a, base, remote, pending)
            self.assertFalse(manager.active)

    def test_service_admission_and_launch_exception(self):
        asyncio.run(self.admission())

    async def admission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "repo"
            populate(root)
            args = dict(
                action_id=ACTION,
                registry=REGISTRY,
                repository_root=str(root),
                context=vars(hub.RunContext(allow_mutating=True)),
            )

            def readonly():
                raise PermissionError("service read-only policy")

            for authorize, allowed, error in [
                (readonly, lambda p: True, "read-only"),
                (lambda: None, lambda p: False, "service roots"),
            ]:
                mcp = FastMCP("setup-policy")
                register_setup_lean_route_tools(mcp, authorize, allowed)
                with self.assertRaisesRegex(Exception, error):
                    await mcp.call_tool("mathformer_setup_lean_route_run_action", args)
                args["context"]["dry_run"] = True
                await mcp.call_tool("mathformer_setup_lean_route_run_action", args)
                args["context"]["dry_run"] = False
            mcp = FastMCP("setup-launch")
            register_setup_lean_route_tools(mcp, lambda: None, lambda p: True)
            with patch.object(
                subprocess, "run", side_effect=OSError("fixture launch unavailable")
            ):
                with self.assertRaisesRegex(Exception, "fixture launch unavailable"):
                    await mcp.call_tool("mathformer_setup_lean_route_run_action", args)
                with self.assertRaisesRegex(OSError, "fixture launch unavailable"):
                    original().run_intent_match(
                        selected_match(MATCH),
                        checked_registry(REGISTRY),
                        hub.RunContext(allow_mutating=True),
                        repository_root=root,
                    )


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
