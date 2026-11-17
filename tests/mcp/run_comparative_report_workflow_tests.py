#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native/original parity, real MCP registration, and Lunar PRISM execution.

Only compiler subprocess and provider network boundaries have test substitutes.
All fixtures and generated reports live in disposable directories.
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
    str(ROOT / "tests/mcp/fixtures"),
]
import asyncio
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import io
import json
import re
import socket
import subprocess
import tempfile
import types
import unittest
import yaml
from comparative_report_tools import source
from comparative_report_boundaries import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_formalphysics_comparative_report_workflow/workflow.yaml"
PREFIX = "mathformer_comparative_report_"


def original():
    module = types.ModuleType("comparative_original_oracle")
    # Retain native resource resolution while running the frozen original code.
    module.__file__ = str(source().__file__)
    path = ROOT / "tests/mcp/fixtures/comparative_report_builder_original.py.txt"
    exec(compile(path.read_text(), str(path), "exec"), module.__dict__)
    return module


def fixture(root, records=None):
    root.mkdir(parents=True)
    base = root / "MathformerPhysicsLib/Lean"
    base.mkdir(parents=True)
    (base / "Foundations.lean").write_text(
        "namespace Foundation\ndef mass : Nat := 1\nend Foundation\n"
    )
    if records is None:
        records = [
            dict(
                FS_index=0,
                question="Show mass equals one",
                answer="mass derivation",
                mathformerphysics_output="obsolete",
                formaldiscovery_output="-- fixture-error\ntheorem mass : (1 : Nat) = 1 := by rfl\n",
            ),
            dict(
                FS_index=1,
                question="Show energy equals one",
                answer="energy reference",
                formaldiscovery_output="-- fixture-timeout\ntheorem energy : (1 : Nat) = 1 := by rfl\n",
            ),
            dict(FS_index=2, question="No repository artifact", answer="reference"),
        ]
    for index in (0, 1):
        d = base / f"formalphysics_{index:04d}"
        d.mkdir()
        (d / "MathformerPhysics.lean").write_text(
            "import MathformerPhysicsLib.Lean.Foundations\n-- Source mass\ntheorem mass : (1 : Nat) = 1 := by rfl\n"
        )
    (root / "input.json").write_text(json.dumps(records))
    (root / "judges.json").write_text(
        json.dumps(
            {
                "results": [
                    dict(
                        case_id="formalphysics_0000",
                        candidate_id="current_mathformer_lean",
                        judge_id="prefix.lean_tp_judge",
                        verdict="fixture supplied",
                    ),
                    dict(
                        case_id="formalphysics_0000",
                        candidate_id="current_mathformer_lean",
                        judge_id="lean_tp_judge",
                        verdict="last supplied wins",
                    ),
                ]
            }
        )
    )
    (root / "synthesis.json").write_text(
        json.dumps({"approaches": {}, "judge_review_synthesis": {}})
    )
    return root


def argv(root, compile=True, keep=False):
    result = [
        "--input-json",
        str(root / "input.json"),
        "--output-dir",
        str(root / "out"),
        "--repo-root",
        str(root),
        "--lean-cwd",
        str(root),
        "--timeout",
        "7",
        "--codex-results-json",
        str(root / "judges.json"),
        "--synthesis-report-json",
        str(root / "synthesis.json"),
        "--json",
    ]
    if compile:
        result += ["--execute-lean"]
    if keep:
        result += ["--keep-obsolete-self-output"]
    return result


def normalize(value):
    if isinstance(value, str):
        value = re.sub(
            r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?\+00:00", "<date>", value
        )
        return re.sub(
            r'[^\s"\']*/tmp[^/\s"\']+/Candidate\.lean', "<temporary-candidate>", value
        )
    if isinstance(value, list):
        return [normalize(v) for v in value]
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    return value


def outputs(root):
    return {
        p.name: normalize(p.read_text())
        for p in (root / "out").rglob("*")
        if p.is_file()
    }


def run_main(module, args):
    out = io.StringIO()
    with redirect_stdout(out):
        code = module.main(args)
    return code, json.loads(out.getvalue())


def assets(doc):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in doc["provenance"]["sources"]
    ]


