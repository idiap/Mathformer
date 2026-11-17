#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native fixture files, registered MCP bindings and real Lunar/PRISM execution.

The selected alias has no provider or external compiler calls. Its native Python
child runs byte-identical source over a temporary repository, never production
artifacts. Only the separate generic hub tests use an external compiler fixture.
No PRISM parser, checker, compiler, runtime or source step is substituted.
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
from api_critic_tools import source
from coherence_api_alias_tools import ACTION
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lib_coherence_api_critic_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
AUTHORED = "skills/control/workflow-contract-validator/references/coherence-api-alias.workflow.json"
CHILD = "mathformerphysicslib:api-operability-critic"
SCRIPT = "skills/mathformerphysicslib/mathformerphysicslib-api-operability-critic/scripts/critic_api_operability.py"
COMMON = "skills/mathformerphysicslib/mathformerphysicslib-coherence-inventory-builder/scripts/coherence_common.py"
OWNER = "libraries/MathformerPhysicsLib/Lean/Foundations/Fields.lean"
PREFIX = "mathformer_coherence_api_alias_"
SERVER_PYTHON = (
    str(ROOT / ".venv/bin/python")
    if (ROOT / ".venv/bin/python").exists()
    else sys.executable
)
SERVER = """import os, sys
from pathlib import Path
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, 'scripts')
import mcp_server as server
server.hub.REPO_ROOT = Path(sys.argv[1])
server.CALL_LOG_PATH = server.hub.REPO_ROOT / 'artifacts/mcp/calls.jsonl'
server.mcp.run(transport='stdio')
"""


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    paths = dict.fromkeys(
        [SCHEMA, *(r["path"] for r in document["provenance"]["sources"])]
    )
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(p, (ROOT / p).read_text()) for p in paths
    ]


def original():
    namespace = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/coherence_api_alias_original.py.txt").read_text(),
        namespace,
    )
    return namespace["run_action"]


class AliasTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="coherence-api-alias-")
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
        owner = self.root / OWNER
        owner.parent.mkdir(parents=True, exist_ok=True)
        owner.write_text("EuclideanSpace Fin component proj\n")

    def test_contract_generator_provenance_and_registration(self):
        doc = self.document
        self.assertEqual(doc["id"], "hub_physics_lib_coherence_api_critic_workflow")
        self.assertEqual(doc["aliases"], [ACTION])
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(
            doc["policy"]["limits"], dict(wall_time_seconds=3600, max_operation_calls=5)
        )
        self.assertEqual(
            doc["policy"]["failure"]["retry"], dict(max_attempts=1, retryable_codes=[])
        )
        self.assertEqual(doc["flow"]["steps"][2]["max_iterations"], 1)
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
        spec = importlib.util.spec_from_file_location("api_alias_generator", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual([d for d in module.inventory() if d["id"] == doc["id"]], [doc])
        # Service discovery does not load configuration, credentials or a provider.
        from mathformer_mcp_service import service_coverage_report

        advertised = service_coverage_report(self.root / "unused.toml", {})["mcp_tools"]
        self.assertTrue(
            {
                PREFIX + s
                for s in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            }
            <= set(advertised)
        )

    def test_native_controller_parity_and_state(self):
        with patch.object(hub, "REPO_ROOT", self.root):
            oracle = original()
            registry = hub.build_registry()
            self.assertEqual(registry[ACTION].command, ())
            self.assertEqual(registry[ACTION].depends_on, (CHILD,))
            self.assertIsNone(registry[CHILD].timeout_seconds)
            for keep in (False, True):
                for dry in (False, True):
                    context = hub.RunContext(dry_run=dry, keep_going=keep)
                    for seen, args in (
                        ([], []),
                        ([ACTION], ["invalid"]),
                        ([CHILD], []),
                        ([], ["invalid"]),
                        (["caller"], []),
                    ):
                        self.assertEqual(
                            hub.run_action(
                                ACTION,
                                registry,
                                context,
                                seen=set(seen),
                                extra_args=args,
                            ),
                            oracle(
                                ACTION,
                                registry,
                                context,
                                seen=set(seen),
                                extra_args=args,
                            ),
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
            for keep in (False, True):
                admission = hub.admit_action(ACTION, registry, seen=["caller"])
                state = hub.initialize_dependencies(admission)
                before = deepcopy(state)
                child = {
                    "ok": False,
                    "stdout": '{"ok":true}',
                    "status": "completed",
                    "returncode": 7,
                }
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
                self.assertTrue(done)  # singleton stops even with keep_going
                self.assertFalse(
                    hub.dependency_command_guard(
                        registry[ACTION], advanced, hub.RunContext(keep_going=keep)
                    )
                )
                self.assertEqual(
                    hub.finish_dependencies(registry[ACTION], advanced)["status"],
                    "sequence_failed",
                )

    def test_actual_critic_semantics_and_uncapped_scan(self):
        native = source()
        owner = self.root / OWNER
        owner.write_text("Alpha BETA")

        def concept(terms, path=OWNER):
            return dict(owner_module=path, api_terms=terms)

        graph = {
            "concepts": [
                concept(["missing"], None),
                concept(["missing"], "Other"),
                concept([]),
                concept(["missing"], "Foundations/absent"),
                concept(["ALPHA", "missing"]),
                concept(["beta"]),
                concept(["alpha", "beta"]),
            ]
        }
        report = native.critic_api(graph, self.root)
        self.assertEqual([r["severity"] for r in report["findings"]], ["high", "low"])
        self.assertFalse(report["ok"])
        self.assertEqual(report["findings"][1]["present_terms"], ["ALPHA"])
        # No specialization's 1024-concept limit leaks into the native alias.
        large = {
            "concepts": [concept(["missing"])] * 1025 + [concept(["alpha", "missing"])]
        }
        report = native.critic_api(large, self.root)
        self.assertEqual(report["finding_count"], 1026)
        self.assertEqual(report["findings"][-1]["severity"], "low")
        payload = native.self_test_payload(self.root)
        self.assertNotIn("concept_occurrence_index", payload)
        self.assertEqual(native.canonicalize(payload)["concepts"], [])
        self.assertEqual(
            native.critic_api(native.canonicalize(payload), self.root)["finding_count"],
            0,
        )
        with self.assertRaises(IsADirectoryError):
            native.critic_api(
                {
                    "concepts": [
                        concept(
                            ["x"], "libraries/MathformerPhysicsLib/Lean/Foundations"
                        )
                    ]
                },
                self.root,
            )

    def test_generic_native_external_compiler_failures_and_audit(self):
        compiler = ROOT / "tests/mcp/fixtures/coherence_api_alias_compiler.py"
        with patch.object(hub, "REPO_ROOT", self.root):
            oracle = original()
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
                self.assertFalse(
                    json.loads(child["stdout"])["ok"]
                )  # printed ok is never parsed
                self.assertEqual(child["returncode"], 7 if mode == "fail" else 0)
                self.assertIn("compiler fixture diagnostic", child["stderr"])
                if mode == "write":
                    self.assertEqual(child["status"], "undeclared_writes")
                    self.assertEqual(
                        child["write_audit"]["unexpected_paths"], ["undeclared.txt"]
                    )
            with self.assertRaises(FileNotFoundError):
                hub.launch_leaf_boundary(
                    hub.build_registry()[CHILD],
                    {"argv": [str(self.root / "absent-executable")]},
                )

    def test_registered_mcp_lunar_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        config = StdioConfig(
            command=SERVER_PYTHON,
            args=["-B", "-c", SERVER, str(self.root)],
            cwd=str(ROOT),
        )

        @asynccontextmanager
        async def opened():
            failure = None
            async with manager.open("api-alias", config, {}) as remote:
                try:
                    yield remote
                except Exception as exc:
                    failure = exc
            if failure:
                raise failure

        async with opened() as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile_doc(doc, inventory=None):
                assets = snapshot(doc)
                selected = workflow_documents([DESCRIPTOR], assets)[0]
                return (
                    compile_workflow(
                        "mcp:api-alias",
                        selected,
                        tools if inventory is None else inventory,
                    ),
                    assets,
                )

            workflow, assets = compile_doc(self.document)
            self.assertTrue(workflow["runnable"], workflow["diagnostics"])
            self.assertTrue(workflow["runtime_source"])
            self.assertEqual(
                set(workflow["bindings"]), set(self.document["operations"])
            )
            self.assertFalse(compile_doc(self.document, [])[0]["runnable"])

            async def allow():
                pass

            async def run(context=None, seen=None, args=None, doc=None):
                w, a = compile_doc(doc) if doc else (workflow, assets)
                self.assertTrue(w["runnable"], w["diagnostics"])
                inputs = dict(
                    context=vars(context or hub.RunContext()),
                    extra_args=args or [],
                    seen=seen or [],
                )
                return await execute(w, a, inputs, remote, allow)

            # End-to-end exact native envelope comparison, including diagnostics/audit.
            with (
                patch.object(hub, "REPO_ROOT", self.root),
                patch.object(sys, "executable", SERVER_PYTHON),
            ):
                oracle = original()
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
                    operations = [c["operation"] for c in result["calls"]]
                    rejected = seen == [ACTION] or bool(args)
                    self.assertEqual(
                        operations,
                        (
                            ["admit", "reject", "carry", "carry"]
                            if rejected
                            else ["admit", "initialize", "visit", "advance", "finish"]
                        ),
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    if not dry and not seen and not args:
                        child = expected["children"][0]
                        self.assertEqual(
                            child["argv"][1:], [SCRIPT, "--self-test", "--json"]
                        )
                        self.assertEqual(child["returncode"], 0)
                        self.assertEqual(json.loads(child["stdout"])["findings"], [])
                        self.assertTrue(child["write_audit"]["ok"])
                # Native missing path preflight precedes successful dry-run return.
                script = self.root / SCRIPT
                saved = script.read_bytes()
                script.unlink()
                for dry in (False, True):
                    result = await run(hub.RunContext(dry_run=dry))
                    child = result["outputs"]["result"]["children"][0]
                    self.assertFalse(child["ok"])
                    self.assertNotIn("status", child)
                    self.assertEqual(
                        child["preflight_errors"], ["missing required path: " + SCRIPT]
                    )
                    self.assertNotIn("returncode", child)
                script.write_bytes(saved)
                # A native read failure becomes subprocess failure data, not a graph exception.
                owner = self.root / OWNER
                owner.unlink()
                owner.mkdir()
                for keep in (False, True):
                    context = hub.RunContext(keep_going=keep)
                    expected = oracle(ACTION, hub.build_registry(), context)
                    result = await run(context)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"result": expected})
                    child = expected["children"][0]
                    self.assertFalse(expected["ok"])
                    self.assertEqual(len(expected["children"]), 1)
                    self.assertNotEqual(child["returncode"], 0)
                    self.assertIn("IsADirectoryError", child["stderr"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["admit", "initialize", "visit", "advance", "finish"],
                    )
                owner.rmdir()
                owner.write_text("Fin EuclideanSpace component proj")
            # The actual singleton exits at its bound; exhaustion is unreachable.
            # Force only the contract exit predicate false to test host exhaustion.
            bounded = deepcopy(self.document)
            bounded["flow"]["steps"][2]["until"] = {"literal": False}
            result = await run(hub.RunContext(dry_run=True), doc=bounded)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(result["failure_disposition"], "fail")
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                [c["operation"] for c in result["calls"]],
                ["admit", "initialize", "visit", "advance"],
            )
            budget = deepcopy(self.document)
            budget["policy"]["limits"]["max_operation_calls"] = 2
            result = await run(hub.RunContext(dry_run=True), doc=budget)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertIn("budget", json.dumps(result).lower())
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 2
            )
            invalid = dict(
                index=1, children=[], dependencies_ok=True, ancestry=[ACTION]
            )
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "visit",
                    dict(state=invalid, context=vars(hub.RunContext(dry_run=True))),
                )
            # Runtime errors must propagate through real tool transport too.
            thrown = deepcopy(self.document)
            thrown["flow"]["steps"][1]["cases"][0]["body"]["steps"][0]["arguments"][
                "admission"
            ] = {"literal": {"accepted": True, "status": "accepted", "ancestry": []}}
            # Direct signatures are covered above; use a valid contract with an
            # exhausted initial cursor to reach the registered visit's exception.
            body = thrown["flow"]["steps"][1]["cases"][0]["body"]
            body["outputs"]["state"]["value"] = {"literal": invalid}
            result = await run(hub.RunContext(dry_run=True), doc=thrown)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(
                [c["operation"] for c in result["calls"]],
                ["admit", "initialize", "visit"],
            )
            self.assertIsNone(result["outputs"])
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
