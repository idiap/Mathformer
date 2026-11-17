#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real native steps, MCP bindings and Lunar PRISM execution on local fixtures.

There is no external provider/compiler in this source. No boundaries are faked:
Lunar uses the actual PRISM parser, checker, compiler and runtime.
"""

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
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import io
import json
import tempfile
import unittest
import yaml
from coherence_gate_tools import source, SOURCE
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathformerphysicslib_coherence_gate_workflow/workflow.yaml"


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(path, (ROOT / path).read_text())
        for path in dict.fromkeys(r["path"] for r in document["provenance"]["sources"])
    ]


class CoherenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.native = source()
        namespace = {"__file__": str(ROOT / SOURCE), "__name__": "coherence_original"}
        exec(
            (ROOT / "tests/mcp/fixtures/coherence_gate_original.py.txt").read_text(),
            namespace,
        )
        self.original = namespace["main"]

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value))
        return str(path)

    def cases(self):
        return [
            [],
            [{"findings": []}],
            [{"findings": [{"severity": "low"}]}],
            [{"findings": [{"severity": "medium", "kind": "thin_foundation_api"}]}],
            [
                {
                    "findings": [
                        {
                            "severity": "high",
                            "kind": "confirmed_competing_concept_owner",
                        },
                        {"severity": "medium", "kind": "manifest_missing_foundations"},
                        {"severity": "low", "kind": "foundation_without_operable_api"},
                        {"severity": "unknown", "kind": "unknown"},
                    ]
                },
                {
                    "findings": [
                        {
                            "severity": "high",
                            "kind": "concept_spread_without_foundation_owner",
                        }
                    ]
                },
            ],
        ]

    def invoke(self, call, argv):
        output = io.StringIO()
        with redirect_stdout(output):
            code = call(argv)
        return code, output.getvalue()

    def test_original_equivalence_and_native_effects(self):
        for index, reports in enumerate(self.cases()):
            argv = []
            # Empty list is tested through a supplied empty report (CLI has no
            # zero-report supplied branch); aggregate itself accepts zero reports.
            for j, r in enumerate(reports or [{}]):
                argv += ["--report", self.write(f"{index}-{j}.json", r)]
            for release in ([], ["--require-release"]):
                self.assertEqual(
                    self.invoke(self.native.main, argv + release),
                    self.invoke(self.original, argv + release),
                )
            repairs = self.native.repair_plan(reports)
            payload = self.native.aggregate(reports, repairs)
            self.assertEqual(
                payload["repair_action_count"],
                sum(len(r.get("findings", [])) for r in reports),
            )
        self.assertEqual(
            self.invoke(self.native.main, ["--self-test", "--json"]),
            self.invoke(self.original, ["--self-test", "--json"]),
        )
        reports = self.cases()[-1]
        repairs = self.native.repair_plan(reports)
        self.assertEqual(
            [a["action"] for a in repairs["actions"]],
            [
                "consolidate_concept_owner",
                "repair_integration_surface",
                "add_operable_bridge_api",
                "record_or_block_gap",
                "consolidate_concept_owner",
            ],
        )
        self.assertEqual(
            (
                self.native.aggregate(reports, repairs)["high_findings"],
                self.native.aggregate(reports, repairs)["medium_findings"],
            ),
            (2, 1),
        )
        for call in (self.native.main, self.original):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
                call(["--unknown"])
            self.assertEqual(cm.exception.code, 2)
            with self.assertRaises(FileNotFoundError):
                call(["--report", str(self.root / "missing")])

    def test_registered_tools_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_mathformerphysicslib_coherence_gate_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertIn(SOURCE, [r["path"] for r in document["provenance"]["sources"]])
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "coherence",
            StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=["-c", server],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    received = assets(doc)
                    selected = workflow_documents([DESCRIPTOR], received)[0]
                    w = compile_workflow(
                        "mcp:coherence",
                        selected,
                        tools if inventory is None else inventory,
                    )
                    return w, received

                w, a = compile(document)
                self.assertTrue(w["runnable"], w["diagnostics"])
                self.assertTrue(w["runtime_source"])
                self.assertEqual(set(w["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def allow():
                    pass

                async def run(argv, doc=None):
                    selected, received = compile(doc) if doc else (w, a)
                    return await execute(
                        selected, received, {"argv": argv}, remote, allow
                    )

                for index, reports in enumerate(self.cases()):
                    argv = []
                    for j, r in enumerate(reports or [{}]):
                        argv += ["--report", self.write(f"case-{index}-{j}.json", r)]
                    for release in ([], ["--require-release"]):
                        code, stdout = self.invoke(self.original, argv + release)
                        result = await run(argv + release)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            result["outputs"],
                            {"payload": json.loads(stdout), "exit_code": code},
                        )
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            [
                                "mathformer_coherence_gate_" + n
                                for n in [
                                    "parse",
                                    "load_reports",
                                    "propose_repairs",
                                    "aggregate",
                                    "emit_return",
                                ]
                            ],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                result = await run(["--self-test", "--json"])
                self.assertEqual(result["status"], "accepted", result)
                code, stdout = self.invoke(self.original, ["--self-test", "--json"])
                self.assertEqual(
                    result["outputs"],
                    {"payload": json.loads(stdout), "exit_code": code},
                )
                self.assertEqual(
                    result["calls"][1]["tool"],
                    "mathformer_coherence_gate_default_reports",
                )
                # Explicit plan is used verbatim, even if its status disagrees
                # with the findings. There is no repair application or retry.
                report = self.write("report.json", {"findings": [{"severity": "high"}]})
                plan = self.write(
                    "plan.json", {"status": "fixture-plan", "actions": [{}, {}]}
                )
                out = self.root / "nested/out.json"
                md = self.root / "nested/out.md"
                argv = [
                    "--report",
                    report,
                    "--repair-plan",
                    plan,
                    "--output",
                    str(out),
                    "--markdown-output",
                    str(md),
                    "--require-release",
                ]
                code, stdout = self.invoke(self.original, argv)
                expected_json = out.read_bytes()
                expected_md = md.read_bytes()
                out.unlink()
                md.unlink()
                result = await run(argv)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"],
                    {"payload": json.loads(stdout), "exit_code": code},
                )
                self.assertEqual(out.read_bytes(), expected_json)
                self.assertEqual(md.read_bytes(), expected_md)
                self.assertEqual(
                    result["outputs"]["payload"]["repair_plan_status"], "fixture-plan"
                )
                self.assertEqual(result["outputs"]["payload"]["repair_action_count"], 2)
                self.assertEqual(
                    result["calls"][2]["tool"], "mathformer_coherence_gate_load_repairs"
                )
                # Budget exhaustion stops before the next native call; source
                # finite traversals have no loop-exhaustion state of their own.
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 4
                out.unlink()
                md.unlink()
                result = await run(argv, bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertIn("budget", str(result).lower())
                self.assertFalse(out.exists())
                self.assertFalse(md.exists())
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    4,
                )
                # Failures must stop subsequent calls and requested writes.
                for bad, expected_calls in [
                    (["--bad-option"], 1),
                    (["--report", str(self.root / "missing")], 2),
                    (
                        [
                            "--report",
                            self.write("bad-shape.json", {"findings": [None]}),
                        ],
                        3,
                    ),
                    (
                        [
                            "--report",
                            report,
                            "--repair-plan",
                            str(self.root / "missing"),
                        ],
                        3,
                    ),
                ]:
                    result = await run(bad + ["--output", str(out)])
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), expected_calls)
                    self.assertIsNone(result["outputs"])
                    self.assertFalse(out.exists())
                # JSON write precedes Markdown failure, and stdout/return do not
                # occur after that failure (same partial effects as main).
                blocker = self.root / "blocker"
                blocker.write_text("file")
                result = await run(
                    [
                        "--report",
                        report,
                        "--output",
                        str(out),
                        "--markdown-output",
                        str(blocker / "out.md"),
                    ]
                )
                self.assertEqual(result["status"], "failed", result)
                self.assertTrue(out.exists())
                self.assertEqual(len(result["calls"]), 5)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