class Observed:
    def __init__(self, remote):
        self.remote, self.seen = remote, []

    async def tools(self):
        return await self.remote.tools()

    async def call(self, tool, arguments):
        result = await self.remote.call(tool, arguments)
        recorded = deepcopy(result)
        if "state" in recorded and "native_json" in recorded["state"]:
            recorded["state"]["data"] = json.loads(recorded["state"]["native_json"])[
                "data"
            ]
        self.seen.append((tool.removeprefix(PREFIX), deepcopy(arguments), recorded))
        return result


class ComparativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = subprocess.run, socket.create_connection, socket.socket.connect
        install()

    @classmethod
    def tearDownClass(cls):
        subprocess.run, socket.create_connection, socket.socket.connect = cls.saved

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="comparative-workflow-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def test_original_entrypoint_parity_and_native_failures(self):
        native, oracle = source(), original()
        root = fixture(self.directory / "parity")
        for compile, keep in [(True, False), (False, True)]:
            old = run_main(oracle, argv(root, compile, keep))
            old_files = outputs(root)
            new = run_main(native, argv(root, compile, keep))
            self.assertEqual(normalize(old), normalize(new))
            self.assertEqual(old_files, outputs(root))
            self.assertEqual(len(old_files), 10)
        for bad in ["{}", "[null]", "{"]:
            (root / "input.json").write_text(bad)
            for module in (native, oracle):
                with self.assertRaises((ValueError, AttributeError, TypeError)):
                    run_main(module, argv(root))
        (root / "input.json").write_text("[{}]")
        for invalid_results in ["{}", '[{"case_id": []}]']:
            (root / "judges.json").write_text(invalid_results)
            for module in (native, oracle):
                with self.assertRaises((ValueError, TypeError)):
                    run_main(module, argv(root))
        (root / "judges.json").write_text("[]")
        with self.assertRaises(SystemExit):
            native.main([])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            native.main(["--unknown"])
        # Native traversal transports state through JSON without losing accumulators.
        (root / "input.json").write_text("[]")
        state = native.prepare_report(native.parse_args(argv(root)))
        self.assertFalse(state["has_cases"])
        self.assertEqual(native.assemble_report(state)["summary"]["case_count"], 0)

    def test_registered_tools_lunar_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_physics_lean_formalphysics_comparative_report_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path[:0]=["scripts","tests/mcp/fixtures"];from comparative_report_boundaries import install;install();from mcp_server import mcp;mcp.run(transport="stdio")'
        packages = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
        env = {"PYTHONPATH": os.pathsep.join(packages), "PYTHONDONTWRITEBYTECODE": "1"}
        async with manager.open(
            "comparative-report",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            env,
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile_doc(doc, inventory=None):
                    snapshot = assets(doc)
                    result = compile_workflow(
                        "mcp:comparative-report",
                        workflow_documents([DESCRIPTOR], snapshot)[0],
                        tools if inventory is None else inventory,
                    )
                    return result, snapshot

                workflow, snapshot = compile_doc(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                self.assertFalse(compile_doc(document, [])[0]["runnable"])

                async def allow():
                    pass

                async def run(root, doc=None, args=None):
                    compiled, received = (
                        compile_doc(doc) if doc else (workflow, snapshot)
                    )
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    observed = Observed(remote)
                    result = await execute(
                        compiled,
                        received,
                        {"extra_args": argv(root) if args is None else args},
                        observed,
                        allow,
                    )
                    return result, observed

                root = fixture(self.directory / "runtime")
                oracle = run_main(original(), argv(root))
                oracle_files = outputs(root)
                result, observed = await run(root)
                self.assertEqual(result["status"], "accepted", result)
                completion = result["outputs"]["result"]
                self.assertEqual(
                    normalize(completion),
                    normalize({"exit_code": oracle[0], "payload": oracle[1]}),
                )
                self.assertEqual(outputs(root), oracle_files)
                report = json.loads(
                    Path(completion["payload"]["artifacts"]["json"]).read_text()
                )
                self.assertEqual(report["summary"]["case_count"], 3)
                self.assertEqual(report["summary"]["candidate_count"], 5)
                self.assertEqual(len(report["codex_exec_judge_prompts"]), 40)
                self.assertTrue(report["judge_synthesis"]["available"])
                self.assertEqual(report["foundations_inventory"]["totals"]["files"], 1)
                self.assertEqual(
                    [
                        c["lean_compile"]["status"]
                        for c in report["cases"][0]["candidates"]
                    ],
                    ["fail", "pass"],
                )
                self.assertEqual(
                    report["cases"][1]["candidates"][0]["lean_compile"]["status"],
                    "timeout",
                )
                self.assertEqual(
                    report["cases"][2]["candidates"][0]["lean_compile"]["status"],
                    "not_applicable",
                )
                self.assertEqual(
                    report["cases"][0]["best_solution"]["candidate_id"],
                    "current_mathformer_lean",
                )
                supplied = [
                    p
                    for p in report["codex_exec_judge_prompts"]
                    if p["result_status"] == "completed"
                ]
                self.assertEqual(len(supplied), 1)
                self.assertEqual(supplied[0]["result"]["verdict"], "last supplied wins")
                self.assertNotIn(
                    "mathformerphysics_output",
                    (root / "out/selected_examples.cleaned.json").read_text(),
                )
                self.assertTrue(result["replay_artifacts"])
                self.assertTrue(result["runtime"]["provenance"])
                expected = (
                    ["parse", "prepare"]
                    + ["open_case", "candidate", "candidate", "close_case"] * 2
                    + ["open_case", "candidate", "close_case", "assemble", "write"]
                )
                self.assertEqual([r[0] for r in observed.seen], expected)
                candidate_rows = [
                    r[2]["state"] for r in observed.seen if r[0] == "candidate"
                ]
                self.assertEqual(
                    [r["data"]["candidate_cursor"] for r in candidate_rows],
                    [1, 2, 1, 2, 1],
                )
                self.assertEqual(
                    [len(r["data"]["codex_prompts"]) for r in candidate_rows],
                    [8, 16, 24, 32, 40],
                )
                close_rows = [
                    r[2]["state"] for r in observed.seen if r[0] == "close_case"
                ]
                self.assertEqual(
                    [r["has_cases"] for r in close_rows], [True, True, False]
                )
                self.assertEqual(
                    [len(r["data"]["cases"]) for r in close_rows], [1, 2, 3]
                )
                for c in result["calls"]:
                    self.assertTrue(c["transport_call_performed"])
                    self.assertEqual(len(c["input_digest"]), 64)
                    self.assertEqual(len(c["output_digest"]), 64)
                # Empty input bypasses every candidate and still writes native outputs.
                empty = fixture(self.directory / "empty", [])
                result, seen = await run(empty)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"]["result"]["payload"]["summary"]["case_count"], 0
                )
                self.assertEqual(
                    [r[0] for r in seen.seen],
                    ["parse", "prepare", "retain", "assemble", "write"],
                )
                # No compile request keeps provisional evidence and ingests supplied judges.
                provisional = fixture(self.directory / "provisional")
                result, _ = await run(provisional, args=argv(provisional, False, True))
                self.assertEqual(result["status"], "accepted", result)
                p = json.loads(
                    Path(
                        result["outputs"]["result"]["payload"]["artifacts"]["json"]
                    ).read_text()
                )
                self.assertEqual(
                    p["cases"][0]["candidates"][0]["lean_compile"]["status"], "not_run"
                )
                self.assertIn(
                    "mathformerphysics_output",
                    (provisional / "out/selected_examples.cleaned.json").read_text(),
                )
                # Exact bound is successful; one fewer iteration fails before assembly/write.
                exact = deepcopy(document)
                exact["flow"]["steps"][2]["max_iterations"] = 11
                result, _ = await run(root, doc=exact)
                self.assertEqual(result["status"], "accepted", result)
                exhausted = deepcopy(exact)
                exhausted["flow"]["steps"][2]["max_iterations"] = 10
                bounded = fixture(self.directory / "exhausted")
                result, seen = await run(bounded, doc=exhausted)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertIn("exhaust", str(result).lower())
                self.assertEqual([r[0] for r in seen.seen][-1], "candidate")
                self.assertEqual(
                    set(outputs(bounded)), {"selected_examples.cleaned.json"}
                )
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 3
                result, seen = await run(root, doc=budget)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(seen.seen), 3)
                self.assertIn("budget", str(result).lower())
                # Unhandled compiler exception aborts immediately, while fail/timeout above continue.
                broken = fixture(self.directory / "broken")
                records = json.loads((broken / "input.json").read_text())
                records[0]["formaldiscovery_output"] = "-- fixture-crash"
                (broken / "input.json").write_text(json.dumps(records))
                result, seen = await run(broken)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(result["calls"][-1]["operation"], "candidate")
                self.assertEqual(
                    [r[0] for r in seen.seen], ["parse", "prepare", "open_case"]
                )
                self.assertEqual(
                    set(outputs(broken)), {"selected_examples.cleaned.json"}
                )
                for content in ["{}", "{", "[null]"]:
                    invalid = fixture(self.directory / ("invalid" + str(len(content))))
                    (invalid / "input.json").write_text(content)
                    result, seen = await run(invalid)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["calls"][-1]["operation"], "prepare")
                    self.assertEqual([r[0] for r in seen.seen], ["parse"])
                huge = fixture(self.directory / "huge", [{}] * 1001)
                result, _ = await run(huge)
                self.assertEqual(result["status"], "failed", result)
                self.assertFalse((huge / "out").exists())
                for args in [[], ["--unknown"]]:
                    result, _ = await run(root, args=args)
                    self.assertEqual(result["status"], "failed", result)
                # Output errors keep the native partial-write order and abort.
                unwritable = fixture(self.directory / "write-failure", [])
                (unwritable / "out/comparative_report.html").mkdir(parents=True)
                with self.assertRaises(IsADirectoryError):
                    run_main(original(), argv(unwritable))
                partial = outputs(unwritable)
                result, seen = await run(unwritable)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["calls"][-1]["operation"], "write")
                self.assertEqual(outputs(unwritable), partial)
                self.assertEqual(
                    set(partial),
                    {"selected_examples.cleaned.json", "comparative_report.json"},
                )
                # Missing input/synthesis reads fail before any downstream evaluations.
                missing = fixture(self.directory / "missing-input")
                (missing / "input.json").unlink()
                result, _ = await run(missing)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["calls"][-1]["operation"], "prepare")
                self.assertFalse((missing / "out").exists())
                missing_synthesis = fixture(self.directory / "missing-synthesis")
                (missing_synthesis / "synthesis.json").unlink()
                result, _ = await run(missing_synthesis)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["calls"][-1]["operation"], "prepare")
                self.assertEqual(
                    set(outputs(missing_synthesis)), {"selected_examples.cleaned.json"}
                )
                # Self-test owns a fixed native fixture and reads repository Foundations.
                # Preserve its assertions even when this checkout lacks the legacy root.
                try:
                    expected_test = run_main(original(), ["--self-test", "--json"])
                except AssertionError:
                    expected_test = None
                    with self.assertRaises(AssertionError):
                        run_main(source(), ["--self-test", "--json"])
                result, seen = await run(root, args=["--self-test", "--json"])
                self.assertEqual(
                    [r["operation"] for r in result["calls"]],
                    ["parse", "empty", "retain", "test"],
                )
                if expected_test is None:
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    self.assertIsNone(result["outputs"])
                else:
                    self.assertEqual(result["status"], "accepted")
                    self.assertTrue(result["outputs"]["result"]["payload"]["ok"])
                    for path in result["outputs"]["result"]["payload"][
                        "artifacts"
                    ].values():
                        self.assertFalse(Path(path).exists())
                # Tool-level ordering checks and missing binding qualification.
                with self.assertRaises(Exception):
                    await remote.call(
                        PREFIX + "candidate",
                        {
                            "state": {
                                k: v for k, v in close_rows[-1].items() if k != "data"
                            }
                        },
                    )
                removed = [t for t in tools if t["name"] != PREFIX + "candidate"]
                self.assertFalse(compile_doc(document, removed)[0]["runnable"])
            except Exception:
                import traceback

                traceback.print_exc()
                raise
        self.assertFalse(manager.active)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ComparativeTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(
        0
        if result.wasSuccessful()
        and result.testsRun > 0
        and len(result.skipped) < result.testsRun
        else 1
    )
