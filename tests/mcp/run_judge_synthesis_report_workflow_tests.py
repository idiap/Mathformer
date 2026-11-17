#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Synthetic native evidence through registered MCP and real Lunar/PRISM.

Provider and compiler fixtures reject every network or external compiler call.
The report builder subprocess and every source step run without substitution.
Artifact fixtures change real bytes between calls to exercise failure branches.
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
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]
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
from judge_synthesis_report_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_formalphysics_judge_synthesis_report_self_test_workflow/workflow.yaml"
PREFIX = "mathformer_synthesis_smoke_"
BOUNDARY = """import subprocess, socket
_native_run = subprocess.run
def guarded_run(command, *args, **kwargs):
    assert isinstance(command, list) and len(command) == 9, command
    assert command[1].endswith('/formalphysics-judge-synthesis-reporter/scripts/build_synthesis_report.py'), command
    assert command[2::2] == ['--comparative-report', '--output-dir', '--codex-results-json', '--json'], command
    assert command[0] == __import__('sys').executable
    assert kwargs['capture_output'] is True and kwargs['text'] is True
    assert 'timeout' not in kwargs
    assert kwargs['env']['PYTHONDONTWRITEBYTECODE'] == '1'
    assert str(kwargs['cwd']) == str(__import__('pathlib').Path(command[1]).parents[4])
    return _native_run(command, *args, **kwargs)
subprocess.run = guarded_run
def no_provider(*args, **kwargs):
    raise AssertionError('Provider/network and external compiler calls are forbidden')
socket.create_connection = no_provider
socket.socket.connect = no_provider
"""


def original():
    loader = SourceFileLoader(
        "_synthesis_original",
        str(ROOT / "tests/mcp/fixtures/judge_synthesis_report_original.py.txt"),
    )
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    module.REPO_ROOT = ROOT
    module.REPORT_BUILDER = source().REPORT_BUILDER
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
        asset(p, (ROOT / p).read_text())
        for p in dict.fromkeys(r["path"] for r in document["provenance"]["sources"])
    ]


class Observed:
    def __init__(self, remote, hook=None):
        self.remote, self.hook, self.seen = remote, hook, []

    async def tools(self):
        return await self.remote.tools()

    async def call(self, tool, arguments):
        result = await self.remote.call(tool, arguments)
        self.seen.append(
            (tool.removeprefix(PREFIX), deepcopy(arguments), deepcopy(result))
        )
        if self.hook:
            self.hook(tool.removeprefix(PREFIX), arguments, result)
        return result


class SynthesisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.boundaries = tempfile.TemporaryDirectory()
        cls.previous_pythonpath = os.environ.get("PYTHONPATH")
        (Path(cls.boundaries.name) / "sitecustomize.py").write_text(BOUNDARY)
        packages = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
        os.environ["PYTHONPATH"] = os.pathsep.join([cls.boundaries.name, *packages])
        import subprocess
        import socket

        cls.saved = subprocess.run, socket.create_connection, socket.socket.connect
        exec(compile(BOUNDARY, "<provider-compiler-fixture>", "exec"), {})

    @classmethod
    def tearDownClass(cls):
        import subprocess
        import socket

        subprocess.run, socket.create_connection, socket.socket.connect = cls.saved
        if cls.previous_pythonpath is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = cls.previous_pythonpath
        cls.boundaries.cleanup()

    def test_native_generator_preserves_authored_contract(self):
        directory = ROOT / "skills/control/workflow-contract-validator/scripts"
        sys.path.insert(0, str(directory))
        try:
            spec = importlib.util.spec_from_file_location(
                "_synthesis_normalizer", directory / "normalize_workflows.py"
            )
            generator = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(generator)
            document = yaml.safe_load(
                Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
            )
            selected = [d for d in generator.inventory() if d["id"] == document["id"]]
            self.assertEqual(selected, [document])
        finally:
            sys.path.remove(str(directory))

    def test_original_equivalence_and_native_checks(self):
        native, oracle = source(), original()
        expected = oracle.run_check()
        self.assertEqual(
            expected,
            {
                "schema_version": 1,
                "ok": True,
                "style": "formalphysics_judge_synthesis_report_test",
                "findings": [],
            },
        )
        self.assertEqual(native.run_check(), expected)
        for module in [oracle, native]:
            for flags in [[], ["--json"]]:
                out = io.StringIO()
                with redirect_stdout(out):
                    code = module.main(flags)
                self.assertEqual(code, 0)
                self.assertEqual(
                    json.loads(out.getvalue()) if flags else out.getvalue(),
                    expected if flags else "ok: True\n",
                )
        with tempfile.TemporaryDirectory() as raw:
            workspace = native.prepare_fixture(Path(raw))
            report = json.loads(Path(workspace["comparative"]).read_text())
            self.assertEqual(len(report["cases"]), 1)
            candidates = report["cases"][0]["candidates"]
            self.assertEqual(
                [c["aggregate"]["status"] for c in candidates], ["blocked", "accepted"]
            )
            self.assertTrue(all(len(c["scores"]) == 14 for c in candidates))
            self.assertEqual(len(report["codex_exec_judge_prompts"]), 4)
            self.assertEqual(
                len(json.loads(Path(workspace["results"]).read_text())["results"]), 2
            )
            # Real failing builder, invalid stdout fallback, ordered independent findings.
            Path(workspace["comparative"]).write_text("{")
            result = native.invoke_builder(workspace)
            self.assertNotEqual(result["code"], 0)
            self.assertEqual(result["payload"], {})
            self.assertIn("JSONDecodeError", result["stderr"])
            state = native.start_checks(workspace, result)
            self.assertEqual(
                [f["code"] for f in state["findings"]],
                ["synthesis_builder_failed", "synthesis_builder_not_ok"],
            )
            for index in range(4):
                previous = deepcopy(state["findings"])
                _, done = native.check_artifact(state)
                self.assertEqual(state["findings"][:-1], previous)
                self.assertEqual(state["index"], index + 1)
                self.assertEqual(done, index == 3)
            previous = deepcopy(state)
            with self.assertRaises(IndexError):
                native.check_artifact(state)
            self.assertEqual(state, previous)
            self.assertFalse(native.finish(state)["ok"])
            # Non-ok and nonzero are independent checks, and malformed payloads raise.
            self.assertEqual(
                native.start_checks(
                    workspace, {"code": 0, "payload": {}, "stderr": ""}
                )["findings"][0]["code"],
                "synthesis_builder_not_ok",
            )
            self.assertEqual(
                native.start_checks(
                    workspace, {"code": 9, "payload": {"ok": True}, "stderr": "failed"}
                )["findings"],
                [
                    {
                        "severity": "high",
                        "code": "synthesis_builder_failed",
                        "stderr": "failed",
                    }
                ],
            )
            with self.assertRaises(AttributeError):
                native.start_checks(workspace, {"code": 0, "payload": [], "stderr": ""})

    def test_registered_mcp_real_lunar_paths_and_limits(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"],
            "hub_physics_lean_formalphysics_judge_synthesis_report_self_test_workflow",
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document["policy"]["limits"]["max_operation_calls"], 18)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        authored = json.loads(
            (
                ROOT
                / "skills/control/workflow-contract-validator/references/judge-synthesis-report-self-test.workflow.json"
            ).read_text()
        )
        self.assertEqual(document, authored)
        manager = SessionManager()
        abandoned = []
        failure = None
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "synthesis-smoke",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {"PYTHONPATH": os.environ["PYTHONPATH"]},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile_doc(doc, inventory=None):
                    snapshot = assets(doc)
                    return (
                        compile_workflow(
                            "mcp:synthesis-smoke",
                            workflow_documents([DESCRIPTOR], snapshot)[0],
                            tools if inventory is None else inventory,
                        ),
                        snapshot,
                    )

                workflow, snapshot = compile_doc(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                self.assertFalse(compile_doc(document, [])[0]["runnable"])
                self.assertFalse(
                    compile_doc(
                        document,
                        [t for t in tools if t["name"] != PREFIX + "invoke_builder"],
                    )[0]["runnable"]
                )

                async def allow():
                    pass

                async def run(doc=None, hook=None):
                    w, a = compile_doc(doc) if doc else (workflow, snapshot)
                    self.assertTrue(w["runnable"], w["diagnostics"])
                    observed = Observed(remote, hook)
                    result = await execute(w, a, {}, observed, allow)
                    return result, observed

                def inspect(op, args, value):
                    if op == "invoke_builder":
                        built = value["result"]
                        self.assertEqual(built["code"], 0)
                        self.assertEqual(built["stderr"], "")
                        self.assertTrue(built["payload"]["ok"])
                        p = built["payload"]["artifacts"]
                        self.assertTrue(
                            all(Path(p[k]).is_file() for k in source().ARTIFACT_KEYS)
                        )
                        report = json.loads(Path(p["json"]).read_text())
                        self.assertEqual(
                            report["policy"]["reference_answer_role"],
                            "non_gold_reference_evidence",
                        )
                        self.assertEqual(len(report["aspect_comparison"]), 5)
                        self.assertEqual(
                            report["approaches"]["current_mathformer_lean"][
                                "accepted_count"
                            ],
                            1,
                        )
                        self.assertEqual(
                            report["approaches"]["external_formaldiscovery"][
                                "blocked_count"
                            ],
                            1,
                        )
                        self.assertTrue(
                            report["approaches"]["current_mathformer_lean"]["strengths"]
                        )
                        self.assertTrue(
                            report["approaches"]["external_formaldiscovery"][
                                "weaknesses"
                            ]
                        )
                        self.assertTrue(report["synthesis_todos"])
                        judges = report["judge_review_synthesis"]
                        self.assertEqual(judges["codex_exec_results_ingested"], 2)
                        self.assertTrue(
                            judges["codex_exec_disagreement_patterns"][
                                "agreement_counts"
                            ]
                        )
                        self.assertEqual(
                            report["todo_state_summary"]["open_repo_actionable_count"],
                            0,
                        )

                result, observed = await run(hook=inspect)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"],
                    {"result": source().finish({"findings": []}), "exit_code": 0},
                )
                expected = (
                    ["prepare_fixture", "invoke_builder", "start_checks"]
                    + ["check_artifact"] * 4
                    + ["prepare_inspection", "check_json", "prepare_inspection"]
                    + ["check_marker"] * 7
                    + ["finish"]
                )
                self.assertEqual([r[0] for r in observed.seen], expected)
                self.assertEqual(len(result["calls"]), 18)
                for op, count in [("check_artifact", 4), ("check_marker", 7)]:
                    rows = [r[2] for r in observed.seen if r[0] == op]
                    self.assertEqual(
                        [r["state"]["index"] for r in rows], list(range(1, count + 1))
                    )
                    self.assertEqual(
                        [r["done"] for r in rows], [False] * (count - 1) + [True]
                    )
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
                for call in result["calls"]:
                    self.assertTrue(call["transport_call_performed"])
                    self.assertEqual(len(call["input_digest"]), 64)
                    self.assertEqual(len(call["output_digest"]), 64)
                self.assertFalse(
                    Path(observed.seen[0][2]["workspace"]["root"]).exists()
                )
                for absent in [
                    ("json",),
                    ("html",),
                    ("json", "html"),
                    ("markdown", "todos"),
                ]:

                    def missing(op, args, value):
                        if op == "invoke_builder":
                            for key in absent:
                                Path(
                                    value["result"]["payload"]["artifacts"][key]
                                ).unlink()

                    result, observed = await run(hook=missing)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"]["exit_code"], 3)
                    self.assertFalse(result["outputs"]["result"]["ok"])
                    self.assertEqual(
                        [f["code"] for f in result["outputs"]["result"]["findings"]],
                        [
                            "missing_" + k + "_artifact"
                            for k in source().ARTIFACT_KEYS
                            if k in absent
                        ],
                    )
                    self.assertEqual(
                        [r[0] for r in observed.seen].count("check_json"),
                        int("json" not in absent),
                    )
                    self.assertEqual(
                        [r[0] for r in observed.seen].count("check_marker"),
                        7 * int("html" not in absent),
                    )
                    self.assertEqual(
                        [r[0] for r in observed.seen].count("carry_state"),
                        len(set(absent) & {"json", "html"}),
                    )
                    self.assertFalse(
                        Path(observed.seen[0][2]["workspace"]["root"]).exists()
                    )

                def degraded(op, args, value):
                    if op == "invoke_builder":
                        p = value["result"]["payload"]["artifacts"]
                        Path(p["json"]).write_text("{}")
                        Path(p["html"]).write_text("")

                result, observed = await run(hook=degraded)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"]["exit_code"], 3)
                findings = result["outputs"]["result"]["findings"]
                self.assertEqual(
                    [f["code"] for f in findings],
                    [
                        "wrong_synthesis_style",
                        "reference_policy_not_preserved",
                        "approach_statuses_not_synthesized",
                        "strengths_or_weaknesses_missing",
                        "aspect_comparison_incomplete",
                        "synthesis_todos_missing",
                        "codex_results_not_ingested",
                        "codex_disagreement_patterns_missing",
                        "todo_actionability_not_classified",
                    ]
                    + ["html_marker_missing"] * 7,
                )
                self.assertEqual(
                    [f["marker"] for f in findings[9:]], list(source().HTML_MARKERS)
                )
                for row in observed.seen:
                    if row[0] in ("check_json", "check_marker"):
                        before = row[1]["state"]["findings"]
                        after = row[2]["state"]["findings"]
                        self.assertEqual(after[: len(before)], before)
                self.assertEqual(len(result["calls"]), 18)

                # Real child failure is reported, not retried, and later checks run.
                def bad_input(op, args, value):
                    if op == "prepare_fixture":
                        Path(value["workspace"]["comparative"]).write_text("{")

                result, observed = await run(hook=bad_input)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"]["exit_code"], 3)
                self.assertEqual(
                    [f["code"] for f in result["outputs"]["result"]["findings"]],
                    ["synthesis_builder_failed", "synthesis_builder_not_ok"]
                    + ["missing_" + k + "_artifact" for k in source().ARTIFACT_KEYS],
                )
                self.assertEqual(observed.seen[1][2]["result"]["payload"], {})
                self.assertIn(
                    "JSONDecodeError", observed.seen[1][2]["result"]["stderr"]
                )
                self.assertEqual(
                    [r[0] for r in observed.seen].count("invoke_builder"), 1
                )
                self.assertFalse(
                    Path(observed.seen[0][2]["workspace"]["root"]).exists()
                )
                # Malformed artifact content propagates once, closes its scope, stops.
                for contents in ["{", "[]"]:

                    def corrupt(op, args, value):
                        if op == "invoke_builder":
                            Path(
                                value["result"]["payload"]["artifacts"]["json"]
                            ).write_text(contents)

                    result, observed = await run(hook=corrupt)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(result["calls"][-1]["operation"], "check_json")
                    self.assertNotIn("finish", [r[0] for r in observed.seen])
                    self.assertFalse(
                        Path(observed.seen[0][2]["workspace"]["root"]).exists()
                    )

                def unreadable_html(op, args, value):
                    if op == "invoke_builder":
                        Path(
                            value["result"]["payload"]["artifacts"]["html"]
                        ).write_bytes(b"\xff")

                result, observed = await run(hook=unreadable_html)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(result["calls"][-1]["operation"], "prepare_inspection")
                self.assertEqual(observed.seen[-1][0], "check_json")
                self.assertFalse(
                    Path(observed.seen[0][2]["workspace"]["root"]).exists()
                )
                # The parser/checker/compiler/runtime remain real in bounded fixtures.
                for target, bound, calls in [("artifacts", 3, 6), ("html", 6, 16)]:
                    capped = deepcopy(document)
                    loop = (
                        capped["flow"]["steps"][3]
                        if target == "artifacts"
                        else capped["flow"]["steps"][7]
                    )
                    loop["max_iterations"] = bound
                    result, observed = await run(capped)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["failure_disposition"], "fail")
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), calls)
                    abandoned.append(Path(observed.seen[0][2]["workspace"]["root"]))
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 2
                result, observed = await run(budget)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    2,
                )
                self.assertIn("budget", str(result).lower())
                abandoned.append(Path(observed.seen[0][2]["workspace"]["root"]))
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                w, a = compile_doc(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(w, a, {}, remote, pending)
                fixture = await remote.call(PREFIX + "prepare_fixture", {})
                changed = deepcopy(fixture)
                changed["workspace"]["comparative"] = str(
                    Path(gettempdir())
                    / "mathformer-test-fixtures/arbitrary/report.json"
                )
                with self.assertRaises(MCPConnectionError):
                    await remote.call(PREFIX + "invoke_builder", changed)
                self.assertFalse(Path(fixture["workspace"]["root"]).exists())
                with self.assertRaises(MCPConnectionError):
                    await remote.call(PREFIX + "invoke_builder", fixture)
                fixture = await remote.call(PREFIX + "prepare_fixture", {})
                built = await remote.call(PREFIX + "invoke_builder", fixture)
                checked = await remote.call(
                    PREFIX + "start_checks", {**fixture, **built}
                )
                changed = deepcopy(checked)
                changed["state"]["index"] = 3
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "check_artifact",
                        {**changed, "context": fixture["context"]},
                    )
                self.assertFalse(Path(fixture["workspace"]["root"]).exists())
                fixture = await remote.call(PREFIX + "prepare_fixture", {})
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "finish", {"state": {}, "context": fixture["context"]}
                    )
                self.assertFalse(Path(fixture["workspace"]["root"]).exists())
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        for path in abandoned:
            self.assertFalse(path.exists(), str(path))
        if failure:
            raise failure


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SynthesisTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(
        0
        if result.wasSuccessful()
        and result.testsRun > 0
        and len(result.skipped) < result.testsRun
        else 1
    )
