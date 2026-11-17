#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Exercise the source route through production MCP and real Lunar/PRISM.

Native runner/self-tests execute from byte-identical copies in temporary mounts.
Only external compiler/provider discovery and the fixture clock are substituted.
No production runs, credentials, model calls or external theorem compilers.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
PYTHON = LUNAR / ".venv/bin/python"
if PYTHON.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(PYTHON), [str(PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
FIXTURES = ROOT / "tests/mcp/fixtures"
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT),
    str(FIXTURES),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)

import asyncio
from copy import deepcopy
from dataclasses import asdict
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from source_units_route_tools import ACTION, ROUTE, selected_match
from normalize_workflows_tools import source as normalizer
from source_units_route_boundary import NATIVE_PYTHON_PATHS
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.contracts import workflow_documents
from mcp_connections.execution import execute, ExecutionRejected
from mcp_connections.models import StdioConfig
from mcp_connections.workflow_compiler import compile_workflow

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_source_formalizable_units_workflow/workflow.yaml"
INTERFACE = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTEXT = asdict(hub.RunContext())
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 17,
    "matched_terms": ["source", "units"],
}


def original():
    namespace = dict(vars(hub))
    path = FIXTURES / "source_units_route_original.py.txt"
    exec(compile(path.read_text(), str(path), "exec"), namespace)
    return namespace["run_intent_match"]


