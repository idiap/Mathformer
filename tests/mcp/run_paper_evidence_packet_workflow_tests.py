#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated filesystem fixtures, production MCP tools and real Lunar/PRISM.

This workflow has no model, provider or external compiler boundary to replace.
The PRISM parser/checker/compiler/runtime are never stubbed. No hub action or
recorded validation command is launched, and no provider configuration is read.
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
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
from paper_evidence_packet_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_paper_evidence_packet_workflow/workflow.yaml"


def oracle():
    path = ROOT / "tests/mcp/fixtures/paper_evidence_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "paper_evidence_oracle", SourceFileLoader("paper_evidence_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.REPO_ROOT = ROOT
    return module


def snapshot(document):
    def asset(path, content):
        return {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


class EvidenceTests(unittest.TestCase):
    def test_native_original_equivalence_and_finite_traversal(self):
        native, original = source(), oracle()
        self.assertEqual(
            native.parse_options([]),
            {
                "feature": "all",
                "output": "artifacts/paper_skills/new_functionality_evidence_packet.json",
                "json": False,
            },
        )
        for feature in ["all", *native.FEATURE_BUILDERS]:
            self.assertEqual(
                native.build_packet(feature), original.build_packet(feature)
            )
        with tempfile.TemporaryDirectory(prefix="paper-evidence-") as directory:
            path = Path(directory)
            existing = path / "present"
            existing.write_text("fixture")
            for value, kind in (
                (str(path), "directory"),
                (str(existing), "file"),
                (str(path / "absent"), "missing"),
            ):
                self.assertEqual(native.path_entry(value), original.path_entry(value))
                self.assertEqual(native.path_entry(value)["kind"], kind)

            # Accumulate across packets and nested containers, sort and dedupe;
            # records themselves recurse, scalar leaves and empty lists terminate.
            def record(name, exists=False):
                return {
                    "path": name,
                    "exists": exists,
                    "kind": "file" if exists else "missing",
                }

            nested = [
                {"a": [record("z"), {"b": record("a")}, None, 3, []]},
                record("z"),
                record("present", True),
            ]
            self.assertEqual(
                native.iter_path_records(nested), original.iter_path_records(nested)
            )
            self.assertEqual(native.missing_paths(nested), ["a", "z"])
            self.assertEqual(native.missing_paths([]), [])
            self.assertEqual(native.iter_path_records("scalar"), [])
            for json_mode in (False, True):
                destination = path / (
                    "json/output.json" if json_mode else "text/output.json"
                )
                argv = [
                    "program",
                    "--feature",
                    "controlled-action-hub",
                    "--output",
                    str(destination),
                ] + (["--json"] if json_mode else [])
                streams = []
                for module in (original, native):
                    stream = io.StringIO()
                    with patch.object(sys, "argv", argv), redirect_stdout(stream):
                        self.assertEqual(module.main(), 0)
                    streams.append(stream.getvalue())
                    self.assertEqual(
                        destination.read_text(),
                        json.dumps(
                            original.build_packet("controlled-action-hub"),
                            indent=2,
                            sort_keys=True,
                        )
                        + "\n",
                    )
                self.assertEqual(*streams)
            for args, code in (
                (["--feature", "invalid"], 2),
                (["--unknown"], 2),
                (["--help"], 0),
            ):
                with (
                    redirect_stdout(io.StringIO()),
                    redirect_stderr(io.StringIO()),
                    self.assertRaises(SystemExit) as error,
                ):
                    native.parse_options(args)
                self.assertEqual(error.exception.code, code)
            self.assertEqual(
                native.resolve_output("relative.json"), ROOT / "relative.json"
            )
            with self.assertRaises(OSError):
                native.write_packet(str(existing / "child"), native.build_packet("all"))

    def test_real_mcp_lunar_compile_execute(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_paper_evidence_packet_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        # Focused production entrypoint: no unrelated backend or credential imports.
        server = "scripts/paper_evidence_packet_tools.py"
        with tempfile.TemporaryDirectory(prefix="paper-evidence-runtime-") as directory:
            directory = Path(directory)
            async with manager.open(
                "evidence",
                StdioConfig(
                    command=sys.executable,
                    args=[server, "--write-root", str(directory)],
                    cwd=str(ROOT),
                ),
                {},
            ) as remote:
                failure = None
                try:
                    tools = [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in await remote.tools()
                    ]

                    def compile(doc, inventory=None):
                        assets = snapshot(doc)
                        selected = workflow_documents([DESCRIPTOR], assets)[0]
                        workflow = compile_workflow(
                            "mcp:evidence",
                            selected,
                            tools if inventory is None else inventory,
                        )
                        return workflow, assets

                    workflow, assets = compile(document)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(
                        set(workflow["bindings"]), set(document["operations"])
                    )
                    missing, _ = compile(document, [])
                    self.assertFalse(missing["runnable"])

                    async def authorize():
                        pass

                    async def run(argv, doc=None):
                        selected, received = (
                            compile(doc) if doc is not None else (workflow, assets)
                        )
                        return await execute(
                            selected, received, {"argv": argv}, remote, authorize
                        )

                    # All and every registered single feature; deterministic native
                    # templates, actual filesystem inspection, real JSON writes.
                    for index, feature in enumerate(
                        ["all", *source().FEATURE_BUILDERS]
                    ):
                        output = directory / f"{index}/packet.json"
                        json_mode = index % 2 == 0
                        argv = ["--feature", feature, "--output", str(output)] + (
                            ["--json"] if json_mode else []
                        )
                        result = await run(argv)
                        self.assertEqual(result["status"], "accepted", result)
                        expected = oracle().build_packet(feature)
                        self.assertEqual(result["outputs"]["packet"], expected)
                        self.assertEqual(result["outputs"]["artifact"], expected)
                        self.assertEqual(json.loads(output.read_text()), expected)
                        self.assertEqual(
                            output.read_text(),
                            json.dumps(expected, indent=2, sort_keys=True) + "\n",
                        )
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            summary, code = source().emit_result(
                                source().parse_options(argv), expected, output
                            )
                        self.assertEqual(result["outputs"]["result"], summary)
                        self.assertEqual(result["outputs"]["exit_code"], code)
                        self.assertEqual(result["outputs"]["stdout"], stream.getvalue())
                        self.assertEqual(len(result["calls"]), 5)
                        self.assertEqual(
                            [call["tool"] for call in result["calls"]],
                            [
                                "mathformer_paper_evidence_parse",
                                "mathformer_paper_evidence_build_"
                                + ("all" if feature == "all" else "one"),
                                "mathformer_paper_evidence_finalize",
                                "mathformer_paper_evidence_write",
                                "mathformer_paper_evidence_emit",
                            ],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        if feature == "all":
                            self.assertEqual(
                                [p["feature_id"] for p in expected["features"]],
                                list(source().FEATURE_BUILDERS),
                            )
                            self.assertEqual(summary["feature_count"], 4)
                        else:
                            self.assertEqual(summary["feature_count"], 1)
                        self.assertEqual(
                            summary["missing_path_count"],
                            len(expected["missing_paths"]),
                        )
                    # Native missing-path metadata is successful, not a retry signal.
                    packet = {
                        "schema_version": 1,
                        "packet_type": "paper_new_functionality_evidence",
                        "nested": [
                            {"path": "absent", "exists": False, "kind": "missing"}
                        ],
                    }
                    finalized = await remote.call(
                        "mathformer_paper_evidence_finalize",
                        {
                            "args": {"feature": "controlled-action-hub"},
                            "packets": [packet],
                        },
                    )
                    self.assertEqual(finalized["packet"]["missing_paths"], ["absent"])
                    # Native argparse termination stops before builder/write, with
                    # SystemExit contained at the transport boundary.
                    for argv in (["--feature", "bad"], ["--unknown"], ["--help"]):
                        failed = await run(argv)
                        self.assertEqual(failed["status"], "failed", failed)
                        self.assertIsNone(failed["outputs"])
                        self.assertEqual(len(failed["calls"]), 1)
                        self.assertEqual(failed["calls"][0]["status"], "rejected")
                    blocker = directory / "blocker"
                    blocker.write_text("file")
                    failed = await run(["--output", str(blocker / "child.json")])
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(len(failed["calls"]), 4)
                    self.assertEqual(failed["calls"][-1]["status"], "rejected")
                    self.assertEqual(blocker.read_text(), "file")
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 3
                    output = directory / "never-written.json"
                    failed = await run(["--output", str(output)], bounded)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in failed["calls"]
                        ),
                        3,
                    )
                    self.assertIn("budget", str(failed).lower())
                    self.assertFalse(output.exists())
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    selected, received = compile(timed)

                    async def pending():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(
                            selected,
                            received,
                            {"argv": ["--output", str(output)]},
                            remote,
                            pending,
                        )
                    self.assertFalse(output.exists())
                    # Deployment restrictions remain effective on the real tool.
                    with self.assertRaises(Exception):
                        await remote.call(
                            "mathformer_paper_evidence_write",
                            {
                                "args": {
                                    "output": str(
                                        directory.parent / "outside-evidence-root.json"
                                    )
                                },
                                "packet": packet,
                            },
                        )
                    self.assertFalse(
                        (directory.parent / "outside-evidence-root.json").exists()
                    )
                    configured = server
                except Exception as error:
                    failure = error
            if failure:
                raise failure
            async with manager.open(
                "readonly",
                StdioConfig(
                    command=sys.executable,
                    args=[configured, "--readonly"],
                    cwd=str(ROOT),
                ),
                {},
            ) as remote:
                with self.assertRaises(Exception):
                    await remote.call(
                        "mathformer_paper_evidence_write",
                        {"args": {"output": str(output)}, "packet": packet},
                    )
                self.assertFalse(output.exists())
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
