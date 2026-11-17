#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402
"""Fixed native fixtures through actual MCP, Lunar and the PRISM runtime.

This suite has no external provider/model or theorem compiler boundary. Its
router and eight Python fixture modules run for real. No production scientific
inputs, provider configuration, subprocess proof tools or model calls are used.
The only fault injection changes temporary fixture files or test contract limits.
"""

from tempfile import gettempdir
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
import yaml

from adversarial_design_guard_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

NATIVE = source()
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_sympy_adversarial_design_guard_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/adversarial-design-guard.workflow.json"
PREFIX = "mathformer_adversarial_guard_"
ORIGINAL_SHA = "6dde6db48e58f857d42b66ef7073e437fa46ad4cad4dd9a6fbecf0ff601f36a7"


def oracle():
    path = ROOT / "tests/mcp/fixtures/adversarial_design_guard_original.py.txt"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == ORIGINAL_SHA
    spec = importlib.util.spec_from_loader(
        "_adversarial_original", SourceFileLoader("_adversarial_original", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Relocated test oracle still reads the same authoritative native router.
    module.ROUTER = NATIVE.ROUTER
    return module


def assets(document):
    def asset(path, content):
        return dict(
            path=path,
            content=content,
            encoding="text",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in document["provenance"]["sources"]
    ]


class ObservedRemote:
    """Observe actual transport responses; optionally damage only fixture inputs."""

    def __init__(self, remote, damage=None):
        self.remote, self.damage = remote, damage
        self.events, self.directories = [], set()

    async def tools(self):
        return await self.remote.tools()

    async def call(self, name, arguments):
        result = await self.remote.call(name, arguments)
        self.events.append((name, deepcopy(arguments), deepcopy(result)))
        if name == PREFIX + "materialize":
            path = Path(result["fixture"]["path"])
            self.directories.add(path.parent)
            if self.damage == "missing":
                path.unlink()
            elif self.damage == "import":
                path.write_text('raise RuntimeError("fixture import failure")\n')
            elif self.damage == "callback":
                path.write_text(
                    path.read_text()
                    + '\ndef validate_no_hidden_target():\n    raise RuntimeError("native callback failure")\n'
                )
        return result


class AdversarialGuardTests(unittest.TestCase):
    def test_authored_contract_survives_native_generator(self):
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("_guard_normalizer", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        authored = json.loads((ROOT / AUTHORED).read_text())
        generated = [d for d in module.inventory() if d["id"] == authored["id"]]
        self.assertEqual(generated, [authored])

    def test_original_entrypoint_and_shared_steps(self):
        original = oracle()
        expected = original.run_suite()
        self.assertTrue(expected["ok"])
        self.assertEqual(NATIVE.run_suite(), expected)
        self.assertEqual(list(NATIVE.FIXTURES), [r["id"] for r in expected["results"]])
        router, temporary, state = NATIVE.initialize_suite()
        directory = Path(temporary.name)
        try:
            for cursor, name in enumerate(NATIVE.FIXTURES):
                previous = deepcopy(state)
                fixture = NATIVE.materialize_fixture(directory, state)
                self.assertEqual(
                    Path(fixture["path"]).read_text(), original.fixture_source(name)
                )
                review = NATIVE.review_fixture(router, fixture)
                self.assertEqual(review["status"], "fail")
                self.assertIsNone(review["evidence"]["reasoning_log"])
                state, done = NATIVE.append_fixture_result(state, fixture, review)
                self.assertEqual(previous["cursor"], cursor)
                self.assertEqual(state["results"][:-1], previous["results"])
                self.assertEqual(state["results"][-1], expected["results"][cursor])
                self.assertEqual(done, cursor == 7)
            with self.assertRaises(IndexError):
                NATIVE.materialize_fixture(directory, state)
        finally:
            temporary.cleanup()
        self.assertFalse(directory.exists())
        self.assertEqual(NATIVE.finish_suite(state), expected)
        for argv in [[], ["--json"]]:
            outputs = []
            for module in [original, NATIVE]:
                stream = io.StringIO()
                with redirect_stdout(stream):
                    code = module.main(argv)
                outputs.append((code, stream.getvalue()))
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0][0], 0)

    def test_real_reviewer_branches_and_expectation_data(self):
        router = NATIVE.load_router()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.py"
            review = router.build_design_guard_review("formalphysics_0000", path, None)
            self.assertEqual(review["status"], "fail")
            self.assertIn("artifact_missing", [f["code"] for f in review["findings"]])
            path.write_text("this is invalid Python !")
            review = router.build_design_guard_review("formalphysics_0000", path, None)
            self.assertIn(
                "artifact_import_failed", [f["code"] for f in review["findings"]]
            )
            path.write_text(NATIVE.fixture_source("healthy"))
            review = router.build_design_guard_review("formalphysics_0000", path, None)
            self.assertEqual(review["status"], "pass")
            self.assertTrue(review["findings"])  # absent log remains medium
            self.assertFalse(
                any(f["severity"] in {"high", "critical"} for f in review["findings"])
            )
            path.write_text(
                NATIVE.fixture_source("healthy")
                + '\ndef validate_numeric_samples():\n    raise ValueError("numeric fixture")\n'
            )
            review = router.build_design_guard_review("formalphysics_0000", path, None)
            self.assertIn(
                "numeric_domain_hole", [f["code"] for f in review["findings"]]
            )
            path.write_text(
                NATIVE.fixture_source("healthy")
                + '\ndef validate_no_hidden_target():\n    raise RuntimeError("callback fixture")\n'
            )
            with self.assertRaisesRegex(RuntimeError, "callback fixture"):
                router.build_design_guard_review("formalphysics_0000", path, None)
        # Filtering, sorting, booleans and failure aggregation are shared native
        # operations, tested directly with inputs, never mocked implementations.
        state = dict(cursor=0, results=[])
        fixture = dict(name="probe", expected_code="expected", repair_surface="route")
        data = dict(
            status="pass",
            findings=[
                None,
                {"severity": "medium", "code": "ignored", "repair_surface": "ignored"},
                {"severity": "critical", "code": "z", "repair_surface": "route"},
                {"severity": "high", "code": "expected", "repair_surface": "a"},
                {"severity": "high", "code": None},
            ],
        )
        updated, done = NATIVE.append_fixture_result(state, fixture, data)
        self.assertEqual(state, dict(cursor=0, results=[]))
        self.assertFalse(done)
        row = updated["results"][0]
        self.assertEqual(row["observed_codes"], ["expected", "z"])
        self.assertEqual(row["observed_repair_surfaces"], ["a", "route"])
        self.assertTrue(
            row["expected_code_present"] and row["expected_surface_present"]
        )
        self.assertFalse(row["blocked"])
        self.assertFalse(NATIVE.finish_suite(updated)["ok"])
        for key in ["blocked", "expected_code_present", "expected_surface_present"]:
            row = dict(
                row,
                blocked=True,
                expected_code_present=True,
                expected_surface_present=True,
            )
            row[key] = False
            report = NATIVE.finish_suite(dict(results=[row], cursor=1))
            self.assertEqual(
                report["findings"][0]["code"],
                "fixture_did_not_fail_with_expected_route",
            )

    def test_registered_mcp_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document, json.loads((ROOT / AUTHORED).read_text()))
        self.assertEqual(
            document["id"], "hub_physics_sympy_adversarial_design_guard_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            dict(wall_time_seconds=180, max_operation_calls=26),
        )
        self.assertIn(
            "tests/physics_sympy/run_adversarial_design_guard_suite.py",
            [s["path"] for s in document["provenance"]["sources"]],
        )
        for s in document["provenance"]["sources"]:
            self.assertEqual(
                s["digest"],
                "sha256:" + hashlib.sha256((ROOT / s["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        directories = set()
        config = StdioConfig(
            command=sys.executable,
            args=[str(Path(__file__).resolve()), "--server"],
            cwd=str(ROOT),
        )
        async with manager.open(
            "adversarial-guard", config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=tools):
                snapshot = assets(doc)
                selected = workflow_documents([DESCRIPTOR], snapshot)[0]
                return (
                    compile_workflow("mcp:adversarial-guard", selected, inventory),
                    snapshot,
                )

            compiled, snapshot = compile(document)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertTrue(compiled["prism_source"] and compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
            for op in document["operations"].values():
                target = op["execution"]["binding"]["target"]
                self.assertFalse(
                    compile(document, [t for t in tools if t["name"] != target])[0][
                        "runnable"
                    ]
                )
            draft = deepcopy(document)
            draft["lifecycle"] = "draft"
            self.assertFalse(compile(draft)[0]["runnable"])

            async def authorize():
                pass

            async def run(doc=document, damage=None):
                c, a = (compiled, snapshot) if doc is document else compile(doc)
                self.assertTrue(c["runnable"], c["diagnostics"])
                observed = ObservedRemote(remote, damage)
                try:
                    result = await execute(c, a, {}, observed, authorize)
                finally:
                    directories.update(observed.directories)
                return result, observed

            expected = oracle().run_suite()
            result, observed = await run()
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(result["outputs"], {"report": expected})
            self.assertEqual(
                [c["tool"] for c in result["calls"]],
                [PREFIX + "initialize"]
                + [
                    PREFIX + step
                    for _ in range(8)
                    for step in ["materialize", "review", "append_and_guard"]
                ]
                + [PREFIX + "finish"],
            )
            self.assertEqual(len(result["calls"]), 26)
            self.assertTrue(
                result["runtime"]["effect_records"] and result["replay_artifacts"]
            )
            for call in result["calls"]:
                self.assertTrue(call["input_digest"] and call["output_digest"])
            appended = [
                response
                for name, _, response in observed.events
                if name == PREFIX + "append_and_guard"
            ]
            for cursor, response in enumerate(appended, 1):
                self.assertEqual(
                    response["state"],
                    dict(cursor=cursor, results=expected["results"][:cursor]),
                )
                self.assertEqual(response["done"], cursor == 8)
            self.assertTrue(all(not p.exists() for p in observed.directories))
            # Actual reviewer missing/import branches produce a complete failing
            # suite report. They do not stop later fixtures or become tool errors.
            for damage, code in [
                ("missing", "artifact_missing"),
                ("import", "artifact_import_failed"),
            ]:
                result, observed = await run(damage=damage)
                self.assertEqual(result["status"], "accepted", result)
                report = result["outputs"]["report"]
                self.assertFalse(report["ok"])
                self.assertEqual(report["fixture_count"], 8)
                self.assertEqual(len(report["findings"]), 8)
                self.assertTrue(
                    all(code in r["observed_codes"] for r in report["results"])
                )
                self.assertEqual(len(result["calls"]), 26)
                self.assertTrue(all(not p.exists() for p in observed.directories))
            # Uncaught target validator exceptions stop at the first reviewer;
            # there is no retry, later fixture, aggregation or leaked directory.
            result, observed = await run(damage="callback")
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(len(result["calls"]), 3)
            self.assertTrue(all(not p.exists() for p in observed.directories))
            # Exact native exhaustion is at fixture 8. A deliberately reduced
            # test bound fails after seven appends, without finish acceptance.
            bounded = deepcopy(document)
            bounded["flow"]["steps"][1]["max_iterations"] = 7
            result, observed = await run(doc=bounded)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(result["failure_disposition"], "fail")
            self.assertIsNone(result["outputs"])
            self.assertEqual(len(result["calls"]), 22)
            self.assertEqual(observed.events[-1][2]["state"]["cursor"], 7)
            budget = deepcopy(document)
            budget["policy"]["limits"]["max_operation_calls"] = 4
            result, _ = await run(doc=budget)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 4
            )
            self.assertIn("budget", str(result).lower())
            timed = deepcopy(document)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            timed_compiled, timed_assets = compile(timed)

            async def pending_authorization():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(
                    timed_compiled, timed_assets, {}, remote, pending_authorization
                )
            # Source ownership rejects a modified carried state, and the real
            # failure propagates through the compiled PRISM execution.
            invalid = deepcopy(document)
            invalid["flow"]["steps"][1]["initial"] = {
                "literal": {"cursor": 1, "results": []}
            }
            result, _ = await run(doc=invalid)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(len(result["calls"]), 2)
            # Direct registered ports also reject reordering, stale handles,
            # fixture path replacement and report forgery; every error closes.
            for attack in ["order", "path", "report", "write"]:
                init = await remote.call(PREFIX + "initialize", {})
                session, state = init["session"], init["state"]
                fixture = (await remote.call(PREFIX + "materialize", init))["fixture"]
                directory = Path(fixture["path"]).parent
                directories.add(directory)
                with self.assertRaises(MCPConnectionError):
                    if attack == "order":
                        await remote.call(PREFIX + "finish", init)
                    elif attack == "path":
                        await remote.call(
                            PREFIX + "review",
                            dict(
                                session=session,
                                fixture=dict(
                                    fixture,
                                    path=str(
                                        Path(gettempdir())
                                        / "mathformer-test-fixtures/other/path.py"
                                    ),
                                ),
                            ),
                        )
                    elif attack == "report":
                        await remote.call(
                            PREFIX + "review", dict(session=session, fixture=fixture)
                        )
                        await remote.call(
                            PREFIX + "append_and_guard",
                            dict(
                                session=session,
                                state=state,
                                fixture=fixture,
                                report={"status": "pass", "findings": []},
                            ),
                        )
                    else:
                        await remote.call(
                            PREFIX + "review", dict(session=session, fixture=fixture)
                        )
                        # Real materialization failure in a later fixture.
                        report = NATIVE.load_router().build_design_guard_review(
                            "formalphysics_0000", Path(fixture["path"]), None
                        )
                        next_state = (
                            await remote.call(
                                PREFIX + "append_and_guard",
                                dict(
                                    session=session,
                                    state=state,
                                    fixture=fixture,
                                    report=report,
                                ),
                            )
                        )["state"]
                        (directory / "target_leakage.py").mkdir()
                        await remote.call(
                            PREFIX + "materialize",
                            dict(session=session, state=next_state),
                        )
                self.assertFalse(directory.exists())
                with self.assertRaises(MCPConnectionError):
                    await remote.call(PREFIX + "materialize", init)
            # Abandonment is reclaimed when the actual MCP session/server exits.
            init = await remote.call(PREFIX + "initialize", {})
            fixture = (await remote.call(PREFIX + "materialize", init))["fixture"]
            directories.add(Path(fixture["path"]).parent)
            self.assertTrue(Path(fixture["path"]).exists())
        self.assertFalse(manager.active)
        self.assertTrue(all(not p.exists() for p in directories), directories)


if __name__ == "__main__":
    if "--server" in sys.argv:
        import mcp_server

        mcp_server.mcp.run(transport="stdio")
    else:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(AdversarialGuardTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        raise SystemExit(
            0
            if result.wasSuccessful() and result.testsRun and not result.skipped
            else 1
        )
