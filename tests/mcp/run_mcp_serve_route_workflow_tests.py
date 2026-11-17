#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline native parity, advertised MCP bindings and real Lunar/PRISM runtime.

The selected server action is only dry-run or rejected before process launch.
Only a separate external compiler boundary is substituted, in test code.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(
        str(python), [str(python), "-B", str(Path(__file__).resolve()), *sys.argv[1:]]
    )
sys.dont_write_bytecode = True
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from mcp_serve_route_tools import ACTION, ROUTE, selected_match, check_state
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_mcp_serve_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
ORDER = ["initialize", "select_action", "execute_action", "advance", "finish"]
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 29,
    "matched_terms": ["start", "mcp server"],
}


def original():
    scope = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/mcp_serve_route_original.py.txt").read_text(), scope
    )
    return scope["run_intent_match"]


def prepare(root, ready=True):
    (root / "scripts").mkdir(exist_ok=True)
    for name in ["mathformer.py", "mcp_server.py"]:
        target = root / "scripts" / name
        if name == "mcp_server.py" and not ready:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes((ROOT / "scripts" / name).read_bytes())


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
            content=t,
            encoding="text",
            sha256=hashlib.sha256(t.encode()).hexdigest(),
        )
        for p, t in values.items()
    ]


@asynccontextmanager
async def preserve_errors(session):
    failure = None
    async with session as remote:
        try:
            yield remote
        except Exception as error:
            failure = error
    if failure:
        raise failure


