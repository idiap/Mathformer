#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic filesystem fixtures through production MCP and real PRISM.

This workflow has no model/provider or external compiler boundary. Real PRISM
parse/check/compile/runtime are exercised; no production inventory is run.
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
import yaml
from coherence_inventory_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathformerphysicslib_coherence_inventory_workflow/workflow.yaml"


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


class CoherenceInventoryTests(unittest.TestCase):
    def test_native_branches_bounds_and_original_cli(self):
        cli, native = source(), source().common
        for argv in (["--invalid"], ["--output"]):
            with (
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as caught,
            ):
                cli.parse_options(argv)
            self.assertEqual(caught.exception.code, 2)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = native.self_test_inventory()
            graph = native.canonicalize(fixture)
            grounding = native.audit_grounding(graph)
            critics = native.self_test_critics(fixture, graph, grounding, root)
            payload = native.finish_self_test(graph, grounding, critics)
            self.assertEqual(payload, native.self_test_payload(root))
            self.assertEqual(graph["concept_count"], 2)
            self.assertEqual(graph["ambiguous_count"], 1)
            self.assertEqual(
                sum(len(x) for x in fixture["concept_occurrence_index"].values()), 4
            )
            self.assertEqual(
                critics["reports"][0]["reuse_metrics"]["healthy_downstream_uses"], 1
            )
            self.assertEqual(payload["gate"]["status"], "blocked")
            self.assertEqual(payload["generative"]["probe_count"], 7)
            self.assertTrue(
                all(
                    "Deterministic context JSON:" in p["prompt"]
                    for p in payload["generative"]["probes"]
                )
            )
            with self.assertRaises(AssertionError):
                native.finish_self_test(
                    {**graph, "concept_count": 1}, grounding, critics
                )
            # The original CLI is frozen, while its source functions share the
            # refactored implementation. Compare parsing/emission and exit code.
            loader = SourceFileLoader(
                "inventory_original",
                str(ROOT / "tests/mcp/fixtures/coherence_inventory_original.py.txt"),
            )
            spec = importlib.util.spec_from_loader(loader.name, loader)
            original = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(original)
            # Configure filesystem context for both native entrypoints, without
            # replacing any source operation or provider/compiler implementation.
            old = (
                native.REPO_ROOT,
                native.LIB_ROOT,
                native.LEAN_ROOT,
                native.FOUNDATIONS_INDEX,
            )
            native.REPO_ROOT = root
            native.LIB_ROOT = root / "MathformerPhysicsLib"
            native.LEAN_ROOT = native.LIB_ROOT / "Lean"
            native.FOUNDATIONS_INDEX = native.LEAN_ROOT / "Foundations.lean"
            try:
                for argv in (
                    [],
                    ["--json"],
                    ["--self-test"],
                    ["--self-test", "--json"],
                ):
                    output = []
                    for main in (original.main, cli.main):
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            self.assertEqual(main(argv), 0)
                        output.append(stream.getvalue())
                    self.assertEqual(*output)
                destination = root / "nested/output.json"
                with redirect_stdout(io.StringIO()):
                    cli.main(["--output", str(destination)])
                self.assertEqual(json.loads(destination.read_text())["module_count"], 0)
            finally:
                (
                    native.REPO_ROOT,
                    native.LIB_ROOT,
                    native.LEAN_ROOT,
                    native.FOUNDATIONS_INDEX,
                ) = old
            self.assertEqual(native.build_inventory(root)["modules"], [])
            lean = root / "MathformerPhysicsLib/Lean"
            lean.mkdir(parents=True)
            (lean / "B.lean").write_text(
                "import Mathlib\nstructure LocalLaw where\n  x : Nat\n"
            )
            (lean / "A.lean").write_text("theorem example1 : True := by trivial\n")
            inv = native.build_inventory(root)
            self.assertEqual(inv["module_count"], 2)
            self.assertEqual(
                [m["path"] for m in inv["modules"]],
                [
                    "MathformerPhysicsLib/Lean/A.lean",
                    "MathformerPhysicsLib/Lean/B.lean",
                ],
            )
            self.assertEqual(inv["declaration_count"], 2)
            (root / "MathformerPhysicsLib/MANIFEST.json").write_text("{")
            with self.assertRaises(json.JSONDecodeError):
                native.build_inventory(root)

        # Ownership branches and empty traversals are all native operations.
        def occ(path, foundation=False):
            return {"path": path, "is_foundation": foundation}

        self.assertEqual(
            native.canonical_owner("unknown", [occ("b"), occ("a", True)]), "a"
        )
        self.assertEqual(native.canonical_owner("unknown", [occ("single")]), "single")
        self.assertIsNone(native.canonical_owner("unknown", [occ("a"), occ("b")]))
        self.assertIsNone(native.canonical_owner("unknown", []))
        hint = native.CONCEPT_RULES["vector_field.real.euclidean3"]["owner_hint"]
        self.assertEqual(
            native.canonical_owner(
                "vector_field.real.euclidean3", [occ("other", True), occ(hint)]
            ),
            hint,
        )
        concepts = [
            {"concept_id": str(i), "mathlib_targets": targets, "owner_module": owner}
            for i, (targets, owner) in enumerate(
                [
                    (["T"], "local"),
                    (["T"], "Foundations/F.lean"),
                    (["T"], None),
                    ([], "local"),
                ]
            )
        ]
        audited = native.audit_grounding({"concepts": concepts})
        self.assertEqual(
            [c["grounding_level"] for c in audited["concepts"]],
            ["direct_mathlib", "mathlib_bridge", "local_blocker", "unverified_local"],
        )
        self.assertEqual(audited["failed_candidate_count"], 1)
        self.assertEqual(native.canonicalize({})["concept_count"], 0)
        self.assertEqual(native.audit_grounding({})["concepts"], [])
        for findings, status in [
            ([], "accepted"),
            ([{"severity": "low"}], "accepted"),
            ([{"severity": "medium"}], "warn"),
            ([{"severity": "medium"}, {"severity": "high"}], "blocked"),
        ]:
            self.assertEqual(
                native.coherence_gate([{"findings": findings}])["status"], status
            )

    def test_registered_mcp_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_mathformerphysicslib_coherence_inventory_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 7},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            async with manager.open(
                "coherence",
                StdioConfig(
                    command=str(ROOT / ".venv/bin/python"),
                    args=["-c", server],
                    cwd=str(ROOT),
                ),
                {},
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(d):
                    received = assets(d)
                    result = compile_workflow(
                        "mcp:coherence",
                        workflow_documents([DESCRIPTOR], received)[0],
                        tools,
                    )
                    self.assertTrue(result["runnable"], result["diagnostics"])
                    return result, received

                async def allow():
                    pass

                async def run(argv, d=document):
                    compiled, received = compile(d)
                    return await execute(
                        compiled,
                        received,
                        {"argv": argv, "repository_root": str(root)},
                        remote,
                        allow,
                    )

                for argv, count in [
                    (["--self-test", "--json"], 7),
                    ([], 3),
                    (["--json"], 3),
                ]:
                    result = await run(argv)
                    self.assertEqual(result["status"], "accepted", result)
                    expected = (
                        source().common.self_test_payload(root)
                        if "--self-test" in argv
                        else source().common.build_inventory(root)
                    )
                    self.assertEqual(
                        result["outputs"],
                        {"result": {"payload": expected, "exit_code": 0}},
                    )
                    expected_calls = (
                        [
                            "parse",
                            "fixture",
                            "canonicalize",
                            "grounding",
                            "critics",
                            "finish",
                            "emit",
                        ]
                        if count == 7
                        else ["parse", "inventory", "emit"]
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_coherence_inventory_" + n for n in expected_calls],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                # Verify that both integration and API checks consume the
                # advertised repository context rather than process globals.
                native = source().common
                inventory = native.self_test_inventory()
                graph = native.canonicalize(inventory)
                owner = next(c for c in graph["concepts"] if c["owner_module"])
                foundation = root / owner["owner_module"]
                foundation.parent.mkdir(parents=True)
                foundation.write_text(" ".join(owner["api_terms"]))
                index = root / "MathformerPhysicsLib/Lean/Foundations.lean"
                index.parent.mkdir(parents=True)
                index.write_text("-- fixture foundation index")
                result = await run(["--self-test"])
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"]["result"]["payload"],
                    native.self_test_payload(root),
                )
                reports = native.self_test_critics(
                    inventory, graph, native.audit_grounding(graph), root
                )["reports"]
                self.assertFalse(
                    any(
                        f["kind"] == "foundation_owner_not_indexed"
                        for f in reports[1]["findings"]
                    )
                )
                self.assertEqual(reports[2]["finding_count"], 0)
                output = root / "output.json"
                result = await run(["--output", str(output)])
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    json.loads(output.read_text()),
                    result["outputs"]["result"]["payload"],
                )
                # Real I/O errors and parse failure stop execution, without retry.
                result = await run(["--invalid"])
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(result["calls"]), 1)
                self.assertIsNone(result["outputs"])
                blocker = root / "blocker"
                blocker.write_text("file")
                result = await run(["--output", str(blocker / "out.json")])
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(result["calls"]), 3)
                lib = root / "MathformerPhysicsLib"
                lib.mkdir(exist_ok=True)
                (lib / "MANIFEST.json").write_text("{")
                result = await run([])
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(result["calls"]), 2)
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 4
                result = await run(["--self-test"], bounded)
                self.assertEqual(result["status"], "failed")
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    4,
                )
                self.assertIn("budget", result["calls"][-1]["error"])
                # Assertion failure crosses the registered MCP boundary unchanged.
                fixture = (
                    await remote.call("mathformer_coherence_inventory_fixture", {})
                )["inventory"]
                graph = (
                    await remote.call(
                        "mathformer_coherence_inventory_canonicalize",
                        {"inventory": fixture},
                    )
                )["graph"]
                grounding = (
                    await remote.call(
                        "mathformer_coherence_inventory_grounding", {"graph": graph}
                    )
                )["grounding"]
                critics = (
                    await remote.call(
                        "mathformer_coherence_inventory_critics",
                        {
                            "inventory": fixture,
                            "graph": graph,
                            "grounding": grounding,
                            "repository_root": str(root),
                        },
                    )
                )["critics"]
                with self.assertRaises(Exception):
                    await remote.call(
                        "mathformer_coherence_inventory_finish",
                        {
                            "graph": {**graph, "concept_count": 0},
                            "grounding": grounding,
                            "critics": critics,
                        },
                    )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
