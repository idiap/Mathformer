#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic filesystem fixtures, registered MCP tools, real PRISM runtime.

There are no provider/model or external compiler boundaries in this workflow.
The PRISM parser, checker, compiler and executor are not substituted.
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
from copy import deepcopy
from contextlib import redirect_stdout
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
import yaml
from reasoning_quality_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_reasoning_log_quality_workflow/workflow.yaml"
PREFIX = "mathformer_reasoning_quality_"


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


class QualityTests(unittest.TestCase):
    def test_native_and_registered_lunar_workflow(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["id"], "hub_control_reasoning_log_quality_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        native = source()
        loader = SourceFileLoader(
            "_quality_oracle",
            str(ROOT / "tests/mcp/fixtures/reasoning_quality_original.py.txt"),
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        oracle = importlib.util.module_from_spec(spec)
        loader.exec_module(oracle)
        oracle.REPO_ROOT = ROOT
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        manager = SessionManager()
        with tempfile.TemporaryDirectory(prefix="quality-workflow-") as tmp:
            directory = Path(tmp) / "artifacts/reasoning/self_test"
            context = {"fixture_directory": str(directory)}
            hooks = ROOT / "skills/SKILL_HOOKS.yaml"
            base = ["--hooks-file", str(hooks)]
            # Only relocate the original's filesystem context; all audit logic is real.
            oracle.default_good_fixture = lambda: directory / "good.jsonl"
            oracle.default_bad_fixture = lambda: directory / "bad.jsonl"
            async with manager.open(
                "quality",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(document, inventory=tools):
                    assets = snapshot(document)
                    c = compile_workflow(
                        "mcp:quality",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        inventory,
                    )
                    return c, assets

                c, a = compile(doc)
                self.assertTrue(c["runnable"], c["diagnostics"])
                self.assertTrue(c["runtime_source"])
                self.assertEqual(set(c["bindings"]), set(doc["operations"]))
                self.assertFalse(compile(doc, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(argv, document=doc):
                    c, a = compile(document)
                    self.assertTrue(c["runnable"], c["diagnostics"])
                    return await execute(
                        c, a, {"argv": argv, "context": context}, remote, authorize
                    )

                async def call(name, **args):
                    return await remote.call(PREFIX + name, args)

                def expected(argv):
                    stdout = io.StringIO()
                    with redirect_stdout(stdout):
                        code = oracle.main(argv)
                    return code, stdout.getvalue()

                def assert_calls(result, names):
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [PREFIX + n for n in names],
                    )

                # No logs creates both fixtures but does not run the explicit bad check.
                result = await run(base + ["--json"])
                self.assertEqual(result["status"], "accepted", result)
                outcome = result["outputs"]["result"]
                self.assertEqual(outcome["exit_code"], 0)
                self.assertTrue(outcome["report"]["consumer_readiness"]["ready"])
                self.assertEqual(outcome["report"]["event_count"], 2)
                self.assertNotIn("self_test", outcome["report"])
                self.assertTrue((directory / "bad.jsonl").exists())
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
                assert_calls(
                    result,
                    ["parse_and_guard", "prepare_fixtures", "audit_selected", "emit"],
                )
                self.assertEqual(
                    (outcome["exit_code"], outcome["stdout"]),
                    expected(base + ["--json"]),
                )
                # Explicit self-test replaces supplied logs, verifies bad, and retains good readiness.
                (directory / "good.jsonl").write_text("stale fixture\n")
                argv = base + [
                    "--log-file",
                    str(directory / "missing.jsonl"),
                    "--self-test",
                    "--json",
                ]
                result = await run(argv)
                outcome = result["outputs"]["result"]
                self.assertEqual(
                    (outcome["exit_code"], outcome["stdout"]), expected(argv)
                )
                self.assertTrue(outcome["report"]["self_test"]["bad_has_high_findings"])
                self.assertIn(
                    "secret_looking_value",
                    outcome["report"]["self_test"]["bad_finding_codes"],
                )
                self.assertTrue(outcome["report"]["consumer_readiness"]["ready"])
                assert_calls(
                    result,
                    [
                        "parse_and_guard",
                        "prepare_fixtures",
                        "audit_selected",
                        "verify_bad",
                        "emit",
                    ],
                )
                # Supplied logs preserve ordering and continue past high findings/malformed lines.
                good = directory / "good.jsonl"
                bad = directory / "bad.jsonl"
                mixed = directory / "mixed.jsonl"
                rows = [json.loads(line) for line in good.read_text().splitlines()]
                event = deepcopy(rows[-1])
                event["payload"]["skill_application"]["human_summary"] = "x" * 321
                mixed.write_text(
                    "invalid json\n"
                    + bad.read_text()
                    + "".join(json.dumps(event) + "\n" for _ in range(35))
                )
                argv = base + ["--log-file", str(mixed), "--log-file", str(good)]
                result = await run(argv)
                outcome = result["outputs"]["result"]
                self.assertEqual(
                    result["status"], "accepted", result
                )  # audit failure is report data
                self.assertEqual(outcome["exit_code"], 3)
                self.assertEqual(outcome["report"]["event_count"], 38)
                self.assertEqual(
                    [r["event_count"] for r in outcome["report"]["logs"]], [36, 2]
                )
                self.assertFalse(outcome["report"]["consumer_readiness"]["ready"])
                self.assertGreater(len(outcome["report"]["findings"]), 20)
                self.assertEqual(
                    len(outcome["stdout"].splitlines()), 22
                )  # first 20 findings only
                self.assertEqual(
                    (outcome["exit_code"], outcome["stdout"]), expected(argv)
                )
                self.assertEqual(
                    outcome["report"],
                    oracle.audit_logs([mixed, good], hooks_file=hooks),
                )
                assert_calls(
                    result,
                    ["parse_and_guard", "select_supplied", "audit_selected", "emit"],
                )
                # Shared CLI emits the identical report/status without any fixture writes.
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    code = native.main(argv)
                self.assertEqual((code, stdout.getvalue()), expected(argv))
                # Empty and advisory-only inputs show ok is weaker than readiness.
                empty = directory / "empty.jsonl"
                empty.write_text("")
                advisory = directory / "advisory.jsonl"
                longrows = deepcopy(rows)
                for row in longrows:
                    row["payload"]["skill_application"]["intent"] = "a" * 181
                advisory.write_text("".join(json.dumps(row) + "\n" for row in longrows))
                for path in (empty, advisory):
                    r = await run(base + ["--log-file", str(path), "--json"])
                    o = r["outputs"]["result"]
                    self.assertEqual(o["exit_code"], 0)
                    self.assertFalse(o["report"]["consumer_readiness"]["ready"])
                    self.assertEqual(
                        (o["exit_code"], o["stdout"]),
                        expected(base + ["--log-file", str(path), "--json"]),
                    )
                # Advisory character limits are inclusive; crossing them changes only scores.
                bounded = deepcopy(rows)
                for row in bounded:
                    app = row["payload"]["skill_application"]
                    app["intent"] = "i" * 180
                    app["human_summary"] = "h" * 320
                edge = directory / "edge.jsonl"
                edge.write_text("".join(json.dumps(row) + "\n" for row in bounded))
                r = await run(base + ["--log-file", str(edge), "--json"])
                self.assertTrue(
                    r["outputs"]["result"]["report"]["consumer_readiness"]["ready"]
                )
                bounded[-1]["payload"]["skill_application"]["human_summary"] += "h"
                edge.write_text("".join(json.dumps(row) + "\n" for row in bounded))
                r = await run(base + ["--log-file", str(edge), "--json"])
                report = r["outputs"]["result"]["report"]
                self.assertTrue(report["ok"])
                self.assertEqual(report["quality_scores"]["concise"], 0.5)
                self.assertIn(
                    "human_summary_too_long", [f["code"] for f in report["findings"]]
                )
                # Missing logs are loading findings, and the next log still contributes events.
                argv = base + [
                    "--log-file",
                    str(directory / "absent.jsonl"),
                    "--log-file",
                    str(good),
                    "--json",
                ]
                r = await run(argv)
                o = r["outputs"]["result"]
                self.assertEqual(o["report"]["event_count"], 2)
                self.assertEqual(o["exit_code"], 3)
                self.assertEqual((o["exit_code"], o["stdout"]), expected(argv))
                # The negative self-test check can fail; retain the good report but change ok.
                parsed = await call(
                    "parse_and_guard", argv=base + ["--self-test"], context=context
                )
                req = parsed["request"]
                selection = (await call("prepare_fixtures", request=req))["selection"]
                report = (
                    await call("audit_selected", request=req, selection=selection)
                )["report"]
                bad.write_text(good.read_text())
                checked = (
                    await call(
                        "verify_bad", request=req, selection=selection, report=report
                    )
                )["report"]
                self.assertFalse(checked["ok"])
                self.assertFalse(checked["self_test"]["bad_has_high_findings"])
                self.assertTrue(checked["consumer_readiness"]["ready"])
                self.assertEqual(
                    (await call("emit", request=req, report=checked))["result"][
                        "exit_code"
                    ],
                    3,
                )
                # Native argument error stops before any filesystem operation.
                rejected = await run(["--invalid-option"])
                self.assertEqual(rejected["status"], "failed")
                self.assertIsNone(rejected["outputs"])
                assert_calls(rejected, ["parse_and_guard"])
                with self.assertRaises(SystemExit) as caught:
                    native.parse_args(["--invalid-option"])
                self.assertEqual(caught.exception.code, 2)
                # A real filesystem exception propagates and prevents emission.
                rejected = await run(base + ["--log-file", str(directory)])
                self.assertEqual(rejected["status"], "failed")
                self.assertIsNone(rejected["outputs"])
                assert_calls(
                    rejected, ["parse_and_guard", "select_supplied", "audit_selected"]
                )
                self.assertTrue(rejected["calls"][-1]["transport_call_performed"])
                with self.assertRaises(IsADirectoryError):
                    oracle.audit_logs([directory], hooks_file=hooks)
                # Runtime call budget rejects the next operation without a transport call.
                limited = deepcopy(doc)
                limited["policy"]["limits"]["max_operation_calls"] = 2
                rejected = await run(base + ["--log-file", str(good)], limited)
                self.assertEqual(rejected["status"], "failed")
                self.assertIsNone(rejected["outputs"])
                self.assertFalse(
                    rejected["calls"][-1].get("transport_call_performed", False)
                )
                self.assertIn("budget", rejected["calls"][-1]["error"])
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
