#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Run real shared smoke steps, MCP transport, and Lunar/PRISM with fixed fixtures.

Only external provider/compiler boundaries are replaced by rejecting fixtures.
The native report-builder subprocess, report generation, and validation run as-is.
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
import re
import tempfile
import unittest
import yaml
from comparative_report_self_test_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_formalphysics_comparative_report_self_test_workflow/workflow.yaml"
PREFIX = "mathformer_comparative_smoke_"
# Inherited by the real builder subprocess too: no provider or theorem prover.
BOUNDARY = """import subprocess, socket
_original_run = subprocess.run
def guarded_run(command, *args, **kwargs):
    if not (isinstance(command, list) and len(command) == 9
            and command[1].endswith('/formalphysics-comparative-analysis-reporter/scripts/build_comparative_report.py')
            and command[2::2] == ['--input-json', '--output-dir', '--synthesis-report-json', '--json']):
        raise AssertionError('External provider/compiler process forbidden: ' + str(command))
    assert kwargs.get('capture_output') is True
    assert kwargs.get('text') is True
    assert 'timeout' not in kwargs
    assert kwargs['env']['PYTHONDONTWRITEBYTECODE'] == '1'
    return _original_run(command, *args, **kwargs)
subprocess.run = guarded_run
def no_provider(*args, **kwargs):
    raise AssertionError('External provider network is forbidden')
socket.create_connection = no_provider
socket.socket.connect = no_provider
"""


def normalize(value):
    if isinstance(value, str):
        return re.sub(
            r'(?:/private)?/var/folders/[^\s"\']+/T/tmp[^/\s"\']+|/tmp/tmp[^/\s"\']+',
            "<tmp>",
            value,
        )
    if isinstance(value, list):
        return [normalize(v) for v in value]
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    return value


