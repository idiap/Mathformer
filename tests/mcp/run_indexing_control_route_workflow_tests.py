#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native indexing route, registered MCP, real Lunar/PRISM, offline compiler."""

from tempfile import gettempdir

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
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml
import mathformer as hub
from indexing_control_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
)
from mathlib_indexing_control_tools import source
from indexing_route_tree import LEAF, PROFILE, populate, clean, stable
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_mathlib_indexing_control_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 17,
    "matched_terms": ["indexing", "control"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "run_action", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/indexing_route_original.py.txt").read_text(), scope
    )
    return SimpleNamespace(**scope)


def snapshot(document):
    values = {
        r["path"]: (ROOT / r["path"]).read_text()
        for r in document["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    values[DESCRIPTOR] = json.dumps(document)
    return [
        {
            "path": p,
            "content": v,
            "encoding": "text",
            "sha256": hashlib.sha256(v.encode()).hexdigest(),
        }
        for p, v in values.items()
    ]


def serve(base):
    from mcp_server import mcp, apply_runtime_config

    mount = Path(base).resolve()
    apply_runtime_config(allowed_write_roots=[str(mount)])

    @mcp.tool()
    def fixture_indexing_original(
        context: dict, match: dict, registry: dict, repository_root: str
    ) -> dict:
        root = Path(repository_root).resolve()
        assert root.is_relative_to(mount) and root != hub.REPO_ROOT
        return original().run_intent_match(
            selected_match(match),
            checked_registry(registry),
            hub.RunContext(**context),
            repository_root=root,
        )

    mcp.run(transport="stdio")


class IndexingRouteTests(unittest.TestCase):
    maxDiff = None

    def test_generator_identity_provenance_and_source_state(self):
        spec = importlib.util.spec_from_file_location(
            "indexing_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document, module.indexing_control_route_descriptor())
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document["id"], "route_mathlib_indexing_control_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            document["policy"]["failure"]["retry"],
            {"max_attempts": 1, "retryable_codes": []},
        )
        self.assertIn(
            {
                "path": "scripts/mathformer.py",
                "selector": "run_intent_match",
                "digest": "sha256:"
                + hashlib.sha256(
                    (ROOT / "scripts/mathformer.py").read_bytes()
                ).hexdigest(),
            },
            document["provenance"]["sources"],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        item = checked_registry(REGISTRY)[ACTION]
        self.assertEqual(item.command, ("{python}", LEAF, "--json"))
        self.assertEqual(item.timeout_seconds, 480)
        self.assertEqual(item.writes, ("artifacts/mathlib_index/",))
        self.assertFalse(item.depends_on)
        for keep in [False, True]:
            for child in [{"ok": True}, {"ok": False}, {}]:
                state = hub.initialize_intent_state()
                self.assertEqual(
                    hub.select_intent_action(state, selected_match(MATCH)), ACTION
                )
                updated, done = hub.advance_intent_state(
                    state, child, hub.RunContext(keep_going=keep), 1
                )
                self.assertEqual(state, {"ok": True, "children": []})
                self.assertEqual(
                    updated, {"ok": bool(child.get("ok", False)), "children": [child]}
                )
                self.assertTrue(done)
                check_state(updated)
                with self.assertRaises(ValueError):
                    check_state(updated, selecting=True)
            updated, done = hub.advance_intent_state(
                hub.initialize_intent_state(),
                {"ok": False},
                hub.RunContext(keep_going=keep),
                2,
            )
            self.assertEqual(done, not keep)
            updated, done = hub.advance_intent_state(
                updated, {"ok": True}, hub.RunContext(keep_going=keep), 2
            )
            self.assertFalse(updated["ok"])
            self.assertTrue(done)
        with self.assertRaises(ValueError):
            check_state({"ok": False, "children": []})
        state = {"position": 0, "results": []}
        for i in range(6):
            updated = source().advance_state(state, {"ok": i != 1, "index": i})
            self.assertEqual(updated["done"], i == 5)
            self.assertEqual(len(state["results"]), i)
            state = updated["state"]
        self.assertEqual([r["index"] for r in state["results"]], list(range(6)))
        self.assertFalse(source().commands_passed(state))
        with self.assertRaises(IndexError):
            source().execute_command(
                state, Path(str(Path(gettempdir()) / "mathformer-test-fixtures/unused"))
            )

    def test_external_compiler_timeout_capture_and_error_propagation(self):
        # Exercise the actual source process boundaries with a separate external
        # compiler; never replace any of the six selected native Python steps.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for mode in ["success", "reject", "write", "launch_error", "timeout"]:
                item = replace(
                    hub.build_registry()[ACTION],
                    command=("fixture-reasoning-compiler", mode),
                    required_paths=(),
                )
                with patch.object(hub, "subprocess", hub.subprocess):
                    calls = install(hub, root)
                    if mode == "launch_error":
                        with self.assertRaises(OSError):
                            hub.run_leaf_action(
                                item, hub.RunContext(), (), repository_root=root
                            )
                    else:
                        result = hub.run_leaf_action(
                            item, hub.RunContext(), (), repository_root=root
                        )
                        self.assertEqual(result["ok"], mode == "success")
                        self.assertEqual(
                            result["status"],
                            {"write": "undeclared_writes", "timeout": "timeout"}.get(
                                mode, "completed"
                            ),
                        )
                        if mode == "timeout":
                            self.assertEqual(
                                (
                                    result["returncode"],
                                    result["stdout"],
                                    result["stderr"],
                                ),
                                (None, "partial", "deadline"),
                            )
                        if mode == "write":
                            self.assertEqual(
                                result["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                    self.assertEqual(
                        calls, [{"argv": list(item.command), "timeout": 480}]
                    )
                (root / "undeclared.txt").unlink(missing_ok=True)
            native = source()
            with patch.object(native, "subprocess", native.subprocess):
                # run_command always prepends PYTHON, so use a compiler boundary
                # that asserts this real argv before returning its diagnostic.
                def compiler(argv, **kwargs):
                    self.assertEqual(argv[:2], [sys.executable, "fixture-compiler"])
                    self.assertEqual(kwargs["timeout"], 240)
                    self.assertEqual(kwargs["cwd"], root)
                    mode = argv[2]
                    if mode == "timeout":
                        raise subprocess.TimeoutExpired(argv, 240)
                    if mode == "launch":
                        raise OSError("compiler launch failed")
                    return subprocess.CompletedProcess(
                        argv,
                        3 if mode == "reject" else 0,
                        {
                            "text": "not json",
                            "array": "[]",
                            "negative": '{"ok":false}',
                            "zero": '{"ok":0}',
                        }.get(mode, '{"ok":true}'),
                        "diagnostic",
                    )

                native.subprocess = SimpleNamespace(run=compiler, PIPE=subprocess.PIPE)
                for mode in ["timeout", "launch", "array"]:
                    with self.assertRaises(
                        {
                            "timeout": subprocess.TimeoutExpired,
                            "launch": OSError,
                            "array": AttributeError,
                        }[mode]
                    ):
                        native.run_command(["fixture-compiler", mode], root)
                for mode in ["success", "reject", "text", "negative", "zero"]:
                    result = native.run_command(["fixture-compiler", mode], root)
                    self.assertEqual(result["ok"], mode in ["success", "text", "zero"])
                    self.assertEqual(
                        result["command"], [sys.executable, "fixture-compiler", mode]
                    )
                    if mode == "text":
                        self.assertEqual(result["payload"], {"stdout": "not json"})

    def test_real_registered_lunar_compile_execute(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        with tempfile.TemporaryDirectory() as directory:
            mount = Path(directory).resolve()
            boundary = ROOT / "tests/mcp/fixtures/indexing_route_boundary"
            env = {
                "PYTHONPATH": os.pathsep.join([str(boundary), *SITES]),
                "LUNAR_PLATFORM_ROOT": str(LUNAR),
                "WORKFLOW_CONTRACT_PATH": str(CONTRACT),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            failure = None
            async with manager.open(
                "indexing-route",
                StdioConfig(
                    command=sys.executable,
                    args=[str(Path(__file__).resolve()), "--serve-fixture", str(mount)],
                    cwd=str(ROOT),
                ),
                env,
            ) as remote:
                try:
                    await self.connected(remote, mount)
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure is not None:
                raise failure

    async def connected(self, remote, mount):
        document = yaml.safe_load(CONTRACT.read_text())
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(doc, inventory=tools):
            assets = snapshot(doc)
            sources = workflow_documents([DESCRIPTOR], assets)
            self.assertTrue(sources[0]["validation"]["valid"], sources)
            c = compile_workflow("mcp:indexing-route", sources[0], inventory)
            return c, assets

        compiled, assets = compile(document)
        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
        self.assertEqual(compiled["runtime_status"], "ready")
        self.assertTrue(compiled["prism_source"])
        self.assertTrue(compiled["runtime_source"])
        self.assertEqual(set(compiled["bindings"]), set(ORDER))
        self.assertFalse(
            compile(
                document,
                [
                    t
                    for t in tools
                    if t["name"] != "mathformer_indexing_route_run_action"
                ],
            )[0]["runnable"]
        )

        async def authorize():
            pass

        root = mount / "repository"
        root.mkdir()
        base = {
            "match": MATCH,
            "registry": REGISTRY,
            "context": vars(hub.RunContext()),
            "repository_root": str(root),
        }

        async def run(inputs=base, changed=None):
            c, a = compile(changed) if changed else (compiled, assets)
            self.assertTrue(c["runnable"], c["diagnostics"])
            return await execute(c, a, inputs, remote, authorize)

        def report():
            return json.loads(
                (
                    root / "artifacts/mathlib_index/indexing_control_suite.json"
                ).read_text()
            )

        def records():
            p = root.with_suffix(".calls.jsonl")
            return (
                [json.loads(line) for line in p.read_text().splitlines()]
                if p.exists()
                else []
            )

        # Missing preflight and dry-run never invoke any process.
        for ready in [False, True]:
            if ready:
                populate(root, ROOT)
            for dry in [False, True] if not ready else [True]:
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["context"].update(dry_run=dry, keep_going=keep)
                    result = await run(inputs)
                    expected = await remote.call("fixture_indexing_original", inputs)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertEqual(expected["ok"], ready)
                    self.assertEqual(len(expected["children"]), 1)
                    self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
                    self.assertEqual(records(), [])
        # Run every native script on synthetic input; no theorem prover starts.
        for mode in ["success", "command_failure", "oracle_failure"]:
            for keep in [False, True]:
                clean(root)
                populate(root, ROOT, declarations=mode != "oracle_failure")
                if mode == "command_failure":
                    (root / PROFILE).unlink()
                inputs = deepcopy(base)
                inputs["context"]["keep_going"] = keep
                result = await run(inputs)
                self.assertEqual(result["status"], "accepted", result)
                actual = result["outputs"]["result"]
                actual_report = report()
                self.assertEqual(actual["ok"], mode == "success")
                self.assertEqual(
                    actual["status"],
                    (
                        "intent_run_completed"
                        if mode == "success"
                        else "intent_run_failed"
                    ),
                )
                self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    ["mathformer_indexing_route_" + o for o in ORDER],
                )
                self.assertEqual(len(actual["children"]), 1)
                child = actual["children"][0]
                self.assertEqual(child["argv"], [sys.executable, LEAF, "--json"])
                self.assertEqual(child["returncode"], 0 if mode == "success" else 1)
                self.assertTrue(child["write_audit"]["ok"], child)
                self.assertEqual(json.loads(child["stdout"]), actual_report)
                self.assertEqual(len(actual_report["results"]), 6)
                self.assertEqual(
                    len(actual_report["oracle_checks"]),
                    0 if mode == "command_failure" else 5,
                )
                self.assertEqual(
                    actual_report["summary"]["command_fail"] > 0,
                    mode == "command_failure",
                )
                self.assertEqual(
                    actual_report["summary"]["oracle_fail"] > 0,
                    mode == "oracle_failure",
                )
                self.assertEqual(
                    [r["command"] for r in actual_report["results"]],
                    [[sys.executable, *p] for p in source().COMMANDS],
                )
                self.assertEqual(
                    [r["argv"] for r in records()],
                    [[sys.executable, LEAF, "--json"]]
                    + [[sys.executable, *p] for p in source().COMMANDS],
                )
                self.assertEqual([r["timeout"] for r in records()], [480] + [240] * 6)
                self.assertTrue(all(r["cwd"] == str(root) for r in records()))
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
                clean(root)
                expected = await remote.call("fixture_indexing_original", inputs)
                self.assertEqual(stable(actual), stable(expected))
                self.assertEqual(stable(actual_report), stable(report()))
        # A source-owned report write failure propagates through main as nonzero
        # exit, then remains failed child data at the route boundary.
        clean(root)
        populate(root, ROOT)
        report_path = root / "artifacts/mathlib_index/indexing_control_suite.json"
        report_path.mkdir(parents=True)
        result = await run()
        self.assertEqual(result["status"], "accepted", result)
        child = result["outputs"]["result"]["children"][0]
        self.assertFalse(result["outputs"]["result"]["ok"])
        self.assertNotEqual(child["returncode"], 0)
        self.assertIn("IsADirectoryError", child["stderr"])
        self.assertTrue(report_path.is_dir())
        self.assertEqual(len(records()), 7)
        self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
        # Artifact oracle failure propagation, including disabled but missing cache.
        populate(root, ROOT)
        clean(root)
        self.assertTrue((await run())["outputs"]["result"]["ok"])
        artifact_dir = root / "artifacts/mathlib_index"
        native = source()
        for filename, content, error in [
            ("index.json", "{", json.JSONDecodeError),
            ("index.json", "[]", AttributeError),
            ("reranker_cache.json", None, FileNotFoundError),
        ]:
            p = artifact_dir / filename
            before = p.read_text()
            if content is None:
                p.unlink()
            else:
                p.write_text(content)
            with self.assertRaises(error):
                native.additional_oracles(root)
            p.write_text(before)
        # Forged declarations, a cursor beyond the single action, and budget exhaustion.
        for kind in ["registry", "match", "cursor"]:
            inputs = deepcopy(base)
            inputs["context"]["dry_run"] = True
            changed = None
            if kind == "registry":
                inputs["registry"][ACTION]["command"] = ["unregistered"]
            elif kind == "match":
                inputs["match"]["route"]["title"] = "forged"
            else:
                changed = deepcopy(document)
                changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                    "state"
                ] = {"literal": {"ok": True, "children": [{"ok": True}]}}
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                result["calls"][-1]["operation"],
                "run_action" if kind == "registry" else "select",
            )
        inputs = deepcopy(base)
        inputs["context"]["dry_run"] = True
        for limit in [1, 3, 4]:
            changed = deepcopy(document)
            changed["policy"]["limits"]["max_operation_calls"] = limit
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]),
                limit,
            )
        changed = deepcopy(document)
        changed["flow"]["steps"][1]["until"] = {"literal": False}
        result = await run(inputs, changed)
        self.assertEqual(result["status"], "failed", result)
        self.assertIsNone(result["outputs"])
        self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:-1])
        unknown = await remote.call(
            "mathformer_indexing_route_run_action",
            {
                "action": ACTION,
                "registry": {},
                "context": vars(hub.RunContext()),
                "repository_root": str(root),
            },
        )
        self.assertEqual(
            unknown,
            {"child": {"ok": False, "status": "unknown_action", "action_id": ACTION}},
        )
        # Optional context mount retains native default, using dry-run only.
        for omitted in [False, True]:
            values = deepcopy(inputs)
            values["repository_root"] = None
            if omitted:
                values.pop("repository_root")
            result = await run(values)
            expected = hub.run_intent_match(
                selected_match(MATCH),
                checked_registry(REGISTRY),
                hub.RunContext(dry_run=True),
            )
            self.assertEqual(result["outputs"], {"result": expected})
        # Service root enforcement is exercised through the registered tool.
        bad = deepcopy(base)
        bad["repository_root"] = str(mount.parent / "outside")
        result = await run(bad)
        self.assertEqual(result["status"], "failed", result)
        self.assertEqual(result["calls"][-1]["operation"], "run_action")
        self.assertEqual(result["calls"][-1]["status"], "rejected")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve-fixture":
        serve(sys.argv[2])
    else:
        result = unittest.main(verbosity=2, exit=False).result
        raise SystemExit(
            0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
        )
