#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Actual native route, MCP bindings and Lunar/PRISM runtime, on disposable data.

WORKFLOW_CONTRACT_PATH is required before and after host installation. No live
provider, external compiler, prover, production workflow or credential is used.
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
from physics_coherence_route_tools import (
    ACTIONS,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
    register_physics_coherence_route_tools,
)
from physics_coherence_route_tree import closure, populate, OUTPUT, REPORT
from reasoning_route_compiler import install
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_mathformerphysicslib_coherence_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
NATIVE = closure(hub.build_registry(), ACTIONS)
REGISTRY = {key: hub.action_to_dict(item) for key, item in NATIVE.items()}
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": list(ACTIONS)},
    "score": 37,
    "matched_terms": ["physics", "coherence"],
}
BODY = ["select_action", "run_selected_action", "advance"]


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/physics_coherence_route_original.py.txt"
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


def leaves(result):
    if "children" in result:
        return [leaf for child in result["children"] for leaf in leaves(child)]
    return [result]


class CoherenceRouteTests(unittest.TestCase):
    maxDiff = None

    def test_contract_generator_provenance_and_native_declarations(self):
        spec = importlib.util.spec_from_file_location(
            "coherence_route_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.physics_coherence_route_descriptor(), document)
        self.assertEqual(
            document["id"], "route_mathformerphysicslib_coherence_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 8},
        )
        self.assertEqual(document["policy"]["failure"]["retry"]["max_attempts"], 1)
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
        suite = NATIVE["mathformerphysicslib:coherence-suite"]
        self.assertEqual(len(suite.depends_on), 9)
        self.assertTrue(all(item.timeout_seconds is None for item in NATIVE.values()))
        self.assertEqual(
            NATIVE["mathformerphysicslib:coherence-loop-report"].command,
            ("{python}", REPORT, "--json"),
        )
        for keep in [False, True]:
            state = hub.initialize_intent_state()
            state, done = hub.advance_intent_state(
                state, {"ok": False}, hub.RunContext(keep_going=keep), 2
            )
            self.assertEqual(done, not keep)
            self.assertFalse(state["ok"])
            state, done = hub.advance_intent_state(
                state, {"ok": True}, hub.RunContext(keep_going=keep), 2
            )
            self.assertTrue(done)
            self.assertFalse(state["ok"])
            check_state(state)
            with self.assertRaises(ValueError):
                check_state(state, selecting=True)

    def test_native_admission_and_external_compiler_boundary(self):
        # There is no provider or compiler in this route: its generative output
        # is an advisory plan. This separate fixture tests the controller's
        # external boundary without replacing any selected production step.
        oracle = original()
        for key, kwargs, status in [
            ("missing", {}, "unknown_action"),
            (ACTIONS[0], {"seen": {ACTIONS[0]}}, "dependency_cycle"),
            (ACTIONS[0], {"extra_args": ["--forbidden"]}, "extra_args_for_sequence"),
        ]:
            expected = oracle.run_action(key, NATIVE, hub.RunContext(), **kwargs)
            self.assertEqual(
                hub.run_action(key, NATIVE, hub.RunContext(), **kwargs), expected
            )
            self.assertEqual(expected["status"], status)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            saved = hub.subprocess
            for mode in ["success", "reject", "write", "timeout", "launch_error"]:
                item = replace(
                    NATIVE["mathformerphysicslib:coherence-loop-report"],
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
                            self.assertEqual(child["stdout"], "partial")
                            self.assertEqual(child["stderr"], "deadline")
                        else:
                            self.assertFalse(json.loads(child["stdout"])["ok"])
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
            mcp = FastMCP("coherence-service-policy")
            permissions = {"write": False, "path": True}

            def authorize():
                if not permissions["write"]:
                    raise PermissionError("service is read-only")

            register_physics_coherence_route_tools(
                mcp, authorize, lambda path: permissions["path"]
            )
            args = {
                "action": ACTIONS[1],
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
                        "mathformer_physics_coherence_route_run_selected_action", args
                    )

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
                + ";from physics_coherence_route_tree import serve;serve("
                + repr(str(root))
                + ")"
            )
            async with manager.open(
                "physics-coherence-route",
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
                        "mcp:physics-coherence-route",
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
                    if t["name"]
                    != "mathformer_physics_coherence_route_run_selected_action"
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
                # Missing preflight paths exercise early stops at both route and
                # nine-item suite levels, with no subprocesses or report writes.
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["context"].update(keep_going=keep)
                    result = await run(inputs)
                    expected = original().run_intent_match(
                        selected_match(MATCH),
                        NATIVE,
                        hub.RunContext(**inputs["context"]),
                        repository_root=root,
                    )
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertEqual(len(expected["children"]), 2 if keep else 1)
                    self.assertEqual(len(leaves(expected)), 10 if keep else 1)
                    self.assertFalse(expected["ok"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["initialize"] + BODY * (2 if keep else 1) + ["finish"],
                    )
                    self.assertFalse((root / OUTPUT).exists())
                lean = populate(root, ROOT, NATIVE)
                # Planned results visit every source action, without launching
                # self-tests or touching reports. Both paths compare to source.
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["context"].update(dry_run=True, keep_going=keep)
                    result = await run(inputs)
                    expected = original().run_intent_match(
                        selected_match(MATCH),
                        NATIVE,
                        hub.RunContext(**inputs["context"]),
                        repository_root=root,
                    )
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertTrue(expected["ok"])
                    self.assertEqual(len(leaves(expected)), 10)
                    self.assertTrue(
                        all(leaf["status"] == "dry_run" for leaf in leaves(expected))
                    )
                    self.assertFalse((root / OUTPUT).exists())
                # Run the unchanged nine native self-tests and one report leaf
                # solely on this copied tree and synthetic Lean text.
                output = root / OUTPUT
                baseline = json.dumps(
                    {
                        "concepts": [
                            {
                                "concept_id": "vector_field.real.euclidean3",
                                "grounding_level": "direct_mathlib",
                            }
                        ]
                    }
                )
                for prior in [None, "{", "[]", "{}", baseline]:

                    def reset():
                        output.mkdir(parents=True, exist_ok=True)
                        path = output / "mathlib_grounding.json"
                        path.unlink(missing_ok=True)
                        if prior is not None:
                            path.write_text(prior)

                    reset()
                    result = await run(base)
                    self.assertEqual(result["status"], "accepted", result)
                    actual = result["outputs"]["result"]
                    self.assertTrue(actual["ok"], actual)
                    self.assertEqual(len(leaves(actual)), 10)
                    suite = actual["children"][0]["children"][0]
                    self.assertEqual(
                        [child["action"]["id"] for child in suite["children"]],
                        list(NATIVE["mathformerphysicslib:coherence-suite"].depends_on),
                    )
                    self.assertTrue(
                        all(child["returncode"] == 0 for child in suite["children"])
                    )
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["initialize"] + BODY * 2 + ["finish"],
                    )
                    leaf = leaves(actual)[-1]
                    self.assertEqual(leaf["argv"], [sys.executable, REPORT, "--json"])
                    report = json.loads(leaf["stdout"])
                    self.assertTrue(report["ok"])
                    self.assertEqual(report["gate_status"], "blocked")
                    self.assertEqual(len(report["checks"]), 6)
                    self.assertEqual(len(report["artifacts"]), 10)
                    self.assertEqual(report["generative_probe_count"], 7)
                    self.assertGreater(report["repair_action_count"], 0)
                    self.assertEqual(
                        sorted(p.name for p in lean.iterdir()),
                        ["Other.lean", "formalphysics_vector.lean"],
                    )
                    comparison = json.loads(
                        (output / "mathlib_grounding.json").read_text()
                    )["monotonic_comparison"]
                    self.assertEqual(
                        comparison["status"],
                        "regressed" if prior == baseline else "no_previous_report",
                    )
                    written = {p.name: p.read_bytes() for p in output.iterdir()}
                    reset()
                    expected = original().run_intent_match(
                        selected_match(MATCH),
                        NATIVE,
                        hub.RunContext(),
                        repository_root=root,
                    )
                    self.assertEqual(actual, expected)
                    self.assertEqual(
                        written, {p.name: p.read_bytes() for p in output.iterdir()}
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                # A malformed inventory manifest becomes a captured report-leaf
                # failure; the preceding nine self-tests still complete.
                manifest = lean.parent / "MANIFEST.json"
                manifest.write_text("{")
                result = await run(base)
                self.assertEqual(result["status"], "accepted", result)
                self.assertFalse(result["outputs"]["result"]["ok"])
                self.assertIn(
                    "JSONDecodeError", leaves(result["outputs"]["result"])[-1]["stderr"]
                )
                manifest.unlink()
                # One missing suite leaf stops the suite early; keep_going
                # visits all nine and then a successful report, retaining failure.
                first = NATIVE["mathformerphysicslib:coherence-suite"].depends_on[0]
                path = root / NATIVE[first].required_paths[0]
                path.unlink()
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["context"]["keep_going"] = keep
                    result = await run(inputs)
                    actual = result["outputs"]["result"]
                    self.assertFalse(actual["ok"])
                    self.assertEqual(len(leaves(actual)), 10 if keep else 1)
                    self.assertEqual(len(actual["children"]), 2 if keep else 1)
                    if keep:
                        self.assertTrue(actual["children"][1]["ok"])
                populate(root, ROOT, NATIVE)
                # Empty inventory makes the six-check summary fail even though
                # all self-tests still succeed; no repair or convergence retry.
                for path in lean.glob("*.lean"):
                    path.unlink()
                result = await run(base)
                actual = result["outputs"]["result"]
                self.assertFalse(actual["ok"])
                self.assertEqual(len(leaves(actual)), 10)
                report = json.loads(leaves(actual)[-1]["stdout"])
                self.assertFalse(report["ok"])
                self.assertEqual(report["module_count"], 0)
                self.assertEqual(leaves(actual)[-1]["returncode"], 1)
                populate(root, ROOT, NATIVE)
                # Partial report writes are retained after native IO failure.
                (output / "inventory.json").unlink()
                (output / "inventory.json").mkdir()
                result = await run(base)
                leaf = leaves(result["outputs"]["result"])[-1]
                self.assertFalse(leaf["ok"])
                self.assertIn("IsADirectoryError", leaf["stderr"])
                self.assertTrue((output / "coherence_report.md").is_file())
                (output / "inventory.json").rmdir()
                # Bounds, exhausted loops, forged capabilities and cursor errors
                # use the actual compiled graph and registered tool interfaces.
                inputs = deepcopy(base)
                inputs["context"]["dry_run"] = True
                for limit in [1, 4, 7]:
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
                for bound in [1, 2]:
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
                        args["registry"][ACTIONS[0]]["depends_on"] = ["forged-command"]
                    elif forged == "match":
                        args["match"]["route"]["title"] = "forged title"
                    elif forged == "missing_registry":
                        args["registry"] = {}
                    else:
                        changed = deepcopy(document)
                        changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                            "state"
                        ] = {
                            "literal": {
                                "ok": True,
                                "children": [{"ok": True}, {"ok": True}],
                            }
                        }
                    result = await run(args, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                unknown = await remote.call(
                    "mathformer_physics_coherence_route_run_selected_action",
                    {
                        "action": ACTIONS[0],
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