def original():
    loader = SourceFileLoader(
        "_comparative_original",
        str(ROOT / "tests/mcp/fixtures/comparative_report_original.py.txt"),
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


class ComparativeSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.boundaries = tempfile.TemporaryDirectory()
        cls.previous_pythonpath = os.environ.get("PYTHONPATH")
        (Path(cls.boundaries.name) / "sitecustomize.py").write_text(BOUNDARY)
        packages = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
        os.environ["PYTHONPATH"] = os.pathsep.join([cls.boundaries.name, *packages])
        # Guard the in-process oracle and native smoke builder call too.
        import subprocess
        import socket

        cls.saved = subprocess.run, socket.create_connection, socket.socket.connect
        exec(compile(BOUNDARY, "<test-provider-compiler-boundaries>", "exec"), {})

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

    def test_original_parity_and_native_state(self):
        native, oracle = source(), original()
        a, b = oracle.run_check(), native.run_check()
        self.assertEqual(a["ok"], not a["findings"])
        self.assertTrue(
            set(f["code"] for f in a["findings"]) <= {"foundations_not_included"}
        )
        self.assertEqual(normalize(a), normalize(b))
        # main keeps its JSON output and 0/3 exit semantics.
        for module in [oracle, native]:
            out = io.StringIO()
            with redirect_stdout(out):
                code = module.main(["--json"])
            self.assertEqual(code, 0 if a["ok"] else 3)
            self.assertEqual(normalize(json.loads(out.getvalue())), normalize(a))
        with tempfile.TemporaryDirectory() as raw:
            state = native.create_fixture(Path(raw))
            self.assertEqual(state["findings"], [])
            self.assertIn(
                "mathformerphysics_output",
                json.loads(Path(state["input_json"]).read_text())[0],
            )
            native.invoke_builder(state)
            native.start_artifacts(state)
            state["findings"].clear()
            # Exercise append-only failure ordering without substituting source operations.
            state["artifacts"] = {}
            for cursor in range(9):
                prior = deepcopy(state["findings"])
                _, done = native.check_item(state)
                self.assertEqual(state["cursor"], cursor + 1)
                self.assertEqual(done, cursor == 8)
                self.assertEqual(state["findings"][:-1], prior)
            saved = deepcopy(state)
            with self.assertRaises(IndexError):
                native.check_item(state)
            self.assertEqual(state, saved)
            self.assertEqual(
                [f["code"] for f in state["findings"]],
                ["missing_" + k + "_artifact" for k in native.CHECK_ITEMS["artifacts"]],
            )
            self.assertFalse(native.finish(state)["ok"])
            state["findings"].clear()
            self.assertTrue(native.finish(state)["ok"])

    def test_mcp_lunar_paths_and_limits(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"],
            "hub_physics_lean_formalphysics_comparative_report_self_test_workflow",
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document["policy"]["limits"]["max_operation_calls"], 41)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        abandoned = []
        failure = None
        server = 'import sys; sys.path.insert(0,"scripts"); from mcp_server import mcp; mcp.run(transport="stdio")'
        async with manager.open(
            "comparative-smoke",
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
                            "mcp:comparative-smoke",
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
                        document, [t for t in tools if t["name"] != PREFIX + "builder"]
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
                    if op == "builder":
                        state = value["state"]
                        self.assertEqual(state["code"], 0)
                        self.assertEqual(state["stderr"], "")
                        p = state["payload"]
                        self.assertTrue(p["ok"])
                        self.assertNotIn(
                            "mathformerphysics_output",
                            Path(
                                state["output_dir"], "selected_examples.cleaned.json"
                            ).read_text(),
                        )
                        report = json.loads(Path(p["artifacts"]["json"]).read_text())
                        self.assertTrue(report["judge_synthesis"]["available"])
                        self.assertEqual(report["summary"]["case_count"], 1)
                        self.assertEqual(len(report["codex_exec_judge_prompts"]), 16)
                        for case in report["cases"]:
                            for candidate in case["candidates"]:
                                self.assertFalse(candidate["lean_compile"]["attempted"])

                result, observed = await run(hook=inspect)
                self.assertEqual(result["status"], "accepted", result)
                baseline = result["outputs"]["report"]
                self.assertEqual(baseline["ok"], not baseline["findings"])
                self.assertEqual(
                    [f["code"] for f in baseline["findings"]],
                    (
                        []
                        if baseline["summary"]["foundations_file_count"]
                        else ["foundations_not_included"]
                    ),
                )
                self.assertEqual(len(result["calls"]), 41)
                expected = (
                    ["fixtures", "builder", "start_artifacts"]
                    + ["check_item"] * 9
                    + ["after_artifacts"]
                    + ["check_item"] * 14
                    + ["report_guard", "start_report"]
                    + ["check_item"] * 5
                    + ["start_critics"]
                    + ["check_item"] * 4
                    + ["finish_report", "finish"]
                )
                self.assertEqual([r[0] for r in observed.seen], expected)
                for phase, count in [
                    ("artifacts", 9),
                    ("html", 14),
                    ("metrics", 5),
                    ("critics", 4),
                ]:
                    rows = [
                        r[2]
                        for r in observed.seen
                        if r[0] == "check_item" and r[2]["state"]["phase"] == phase
                    ]
                    self.assertEqual(
                        [r["state"]["cursor"] for r in rows], list(range(1, count + 1))
                    )
                    self.assertEqual(
                        [r["done"] for r in rows], [False] * (count - 1) + [True]
                    )
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
                for c in result["calls"]:
                    self.assertTrue(c["transport_call_performed"])
                    self.assertEqual(len(c["input_digest"]), 64)
                    self.assertEqual(len(c["output_digest"]), 64)
                self.assertFalse(Path(observed.seen[0][2]["state"]["tmp"]).exists())
                # Missing files take real guard defaults and omit their inner checks.
                for absent in [("html",), ("json",), ("html", "json")]:

                    def missing(op, args, value):
                        if op == "builder":
                            for key in absent:
                                Path(
                                    value["state"]["payload"]["artifacts"][key]
                                ).unlink()

                    result, observed = await run(hook=missing)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertFalse(result["outputs"]["report"]["ok"])
                    expected_missing = [
                        "missing_" + k + "_artifact"
                        for k in source().CHECK_ITEMS["artifacts"]
                        if k in absent
                    ]
                    self.assertEqual(
                        [f["code"] for f in result["outputs"]["report"]["findings"]],
                        [f["code"] for f in baseline["findings"]] + expected_missing,
                    )
                    self.assertEqual(
                        [r[0] for r in observed.seen].count("retain"),
                        int("html" in absent) + 5 * int("json" in absent),
                    )
                    self.assertEqual(
                        [r[0] for r in observed.seen].count("check_item"),
                        9
                        + 14 * int("html" not in absent)
                        + 9 * int("json" not in absent),
                    )
                    self.assertFalse(Path(observed.seen[0][2]["state"]["tmp"]).exists())

                # Real report bytes exercise all fixed checks even after findings.
                def degraded(op, args, value):
                    if op == "builder":
                        state = value["state"]
                        p = state["payload"]
                        Path(p["artifacts"]["html"]).write_text("")
                        Path(p["artifacts"]["json"]).write_text("{}")
                        Path(
                            state["output_dir"], "selected_examples.cleaned.json"
                        ).write_text("mathformerphysics_output")

                result, observed = await run(hook=degraded)
                self.assertEqual(result["status"], "accepted", result)
                codes = [f["code"] for f in result["outputs"]["report"]["findings"]]
                self.assertEqual(
                    codes,
                    [f["code"] for f in baseline["findings"]]
                    + ["obsolete_self_output_not_removed"]
                    + ["html_marker_missing"] * 14
                    + ["qualitative_reviewers_missing"]
                    + ["metric_criterion_missing"] * 5
                    + ["critic_profile_missing"] * 4
                    + [
                        "critic_evidence_missing",
                        "invoked_dependency_excerpts_missing",
                        "judge_synthesis_not_loaded",
                        "judge_synthesis_summary_not_loaded",
                    ],
                )
                self.assertEqual(len(result["calls"]), 41)

                # A genuine failed child yields empty stdout payload, ordered findings,
                # no retries, and normal ok=false completion (native main => exit 3).
                def bad_input(op, args, value):
                    if op == "fixtures":
                        Path(value["state"]["input_json"]).write_text("{")

                result, observed = await run(hook=bad_input)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(observed.seen[1][2]["state"]["payload"], {})
                self.assertNotEqual(observed.seen[1][2]["state"]["code"], 0)
                self.assertIn("JSONDecodeError", observed.seen[1][2]["state"]["stderr"])
                self.assertEqual(
                    [f["code"] for f in result["outputs"]["report"]["findings"]][:4],
                    [
                        "report_builder_failed",
                        "report_builder_not_ok",
                        "reference_role_not_non_gold",
                        "foundations_not_included",
                    ],
                )
                self.assertEqual([r[0] for r in observed.seen].count("builder"), 1)
                # Uncaught report parse and first-candidate shape errors stop once.
                for contents, stop in [
                    ("{", "start_report"),
                    ('{"cases": []}', "finish_report"),
                ]:

                    def corrupt(op, args, value):
                        if op == "builder":
                            Path(
                                value["state"]["payload"]["artifacts"]["json"]
                            ).write_text(contents)

                    result, observed = await run(hook=corrupt)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(result["calls"][-1]["operation"], stop)
                    self.assertNotIn("finish", [r[0] for r in observed.seen])
                    self.assertFalse(Path(observed.seen[0][2]["state"]["tmp"]).exists())
                # Exact bounds completed above. Change only test contract bounds to
                # prove PRISM exhaustion and host call-budget failures propagate.
                exhausted = deepcopy(document)
                exhausted["flow"]["steps"][3]["max_iterations"] = 8
                result, observed = await run(exhausted)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), 11)
                self.assertEqual(result["failure_disposition"], "fail")
                abandoned.append(Path(observed.seen[0][2]["state"]["tmp"]))
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
                abandoned.append(Path(observed.seen[0][2]["state"]["tmp"]))
                fixture = await remote.call(PREFIX + "fixtures", {})
                changed = deepcopy(fixture)
                changed["state"]["input_json"] = str(
                    Path(gettempdir()) / "mathformer-test-fixtures/arbitrary/input.json"
                )
                with self.assertRaises(MCPConnectionError):
                    await remote.call(PREFIX + "builder", changed)
                self.assertFalse(Path(fixture["state"]["tmp"]).exists())
                with self.assertRaises(MCPConnectionError):
                    await remote.call(PREFIX + "builder", fixture)
                fixture = await remote.call(PREFIX + "fixtures", {})
                with self.assertRaises(MCPConnectionError):
                    await remote.call(PREFIX + "finish", fixture)
                self.assertFalse(Path(fixture["state"]["tmp"]).exists())
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        for path in abandoned:
            self.assertFalse(path.exists(), str(path))
        if failure:
            raise failure


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ComparativeSmokeTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(
        0
        if result.wasSuccessful()
        and result.testsRun > 0
        and len(result.skipped) < result.testsRun
        else 1
    )
