#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native physics planning route through registered MCP and real Lunar/PRISM.

Explicit WORKFLOW_CONTRACT_PATH is required, including after host installation.
Sources run solely in disposable trees. No model, compiler, prover, credential,
promotion or production workflow is used. The deterministic compiler fixture
covers the generic controller boundary separately; this route has no provider.
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
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
sys.path.extend(SITES)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import traceback
from dataclasses import replace
import hashlib
import importlib.util
import json
import tempfile
from types import SimpleNamespace
import unittest
import yaml

import mathformer as hub
from physics_pathologies_route_tools import (
    ACTIONS,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
    register_physics_pathologies_route_tools,
)
from physics_pathologies_route_tree import populate
from reasoning_route_compiler import install
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_repair_physics_lean_pathologies_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
NATIVE = {key: hub.build_registry()[key] for key in ACTIONS}
REGISTRY = {key: hub.action_to_dict(item) for key, item in NATIVE.items()}
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": list(ACTIONS)},
    "score": 37,
    "matched_terms": ["physics", "pathologies"],
}
BODY = ["select", "run_child", "advance"]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/physics_pathologies_route_original.py.txt"
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


@asynccontextmanager
async def checked_session(manager, *args):
    # SessionManager sanitizes arbitrary body exceptions for service callers.
    # Keep local assertion diagnostics in this credential-free test runner.
    async with manager.open(*args) as remote:
        try:
            yield remote
        except Exception as error:
            raise MCPConnectionError(traceback.format_exc()) from error


