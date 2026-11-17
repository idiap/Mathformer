#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline native verifier, actual MCP bindings, Lunar compiler and PRISM runtime.

Only the external PRISM subprocess/provider boundary is replaced. Its responses
are deterministic test evidence, never production semantic evidence.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(
        Path(os.environ.get("TO_PRISM_ROOT", LUNAR.parent / "abducer/abducer-prism"))
        / "src"
    ),
]
import asyncio
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import shutil
import tempfile
import threading
from types import SimpleNamespace
import unittest
import yaml
from prism_verification_tools import native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_prism_native_semantic_parallel_e2e_workflow/workflow.yaml"
PREFIX = "mathformer_prism_"


class CompilerProviderFixture:
    """External run/verify-run boundary, with native-shaped trace/effect records."""

    def __init__(self, synchronize=True):
        self.synchronize = synchronize
        self.outputs = []
        self.lock = threading.Lock()
        self.barrier = threading.Barrier(4, timeout=15)
        self.public_calls = 0
        self.calls = []

    def run(self, argv, **kwargs):
        project = Path(kwargs["cwd"])
        workflow_id = project.parent.name
        mode_path = project.parents[2] / "boundary-mode.json"
        mode = json.loads(mode_path.read_text()) if mode_path.exists() else {}
        with self.lock:
            self.calls.append((workflow_id, argv[1], argv[2]))
        if argv[1] == "verify-run":
            return SimpleNamespace(
                returncode=int(mode.get("offline_fail", False)),
                stdout="",
                stderr="fixture offline rejection",
            )
        self.outputs.append(Path(argv[argv.index("--output") + 1]))
        assert argv[1] == "run" and argv[3:5] == ["--handler", "codex"]
        workflow = json.loads(
            (project.parent / "conversion/workflow-architecture-plan.json").read_text()
        )["workflows"][0]
        public = argv[2] == "main.prism"
        if public:
            with self.lock:
                self.public_calls += 1
                index = self.public_calls
            if index <= 4 and self.synchronize:
                self.barrier.wait()
        if mode.get("run_fail") == workflow_id:
            return SimpleNamespace(
                returncode=1, stdout="", stderr="fixture provider failure"
            )
        projection = workflow["reasoning_projection"]
        ids = (
            [
                i
                for node in projection["topology"]
                for i in (node["parallel"] if isinstance(node, dict) else [node])
            ]
            if public
            else [s["id"] for s in workflow["steps"]]
        )
        count = (
            len(ids)
            if public
            else sum(s["semantic_role"] == "epistemic" for s in workflow["steps"])
        )
        operational = 0 if public else len(ids) - count
        trace = [{"kind": "workflow-node", "name": i} for i in ids]
        trace += [
            {"kind": "agent-invoked", "metadata": {"skills": ["fixture-owner"]}}
            for _ in range(count)
        ]
        trace += [{"kind": "deterministic-computation"} for _ in range(operational)]
        records = {}
        for index in range(count):
            key = f"fixture-{index}"
            records[key] = {
                "invocation": {
                    "handler": "codex",
                    "symbol": "generate",
                    "call_id": key,
                    "input_digest": "fixture-input",
                },
                "observation": {
                    "status": "accepted",
                    "output_digest": "fixture-output",
                    "provenance": {"provider": "codex", "synthetic": False},
                },
            }
            trace.append({"kind": "effect", "metadata": {"record": key}})
        if mode.get("duplicate_calls") and count > 1:
            records["fixture-1"]["invocation"]["call_id"] = "fixture-0"
        fields = {
            "status": "blocked_fixture",
            "blockers": ["fixture: unresolved evidence"],
            "limitations": [],
            "promoted_modules": [],
        }
        if mode.get("promote"):
            fields["promoted_modules"] = ["unsafe-fixture"]
        payload = {
            "status": "accepted",
            "trace": trace,
            "effect_records": records,
            "result": {
                "value": {
                    "producer": "codex:deterministic-test-fixture",
                    "value": {
                        "type_name": (
                            projection["output_type"]
                            if public
                            else workflow["output"]["type"]
                        ),
                        "fields": fields,
                    },
                }
            },
        }
        Path(argv[argv.index("--output") + 1]).write_text(json.dumps(payload))
        return SimpleNamespace(returncode=0, stdout="", stderr="")


