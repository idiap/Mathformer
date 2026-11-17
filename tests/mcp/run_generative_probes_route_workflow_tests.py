#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real registered tools and Lunar PRISM compilation/runtime on synthetic inputs."""

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
import yaml

import mathformer as hub
from generative_probes_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
)
from generative_probes_tree import populate, stable, LEAF, CRITERIA, PROBES, REPORT
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_generative_probes_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 17,
    "matched_terms": ["generative", "probes"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "invoke", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/generative_probes_route_original.py.txt"
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


class GenerativeProbesTests(unittest.TestCase):
    maxDiff = None

    def test_authored_generator_policy_and_provenance(self):
        spec = importlib.util.spec_from_file_location(
            "probes_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.generative_probes_route_descriptor(), document)
        self.assertEqual(document["id"], "route_generative_probes_workflow")
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
            document["policy"]["effects"]["filesystem"]["write"],
            ["artifacts/", "artifacts/workflow_hub/"],
        )
        self.assertEqual(document["policy"]["resume"]["mode"], "none")
        self.assertEqual(set(document["operations"]), set(ORDER))
        self.assertIn(
            {"path": "scripts/mathformer.py", "selector": "run_intent_match"},
            [
                {k: v for k, v in row.items() if k != "digest"}
                for row in document["provenance"]["sources"]
            ],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        action = checked_registry(REGISTRY)[ACTION]
        self.assertEqual(action.command, ("{python}", LEAF, "--json"))
        self.assertEqual(action.timeout_seconds, 900)
        self.assertEqual(action.writes, ("artifacts/",))
        self.assertEqual(checked_registry({}), {})

    def assert_report(self, root, child, mode):
        payload = json.loads(child["stdout"])
        self.assertEqual(payload, json.loads((root / REPORT).read_text()))
        self.assertEqual(payload["mode"], "validate-only")
        self.assertEqual(payload["criteria_file"], CRITERIA)
        self.assertEqual(payload["probes_file"], PROBES)
        self.assertEqual(
            payload["probe_count"], {"valid": 1, "empty": 0, "invalid": 131}[mode]
        )
        self.assertEqual(
            payload["errors"],
            (
                [
                    "broken-first missing forbidden_claims, prompt",
                    "broken-first has no forbidden claims",
                    "broken-last has no forbidden claims",
                ]
                if mode == "invalid"
                else []
            ),
        )
        self.assertEqual(child["returncode"], 3 if mode == "invalid" else 0)
        self.assertEqual(child["argv"], [sys.executable, LEAF, "--json"])
        self.assertEqual(child["write_audit"]["unexpected_paths"], [])
        self.assertTrue(child["write_audit"]["ok"])

    def test_native_original_equivalence_and_leaf_cli_flags(self):
        oracle = original()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for mode in ["valid", "empty", "invalid"]:
                populate(root, ROOT, mode)
                for keep in [False, True]:
                    context = hub.RunContext(keep_going=keep)
                    expected = oracle.run_intent_match(
                        selected_match(MATCH),
                        checked_registry(REGISTRY),
                        context,
                        repository_root=root,
                    )
                    result = hub.run_intent_match(
                        selected_match(MATCH),
                        checked_registry(REGISTRY),
                        context,
                        repository_root=root,
                    )
                    self.assertEqual(stable(result), stable(expected))
                    self.assertEqual(len(result["children"]), 1)
                    self.assertEqual(result["ok"], mode != "invalid")
                    self.assert_report(root, result["children"][0], mode)
                # --validate-only does not change the native algorithm or status.
                before = stable(json.loads((root / REPORT).read_text()))
                result = subprocess.run(
                    [sys.executable, LEAF, "--json", "--validate-only"],
                    cwd=root,
                    text=True,
                    capture_output=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 3 if mode == "invalid" else 0)
                self.assertEqual(stable(json.loads(result.stdout)), before)
        for keep in [False, True]:
            for child in [{"ok": True}, {"ok": False}, {}]:
                state = hub.initialize_intent_state()
                updated, done = hub.advance_intent_state(
                    state, child, hub.RunContext(keep_going=keep), 1
                )
                self.assertTrue(done)
                self.assertEqual(
                    updated, {"ok": bool(child.get("ok", False)), "children": [child]}
                )
                self.assertEqual(state, {"ok": True, "children": []})
                with self.assertRaises(ValueError):
                    check_state(updated, selecting=True)
        # General native controller success is sticky after a failed child.
        updated, done = hub.advance_intent_state(
            {"ok": False, "children": [{"ok": False}]},
            {"ok": True},
            hub.RunContext(keep_going=True),
            2,
        )
        self.assertFalse(updated["ok"])
        self.assertTrue(done)

    def test_external_compiler_capture_timeout_and_exception_fixture(self):
        # This separate test action substitutes only an external compiler. The
        # selected validation leaf above and through MCP below is always real.
        saved = hub.subprocess
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                for mode in ["success", "reject", "timeout", "write", "launch_error"]:
                    item = replace(
                        hub.build_registry()[ACTION],
                        command=("fixture-reasoning-compiler", mode),
                        required_paths=(),
                    )
                    calls = install(hub, root)
                    if mode == "launch_error":
                        with self.assertRaisesRegex(OSError, "compiler launch failed"):
                            hub.run_leaf_action(
                                item, hub.RunContext(), (), repository_root=root
                            )
                    else:
                        child = hub.run_leaf_action(
                            item, hub.RunContext(), (), repository_root=root
                        )
                        self.assertEqual(child["ok"], mode == "success")
                        self.assertEqual(
                            child["status"],
                            {"timeout": "timeout", "write": "undeclared_writes"}.get(
                                mode, "completed"
                            ),
                        )
                        if mode == "timeout":
                            self.assertEqual(
                                (child["returncode"], child["stdout"], child["stderr"]),
                                (None, "partial", "deadline"),
                            )
                            self.assertEqual(child["timeout_seconds"], 900)
                        elif mode == "write":
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        else:
                            self.assertEqual(
                                child["returncode"], 7 if mode == "reject" else 0
                            )
                            self.assertEqual(
                                json.loads(child["stdout"])["artifact"]["nodes"],
                                ["input", "check"],
                            )
                    self.assertEqual(
                        calls, [{"argv": list(item.command), "timeout": 900}]
                    )
                    (root / "undeclared.txt").unlink(missing_ok=True)
        finally:
            hub.subprocess = saved

    def test_service_write_roots(self):
        # Call the actual registered functions with a temporary restrictive
        # service callback, without launching a process or reading credentials.
        from mcp.server.fastmcp import FastMCP
        from generative_probes_route_tools import register_generative_probes_route_tools

        async def scenario():
            server = FastMCP("restricted-fixture")
            register_generative_probes_route_tools(server, lambda path: False)
            with tempfile.TemporaryDirectory() as directory:
                args = {
                    "action_id": ACTION,
                    "context": vars(hub.RunContext()),
                    "registry": REGISTRY,
                    "repository_root": directory,
                }
                with self.assertRaisesRegex(
                    Exception, "outside configured service roots"
                ):
                    await server.call_tool("mathformer_generative_probes_invoke", args)
                args["context"]["dry_run"] = True
                # Missing required leaf reaches native preflight rather than policy.
                await server.call_tool("mathformer_generative_probes_invoke", args)

        asyncio.run(scenario())

    def test_registered_mcp_and_real_lunar_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "generative-probes",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
        ) as remote:
            await self.connected(remote)
        self.assertFalse(manager.active)

    async def connected(self, remote):
        document = yaml.safe_load(CONTRACT.read_text())
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(doc):
            assets = snapshot(doc)
            workflow = workflow_documents([DESCRIPTOR], assets)[0]
            self.assertTrue(workflow["validation"]["valid"], workflow)
            compiled = compile_workflow("mcp:generative-probes", workflow, tools)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertEqual(compiled["runtime_status"], "ready")
            self.assertTrue(compiled["prism_source"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(ORDER))
            return compiled, assets

        compiled, assets = compile(document)
        rejected = compile_workflow(
            "mcp:generative-probes",
            workflow_documents([DESCRIPTOR], assets)[0],
            [t for t in tools if t["name"] != "mathformer_generative_probes_invoke"],
        )
        self.assertFalse(rejected["runnable"])

        async def authorize():
            pass

        async def run(inputs, changed=None):
            workflow, values = compile(changed) if changed else (compiled, assets)
            return await execute(workflow, values, inputs, remote, authorize)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            base = {
                "context": vars(hub.RunContext()),
                "match": MATCH,
                "registry": REGISTRY,
                "repository_root": str(root),
            }
            # Missing leaf is native preflight failure. Successful dry-run never
            # reads probes, launches the validator or writes a report.
            for ready in [False, True]:
                if ready:
                    populate(root, ROOT)
                for keep in [False, True]:
                    for dry in [False, True]:
                        inputs = deepcopy(base)
                        inputs["context"].update(keep_going=keep, dry_run=dry)
                        before = hub.snapshot_repository(root)
                        result = await run(inputs)
                        self.assertEqual(result["status"], "accepted", result)
                        actual = result["outputs"]["result"]
                        if not ready or dry:
                            self.assertEqual(hub.snapshot_repository(root), before)
                            self.assertNotIn("returncode", actual["children"][0])
                        else:
                            self.assert_report(root, actual["children"][0], "valid")
                        expected = original().run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            hub.RunContext(**inputs["context"]),
                            repository_root=root,
                        )
                        self.assertEqual(stable(actual), stable(expected))
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], ORDER
                        )
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            ["mathformer_generative_probes_" + op for op in ORDER],
                        )
                        self.assertEqual(len(actual["children"]), 1)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
            for mode in ["empty", "invalid", "malformed"]:
                populate(root, ROOT, mode)
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["context"]["keep_going"] = keep
                    result = await run(inputs)
                    self.assertEqual(result["status"], "accepted", result)
                    actual = result["outputs"]["result"]
                    self.assertEqual(len(actual["children"]), 1)
                    self.assertEqual(actual["ok"], mode == "empty")
                    self.assertEqual(
                        actual["status"],
                        (
                            "intent_run_completed"
                            if mode == "empty"
                            else "intent_run_failed"
                        ),
                    )
                    self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
                    if mode != "malformed":
                        self.assert_report(root, actual["children"][0], mode)
                    else:
                        self.assertEqual(actual["children"][0]["returncode"], 1)
                        self.assertIn(
                            "JSONDecodeError", actual["children"][0]["stderr"]
                        )
            # Unexpected launch-adjacent failure (missing interpreter script is
            # captured by Python above); native metadata errors propagate here.
            inputs = deepcopy(base)
            inputs["registry"] = {}
            result = await run(inputs)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(result["calls"][-1]["operation"], "finish")
            unknown = await remote.call(
                "mathformer_generative_probes_invoke",
                {
                    "action_id": ACTION,
                    "registry": {},
                    "context": vars(hub.RunContext()),
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
            for forged in ["registry", "match", "cursor"]:
                test, changed = deepcopy(inputs), None
                if forged == "registry":
                    test["registry"][ACTION]["command"] = ["forged-command"]
                elif forged == "match":
                    test["match"]["route"]["title"] = "forged title"
                else:
                    changed = deepcopy(document)
                    changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                        "state"
                    ] = {"literal": {"ok": True, "children": [{"ok": True}]}}
                result = await run(test, changed)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
            for limit in [1, 3, 4]:
                changed = deepcopy(document)
                changed["policy"]["limits"]["max_operation_calls"] = limit
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed", result)
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
            # Optional filesystem context preserves native default, dry-run only.
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
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
