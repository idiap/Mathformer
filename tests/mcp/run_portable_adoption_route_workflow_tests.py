#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline native, registered MCP and real Lunar/PRISM integration tests."""

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
import tempfile
from types import SimpleNamespace
import unittest
import yaml
import mathformer as hub
from portable_adoption_route_tools import (
    ACTION,
    ROUTE,
    DEPENDENCIES,
    selected_match,
    checked_registry,
    check_dependencies,
)
from portable_adoption_route_tree import populate, DIRECTORY, CATALOG
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_repository_portable_adoption_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
DOCUMENT = yaml.safe_load(CONTRACT.read_text())
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 23,
    "matched_terms": ["portable", "adoption"],
}
REGISTRY = {
    key: hub.action_to_dict(hub.build_registry()[key])
    for key in (ACTION, *DEPENDENCIES)
}


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/portable_adoption_route_original.py.txt"
        ).read_text(),
        scope,
    )
    return SimpleNamespace(**scope)


def snapshot(document):
    values = {
        s["path"]: (ROOT / s["path"]).read_text()
        for s in document["provenance"]["sources"]
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


def outcomes(result):
    # Native unittest diagnostics include timing; all decision, argv, capture,
    # ordering and audit fields are preserved, with only that timing removed.
    import re

    return json.loads(
        re.sub(
            r"Ran (\d+) tests in [0-9.]+s",
            r"Ran \1 tests in <clock>s",
            json.dumps(result),
        )
    )


class PortableRouteTests(unittest.TestCase):
    maxDiff = None

    def test_generator_identity_policy_and_provenance(self):
        spec = importlib.util.spec_from_file_location(
            "portable_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.portable_adoption_route_descriptor(), DOCUMENT)
        self.assertEqual(DOCUMENT["id"], "route_repository_portable_adoption_workflow")
        self.assertEqual(DOCUMENT["aliases"], [ROUTE])
        self.assertEqual(DOCUMENT["lifecycle"], "active")
        self.assertEqual(
            DOCUMENT["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 14},
        )
        self.assertEqual(
            DOCUMENT["policy"]["failure"]["retry"],
            {"max_attempts": 1, "retryable_codes": []},
        )
        self.assertEqual(
            DOCUMENT["policy"]["effects"],
            {
                "filesystem": {
                    "read": ["repository", "native_runtime_inputs"],
                    "write": ["artifacts/workflow_hub/"],
                },
                "network": [],
                "external_write": [],
            },
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
            DOCUMENT["provenance"]["sources"],
        )
        for row in DOCUMENT["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        native = checked_registry(REGISTRY)
        self.assertFalse(native[ACTION].command)
        self.assertEqual(native[ACTION].depends_on, DEPENDENCIES)
        self.assertTrue(all(native[k].timeout_seconds is None for k in DEPENDENCIES))
        self.assertEqual(selected_match(MATCH).route.action_ids, (ACTION,))
        self.assertEqual(checked_registry({}), {})
        for field in ["command", "depends_on", "writes"]:
            forged = deepcopy(REGISTRY)
            forged[ACTION][field] = ["forged"]
            with self.assertRaisesRegex(ValueError, "projection"):
                checked_registry(forged)

    def test_native_admission_history_and_bounds(self):
        native = checked_registry(REGISTRY)
        item = native[ACTION]
        for args, seen, status in [
            ((), None, "accepted"),
            (("extra",), None, "extra_args_for_sequence"),
            ((), {ACTION}, "dependency_cycle"),
        ]:
            admission = hub.admit_action(ACTION, native, args, seen)
            self.assertEqual(admission["status"], status)
            if status != "accepted":
                self.assertFalse(hub.reject_action(ACTION, admission)["ok"])
        self.assertEqual(
            hub.admit_action(ACTION, {}, (), {ACTION})["status"], "unknown_action"
        )
        for keep in [False, True]:
            state = hub.initialize_dependencies(hub.admit_action(ACTION, native))
            for i in range(4):
                previous = deepcopy(state)
                state, done = hub.advance_dependencies(
                    item,
                    state,
                    {"ok": i != 0, "ordinal": i},
                    hub.RunContext(keep_going=keep),
                )
                self.assertEqual(previous["index"], i)
                self.assertEqual(state["index"], i + 1)
                self.assertEqual(
                    [c["ordinal"] for c in state["children"]], list(range(i + 1))
                )
                self.assertFalse(state["dependencies_ok"])
                self.assertEqual(done, i == 3 or (i == 0 and not keep))
                check_dependencies(state)
            with self.assertRaisesRegex(ValueError, "out of bounds"):
                check_dependencies(state, visiting=True)
            with self.assertRaisesRegex(ValueError, "accumulator"):
                check_dependencies({**state, "dependencies_ok": True})
            self.assertEqual(
                hub.finish_dependencies(item, state)["status"], "sequence_failed"
            )
            self.assertFalse(
                hub.dependency_command_guard(
                    item, state, hub.RunContext(keep_going=keep)
                )
            )
            route, done = hub.advance_intent_state(
                hub.initialize_intent_state(),
                {"ok": False},
                hub.RunContext(keep_going=keep),
                1,
            )
            self.assertTrue(done)
            self.assertFalse(route["ok"])

    def test_deterministic_external_compiler_boundary(self):
        # This workflow has no provider/compiler boundary. A separate compiler
        # fixture exercises the shared process runner, never replaces local gates.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            saved = hub.subprocess
            try:
                for mode in ["success", "reject", "write", "launch_error", "timeout"]:
                    (root / "undeclared.txt").unlink(missing_ok=True)
                    leaf = replace(
                        hub.build_registry()[DEPENDENCIES[0]],
                        command=("fixture-reasoning-compiler", mode),
                        required_paths=(),
                        timeout_seconds=3 if mode == "timeout" else None,
                    )
                    calls = install(hub, root)
                    if mode == "launch_error":
                        with self.assertRaisesRegex(OSError, "launch failed"):
                            hub.run_action(
                                leaf.action_id,
                                {leaf.action_id: leaf},
                                hub.RunContext(),
                                repository_root=root,
                            )
                    else:
                        result = hub.run_action(
                            leaf.action_id,
                            {leaf.action_id: leaf},
                            hub.RunContext(),
                            repository_root=root,
                        )
                        self.assertEqual(result["ok"], mode == "success")
                        self.assertEqual(
                            result["status"],
                            {"timeout": "timeout", "write": "undeclared_writes"}.get(
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
                        else:
                            self.assertEqual(
                                json.loads(result["stdout"])["artifact"]["nodes"],
                                ["input", "check"],
                            )
                            self.assertEqual(
                                result["returncode"], 7 if mode == "reject" else 0
                            )
                        if mode == "write":
                            self.assertEqual(
                                result["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                    self.assertEqual(
                        calls,
                        [{"argv": list(leaf.command), "timeout": leaf.timeout_seconds}],
                    )
            finally:
                hub.subprocess = saved

    def test_registered_mcp_real_lunar_compile_runtime_and_native_parity(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        error = None
        code = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "portable-route",
            StdioConfig(command=sys.executable, args=["-c", code], cwd=str(ROOT)),
            {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
        ) as remote:
            try:
                await self.connected(remote)
            except Exception as exc:
                error = exc
        self.assertFalse(manager.active)
        if error:
            raise error

    async def connected(self, remote):
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile_document(document, advertised=tools):
            assets = snapshot(document)
            docs = workflow_documents([DESCRIPTOR], assets)
            self.assertEqual(len(docs), 1)
            self.assertTrue(docs[0]["validation"]["valid"], docs[0])
            compiled = compile_workflow("mcp:portable-route", docs[0], advertised)
            return compiled, assets

        compiled, assets = compile_document(DOCUMENT)
        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
        self.assertEqual(compiled["runtime_status"], "ready")
        self.assertTrue(compiled["prism_source"])
        self.assertTrue(compiled["runtime_source"])
        self.assertEqual(set(compiled["bindings"]), set(DOCUMENT["operations"]))
        for name in DOCUMENT["operations"]:
            target = "mathformer_portable_route_" + name
            self.assertIn(target, [t["name"] for t in tools])
            unavailable, _ = compile_document(
                DOCUMENT, [t for t in tools if t["name"] != target]
            )
            self.assertFalse(unavailable["runnable"])

        async def authorize():
            pass

        async def run(inputs, changed=None):
            c, a = compile_document(changed) if changed else (compiled, assets)
            self.assertTrue(c["runnable"], c["diagnostics"])
            return await execute(c, a, inputs, remote, authorize)

        def call_order(n):
            return (
                ["initialize_route", "select_and_admit", "initialize_dependencies"]
                + ["visit_leaf", "advance_dependencies"] * n
                + ["finish_dependencies", "advance_route", "finish_route"]
            )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            base = {
                "context": vars(hub.RunContext()),
                "match": MATCH,
                "registry": REGISTRY,
                "repository_root": str(root),
            }
            for ready in [False, True]:
                if ready:
                    populate(root, ROOT)
                for dry in [False, True]:
                    for keep in [False, True]:
                        inputs = deepcopy(base)
                        inputs["context"].update(dry_run=dry, keep_going=keep)
                        before = hub.snapshot_repository(root)
                        result = await run(inputs)
                        expected = original().run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            hub.RunContext(**inputs["context"]),
                            repository_root=root,
                        )
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            outcomes(result["outputs"]), outcomes({"result": expected})
                        )
                        actual = result["outputs"]["result"]
                        parent = actual["children"][0]
                        children = parent["children"]
                        count = 4 if keep or (ready and dry) else 3 if ready else 1
                        self.assertEqual(len(actual["children"]), 1)
                        self.assertEqual(len(children), count)
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], call_order(count)
                        )
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            [
                                "mathformer_portable_route_" + op
                                for op in call_order(count)
                            ],
                        )
                        self.assertEqual(actual["ok"], ready and dry)
                        self.assertEqual(parent["ok"], ready and dry)
                        self.assertEqual(
                            [c["action"]["id"] for c in children],
                            list(DEPENDENCIES[:count]),
                        )
                        self.assertEqual(actual["route"]["score"], MATCH["score"])
                        self.assertEqual(
                            actual["route"]["matched_terms"], MATCH["matched_terms"]
                        )
                        self.assertEqual(hub.snapshot_repository(root), before)
                        for child in children:
                            self.assertEqual(
                                child["argv"],
                                hub.resolve_command(
                                    checked_registry(REGISTRY)[
                                        child["action"]["id"]
                                    ].command
                                ),
                            )
                            if dry and (
                                ready or child["action"]["id"] != DEPENDENCIES[0]
                            ):
                                self.assertEqual(child["status"], "dry_run")
                                self.assertNotIn("returncode", child)
                            elif not child["preflight_errors"]:
                                self.assertTrue(child["write_audit"]["ok"])
                        if ready and not dry:
                            self.assertTrue(children[0]["ok"])
                            self.assertTrue(children[1]["ok"])
                            self.assertEqual(
                                json.loads(children[0]["stdout"]),
                                {"ok": True, "surface_count": 4, "operation_count": 8},
                            )
                            self.assertTrue(
                                json.loads(children[1]["stdout"])["checked"]
                            )
                            self.assertEqual(children[2]["returncode"], 2)
                            if keep:
                                self.assertTrue(
                                    children[3]["ok"]
                                )  # failure remains sticky
                                self.assertIn("OK", children[3]["stderr"])
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
            # Real catalog drift stops after the second launch, or continues to
            # all four checks; no regeneration or repair is authorized.
            (root / CATALOG).write_text("stale\n")
            for keep in [False, True]:
                inputs = deepcopy(base)
                inputs["context"]["keep_going"] = keep
                result = await run(inputs)
                children = result["outputs"]["result"]["children"][0]["children"]
                self.assertEqual(len(children), 4 if keep else 2)
                self.assertEqual(
                    json.loads(children[1]["stdout"]),
                    {"ok": False, "error": "generated pilot catalog is stale"},
                )
                self.assertEqual(children[1]["returncode"], 2)
                self.assertFalse(result["outputs"]["result"]["ok"])
                self.assertEqual((root / CATALOG).read_text(), "stale\n")
            # Invalid real authored metadata fails in the first native leaf.
            (root / DIRECTORY / "references/portable-adoption.json").write_text("{}")
            result = await run(base)
            children = result["outputs"]["result"]["children"][0]["children"]
            self.assertEqual(len(children), 1)
            self.assertEqual(children[0]["returncode"], 2)
            self.assertFalse(json.loads(children[0]["stdout"])["ok"])
            inputs = deepcopy(base)
            inputs["context"]["dry_run"] = True
            # Missing leaf remains result data consumed by both accumulators.
            del inputs["registry"][DEPENDENCIES[1]]
            result = await run(inputs)
            children = result["outputs"]["result"]["children"][0]["children"]
            self.assertEqual(len(children), 2)
            self.assertEqual(children[1]["status"], "unknown_action")
            # Parent rejection proceeds through the original route accumulator,
            # then preserves native missing metadata KeyError at route finish.
            inputs["registry"] = {}
            with self.assertRaises(KeyError):
                original().run_intent_match(
                    selected_match(MATCH),
                    {},
                    hub.RunContext(dry_run=True),
                    repository_root=root,
                )
            result = await run(inputs)
            self.assertEqual(result["status"], "failed")
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                [c["operation"] for c in result["calls"]],
                [
                    "initialize_route",
                    "select_and_admit",
                    "reject",
                    "retain_rejection",
                    "finish_dependencies",
                    "advance_route",
                    "finish_route",
                ],
            )
            for status in [
                "unknown_action",
                "dependency_cycle",
                "extra_args_for_sequence",
            ]:
                rejection = await remote.call(
                    "mathformer_portable_route_reject",
                    {
                        "admission": {
                            "action_id": ACTION,
                            "accepted": False,
                            "status": status,
                            "ancestry": [ACTION],
                        }
                    },
                )
                expected_rejection = hub.reject_action(
                    ACTION, {"status": status, "ancestry": [ACTION]}
                )
                self.assertEqual(
                    rejection,
                    {
                        "result": expected_rejection,
                        "state": {
                            "accepted": False,
                            "dependencies": None,
                            "rejection": expected_rejection,
                        },
                    },
                )
            inputs = deepcopy(base)
            inputs["context"]["dry_run"] = True
            for kind in ["registry", "route", "cursor"]:
                forged = deepcopy(inputs)
                changed = None
                if kind == "registry":
                    forged["registry"][DEPENDENCIES[0]]["command"] = ["forged"]
                elif kind == "route":
                    forged["match"]["route"]["title"] = "forged"
                else:
                    changed = deepcopy(DOCUMENT)
                    visit = changed["flow"]["steps"][1]["body"]["steps"][2]["body"][
                        "cases"
                    ][0]["body"]["steps"][0]
                    visit["arguments"]["state"] = {
                        "literal": {
                            "accepted": True,
                            "dependencies": {
                                "index": 4,
                                "children": [],
                                "dependencies_ok": True,
                                "ancestry": [ACTION],
                            },
                            "rejection": None,
                        }
                    }
                result = await run(forged, changed)
                self.assertEqual(result["status"], "failed")
                self.assertIsNone(result["outputs"])
            # Exact native bound is normal completion; a shortened bound or
            # falsified exit predicate fails without producing partial success.
            changed = deepcopy(DOCUMENT)
            changed["flow"]["steps"][1]["body"]["steps"][2]["max_iterations"] = 3
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed")
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                sum(c["operation"] == "visit_leaf" for c in result["calls"]), 3
            )
            changed = deepcopy(DOCUMENT)
            changed["flow"]["steps"][1]["until"] = {"literal": False}
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed")
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                [c["operation"] for c in result["calls"]], call_order(4)[:-1]
            )
            for cap in [1, 13]:
                changed = deepcopy(DOCUMENT)
                changed["policy"]["limits"]["max_operation_calls"] = cap
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed")
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    cap,
                )
            # Native default mount is inspected through dry-run only.
            for omitted in [False, True]:
                inputs["repository_root"] = None
                if omitted:
                    inputs.pop("repository_root")
                result = await run(inputs)
                self.assertEqual(
                    result["outputs"],
                    {
                        "result": hub.run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            hub.RunContext(dry_run=True),
                        )
                    },
                )


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
