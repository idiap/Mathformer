#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Local deterministic ProofNet fixtures through native CLI, MCP and real PRISM.

There is no provider or external compiler boundary in this evaluator. Nothing
substitutes its local loader, scoring functions, parser/checker/compiler or runtime.
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
from proofnet_evaluate_tools import source

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_benchmark_proofnet_evaluate_workflow/workflow.yaml"


def snapshot(document):
    texts = {DESCRIPTOR: json.dumps(document)}
    texts.update(
        {
            row["path"]: (ROOT / row["path"]).read_text()
            for row in document["provenance"]["sources"]
        }
    )
    return [
        {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
        for path, text in texts.items()
    ]


def oracle():
    source()  # initialize the native proofnet import path
    path = ROOT / "tests/mcp/fixtures/proofnet_evaluate_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "proofnet_original", SourceFileLoader("proofnet_original", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixtures(directory, empty=False):
    gold = (
        []
        if empty
        else [
            {
                "id": id,
                "formal_statement": text,
                "nl_statement": "",
                "nl_proof": "",
                "src_header": "",
            }
            for id, text in [
                ("a", "α = α"),
                ("b", "x = x"),
                ("c", "missing"),
                ("d", "wrong"),
            ]
        ]
    )
    for filename in ["valid.jsonl", "test.jsonl"]:
        (directory / filename).write_text(
            "".join(json.dumps(row) + "\n" for row in gold)
        )
    predictions = directory / "predictions.jsonl"
    predictions.write_text(
        ""
        if empty
        else "\n"
        + "".join(
            json.dumps({"key": id, "value": text}) + "\n"
            for id, text in [
                ("a", "old"),
                ("a", "α = α"),
                ("b", " x  =\nx "),
                ("d", 42),
                ("unknown", True),
            ]
        )
    )
    return [
        "--gold-dir",
        str(directory),
        "--predictions-file",
        str(predictions),
        "--id-key",
        "key",
        "--prediction-key",
        "value",
    ]


def cli(module, argv):
    output = io.StringIO()
    with (
        patch.object(sys, "argv", ["evaluate_predictions.py", *argv]),
        redirect_stdout(output),
    ):
        code = module.main()
    return code, output.getvalue()


class ProofNetTests(unittest.TestCase):
    def test_cli_and_failure_equivalence(self):
        native, original = source(), oracle()
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for empty in [False, True]:
                argv = fixtures(directory, empty)
                for extra in [
                    [],
                    ["--split", "test", "--summary-only"],
                    ["--output-json", str(directory / "nested/out.json")],
                ]:
                    expected = cli(original, argv + extra)
                    file_before = (
                        (directory / "nested/out.json").read_bytes()
                        if "--output-json" in extra
                        else None
                    )
                    self.assertEqual(cli(native, argv + extra), expected)
                    if file_before is not None:
                        self.assertEqual(
                            (directory / "nested/out.json").read_bytes(), file_before
                        )
                for bad in ["\n{", '{"key":"a"}', '{"value":"a"}']:
                    (directory / "predictions.jsonl").write_text(bad)
                    errors = []
                    for module in [original, native]:
                        with self.assertRaises(RuntimeError) as failure:
                            cli(module, argv)
                        errors.append(str(failure.exception))
                    self.assertEqual(*errors)

    def test_native_bound_and_exhaustion(self):
        native = source()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "predictions.jsonl"
            path.write_text("\n" * 100000)
            state = native.prediction_state(path, "id", "pred")
            with path.open() as stream:
                for _ in range(100000):
                    self.assertFalse(native.read_prediction(stream, state))
                self.assertTrue(native.read_prediction(stream, state))
            self.assertEqual(state["line_number"], 100000)
            self.assertEqual(state["predictions"], {})
            scores = native.initialize_scores(
                [{"id": "a", "formal_statement": "a"}] * 100000, {}
            )
            for _ in range(100000):
                self.assertFalse(native.score_example(scores))
            self.assertTrue(native.score_example(scores))
            self.assertEqual(
                (scores["index"], len(scores["details"]), scores["answered"]),
                (100000, 100000, 0),
            )

    def test_registered_tools_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document["id"], "hub_benchmark_proofnet_evaluate_workflow")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 200010},
        )
        self.assertEqual(document["flow"]["steps"][3]["max_iterations"], 100001)
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "proofnet",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                async def allow():
                    pass

                async def run(argv, doc=None):
                    received = snapshot(document if doc is None else doc)
                    compiled = compile_workflow(
                        "mcp:proofnet",
                        workflow_documents([DESCRIPTOR], received)[0],
                        tools,
                    )
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(
                        set(compiled["bindings"]), set(document["operations"])
                    )
                    return await execute(
                        compiled, received, {"extra_args": argv}, remote, allow
                    )

                with tempfile.TemporaryDirectory() as temp:
                    directory = Path(temp)
                    for empty in [False, True]:
                        argv = fixtures(directory, empty)
                        for extra in [
                            [],
                            ["--split", "test", "--summary-only"],
                            ["--output-json", str(directory / "out/metrics.json")],
                        ]:
                            expected = cli(oracle(), argv + extra)
                            result = await run(argv + extra)
                            self.assertEqual(result["status"], "accepted", result)
                            self.assertEqual(
                                result["outputs"]["exit_code"], expected[0]
                            )
                            metrics = result["outputs"]["metrics"]
                            expected_metrics = json.loads(
                                (directory / "out/metrics.json").read_text()
                                if "--output-json" in extra
                                else expected[1]
                            )
                            self.assertEqual(metrics, expected_metrics)
                            if not empty:
                                self.assertEqual(
                                    (
                                        metrics["answered"],
                                        metrics["missing"],
                                        metrics["exact_match"],
                                        metrics["normalized_exact_match"],
                                    ),
                                    (3, 1, 0.25, 0.5),
                                )
                            self.assertEqual(len(result["calls"]), 8 if empty else 18)
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["replay_artifacts"])
                    # Exact exhaustion boundary: one item needs a second EOF observation.
                    argv = fixtures(directory)
                    (directory / "valid.jsonl").write_text(
                        json.dumps(
                            {
                                "id": "a",
                                "formal_statement": "a",
                                "nl_statement": "",
                                "nl_proof": "",
                                "src_header": "",
                            }
                        )
                        + "\n"
                    )
                    (directory / "predictions.jsonl").write_text(
                        '{"key":"a","value":"a"}\n'
                    )
                    tight = deepcopy(document)
                    for position in [3, 5]:
                        tight["flow"]["steps"][position]["max_iterations"] = 2
                    result = await run(argv, tight)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"]["metrics"]["exact_match"], 1.0)
                    self.assertEqual(len(result["calls"]), 10)
                    # No answers is still success, including nonempty gold denominators.
                    (directory / "predictions.jsonl").write_text("")
                    result = await run(argv)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"]["metrics"]["exact_match_on_answered"], 0.0
                    )
                    self.assertEqual(result["outputs"]["metrics"]["coverage"], 0.0)
                    self.assertEqual(result["outputs"]["metrics"]["missing"], 1)
                    argv = fixtures(directory)
                    # Inspect actual registered transition ports and state histories.
                    config = (
                        await remote.call("mathformer_proofnet_parse", {"argv": argv})
                    )["config"]
                    gold = (
                        await remote.call(
                            "mathformer_proofnet_load_gold", {"config": config}
                        )
                    )["gold"]
                    state = (
                        await remote.call(
                            "mathformer_proofnet_initialize_predictions",
                            {"config": config},
                        )
                    )["state"]
                    for line_number in range(1, 7):
                        transition = await remote.call(
                            "mathformer_proofnet_read_prediction", {"state": state}
                        )
                        state = transition["state"]
                        self.assertFalse(transition["done"])
                        self.assertEqual(state["line_number"], line_number)
                        if line_number == 2:
                            self.assertEqual(state["predictions"]["a"], "old")
                        if line_number == 3:
                            self.assertEqual(state["predictions"]["a"], "α = α")
                    terminal = await remote.call(
                        "mathformer_proofnet_read_prediction", {"state": state}
                    )
                    self.assertTrue(terminal["done"])
                    self.assertEqual(terminal["state"], state)
                    self.assertEqual(state["predictions"]["d"], "42")
                    scores = (
                        await remote.call(
                            "mathformer_proofnet_initialize_scores",
                            {"gold": gold, "predictions": state},
                        )
                    )["state"]
                    for index, counts in enumerate(
                        [(1, 1, 1), (2, 1, 2), (2, 1, 2), (3, 1, 2)], 1
                    ):
                        step = await remote.call(
                            "mathformer_proofnet_score_example", {"state": scores}
                        )
                        scores = step["state"]
                        self.assertFalse(step["done"])
                        self.assertEqual(scores["index"], index)
                        self.assertEqual(
                            (
                                scores["answered"],
                                scores["exact"],
                                scores["normalized_exact"],
                            ),
                            counts,
                        )
                    self.assertTrue(
                        (
                            await remote.call(
                                "mathformer_proofnet_score_example", {"state": scores}
                            )
                        )["done"]
                    )
                    # Real loop bound exhaustion: no finalize/output, no retry or truncation success.
                    for position in [3, 5]:
                        bounded = deepcopy(document)
                        bounded["flow"]["steps"][position]["max_iterations"] = 1
                        result = await run(argv, bounded)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertNotIn(
                            "mathformer_proofnet_finalize",
                            [c["tool"] for c in result["calls"]],
                        )
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 2
                    result = await run(argv, bounded)
                    self.assertEqual(result["status"], "failed")
                    self.assertIn("budget", json.dumps(result).lower())
                    # Gold failure precedes predictions; parse and I/O failures stop at their source.
                    for bad in ["\n{", '{"key":"a"}', '{"value":"a"}']:
                        (directory / "predictions.jsonl").write_text(bad)
                        result = await run(argv)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertEqual(
                            result["calls"][-1]["tool"],
                            "mathformer_proofnet_read_prediction",
                        )
                        self.assertIsNone(result["outputs"])
                    (directory / "valid.jsonl").write_text("{}\n")
                    result = await run(argv)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 2)
                    result = await run(["--split", "invalid"])
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 1)
                    argv = fixtures(directory)
                    (directory / "predictions.jsonl").unlink()
                    result = await run(argv)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 3)
                    argv = fixtures(directory)
                    result = await run(argv + ["--output-json", str(directory)])
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(
                        result["calls"][-1]["tool"], "mathformer_proofnet_write_output"
                    )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