class ServeRouteTests(unittest.TestCase):
    maxDiff = None

    def test_contract_generator_identity_policies_and_digests(self):
        document = yaml.safe_load(CONTRACT.read_text())
        spec = importlib.util.spec_from_file_location(
            "serve_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(generator.mcp_serve_route_descriptor(), document)
        self.assertEqual(document["id"], "route_mcp_serve_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            document["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertEqual(
            document["policy"]["effects"]["network"],
            ["native_binding_capabilities_require_qualification"],
        )
        self.assertEqual(
            document["policy"]["effects"]["external_write"],
            ["native_binding_capabilities_require_qualification"],
        )
        self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 1)
        self.assertEqual(document["flow"]["steps"][1]["on_exhausted"], "fail")
        self.assertEqual(list(document["operations"]), ORDER)
        self.assertTrue(
            any(
                r["path"] == "scripts/mathformer.py"
                and r["selector"] == "run_intent_match"
                for r in document["provenance"]["sources"]
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        item = hub.build_registry()[ACTION]
        self.assertEqual(item.command, ("{python}", "scripts/mcp_server.py"))
        self.assertIsNone(item.timeout_seconds)  # CLI remains unbounded
        self.assertEqual((item.depends_on, item.writes), ((), ()))

    def test_original_entrypoint_and_native_state(self):
        oracle, match = original(), selected_match(MATCH)
        registry = {ACTION: hub.build_registry()[ACTION]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for ready in (False, True):
                prepare(root, ready)
                for keep in (False, True):
                    for dry in ((False, True) if not ready else (True,)):
                        context = hub.RunContext(dry_run=dry, keep_going=keep)
                        expected = oracle(
                            match, registry, context, repository_root=root
                        )
                        actual = hub.run_intent_match(
                            match, registry, context, repository_root=root
                        )
                        self.assertEqual(actual, expected)
                        self.assertEqual(actual["ok"], ready)
                        self.assertEqual(len(actual["children"]), 1)
                        self.assertNotIn("returncode", actual["children"][0])
            self.assertFalse((root / "artifacts").exists())
        for keep in (False, True):
            for child in ({"ok": True}, {"ok": False}, {}):
                state = hub.initialize_intent_state()
                updated, done = hub.advance_intent_state(
                    state, child, hub.RunContext(keep_going=keep), 1
                )
                self.assertEqual(state, {"ok": True, "children": []})
                self.assertEqual(
                    updated, {"ok": bool(child.get("ok", False)), "children": [child]}
                )
                self.assertTrue(done)  # keep-going cannot add a second server
                check_state(updated, complete=True)
                with self.assertRaises(ValueError):
                    check_state(updated)
            state, done = hub.advance_intent_state(
                hub.initialize_intent_state(),
                {"ok": False},
                hub.RunContext(keep_going=keep),
                2,
            )
            self.assertEqual(done, not keep)
            state, done = hub.advance_intent_state(
                state, {"ok": True}, hub.RunContext(keep_going=keep), 2
            )
            self.assertFalse(state["ok"])
            self.assertTrue(done)

    def test_deterministic_external_compiler_failure_boundary(self):
        # Separate compiler action: never replaces or runs the mcp:serve leaf.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            saved = hub.subprocess
            try:
                for mode in ("success", "reject", "write", "timeout", "launch_error"):
                    item = replace(
                        hub.build_registry()[ACTION],
                        action_id="fixture:compiler",
                        command=("fixture-reasoning-compiler", mode),
                        required_paths=(),
                        timeout_seconds=3 if mode == "timeout" else None,
                    )
                    calls = install(hub, root)
                    if mode == "launch_error":
                        with self.assertRaisesRegex(OSError, "compiler launch failed"):
                            hub.run_action(
                                item.action_id,
                                {item.action_id: item},
                                hub.RunContext(),
                                repository_root=root,
                            )
                    else:
                        child = hub.run_action(
                            item.action_id,
                            {item.action_id: item},
                            hub.RunContext(),
                            repository_root=root,
                        )
                        self.assertEqual(child["ok"], mode == "success")
                        self.assertEqual(
                            child["status"],
                            {"write": "undeclared_writes", "timeout": "timeout"}.get(
                                mode, "completed"
                            ),
                        )
                        if mode in ("success", "reject"):
                            report = json.loads(child["stdout"])
                            self.assertFalse(
                                report["ok"]
                            )  # process exit owns native success
                            self.assertEqual(
                                report["artifact"]["nodes"], ["input", "check"]
                            )
                            self.assertEqual(
                                report["diagnostics"][0]["code"], "fixture_type_error"
                            )
                            self.assertEqual(
                                child["returncode"], 0 if mode == "success" else 7
                            )
                        elif mode == "write":
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        elif mode == "timeout":
                            self.assertEqual(
                                (child["returncode"], child["stdout"], child["stderr"]),
                                (None, "partial", "deadline"),
                            )
                    self.assertEqual(
                        calls,
                        [{"argv": list(item.command), "timeout": item.timeout_seconds}],
                    )
                    (root / "undeclared.txt").unlink(missing_ok=True)
            finally:
                hub.subprocess = saved

    def test_registered_mcp_and_lunar_compile_execute(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        for mode in ("normal", "launch_error"):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                prepare(root)
                manager = SessionManager()
                async with preserve_errors(
                    manager.open(
                        "serve-route",
                        StdioConfig(
                            command=sys.executable,
                            args=[
                                "-B",
                                "tests/mcp/fixtures/mcp_serve_route_server.py",
                                str(root),
                                mode,
                            ],
                            cwd=str(ROOT),
                        ),
                        {"PYTHONDONTWRITEBYTECODE": "1"},
                    )
                ) as remote:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile(doc=document, inventory=None):
                        assets = snapshot(doc)
                        workflow = workflow_documents([DESCRIPTOR], assets)[0]
                        self.assertTrue(workflow["validation"]["valid"], workflow)
                        compiled = compile_workflow(
                            "mcp:serve-route",
                            workflow,
                            tools if inventory is None else inventory,
                        )
                        return compiled, assets

                    compiled, assets = compile()
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertEqual(compiled["runtime_status"], "ready")
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(set(compiled["bindings"]), set(ORDER))
                    missing = [
                        t
                        for t in tools
                        if t["name"] != "mathformer_mcp_serve_route_execute"
                    ]
                    self.assertFalse(compile(inventory=missing)[0]["runnable"])

                    async def authorize():
                        pass

                    async def run(inputs, changed=None):
                        c, a = compile(changed) if changed else (compiled, assets)
                        self.assertTrue(c["runnable"], c["diagnostics"])
                        return await execute(c, a, inputs, remote, authorize)

                    inputs = await remote.call(
                        "mathformer_mcp_serve_route_inputs", {"dry_run": True}
                    )
                    self.assertEqual(inputs["registry"][ACTION]["timeout_seconds"], 17)
                    inputs["match"].update(
                        score=29, matched_terms=MATCH["matched_terms"]
                    )
                    item = replace(hub.build_registry()[ACTION], timeout_seconds=17)
                    registry = {ACTION: item}
                    if mode == "launch_error":
                        inputs["context"]["dry_run"] = False
                        for entry in (original(), hub.run_intent_match):
                            with patch.object(
                                sys, "executable", str(root / "unavailable-python")
                            ):
                                with self.assertRaises(FileNotFoundError):
                                    entry(
                                        selected_match(inputs["match"]),
                                        registry,
                                        hub.RunContext(**inputs["context"]),
                                        repository_root=root,
                                    )
                        result = await run(inputs)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], ORDER[:3]
                        )
                        self.assertEqual(result["calls"][-1]["status"], "rejected")
                        continue
                    for ready in (True, False):
                        prepare(root, ready)
                        for dry in ((True,) if ready else (False, True)):
                            for keep in (False, True):
                                inputs["context"].update(dry_run=dry, keep_going=keep)
                                inputs["repository_root"] = str(root) if keep else None
                                with patch.object(hub, "REPO_ROOT", root):
                                    expected = original()(
                                        selected_match(inputs["match"]),
                                        registry,
                                        hub.RunContext(**inputs["context"]),
                                        repository_root=root,
                                    )
                                result = await run(inputs)
                                self.assertEqual(result["status"], "accepted", result)
                                self.assertEqual(
                                    result["outputs"], {"result": expected}
                                )
                                self.assertEqual(
                                    [c["operation"] for c in result["calls"]], ORDER
                                )
                                self.assertEqual(
                                    result["outputs"]["result"]["ok"], ready
                                )
                                self.assertEqual(len(expected["children"]), 1)
                                self.assertEqual(expected["route"]["score"], 29)
                                self.assertEqual(
                                    expected["route"]["matched_terms"],
                                    MATCH["matched_terms"],
                                )
                                self.assertTrue(result["runtime"]["effect_records"])
                                self.assertTrue(result["replay_artifacts"])
                                if ready:
                                    self.assertEqual(
                                        expected["children"][0]["status"], "dry_run"
                                    )
                                else:
                                    self.assertIn(
                                        "missing required path",
                                        str(
                                            expected["children"][0]["preflight_errors"]
                                        ),
                                    )
                                self.assertNotIn("returncode", expected["children"][0])
                    prepare(root)
                    inputs["context"]["dry_run"] = True
                    for mount in ("omitted", None, str(root)):
                        values = deepcopy(inputs)
                        if mount == "omitted":
                            values.pop("repository_root")
                        else:
                            values["repository_root"] = mount
                        self.assertTrue((await run(values))["outputs"]["result"]["ok"])
                    unknown = deepcopy(inputs)
                    unknown["registry"] = {}
                    result = await run(unknown)
                    with patch.object(hub, "REPO_ROOT", root):
                        with self.assertRaises(KeyError):
                            original()(
                                selected_match(inputs["match"]),
                                {},
                                hub.RunContext(**inputs["context"]),
                                repository_root=root,
                            )
                    self.assertEqual(result["status"], "failed")
                    self.assertIsNone(result["outputs"])
                    self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    child = await remote.call(
                        "mathformer_mcp_serve_route_execute",
                        {
                            "action_id": ACTION,
                            "registry": {},
                            "context": inputs["context"],
                        },
                    )
                    self.assertEqual(
                        child,
                        {
                            "child": {
                                "ok": False,
                                "status": "unknown_action",
                                "action_id": ACTION,
                            }
                        },
                    )
                    for forged in ("registry", "timeout", "match", "mount"):
                        values = deepcopy(inputs)
                        if forged == "registry":
                            values["registry"][ACTION]["command"] = ["unregistered"]
                        elif forged == "timeout":
                            values["registry"][ACTION]["timeout_seconds"] = None
                        elif forged == "match":
                            values["match"]["route"]["title"] = "invented"
                        else:
                            values["repository_root"] = str(root / "other")
                        result = await run(values)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            result["calls"][-1]["operation"],
                            "select_action" if forged == "match" else "execute_action",
                        )
                    for state in (
                        {"ok": False, "children": []},
                        {"ok": True, "children": [{"ok": True}]},
                    ):
                        with self.assertRaises(ValueError):
                            await remote.call(
                                "mathformer_mcp_serve_route_select",
                                {"state": state, "match": inputs["match"]},
                            )
                    for keep in (False, True):
                        inputs["context"]["keep_going"] = keep
                        observed = await remote.call(
                            "mathformer_mcp_serve_route_advance",
                            {
                                "state": {"ok": True, "children": []},
                                "child": {"ok": False},
                                "context": inputs["context"],
                            },
                        )
                        self.assertEqual(
                            observed,
                            {
                                "state": {"ok": False, "children": [{"ok": False}]},
                                "done": True,
                            },
                        )
                    for limit in (1, 3, 4):
                        changed = deepcopy(document)
                        changed["policy"]["limits"]["max_operation_calls"] = limit
                        result = await run(inputs, changed)
                        self.assertEqual(result["status"], "failed")
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            sum(
                                bool(c.get("transport_call_performed"))
                                for c in result["calls"]
                            ),
                            limit,
                        )
                    changed = deepcopy(document)
                    changed["flow"]["steps"][1]["until"] = {"literal": False}
                    exhausted = await run(inputs, changed)
                    self.assertEqual(exhausted["status"], "failed")
                    self.assertEqual(exhausted["failure_disposition"], "fail")
                    self.assertIsNone(exhausted["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in exhausted["calls"]], ORDER[:-1]
                    )
                    self.assertFalse((root / "artifacts").exists())
                self.assertFalse(manager.active)


if __name__ == "__main__":
    suite = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if suite.wasSuccessful() and suite.testsRun > len(suite.skipped) else 1
    )