def snapshot(document):
    paths = {row["path"] for row in document["provenance"]["sources"]} | {INTERFACE}
    texts = {p: (ROOT / p).read_text() for p in paths}
    texts[DESCRIPTOR] = json.dumps(document)
    return [
        {
            "path": p,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
        for p, text in texts.items()
    ]


def matrix(modes, family="source"):
    return {
        "schema_version": 2,
        "tests": [
            {
                "id": f"fixture.{i}",
                "module_family": family,
                "command": ["fixture-source-compiler", mode],
                "owner_skill": "fixture",
                "hook_id": "test.fixture",
                "test_kind": "regression",
                "risk_level": "low",
                "fixture_ids": ["deterministic-compiler"],
                "expected_exit": 0,
                "write_set": [],
                "timeout_seconds": 120,
                **(
                    {"optional_dependency": "fixture_provider_unavailable"}
                    if mode == "missing"
                    else {}
                ),
            }
            for i, mode in enumerate(modes)
        ],
    }


class SourceUnitsRouteTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        cls.temporary = tempfile.TemporaryDirectory(prefix="mathformer-source-units-")
        cls.directory = Path(cls.temporary.name)
        cls.mount = cls.directory / "repository"
        cls.empty = cls.mount / "missing-inputs"
        cls.empty.mkdir(parents=True)
        cls.outside = cls.directory / "outside-service"
        cls.outside.mkdir()
        for path in NATIVE_PYTHON_PATHS | {
            "scripts/workflow_write_audit.py",
            "tests/test_matrix.json",
        }:
            target = cls.mount / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / path).read_bytes())
        cls.canonical = json.loads((ROOT / "tests/test_matrix.json").read_text())
        cls.canonical["tests"] = [
            r for r in cls.canonical["tests"] if r["module_family"] == "source"
        ]
        cls.registry = {ACTION: hub.build_registry()[ACTION]}
        cls.projection = {
            key: hub.action_to_dict(value) for key, value in cls.registry.items()
        }

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def reset(self, data):
        shutil.rmtree(self.mount / "artifacts", ignore_errors=True)
        (self.mount / "undeclared.txt").unlink(missing_ok=True)
        (self.mount / "tests/test_matrix.json").write_text(json.dumps(data))

    def test_contract_identity_policy_provenance_generator(self):
        d = self.document
        self.assertEqual(d["id"], "route_source_formalizable_units_workflow")
        self.assertEqual(d["aliases"], [ROUTE])
        self.assertEqual(d["lifecycle"], "active")
        self.assertEqual(
            d["policy"]["limits"], {"wall_time_seconds": 3600, "max_operation_calls": 5}
        )
        self.assertEqual(d["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertEqual(d["policy"]["resume"]["mode"], "none")
        self.assertEqual(d["flow"]["steps"][1]["max_iterations"], 1)
        self.assertEqual(d["flow"]["steps"][1]["on_exhausted"], "fail")
        self.assertIn(
            "scripts/mathformer.py", [r["path"] for r in d["provenance"]["sources"]]
        )
        for row in d["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertEqual(normalizer().source_units_route_descriptor(), d)
        self.assertEqual(
            self.registry[ACTION].command,
            (
                "{python}",
                "tests/test_program/run_comprehensive_tests.py",
                "--module-family",
                "source",
                "--json",
            ),
        )
        self.assertEqual(self.registry[ACTION].timeout_seconds, 900)
        self.assertEqual(len(self.canonical["tests"]), 4)
        self.assertEqual(
            [r["timeout_seconds"] for r in self.canonical["tests"]], [120] * 4
        )

    def test_frozen_entrypoint_and_shared_steps(self):
        match = selected_match(MATCH)
        for root in (self.empty, self.mount):
            for keep_going in (False, True):
                context = hub.RunContext(dry_run=True, keep_going=keep_going)
                actual = hub.run_intent_match(
                    match, self.registry, context, repository_root=root
                )
                self.assertEqual(
                    actual,
                    original()(match, self.registry, context, repository_root=root),
                )
                self.assertEqual(len(actual["children"]), 1)
                self.assertEqual(actual["ok"], root == self.mount)
        state = hub.initialize_intent_state()
        for keep_going in (False, True):
            child = {"ok": False, "status": "failed"}
            updated, done = hub.advance_intent_state(
                state, child, hub.RunContext(keep_going=keep_going), 1
            )
            self.assertTrue(done)
            self.assertEqual(updated, {"ok": False, "children": [child]})
            self.assertEqual(state, {"ok": True, "children": []})
        self.assertEqual(
            hub.run_action(ACTION, {}, hub.RunContext()),
            {"ok": False, "status": "unknown_action", "action_id": ACTION},
        )
        with self.assertRaises(KeyError):
            original()(match, {}, hub.RunContext())

    def test_native_runner_cursor_and_exhaustion(self):
        path = self.mount / "tests/test_program/run_comprehensive_tests.py"
        spec = importlib.util.spec_from_file_location(
            "source_units_fixture_runner", path
        )
        native = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(native)
        # No external processes are needed to exercise cursor and exhaustion guards.
        self.reset(matrix(["pass"], family="atp"))
        args = native.parse_args(["--module-family", "source", "--json"])
        state = native.prepare_checks(args)
        self.assertEqual(state["selected"], [])
        self.assertEqual(state["index"], 0)
        self.assertEqual(state["results"], [])
        self.assertFalse(native.checks_pending(state))
        with self.assertRaisesRegex(ValueError, "exhausted"):
            native.advance_check(state, args)
        self.reset(matrix(["pass", "fail", "pass"]))
        state = native.prepare_checks(args)
        self.assertTrue(native.checks_pending(state))
        with self.assertRaisesRegex(ValueError, "unconsumed"):
            native.finalize_checks(state, args)
        broken = deepcopy(state)
        broken["results"] = [{}]
        with self.assertRaisesRegex(ValueError, "cursor"):
            native.advance_check(broken, args)

    def test_registered_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        server = (
            "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
            + repr([str(ROOT / "scripts"), str(FIXTURES), str(ROOT), *SITES])
            + ";from source_units_route_boundary import serve;serve("
            + repr(str(self.mount))
            + ","
            + repr(str(FIXTURES))
            + ")"
        )
        manager = SessionManager()
        failure = None
        async with manager.open(
            "source-units",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile_document(document, inventory=None):
                    assets = snapshot(document)
                    selected = workflow_documents([DESCRIPTOR], assets)[0]
                    compiled = compile_workflow(
                        "mcp:source-units",
                        selected,
                        tools if inventory is None else inventory,
                    )
                    return compiled, assets

                workflow, assets = compile_document(self.document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(
                    set(workflow["bindings"]), set(self.document["operations"])
                )
                self.assertFalse(compile_document(self.document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(
                    data=None,
                    context=None,
                    root=None,
                    document=None,
                    registry=None,
                    match=None,
                ):
                    if data is not None:
                        self.reset(data)
                    compiled, received = (
                        compile_document(document) if document else (workflow, assets)
                    )
                    return await execute(
                        compiled,
                        received,
                        {
                            "context": CONTEXT if context is None else context,
                            "match": MATCH if match is None else match,
                            "registry": (
                                self.projection if registry is None else registry
                            ),
                            "repository_root": str(
                                self.mount if root is None else root
                            ),
                        },
                        remote,
                        authorize,
                    )

                # Missing inputs and dry-run preserve native payloads without launches.
                for root in (self.empty, self.mount):
                    context = dict(CONTEXT, dry_run=True)
                    result = await run(context=context, root=root)
                    self.assertEqual(result["status"], "accepted", result)
                    expected = original()(
                        selected_match(MATCH),
                        self.registry,
                        hub.RunContext(**context),
                        repository_root=root,
                    )
                    self.assertEqual(result["outputs"], {"result": expected})
                default = await remote.call(
                    "mathformer_source_units_route_dispatch",
                    {
                        "action_id": ACTION,
                        "context": dict(CONTEXT, dry_run=True),
                        "registry": self.projection,
                    },
                )
                self.assertEqual(
                    default["child"],
                    hub.run_action(ACTION, self.registry, hub.RunContext(dry_run=True)),
                )
                for mount in ({}, {"repository_root": None}):
                    result = await execute(
                        workflow,
                        assets,
                        {
                            "context": dict(CONTEXT, dry_run=True),
                            "match": MATCH,
                            "registry": self.projection,
                            **mount,
                        },
                        remote,
                        authorize,
                    )
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"]["result"]["children"], [default["child"]]
                    )
                result = await run(root=self.empty)
                self.assertEqual(result["status"], "accepted", result)
                self.assertFalse(result["outputs"]["result"]["ok"])
                child = result["outputs"]["result"]["children"][0]
                self.assertTrue(child["preflight_errors"])
                self.assertNotIn("returncode", child)
                # The canonical four self-tests run their real Python implementations.
                result = await run(self.canonical)
                self.assertEqual(result["status"], "accepted", result)
                route = result["outputs"]["result"]
                self.assertTrue(route["ok"], route)
                child = route["children"][0]
                self.assertEqual(child["returncode"], 0)
                self.assertTrue(child["write_audit"]["ok"])
                report = json.loads(child["stdout"])
                self.assertEqual(
                    report,
                    json.loads(
                        (
                            self.mount
                            / "artifacts/test_program/deterministic_tests.json"
                        ).read_text()
                    ),
                )
                self.assertEqual(report["families"], ["source"])
                self.assertEqual(
                    [r["check_id"] for r in report["results"]],
                    [r["id"] for r in self.canonical["tests"]],
                )
                self.assertEqual([r["status"] for r in report["results"]], ["pass"] * 4)
                self.assertTrue((self.mount / report["dependency_map"]).is_file())
                self.assertEqual(report["schema_errors"], [])
                # Ordinary failed checks all complete in source order; keep-going
                # only controls route children, so it cannot add another action.
                data = matrix(["fail", "timeout", "write", "missing", "pass"])
                for keep_going in (False, True):
                    result = await run(
                        data, context=dict(CONTEXT, keep_going=keep_going)
                    )
                    self.assertEqual(result["status"], "accepted", result)
                    route = result["outputs"]["result"]
                    self.assertFalse(route["ok"])
                    self.assertEqual(route["status"], "intent_run_failed")
                    self.assertEqual(route["route"]["score"], 17)
                    self.assertEqual(
                        route["route"]["matched_terms"], MATCH["matched_terms"]
                    )
                    self.assertEqual(len(route["children"]), 1)
                    child = route["children"][0]
                    self.assertEqual(child["returncode"], 3)
                    self.assertEqual(child["status"], "undeclared_writes")
                    self.assertFalse(child["write_audit"]["ok"])
                    report = json.loads(child["stdout"])
                    self.assertEqual(
                        report,
                        json.loads(
                            (
                                self.mount
                                / "artifacts/test_program/deterministic_tests.json"
                            ).read_text()
                        ),
                    )
                    self.assertEqual(
                        [r["check_id"] for r in report["results"]],
                        [r["id"] for r in data["tests"]],
                    )
                    self.assertEqual(
                        [r["status"] for r in report["results"]],
                        ["fail", "fail", "fail", "skip", "pass"],
                    )
                    self.assertEqual(
                        report["results"][1]["stderr"], "timeout after 120s"
                    )
                    self.assertEqual(report["results"][1]["stdout"], "partial")
                    self.assertFalse(report["results"][2]["write_audit"]["ok"])
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [
                            "mathformer_source_units_route_" + op
                            for op in (
                                "initialize",
                                "select",
                                "dispatch",
                                "advance",
                                "finish",
                            )
                        ],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    # Compare the frozen native entrypoint using the same actual
                    # subprocesses and deterministic external boundary inputs.
                    self.reset(data)
                    environment = {
                        "PYTHONDONTWRITEBYTECODE": "1",
                        "PYTHONPATH": os.pathsep.join(
                            [
                                str(FIXTURES / "source_units_route_startup"),
                                str(FIXTURES),
                            ]
                        ),
                    }
                    with patch.dict(os.environ, environment, clear=True):
                        expected = original()(
                            selected_match(MATCH),
                            self.registry,
                            hub.RunContext(keep_going=keep_going),
                            repository_root=self.mount,
                        )
                    self.assertEqual(route, expected)
                # Selection exhaustion (including empty selection) is owned by
                # the native runner, not an invented four-row contract limit.
                for data, total in (
                    (matrix(["pass"], "atp"), 0),
                    (matrix(["pass"] * 6), 6),
                ):
                    result = await run(data)
                    self.assertEqual(result["status"], "accepted", result)
                    child = result["outputs"]["result"]["children"][0]
                    report = json.loads(child["stdout"])
                    self.assertTrue(report["ok"])
                    self.assertEqual(report["summary"]["total"], total)
                result = await run(matrix(["fail", "pass"]))
                child = result["outputs"]["result"]["children"][0]
                self.assertFalse(result["outputs"]["result"]["ok"])
                self.assertEqual(child["status"], "completed")
                self.assertEqual(child["returncode"], 3)
                self.assertTrue(child["write_audit"]["ok"])
                self.assertEqual(
                    [r["status"] for r in json.loads(child["stdout"])["results"]],
                    ["fail", "pass"],
                )
                # Unexpected external launch exceptions abort the runner and
                # propagate as the native subprocess's nonzero exit, no retries.
                result = await run(matrix(["crash", "pass"]))
                child = result["outputs"]["result"]["children"][0]
                self.assertEqual(child["returncode"], 1)
                self.assertIn(
                    "OSError: fixture compiler launch failed", child["stderr"]
                )
                self.assertEqual(child["stdout"], "")
                self.assertFalse(
                    (
                        self.mount / "artifacts/test_program/deterministic_tests.json"
                    ).exists()
                )
                malformed = matrix(["pass"])
                malformed["schema_version"] = 1
                result = await run(malformed)
                self.assertEqual(result["status"], "accepted", result)
                child = result["outputs"]["result"]["children"][0]
                self.assertEqual(child["returncode"], 1)
                self.assertIn("schema_version 2", child["stderr"])
                self.assertFalse(result["outputs"]["result"]["ok"])
                logs = [
                    json.loads(s)
                    for s in (self.directory / "native-launch.jsonl")
                    .read_text()
                    .splitlines()
                ]
                self.assertTrue(
                    any(
                        r["command"][1:]
                        == [
                            "tests/test_program/run_comprehensive_tests.py",
                            "--module-family",
                            "source",
                            "--json",
                        ]
                        and r["timeout"] == 900
                        for r in logs
                    )
                )
                self.assertEqual(
                    {r["timeout"] for r in logs if "--self-test" in r["command"]}, {120}
                )
                compiler = [
                    json.loads(s)
                    for s in (self.directory / "compiler.jsonl")
                    .read_text()
                    .splitlines()
                ]
                self.assertTrue(compiler)
                self.assertEqual({r["timeout"] for r in compiler}, {120})
                rejected = await remote.call(
                    "mathformer_source_units_route_dispatch",
                    {
                        "action_id": ACTION,
                        "context": CONTEXT,
                        "registry": {},
                        "repository_root": str(self.empty),
                    },
                )
                self.assertEqual(rejected["child"]["status"], "unknown_action")
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_source_units_route_finish",
                        {
                            "state": {"ok": False, "children": [rejected["child"]]},
                            "match": MATCH,
                            "registry": {},
                        },
                    )
                for keep_going in (False, True):
                    child = {"ok": False, "status": "ordinary_failure"}
                    advanced = await remote.call(
                        "mathformer_source_units_route_advance",
                        {
                            "state": {"ok": True, "children": []},
                            "child": child,
                            "context": dict(CONTEXT, keep_going=keep_going),
                        },
                    )
                    self.assertEqual(
                        advanced,
                        {"state": {"ok": False, "children": [child]}, "done": True},
                    )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_source_units_route_select",
                            {"state": advanced["state"], "match": MATCH},
                        )
                forged = deepcopy(self.projection)
                forged[ACTION]["command"].append("--forged")
                result = await run(root=self.empty, registry=forged)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(result["calls"]), 3)
                forged = deepcopy(MATCH)
                forged["route"]["title"] = "untrusted route"
                result = await run(root=self.empty, match=forged)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(result["calls"]), 2)
                # Exhaustion cannot occur for the admitted singleton; force the
                # condition false to check the actual PRISM runtime's bound.
                exhausted = deepcopy(self.document)
                exhausted["flow"]["steps"][1]["until"] = {"literal": False}
                result = await run(root=self.empty, document=exhausted)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertEqual(len(result["calls"]), 4)
                self.assertIsNone(result["outputs"])
                budget = deepcopy(self.document)
                budget["policy"]["limits"]["max_operation_calls"] = 3
                result = await run(root=self.empty, document=budget)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    3,
                )
                self.assertIn("budget", str(result).lower())
                invalid = deepcopy(MATCH)
                invalid["route"]["action_ids"].append(ACTION)
                with self.assertRaises(ExecutionRejected):
                    await run(root=self.empty, match=invalid)
                # Service write roots are checked even when native selection
                # would otherwise be admissible; production guard is registered.
                result = await run(root=self.outside)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(result["calls"]), 3)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