class PathologiesRouteTests(unittest.TestCase):
    maxDiff = None

    def test_contract_generator_provenance_and_native_declarations(self):
        module = load_module(
            "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
            "pathologies_normalizer",
        )
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.physics_pathologies_route_descriptor(), document)
        self.assertEqual(
            document["id"], "route_repair_physics_lean_pathologies_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 20},
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
        self.assertEqual(checked_registry(REGISTRY), NATIVE)
        self.assertEqual(selected_match(MATCH).route.action_ids, ACTIONS)
        self.assertTrue(
            all(
                not item.depends_on
                and item.timeout_seconds is None
                and len(item.command) == 2
                for item in NATIVE.values()
            )
        )
        for keep in [False, True]:
            state = hub.initialize_intent_state()
            prior = deepcopy(state)
            state, done = hub.advance_intent_state(
                state, {"ok": False}, hub.RunContext(keep_going=keep), 6
            )
            self.assertEqual(prior, {"ok": True, "children": []})
            self.assertEqual(done, not keep)
            self.assertFalse(state["ok"])
            for _ in range(5):
                state, done = hub.advance_intent_state(
                    state, {"ok": True}, hub.RunContext(keep_going=keep), 6
                )
            self.assertTrue(done)
            self.assertFalse(state["ok"])
            check_state(state)
            with self.assertRaises(ValueError):
                check_state(state, selecting=True)

    def test_advisory_controller_decision_priority_and_history(self):
        controller = load_module(
            NATIVE[ACTIONS[-1]].command[1], "pathologies_controller"
        )
        frontier = [
            {
                "node_id": "operator.domain",
                "owner_skill": "mathformerphysicslib-object-workbench",
                "action": "work_object",
                "blockers": ["not_promoted"],
            }
        ]
        base = {
            "status": "needs_expansion",
            "exhaustive": True,
            "iteration_signature": "abc",
            "outstanding_nodes": [{"id": "operator.domain"}],
            "next_frontier": frontier,
        }
        cases = [
            (
                {"status": "complete", "outstanding_nodes": [], "exhaustive": False},
                ["abc"],
                6,
                "complete",
                [],
            ),
            (
                {"status": "not_required", "outstanding_nodes": []},
                [],
                6,
                "complete",
                [],
            ),
            (
                {"exhaustive": False},
                ["abc"],
                6,
                "blocked",
                ["expansion_map_not_exhaustive"],
            ),
            ({}, ["abc"], 6, "blocked", ["repeated_iteration_signature:abc"]),
            ({}, [], 6, "blocked", ["max_iterations_reached:6"]),
            ({"outstanding_nodes": []}, [], 6, "blocked", ["max_iterations_reached:6"]),
            ({"outstanding_nodes": []}, [], 1, "complete", []),
            ({}, [], 1, "recurse", []),
            ({"status": "blocked"}, [], 1, "blocked", ["expansion_map_blocked"]),
            (
                {"status": "blocked", "exhaustive": False},
                [],
                1,
                "blocked",
                ["expansion_map_blocked", "expansion_map_not_exhaustive"],
            ),
        ]
        for change, prior, iteration, decision, blockers in cases:
            expansion = dict(deepcopy(base), **change)
            history = [{"iteration_signature": sig} for sig in prior]
            saved = deepcopy((expansion, history))
            result = controller.build_control_plan(
                expansion_map=expansion,
                previous_expansion_maps=history,
                iteration=iteration,
                max_iterations=6,
            )
            self.assertEqual(result["decision"], decision)
            self.assertEqual(result["blockers"], blockers)
            self.assertEqual(result["iteration"], iteration)
            self.assertEqual(result["prior_iteration_signatures"], prior)
            self.assertEqual(
                result["outstanding_node_count"], len(expansion["outstanding_nodes"])
            )
            self.assertEqual(
                result["next_actions"],
                [] if decision == "complete" else [dict(frontier[0], order=1)],
            )
            self.assertEqual((expansion, history), saved)
        defaults = controller.parse_args([])
        self.assertEqual((defaults.iteration, defaults.max_iterations), (1, 6))

    def test_native_external_compiler_boundary(self):
        # Separate generic subprocess boundary; never substitutes a source step.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            saved = hub.subprocess
            for mode in ["success", "reject", "write", "timeout", "launch_error"]:
                item = replace(
                    NATIVE[ACTIONS[-1]],
                    command=("fixture-reasoning-compiler", mode),
                    required_paths=(),
                    timeout_seconds=3,
                )
                calls = install(hub, root)
                try:
                    if mode == "launch_error":
                        with self.assertRaisesRegex(
                            OSError, "fixture compiler launch failed"
                        ):
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
                            {"write": "undeclared_writes", "timeout": "timeout"}.get(
                                mode, "completed"
                            ),
                        )
                        if mode == "timeout":
                            self.assertIsNone(child["returncode"])
                            self.assertEqual(
                                (child["stdout"], child["stderr"]),
                                ("partial", "deadline"),
                            )
                        else:
                            self.assertEqual(
                                json.loads(child["stdout"])["diagnostics"][0]["code"],
                                "fixture_type_error",
                            )
                            self.assertEqual(
                                child["returncode"], 7 if mode == "reject" else 0
                            )
                        if mode == "write":
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                    self.assertEqual(
                        calls,
                        [{"argv": ["fixture-reasoning-compiler", mode], "timeout": 3}],
                    )
                finally:
                    hub.subprocess = saved
                    (root / "undeclared.txt").unlink(missing_ok=True)

    def test_registered_service_policy(self):
        async def scenario():
            mcp = FastMCP("pathologies-service-policy")
            permissions = {"write": False, "path": True}

            def authorize():
                if not permissions["write"]:
                    raise PermissionError("service is read-only")

            register_physics_pathologies_route_tools(
                mcp, authorize, lambda path: permissions["path"]
            )
            args = {
                "action_id": ACTIONS[0],
                "registry": REGISTRY,
                "context": vars(hub.RunContext()),
                "repository_root": None,
            }
            for allowed, path, message in [
                (False, True, "read-only"),
                (True, False, "service roots"),
            ]:
                permissions.update(write=allowed, path=path)
                with self.assertRaisesRegex(Exception, message):
                    await mcp.call_tool(
                        "mathformer_physics_pathologies_route_run_child", args
                    )
            args["context"]["dry_run"] = True
            # Null uses the default mount, dry-run performs no process/write.
            result = await mcp.call_tool(
                "mathformer_physics_pathologies_route_run_child", args
            )
            self.assertTrue(result)

        asyncio.run(scenario())

    def test_registered_mcp_lunar_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            manager = SessionManager()
            paths = [str(ROOT / "scripts"), str(ROOT / "tests/mcp/fixtures"), *SITES]
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr(paths)
                + ";from physics_pathologies_route_tree import serve;serve("
                + repr(str(root))
                + ")"
            )
            async with checked_session(
                manager,
                "physics-pathologies-route",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {"PYTHONDONTWRITEBYTECODE": "1"},
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile_doc(doc, inventory=None):
                    assets = snapshot(doc)
                    compiled = compile_workflow(
                        "mcp:physics-pathologies-route",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools if inventory is None else inventory,
                    )
                    return compiled, assets

                compiled, assets = compile_doc(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertEqual(compiled["runtime_status"], "ready")
                self.assertTrue(compiled["prism_source_hash"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                missing = [
                    t
                    for t in tools
                    if t["name"] != "mathformer_physics_pathologies_route_run_child"
                ]
                self.assertFalse(compile_doc(document, missing)[0]["runnable"])
                advertised = {t["name"]: t for t in tools}
                for op in document["operations"].values():
                    interface = advertised[op["execution"]["binding"]["target"]]
                    self.assertEqual(
                        set(interface["inputSchema"].get("required", [])),
                        set(op["inputs"]),
                    )
                    self.assertEqual(
                        set(interface["outputSchema"]["properties"]), set(op["outputs"])
                    )

                async def authorize():
                    pass

                async def run(inputs, changed=None):
                    c, a = compile_doc(changed) if changed else (compiled, assets)
                    self.assertTrue(c["runnable"], c["diagnostics"])
                    return await execute(c, a, inputs, remote, authorize)

                base = {
                    "context": vars(hub.RunContext()),
                    "match": MATCH,
                    "registry": REGISTRY,
                    "repository_root": str(root),
                }

                async def compare(inputs, count):
                    result = await run(inputs)
                    expected = original().run_intent_match(
                        selected_match(MATCH),
                        NATIVE,
                        hub.RunContext(**inputs["context"]),
                        repository_root=root,
                    )
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertEqual(len(expected["children"]), count)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["initialize"] + BODY * count + ["finish"],
                    )
                    return result

                # Actual preflight failure, both native stopping policies.
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["context"]["keep_going"] = keep
                    result = await compare(inputs, 6 if keep else 1)
                    self.assertFalse(result["outputs"]["result"]["ok"])
                populate(root, ROOT, NATIVE)
                inputs = deepcopy(base)
                inputs["context"]["dry_run"] = True
                result = await compare(inputs, 6)
                self.assertTrue(
                    all(
                        c["status"] == "dry_run"
                        for c in result["outputs"]["result"]["children"]
                    )
                )
                # All six unchanged native CLIs run against empty fixture inputs.
                # Planner blocked is data, with exit 0, so all six still succeed.
                result = await compare(base, 6)
                envelope = result["outputs"]["result"]
                self.assertTrue(envelope["ok"])
                plans = [json.loads(child["stdout"]) for child in envelope["children"]]
                self.assertEqual(plans[1]["status"], "no_objects")
                self.assertEqual(plans[-1]["status"], "blocked")
                self.assertEqual(
                    plans[-1]["blockers"], ["expansion_map_not_exhaustive"]
                )
                self.assertEqual(plans[-1]["prior_iteration_signatures"], [])
                self.assertEqual(
                    (plans[-1]["iteration"], plans[-1]["max_iterations"]), (1, 6)
                )
                self.assertEqual(plans[-1]["next_actions"], [])
                self.assertEqual(plans[3]["detected_object_classes"], [])
                self.assertTrue(plans[3]["requires_deterministic_first"])
                self.assertTrue(
                    plans[3]["acceptance_policy"]["generative_output_is_advisory"]
                )
                for child, item in zip(envelope["children"], NATIVE.values()):
                    self.assertEqual(child["argv"], [sys.executable, item.command[1]])
                    self.assertEqual(child["returncode"], 0)
                    self.assertTrue(child["write_audit"]["ok"])
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
                self.assertFalse((root / "artifacts").exists())
                # Real interpreter nonzero exit: required path exists but is a
                # directory. Remaining native planners succeed under keep-going.
                broken = root / NATIVE[ACTIONS[2]].command[1]
                broken.unlink()
                broken.mkdir()
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["context"]["keep_going"] = keep
                    result = await compare(inputs, 6 if keep else 3)
                    envelope = result["outputs"]["result"]
                    self.assertFalse(envelope["ok"])
                    self.assertEqual(envelope["status"], "intent_run_failed")
                    self.assertNotEqual(envelope["children"][2]["returncode"], 0)
                    self.assertFalse(envelope["children"][2]["ok"])
                    if keep:
                        self.assertTrue(envelope["children"][-1]["ok"])
                broken.rmdir()
                populate(root, ROOT, NATIVE)
                # Native leaf deadlines stay unbounded, unlike legacy MCP cap.
                import mcp_server

                capped = mcp_server._cap_unbounded_timeouts(NATIVE)
                self.assertTrue(
                    all(
                        a.timeout_seconds == mcp_server._DEFAULT_TIMEOUT_SECONDS
                        for a in capped.values()
                    )
                )
                self.assertTrue(all(a.timeout_seconds is None for a in NATIVE.values()))
                # Real compiler/runtime budget and exhausted-loop failure paths.
                inputs = deepcopy(base)
                inputs["context"]["dry_run"] = True
                for limit in [1, 4, 19]:
                    changed = deepcopy(document)
                    changed["policy"]["limits"]["max_operation_calls"] = limit
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        limit,
                    )
                for bound in [1, 6]:
                    changed = deepcopy(document)
                    changed["flow"]["steps"][1]["max_iterations"] = bound
                    changed["flow"]["steps"][1]["until"] = {"literal": False}
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["initialize"] + BODY * bound,
                    )
                for forged in ["registry", "match", "cursor", "missing_registry"]:
                    args, changed = deepcopy(inputs), None
                    if forged == "registry":
                        args["registry"][ACTIONS[0]]["command"] = ["forged-command"]
                    elif forged == "match":
                        args["match"]["route"]["title"] = "forged title"
                    elif forged == "missing_registry":
                        args["registry"] = {}
                    else:
                        changed = deepcopy(document)
                        changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                            "state"
                        ] = {"literal": {"ok": True, "children": [{"ok": True}] * 6}}
                    result = await run(args, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                unknown = await remote.call(
                    "mathformer_physics_pathologies_route_run_child",
                    {
                        "action_id": ACTIONS[0],
                        "registry": {},
                        "context": vars(hub.RunContext(dry_run=True)),
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
            self.assertFalse(manager.active)


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
