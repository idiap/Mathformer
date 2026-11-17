#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native ProofNet, actual registered MCP tools and real Lunar/PRISM execution.

Only the remote dataset provider is substituted. This workflow has no model or
external theorem compiler; the PRISM parser, checker, compiler and runtime run
unchanged. All data and output live in temporary directories.
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
from proofnet_tools import source, parse, invoke

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_benchmark_proofnet_workflow/workflow.yaml"
CONTRACT = Path(os.environ.get("WORKFLOW_CONTRACT_PATH", ROOT / DESCRIPTOR))


def snapshot(document):
    texts = {DESCRIPTOR: json.dumps(document)}
    for row in document["provenance"]["sources"]:
        content = (ROOT / row["path"]).read_text()
        if "digest" in row:
            assert (
                row["digest"]
                == "sha256:" + hashlib.sha256(content.encode()).hexdigest()
            ), row
        texts[row["path"]] = content
    return [
        {
            "path": p,
            "content": t,
            "encoding": "text",
            "sha256": hashlib.sha256(t.encode()).hexdigest(),
        }
        for p, t in texts.items()
    ]


def oracle():
    name = "proofnet_original"
    spec = importlib.util.spec_from_loader(
        name,
        SourceFileLoader(
            name, str(ROOT / "tests/mcp/fixtures/proofnet_original.py.txt")
        ),
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def cli(module, argv):
    output = io.StringIO()
    with patch.object(sys, "argv", ["proofnet.py", *argv]), redirect_stdout(output):
        result = module.main()
    return {"result": result, "stdout": output.getvalue()}


def fixtures(directory, empty=False):
    directory.mkdir(exist_ok=True)
    rows = (
        []
        if empty
        else [
            dict(
                id=id,
                nl_statement=f"α = {i}",
                nl_proof="proof",
                formal_statement=f"{i} = {i}",
                src_header="",
            )
            for i, id in enumerate([7, 7, "b"])
        ]
    )
    for filename in ["valid.jsonl", "test.jsonl"]:
        (directory / filename).write_text(
            "\n" + "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
        )
    for filename in source().OPTIONAL_FILES:
        (directory / filename).write_text(filename)
    return rows


class ProofNetTests(unittest.TestCase):
    def test_native_equivalence_and_ports(self):
        native, original = source(), oracle()
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            fixtures(data)
            for argv in [
                ["stats"],
                ["sample"],
                ["sample", "-n", "0"],
                ["sample", "-n", "-1"],
                ["sample", "-n", "99"],
                ["sample", "--split", "test"],
                [
                    "export-inputs",
                    "--output-file",
                    str(data / "export.jsonl"),
                    "--include-proof",
                    "--formal-language",
                    "Lean4",
                ],
            ]:
                argv += ["--output", str(data)]
                expected = cli(original, argv)
                self.assertEqual(cli(native, argv), expected)
                self.assertEqual(invoke(argv[0], parse(argv)["args"]), expected)
            for malformed in ["{}\n", "{\n"]:
                (data / "valid.jsonl").write_text(malformed)
                argv = ["sample", "--output", str(data), "-n", "0"]
                self.assertEqual(cli(native, argv), cli(original, argv))
                self.assertEqual(
                    cli(native, argv)["result"], 2
                )  # full load precedes slicing
            with self.assertRaises(ValueError):
                invoke("stats", parse(["sample"])["args"])

    def test_registered_tools_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document["id"], "hub_benchmark_proofnet_workflow")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 2},
        )
        self.assertEqual(document["policy"]["failure"]["retry"]["max_attempts"], 1)
        manager = SessionManager()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            provider = root / "provider"
            fixtures(provider)
            data = root / "data"
            fixtures(data)
            boundary, ledger = root / "boundary.json", root / "ledger.jsonl"
            boundary.write_text(json.dumps({"directory": str(provider)}))
            config = StdioConfig(
                command=sys.executable,
                args=[
                    str(ROOT / "tests/mcp/fixtures/proofnet_server.py"),
                    str(boundary),
                    str(ledger),
                ],
                cwd=str(ROOT),
            )
            async with manager.open("proofnet", config, {}) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                async def allow():
                    pass

                async def run(argv, doc=None):
                    assets = snapshot(document if doc is None else doc)
                    compiled = compile_workflow(
                        "mcp:proofnet",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools,
                    )
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(
                        set(compiled["bindings"]), set(document["operations"])
                    )
                    return await execute(
                        compiled, assets, {"extra_args": argv}, remote, allow
                    )

                async def equivalent(argv):
                    expected = cli(oracle(), argv)
                    result = await run(argv)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], expected)
                    self.assertEqual(len(result["calls"]), 2)
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    return result

                for empty in [False, True]:
                    fixtures(data, empty)
                    stats = await equivalent(["stats", "--output", str(data)])
                    payload = json.loads(stats["outputs"]["stdout"])
                    self.assertEqual(payload["total_examples"], 0 if empty else 6)
                    self.assertEqual(
                        payload["splits"]["validation"]["unique_ids"], 0 if empty else 2
                    )
                    for n in ["0", "1", "-1", "99"]:
                        sample = await equivalent(
                            ["sample", "--output", str(data), "-n", n]
                        )
                        self.assertEqual(
                            sample["outputs"]["stdout"].count('"id"'),
                            0 if empty else {"0": 0, "1": 1, "-1": 2, "99": 3}[n],
                        )
                    for proof in [False, True]:
                        target = root / "nested/export.jsonl"
                        argv = [
                            "export-inputs",
                            "--output",
                            str(data),
                            "--output-file",
                            str(target),
                            "--split",
                            "test",
                        ] + (
                            ["--include-proof", "--formal-language", "Lean4"]
                            if proof
                            else []
                        )
                        expected = cli(oracle(), argv)
                        before = target.read_bytes()
                        result = await run(argv)
                        self.assertEqual(result["outputs"], expected)
                        self.assertEqual(target.read_bytes(), before)
                        rows = [
                            json.loads(line) for line in target.read_text().splitlines()
                        ]
                        self.assertEqual(len(rows), 0 if empty else 3)
                        if rows:
                            self.assertEqual(
                                [row["id"] for row in rows], ["7", "7", "b"]
                            )
                            self.assertEqual("nl_proof" in rows[0], proof)
                            self.assertIn(
                                "Lean4" if proof else "Lean3", rows[0]["prompt"]
                            )
                # Native finite list bounds: two required files, six with optional files.
                destination = root / "download"
                argv = ["download", "--output", str(destination), "--no-optional"]
                result = await run(argv)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"], cli(oracle(), argv))
                calls = [json.loads(line) for line in ledger.read_text().splitlines()]
                self.assertEqual(
                    [c["filename"] for c in calls], ["valid.jsonl", "test.jsonl"]
                )
                self.assertEqual(
                    calls[0],
                    {
                        "repo_id": source().DATASET_REPO_ID,
                        "repo_type": "dataset",
                        "filename": "valid.jsonl",
                        "cache_dir": str(destination / ".hf_cache"),
                    },
                )
                await run(argv)  # existing targets reuse without contacting provider
                self.assertEqual(len(ledger.read_text().splitlines()), 2)
                cache = root / "cache"
                result = await run(
                    [
                        "download",
                        "--output",
                        str(destination),
                        "--force",
                        "--cache-dir",
                        str(cache),
                    ]
                )
                self.assertEqual(result["outputs"]["result"], 0)
                calls = [json.loads(line) for line in ledger.read_text().splitlines()]
                self.assertEqual(
                    [c["filename"] for c in calls[2:]],
                    ["valid.jsonl", "test.jsonl", *source().OPTIONAL_FILES],
                )
                self.assertTrue(all(c["cache_dir"] == str(cache) for c in calls[2:]))
                for filename in ["valid.jsonl", "test.jsonl", *source().OPTIONAL_FILES]:
                    self.assertEqual(
                        (destination / filename).read_bytes(),
                        (provider / filename).read_bytes(),
                    )
                # External error propagates immediately, without retry or later file downloads.
                boundary.write_text(json.dumps({"error": "provider unavailable"}))
                failed = await run(argv + ["--force"])
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(len(ledger.read_text().splitlines()), 9)
                self.assertIsNone(failed["outputs"])
                # Malformed or missing data is caught by native main's error boundary.
                for content in ["{}\n", "{\n"]:
                    (data / "valid.jsonl").write_text(content)
                    await equivalent(["sample", "--output", str(data), "-n", "0"])
                (data / "valid.jsonl").unlink()
                error = await equivalent(["stats", "--output", str(data)])
                self.assertEqual(error["outputs"]["result"], 2)
                for argv in [[], ["bogus"], ["export-inputs"], ["sample", "-n", "bad"]]:
                    failed = await run(argv)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(len(failed["calls"]), 1)
                fixtures(data)
                # Filesystem failures outside ProofNetError must propagate.
                failed = await run(
                    ["export-inputs", "--output", str(data), "--output-file", str(data)]
                )
                self.assertEqual(failed["status"], "failed", failed)
                # Actual runtime call budget stops dispatch, leaving output untouched.
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 1
                target = root / "must-not-write.jsonl"
                failed = await run(
                    [
                        "export-inputs",
                        "--output",
                        str(data),
                        "--output-file",
                        str(target),
                    ],
                    bounded,
                )
                self.assertEqual(failed["status"], "failed", failed)
                self.assertFalse(target.exists())
                self.assertIn("budget", json.dumps(failed).lower())
        self.assertFalse(manager.active)
        # The same write guard installed in production honors service scope.
        import mcp_server as server

        with tempfile.TemporaryDirectory() as temp:
            allowed = Path(temp).resolve()
            with (
                patch.object(server, "_ALLOWED_WRITE_ROOTS", [allowed]),
                patch.object(server, "_READONLY", False),
            ):
                server._proofnet_write_policy([allowed / "output", allowed / "cache"])
                with self.assertRaisesRegex(ValueError, "outside allowed"):
                    server._proofnet_write_policy([allowed.parent / "outside"])
            with patch.object(server, "_READONLY", True):
                with self.assertRaisesRegex(ValueError, "read-only"):
                    server._proofnet_write_policy([allowed / "output"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
