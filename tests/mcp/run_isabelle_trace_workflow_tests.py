#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline source equivalence and registered MCP/Lunar compiler execution tests."""

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
    str(Path(__file__).parent / "fixtures"),
]
import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import json
import shutil
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
import yaml
from isabelle_trace_workflow_tools import load_runtime, register_isabelle_trace_tools
from isabelle_trace_boundaries import Boundaries
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

ID = "isabelle_physics_derivation_trace_loop"
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/loop/loop_isabelle_physics_derivation_trace_loop_workflow/workflow.yaml"


def exporter():
    spec = importlib.util.spec_from_file_location(
        "exporter_fixture", ROOT / "scripts/prism/export_mathformer_lunar.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def package(root):
    e = exporter()
    source = ROOT / "mathformer-prism/projects" / ID
    target = root / "project"
    shutil.copytree(source, target)
    prism = target / "prism_project"
    body, api = e.reasoning_materialization(source)
    (prism / "reasoning_materialization.prism").write_bytes(body)
    (prism / "reasoning_api.prism").write_bytes(api)
    (prism / "native_execution.prism").write_text(e.ISABELLE_EXECUTION_SOURCE)
    catalog = json.loads((ROOT / "mathformer-prism/workflow_catalog.json").read_text())
    workflow = next(w for w in catalog["workflows"] if w["id"] == ID)
    c = e.reasoning_contract(source, workflow)
    (prism / "material_main.prism").write_bytes(e.runnable_reasoning_main(workflow, c))
    return dict(
        argument=c["argument"],
        schema=c["schema"],
        workflow_fields=c["workflow_fields"],
        backend="isabelle",
        reasoning_workflow="ReconstructInIsabelle",
        entry_file="project/prism_project/material_main.prism",
        native_entry_file="project/prism_project/native_execution.prism",
    )


def prepared(root, contract):
    root.mkdir()
    values = deepcopy(exporter().PLAUSIBLE_INPUTS[ID])
    # Use the actual prepare hook, including its input validation and request digest.
    runtime = load_runtime()
    runtime.__file__ = str(root / "runtime.py")
    (root / "workflow-inputs.json").write_text(json.dumps({ID: contract}))
    return runtime.prepare(workflow_id=ID, inputs=values, run_root=root)["state"]


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in document["provenance"]["sources"]
    ]


def original_runtime():
    # Frozen exporter source, captured before the shared-step extraction.
    path = Path(__file__).parent / "fixtures/isabelle_trace_original.py.txt"
    import ast

    tree = ast.parse(path.read_text())
    source = next(
        ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "RUNTIME_SOURCE" for t in n.targets)
    )
    module = ModuleType("isabelle_trace_original")
    module.__file__ = str(ROOT / "scripts/prism/mathformer_lunar_runtime.py")
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


class IsabelleTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        cls.temporary = tempfile.TemporaryDirectory(prefix="isabelle-trace-fixture-")
        cls.base = Path(cls.temporary.name)
        cls.contract = package(cls.base)
        cls.counter = 0
        partial = cls.base / "project/prism_project/partial.prism"
        partial.write_text(
            """from isabelle_physics_derivation_trace_loop import PhysicsIsabelleDerivationRequest, IsabelleTheory

def draft(request: PhysicsIsabelleDerivationRequest, model: Model, access: ModelGenerate) -> Result[Generated[IsabelleTheory], ModelFailure] ! {AI.Generate}:
    return generate[IsabelleTheory](request, model, access)

workflow partial_graph(request: PhysicsIsabelleDerivationRequest, model: Model, access: ModelGenerate) -> Generated[IsabelleTheory]
    fails ModelFailure
    ! {AI.Generate}:
    [theory: draft(request, model, access)]
    return theory

def main(workflow_source: PhysicsIsabelleDerivationRequest, model: Model, access: ModelGenerate) -> Result[Generated[IsabelleTheory], ModelFailure] ! {AI.Generate}:
    return solve partial_graph(workflow_source, model, access)
"""
        )
        (partial.parent / "no_steps.prism").write_text(
            """from isabelle_physics_derivation_trace_loop import PhysicsIsabelleDerivationRequest, IsabelleTheory

def main(workflow_source: PhysicsIsabelleDerivationRequest, model: Model, access: ModelGenerate) -> Result[Generated[IsabelleTheory], ModelFailure] ! {AI.Generate}:
    return generate[IsabelleTheory](workflow_source, model, access)
"""
        )
        for row in cls.document["provenance"]["sources"]:
            if "digest" in row:
                assert (
                    row["digest"]
                    == "sha256:"
                    + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest()
                ), row["path"]

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def state(self):
        type(self).counter += 1
        return prepared(self.base / ("run-" + str(self.counter)), self.contract)

    def test_original_entrypoint_equivalence_and_bounds(self):
        for options, expected in [
            ({"outcomes": [0]}, 1),
            ({"outcomes": [1, 0]}, 2),
            ({"outcomes": [1, 1, 0]}, 3),
            ({"outcomes": [1, 1, 1]}, 3),
            ({"outcomes": ["timeout", 0]}, 2),
            ({"outcomes": [1], "reject_repair": True}, 3),
        ]:
            results = []
            for module in (original_runtime(), load_runtime()):
                state = self.state()
                boundary = Boundaries(self.base, options)
                boundary.install(module)
                # Original entrypoint imports its host compiler channel by name.
                old = sys.modules.get("prism_engine")
                sys.modules["prism_engine"] = SimpleNamespace(
                    execute_prism=boundary.execute_prism
                )
                try:
                    execution = module.execute(
                        state=state, services=boundary.services()
                    )
                finally:
                    if old is None:
                        sys.modules.pop("prism_engine", None)
                    else:
                        sys.modules["prism_engine"] = old
                report = module.verify(state=state, execution=execution)
                self.assertEqual(len(execution.receipts), expected)
                self.assertEqual(len(boundary.executions), expected)
                self.assertGreaterEqual(len(execution.completed_steps), 10)
                self.assertGreaterEqual(execution.reasoning_event_count, 20)
                self.assertEqual(
                    execution.reasoning_event_count,
                    len([p for k, p in boundary.events if k == "reasoning"]),
                )
                self.assertFalse(
                    report["result"]["analysis_results"]["repository_promotion"]
                )
                steps = [
                    (p["reasoning_step"]["name"], p["status"])
                    for k, p in boundary.events
                    if k == "reasoning" and p.get("reasoning_step")
                ]

                def position(name, status):
                    return steps.index((name, status))

                for before, after in [
                    ("source_model", "formalization_packet"),
                    ("source_model", "physical_model"),
                    ("formalization_packet", "isabelle_plan"),
                    ("physical_model", "isabelle_plan"),
                    ("isabelle_plan", "theory"),
                    ("theory", "session_report"),
                    ("session_report", "math_review"),
                    ("theory", "physics_review"),
                    ("math_review", "process_review"),
                    ("physics_review", "process_review"),
                    ("process_review", "report"),
                ]:
                    self.assertLess(
                        position(before, "completed"), position(after, "running")
                    )
                self.assertEqual(boundary.executions[0]["input"], state["prepared"])

                for i, r in enumerate(execution.receipts, 1):
                    saved = json.loads(
                        (
                            Path(state["run_root"]) / f"attempt-{i}/receipt.json"
                        ).read_text()
                    )
                    self.assertEqual(saved, r)
                    self.assertEqual(
                        r["request_digest"], state["prepared"]["request_digest"]
                    )
                    self.assertEqual(
                        r["source_sha256"],
                        hashlib.sha256(
                            (
                                Path(state["run_root"])
                                / f"attempt-{i}"
                                / r["source_file"]
                            ).read_bytes()
                        ).hexdigest(),
                    )
                for index, call in enumerate(boundary.executions[1:], 1):
                    request = call["input"]["value"]
                    self.assertEqual(
                        json.loads(request["specification"]), state["workflow_inputs"]
                    )
                    self.assertIn(
                        "without changing the requested theorem or dropping source assumptions",
                        request["instructions"],
                    )
                    previous = json.loads(request["previous_diagnostics"])
                    self.assertEqual(
                        previous["execution"], execution.receipts[index - 1]
                    )
                    self.assertEqual(
                        previous["previous_code"],
                        (
                            Path(state["run_root"])
                            / f"attempt-{index}"
                            / execution.receipts[index - 1]["source_file"]
                        ).read_text(),
                    )
                if "timeout" in options["outcomes"]:
                    self.assertEqual(boundary.killed, [(78231, 9)])
                    self.assertTrue(execution.receipts[0]["timed_out"])
                self.assertTrue(
                    all(
                        p["waits"][0] == (60 if p["version"] else 180)
                        for p in boundary.processes
                    )
                )
                # Strip only run-location data and unique PRISM evidence IDs.
                result = deepcopy(report["result"]["analysis_results"])
                results.append(
                    (
                        result,
                        [r["status"] for r in execution.receipts],
                        len(boundary.model_calls),
                    )
                )
            self.assertEqual(results[0], results[1])

    def test_preflight_provider_and_extraction_failures(self):
        for options, message in [
            ({"missing": True}, "not installed"),
            ({"version_failure": True}, "version probe failed"),
            ({"provider_error": True}, "not accepted"),
            ({"no_theory": True}, "complete named Isabelle theory"),
            (
                {"outcomes": [1], "repair_error": True},
                "did not produce an Isabelle receipt",
            ),
        ]:
            with self.subTest(options=options):
                module = load_runtime()
                b = Boundaries(self.base, options)
                b.install(module)
                with self.assertRaisesRegex(Exception, message):
                    module.execute(state=self.state(), services=b.services())
                if options.get("missing") or options.get("version_failure"):
                    self.assertFalse(b.model_calls)

    def test_incomplete_reasoning_and_non_isabelle_branch(self):
        for filename, message in [
            ("partial.prism", "missing:"),
            ("no_steps.prism", "no completed steps"),
        ]:
            module = load_runtime()
            b = Boundaries(self.base)
            b.install(module)
            state = self.state()
            state["contract"]["entry_file"] = "project/prism_project/" + filename
            with self.assertRaisesRegex(ValueError, message):
                module.execute(state=state, services=b.services())
            self.assertFalse(any(not p["version"] for p in b.processes))
        module = load_runtime()
        b = Boundaries(self.base)
        b.install(module)
        state = self.state()
        state["contract"].pop("backend")
        execution = module.execute(state=state, services=b.services())
        self.assertFalse(hasattr(execution, "receipts"))
        self.assertFalse(b.processes)
        self.assertEqual(
            module.verify(state=state, execution=execution)["result"][
                "report_verification"
            ]["status"],
            "passed",
        )

    def test_retained_source_integrity_failure(self):
        module = load_runtime()
        b = Boundaries(self.base)
        b.install(module)
        state = self.state()
        execution = module.execute(state=state, services=b.services())
        (Path(state["run_root"]) / "attempt-1/Mathformer.thy").write_text("changed")
        with self.assertRaisesRegex(ValueError, "changed after validation"):
            module.verify(state=state, execution=execution)

    def test_mcp_lunar_execution(self):
        asyncio.run(self.mcp_cases())

    async def mcp_cases(self):
        snapshot = assets(self.document)
        workflow = workflow_documents([DESCRIPTOR], snapshot)[0]
        manager = SessionManager()
        config = StdioConfig(
            command=sys.executable,
            args=[str(Path(__file__).resolve()), "--fixture-server", str(self.base)],
            cwd=str(ROOT),
        )
        async with manager.open(
            "isabelle-trace", config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]
            compiled = compile_workflow("mcp:isabelle-trace", workflow, tools)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertEqual(len(compiled["bindings"]), 6)
            self.assertFalse(
                compile_workflow("mcp:isabelle-trace", workflow, tools[1:])["runnable"]
            )

            async def authorize():
                pass

            for options, count, status in [
                ({"outcomes": [0]}, 1, "passed"),
                ({"outcomes": [1, 0]}, 2, "passed"),
                ({"outcomes": [1, 1, 1]}, 3, "failed"),
                ({"outcomes": [1], "reject_repair": True}, 3, "rejected"),
            ]:
                state = self.state()
                handle = await remote.call(
                    "fixture_host_open", {"state": state, "options": options}
                )
                result = await execute(
                    compiled,
                    snapshot,
                    {"state": state, "services": handle},
                    remote,
                    authorize,
                )
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(len(result["calls"]), 3 + 2 * count)
                execution = result["outputs"]["execution"]
                verification = result["outputs"]["verification"]["result"]
                self.assertEqual(len(execution["receipts"]), count)
                self.assertEqual(
                    verification["structured_value"]["reasoning"]["status"], status
                )
                self.assertEqual(
                    verification["report_verification"]["status"],
                    "passed" if status == "passed" else "failed",
                )
                observed = await remote.call("fixture_host_observe", {"handle": handle})
                self.assertEqual(
                    observed["reasoning_count"], execution["reasoning_event_count"]
                )
                self.assertEqual(observed["closed"], True)
                self.assertEqual(observed["execution_count"], count)
                self.assertEqual(
                    [c["operation"] for c in result["calls"]],
                    ["reason_and_initialize", "first_build", "record_and_advance"]
                    + ["repair_build", "record_and_advance"] * (count - 1)
                    + ["assemble_execution", "verify_result"],
                )
            for options in (
                {"missing": True},
                {"provider_error": True},
                {"no_theory": True},
                {"outcomes": [1], "repair_error": True},
            ):
                state = self.state()
                handle = await remote.call(
                    "fixture_host_open", {"state": state, "options": options}
                )
                result = await execute(
                    compiled,
                    snapshot,
                    {"state": state, "services": handle},
                    remote,
                    authorize,
                )
                self.assertEqual(result["status"], "failed")
                self.assertIsNone(result["outputs"])
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                self.assertTrue(
                    (await remote.call("fixture_host_observe", {"handle": handle}))[
                        "closed"
                    ]
                )
            # Host evidence cannot be changed or replayed through public MCP tools.
            from mcp_connections.client import MCPConnectionError

            state = self.state()
            handle = await remote.call(
                "fixture_host_open", {"state": state, "options": {}}
            )
            changed = deepcopy(state)
            changed["workflow_inputs"]["source_derivation"] = "changed"
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    "mathformer_isabelle_trace_reason",
                    {"state": changed, "services": handle},
                )
            self.assertTrue(
                (await remote.call("fixture_host_observe", {"handle": handle}))[
                    "closed"
                ]
            )
            self.assertFalse((Path(state["run_root"]) / "reasoning").exists())
            # Explicitly exercise the actual loop guard if source stop evidence is disabled:
            # this changes only the test contract, never the production implementation.
            bounded = deepcopy(self.document)
            bounded["flow"]["steps"][1]["until"] = {"literal": False}
            bounded_snapshot = assets(bounded)
            bound_compiled = compile_workflow(
                "mcp:isabelle-trace",
                workflow_documents([DESCRIPTOR], bounded_snapshot)[0],
                tools,
            )
            state = self.state()
            handle = await remote.call(
                "fixture_host_open",
                {"state": state, "options": {"outcomes": [1, 1, 1]}},
            )
            result = await execute(
                bound_compiled,
                bounded_snapshot,
                {"state": state, "services": handle},
                remote,
                authorize,
            )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failure_disposition"], "fail")
            self.assertEqual(len(result["calls"]), 7)
        self.assertFalse(manager.active)


def serve(base):
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("offline Isabelle trace boundary fixture")
    registry = register_isabelle_trace_tools(mcp)
    observations = {}

    @mcp.tool()
    def fixture_host_open(state: dict, options: dict) -> dict:
        # Test-only host provisioning. Production has no fixture tools/switches.
        b = Boundaries(base, options)
        handle = registry.open(state, b.services())
        # Each session has its own native runtime module and boundary instances.
        # Requests execute sequentially in this test server.
        runtime._isabelle_module = load_runtime()._isabelle_module
        b.install(runtime)
        observations[handle["session_id"]] = b
        return handle

    runtime = registry.runtime

    @mcp.tool()
    def fixture_host_observe(handle: dict) -> dict:
        b = observations[handle["session_id"]]
        return dict(
            reasoning_count=len([p for k, p in b.events if k == "reasoning"]),
            execution_count=len(b.executions),
            closed=handle["session_id"] not in registry.sessions,
        )

    mcp.run(transport="stdio")


if __name__ == "__main__":
    if "--fixture-server" in sys.argv:
        serve(Path(sys.argv[-1]))
    else:
        unittest.main(verbosity=2)
