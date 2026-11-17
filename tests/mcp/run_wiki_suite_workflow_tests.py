#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native suite equivalence and real MCP/Lunar/PRISM compile-execute tests."""

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
from wiki_suite_tools import source, create_server
from wiki_suite_boundary import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
from mcp_connections.workflow_contract.validator import validate

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_lean_wiki_level_suite_workflow/workflow.yaml"


def oracle():
    path = ROOT / "tests/mcp/fixtures/wiki_suite_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "wiki_oracle", SourceFileLoader("wiki_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.REPO_ROOT = ROOT
    return module


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


def stable(value):
    # Compare source data without replacing the source clock or logger.
    if isinstance(value, dict):
        return {
            key: stable(item)
            for key, item in value.items()
            if key not in ("generated_at_utc", "duration_ms")
        }
    if isinstance(value, list):
        return [stable(item) for item in value]
    return value


def events(path):
    # Source logger owns timestamps; compare ordered semantic records.
    rows = (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )

    def normalize(value):
        if isinstance(value, dict):
            return {
                key: normalize(item)
                for key, item in value.items()
                if key
                not in (
                    "skill_call_id",
                    "timestamp_utc",
                    "timestamp_unix_ms",
                    "duration_ms",
                )
            }
        if isinstance(value, list):
            return [normalize(item) for item in value]
        return value

    return [(row.get("step"), normalize(row.get("payload"))) for row in rows]


class WikiSuiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.native = source()
        self.original = oracle()
        self.manifest = self.directory / "manifest.json"
        self.gold = self.directory / "gold.lean"
        self.gold.write_text("import Mathlib\n theorem fixture : True := by trivial\n")
        self.latex = self.directory / "case.tex"
        self.latex.write_text(r"""% mathformer-case-id: fixture
% expected-lean-name: fixture
% controlled-suite: wiki_level_latex_to_lean
\begin{document}
\section*{Statement and Proof}
\begin{theorem}Every group is a group.\end{theorem}
\begin{proof}By definition.\end{proof}
\section*{Lean Target}
fixture
\end{document}
""")
        self.case = {
            "id": "fixture",
            "latex_file": str(self.latex),
            "lean_theorem": "fixture",
            "concepts": ["group"],
            "expected_mathlib_declarations": [
                "Nat.add_comm",
                "",
                "Nat.add_comm",
                "Nat.mul_comm",
            ],
        }
        self.options = {
            "output_dir": str(self.directory / "out"),
            "output_name": "report.json",
            "reasoning_log": str(self.directory / "reasoning.jsonl"),
            "no_reasoning_log": False,
            "append_reasoning_log": False,
            "skip_concept_map": False,
            "skip_hierarchy": False,
            "skip_declaration_checks": False,
            "verify_timeout_sec": 7,
        }
        self.write_manifest(2)

    def write_manifest(self, n, case=None):
        self.manifest.write_text(
            json.dumps(
                {
                    "suite": "fixture",
                    "gold_lean_file": str(self.gold),
                    "gold_expected_imports": ["Missing.Import"],
                    "cases": [case or self.case] * n,
                }
            )
        )

    def args(self, module, options=None):
        args = module.parse_args([])
        for key, value in (options or self.options).items():
            setattr(
                args,
                key,
                Path(value) if key in ("output_dir", "reasoning_log") else value,
            )
        args.manifest = self.manifest
        return args

    def original_report(self, mode, options=None):
        ledger = install(self.original, mode)
        report = self.original.run_suite(self.args(self.original, options))
        return report, ledger, events(Path((options or self.options)["reasoning_log"]))

    def test_shared_steps_match_original_and_cli(self):
        for mode in ("success", "fail", "timeout"):
            for skipped in (False, True):
                with self.subTest(mode=mode, skipped=skipped):
                    opts = {
                        **self.options,
                        "skip_concept_map": skipped,
                        "skip_hierarchy": skipped,
                        "skip_declaration_checks": skipped,
                    }
                    expected, calls, history = self.original_report(mode, opts)
                    actual_calls = install(self.native, mode)
                    actual = self.native.run_suite(self.args(self.native, opts))
                    self.assertEqual(stable(actual), stable(expected))
                    self.assertEqual(actual_calls, calls)
                    self.assertEqual(events(Path(opts["reasoning_log"])), history)
                    self.assertEqual(actual["summary"]["passed"], mode == "success")
                    self.assertEqual(actual["summary"]["case_count"], 2)
                    self.assertEqual(
                        actual["import_check"]["missing_imports"], ["Missing.Import"]
                    )
                    self.assertEqual(
                        actual["expected_declaration_checks"]["checked_count"],
                        0 if skipped else 2,
                    )
        # Append and disabled logging retain native history/reset semantics.
        for opts in (
            {**self.options, "append_reasoning_log": True},
            {**self.options, "no_reasoning_log": True},
        ):
            install(self.native)
            before = events(Path(opts["reasoning_log"]))
            self.native.run_suite(self.args(self.native, opts))
            after = events(Path(opts["reasoning_log"]))
            self.assertEqual(after[: len(before)], before)
            self.assertEqual(len(after) > len(before), not opts["no_reasoning_log"])
        install(self.native)
        stream = io.StringIO()
        argv = [
            "--manifest",
            str(self.manifest),
            "--output-dir",
            self.options["output_dir"],
            "--no-reasoning-log",
            "--json",
        ]
        with redirect_stdout(stream):
            code = self.native.main(argv)
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(stream.getvalue())["summary"]["passed"])
        install(self.native, "fail")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.native.main(argv), 1)
        for module in (self.native, self.original):
            calls = install(module, "exception")
            with self.assertRaises(OSError):
                module.run_suite(self.args(module))
            self.assertEqual(len(calls), 1)

    def test_registration_respects_write_policy(self):
        async def check():
            mcp = create_server(readonly=True)
            result = await mcp.call_tool(
                "mathformer_wiki_suite_prepare",
                {"manifest": str(self.manifest), "options": self.options},
            )
            return result

        with self.assertRaisesRegex(Exception, "read-only policy"):
            asyncio.run(check())

    def test_lunar_registered_tools_runtime_and_bounds(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_lean_wiki_level_suite_workflow")
        self.assertEqual(document["lifecycle"], "active")
        # Validate within the repository without installing host-owned files.
        checked = validate(
            ROOT
            / "skills/control/workflow-contract-validator/references/wiki-suite.workflow.json",
            ROOT,
            True,
        )
        self.assertTrue(checked["valid"], checked)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        for mode in ("success", "fail", "timeout", "exception"):
            manager = SessionManager()
            failure = None
            async with manager.open(
                "wiki",
                StdioConfig(
                    command=sys.executable,
                    args=["tests/mcp/fixtures/wiki_suite_server.py", mode],
                    cwd=str(ROOT),
                ),
                {},
            ) as remote:
                try:
                    tools = [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in await remote.tools()
                    ]

                    def compile(doc, inventory=None):
                        received = assets(doc)
                        workflow = compile_workflow(
                            "mcp:wiki",
                            workflow_documents([DESCRIPTOR], received)[0],
                            tools if inventory is None else inventory,
                        )
                        return workflow, received

                    workflow, received = compile(document)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(
                        set(workflow["bindings"]), set(document["operations"])
                    )
                    self.assertFalse(compile(document, [])[0]["runnable"])

                    async def allow():
                        pass

                    async def run(opts=None, doc=None):
                        w, a = compile(doc) if doc else (workflow, received)
                        return await execute(
                            w,
                            a,
                            {
                                "manifest": str(self.manifest),
                                "options": opts or self.options,
                            },
                            remote,
                            allow,
                        )

                    self.write_manifest(2)
                    if mode == "exception":
                        result = await run()
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            [
                                "mathformer_wiki_suite_prepare",
                                "mathformer_wiki_suite_case_step",
                            ],
                        )
                        self.assertEqual(result["calls"][-1]["status"], "rejected")
                        continue
                    for count, skipped in (
                        (2, False),
                        (2, True),
                        (0, False),
                        (0, True),
                    ):
                        self.write_manifest(count)
                        opts = {
                            **self.options,
                            "skip_concept_map": skipped,
                            "skip_hierarchy": skipped,
                            "skip_declaration_checks": skipped,
                        }
                        expected, calls, history = self.original_report(mode, opts)
                        before = len((await remote.call("fixture_ledger", {}))["calls"])
                        result = await run(opts)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            stable(result["outputs"]["report"]), stable(expected)
                        )
                        self.assertEqual(
                            (await remote.call("fixture_ledger", {}))["calls"][before:],
                            calls,
                        )
                        self.assertEqual(events(Path(opts["reasoning_log"])), history)
                        self.assertEqual(
                            stable(
                                json.loads(
                                    (
                                        Path(opts["output_dir"]) / "report.json"
                                    ).read_text()
                                )
                            ),
                            stable(expected),
                        )
                        expected_tools = (
                            ["prepare"]
                            + (["case_step"] * count if count else ["empty_cases"])
                            + [
                                "compile_gold",
                                "audit",
                                (
                                    "skip_declarations"
                                    if skipped
                                    else "check_declarations"
                                ),
                                "finish",
                            ]
                        )
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            ["mathformer_wiki_suite_" + s for s in expected_tools],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                    if mode != "success":
                        continue
                    # A static finding and missing target remain data; all later checks still run.
                    self.write_manifest(2, {**self.case, "lean_theorem": "absent"})
                    expected, calls, history = self.original_report(mode)
                    before = len((await remote.call("fixture_ledger", {}))["calls"])
                    result = await run()
                    self.assertEqual(result["status"], "accepted")
                    self.assertFalse(result["outputs"]["report"]["summary"]["passed"])
                    self.assertEqual(
                        result["outputs"]["report"]["summary"]["missing_lean_theorems"],
                        ["fixture", "fixture"],
                    )
                    self.assertEqual(
                        stable(result["outputs"]["report"]), stable(expected)
                    )
                    self.assertEqual(
                        (await remote.call("fixture_ledger", {}))["calls"][before:],
                        calls,
                    )
                    # Optional paths are independent of one another.
                    self.write_manifest(1)
                    for opts in (
                        {**self.options, "skip_concept_map": True},
                        {**self.options, "skip_hierarchy": True},
                        {**self.options, "skip_declaration_checks": True},
                    ):
                        expected, _, _ = self.original_report(mode, opts)
                        result = await run(opts)
                        self.assertEqual(result["status"], "accepted")
                        self.assertEqual(
                            stable(result["outputs"]["report"]), stable(expected)
                        )
                    scratch = (
                        Path(self.options["output_dir"])
                        / "tmp/expected_declaration_checks.lean"
                    )
                    self.assertEqual(
                        scratch.read_text(),
                        "import Mathlib\n#check Nat.add_comm\n#check Nat.mul_comm\n",
                    )
                    # Real state ports retain order and duplicates until declaration checks deduplicate.
                    self.write_manifest(2)
                    loaded = await remote.call(
                        "mathformer_wiki_suite_prepare",
                        {"manifest": str(self.manifest), "options": self.options},
                    )
                    self.assertEqual(
                        loaded["state"],
                        {"cursor": 0, "cases": [], "expected_declarations": []},
                    )
                    state = loaded["state"]
                    install(self.native)
                    for cursor in (1, 2):
                        expected = self.native.advance_case(loaded["session"], state)
                        advanced = await remote.call(
                            "mathformer_wiki_suite_case_step",
                            {"session": loaded["session"], "state": state},
                        )
                        self.assertEqual(stable(advanced), stable(expected))
                        self.assertEqual(advanced["state"]["cursor"], cursor)
                        self.assertEqual(advanced["done"], cursor == 2)
                        state = advanced["state"]
                    self.assertEqual(
                        state["expected_declarations"],
                        self.case["expected_mathlib_declarations"] * 2,
                    )
                    # Empty expected names take the helper's immediate success branch.
                    self.write_manifest(
                        1, {**self.case, "expected_mathlib_declarations": []}
                    )
                    result = await run()
                    self.assertEqual(
                        result["outputs"]["report"]["expected_declaration_checks"],
                        {"ok": True, "checks": {}, "checked_count": 0},
                    )
                    # Full native traversal at the admitted bound. Use the actual
                    # registered final transition to check the 1000th-case stop.
                    # Replaying every growing state over stdio would be quadratic;
                    # exact loop-bound execution is tested below with a compiler fixture.
                    self.write_manifest(1000)
                    opts = {
                        **self.options,
                        "no_reasoning_log": True,
                        "skip_concept_map": True,
                        "skip_hierarchy": True,
                        "skip_declaration_checks": True,
                    }
                    expected, _, _ = self.original_report("success", opts)
                    install(self.native)
                    prepared = self.native.prepare_suite(
                        self.args(self.native, opts), max_cases=1000
                    )
                    state = prepared["state"]
                    for _ in range(999):
                        state = self.native.advance_case(prepared["session"], state)[
                            "state"
                        ]
                    advanced = await remote.call(
                        "mathformer_wiki_suite_case_step",
                        {"session": prepared["session"], "state": state},
                    )
                    self.assertTrue(advanced["done"])
                    self.assertEqual(advanced["state"]["cursor"], 1000)
                    self.assertEqual(
                        stable(advanced["state"]["cases"]), stable(expected["cases"])
                    )
                    self.assertEqual(
                        advanced["state"]["expected_declarations"],
                        self.case["expected_mathlib_declarations"] * 1000,
                    )
                    final = self.native.finish_suite(
                        prepared["session"],
                        advanced["state"],
                        self.native.compile_suite_gold(prepared["session"]),
                        self.native.audit_suite(prepared["session"]),
                        self.native.skipped_declarations(),
                    )
                    self.assertEqual(stable(final), stable(expected))
                    self.write_manifest(1001)
                    result = await run(opts)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 1)
                    self.assertIsNone(result["outputs"])
                    # Compiler fixtures narrow the loop/call budgets to prove exhaustion dispositions.
                    self.write_manifest(2)
                    bounded = deepcopy(document)
                    bounded["flow"]["steps"][1]["max_iterations"] = 2
                    result = await run(opts, bounded)
                    self.assertEqual(result["status"], "accepted")
                    self.assertEqual(
                        result["outputs"]["report"]["summary"]["case_count"], 2
                    )
                    self.assertEqual(len(result["calls"]), 7)
                    bounded["flow"]["steps"][1]["max_iterations"] = 1
                    result = await run(opts, bounded)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["failure_disposition"], "fail")
                    self.assertEqual(len(result["calls"]), 2)
                    self.assertIsNone(result["outputs"])
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 1
                    result = await run(opts, budget)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        1,
                    )
                    # Bad source data aborts at its native read boundary without later checks.
                    self.write_manifest(
                        2,
                        {
                            **self.case,
                            "latex_file": str(self.directory / "missing.tex"),
                        },
                    )
                    result = await run()
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 2)
                    self.manifest.write_text("{")
                    result = await run()
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 1)
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
