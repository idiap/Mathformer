#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real MCP + Lunar/PRISM over deterministic temporary repository fixtures.

The selected source constructs advisory prompts; it has no provider or external
compiler call. No production plan/prover/model is run. Generic hub compiler
boundary tests use an executable fixture, never replace a source step or PRISM.
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
from contextlib import asynccontextmanager, redirect_stdout
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
import yaml
import mathformer as hub
import generative_critic_tools as transport
from coherence_generative_alias_tools import ACTION
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lib_coherence_generative_critic_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/coherence-generative-alias.workflow.json"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
SOURCE = "skills/mathformerphysicslib/mathformerphysicslib-generative-coherence-critic/scripts/build_generative_coherence_critic_plan.py"
COMMON = "skills/mathformerphysicslib/mathformerphysicslib-coherence-inventory-builder/scripts/coherence_common.py"
CHILD = "mathformerphysicslib:generative-coherence-critic"
PREFIX = "mathformer_coherence_generative_alias_"
CONTEXT = vars(hub.RunContext(json_output=True))
SERVER_PYTHON = str(ROOT / ".venv/bin/python")
SERVER = """import sys
sys.dont_write_bytecode = True
sys.path.insert(0,'scripts')
from mcp_server import mcp
mcp.run(transport='stdio')
"""


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


native = load("generative_alias_native", ROOT / SOURCE)


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    paths = {SCHEMA, *(s["path"] for s in document["provenance"]["sources"])}
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(p, (ROOT / p).read_text()) for p in sorted(paths)
    ]


class Observed:
    def __init__(self, remote):
        self.remote, self.records = remote, []

    async def tools(self):
        return await self.remote.tools()

    async def call(self, name, arguments):
        output = await self.remote.call(name, arguments)
        self.records.append((name, deepcopy(arguments), deepcopy(output)))
        return output


class AliasTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="generative-alias-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        # Preflight checks the explicit mount. Algorithms run unchanged source,
        # and all repository reads/audits are against this synthetic context.
        for p in (SOURCE, COMMON):
            target = self.root / p
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / p, target)
        self.doc = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )

    def test_generator_provenance_and_native_source_semantics(self):
        self.assertEqual(
            self.doc["id"], "hub_physics_lib_coherence_generative_critic_workflow"
        )
        self.assertEqual(self.doc["aliases"], [ACTION])
        self.assertEqual(self.doc["lifecycle"], "active")
        self.assertEqual(
            self.doc["policy"]["limits"],
            dict(wall_time_seconds=3600, max_operation_calls=10),
        )
        self.assertEqual(
            self.doc["policy"]["failure"]["retry"],
            dict(max_attempts=1, retryable_codes=[]),
        )
        self.assertEqual(self.doc["flow"]["steps"][2]["max_iterations"], 1)
        self.assertIn(SOURCE, [s["path"] for s in self.doc["provenance"]["sources"]])
        for row in self.doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertEqual(json.loads((ROOT / AUTHORED).read_text()), self.doc)
        generator = load(
            "generative_alias_generator",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        self.assertEqual(
            [d for d in generator.inventory() if d["id"] == self.doc["id"]], [self.doc]
        )
        from mathformer_mcp_service import service_coverage_report

        registered = set(
            service_coverage_report(self.root / "unused.toml", {})["mcp_tools"]
        )
        self.assertTrue(
            {
                v["execution"]["binding"]["target"]
                for v in self.doc["operations"].values()
            }
            <= registered
        )
        # Reuse the leaf's meaningful original-CLI parity, assertion failure,
        # report loading, full-scan/12-item slicing, ordering and seven-probe tests.
        leaf_tests = load(
            "generative_alias_leaf_tests",
            ROOT / "tests/mcp/run_generative_critic_workflow_tests.py",
        )
        leaf_tests.GenerativeTests(
            "test_original_cli_and_full_scan_before_slice"
        ).test_original_cli_and_full_scan_before_slice()
        common = sys.modules["coherence_common"]
        summary = common.self_test_payload(self.root)
        self.assertNotIn("concept_occurrence_index", summary)
        self.assertEqual(common.canonicalize(summary)["concepts"], [])
        self.assertEqual(len(native.default_reports(True, self.root)), 4)

    def test_hub_state_and_external_compiler_boundary(self):
        registry = hub.build_registry()
        item = registry[ACTION]
        self.assertEqual(item.depends_on, (CHILD,))
        self.assertFalse(item.command)
        self.assertIsNone(registry[CHILD].timeout_seconds)
        admission = hub.admit_action(ACTION, registry, seen=["caller"])
        state = hub.initialize_dependencies(admission)
        before = deepcopy(state)
        for keep in (False, True):
            updated, done = hub.advance_dependencies(
                item,
                state,
                dict(ok=False, returncode=7),
                hub.RunContext(keep_going=keep),
            )
            self.assertEqual(state, before)
            self.assertTrue(done)
            self.assertEqual(
                updated,
                dict(
                    index=1,
                    children=[dict(ok=False, returncode=7)],
                    dependencies_ok=False,
                    ancestry=sorted(["caller", ACTION]),
                ),
            )
            self.assertFalse(
                hub.dependency_command_guard(
                    item, updated, hub.RunContext(keep_going=keep)
                )
            )
            self.assertEqual(
                hub.finish_dependencies(item, updated)["status"], "sequence_failed"
            )
        # Existing deterministic executable fixture substitutes only a generic
        # external compiler boundary; printed scientific ok never decides hub ok.
        compiler = ROOT / "tests/mcp/fixtures/coherence_canonicalize_alias_compiler.py"
        with patch.object(hub, "REPO_ROOT", self.root):
            for mode in ("success", "fail", "write"):
                (self.root / "undeclared.txt").unlink(missing_ok=True)
                registry[CHILD] = replace(
                    registry[CHILD], command=(hub.PYTHON_TOKEN, str(compiler), mode)
                )
                result = hub.run_action(ACTION, registry, hub.RunContext())
                child = result["children"][0]
                self.assertEqual(result["ok"], mode == "success")
                self.assertFalse(json.loads(child["stdout"])["ok"])
                self.assertEqual(child["returncode"], 7 if mode == "fail" else 0)
                self.assertIn("compiler fixture diagnostic", child["stderr"])
                if mode == "write":
                    self.assertEqual(
                        child["write_audit"]["unexpected_paths"], ["undeclared.txt"]
                    )
            (self.root / "undeclared.txt").unlink(missing_ok=True)
            registry[CHILD] = replace(
                registry[CHILD],
                command=(hub.PYTHON_TOKEN, str(compiler), "timeout"),
                timeout_seconds=1,
            )
            child = hub.run_action(ACTION, registry, hub.RunContext())["children"][0]
            self.assertEqual(child["status"], "timeout")
            self.assertFalse(child["ok"])
            self.assertTrue(child["write_audit"]["ok"])
            with self.assertRaises(FileNotFoundError):
                hub.launch_leaf_boundary(
                    registry[CHILD], dict(argv=[str(self.root / "absent")])
                )

    def test_native_transport_closed_and_mismatched_continuations(self):
        # Use real child IO, including source-owned traceback and nonzero exit.
        boundary = hub.prepare_leaf_boundary(
            hub.build_registry()[CHILD], hub.RunContext(), [], repository_root=self.root
        )
        boundary["repository_root"] = str(self.root)
        for acknowledgment in ("wrong-stage", None):
            child = transport.Child(boundary)
            try:
                self.assertEqual(
                    json.loads(child.read("reports")),
                    native.default_reports(True, self.root),
                )
                if acknowledgment is None:
                    child.process.stdin.close()
                    child.process.stdin = None
                else:
                    child.resume(acknowledgment)
                result = child.finish()
                self.assertEqual(result["returncode"], 1)
                self.assertEqual(result["stdout"], "")
                self.assertIn(
                    "staged child continuation was closed or mismatched",
                    result["stderr"],
                )
            finally:
                child.close()

    def test_registered_tools_lunar_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()

        @asynccontextmanager
        async def opened():
            error = None
            async with manager.open(
                "generative-alias",
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
            inventory = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile_doc(doc, tools=None):
                a = assets(doc)
                w = compile_workflow(
                    "mcp:generative-alias",
                    workflow_documents([DESCRIPTOR], a)[0],
                    inventory if tools is None else tools,
                )
                return w, a

            workflow, a = compile_doc(self.doc)
            self.assertTrue(workflow["runnable"], workflow["diagnostics"])
            self.assertTrue(workflow["runtime_source"])
            self.assertEqual(set(workflow["bindings"]), set(self.doc["operations"]))
            self.assertFalse(compile_doc(self.doc, [])[0]["runnable"])
            for name in ("reports", "plan", "advance"):
                self.assertFalse(
                    compile_doc(
                        self.doc, [t for t in inventory if t["name"] != PREFIX + name]
                    )[0]["runnable"]
                )

            async def allow():
                pass

            async def run(context=None, seen=None, args=None, doc=None):
                w, received = compile_doc(doc) if doc else (workflow, a)
                self.assertTrue(w["runnable"], w["diagnostics"])
                self.observed = Observed(remote)
                return await execute(
                    w,
                    received,
                    dict(
                        context=context or CONTEXT,
                        repository_root=str(self.root),
                        extra_args=args or [],
                        seen=seen or [],
                    ),
                    self.observed,
                    allow,
                )

            for dry, keep, seen, args in (
                (False, False, [], []),
                (True, True, [], []),
                (False, False, [ACTION], ["bad"]),
                (False, False, [], ["bad"]),
                (False, False, [CHILD], []),
                (False, True, [CHILD], []),
            ):
                context = {**CONTEXT, "dry_run": dry, "keep_going": keep}
                result = await run(context, seen, args)
                self.assertEqual(result["status"], "accepted", result)
                output = result["outputs"]["result"]
                ops = [r["operation"] for r in result["calls"]]
                rejected = seen == [ACTION] or bool(args)
                if rejected:
                    expected = hub.reject_action(
                        ACTION,
                        hub.admit_action(ACTION, hub.build_registry(), args, seen),
                    )
                    self.assertEqual(output, expected)
                    self.assertEqual(ops, ["admit", "reject", "carry", "carry"])
                else:
                    self.assertEqual(len(output["children"]), 1)
                    child = output["children"][0]
                    self.assertEqual(output["ok"], child["ok"])
                    self.assertEqual(
                        output["status"],
                        "sequence_completed" if child["ok"] else "sequence_failed",
                    )
                    updated = next(
                        v
                        for n, _, v in self.observed.records
                        if n == PREFIX + "advance"
                    )
                    self.assertTrue(updated["done"])
                    self.assertEqual(
                        updated["state"],
                        dict(
                            index=1,
                            children=[child],
                            dependencies_ok=child["ok"],
                            ancestry=sorted(set(seen) | {ACTION}),
                        ),
                    )
                    if dry or seen:
                        self.assertEqual(
                            ops,
                            [
                                "admit",
                                "initialize",
                                "prepare_child",
                                "skip_child",
                                "advance",
                                "finish",
                            ],
                        )
                        self.assertNotIn("stdout", child)
                        if dry:
                            self.assertEqual(child["status"], "dry_run")
                        else:
                            self.assertEqual(child["status"], "dependency_cycle")
                    else:
                        self.assertEqual(
                            ops,
                            [
                                "admit",
                                "initialize",
                                "prepare_child",
                                "reports",
                                "plan",
                                "complete_child",
                                "advance",
                                "finish",
                            ],
                        )
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            self.assertEqual(
                                native.main(
                                    ["--self-test", "--json"], repository_root=self.root
                                ),
                                0,
                            )
                        self.assertEqual(child["stdout"], stream.getvalue())
                        self.assertEqual(child["stderr"], "")
                        self.assertEqual(child["returncode"], 0)
                        self.assertTrue(child["write_audit"]["ok"])
                        reports = next(
                            v["stage"]
                            for n, _, v in self.observed.records
                            if n == PREFIX + "reports"
                        )
                        plan = next(
                            v["stage"]
                            for n, _, v in self.observed.records
                            if n == PREFIX + "plan"
                        )
                        self.assertEqual(
                            reports["state"]["token"], plan["state"]["token"]
                        )
                        self.assertEqual(
                            json.loads(reports["state"]["reports_json"]),
                            native.default_reports(True, self.root),
                        )
                        self.assertEqual(
                            json.loads(plan["state"]["plan_json"]),
                            json.loads(child["stdout"]),
                        )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
            # Preflight errors precede dry-run and produce no child process/audit.
            path = self.root / SOURCE
            saved = path.read_bytes()
            path.unlink()
            for dry in (False, True):
                result = await run({**CONTEXT, "dry_run": dry})
                child = result["outputs"]["result"]["children"][0]
                self.assertFalse(child["ok"])
                self.assertTrue(child["preflight_errors"])
                self.assertNotIn("write_audit", child)
                self.assertNotIn("reports", [r["operation"] for r in result["calls"]])
            path.write_bytes(saved)
            # Real filesystem failure aborts the child during default_reports;
            # planning is bypassed, and its nonzero output survives aggregation.
            common = sys.modules["coherence_common"]
            owner = next(
                c
                for c in common.canonicalize(common.self_test_inventory())["concepts"]
                if c["owner_module"]
            )
            blocker = self.root / owner["owner_module"]
            blocker.mkdir(parents=True)
            for keep in (False, True):
                failed = await run({**CONTEXT, "keep_going": keep})
                self.assertEqual(failed["status"], "accepted", failed)
                out = failed["outputs"]["result"]
                child = out["children"][0]
                self.assertFalse(out["ok"])
                self.assertEqual(out["status"], "sequence_failed")
                self.assertEqual(child["returncode"], 1)
                self.assertEqual(child["stdout"], "")
                self.assertIn("IsADirectoryError", child["stderr"])
                self.assertTrue(child["write_audit"]["ok"])
                self.assertEqual(
                    [r["operation"] for r in failed["calls"]],
                    [
                        "admit",
                        "initialize",
                        "prepare_child",
                        "reports",
                        "carry_stage",
                        "complete_child",
                        "advance",
                        "finish",
                    ],
                )
            shutil.rmtree(blocker)
            # Source plan is completed before the audit detects a real write.
            admission = (
                await remote.call(PREFIX + "admit", dict(extra_args=[], seen=[]))
            )["admission"]
            state = (
                await remote.call(PREFIX + "initialize", dict(admission=admission))
            )["state"]
            boundary = (
                await remote.call(
                    PREFIX + "prepare_child",
                    dict(state=state, context=CONTEXT, repository_root=str(self.root)),
                )
            )["boundary"]
            stage = (await remote.call(PREFIX + "reports", dict(boundary=boundary)))[
                "stage"
            ]
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "plan",
                    dict(
                        stage={
                            **stage,
                            "state": {**stage["state"], "reports_json": "[]"},
                        }
                    ),
                )
            stage = (await remote.call(PREFIX + "plan", dict(stage=stage)))["stage"]
            (self.root / "undeclared.txt").write_text("fixture write")
            audited = (
                await remote.call(
                    PREFIX + "complete_child", dict(stage=stage, boundary=boundary)
                )
            )["result"]
            self.assertEqual(audited["status"], "undeclared_writes")
            self.assertFalse(audited["ok"])
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "prepare_child",
                    dict(
                        state={**state, "index": 1},
                        context=CONTEXT,
                        repository_root=str(self.root),
                    ),
                )
            # Reduced call budget terminates without output; no hidden retry.
            bounded = deepcopy(self.doc)
            bounded["policy"]["limits"]["max_operation_calls"] = 7
            exhausted = await run(doc=bounded)
            self.assertEqual(exhausted["status"], "failed", exhausted)
            self.assertIsNone(exhausted["outputs"])
            self.assertEqual(
                sum(
                    bool(c.get("transport_call_performed")) for c in exhausted["calls"]
                ),
                7,
            )
            self.assertIn("budget", str(exhausted).lower())
            # Loop exhaustion is tested through real PRISM with the real native
            # transition; until=false deliberately declines its singleton stop.
            bounded = deepcopy(self.doc)
            bounded["flow"]["steps"][2]["until"] = {"literal": False}
            exhausted = await run(doc=bounded)
            self.assertEqual(exhausted["status"], "failed", exhausted)
            self.assertIsNone(exhausted["outputs"])
            self.assertNotIn("finish", [r["operation"] for r in exhausted["calls"]])
        self.assertFalse(manager.active)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
