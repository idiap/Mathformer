#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Navigation source, production MCP bindings, and actual Lunar/PRISM execution.

Only the external version subprocess boundary is substituted. Ontology, index,
Lean source and report fixtures are real files. No model/provider is involved.
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
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml
from mathlib_navigation_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathlib_navigation_state_workflow/workflow.yaml"


def external_version(command, **kwargs):
    # The native index builder probes Lean/Git versions; never launch either.
    assert command[0] in ("lean", "git"), command
    return SimpleNamespace(stdout="fixture version\n", stderr="", returncode=0)


def fixture_server():
    from mcp_server import mcp

    source()
    sys.modules["mathlib_index_common"].subprocess = SimpleNamespace(
        run=external_version, PIPE=-1, TimeoutExpired=TimeoutError
    )
    mcp.run(transport="stdio")


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k != "generated_at_utc"}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def snapshot(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in document["provenance"]["sources"]
    ]


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="navigation-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.index = self.base / "index.json"
        self.profile = self.base / "profile.json"
        self.root = self.base / "Mathlib"
        self.root.mkdir()
        self.out = self.base / "reports"
        self.context = {
            "default_index": str(self.index),
            "output_directory": str(self.out),
            "mathlib_root": str(self.root),
            "profile_path": str(self.profile),
        }
        modules = [f"Mathlib.Fixture{i}" for i in range(10)]

        def concept(id, terms, **kwargs):
            return {
                "concept_id": id,
                "surface_terms": terms,
                "preferred_modules": modules,
                "lean_objects": ["fixture"],
                **kwargs,
            }

        self.concepts = [
            concept("topology.compact_set", ["compact set"]),
            concept(
                "set.finite_intersection_family",
                ["finite subfamily", "finite intersection property"],
            ),
            concept("analysis.convex_set", ["convex set", "convex subset"]),
            concept("shared.a", ["sharedterm"]),
            concept("shared.b", ["sharedterm"]),
            concept(
                "negative",
                ["badterm"],
                negative_context_clues=["badterm", "absent", "false"],
            ),
            concept("missing", ["missingterm"], preferred_modules=[], lean_objects=[]),
        ]
        self.profile.write_text(json.dumps({"concepts": self.concepts}))
        self.rows = [
            {
                "qualified_name": f"Mathlib.Fixture0.decl{i:02}",
                "short_name": f"decl{i:02}",
                "module": modules[0],
                "kind": "theorem",
                "source_ref": f"Fixture0.lean:{i+1}",
                "declaration_tokens": ["fixture"],
                "namespace_tokens": [],
                "signature": "fixture",
                "import_cost": 0,
                "lean_check_status": "checked",
                "theorem_shape": {"conclusion_head": "fixture"},
            }
            for i in range(12)
        ]
        self.index.write_text(
            json.dumps(
                {
                    "declarations": self.rows,
                    "declaration_graph": {
                        r["qualified_name"]: [f"neighbor{i}" for i in range(12)]
                        for r in self.rows
                    },
                }
            )
        )

    def test_source_branches_bounds_and_original_entrypoint(self):
        native = source()
        spec = importlib.util.spec_from_loader(
            "navigation_oracle",
            SourceFileLoader(
                "navigation_oracle",
                str(ROOT / "tests/mcp/fixtures/mathlib_navigation_original.py.txt"),
            ),
        )
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        for key in (
            "OUTPUT_PATH",
            "GAP_LEDGER_PATH",
            "MONOTONIC_PATH",
            "SELF_TEST_PATH",
        ):
            setattr(original, key, self.out / getattr(native, key).name)
        original.plan_navigation.__kwdefaults__["index_path"] = self.index
        # Set the original annotator's input default, keeping its full algorithm.
        with patch.dict(
            original.annotate_text.__kwdefaults__, {"profile_path": self.profile}
        ):
            expected = original.self_test()
            observed = native.self_test(context=self.context)
            self.assertEqual(clean(expected), clean(observed))
            self.assertTrue(observed["ok"])
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    original.main(["--self-test", "--monotonic-check", "--json"]), 0
                )
            self.assertEqual(clean(json.loads(output.getvalue())), clean(observed))
            # The normal CLI continues using explicit --index; path context is
            # only a new optional embedding interface, not a CLI behavior change.
            with (
                patch.object(native, "OUTPUT_PATH", self.out / "navigation_state.json"),
                patch.object(native, "GAP_LEDGER_PATH", self.out / "gap_ledger.json"),
                patch.object(
                    native,
                    "MONOTONIC_PATH",
                    self.out / "monotonic_refinement_report.json",
                ),
                patch.dict(
                    native.plan_navigation.__kwdefaults__, {"index_path": self.index}
                ),
            ):
                for argv in (
                    ["--text", "compact set", "--index", str(self.index), "--json"],
                    ["--monotonic-check"],
                    ["--text", "unmapped", "--index", str(self.index)],
                ):
                    streams = [io.StringIO(), io.StringIO()]
                    with redirect_stdout(streams[0]):
                        a = original.main(argv)
                    with redirect_stdout(streams[1]):
                        b = native.main(argv)
                    self.assertEqual(a, b)
                    if "--json" in argv:
                        self.assertEqual(
                            clean(json.loads(streams[0].getvalue())),
                            clean(json.loads(streams[1].getvalue())),
                        )
                    else:
                        self.assertEqual(streams[0].getvalue(), streams[1].getvalue())
            with self.assertRaisesRegex(SystemExit, "provide --text"):
                native.main([])
        report = native.plan_navigation(
            "compact set sharedterm badterm absent false missingterm compact set",
            index_path=self.index,
            context=self.context,
        )
        self.assertEqual(
            [s["allowed_next_operation"] for s in report["states"]],
            [
                "verify_candidate",
                "query_declarations",
                "mark_gap",
                "mark_gap",
                "verify_candidate",
            ],
        )
        self.assertEqual(len(report["gap_ledger"]), 2)
        for state in (report["states"][0], report["states"][-1]):
            self.assertEqual(len(state["candidate_declarations"]), 8)
            self.assertEqual(
                [r["qualified_name"] for r in state["candidate_declarations"]],
                [r["qualified_name"] for r in self.rows[:8]],
            )
            self.assertTrue(
                all(
                    len(r["neighborhood"]) == 8 for r in state["candidate_declarations"]
                )
            )
            self.assertEqual(
                state["budget"],
                {
                    "breadth_remaining": 0,
                    "depth_remaining": 4,
                    "declaration_checks_remaining": 0,
                    "fallback_searches_remaining": 2,
                },
            )
            self.assertEqual(state["stop_reason"], "candidate_ready")
        # No budget-driven stop; the last annotation was still appended.
        self.index.write_text('{"declarations":[]}')
        report = native.plan_navigation(
            "sharedterm compact set", index_path=self.index, context=self.context
        )
        self.assertEqual(len(report["states"]), 2)
        self.assertEqual(len(report["gap_ledger"]), 2)
        self.assertEqual(
            report["states"][0]["allowed_next_operation"], "query_declarations"
        )
        self.assertTrue(
            all(
                s["stop_reason"] == "gap_or_needs_broader_index"
                for s in report["states"]
            )
        )
        report = native.plan_navigation("", index_path=self.index, context=self.context)
        self.assertEqual(report["states"], [])
        self.assertEqual(report["gap_ledger"][0]["source_span"], {"start": 0, "end": 0})
        self.assertEqual(
            native.candidate_declarations({"normalized_candidates": []}, {}), []
        )
        forbidden = deepcopy(self.rows)
        forbidden[0]["qualified_name"] = "Mathlib.Fixture0.Operator00"
        self.index.write_text(json.dumps({"declarations": forbidden}))
        mono = native.monotonic_check(context=self.context)
        self.assertEqual([row["ok"] for row in mono["results"]], [False, True, True])
        self.assertEqual(
            mono["results"][0]["top_declarations"][0], "Mathlib.Fixture0.Operator00"
        )
        self.assertEqual(
            json.loads((self.out / "navigation_state.json").read_text())["source_text"],
            native.BASELINES[-1]["text"],
        )

    def test_index_build_bound_and_failure(self):
        native = source()
        # Actual parser reads first 220 sorted Lean fixture files. Only the
        # external version process is replaced, including in the MCP server.
        for i in range(222):
            (self.root / f"File{i:03}.lean").write_text(
                f"theorem fixture{i} : True := by trivial\n"
            )
        built = self.base / "built.json"
        with patch.object(
            sys.modules["mathlib_index_common"].subprocess, "run", external_version
        ):
            report = native.plan_navigation(
                "compact set", index_path=built, context=self.context
            )
        self.assertEqual(len(json.loads(built.read_text())["modules"]), 220)
        self.assertEqual(len(json.loads(built.read_text())["declarations"]), 220)
        self.assertTrue(report["ok"])
        built.write_text("{")
        with self.assertRaises(json.JSONDecodeError):
            native.plan_navigation(
                "compact set", index_path=built, context=self.context
            )

    def test_registered_mcp_real_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_mathlib_navigation_state_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import runpy;runpy.run_path("tests/mcp/run_mathlib_navigation_workflow_tests.py",run_name="fixture_server")["fixture_server"]()'
        failure = None
        async with manager.open(
            "navigation",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {"LUNAR_PLATFORM_ROOT": str(LUNAR)},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    assets = snapshot(doc)
                    selected = workflow_documents([DESCRIPTOR], assets)[0]
                    return (
                        compile_workflow(
                            "mcp:navigation",
                            selected,
                            tools if inventory is None else inventory,
                        ),
                        assets,
                    )

                workflow, assets = compile(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(args=None, doc=None, context=None):
                    selected, received = compile(doc) if doc else (workflow, assets)
                    return await execute(
                        selected,
                        received,
                        {
                            "args": args
                            or {
                                "self_test": True,
                                "monotonic_check": True,
                                "text": "ignored",
                                "index": "ignored",
                                "json": True,
                            },
                            "context": context or self.context,
                        },
                        remote,
                        authorize,
                    )

                result = await run()
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    clean(result["outputs"]["payload"]),
                    clean(source().self_test(context=self.context)),
                )
                self.assertTrue(result["outputs"]["payload"]["ok"])
                self.assertEqual(result["outputs"]["exit_code"], 0)
                self.assertEqual(
                    json.loads(result["outputs"]["stdout"]),
                    result["outputs"]["payload"],
                )
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [
                        "mathformer_navigation_plan",
                        "mathformer_navigation_plan",
                        "mathformer_navigation_monotonic",
                        "mathformer_navigation_finish_self_test",
                        "mathformer_navigation_emit",
                    ],
                )
                self.assertTrue(result["replay_artifacts"])
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertEqual(
                    json.loads((self.out / "navigation_state.json").read_text())[
                        "source_text"
                    ],
                    source().BASELINES[-1]["text"],
                )
                self.assertEqual(
                    len(
                        json.loads(
                            (self.out / "monotonic_refinement_report.json").read_text()
                        )["results"]
                    ),
                    3,
                )

                def args(text="", mono=False):
                    return {
                        "self_test": False,
                        "monotonic_check": mono,
                        "text": text,
                        "index": str(self.index),
                        "json": False,
                    }

                result = await run(
                    args(
                        "compact set sharedterm badterm absent false missingterm compact set"
                    )
                )
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    [
                        s["allowed_next_operation"]
                        for s in result["outputs"]["payload"]["states"]
                    ],
                    [
                        "verify_candidate",
                        "query_declarations",
                        "mark_gap",
                        "mark_gap",
                        "verify_candidate",
                    ],
                )
                self.assertEqual(
                    result["outputs"]["stdout"], "PASS mathlib navigation state\n"
                )
                normal = (
                    await remote.call(
                        "mathformer_navigation_plan",
                        {
                            "text": "compact set",
                            "index": str(self.index),
                            "context": self.context,
                        },
                    )
                )["payload"]
                gap = (
                    await remote.call(
                        "mathformer_navigation_plan",
                        {
                            "text": "unmapped",
                            "index": str(self.index),
                            "context": self.context,
                        },
                    )
                )["payload"]
                for field in ("operation_catalog", "allowed_operations_seen"):
                    altered = deepcopy(normal)
                    altered[field] = ["unknown"]
                    aggregate = await remote.call(
                        "mathformer_navigation_finish_self_test",
                        {
                            "normal": altered,
                            "gap": gap,
                            "monotonic": {"ok": True},
                            "context": self.context,
                        },
                    )
                    self.assertFalse(aggregate["payload"]["ok"])
                    self.assertEqual(
                        json.loads(
                            (self.out / "navigation_state_self_test.json").read_text()
                        ),
                        aggregate["payload"],
                    )
                # Fail the first baseline via real profile data; later baselines still
                # execute, and ordinary ok=false reaches emit with exit code one.
                changed = deepcopy(self.concepts)
                changed[0]["concept_id"] = "wrong"
                self.profile.write_text(json.dumps({"concepts": changed}))
                result = await run(args(mono=True))
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    [r["ok"] for r in result["outputs"]["payload"]["results"]],
                    [False, True, True],
                )
                self.assertEqual(result["outputs"]["exit_code"], 1)
                self.assertEqual(
                    result["outputs"]["stdout"], "FAIL mathlib navigation state\n"
                )
                result = await run()
                self.assertFalse(result["outputs"]["payload"]["ok"])
                self.assertEqual(len(result["calls"]), 5)
                # Missing text terminates before plan/emit and never retries.
                result = await run(args())
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), 1)
                self.assertEqual(result["calls"][0]["status"], "rejected")
                # Real malformed index raises at the first plan in self-test.
                self.index.write_text("{")
                result = await run()
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 1)
                # Real empty source tree builds an empty index and exits by finite
                # exhaustion. No external prover process can run in fixture_server.
                self.index.unlink()
                result = await run(args("unmapped"))
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"]["payload"]["states"], [])
                self.assertEqual(len(result["outputs"]["payload"]["gap_ledger"]), 1)
                self.assertEqual(json.loads(self.index.read_text())["declarations"], [])
                # Runtime enforces graph call bounds independently of navigation's
                # recorded metadata. The source baseline helper is still one call.
                limited = deepcopy(document)
                limited["policy"]["limits"]["max_operation_calls"] = 2
                result = await run(doc=limited)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    2,
                )
                self.assertIn("budget", str(result).lower())
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
