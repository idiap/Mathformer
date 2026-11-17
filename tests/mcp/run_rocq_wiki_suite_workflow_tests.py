#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Actual suite CLIs, registered tools and Lunar PRISM execution; no live compilers."""

from tempfile import gettempdir

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
import asyncio
from copy import deepcopy
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import yaml
from rocq_wiki_suite_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_rocq_wiki_suite_workflow/workflow.yaml"
FIXTURE = ROOT / "tests/mcp/fixtures/rocq_wiki_compiler"


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


def environment(mode, ledger):
    return {
        "PYTHONPATH": os.pathsep.join([str(FIXTURE), str(ROOT)]),
        "ROCQ_WIKI_COMPILER_FIXTURE": mode,
        "ROCQ_WIKI_LEDGER": str(ledger),
    }


def stable(value):
    if isinstance(value, str):
        try:
            return stable(json.loads(value))
        except (ValueError, TypeError):
            return value
    if isinstance(value, dict):
        return {
            k: stable(v)
            for k, v in value.items()
            if k not in ("generated_at_utc", "duration_ms")
        }
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


class SuiteTests(unittest.TestCase):
    def test_original_cli_parity_and_report_aggregation(self):
        original = type(sys)("_wiki_original")
        original.__file__ = str(ROOT / "tests/rocq/run_wiki_suite.py")
        exec(
            compile(
                (
                    ROOT / "tests/mcp/fixtures/rocq_wiki_suite_original.py.txt"
                ).read_text(),
                original.__file__,
                "exec",
            ),
            original.__dict__,
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            ledger = Path(tmp) / "ledger"
            for mode in ("missing", "reject", "timeout", "raise"):
                for required in (False, True):
                    args = dict(
                        output_dir=out, require_compiler=required, timeout_sec=30
                    )
                    with patch.dict(os.environ, environment(mode, ledger)):
                        before = original.run_suite(**args)
                        after = source().run_suite(**args)
                    self.assertEqual(stable(before), stable(after))
                    self.assertEqual(after["ok"], mode == "missing" and not required)
                    self.assertTrue(after["checks"]["draft_command_ok"])
                    self.assertTrue(after["checks"]["all_files_produced"])
                    self.assertEqual(after["steps"]["execution"]["timeout"], False)
            with patch.dict(os.environ, environment("missing", ledger)):
                stream = io.StringIO()
                reportfile = Path(tmp) / "suite.json"
                with redirect_stdout(stream):
                    code = source().main(
                        [
                            "--output-dir",
                            str(out),
                            "--report-file",
                            str(reportfile),
                            "--json",
                        ]
                    )
                self.assertEqual(code, 0)
                self.assertEqual(
                    json.loads(stream.getvalue()), json.loads(reportfile.read_text())
                )
            prepared = source().prepare_suite(
                output_dir=out, require_compiler=False, timeout_sec=30
            )
            good = after["steps"]["draft"]
            for bad in ("", "invalid", "[]"):
                report = source().aggregate_suite(
                    prepared, good, {**good, "stdout": bad}
                )
                self.assertFalse(report["ok"])
                self.assertFalse(report["checks"]["all_theorems_seen"])
            malformed = {**good, "stdout": json.dumps({"validations": [None]})}
            with self.assertRaises(AttributeError):
                source().aggregate_suite(prepared, good, malformed)
            with self.assertRaises(FileNotFoundError):
                source().run_command(
                    [
                        str(
                            Path(gettempdir())
                            / "mathformer-test-fixtures/fixture/absent"
                        )
                    ],
                    timeout_sec=1,
                )

    def test_native_draft_state_and_exhaustion(self):
        from backends.rocq.MathformerRocq import autoformalize as native

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = json.loads(
                (ROOT / "tests/latex/wiki_level/manifest.json").read_text()
            )
            for index, case_id in enumerate(native.DEFAULT_CASE_ORDER):
                row = next(c for c in manifest["cases"] if c["id"] == case_id)
                latex = root / (str(index) + ".tex")
                latex.write_text(
                    r"\begin{theorem}"
                    + ("Admitted." if index == 0 else "True")
                    + r"\end{theorem}"
                )
                row["latex_file"] = str(latex)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            state = native.initialize_draft(manifest_path, root / "out")
            original_selected = deepcopy(state["selected"])
            self.assertEqual(state["cursor"], 0)
            self.assertEqual(state["reports"], [])
            for cursor in range(5):
                old = state
                advanced = native.draft_next(state)
                state = advanced["state"]
                self.assertEqual(old["cursor"], cursor)
                self.assertEqual(state["cursor"], cursor + 1)
                self.assertEqual(len(state["reports"]), cursor + 1)
                self.assertEqual(state["reports"][:-1], old["reports"])
                self.assertEqual(state["selected"], original_selected)
                self.assertEqual(advanced["done"], cursor == 4)
            self.assertFalse(state["reports"][0]["ok"])
            self.assertTrue(all(r["ok"] for r in state["reports"][1:]))
            self.assertFalse(native.finish_draft(state)["ok"])
            self.assertEqual(len(list((root / "out").glob("*.v"))), 5)
            with self.assertRaises(IndexError):
                native.draft_next(state)

    def test_lunar_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(doc["id"], "hub_rocq_wiki_suite_workflow")
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        for mode in ("success", "missing", "reject", "timeout", "raise", "slow"):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                ledger = root / "compiler.jsonl"
                manager = SessionManager()
                failure = None
                async with manager.open(
                    "rocq-wiki",
                    StdioConfig(
                        command=sys.executable,
                        args=["-B", "tests/mcp/fixtures/rocq_wiki_suite_server.py"],
                        cwd=str(ROOT),
                    ),
                    environment(mode, ledger),
                ) as remote:
                    try:
                        tools = [
                            t.model_dump(by_alias=True, exclude_none=True)
                            for t in await remote.tools()
                        ]
                        assets = snapshot(doc)
                        selected = workflow_documents([DESCRIPTOR], assets)[0]
                        compiled = compile_workflow("mcp:rocq-wiki", selected, tools)
                        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                        self.assertTrue(compiled["prism_source"])
                        self.assertTrue(compiled["runtime_source"])
                        self.assertEqual(
                            set(compiled["bindings"]), set(doc["operations"])
                        )
                        self.assertFalse(
                            compile_workflow("mcp:rocq-wiki", selected, [])["runnable"]
                        )

                        async def allow():
                            pass

                        async def run(required=False, document=doc, timeout=30):
                            a = snapshot(document)
                            w = compile_workflow(
                                "mcp:rocq-wiki",
                                workflow_documents([DESCRIPTOR], a)[0],
                                tools,
                            )
                            return await execute(
                                w,
                                a,
                                {
                                    "options": dict(
                                        output_dir=str(out),
                                        require_compiler=required,
                                        timeout_sec=timeout,
                                    )
                                },
                                remote,
                                allow,
                            )

                        result = await run(timeout=1 if mode == "slow" else 30)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]],
                            ["prepare", "draft", "check", "aggregate"],
                        )
                        report = result["outputs"]["report"]
                        self.assertEqual(report["ok"], mode in ("success", "missing"))
                        self.assertEqual(len(list(out.glob("*.v"))), 5)
                        self.assertTrue(report["checks"]["draft_report_ok"])
                        self.assertTrue(report["checks"]["all_files_produced"])
                        self.assertTrue((out / "wiki_level_draft.json").exists())
                        if mode not in ("raise", "slow"):
                            execution = report["steps"]["execution"]["parsed"]
                            self.assertEqual(execution["file_count"], 5)
                            self.assertEqual(len(execution["validations"]), 5)
                            self.assertEqual(len(execution["external_checks"]), 5)
                            self.assertTrue(report["checks"]["all_theorems_seen"])
                            if mode != "missing":
                                calls = [
                                    json.loads(line)
                                    for line in ledger.read_text().splitlines()
                                ]
                                self.assertEqual(len(calls), 5)
                                self.assertEqual(
                                    [Path(c["cmd"][-1]).name for c in calls],
                                    sorted(p.name for p in out.glob("*.v")),
                                )
                                self.assertEqual(
                                    [c["timeout"] for c in calls], [30] * 5
                                )
                            if mode == "timeout":
                                self.assertTrue(
                                    execution["external_checks"][0]["timeout"]
                                )
                        if mode == "slow":
                            self.assertTrue(report["steps"]["execution"]["timeout"])
                        if mode == "raise":
                            self.assertFalse(report["checks"]["execution_command_ok"])
                            self.assertIsNone(report["steps"]["execution"]["parsed"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        if mode == "missing":
                            required = await run(True)
                            self.assertFalse(required["outputs"]["report"]["ok"])
                            self.assertFalse(
                                required["outputs"]["report"]["checks"][
                                    "execution_report_ok"
                                ]
                            )
                        if mode == "success":
                            # Extra files are allowed and participate in both complete passes.
                            (out / "Extra.v").write_text(
                                (out / "AutoformalizedWikiContrapositive.v").read_text()
                            )
                            extra = await run()
                            self.assertTrue(extra["outputs"]["report"]["ok"])
                            self.assertEqual(
                                extra["outputs"]["report"]["steps"]["execution"][
                                    "parsed"
                                ]["file_count"],
                                6,
                            )
                            (out / "Bad.v").write_text("Admitted.")
                            bad = await run()
                            bad_report = bad["outputs"]["report"]
                            self.assertFalse(bad_report["ok"])
                            evidence = bad_report["steps"]["execution"]["parsed"]
                            self.assertEqual(len(evidence["validations"]), 7)
                            self.assertEqual(len(evidence["external_checks"]), 7)
                            self.assertEqual(
                                sum(not v["ok"] for v in evidence["validations"]), 1
                            )
                            self.assertTrue(
                                all(v["ok"] for v in evidence["external_checks"])
                            )
                            # Draft CLI catches the native OSError; checking still runs.
                            for p in out.glob("*.v"):
                                p.unlink()
                            (out / "AutoformalizedWikiContrapositive.v").mkdir()
                            failed = await run()
                            r = failed["outputs"]["report"]
                            self.assertFalse(r["checks"]["draft_command_ok"])
                            self.assertFalse(r["ok"])
                            self.assertFalse(r["checks"]["execution_command_ok"])
                            self.assertEqual(
                                [c["operation"] for c in failed["calls"]],
                                ["prepare", "draft", "check", "aggregate"],
                            )
                            bounded = deepcopy(doc)
                            bounded["policy"]["limits"]["max_operation_calls"] = 2
                            limited = await run(document=bounded)
                            self.assertEqual(limited["status"], "failed")
                            self.assertIsNone(limited["outputs"])
                            self.assertFalse(
                                any(
                                    c["operation"] == "aggregate"
                                    for c in limited["calls"]
                                )
                            )
                            self.assertIn("budget", json.dumps(limited).lower())
                            timed = await run(timeout=0)
                            self.assertEqual(timed["status"], "accepted")
                            timed_report = timed["outputs"]["report"]
                            self.assertTrue(timed_report["steps"]["draft"]["timeout"])
                            self.assertTrue(
                                timed_report["steps"]["execution"]["timeout"]
                            )
                            self.assertFalse(timed_report["ok"])
                            self.assertEqual(
                                [c["operation"] for c in timed["calls"]],
                                ["prepare", "draft", "check", "aggregate"],
                            )
                            shutil.rmtree(out)
                            out.write_text("occupied destination")
                            exception = await run()
                            self.assertEqual(exception["status"], "failed")
                            self.assertIsNone(exception["outputs"])
                            self.assertEqual(
                                [c["operation"] for c in exception["calls"]],
                                ["prepare"],
                            )
                    except Exception as error:
                        failure = error
                if failure:
                    raise failure
                self.assertFalse(manager.active)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SuiteTests)
    )
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
