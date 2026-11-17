#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Frozen-source parity and real MCP/Lunar/PRISM map compilation/execution.

No native source step is replaced. JSON files are deterministic case/review
fixtures. There is no model or external compiler in this map; fixture transport
denies those boundaries. The real PRISM parser, checker, compiler and runtime
are used for every workflow invocation.
"""

from tempfile import gettempdir

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
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
from importlib.machinery import SourceFileLoader
import importlib.util
import io
import json
import tempfile
import unittest
import yaml

from sympy_expansion_tools import source, SOURCE
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_sympy_repair_expansion_map_0000_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/sympy-expansion-map.workflow.json"
PREFIX = "mathformer_sympy_expansion_"
MAP_OUTPUT = "expansion"
EMISSION_OUTPUT = "result"
PARSE_NAME = "parse_cli"
BAD_PLAN_CALLS = 2
CASE_ID = "formalphysics_0000"
MISSING_NAME = "plan_case"


def oracle():
    source()  # Restore the native optional logger import context before relocation.
    loader = SourceFileLoader(
        "sympy_expansion_original",
        str(ROOT / "tests/mcp/fixtures/sympy_expansion_original.py.txt"),
    )
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    module.REPO_ROOT = ROOT
    module.PLANNER = source().PLANNER
    return module


def finding(surface, severity="high", code=None):
    return {
        "code": code or surface,
        "severity": severity,
        "repair_surface": surface,
        "message": "Δ量",
        "evidence": {"z": "last", "a": "first"},
    }


def scenarios():
    return [
        (
            {"case_id": "fixture", "next_action": "complete", "findings": []},
            [],
            "complete",
        ),
        (
            {"case_id": "fixture", "next_action": "blocked", "findings": []},
            [],
            "blocked",
        ),
        (
            {"case_id": "fixture", "next_action": "recurse", "findings": []},
            [],
            "needs_expansion",
        ),
        (
            {
                "case_id": "fixture",
                "next_action": "complete",
                "findings": [
                    None,
                    finding("unit", "low"),
                    finding("quantity", "critical"),
                ],
            },
            [
                {
                    "style": "review",
                    "findings": [
                        finding("unit", "medium"),
                        finding("source_anchor"),
                        finding("source_anchor"),
                    ],
                }
            ],
            "needs_expansion",
        ),
        (
            {"case_id": "fixture", "next_action": "complete"},
            [
                {
                    "status": "fail",
                    "findings": [],
                    "repair_surfaces": ["unit", "dimension", "unit", None],
                },
                {"diagnostics": [None, finding("zz_custom"), finding("aa_custom")]},
                {
                    "status": "blocked",
                    "findings": [finding("frame", "low")],
                    "repair_surfaces": ["regime"],
                },
            ],
            "needs_expansion",
        ),
        (
            {"next_action": "complete"},
            [
                {
                    "status": "fail",
                    "repair_surfaces": ["unit"],
                    "findings": [finding("unit", "medium")],
                }
            ],
            "complete",
        ),
        # Input exhaustion, without a fabricated count cap or repair iteration.
        (
            {
                "case_id": "large",
                "next_action": "complete",
                "findings": [finding("dimension", code=str(i)) for i in range(137)],
            },
            [],
            "needs_expansion",
        ),
    ]


class ExpansionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sympy-expansion-")
        self.directory = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def write(self, name, payload):
        path = self.directory / name
        path.write_text(json.dumps(payload, ensure_ascii=False))
        return str(path)

    def test_native_original_equivalence_and_emission(self):
        original, native = oracle(), source()
        frozen = ROOT / "tests/mcp/fixtures/sympy_expansion_original.py.txt"
        self.assertEqual(
            hashlib.sha256(frozen.read_bytes()).hexdigest(),
            "4b267187c93e387b2065a354720fb8c06a8e99e316f6065034f648013db528ce",
        )
        for index, (plan, reviews, status) in enumerate(scenarios()):
            expected = original.build_map(plan, reviews)
            self.assertEqual(native.build_map(plan, reviews), expected)
            self.assertEqual(expected["status"], status)
            self.assertEqual(
                expected["outstanding_node_count"], len(expected["next_frontier"])
            )
            self.assertEqual(
                [x["order"] for x in expected["next_frontier"]],
                list(range(1, expected["outstanding_node_count"] + 1)),
            )
            argv = ["--goal-plan", self.write(f"plan{index}.json", plan)]
            for j, review in enumerate(reviews):
                argv += ["--review", self.write(f"review{index}-{j}.json", review)]
            streams = []
            for module in (original, native):
                stream = io.StringIO()
                with redirect_stdout(stream):
                    self.assertEqual(module.main(argv), 0)
                streams.append(stream.getvalue())
            self.assertEqual(streams[0], streams[1])
        # Native self-test ignores file inputs and retains its first probe.
        for module in (original, native):
            stream = io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(
                    module.main(
                        [
                            "--self-test",
                            "--goal-plan",
                            str(
                                Path(gettempdir()) / "mathformer-test-fixtures/missing"
                            ),
                            "--review",
                            str(
                                Path(gettempdir()) / "mathformer-test-fixtures/missing"
                            ),
                        ]
                    ),
                    0,
                )
            self.assertEqual(json.loads(stream.getvalue()), native.self_test_map())
        # Real output followed by a real consumer reasoning log.
        expansion = native.build_map(
            {"case_id": "fixture", "next_action": "blocked"}, []
        )
        for name, module in [("old", original), ("new", native)]:
            output = self.directory / name / "map.json"
            log = self.directory / name / "map.jsonl"
            argv = [
                "--goal-plan",
                self.write(
                    "blocked.json", {"case_id": "fixture", "next_action": "blocked"}
                ),
                "--output",
                str(output),
                "--reasoning-log",
                str(log),
            ]
            self.assertEqual(module.main(argv), 0)
            self.assertEqual(
                output.read_text(),
                json.dumps(expansion, ensure_ascii=False, indent=2) + "\n",
            )
            event = json.loads(log.read_text())
            self.assertIn("physics_sympy_repair_expansion_map_complete", str(event))
            self.assertIn(expansion["iteration_signature"], str(event))
        for module in (original, native):
            with self.assertRaisesRegex(SystemExit, "provide --goal-plan or --case"):
                module.main([])
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                module.main(["--unknown"])
            with self.assertRaises(FileNotFoundError):
                module.main(["--goal-plan", str(self.directory / "absent")])

    def test_registered_mcp_lunar_prism(self):
        asyncio.run(self.runtime())

    async def runtime(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document, json.loads((ROOT / AUTHORED).read_text()))
        from normalize_workflows_tools import source as normalization_source

        authored = next(
            row
            for row in normalization_source().inventory()
            if row["id"] == document["id"]
        )
        self.assertEqual(authored, document)
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 360, "max_operation_calls": 5},
        )
        self.assertIn(
            SOURCE, [row["path"] for row in document["provenance"]["sources"]]
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        config = StdioConfig(
            command=sys.executable,
            args=[str(ROOT / "tests/mcp/fixtures/sympy_expansion_server.py")],
            cwd=str(self.directory),
        )
        failure = None
        async with manager.open("sympy-expansion-fixture", config, {}) as remote:
            try:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]
                parsed = await remote.call(PREFIX + PARSE_NAME, {"extra_args": []})
                self.assertEqual(parsed["options"]["case"], CASE_ID)
                self.assertTrue(parsed["options"]["json"])
                overridden = await remote.call(
                    PREFIX + PARSE_NAME, {"extra_args": ["--case", "override"]}
                )
                self.assertEqual(overridden["options"]["case"], "override")

                def compile(doc, inventory=None):
                    def asset(path, text):
                        return {
                            "path": path,
                            "content": text,
                            "encoding": "text",
                            "sha256": hashlib.sha256(text.encode()).hexdigest(),
                        }

                    assets = [asset(DESCRIPTOR, json.dumps(doc))] + [
                        asset(row["path"], (ROOT / row["path"]).read_text())
                        for row in doc["provenance"]["sources"]
                    ]
                    selected = workflow_documents([DESCRIPTOR], assets)[0]
                    workflow = compile_workflow(
                        "mcp:sympy-expansion-fixture",
                        selected,
                        tools if inventory is None else inventory,
                    )
                    return workflow, assets

                compiled, assets = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                missing, _ = compile(document, [])
                self.assertFalse(missing["runnable"])
                incompatible = deepcopy(tools)
                for tool in incompatible:
                    if tool["name"] == PREFIX + PARSE_NAME:
                        tool["inputSchema"]["properties"]["extra_args"] = {
                            "type": "integer"
                        }
                wrong_interface, wrong_assets = compile(document, incompatible)

                async def authorize():
                    pass

                # The runtime enforces the advertised input schema before transport.
                rejected = await execute(
                    wrong_interface, wrong_assets, {"extra_args": []}, remote, authorize
                )
                self.assertEqual(rejected["status"], "failed", rejected)
                self.assertIsNone(rejected["outputs"])
                self.assertFalse(
                    any(c.get("transport_call_performed") for c in rejected["calls"])
                )

                async def run(argv, doc=None):
                    workflow, received = compile(doc) if doc else (compiled, assets)
                    return await execute(
                        workflow, received, {"extra_args": argv}, remote, authorize
                    )

                for index, (plan, reviews, status) in enumerate(scenarios()):
                    argv = ["--goal-plan", self.write(f"p{index}.json", plan)]
                    for j, review in enumerate(reviews):
                        argv += ["--review", self.write(f"r{index}-{j}.json", review)]
                    result = await run(argv)
                    self.assertEqual(result["status"], "accepted", result)
                    expected = source().build_map(plan, reviews)
                    self.assertEqual(result["outputs"][MAP_OUTPUT], expected)
                    self.assertEqual(
                        result["outputs"][EMISSION_OUTPUT],
                        {
                            "serialized_json": json.dumps(
                                expected, ensure_ascii=False, indent=2
                            ),
                            "exit_code": 0,
                        },
                    )
                    self.assertEqual(
                        [call["tool"] for call in result["calls"]],
                        [
                            PREFIX + name
                            for name in [
                                PARSE_NAME,
                                "load_plan",
                                "load_reviews",
                                "build_map",
                                "emit",
                            ]
                        ],
                    )
                    self.assertTrue(result["replay_artifacts"])
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                # A repeated signature is not stopped by this map action.
                # Controller histories and iteration limits belong to its caller.
                repeated = await run(argv)
                self.assertEqual(repeated["status"], "accepted", repeated)
                self.assertEqual(repeated["outputs"], result["outputs"])
                self.assertEqual(repeated["outputs"][MAP_OUTPUT]["node_count"], 137)
                # Explicit priority, synthesis/dedup per report, and satisfied nodes.
                mixed = source().build_map(*scenarios()[3][:2])
                self.assertEqual(
                    [x["repair_surface"] for x in mixed["outstanding_nodes"]],
                    ["source_anchor", "source_anchor", "source_anchor", "quantity"],
                )
                self.assertEqual(mixed["node_count"], 5)
                self.assertEqual(mixed["nodes"][1]["status"], "satisfied")
                result = await run(
                    [
                        "--self-test",
                        "--review",
                        str(Path(gettempdir()) / "mathformer-test-fixtures/missing"),
                        "--goal-plan",
                        str(Path(gettempdir()) / "mathformer-test-fixtures/missing"),
                    ]
                )
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"][MAP_OUTPUT], source().self_test_map()
                )
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [PREFIX + n for n in (PARSE_NAME, "self_test", "emit")],
                )
                # Actual planner CLI rejection, not a replaced planner implementation.
                result = await run(["--case", "invalid-fixture-case"])
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"][MAP_OUTPUT]["status"], "blocked")
                self.assertEqual(
                    result["outputs"][MAP_OUTPUT]["outstanding_nodes"][0]["blockers"],
                    ["goal_planner_failed"],
                )
                self.assertEqual(result["outputs"][EMISSION_OUTPUT]["exit_code"], 0)
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [
                        PREFIX + n
                        for n in (
                            PARSE_NAME,
                            "plan_case",
                            "load_reviews",
                            "build_map",
                            "emit",
                        )
                    ],
                )
                # Output/logging are source-owned and occur only after map construction.
                output, log = (
                    self.directory / "nested/map.json",
                    self.directory / "events.jsonl",
                )
                result = await run(
                    [
                        "--self-test",
                        "--output",
                        str(output),
                        "--reasoning-log",
                        str(log),
                    ]
                )
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    output.read_text(),
                    result["outputs"][EMISSION_OUTPUT]["serialized_json"] + "\n",
                )
                self.assertIn(
                    result["outputs"][MAP_OUTPUT]["iteration_signature"],
                    log.read_text(),
                )
                # File/parse/shape failures stop downstream calls; there is no retry.
                bad_json = self.directory / "invalid.json"
                bad_json.write_text("{")
                valid = self.write("complete.json", {"next_action": "complete"})
                for argv, count in [
                    (["--unknown"], 1),
                    (["--case", ""], 2),
                    (
                        [
                            "--goal-plan",
                            str(
                                Path(gettempdir()) / "mathformer-test-fixtures/missing"
                            ),
                        ],
                        2,
                    ),
                    (["--goal-plan", str(bad_json)], 2),
                    (
                        [
                            "--goal-plan",
                            valid,
                            "--review",
                            str(
                                Path(gettempdir()) / "mathformer-test-fixtures/missing"
                            ),
                        ],
                        3,
                    ),
                    (
                        [
                            "--goal-plan",
                            self.write("bad-shape.json", {"findings": None}),
                        ],
                        BAD_PLAN_CALLS,
                    ),
                    (
                        [
                            "--goal-plan",
                            valid,
                            "--review",
                            self.write("bad-review.json", {"findings": 1}),
                        ],
                        4,
                    ),
                ]:
                    failed = await run(argv)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual(len(failed["calls"]), count, failed)
                    self.assertEqual(failed["calls"][-1]["status"], "rejected")
                    if argv == ["--case", ""]:
                        self.assertEqual(
                            failed["calls"][-1]["tool"], PREFIX + MISSING_NAME
                        )
                # Emission failure propagates after construction, no success output.
                blocker = self.directory / "file"
                blocker.write_text("file")
                failed = await run(
                    ["--self-test", "--output", str(blocker / "map.json")]
                )
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(len(failed["calls"]), 3)
                # Relative argv paths retain the native hub repository cwd,
                # independent of the MCP process's working directory.
                relative_output = self.directory / "relative.json"
                relative_log = self.directory / "relative.jsonl"
                result = await run(
                    [
                        "--goal-plan",
                        os.path.relpath(valid, ROOT),
                        "--review",
                        os.path.relpath(self.write("relative-review.json", {}), ROOT),
                        "--output",
                        os.path.relpath(relative_output, ROOT),
                        "--reasoning-log",
                        os.path.relpath(relative_log, ROOT),
                    ]
                )
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    json.loads(relative_output.read_text()),
                    result["outputs"][MAP_OUTPUT],
                )
                self.assertTrue(relative_log.exists())
                # Logger errors follow the output write, as in the native CLI.
                written = self.directory / "before-log-failure.json"
                failed = await run(
                    [
                        "--self-test",
                        "--output",
                        str(written),
                        "--reasoning-log",
                        str(self.directory),
                    ]
                )
                self.assertEqual(failed["status"], "failed", failed)
                self.assertIsNone(failed["outputs"])
                self.assertEqual(
                    json.loads(written.read_text()), source().self_test_map()
                )
                # Mandatory equality check prevents text/typed payload divergence.
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "build_map",
                        {
                            "plan": {},
                            "plan_json": '{"next_action":"complete"}',
                            "reviews": [],
                            "reviews_json": "[]",
                        },
                    )
                never = self.directory / "never.json"
                for budget in range(1, 5):
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = budget
                    failed = await run(
                        ["--goal-plan", valid, "--output", str(never)], bounded
                    )
                    self.assertEqual(failed["status"], "failed")
                    self.assertIn("budget", str(failed).lower())
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in failed["calls"]
                        ),
                        budget,
                    )
                    self.assertFalse(never.exists())
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                workflow, received = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        workflow,
                        received,
                        {"extra_args": ["--self-test"]},
                        remote,
                        pending,
                    )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


def main():
    result = unittest.main(module=__name__, verbosity=2, exit=False).result
    return 0 if result.wasSuccessful() and result.testsRun and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
