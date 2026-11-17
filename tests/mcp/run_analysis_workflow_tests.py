#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native analysis oracle and real MCP/PRISM compiler/runtime integration."""

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
from unittest.mock import patch
import yaml
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
from agentc_analysis_tools import source

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_agentc_analyze_logs_workflow/workflow.yaml"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(path, (ROOT / path).read_text())
        for path in dict.fromkeys(
            row["path"] for row in document["provenance"]["sources"]
        )
    ]


def oracle():
    source()  # Install the real native sibling module, with no provider initialization.
    path = ROOT / "tests/mcp/fixtures/analysis_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "analysis_oracle", SourceFileLoader("analysis_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(directory, indexed=True):
    def write(name, value):
        path = directory / name
        path.write_text(json.dumps(value))
        return str(path)

    first, last = directory / "round_01.lean", directory / "round_02.lean"
    first.write_text("theorem first : True := by sorry\n")
    last.write_text(
        "theorem last : True := by trivial\n\nexample : True := by trivial\n"
    )
    entries = [
        dict(event_index=i, timestamp_unix_ms=ts, step=step, payload=payload)
        for i, ts, step, payload in [
            (1, 10, "draft_start", {}),
            (2, 20, "draft_start", {}),
            (3, 50, "draft_complete", {}),
            (4, 70, "draft_complete", {}),
            (
                5,
                80,
                "hard_critique_output",
                {
                    "correctness": "False",
                    "lean_error_log": "\n".join(
                        "error: unknown identifier x" + str(i) for i in range(25)
                    ),
                },
            ),
            (6, 90, "hard_critique_output", {"correctness": "True"}),
        ]
    ]
    if not indexed:
        for entry in entries:
            entry.pop("event_index")
    log = directory / "reasoning.jsonl"
    log.write_text(
        "\n".join(json.dumps(e) for e in reversed(entries)) + "\nmalformed\n[]\n"
    )
    report = {
        key: "text"
        for key in [
            "informal_statement",
            "normalized_statement",
            "initial_code",
            "final_code",
            "initial_correctness",
            "final_correctness",
            "initial_hard_feedback",
            "final_hard_feedback",
        ]
    }
    report.update(
        used_iterative_refinement=True,
        ignored_unknown=True,
        output_file=str(last),
        round_version_files=[
            str(last),
            str(first),
            str(first),
            str(directory / "missing.lean"),
        ],
        reasoning_log_file=str(log),
        history_file=write(
            "history.json",
            [
                dict(
                    round_index=0,
                    agent_name="FormalRefinementAgent",
                    step_timings_ms={"total_round_ms": 12},
                    refinement_analysis={"primary_refinement_type": "repair"},
                )
            ],
        ),
        cycle_manifest_file=write(
            "cycles.json", {"cycles": [{"output_file": str(first)}, {}]}
        ),
        dependency_reports=[
            {
                "output_file": str(first),
                "dependency_reports": [{"output_file": str(last)}],
            }
        ],
    )
    report_path = directory / "report.json"
    report["report_file"] = str(report_path)
    report_path.write_text(json.dumps(report))
    return report_path, report


