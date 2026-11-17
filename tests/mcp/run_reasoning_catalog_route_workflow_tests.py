#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Selected source, real MCP bindings and real Lunar/PRISM compilation/runtime.

All renderer executions use synthetic temporary repositories. Only a separate
external compiler boundary is substituted; no live provider or prover is used.
"""

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
from reasoning_catalog_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
)
from reasoning_catalog_tree import populate, put, LEAF, SEMANTIC, MATERIAL, NAMES
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_docs_reasoning_flow_catalog_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 23,
    "matched_terms": ["reasoning", "catalogue"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "dispatch", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/reasoning_catalog_route_original.py.txt"
        ).read_text(),
        scope,
    )
    return SimpleNamespace(**scope)


def snapshot(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    values[DESCRIPTOR] = json.dumps(document)
    return [
        {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }
        for path, content in values.items()
    ]


def stale(root):
    for relative in [SEMANTIC, MATERIAL]:
        put(root, relative, "old fixture document\n")


def assert_documents(test, root, child):
    payload = json.loads(child["stdout"])
    test.assertEqual(payload["action"], "rendered")
    test.assertTrue(payload["ok"])
    test.assertEqual(payload["profile_ids"], list(NAMES))
    test.assertEqual(payload["profile_count"], 2)
    test.assertEqual(payload["loop_contract_ids"], ["fixture_operational_loop"])
    for path, digest in [(SEMANTIC, "sha256"), (MATERIAL, "materializations_sha256")]:
        test.assertEqual(
            payload[digest], hashlib.sha256((root / path).read_bytes()).hexdigest()
        )
    semantic = (root / SEMANTIC).read_text()
    material = (root / MATERIAL).read_text()
    test.assertLess(
        semantic.index("## fixture_beta"), semantic.index("## fixture_alpha")
    )
    for forbidden in [
        "fixture-control-skill",
        "fixture_operational_loop",
        "fixture:catalogue",
    ]:
        test.assertNotIn(forbidden, semantic)
    test.assertIn("fixture-control-skill", material)
    test.assertIn("fixture_operational_loop", material)
    test.assertEqual(child["write_audit"]["unexpected_paths"], [])
    test.assertTrue(child["write_audit"]["ok"])


class ReasoningCatalogTests(unittest.TestCase):
    maxDiff = None

    def test_generator_bindings_policy_and_source_provenance(self):
        spec = importlib.util.spec_from_file_location(
            "catalogue_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.reasoning_catalog_route_descriptor(), document)
        self.assertEqual(document["id"], "route_docs_reasoning_flow_catalog_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            document["policy"]["effects"],
            {
                "filesystem": {
                    "read": ["repository", "native_runtime_inputs"],
                    "write": ["artifacts/workflow_hub/", SEMANTIC, MATERIAL],
                },
                "network": [],
                "external_write": [],
            },
        )
        self.assertEqual(
            document["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertEqual(set(document["operations"]), set(ORDER))
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
        item = checked_registry(REGISTRY)[ACTION]
        self.assertEqual(item.command, ("{python}", LEAF, "--json"))
        self.assertEqual(item.safety, "writes_repo")
        self.assertEqual(item.writes, (SEMANTIC, MATERIAL))
        self.assertIsNone(item.timeout_seconds)
        self.assertFalse(item.depends_on)
        self.assertEqual(checked_registry({}), {})

    def test_original_entrypoint_equivalence_and_exact_single_action_stop(self):
        oracle = original()
        native, match = checked_registry(REGISTRY), selected_match(MATCH)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for ready in [False, True]:
                if ready:
                    populate(root, ROOT)
                for dry in [False, True]:
                    for allow in [False, True]:
                        for keep in [False, True]:
                            context = hub.RunContext(
                                dry_run=dry, allow_mutating=allow, keep_going=keep
                            )
                            results = []
                            for source in [oracle, hub]:
                                if ready:
                                    stale(root)
                                results.append(
                                    source.run_intent_match(
                                        match, native, context, repository_root=root
                                    )
                                )
                            self.assertEqual(*results)
                            actual = results[0]
                            self.assertEqual(len(actual["children"]), 1)
                            self.assertEqual(actual["ok"], ready and (dry or allow))
                            if ready and not dry and allow:
                                assert_documents(self, root, actual["children"][0])
                self.assertFalse((root / "artifacts").exists())
        for keep in [False, True]:
            for child in [{"ok": True}, {"ok": False}, {}]:
                state = hub.initialize_intent_state()
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
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            check_state({"ok": False, "children": []})

    def test_deterministic_external_compiler_capture_and_failure_fixture(self):
        # This separate test action covers the source subprocess boundary, not
        # a substitute for the actual registered catalogue renderer.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            saved = hub.subprocess
            try:
                for mode in ["success", "reject", "write", "launch_error", "timeout"]:
                    item = replace(
                        hub.build_registry()[ACTION],
                        command=("fixture-reasoning-compiler", mode),
                        required_paths=(),
                        timeout_seconds=3 if mode == "timeout" else None,
                    )
                    calls = install(hub, root)
                    if mode == "launch_error":
                        with self.assertRaisesRegex(OSError, "compiler launch failed"):
                            hub.run_leaf_action(
                                item,
                                hub.RunContext(allow_mutating=True),
                                (),
                                repository_root=root,
                            )
                    else:
                        child = hub.run_leaf_action(
                            item,
                            hub.RunContext(allow_mutating=True),
                            (),
                            repository_root=root,
                        )
                        self.assertEqual(child["ok"], mode == "success")
                        self.assertEqual(
                            child["status"],
                            {"write": "undeclared_writes", "timeout": "timeout"}.get(
                                mode, "completed"
                            ),
                        )
                        if mode == "success":
                            self.assertFalse(
                                json.loads(child["stdout"])["ok"]
                            )  # exit code owns native success
                        elif mode == "reject":
                            self.assertEqual(child["returncode"], 7)
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

    def test_registered_mcp_lunar_prism_runtime_and_failure_paths(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        failure = None
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "reasoning-catalogue",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
        ) as remote:
            try:
                await self.connected_scenario(remote)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure

    async def connected_scenario(self, remote):
        document = yaml.safe_load(CONTRACT.read_text())
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(doc):
            assets = snapshot(doc)
            documents = workflow_documents([DESCRIPTOR], assets)
            self.assertTrue(documents[0]["validation"]["valid"], documents[0])
            compiled = compile_workflow("mcp:reasoning-catalogue", documents[0], tools)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertEqual(compiled["runtime_status"], "ready")
            self.assertTrue(compiled["prism_source"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(ORDER))
            return compiled, assets

        compiled, assets = compile(document)
        missing = [
            t for t in tools if t["name"] != "mathformer_reasoning_catalog_dispatch"
        ]
        rejected = compile_workflow(
            "mcp:reasoning-catalogue",
            workflow_documents([DESCRIPTOR], assets)[0],
            missing,
        )
        self.assertFalse(rejected["runnable"])
        self.assertTrue(rejected["diagnostics"])

        async def authorize():
            pass

        async def run(inputs, changed=None):
            workflow, received = compile(changed) if changed else (compiled, assets)
            return await execute(workflow, received, inputs, remote, authorize)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            base = {
                "context": vars(hub.RunContext(allow_mutating=True)),
                "match": MATCH,
                "registry": REGISTRY,
                "repository_root": str(root),
            }
            for ready in [False, True]:
                if ready:
                    populate(root, ROOT)
                for dry in [False, True]:
                    for allow in [False, True]:
                        for keep in [False, True]:
                            inputs = deepcopy(base)
                            inputs["context"].update(
                                dry_run=dry, allow_mutating=allow, keep_going=keep
                            )
                            if ready:
                                stale(root)
                            before = hub.snapshot_repository(root)
                            result = await run(inputs)
                            if not (ready and not dry and allow):
                                self.assertEqual(hub.snapshot_repository(root), before)
                            if ready:
                                stale(root)
                            expected = original().run_intent_match(
                                selected_match(MATCH),
                                checked_registry(REGISTRY),
                                hub.RunContext(**inputs["context"]),
                                repository_root=root,
                            )
                            self.assertEqual(result["status"], "accepted", result)
                            self.assertEqual(result["outputs"], {"result": expected})
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]], ORDER
                            )
                            self.assertEqual(
                                [c["tool"] for c in result["calls"]],
                                ["mathformer_reasoning_catalog_" + op for op in ORDER],
                            )
                            self.assertEqual(len(expected["children"]), 1)
                            self.assertEqual(expected["ok"], ready and (dry or allow))
                            self.assertEqual(expected["route"]["score"], MATCH["score"])
                            self.assertEqual(
                                expected["route"]["matched_terms"],
                                MATCH["matched_terms"],
                            )
                            child = expected["children"][0]
                            if ready and not dry and allow:
                                self.assertEqual(child["returncode"], 0)
                                self.assertEqual(
                                    child["argv"], [sys.executable, LEAF, "--json"]
                                )
                                assert_documents(self, root, child)
                            else:
                                self.assertNotIn("returncode", child)
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
            # Strict validation rejects unresolved profile gaps. Both keep-going
            # choices still terminate at exactly one dispatch, with no retry.
            profile = root / f"examples/reasoning_flows/{NAMES[0]}.rflow"
            valid_profile = profile.read_text()
            profile.write_text(
                valid_profile.replace("a:A[gap::Context->candidate::Claim]", "_")
            )
            for keep in [False, True]:
                inputs = deepcopy(base)
                inputs["context"]["keep_going"] = keep
                stale(root)
                result = await run(inputs)
                self.assertEqual(result["status"], "accepted", result)
                output = result["outputs"]["result"]
                self.assertFalse(output["ok"])
                self.assertEqual(output["status"], "intent_run_failed")
                self.assertEqual(len(output["children"]), 1)
                child = output["children"][0]
                self.assertEqual(child["returncode"], 1)
                self.assertFalse(json.loads(child["stdout"])["ok"])
                self.assertTrue(child["write_audit"]["ok"])
                self.assertEqual(
                    (root / SEMANTIC).read_text(), "old fixture document\n"
                )
                self.assertEqual(
                    (root / MATERIAL).read_text(), "old fixture document\n"
                )
                self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
            profile.write_text(valid_profile)
            # The actual second write fails: first output survives unchanged;
            # native captured stdout and audit reach finish as failure data.
            (root / MATERIAL).unlink()
            (root / MATERIAL).mkdir()
            result = await run(base)
            self.assertEqual(result["status"], "accepted", result)
            output = result["outputs"]["result"]
            self.assertFalse(output["ok"])
            child = output["children"][0]
            self.assertEqual(child["returncode"], 1)
            payload = json.loads(child["stdout"])
            self.assertEqual(payload["action"], "rendered")
            self.assertIn("error", payload)
            self.assertTrue((root / SEMANTIC).read_text().startswith("<!--"))
            self.assertTrue((root / MATERIAL).is_dir())
            self.assertTrue(child["write_audit"]["ok"])
            self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
            (root / MATERIAL).rmdir()
            for forged in ["registry", "match", "cursor"]:
                inputs, changed = deepcopy(base), None
                inputs["context"]["dry_run"] = True
                if forged == "registry":
                    inputs["registry"][ACTION]["command"] = ["forged-command"]
                elif forged == "match":
                    inputs["match"]["route"]["title"] = "forged title"
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
                    "dispatch" if forged == "registry" else "select",
                )
            unknown = await remote.call(
                "mathformer_reasoning_catalog_dispatch",
                {
                    "action": ACTION,
                    "context": vars(hub.RunContext(dry_run=True)),
                    "registry": {},
                    "repository_root": str(root),
                },
            )
            self.assertEqual(
                unknown,
                {
                    "child": {
                        "ok": False,
                        "status": "unknown_action",
                        "action_id": ACTION,
                    }
                },
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
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    limit,
                )
            changed = deepcopy(document)
            changed["flow"]["steps"][1]["until"] = {"literal": False}
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:-1])
            # The real project may only be reached in dry-run mode in this suite.
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
                            hub.RunContext(dry_run=True, allow_mutating=True),
                        )
                    },
                )


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
