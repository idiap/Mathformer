#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Temporary source-identical repositories through real MCP, Lunar and PRISM.

The planner has no model/provider or external compiler boundary. Its native
Python child runs against synthetic files. Only generic hub boundary tests
substitute an external compiler with a deterministic executable fixture.
No source operation, MCP transport, PRISM parser/checker/compiler/runtime is mocked.
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
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
import yaml
import mathformer as hub
from coherence_repair_tools import source
from api_critic_tools import source as common_source
from coherence_repair_alias_tools import ACTION
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lib_coherence_repair_plan_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/coherence-repair-alias.workflow.json"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
SCRIPT = "skills/mathformerphysicslib/mathformerphysicslib-coherence-repair-planner/scripts/plan_coherence_repairs.py"
COMMON = "skills/mathformerphysicslib/mathformerphysicslib-coherence-inventory-builder/scripts/coherence_common.py"
CHILD = "mathformerphysicslib:coherence-repair-plan"
PREFIX = "mathformer_coherence_repair_alias_"
SERVER_PYTHON = str(ROOT / ".venv/bin/python")
SERVER = """import sys
sys.dont_write_bytecode = True
sys.path.insert(0, 'scripts')
from mcp_server import mcp
mcp.run(transport='stdio')
"""


def original(root):
    namespace = dict(vars(hub), REPO_ROOT=root)
    exec(
        (
            ROOT / "tests/mcp/fixtures/coherence_repair_alias_original.py.txt"
        ).read_text(),
        namespace,
    )
    # The frozen executor uses the native globals and the synthetic mount.
    return namespace["run_action"]


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    paths = {SCHEMA, *(r["path"] for r in document["provenance"]["sources"])}
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(p, (ROOT / p).read_text()) for p in sorted(paths)
    ]


class Observed:
    def __init__(self, remote):
        self.remote, self.records = remote, []

    async def tools(self):
        return await self.remote.tools()

    async def call(self, name, arguments):
        value = await self.remote.call(name, arguments)
        self.records.append(
            (name.removeprefix(PREFIX), deepcopy(arguments), deepcopy(value))
        )
        return value


class AliasTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="repair-alias-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        for name in (
            SCRIPT,
            COMMON,
            "libraries/MathformerPhysicsLib/release_status.py",
        ):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def test_contract_generator_provenance_and_registration(self):
        doc = self.document
        self.assertEqual(doc["id"], "hub_physics_lib_coherence_repair_plan_workflow")
        self.assertEqual(doc["aliases"], [ACTION])
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(
            doc["policy"]["limits"], dict(wall_time_seconds=3600, max_operation_calls=6)
        )
        self.assertEqual(
            doc["policy"]["failure"]["retry"], dict(max_attempts=1, retryable_codes=[])
        )
        self.assertIn(
            "scripts/mathformer.py", [r["path"] for r in doc["provenance"]["sources"]]
        )
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertEqual(json.loads((ROOT / AUTHORED).read_text()), doc)
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("repair_alias_generator", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual([d for d in module.inventory() if d["id"] == doc["id"]], [doc])
        from mathformer_mcp_service import service_coverage_report

        advertised = service_coverage_report(self.root / "unused.toml", {})["mcp_tools"]
        self.assertTrue(
            {v["execution"]["binding"]["target"] for v in doc["operations"].values()}
            <= set(advertised)
        )

    def test_native_controller_parity_and_state(self):
        with (
            patch.object(hub, "REPO_ROOT", self.root),
            patch.object(sys, "executable", SERVER_PYTHON),
        ):
            oracle = original(self.root)
            registry = hub.build_registry()
            self.assertFalse(registry[ACTION].command)
            self.assertEqual(registry[ACTION].depends_on, (CHILD,))
            self.assertIsNone(registry[CHILD].timeout_seconds)
            for keep in (False, True):
                for dry in (False, True):
                    context = hub.RunContext(dry_run=dry, keep_going=keep)
                    for seen, args in (
                        ([], []),
                        ([ACTION], ["bad"]),
                        ([CHILD], []),
                        ([], ["bad"]),
                        (["caller"], []),
                    ):
                        expected = oracle(
                            ACTION, registry, context, seen=set(seen), extra_args=args
                        )
                        self.assertEqual(
                            hub.run_action(
                                ACTION,
                                registry,
                                context,
                                seen=set(seen),
                                extra_args=args,
                            ),
                            expected,
                        )
                        self.assertEqual(
                            hub.run_action(
                                ACTION,
                                registry,
                                context,
                                seen=set(seen),
                                extra_args=args,
                                repository_root=self.root,
                            ),
                            expected,
                        )
            self.assertEqual(
                hub.run_action(
                    "missing",
                    registry,
                    hub.RunContext(),
                    seen={"missing"},
                    extra_args=["x"],
                ),
                dict(ok=False, status="unknown_action", action_id="missing"),
            )
            admission = hub.admit_action(ACTION, registry, seen=["caller"])
            state = hub.initialize_dependencies(admission)
            before = deepcopy(state)
            for keep in (False, True):
                child = dict(ok=False, status="completed", returncode=7)
                advanced, done = hub.advance_dependencies(
                    registry[ACTION], state, child, hub.RunContext(keep_going=keep)
                )
                self.assertEqual(state, before)
                self.assertEqual(
                    advanced,
                    dict(
                        index=1,
                        children=[child],
                        dependencies_ok=False,
                        ancestry=sorted([ACTION, "caller"]),
                    ),
                )
                self.assertTrue(done)
                self.assertFalse(
                    hub.dependency_command_guard(
                        registry[ACTION], advanced, hub.RunContext(keep_going=keep)
                    )
                )
                self.assertEqual(
                    hub.finish_dependencies(registry[ACTION], advanced)["status"],
                    "sequence_failed",
                )
                # Sticky failure is native even if a later successful child is supplied.
                advanced, _ = hub.advance_dependencies(
                    replace(registry[ACTION], depends_on=(CHILD, CHILD)),
                    advanced,
                    {"ok": True},
                    hub.RunContext(keep_going=keep),
                )
                self.assertFalse(advanced["dependencies_ok"])
                self.assertEqual(len(advanced["children"]), 2)

    def test_native_planner_findings_order_exhaustion_and_emission(self):
        from contextlib import redirect_stdout, redirect_stderr
        from io import StringIO

        native = source()
        common = common_source()
        # Every report and finding is consumed in order, with no hidden cap.
        kinds = [
            "concept_spread_without_foundation_owner",
            "confirmed_competing_concept_owner",
            "manifest_missing_foundations",
            "missing_foundations_index",
            "foundation_owner_not_indexed",
            "foundation_without_operable_api",
            "thin_foundation_api",
            "unrecognized",
            None,
        ]
        expected_actions = (
            ["consolidate_concept_owner"] * 2
            + ["repair_integration_surface"] * 3
            + ["add_operable_bridge_api"] * 2
            + ["record_or_block_gap"] * 2
        )
        reports = [
            {
                "findings": [
                    dict(kind=k, severity="high", concept_id=f"{i}:{j}")
                    for j, k in enumerate(kinds)
                ]
            }
            for i in range(130)
        ]
        before = deepcopy(reports)
        payload = native.repair_plan(reports)
        self.assertEqual(reports, before)
        self.assertEqual(payload["action_count"], 1170)
        self.assertEqual(payload["status"], "repair_required")
        self.assertEqual(
            [a["action"] for a in payload["actions"]], expected_actions * 130
        )
        self.assertEqual(
            [a["concept_id"] for a in payload["actions"]],
            [f"{i}:{j}" for i in range(130) for j in range(9)],
        )
        # Source takes sequences/iterables, exhausts nested inputs, and propagates malformed reports.
        self.assertEqual(native.repair_plan(iter(reports)), payload)
        self.assertEqual(
            native.repair_plan([{}, {"findings": []}])["status"], "no_repairs_required"
        )
        with self.assertRaises(AttributeError):
            native.repair_plan([{"findings": [None]}])
        summary = common.self_test_payload(self.root)
        self.assertNotIn("concept_occurrence_index", summary)
        graph = common.canonicalize(summary)
        self.assertEqual(graph["concepts"], [])
        grounding = common.audit_grounding(graph)
        expected = [
            grounding,
            common.critic_redefinitions(graph, grounding),
            common.critic_integration(summary, graph, self.root),
            common.critic_api(graph, self.root),
        ]
        self.assertEqual(native.default_reports(True, self.root), expected)
        planned = native.repair_plan(expected)
        self.assertEqual(
            [a["source_kind"] for a in planned["actions"]],
            ["missing_foundations_index", "manifest_missing_foundations"],
        )
        self.assertEqual(planned["status"], "repair_required")
        # Real parse/load/write/emit on explicit fixture reports, including zero-action exit zero.
        for selected in (reports, [{}, {"findings": []}]):
            paths = []
            for i, report in enumerate(selected):
                path = self.root / f"report-{i}.json"
                path.write_text(json.dumps(report))
                paths.append(str(path))
            output = self.root / "nested/plan.json"
            argv = [v for path in paths for v in ("--report", path)] + [
                "--output",
                str(output),
                "--json",
            ]
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = native.main(argv)
            self.assertEqual(code, 0)
            self.assertEqual(
                json.loads(stdout.getvalue()), native.repair_plan(selected)
            )
            self.assertEqual(
                json.loads(output.read_text()), native.repair_plan(selected)
            )
        with self.assertRaises(FileNotFoundError):
            native.load_reports({"reports": [str(self.root / "missing.json")]})
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            native.parse_arguments(["--not-an-option"])

    def test_generic_external_compiler_boundary_and_write_audit(self):
        compiler = ROOT / "tests/mcp/fixtures/coherence_canonicalize_alias_compiler.py"
        with patch.object(hub, "REPO_ROOT", self.root):
            oracle = original(self.root)
            for mode in ("success", "fail", "write"):
                registry = hub.build_registry()
                registry[CHILD] = replace(
                    registry[CHILD], command=(hub.PYTHON_TOKEN, str(compiler), mode)
                )
                results = []
                for run in (oracle, hub.run_action):
                    (self.root / "undeclared.txt").unlink(missing_ok=True)
                    results.append(run(ACTION, registry, hub.RunContext()))
                self.assertEqual(*results)
                result = results[0]
                child = result["children"][0]
                self.assertEqual(result["ok"], mode == "success")
                self.assertFalse(json.loads(child["stdout"])["ok"])
                self.assertEqual(child["returncode"], 7 if mode == "fail" else 0)
                if mode == "write":
                    self.assertEqual(
                        child["write_audit"]["unexpected_paths"], ["undeclared.txt"]
                    )
            registry[CHILD] = replace(
                registry[CHILD],
                command=(hub.PYTHON_TOKEN, str(compiler), "timeout"),
                timeout_seconds=1,
            )
            (self.root / "undeclared.txt").unlink(missing_ok=True)
            child = hub.run_action(ACTION, registry, hub.RunContext())["children"][0]
            self.assertEqual(child["status"], "timeout")
            self.assertFalse(child["ok"])
            self.assertTrue(child["write_audit"]["ok"])
            with self.assertRaises(FileNotFoundError):
                hub.launch_leaf_boundary(
                    registry[CHILD], dict(argv=[str(self.root / "absent")])
                )

    def test_registered_mcp_lunar_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()

        @asynccontextmanager
        async def opened():
            error = None
            async with manager.open(
                "repair-alias",
                StdioConfig(
                    command=SERVER_PYTHON, args=["-B", "-c", SERVER], cwd=str(ROOT)
                ),
                {},
            ) as remote:
                try:
                    yield remote
                except Exception as exc:
                    error = exc
            if error:
                raise error

        async with opened() as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile_doc(doc, inventory=None):
                received = assets(doc)
                selected = workflow_documents([DESCRIPTOR], received)[0]
                return (
                    compile_workflow(
                        "mcp:repair-alias",
                        selected,
                        tools if inventory is None else inventory,
                    ),
                    received,
                )

            workflow, received = compile_doc(self.document)
            self.assertTrue(workflow["runnable"], workflow["diagnostics"])
            self.assertTrue(workflow["runtime_source"])
            self.assertEqual(
                set(workflow["bindings"]), set(self.document["operations"])
            )
            self.assertFalse(compile_doc(self.document, [])[0]["runnable"])
            for name in self.document["operations"]:
                self.assertFalse(
                    compile_doc(
                        self.document, [t for t in tools if t["name"] != PREFIX + name]
                    )[0]["runnable"]
                )

            async def allow():
                pass

            async def run(context=None, seen=None, args=None, doc=None):
                w, a = compile_doc(doc) if doc else (workflow, received)
                self.assertTrue(w["runnable"], w["diagnostics"])
                self.observed = Observed(remote)
                return await execute(
                    w,
                    a,
                    dict(
                        context=vars(context or hub.RunContext()),
                        repository_root=str(self.root),
                        extra_args=args or [],
                        seen=seen or [],
                    ),
                    self.observed,
                    allow,
                )

            with (
                patch.object(hub, "REPO_ROOT", self.root),
                patch.object(sys, "executable", SERVER_PYTHON),
            ):
                oracle = original(self.root)
                for dry, keep, seen, args in (
                    (False, False, [], []),
                    (True, True, [], []),
                    (False, False, [ACTION], ["bad"]),
                    (False, False, [], ["bad"]),
                    (False, False, [CHILD], []),
                    (False, True, [CHILD], []),
                ):
                    context = hub.RunContext(dry_run=dry, keep_going=keep)
                    expected = oracle(
                        ACTION,
                        hub.build_registry(),
                        context,
                        extra_args=args,
                        seen=set(seen),
                    )
                    result = await run(context, seen, args)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"result": expected})
                    ops = [c["operation"] for c in result["calls"]]
                    rejected = seen == [ACTION] or bool(args)
                    self.assertEqual(
                        ops,
                        (
                            ["admit", "reject", "carry", "carry"]
                            if rejected
                            else ["admit", "initialize", "visit", "advance", "finish"]
                        ),
                    )
                    if not rejected:
                        child = expected["children"][0]
                        transition = next(
                            v
                            for name, _, v in self.observed.records
                            if name == "advance"
                        )
                        self.assertEqual(
                            transition,
                            dict(
                                done=True,
                                state=dict(
                                    index=1,
                                    children=[child],
                                    dependencies_ok=child["ok"],
                                    ancestry=sorted(set(seen) | {ACTION}),
                                ),
                            ),
                        )
                        if not dry and not seen:
                            self.assertTrue(expected["ok"])
                            self.assertEqual(
                                json.loads(child["stdout"])["status"], "repair_required"
                            )
                            self.assertEqual(child["returncode"], 0)
                            self.assertEqual(child["stderr"], "")
                            self.assertTrue(child["write_audit"]["ok"])
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                # Missing required source prevents launch even in dry-run.
                path = self.root / SCRIPT
                saved = path.read_bytes()
                path.unlink()
                for dry in (False, True):
                    context = hub.RunContext(dry_run=dry)
                    result = await run(context)
                    expected = oracle(ACTION, hub.build_registry(), context)
                    self.assertEqual(result["outputs"], {"result": expected})
                    child = result["outputs"]["result"]["children"][0]
                    self.assertFalse(child["ok"])
                    self.assertTrue(child["preflight_errors"])
                    self.assertNotIn("returncode", child)
                    self.assertNotIn("write_audit", child)
                path.write_bytes(saved)
                # Source-owned filesystem error midway through self_test_payload.
                native = common_source()
                owner = next(
                    c["owner_module"]
                    for c in native.canonicalize(native.self_test_inventory())[
                        "concepts"
                    ]
                    if c["owner_module"]
                )
                blocker = self.root / owner
                blocker.mkdir(parents=True)
                for keep in (False, True):
                    context = hub.RunContext(keep_going=keep)
                    result = await run(context)
                    expected = oracle(ACTION, hub.build_registry(), context)
                    self.assertEqual(result["outputs"], {"result": expected})
                    child = expected["children"][0]
                    self.assertFalse(expected["ok"])
                    self.assertEqual(expected["status"], "sequence_failed")
                    self.assertEqual(child["returncode"], 1)
                    self.assertEqual(child["stdout"], "")
                    self.assertIn("IsADirectoryError", child["stderr"])
                    self.assertTrue(child["write_audit"]["ok"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["admit", "initialize", "visit", "advance", "finish"],
                    )
                shutil.rmtree(blocker)
            state = hub.initialize_dependencies(
                hub.admit_action(ACTION, hub.build_registry())
            )
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "visit",
                    dict(
                        state={**state, "index": 1},
                        context=vars(hub.RunContext()),
                        repository_root=str(self.root),
                    ),
                )
            # A missing mount fails preflight without a child process.
            gone = self.root / "absent-root"
            failed = await execute(
                workflow,
                received,
                dict(
                    context=vars(hub.RunContext()),
                    repository_root=str(gone),
                    extra_args=[],
                    seen=[],
                ),
                remote,
                allow,
            )
            self.assertFalse(
                failed["outputs"]["result"]["ok"]
            )  # preflight failure remains data
            # Force loop exhaustion while keeping every native transition real.
            bounded = deepcopy(self.document)
            bounded["flow"]["steps"][2]["until"] = {"literal": False}
            exhausted = await run(doc=bounded)
            self.assertEqual(exhausted["status"], "failed", exhausted)
            self.assertIsNone(exhausted["outputs"])
            self.assertNotIn("finish", [c["operation"] for c in exhausted["calls"]])
            bounded = deepcopy(self.document)
            bounded["policy"]["limits"]["max_operation_calls"] = 3
            exhausted = await run(doc=bounded)
            self.assertEqual(exhausted["status"], "failed")
            self.assertIsNone(exhausted["outputs"])
            self.assertEqual(
                sum(
                    bool(c.get("transport_call_performed")) for c in exhausted["calls"]
                ),
                3,
            )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