class AnalysisTests(unittest.TestCase):
    def test_shared_steps_match_original_and_preserve_defaults(self):
        original, native = oracle(), source()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path, payload = fixture(directory)
            for module in (original, native):
                with (
                    patch.object(sys, "argv", ["analyze", "--report-file", str(path)]),
                    redirect_stdout(io.StringIO()) as output,
                ):
                    self.assertEqual(module.main(), 0)
                self.assertEqual(
                    output.getvalue().splitlines(),
                    [
                        str(path.with_suffix(".stats.json")),
                        str(path.with_suffix(".stats.tex")),
                    ],
                )
                actual = [
                    path.with_suffix(".stats.json").read_bytes(),
                    path.with_suffix(".stats.tex").read_bytes(),
                ]
                if module is original:
                    expected = actual
                else:
                    self.assertEqual(actual, expected)
            for module in (original, native):
                with (
                    patch.object(sys, "argv", ["analyze", "--help"]),
                    redirect_stdout(io.StringIO()) as help_text,
                ):
                    with self.assertRaises(SystemExit) as exited:
                        module.main()
                self.assertEqual(exited.exception.code, 0)
                self.assertIn("--report-file", help_text.getvalue())
            coerced = native._coerce_report(payload)
            self.assertIsNone(coerced.expanded_statement)
            self.assertFalse(hasattr(coerced, "ignored_unknown"))
            # Empty/missing collections stop by exhaustion and suppress version deltas.
            for name in [
                "reasoning_log_file",
                "history_file",
                "cycle_manifest_file",
                "output_file",
                "report_file",
                "dependency_reports",
                "round_version_files",
            ]:
                payload.pop(name, None)
            old = Path.cwd()
            try:
                os.chdir(directory)
                a, b, stats = native.save_autoformalization_statistics(
                    native._coerce_report(payload)
                )
                self.assertEqual(
                    str(a), "artifacts/autoformalization/autoformalization.stats.json"
                )
                self.assertTrue(b.exists())
                self.assertEqual(stats["timing"]["reasoning_event_count"], 0)
                self.assertIsNone(stats["files"]["round_evolution"])
            finally:
                os.chdir(old)

    def test_lunar_registered_tools_success_failures_and_budget(self):
        async def run():
            document = yaml.safe_load(CONTRACT.read_text())
            self.assertEqual(document["lifecycle"], "active")
            manager = SessionManager()
            failure = None
            async with manager.open(
                "analysis",
                StdioConfig(
                    command=sys.executable,
                    args=[str(ROOT / "tests/mcp/fixtures/analysis_server.py")],
                    cwd=str(ROOT),
                ),
                {},
            ) as remote:
                try:
                    tools = [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in await remote.tools()
                    ]

                    def compile_doc(doc):
                        assets = snapshot(doc)
                        workflow = compile_workflow(
                            "mcp:analysis",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools,
                        )
                        self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                        self.assertTrue(workflow["runtime_source"])
                        return workflow, assets

                    workflow, assets = compile_doc(document)
                    self.assertEqual(
                        set(workflow["bindings"]),
                        {"parse", "load", "coerce", "save", "finish"},
                    )

                    async def allow():
                        pass

                    async def invoke(argv, wf=workflow, data=assets):
                        return await execute(wf, data, {"argv": argv}, remote, allow)

                    with tempfile.TemporaryDirectory() as temporary:
                        directory = Path(temporary)
                        for indexed in (True, False):
                            path, payload = fixture(directory, indexed)
                            result = await invoke(["--report-file", str(path)])
                            self.assertEqual(result["status"], "accepted", result)
                            self.assertEqual(result["outputs"]["exit_code"], 0)
                            self.assertEqual(
                                [c["tool"] for c in result["calls"]],
                                [
                                    "mathformer_analysis_" + n
                                    for n in [
                                        "parse",
                                        "load",
                                        "coerce",
                                        "save",
                                        "finish",
                                    ]
                                ],
                            )
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            stats = json.loads(
                                Path(result["outputs"]["paths"]["json"]).read_text()
                            )
                            self.assertEqual(
                                stats["workflow_counts"]["process_duration_ms"][
                                    "draft"
                                ],
                                {"count": 2, "total_ms": 90.0, "avg_ms": 45.0},
                            )
                            self.assertEqual(
                                stats["timing"]["reasoning_event_count"], 6
                            )
                            self.assertEqual(
                                stats["hard_critique"],
                                {"checks": 2, "checks_true": 1, "checks_false": 1},
                            )
                            self.assertEqual(
                                stats["metadata"]["dependency_report_count"], 2
                            )
                            self.assertEqual(stats["metadata"]["cycle_count"], 2)
                            self.assertEqual(stats["files"]["analyzed_file_count"], 2)
                            self.assertEqual(
                                stats["files"]["round_evolution"]["delta_sorry_count"],
                                -1,
                            )
                            self.assertEqual(
                                stats["refinement_dynamics"]["round_duration_ms"][
                                    "total_ms"
                                ],
                                12,
                            )
                            self.assertEqual(
                                len(stats["errors"]["top_error_lines"]), 20
                            )
                            self.assertEqual(stats["errors"]["total_error_lines"], 25)
                            self.assertIn(
                                "\\begin{",
                                Path(result["outputs"]["paths"]["tex"]).read_text(),
                            )
                            self.assertEqual(
                                stats,
                                source().save_autoformalization_statistics(
                                    source()._coerce_report(payload),
                                    statistics_file=directory / "oracle.json",
                                    statistics_tex_file=directory / "oracle.tex",
                                )[2],
                            )
                        # Independent JSON override leaves native TeX default intact.
                        custom = directory / "custom.json"
                        result = await invoke(
                            ["--report-file", str(path), "--output-json", str(custom)]
                        )
                        self.assertEqual(
                            result["outputs"]["paths"],
                            {
                                "json": str(custom),
                                "tex": str(path.with_suffix(".stats.tex")),
                            },
                        )
                        help_result = await invoke(["--help"])
                        self.assertEqual(help_result["status"], "accepted", help_result)
                        self.assertEqual(
                            help_result["outputs"], {"paths": None, "exit_code": 0}
                        )
                        self.assertEqual(len(help_result["calls"]), 2)
                        # Errors stop immediately; no downstream calls or automatic retries.
                        for content, argv, calls in [
                            (None, [], 1),
                            (None, ["--report-file", str(directory / "absent")], 2),
                            ("[]", ["--report-file", str(path)], 2),
                            ("{", ["--report-file", str(path)], 2),
                            ("{}", ["--report-file", str(path)], 3),
                        ]:
                            if content is not None:
                                path.write_text(content)
                            result = await invoke(argv)
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(len(result["calls"]), calls)
                            self.assertEqual(result["calls"][-1]["status"], "rejected")
                        path, _ = fixture(directory)
                        # Analysis exceptions stop before any output is created.
                        path, bad_payload = fixture(directory)
                        bad_payload["consistency_report"] = {"summary": None}
                        path.write_text(json.dumps(bad_payload))
                        analysis_output = directory / "analysis_failure.json"
                        result = await invoke(
                            [
                                "--report-file",
                                str(path),
                                "--output-json",
                                str(analysis_output),
                            ]
                        )
                        self.assertEqual(result["status"], "failed")
                        self.assertEqual(len(result["calls"]), 4)
                        self.assertFalse(analysis_output.exists())
                        path, _ = fixture(directory)
                        # Native partial-write behavior: JSON survives a subsequent TeX error.
                        partial = directory / "partial.json"
                        result = await invoke(
                            [
                                "--report-file",
                                str(path),
                                "--output-json",
                                str(partial),
                                "--output-tex",
                                str(directory),
                            ]
                        )
                        self.assertEqual(result["status"], "failed")
                        self.assertEqual(len(result["calls"]), 4)
                        self.assertTrue(partial.exists())
                        bounded = deepcopy(document)
                        bounded["policy"]["limits"]["max_operation_calls"] = 3
                        limited, limited_assets = compile_doc(bounded)
                        forbidden = directory / "budget.json"
                        result = await invoke(
                            [
                                "--report-file",
                                str(path),
                                "--output-json",
                                str(forbidden),
                            ],
                            limited,
                            limited_assets,
                        )
                        self.assertEqual(result["status"], "failed")
                        self.assertIn("budget", result["calls"][-1]["error"])
                        self.assertFalse(forbidden.exists())
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure is not None:
                raise failure

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