def fixture(base):
    root = base / "mathformer-prism"
    root.mkdir()
    shutil.copytree(ROOT / "mathformer-prism/projects", root / "projects")
    shutil.copy(ROOT / "mathformer-prism/skill_dispositions.json", root)
    catalog = json.loads((ROOT / "mathformer-prism/workflow_catalog.json").read_text())
    fingerprint = "sha256:" + native.digest_sources()
    catalog["source_fingerprint"] = fingerprint
    (root / "workflow_catalog.json").write_text(json.dumps(catalog))
    for entry in catalog["workflows"]:
        path = root / entry["semantic_taxonomy"]
        taxonomy = json.loads(path.read_text())
        taxonomy["source_fingerprint"] = fingerprint
        path.write_text(json.dumps(taxonomy))
    return root


def oracle():
    loader = SourceFileLoader(
        "original_parallel_verifier",
        str(ROOT / "tests/mcp/fixtures/prism_verification_original.py.txt"),
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    module.REPOSITORY = ROOT
    module.PROJECTION_SPECS = native.PROJECTION_SPECS
    module.SEMANTIC_SOURCES = native.SEMANTIC_SOURCES
    return module


def snapshot(doc):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in doc["provenance"]["sources"]
    ]


def stable(report):
    report = deepcopy(report)
    for row in report["workflows"]:
        row.pop("run_started_ns")
        row.pop("run_ended_ns")
    return report


class VerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="prism-verifier-fixture-", dir=base
        )
        cls.base = Path(cls.temporary.name)
        cls.root = fixture(cls.base)
        cls.output = cls.root / "tests/native-semantic-parallel-e2e.json"

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_source_equivalence_and_runtime_failures(self):
        (self.root / "boundary-mode.json").unlink(missing_ok=True)
        original = oracle()
        reports = []
        for module in (original, native):
            boundary = CompilerProviderFixture()
            module.subprocess = SimpleNamespace(run=boundary.run)
            reports.append(
                module.verify(
                    self.root, "unused-fixture-compiler", 4, self.output, "codex"
                )
            )
            self.assertEqual(len(boundary.calls), 56)
        self.assertEqual(stable(reports[0]), stable(reports[1]))
        self.assertEqual(reports[1]["workflow_count"], 14)
        self.assertTrue(reports[1]["actual_run_overlap"])
        self.assertEqual(len(reports[1]["negative_controls"]), 4)
        mode = self.root / "boundary-mode.json"
        for options, message in [
            ({"run_fail": "control_validation_loop"}, "fixture provider failure"),
            ({"offline_fail": True}, "offline verification failed"),
            ({"duplicate_calls": True}, "duplicate or missing native call ids"),
            ({"promote": True}, "populated"),
        ]:
            mode.write_text(json.dumps(options))
            self.output.unlink(missing_ok=True)
            boundary = CompilerProviderFixture()
            native.subprocess = SimpleNamespace(run=boundary.run)
            with self.assertRaisesRegex(native.VerificationError, message):
                native.verify(self.root, "unused", 4, self.output, "codex")
            self.assertEqual(
                boundary.public_calls, 14
            )  # no fail-fast while joining futures
            self.assertFalse(self.output.exists())
            self.assertTrue(all(not path.parent.exists() for path in boundary.outputs))
        mode.unlink()
        # Selection restricts runtime only: all static entries are still checked.
        bad = (
            self.root
            / json.loads((self.root / "workflow_catalog.json").read_text())[
                "workflows"
            ][-1]["semantic_taxonomy"]
        )
        before = bad.read_text()
        value = json.loads(before)
        value["review_status"] = "pending"
        bad.write_text(json.dumps(value))
        boundary = CompilerProviderFixture()
        native.subprocess = SimpleNamespace(run=boundary.run)
        with self.assertRaisesRegex(native.VerificationError, "taxonomy not approved"):
            native.verify(
                self.root,
                "unused",
                4,
                self.output,
                "codex",
                {"control_validation_loop"},
            )
        self.assertFalse(boundary.calls)
        bad.write_text(before)
        with self.assertRaisesRegex(
            native.VerificationError, "unknown selected workflows"
        ):
            native.verify(self.root, "unused", 4, self.output, "codex", {"missing"})

    def test_worker_bounds_selection_and_finalization_gates(self):
        (self.root / "boundary-mode.json").unlink(missing_ok=True)
        for jobs, workers in [(0, 1), (99, 4)]:
            boundary = CompilerProviderFixture(synchronize=False)
            native.subprocess = SimpleNamespace(run=boundary.run)
            session = native.VerificationSession(
                self.root,
                "unused",
                jobs,
                self.output,
                "codex",
                {"control_validation_loop"},
            )
            self.assertEqual(session.cursor, 0)
            for index in range(14):
                self.assertEqual(session.validate_entry(), index == 13)
            self.assertEqual(session.cursor, 14)
            session.prepare_runtime()
            try:
                self.assertEqual(session.executor._max_workers, workers)
                self.assertEqual(len(session.futures), 1)
                self.assertTrue(session.await_entry())
                self.assertEqual(session.cursor, 1)
                session.finish_runtime()
                self.assertIsNone(session.resources)
                self.assertFalse(session.temporary.exists())
                self.output.unlink(missing_ok=True)
                before = session.before
                session.before = "stale"
                with self.assertRaisesRegex(
                    native.VerificationError, "canonical semantic sources changed"
                ):
                    session.write_report()
                session.before = before
                skills = session.skills_before
                session.skills_before = "stale"
                with self.assertRaisesRegex(
                    native.VerificationError, "canonical skill sources changed"
                ):
                    session.write_report()
                session.skills_before = skills
                self.assertFalse(self.output.exists())
                report = session.write_report()
                self.assertEqual(
                    report["runtime_selection"], ["control_validation_loop"]
                )
                self.assertEqual(report["catalog_workflow_count"], 14)
                self.assertEqual(report["jobs"], 1)
                self.assertFalse(
                    report["actual_run_overlap"]
                )  # single run is permitted
                session.results = [
                    dict(session.results[0], run_started_ns=1, run_ended_ns=2),
                    dict(session.results[0], run_started_ns=2, run_ended_ns=3),
                ]
                self.output.unlink()
                with self.assertRaisesRegex(
                    native.VerificationError, "did not observe overlapping"
                ):
                    session.write_report()
                self.assertFalse(self.output.exists())
            finally:
                session.close()

    def test_registered_mcp_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["lifecycle"], "active")
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        failure = None
        server = str(Path(__file__).resolve())
        async with manager.open(
            "verifier",
            StdioConfig(
                command=sys.executable, args=[server, "--fixture-server"], cwd=str(ROOT)
            ),
            {"LUNAR_PLATFORM_ROOT": str(LUNAR)},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(document, inventory=tools):
                    assets = snapshot(document)
                    c = compile_workflow(
                        "mcp:verifier",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        inventory,
                    )
                    return c, assets

                compiled, assets = compile(doc)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
                self.assertFalse(compile(doc, [])[0]["runnable"])
                config = {
                    "root": "mathformer-prism",
                    "prism_bin": "unused-fixture-compiler",
                    "jobs": 4,
                    "handler": "codex",
                    "report_path": "mathformer-prism/tests/native-semantic-parallel-e2e.json",
                    "selected_workflows": None,
                }
                inputs = {
                    "config": config,
                    "context": {"working_directory": str(self.base)},
                }

                async def authorize():
                    pass

                async def run(document=doc, values=inputs):
                    c, a = compile(document)
                    return await execute(c, a, values, remote, authorize)

                result = await run()
                self.assertEqual(
                    result["status"],
                    "accepted",
                    {k: result.get(k) for k in ("status", "diagnostics", "calls")},
                )
                report = result["outputs"]["report"]
                self.assertEqual(report, json.loads(self.output.read_text()))
                self.assertEqual(report["workflow_count"], 14)
                self.assertTrue(report["actual_run_overlap"])
                expected = (
                    ["initialize"]
                    + ["validate_entry"] * 14
                    + ["prepare_runtime"]
                    + ["await_entry"] * 14
                    + ["finish_runtime", "write_report"]
                )
                self.assertEqual(
                    [c["tool"] for c in result["calls"]], [PREFIX + s for s in expected]
                )
                self.assertEqual(len(result["calls"]), 32)
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
                for which, index in [("catalog", 1), ("await_all", 3)]:
                    bounded = deepcopy(doc)
                    bounded["flow"]["steps"][index]["max_iterations"] = 13
                    self.output.unlink(missing_ok=True)
                    failed = await run(bounded)
                    self.assertEqual(failed["status"], "failed")
                    self.assertFalse(self.output.exists())
                    self.assertIn("exhaust", str(failed).lower())
                    # Runtime exhaustion is outside a source call; the client
                    # explicitly closes the process-local capability it received.
                    tokens = set()

                    def find_states(value):
                        if isinstance(value, dict):
                            if "session_id" in value:
                                tokens.add(value["session_id"])
                            for child in value.values():
                                find_states(child)
                        elif isinstance(value, list):
                            for child in value:
                                find_states(child)
                        elif (
                            isinstance(value, str)
                            and value.startswith("{")
                            and "session_id" in value
                        ):
                            try:
                                parsed = json.loads(value)
                            except ValueError:
                                return
                            find_states(parsed)

                    find_states(failed["replay_artifacts"])
                    self.assertTrue(tokens)
                    for token in tokens:
                        closed = await remote.call(
                            PREFIX + "close", {"state": {"session_id": token}}
                        )
                        self.assertTrue(closed["closed"])
                mode = self.root / "boundary-mode.json"
                mode.write_text(json.dumps({"run_fail": "control_validation_loop"}))
                failed = await run()
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(
                    [c["tool"] for c in failed["calls"]],
                    [PREFIX + s for s in expected[:-1]],
                )
                self.assertEqual(failed["calls"][-1]["status"], "rejected")
                self.assertFalse(self.output.exists())
                mode.unlink()
                # Exact state tokens prohibit replay and out-of-order execution.
                state = (await remote.call(PREFIX + "initialize", inputs))["state"]
                state2 = (
                    await remote.call(PREFIX + "validate_entry", {"state": state})
                )["state"]
                self.assertEqual(state2["cursor"], 1)
                with self.assertRaises(Exception):
                    await remote.call(PREFIX + "prepare_runtime", {"state": state2})
                with self.assertRaises(Exception):
                    await remote.call(PREFIX + "validate_entry", {"state": state})
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    if "--fixture-server" in sys.argv:
        # Patch only the external compiler/provider subprocess boundary before
        # importing the real production MCP registrations. No config/credentials.
        native.subprocess = SimpleNamespace(run=CompilerProviderFixture().run)
        from mcp.server.fastmcp import FastMCP
        from prism_verification_tools import register_prism_verification_tools

        mcp = FastMCP("offline parallel verifier fixture")
        register_prism_verification_tools(mcp)
        mcp.run(transport="stdio")
    else:
        unittest.main(verbosity=2)
