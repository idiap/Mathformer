#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline real plugin commands, registered MCP tools, Lunar and PRISM runtime.

The selected route has no provider/compiler. Only a separate external compiler
boundary is substituted to qualify shared process failure and audit behavior.
The actual plugin check and entire unit suite run in synthetic repositories.
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
os.environ.update(
    PYTHONDONTWRITEBYTECODE="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1"
)
FIXTURES = ROOT / "tests/mcp/fixtures"
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(FIXTURES),
    *SITES,
]

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import re
import tempfile
from types import SimpleNamespace
import unittest
import yaml

import mathformer as hub
from skills_plugin_check_route_tools import (
    ACTIONS,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
)
from skills_plugin_check_repository import DESCRIPTOR, SCHEMA, populate
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
AUTHORED = "skills/control/workflow-contract-validator/references/skills-plugin-check-route.workflow.json"
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": list(ACTIONS)},
    "score": 31,
    "matched_terms": ["validate agent plugins"],
}
REGISTRY = {key: hub.action_to_dict(hub.build_registry()[key]) for key in ACTIONS}
ORDER = [
    "initialize",
    "select",
    "dispatch",
    "advance",
    "select",
    "dispatch",
    "advance",
    "finish",
]
PREFIX = "mathformer_skills_plugin_check_route_"


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "skills_plugin_check_route_original.py.txt").read_text(), scope)
    return SimpleNamespace(**scope)


def snapshot(document):
    paths = {SCHEMA} | {row["path"] for row in document["provenance"]["sources"]}
    values = {p: (ROOT / p).read_text() for p in paths}
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


def stable(value):
    """Ignore elapsed time and macOS sandbox diagnostics during oracle comparison.

    The unmodified stderr remains in the actual native result. Apple's Git
    emits this host diagnostic only in the sandboxed MCP child environment.
    """
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [stable(v) for v in value]
    if isinstance(value, str):
        value = value.replace(
            "git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead\n",
            "",
        )
        return re.sub(r"(Ran \d+ tests in )\d+\.\d+s", r"\1<TIME>s", value)
    return value


