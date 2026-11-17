#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native fixture steps, production MCP registrations and real Lunar/PRISM.

This deterministic source has no external provider/compiler boundary. No model,
credentials, external compiler or prover is used. Fixture filesystem inputs are
real; PRISM parsing, checking, compilation and execution are never substituted.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
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
from concept_canonicalize_tools import source
import mathformer as hub
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathformerphysicslib_concept_canonicalize_workflow/workflow.yaml"


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


class ConceptTests(unittest.TestCase):
    def test_native_source_original_and_finite_ownership_paths(self):
        native = source()
        loader = SourceFileLoader(
            "concept_original",
            str(ROOT / "tests/mcp/fixtures/concept_canonicalize_original.py.txt"),
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = native.self_test_payload(root)
            self.assertEqual(report["graph"]["concept_count"], 2)
            self.assertEqual(report["graph"]["ambiguous_count"], 1)
            self.assertEqual(report["generative"]["probe_count"], 7)
            self.assertEqual(report["gate"]["status"], "blocked")
            self.assertEqual(native.canonicalize(report)["concepts"], [])
            for argv in (["--self-test", "--json"], ["--self-test"]):
                outputs = []
                for entry in (original.main, native.main):
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        self.assertEqual(entry(argv), 0)
                    outputs.append(stream.getvalue())
                self.assertEqual(*outputs)
                self.assertEqual(json.loads(outputs[0])["concept_count"], 0)
            inventory = {
                "concept_occurrence_index": {
                    "z": [{"path": "a"}, {"path": "b"}],
                    "s": [{"path": "only"}],
                    "f": [
                        {"path": "other"},
                        {"path": "foundation", "is_foundation": True},
                    ],
                    "e": [],
                }
            }
            graph = native.canonicalize(inventory)
            self.assertEqual(
                [c["concept_id"] for c in graph["concepts"]], ["e", "f", "s", "z"]
            )
            self.assertEqual(
                [c["owner_module"] for c in graph["concepts"]],
                [None, "foundation", "only", None],
            )
            self.assertEqual(graph["ambiguous_count"], 2)
            self.assertEqual(
                graph["concepts"][0]["blockers"], ["missing_canonical_owner"]
            )
            self.assertEqual(
                graph["concepts"][-1]["occurrences"],
                inventory["concept_occurrence_index"]["z"],
            )
            # Non-selected input/output CLI branches continue sharing native logic.
            input_file, output_file = root / "in.json", root / "out.json"
            input_file.write_text(json.dumps(inventory))
            for entry in (original.main, native.main):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        entry(
                            ["--input", str(input_file), "--output", str(output_file)]
                        ),
                        0,
                    )
                self.assertEqual(json.loads(output_file.read_text()), graph)
            with (
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as caught,
            ):
                native.main(["--invalid"])
            self.assertEqual(caught.exception.code, 2)
            import coherence_common as common

            fixture = common.self_test_inventory()
            fixture_graph = common.canonicalize(fixture)
            grounding = common.audit_grounding(fixture_graph)
            critics = common.self_test_critics(fixture, fixture_graph, grounding, root)
            with self.assertRaises(AssertionError):
                common.finish_self_test(
                    {**fixture_graph, "concept_count": 0}, grounding, critics
                )
            hint_id, rule = next(
                (key, value)
                for key, value in common.CONCEPT_RULES.items()
                if value.get("owner_hint")
            )
            hinted = [
                {"path": "first", "is_foundation": True},
                {"path": rule["owner_hint"] + "/a"},
                {"path": rule["owner_hint"] + "/b"},
            ]
            self.assertEqual(common.canonical_owner(hint_id, hinted), hinted[1]["path"])

    def test_registered_mcp_lunar_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_mathformerphysicslib_concept_canonicalize_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/concept-canonicalize.workflow.json"
                ).read_text()
            ),
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        # Import registered tools without launcher/config/credential loading.
        server = 'import sys;sys.path.insert(0,"scripts");from mcp.server.fastmcp import FastMCP;from concept_canonicalize_tools import register_concept_canonicalize_tools;mcp=FastMCP("concept-fixture");register_concept_canonicalize_tools(mcp);mcp.run(transport="stdio")'
        failure = None
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            async with manager.open(
                "concept",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
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
                        return (
                            compile_workflow(
                                "mcp:concept",
                                selected,
                                tools if inventory is None else inventory,
                            ),
                            received,
                        )

                    workflow, received = compile(document)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(
                        set(workflow["bindings"]), set(document["operations"])
                    )
                    unavailable, _ = compile(document, [])
                    self.assertFalse(unavailable["runnable"])
                    context = dict(
                        dry_run=False,
                        json_output=True,
                        keep_going=False,
                        allow_mutating=False,
                        write_report=False,
                    )

                    async def authorize():
                        pass

                    async def run(ctx=None, extra=None, doc=None, repository=None):
                        compiled, snapshot = (
                            compile(doc) if doc else (workflow, received)
                        )
                        return await execute(
                            compiled,
                            snapshot,
                            {
                                "context": ctx or context,
                                "extra_args": extra or [],
                                "repository_root": str(repository or root),
                            },
                            remote,
                            authorize,
                        )

                    result = await run()
                    self.assertEqual(result["status"], "accepted", result)
                    payload = result["outputs"]["result"]
                    self.assertTrue(payload["ok"], payload)
                    self.assertEqual(payload["returncode"], 0)
                    expected = source().canonicalize(source().self_test_payload(root))
                    self.assertEqual(
                        payload["stdout"],
                        json.dumps(expected, indent=2, sort_keys=True) + "\n",
                    )
                    self.assertEqual(payload["stderr"], "")
                    self.assertTrue(payload["write_audit"]["ok"])
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [
                            "mathformer_concept_canonicalize_" + s
                            for s in ("prepare", "self_test", "canonicalize", "finish")
                        ],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    # Native dry-run and rejected extra args stop before self-test.
                    for ctx, extra in (
                        ({**context, "dry_run": True}, []),
                        (context, ["--input", "forbidden"]),
                    ):
                        stopped = await run(ctx, extra)
                        self.assertEqual(stopped["status"], "accepted", stopped)
                        expected_stop = hub.run_action(
                            "mathformerphysicslib:concept-canonicalize",
                            hub.build_registry(),
                            hub.RunContext(**ctx),
                            extra_args=extra,
                        )
                        self.assertEqual(stopped["outputs"]["result"], expected_stop)
                        self.assertEqual(
                            [c["tool"] for c in stopped["calls"]],
                            [
                                "mathformer_concept_canonicalize_prepare",
                                "mathformer_concept_canonicalize_stopped",
                            ],
                        )
                    # Real filesystem decoding failure in the native critic aborts
                    # the self-test, with no canonicalization, finish, or retry.
                    report = source().self_test_payload(root)
                    owner = next(
                        c["owner_module"]
                        for c in report["graph"]["concepts"]
                        if c["owner_module"]
                    )
                    broken = root / "broken"
                    bad_file = broken / owner
                    bad_file.parent.mkdir(parents=True)
                    bad_file.write_bytes(b"\xff")
                    failed = await run(repository=broken)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual(len(failed["calls"]), 2)
                    self.assertEqual(failed["calls"][-1]["status"], "rejected")
                    limited = deepcopy(document)
                    limited["policy"]["limits"]["max_operation_calls"] = 2
                    failed = await run(doc=limited)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in failed["calls"]
                        ),
                        2,
                    )
                    self.assertIn("budget", str(failed).lower())
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    compiled, snapshot = compile(timed)

                    async def pending():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(
                            compiled,
                            snapshot,
                            {
                                "context": context,
                                "extra_args": [],
                                "repository_root": str(root),
                            },
                            remote,
                            pending,
                        )
                    # Inspect the actual intermediate report via the real tool.
                    boundary = (
                        await remote.call(
                            "mathformer_concept_canonicalize_prepare",
                            {
                                "context": context,
                                "extra_args": [],
                                "repository_root": str(root),
                            },
                        )
                    )["boundary"]
                    checked = await remote.call(
                        "mathformer_concept_canonicalize_self_test",
                        {"boundary": boundary, "repository_root": str(root)},
                    )
                    self.assertEqual(checked["report"], report)
                    graph = (
                        await remote.call(
                            "mathformer_concept_canonicalize_canonicalize", checked
                        )
                    )["graph"]
                    self.assertEqual(graph, expected)
                    # The source-owned audit detects a real undeclared write.
                    marker = root / "concept-canonicalize-fixture.tmp"
                    self.assertFalse(marker.exists())
                    try:
                        marker.write_text("fixture")
                        audited = await remote.call(
                            "mathformer_concept_canonicalize_finish",
                            {
                                "boundary": boundary,
                                "graph": graph,
                                "repository_root": str(root),
                            },
                        )
                        self.assertFalse(audited["result"]["ok"])
                        self.assertEqual(
                            audited["result"]["status"], "undeclared_writes"
                        )
                        self.assertIn(
                            marker.name,
                            audited["result"]["write_audit"]["unexpected_paths"],
                        )
                    finally:
                        marker.unlink(missing_ok=True)
                except Exception as error:
                    failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
