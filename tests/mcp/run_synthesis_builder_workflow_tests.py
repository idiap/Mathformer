#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native/original parity and registered MCP through real Lunar/PRISM.

All evidence is synthetic and all reports are disposable. Only external
provider/compiler boundaries are substituted; no source step is replaced.
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
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
import asyncio
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import re
import tempfile
import types
import unittest
import yaml
from synthesis_builder_tools import source, unpack
from synthesis_builder_boundaries import install, restore
from judge_synthesis_report_tools import source as fixture_source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_formalphysics_judge_synthesis_report_workflow/workflow.yaml"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/judge-synthesis-report.workflow.json"
)
PREFIX = "mathformer_synthesis_builder_"


def original():
    module = types.ModuleType("synthesis_original_oracle")
    module.__file__ = str(source().__file__)
    path = ROOT / "tests/mcp/fixtures/synthesis_builder_original.py.txt"
    exec(compile(path.read_text(), str(path), "exec"), module.__dict__)
    return module


def normalize(text):
    return re.sub(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?\+00:00", "<date>", text)


def outputs(root):
    return {
        p.name: normalize(p.read_text())
        for p in (root / "out").iterdir()
        if p.is_file()
    }


def fixture(root, extras=True, tied=False):
    fixture_source().write_comparative_report(root / "report.json")
    fixture_source().write_codex_results(root / "results.json")
    if tied:
        report = json.loads((root / "report.json").read_text())
        for candidate in report["cases"][0]["candidates"]:
            candidate["scores"] = {
                m: fixture_source().score_block(3) for m in fixture_source().METRICS
            }
        (root / "report.json").write_text(json.dumps(report))
    if extras:
        directory = root / "results"
        (directory / "nested").mkdir(parents=True)
        (directory / "a.json").write_text("{bad optional JSON")
        result = dict(
            case_id="formalphysics_0000",
            candidate_id="current_mathformer_lean",
            judge_id="physics_expert",
            scores={"overall": {"score": 1}},
            note="last wins",
        )
        # JSONL silently skips unparseable lines; stdout wrapper is unwrapped.
        (directory / "nested/b.jsonl").write_text(
            "bad line\n"
            + json.dumps(
                dict(result, note="superseded", scores={"overall": {"score": 2}})
            )
            + "\n"
            + json.dumps({"stdout": json.dumps(result)})
            + "\n"
        )
        unmatched = [dict(result, case_id=f"absent_{i}") for i in range(30)]
        (directory / "c.json").write_text(json.dumps(unmatched))
    return root


def argv(root, extras=True, supplied=True, json_output=True):
    value = [
        "--comparative-report",
        str(root / "report.json"),
        "--output-dir",
        str(root / "out"),
    ]
    if supplied:
        value += ["--codex-results-json", str(root / "results.json")]
    if extras:
        value += ["--codex-results-dir", str(root / "results")]
    if json_output:
        value += ["--json"]
    return value


def main_result(module, args):
    out = io.StringIO()
    with redirect_stdout(out):
        code = module.main(args)
    return code, out.getvalue()


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


class Observed:
    def __init__(self, remote):
        self.remote, self.seen = remote, []

    async def tools(self):
        return await self.remote.tools()

    async def call(self, tool, arguments):
        result = await self.remote.call(tool, arguments)
        self.seen.append(
            (tool.removeprefix(PREFIX), deepcopy(arguments), deepcopy(result))
        )
        return result


class SynthesisBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fences = tempfile.TemporaryDirectory()
        cls.saved_pythonpath = os.environ.get("PYTHONPATH")
        (Path(cls.fences.name) / "sitecustomize.py").write_text(
            "from synthesis_builder_boundaries import install\ninstall()\n"
        )
        packages = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
        os.environ["PYTHONPATH"] = os.pathsep.join(
            [cls.fences.name, str(ROOT / "tests/mcp/fixtures"), *packages]
        )
        cls.saved = install()

    @classmethod
    def tearDownClass(cls):
        restore(cls.saved)
        if cls.saved_pythonpath is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = cls.saved_pythonpath
        cls.fences.cleanup()

    def test_original_parity_and_finite_native_branches(self):
        native, oracle = source(), original()
        for extras, supplied, tied in [
            (True, True, False),
            (False, False, True),
            (False, True, False),
        ]:
            with tempfile.TemporaryDirectory() as raw:
                root = fixture(Path(raw), extras, tied)
                args = argv(root, extras, supplied, json_output=supplied)
                expected = main_result(oracle, args)
                expected_files = outputs(root)
                actual = main_result(native, args)
                self.assertEqual(actual, expected)
                self.assertEqual(outputs(root), expected_files)
                self.assertEqual(
                    set(expected_files),
                    {
                        "synthesis_report.json",
                        "synthesis_report.md",
                        "synthesis_report.html",
                        "synthesis_todos.md",
                    },
                )
        for module in (oracle, native):
            with self.assertRaisesRegex(SystemExit, "--comparative-report is required"):
                module.main([])
            with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
                module.main(["--unknown"])
            for flags in (["--self-test"], ["--self-test", "--json"]):
                code, text = main_result(module, flags)
                self.assertEqual(code, 0)
                if "--json" in flags:
                    result = json.loads(text)
                    self.assertTrue(result["ok"])
                    self.assertEqual(len(result["artifacts"]), 4)
                    self.assertTrue(
                        all(not Path(p).exists() for p in result["artifacts"].values())
                    )
                else:
                    self.assertEqual(text, "ok: True\n")
        ids = list(native.ASPECTS)
        for gap, word in [(0, "tied"), (0.5, "slightly"), (0.75, "clear")]:
            approaches = {
                "z_first": {"aspect_scores": dict.fromkeys(ids, 3 + gap)},
                "a_second": {"aspect_scores": dict.fromkeys(ids, 3)},
            }
            self.assertEqual(
                native.compare_aspects(approaches), oracle.compare_aspects(approaches)
            )
            state = native.pack_aspects(approaches)
            history = []
            for i in range(5):
                _, done = native.compare_next_aspect(state)
                history.append(deepcopy(state))
                self.assertEqual(done, i == 4)
                self.assertEqual(state["rows"][-1]["winner"], "z_first")
                self.assertIn(word, state["rows"][-1]["interpretation"])
                self.assertEqual(state["index"], i + 1)
                self.assertEqual(len(state["rows"]), i + 1)
            before = deepcopy(state)
            with self.assertRaises(IndexError):
                native.compare_next_aspect(state)
            self.assertEqual(state, before)
            self.assertEqual([s["index"] for s in history], [1, 2, 3, 4, 5])
        self.assertEqual(
            native.compare_aspects({"single": approaches["z_first"]})[0]["gap"], 0
        )
        with self.assertRaises(IndexError):
            native.compare_aspects({})
        # External boundaries are closed in this process too.
        import socket
        import subprocess

        for invoke in (
            lambda: subprocess.run(["lean", "--version"]),
            lambda: socket.create_connection(("example.invalid", 443)),
        ):
            with self.assertRaisesRegex(
                AssertionError, "provider or external compiler"
            ):
                invoke()

    def test_generator_and_provenance(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document, json.loads(AUTHORED.read_text()))
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(
            str(source().__file__),
            [str(ROOT / r["path"]) for r in document["provenance"]["sources"]],
        )
        directory = ROOT / "skills/control/workflow-contract-validator/scripts"
        sys.path.insert(0, str(directory))
        try:
            spec = importlib.util.spec_from_file_location(
                "_synthesis_normalizer", directory / "normalize_workflows.py"
            )
            generator = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(generator)
            self.assertEqual(
                [d for d in generator.inventory() if d["id"] == document["id"]],
                [document],
            )
        finally:
            sys.path.remove(str(directory))

    def test_registered_tools_real_lunar_runtime_and_failures(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"],
            "hub_physics_lean_formalphysics_judge_synthesis_report_workflow",
        )
        self.assertEqual(document["lifecycle"], "active")
        manager = SessionManager()
        failure = None
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "synthesis-builder",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {"PYTHONPATH": os.environ["PYTHONPATH"]},
        ) as remote:
            try:
                inventory = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile_doc(doc, tools=None):
                    snapshot = assets(doc)
                    workflow = compile_workflow(
                        "mcp:synthesis-builder",
                        workflow_documents([DESCRIPTOR], snapshot)[0],
                        inventory if tools is None else tools,
                    )
                    return workflow, snapshot

                workflow, snapshot = compile_doc(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                self.assertFalse(compile_doc(document, [])[0]["runnable"])
                self.assertFalse(
                    compile_doc(
                        document, [t for t in inventory if t["name"] != PREFIX + "emit"]
                    )[0]["runnable"]
                )

                async def allow():
                    pass

                async def run(args, doc=None):
                    w, a = compile_doc(doc) if doc else (workflow, snapshot)
                    self.assertTrue(w["runnable"], w["diagnostics"])
                    observed = Observed(remote)
                    result = await execute(w, a, {"argv": args}, observed, allow)
                    return result, observed.seen

                for extras, supplied, tied in [
                    (True, True, False),
                    (False, False, True),
                ]:
                    with tempfile.TemporaryDirectory() as raw:
                        root = fixture(Path(raw), extras, tied)
                        args = argv(root, extras, supplied, json_output=supplied)
                        expected = main_result(original(), args)
                        expected_files = outputs(root)
                        result, seen = await run(args)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            result["outputs"]["result"]["returncode"], expected[0]
                        )
                        if supplied:
                            self.assertEqual(
                                result["outputs"]["result"]["printed_result"],
                                json.loads(expected[1]),
                            )
                        self.assertEqual(outputs(root), expected_files)
                        self.assertEqual(
                            [s[0] for s in seen],
                            [
                                "parse_cli",
                                "load_inputs",
                                "attach_results",
                                "summarize_approaches",
                                "pack_aspects",
                            ]
                            + ["compare_next_aspect"] * 5
                            + ["finish_synthesis", "emit"],
                        )
                        self.assertEqual(len(result["calls"]), 12)
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["runtime"]["effect_records"])
                        states = [
                            (unpack(v["state"]), v["done"])
                            for op, _, v in seen
                            if op == "compare_next_aspect"
                        ]
                        self.assertEqual(
                            [s["index"] for s, _ in states], [1, 2, 3, 4, 5]
                        )
                        self.assertEqual(
                            [done for _, done in states], [False] * 4 + [True]
                        )
                        self.assertEqual(
                            [len(s["rows"]) for s, _ in states], [1, 2, 3, 4, 5]
                        )
                        synthesis = unpack(seen[-2][2]["synthesis"])
                        self.assertEqual(
                            list(synthesis["approaches"]),
                            ["external_formaldiscovery", "current_mathformer_lean"],
                        )
                        self.assertEqual(len(synthesis["aspect_comparison"]), 5)
                        todos = synthesis["synthesis_todos"]
                        self.assertEqual(
                            [t["id"] for t in todos],
                            [f"FPSYN-{i:03d}" for i in range(1, len(todos) + 1)],
                        )
                        self.assertTrue(
                            any(
                                t["actionability"] == "external_input_required"
                                for t in todos
                            )
                        )
                        self.assertTrue(
                            any(
                                t["status"] == "external_reference_not_repo_actionable"
                                for t in todos
                            )
                        )
                        if extras:
                            loaded = unpack(seen[1][2]["loaded"])
                            attached = unpack(seen[2][2]["report"])
                            self.assertEqual(len(loaded["errors"]), 1)
                            self.assertEqual(
                                [Path(p).name for p in loaded["files"]],
                                ["results.json", "a.json", "c.json", "b.jsonl"],
                            )
                            ingestion = attached["codex_exec_result_ingestion"]
                            self.assertEqual(ingestion["unmatched_result_count"], 30)
                            self.assertEqual(len(ingestion["unmatched_results"]), 25)
                            self.assertEqual(ingestion["matched_result_count"], 3)
                            matched = [
                                p
                                for p in attached["codex_exec_judge_prompts"]
                                if p.get("result", {}).get("note") == "last wins"
                            ]
                            self.assertEqual(len(matched), 1)
                            self.assertEqual(
                                matched[0]["result"]["scores"]["overall"]["score"], 1
                            )
                            self.assertEqual(
                                synthesis["judge_review_synthesis"][
                                    "codex_exec_results_ingested"
                                ],
                                3,
                            )
                            agreement = synthesis["judge_review_synthesis"][
                                "codex_exec_disagreement_patterns"
                            ]["agreement_counts"]
                            self.assertEqual(agreement["partial_result_set"], 1)
                            self.assertEqual(
                                agreement["agrees_with_deterministic_best"], 1
                            )
                            self.assertTrue(
                                synthesis["judge_review_synthesis"][
                                    "codex_exec_disagreement_patterns"
                                ]["large_generated_vs_deterministic_score_deltas"]
                            )
                        else:
                            self.assertNotIn(
                                "codex_exec_result_ingestion",
                                unpack(seen[2][2]["report"]),
                            )
                            self.assertTrue(
                                all(
                                    row["winner"] == "external_formaldiscovery"
                                    and row["gap"] == 0
                                    for row in synthesis["aspect_comparison"]
                                )
                            )
                for flags in (
                    ["--self-test"],
                    [
                        "--self-test",
                        "--json",
                        "--comparative-report",
                        str(Path(gettempdir()) / "mathformer-test-fixtures/absent"),
                    ],
                ):
                    result, seen = await run(flags)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        [s[0] for s in seen],
                        ["parse_cli", "empty_aspects", "retain_aspects", "self_test"],
                    )
                    self.assertTrue(result["outputs"]["result"]["printed_result"]["ok"])
                    self.assertTrue(
                        all(
                            not Path(p).exists()
                            for p in result["outputs"]["result"]["printed_result"][
                                "artifacts"
                            ].values()
                        )
                    )
                # Native early errors propagate and never reach synthesis or output.
                for args, successes in [([], ["parse_cli"]), (["--unknown"], [])]:
                    result, seen = await run(args)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual([s[0] for s in seen], successes)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    self.assertEqual(
                        result["calls"][-1]["operation"],
                        "load_inputs" if args == [] else "parse_cli",
                    )
                for mode in (
                    "parse_failure",
                    "empty_candidates",
                    "write_failure",
                    "partial_write",
                    "loop_exhaustion",
                    "budget",
                ):
                    with tempfile.TemporaryDirectory() as raw:
                        root = fixture(Path(raw), False)
                        doc = deepcopy(document)
                        if mode == "parse_failure":
                            (root / "report.json").write_text("{")
                        if mode == "empty_candidates":
                            (root / "report.json").write_text('{"cases":[]}')
                        if mode == "write_failure":
                            (root / "out").write_text("file blocks output directory")
                        if mode == "partial_write":
                            (root / "out/synthesis_report.md").mkdir(parents=True)
                            with self.assertRaises(IsADirectoryError):
                                main_result(original(), argv(root, False))
                            oracle_partial = outputs(root)
                        if mode == "loop_exhaustion":
                            doc["flow"]["steps"][2]["max_iterations"] = 4
                        if mode == "budget":
                            doc["policy"]["limits"]["max_operation_calls"] = 11
                        result, seen = await run(argv(root, False), doc)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertNotIn("emit", [s[0] for s in seen])
                        if mode == "loop_exhaustion":
                            self.assertEqual(result["failure_disposition"], "fail")
                            self.assertEqual(len(result["calls"]), 9)
                            self.assertEqual(unpack(seen[-1][2]["state"])["index"], 4)
                        if mode == "budget":
                            self.assertEqual(
                                sum(
                                    bool(c.get("transport_call_performed"))
                                    for c in result["calls"]
                                ),
                                11,
                            )
                            self.assertIn("budget", str(result).lower())
                        if mode == "partial_write":
                            self.assertEqual(result["calls"][-1]["operation"], "emit")
                            self.assertEqual(result["calls"][-1]["status"], "rejected")
                            self.assertEqual(outputs(root), oracle_partial)
                            self.assertEqual(
                                set(oracle_partial), {"synthesis_report.json"}
                            )
                        elif mode != "write_failure":
                            self.assertFalse((root / "out").exists())
                # The descriptor ceiling also stops execution before an operation.
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                w, a = compile_doc(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(w, a, {"argv": ["--self-test"]}, remote, pending)
                # A sixth call surfaces native iterator exhaustion and leaves no retry.
                state = await remote.call(
                    PREFIX + "pack_aspects",
                    {
                        "approaches": {
                            "native_json": json.dumps({"only": {"aspect_scores": {}}})
                        }
                    },
                )
                for _ in range(5):
                    state = await remote.call(
                        PREFIX + "compare_next_aspect", {"state": state["state"]}
                    )
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "compare_next_aspect", {"state": state["state"]}
                    )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure
        readonly_server = 'import sys;sys.path.insert(0,"scripts");import mcp_server;mcp_server._READONLY=True;mcp=mcp_server.mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "synthesis-readonly",
            StdioConfig(
                command=sys.executable, args=["-c", readonly_server], cwd=str(ROOT)
            ),
            {"PYTHONPATH": os.environ["PYTHONPATH"]},
        ) as readonly:
            try:
                result = await execute(
                    workflow, snapshot, {"argv": ["--self-test"]}, readonly, allow
                )
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(result["calls"][-1]["operation"], "self_test")
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                with tempfile.TemporaryDirectory() as raw:
                    root = fixture(Path(raw), False)
                    result = await execute(
                        workflow, snapshot, {"argv": argv(root, False)}, readonly, allow
                    )
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["calls"][-1]["operation"], "emit")
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    self.assertFalse((root / "out").exists())
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SynthesisBuilderTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(
        0
        if result.wasSuccessful() and result.testsRun > 0 and not result.skipped
        else 1
    )
