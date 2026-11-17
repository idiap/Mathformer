#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real registered MCP tools and Lunar/PRISM execution over finite local data."""

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
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
import yaml

from formal_science_tools import source, parse, invoke
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_benchmark_formal_science_workflow/workflow.yaml"
RECORDS = [
    {
        "field": "Other",
        "question": "{\n**\n$Q$\n}\n**",
        "answer": "}\nA\n{",
        "formal_answer": "SECRET_PROOF",
    },
    {"field": "Other", "question": "$Q$", "answer": "A", "formal_answer": ""},
    {
        "field": "Quantum Mechanics",
        "question": "Hamiltonian $H$ " * 20,
        "answer": "\\int x dx\n" * 8,
        "formal_answer": "SECRET_PROOF",
    },
    {"field": "Excluded", "question": "x", "answer": "y"},
]


def snapshot(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


def oracle():
    path = ROOT / "tests/mcp/fixtures/formal_science_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "formal_science_oracle", SourceFileLoader("formal_science_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def cli(module, args):
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code = module.main(args)
        except SystemExit as error:
            code = error.code
    return {"exit_code": code, "stdout": stdout.getvalue(), "stderr": stderr.getvalue()}


class FormalScienceTests(unittest.TestCase):
    def test_shared_source_and_original(self):
        old = oracle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / source().DATASET_FILENAME
            dataset.write_text(json.dumps(RECORDS))
            for args in [
                ["self-test"],
                ["stats", "--output", directory],
                *[
                    ["rank", "--output", directory, "-n", str(n)]
                    for n in [-9, -1, 0, 1, 99]
                ],
            ]:
                expected = cli(old, args)
                self.assertEqual(cli(source(), args), expected)
                with redirect_stderr(io.StringIO()):
                    self.assertEqual(
                        invoke(parse(args)["args"]["command"], parse(args)["args"]),
                        expected,
                    )
            for args in [[], ["--help"], ["rank", "-n", "bad"], ["unknown"]]:
                self.assertEqual(cli(source(), args), cli(old, args))
            for content in ["{}", "[null]", "[{}]", "{"]:
                dataset.write_text(content)
                self.assertEqual(
                    cli(source(), ["stats", "--output", directory]),
                    cli(old, ["stats", "--output", directory]),
                )
            self.assertEqual(
                source()._clean_informal_text("{\n}\n**\nx\n}\n{\n**"), "x"
            )
            with self.assertRaisesRegex(ValueError, "does not match"):
                invoke("rank", parse(["self-test"])["args"])

    def test_registered_tools_and_lunar_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_benchmark_formal_science_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 1200, "max_operation_calls": 2},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        failure = None
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            boundary, events = root / "http.json", root / "requests.jsonl"
            boundary.write_text(json.dumps({"body": json.dumps(RECORDS)}))
            config = StdioConfig(
                command=sys.executable,
                args=[
                    str(ROOT / "tests/mcp/fixtures/formal_science_server.py"),
                    str(boundary),
                    str(events),
                ],
                cwd=str(ROOT),
            )
            async with manager.open("formal-science", config, {}) as remote:
                try:
                    tools = [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in await remote.tools()
                    ]

                    def compile(doc):
                        assets = snapshot(doc)
                        compiled = compile_workflow(
                            "mcp:formal-science",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools,
                        )
                        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                        self.assertTrue(compiled["runtime_source"])
                        self.assertEqual(
                            set(compiled["bindings"]), set(doc["operations"])
                        )
                        return compiled, assets

                    workflow, assets = compile(document)

                    async def authorize():
                        pass

                    async def run(argv, doc=None):
                        compiled, received = compile(doc) if doc else (workflow, assets)
                        return await execute(
                            compiled, received, {"extra_args": argv}, remote, authorize
                        )

                    async def accepted(argv, handler):
                        result = await run(argv)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            [call["tool"] for call in result["calls"]],
                            [
                                "mathformer_formal_science_parse",
                                "mathformer_formal_science_" + handler,
                            ],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        return result["outputs"]

                    await accepted(["self-test"], "self_test")
                    data = root / "data"
                    args = ["download", "--output", str(data)]
                    output = await accepted(args, "download")
                    self.assertEqual(output["exit_code"], 0)
                    dataset = data / source().DATASET_FILENAME
                    self.assertEqual(json.loads(dataset.read_text()), RECORDS)
                    self.assertEqual(len(events.read_text().splitlines()), 1)
                    self.assertEqual(
                        json.loads(events.read_text())["url"], source().DATASET_URL
                    )
                    # Existing files bypass HTTP and validation, including corrupt JSON.
                    dataset.write_text("corrupt")
                    await accepted(args, "download")
                    self.assertEqual(dataset.read_text(), "corrupt")
                    self.assertEqual(len(events.read_text().splitlines()), 1)
                    for specification in [
                        {"body": "{}"},
                        {"body": "{"},
                        {"error": "offline"},
                    ]:
                        boundary.write_text(json.dumps(specification))
                        result = await accepted([*args, "--force"], "download")
                        self.assertEqual(result["exit_code"], 2)
                        self.assertIn("error:", result["stderr"])
                        self.assertEqual(dataset.read_text(), "corrupt")
                    boundary.write_text(
                        json.dumps({"unexpected": "unhandled HTTP failure"})
                    )
                    result = await run([*args, "--force"])
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 2)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(events.read_text().splitlines()), 5)
                    boundary.write_text(json.dumps({"body": json.dumps(RECORDS)}))
                    await accepted([*args, "--force"], "download")
                    old = oracle()
                    for argv in [
                        ["stats", "--output", str(data)],
                        *[
                            ["rank", "--output", str(data), "-n", str(n)]
                            for n in [-99, -1, 0, 1, 100]
                        ],
                        ["rank", "--output", str(data), "--fields", " "],
                        ["rank", "--output", str(data), "--fields", "Absent"],
                    ]:
                        output = await accepted(argv, argv[0])
                        self.assertEqual(output, cli(old, argv))
                    output = await accepted(["stats", "--output", str(data)], "stats")
                    stats = json.loads(output["stdout"])
                    self.assertEqual(
                        stats["fields"],
                        {"Other": 2, "Quantum Mechanics": 1, "Excluded": 1},
                    )
                    self.assertEqual(
                        stats["formal_answer_records_present_but_withheld"], 2
                    )
                    output = await accepted(
                        ["rank", "--output", str(data), "--fields", "Other"], "rank"
                    )
                    self.assertEqual(
                        [
                            json.loads(line)["source_index"]
                            for line in output["stdout"].splitlines()
                        ],
                        [1, 0],
                    )
                    # Negative slicing, empty selection and finite exhaustion; compare
                    # JSONL and each sequential TeX write byte-for-byte with the oracle.
                    export = root / "sample.jsonl"
                    for size in [-1, 0, 100]:
                        bundles = root / ("bundles" + str(size))
                        argv = [
                            "export-informal-sample",
                            "--output",
                            str(data),
                            "--output-file",
                            str(export),
                            "--sample-size",
                            str(size),
                            "--bundle-dir",
                            str(bundles),
                        ]
                        output = await accepted(argv, "export")
                        contents = export.read_bytes()
                        packets = {p.name: p.read_bytes() for p in bundles.iterdir()}
                        self.assertEqual(output, cli(old, argv))
                        self.assertEqual(export.read_bytes(), contents)
                        self.assertEqual(
                            {p.name: p.read_bytes() for p in bundles.iterdir()}, packets
                        )
                        payloads = [json.loads(line) for line in contents.splitlines()]
                        self.assertEqual(len(payloads), {-1: 2, 0: 0, 100: 3}[size])
                        self.assertEqual(len(packets), len(payloads))
                        for index, payload in enumerate(payloads, 1):
                            self.assertEqual(payload["rank"], index)
                            self.assertNotIn("formal_answer", payload)
                            self.assertNotIn("SECRET_PROOF", json.dumps(payload))
                            self.assertEqual(
                                payload["withheld_fields"], ["formal_answer"]
                            )
                            self.assertEqual(
                                payload["source_sha256"],
                                hashlib.sha256(
                                    payload["source_text"].encode()
                                ).hexdigest(),
                            )
                    # A late bundle failure preserves the completed earlier JSONL.
                    blocked = root / "blocked"
                    blocked.write_text("file")
                    result = await run(
                        [
                            "export-informal-sample",
                            "--output",
                            str(data),
                            "--output-file",
                            str(export),
                            "--bundle-dir",
                            str(blocked),
                        ]
                    )
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(export.read_text().splitlines()), 3)
                    self.assertEqual(len(result["calls"]), 2)
                    for content in ["{}", "[null]", "[{}]", "{"]:
                        dataset.write_text(content)
                        argv = ["stats", "--output", str(data)]
                        self.assertEqual(await accepted(argv, "stats"), cli(old, argv))
                    dataset.unlink()
                    self.assertEqual(
                        (await accepted(["stats", "--output", str(data)], "stats"))[
                            "exit_code"
                        ],
                        2,
                    )
                    dataset.mkdir()
                    result = await run(["stats", "--output", str(data)])
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 2)
                    for argv in [
                        [],
                        ["--help"],
                        ["unknown"],
                        ["rank", "-n", "bad"],
                        ["export-informal-sample"],
                    ]:
                        result = await run(argv)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            [call["tool"] for call in result["calls"]],
                            [
                                "mathformer_formal_science_parse",
                                "mathformer_formal_science_parse_exit",
                            ],
                        )
                        self.assertEqual(
                            result["outputs"]["exit_code"],
                            0 if argv == ["--help"] else 2,
                        )
                        self.assertTrue(
                            result["outputs"]["stdout"]
                            if argv == ["--help"]
                            else result["outputs"]["stderr"]
                        )
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 1
                    result = await run(["self-test"], bounded)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        sum(
                            bool(call.get("transport_call_performed"))
                            for call in result["calls"]
                        ),
                        1,
                    )
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    self.assertIn("budget", json.dumps(result).lower())
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    compiled, received = compile(timed)

                    async def wait_for_authority():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(
                            compiled,
                            received,
                            {"extra_args": ["self-test"]},
                            remote,
                            wait_for_authority,
                        )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