class SkillsPluginCheckTests(unittest.TestCase):
    maxDiff = None

    def test_generator_bindings_provenance_and_registry(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        spec = importlib.util.spec_from_file_location(
            "plugin_check_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(generator.skills_plugin_check_route_descriptor(), doc)
        self.assertEqual(json.loads((ROOT / AUTHORED).read_text()), doc)
        self.assertEqual(doc["id"], "route_skills_plugin_check_workflow")
        self.assertEqual(doc["aliases"], [ROUTE])
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 8},
        )
        self.assertEqual(
            doc["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertEqual(doc["flow"]["steps"][1]["max_iterations"], 2)
        self.assertTrue(
            any(
                s["path"] == "scripts/mathformer.py"
                and s["selector"] == "run_intent_match"
                for s in doc["provenance"]["sources"]
            )
        )
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        for key, op in doc["operations"].items():
            self.assertEqual(op["execution"]["binding"]["target"], PREFIX + key)
        self.assertEqual(selected_match(MATCH).route.action_ids, ACTIONS)
        self.assertEqual(checked_registry({}), {})
        for timeout in [None, 1, 600]:
            wire = deepcopy(REGISTRY)
            for row in wire.values():
                row["timeout_seconds"] = timeout
            self.assertTrue(
                all(
                    a.timeout_seconds == timeout
                    for a in checked_registry(wire).values()
                )
            )
        for field, value in [
            ("command", ["arbitrary-code"]),
            ("writes", ["elsewhere"]),
            ("timeout_seconds", True),
            ("timeout_seconds", 0),
        ]:
            wire = deepcopy(REGISTRY)
            wire[ACTIONS[0]][field] = value
            with self.assertRaises(ValueError):
                checked_registry(wire)

    def test_native_state_order_sticky_failure_and_bound(self):
        for keep in [False, True]:
            for first_ok in [False, True]:
                for second_ok in [False, True]:
                    state = hub.initialize_intent_state()
                    previous = deepcopy(state)
                    for index, ok in enumerate([first_ok, second_ok]):
                        self.assertEqual(
                            hub.select_intent_action(state, selected_match(MATCH)),
                            ACTIONS[index],
                        )
                        child = {"ok": ok, "stdout": str(index)}
                        old = deepcopy(state)
                        state, done = hub.advance_intent_state(
                            state, child, hub.RunContext(keep_going=keep), 2
                        )
                        self.assertEqual(state["children"], [*old["children"], child])
                        self.assertEqual(state["ok"], old["ok"] and ok)
                        self.assertEqual(done, index == 1 or (not ok and not keep))
                        check_state(state)
                        if done:
                            break
                    self.assertEqual(previous, {"ok": True, "children": []})
                    self.assertEqual(
                        len(state["children"]), 1 if not first_ok and not keep else 2
                    )
                    result = hub.finish_intent_state(
                        state, selected_match(MATCH), checked_registry(REGISTRY)
                    )
                    self.assertEqual(
                        result["status"],
                        "intent_run_completed" if state["ok"] else "intent_run_failed",
                    )
        for state in [
            {"ok": True, "children": [{}, {}]},
            {"ok": True, "children": [{"ok": False}]},
        ]:
            with self.assertRaises(ValueError):
                check_state(state, selecting=True)

    def test_external_compiler_boundary_capture_audit_and_exceptions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for mode in ["success", "reject", "write", "timeout", "launch_error"]:
                old = hub.subprocess
                compiler = replace(
                    hub.build_registry()[ACTIONS[0]],
                    command=("fixture-reasoning-compiler", mode),
                    required_paths=(),
                    timeout_seconds=3 if mode == "timeout" else None,
                )
                try:
                    calls = install(hub, root)
                    if mode == "launch_error":
                        with self.assertRaisesRegex(OSError, "compiler launch failed"):
                            hub.run_action(
                                ACTIONS[0],
                                {ACTIONS[0]: compiler},
                                hub.RunContext(),
                                repository_root=root,
                            )
                    else:
                        result = hub.run_action(
                            ACTIONS[0],
                            {ACTIONS[0]: compiler},
                            hub.RunContext(),
                            repository_root=root,
                        )
                        self.assertEqual(result["ok"], mode == "success")
                        self.assertEqual(
                            result["status"],
                            {"write": "undeclared_writes", "timeout": "timeout"}.get(
                                mode, "completed"
                            ),
                        )
                        if mode == "success":
                            # Native success follows the exit status, not parsed JSON.
                            self.assertFalse(json.loads(result["stdout"])["ok"])
                            self.assertEqual(
                                result["stderr"], "fixture compiler diagnostic"
                            )
                        elif mode == "reject":
                            self.assertEqual(result["returncode"], 7)
                        elif mode == "write":
                            self.assertEqual(
                                result["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        else:
                            self.assertEqual(
                                (
                                    result["returncode"],
                                    result["stdout"],
                                    result["stderr"],
                                ),
                                (None, "partial", "deadline"),
                            )
                    self.assertEqual(
                        calls,
                        [
                            {
                                "argv": list(compiler.command),
                                "timeout": compiler.timeout_seconds,
                            }
                        ],
                    )
                finally:
                    hub.subprocess = old
                    (root / "undeclared.txt").unlink(missing_ok=True)

    def test_registered_mcp_lunar_prism_runtime_and_failure_paths(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "repository"
            manager = SessionManager()
            server = 'import sys;sys.path.insert(0,"scripts");import mcp_server as s;s.mcp.run(transport="stdio")'
            error = None
            async with manager.open(
                "mcp:plugin-check",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {
                    "PYTHONPATH": os.pathsep.join(SITES),
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_CONFIG_NOSYSTEM": "1",
                },
            ) as remote:
                try:
                    await self.connected(remote, root)
                except Exception as exc:
                    error = exc
            self.assertFalse(manager.active)
            if error:
                raise error

    async def connected(self, remote, root):
        document = yaml.safe_load(CONTRACT.read_text())
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(doc):
            assets = snapshot(doc)
            docs = workflow_documents([DESCRIPTOR], assets)
            self.assertTrue(docs[0]["validation"]["valid"], docs[0])
            compiled = compile_workflow("mcp:plugin-check", docs[0], tools)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertEqual(compiled["runtime_status"], "ready")
            self.assertTrue(compiled["prism_source"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
            return compiled, assets

        compiled, assets = compile(document)
        missing = [t for t in tools if t["name"] != PREFIX + "dispatch"]
        rejected = compile_workflow(
            "mcp:plugin-check", workflow_documents([DESCRIPTOR], assets)[0], missing
        )
        self.assertFalse(rejected["runnable"])
        self.assertTrue(rejected["diagnostics"])

        async def authorize():
            pass

        async def run(inputs, changed=None):
            workflow, received = compile(changed) if changed else (compiled, assets)
            return await execute(workflow, received, inputs, remote, authorize)

        base = {
            "context": vars(hub.RunContext()),
            "match": MATCH,
            "registry": REGISTRY,
            "repository_root": str(root),
        }
        for mode in ["success", "drift", "missing_check", "missing_test"]:
            for keep in [False, True]:
                # missing_check also prevents the test module's import; the
                # separate preflight scenario below proves sticky failure plus success.
                populate(root, ROOT, document, mode)
                before = hub.snapshot_repository(root)
                inputs = deepcopy(base)
                inputs["context"]["keep_going"] = keep
                result = await run(inputs)
                self.assertEqual(result["status"], "accepted", result)
                actual = result["outputs"]["result"]
                expected = original().run_intent_match(
                    selected_match(MATCH),
                    checked_registry(REGISTRY),
                    hub.RunContext(keep_going=keep),
                    repository_root=root,
                )
                self.assertEqual(stable(actual), stable(expected))
                self.assertEqual(hub.snapshot_repository(root), before)
                count = 1 if mode in ["drift", "missing_check"] and not keep else 2
                self.assertEqual(len(actual["children"]), count)
                self.assertEqual(actual["ok"], mode == "success")
                self.assertEqual(
                    actual["status"],
                    "intent_run_completed" if actual["ok"] else "intent_run_failed",
                )
                self.assertEqual(actual["route"]["score"], MATCH["score"])
                self.assertEqual(
                    actual["route"]["matched_terms"], MATCH["matched_terms"]
                )
                order = ORDER if count == 2 else ORDER[:4] + ["finish"]
                self.assertEqual([c["operation"] for c in result["calls"]], order)
                self.assertEqual(
                    [c["tool"] for c in result["calls"]], [PREFIX + op for op in order]
                )
                if mode == "success":
                    first, second = actual["children"]
                    self.assertEqual(
                        first["argv"],
                        [sys.executable, "scripts/sync_agent_plugins.py", "--check"],
                    )
                    self.assertEqual(
                        second["argv"],
                        [sys.executable, "tests/agent_clients/test_agent_plugins.py"],
                    )
                    self.assertEqual(
                        json.loads(first["stdout"]),
                        {"ok": True, "mode": "check", "changed": []},
                    )
                    self.assertIn("Ran 12 tests", second["stderr"])
                    self.assertTrue(second["stderr"].endswith("OK\n"))
                    self.assertTrue(
                        all(c["write_audit"]["ok"] for c in actual["children"])
                    )
                if mode == "drift":
                    changed = json.loads(actual["children"][0]["stdout"])["changed"]
                    self.assertEqual(
                        changed,
                        [
                            "plugins/mathformer/skills/demo/SKILL.md",
                            "plugins/mathformer/skills/obsolete/SKILL.md",
                        ],
                    )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
        populate(root, ROOT, document)
        # Missing registry entries preserve admission failure, including the
        # source-owned metadata exception at finish.
        for keep in [False, True]:
            inputs = deepcopy(base)
            inputs["registry"].pop(ACTIONS[0])
            inputs["context"].update(dry_run=True, keep_going=keep)
            result = await run(inputs)
            # Native finish indexes the missing action to build route metadata.
            with self.assertRaises(KeyError):
                original().run_intent_match(
                    selected_match(MATCH),
                    checked_registry(inputs["registry"]),
                    hub.RunContext(**inputs["context"]),
                    repository_root=root,
                )
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                [c["operation"] for c in result["calls"]],
                ORDER if keep else ORDER[:4] + ["finish"],
            )
            unknown = await remote.call(
                PREFIX + "dispatch",
                {
                    "action_id": ACTIONS[0],
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
                        "action_id": ACTIONS[0],
                    }
                },
            )
        # Real preflight failure followed by a successful dry-run child.
        import shutil

        shutil.rmtree(root / "skills")
        inputs = deepcopy(base)
        inputs["context"].update(dry_run=True, keep_going=True)
        result = await run(inputs)
        self.assertEqual(result["status"], "accepted", result)
        actual = result["outputs"]["result"]
        self.assertFalse(actual["ok"])
        self.assertEqual([c["ok"] for c in actual["children"]], [False, True])
        self.assertEqual(
            actual["children"][0]["preflight_errors"],
            ["missing required path: skills/"],
        )
        self.assertEqual(actual["children"][1]["status"], "dry_run")
        populate(root, ROOT, document)
        # CLI None and the MCP caller's 600-second leaf cap both pass through.
        for timeout in [None, 600]:
            inputs = deepcopy(base)
            inputs["context"]["dry_run"] = True
            for row in inputs["registry"].values():
                row["timeout_seconds"] = timeout
            result = await run(inputs)
            expected = original().run_intent_match(
                selected_match(MATCH),
                checked_registry(inputs["registry"]),
                hub.RunContext(dry_run=True),
                repository_root=root,
            )
            self.assertEqual(result["outputs"], {"result": expected})
        for forged in ["registry", "match", "cursor"]:
            inputs, changed = deepcopy(base), None
            inputs["context"]["dry_run"] = True
            if forged == "registry":
                inputs["registry"][ACTIONS[0]]["command"] = ["untrusted-code"]
            elif forged == "match":
                inputs["match"]["route"]["title"] = "untrusted metadata"
            else:
                changed = deepcopy(document)
                changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                    "state"
                ] = {"literal": {"ok": True, "children": [{"ok": True}, {"ok": True}]}}
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
        inputs = deepcopy(base)
        inputs["context"]["dry_run"] = True
        for limit in [1, 4, 7]:
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
        # Null/omitted repository ports retain REPO_ROOT, exclusively dry-run.
        for omitted in [False, True]:
            inputs = deepcopy(base)
            inputs["context"]["dry_run"] = True
            inputs["repository_root"] = None
            if omitted:
                inputs.pop("repository_root")
            result = await run(inputs)
            expected = original().run_intent_match(
                selected_match(MATCH),
                checked_registry(REGISTRY),
                hub.RunContext(dry_run=True),
            )
            self.assertEqual(result["outputs"], {"result": expected})


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
