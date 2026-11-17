#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 -- bootstrap the host Lunar interpreter before imports
"""Temporary library fixtures through native steps, registered MCP, real PRISM.

There is no provider or external compiler boundary in this workflow. All Lean
files are deterministic text fixtures; no theorem prover or promotion is run.
The Lunar compiler uses its actual PRISM parser, checker, compiler and runtime.
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
from object_workbench_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_object_workbench_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/object-workbench.workflow.json"
PREFIX = "mathformer_object_workbench_"


def oracle(root):
    loader = SourceFileLoader(
        "workbench_oracle",
        str(ROOT / "tests/mcp/fixtures/object_workbench_original.py.txt"),
    )
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    # Restore the frozen entrypoint's repository context to the fixture mount.
    module.REPO_ROOT = root
    module.LIB_ROOTS = [
        root / "MathformerPhysicsLib/Lean",
        root / "MathformerPhysicsLib",
    ]
    module.FOUNDATIONS_ROOT = root / "MathformerPhysicsLib/Lean/Foundations"
    return module


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in document["provenance"]["sources"]
    ]


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="workbench-fixture-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        self.repository = self.directory / "repository"
        self.lean = self.repository / "MathformerPhysicsLib/Lean"
        self.lean.mkdir(parents=True)
        self.file("MathformerPhysicsLib/Lean/Foundations.lean", "CoMmUtAtOr index\n")
        self.file("MathformerPhysicsLib/Lean/Foundations/B.lean", "commutator B\n" * 5)
        self.file("MathformerPhysicsLib/Lean/Foundations/A.lean", "commutator A\n" * 4)
        self.file(
            "MathformerPhysicsLib/Lean/Ordinary.lean",
            "unrelated\nordinaryCue " + "x" * 260 + "\n",
        )
        self.file("MathformerPhysicsLib/Other.lean", "ordinaryCue outer\n")
        (self.lean / "00undecodable.lean").write_bytes(b"\xffordinaryCue")
        (self.lean / "Alias.lean").symlink_to(self.lean / "Foundations/A.lean")
        self.native, self.original = source(), oracle(self.repository)
        self.packet = {
            "packet_id": {"z": "déterministic", "a": 1},
            "objects": [
                None,
                7,
                [],
                "ignored",
                {"object_class": "commutator", "repair_surface": "law_grounding"},
                {"object_class": "ordinaryCue", "repair_surface": {"z": 2, "a": 1}},
                {
                    "object_class": "missing_object",
                    "required_mathformerphysicslib_surfaces": ["α surface"],
                },
            ],
        }

    def file(self, name, text):
        path = self.repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def packet_file(self, packet, name="packet.json"):
        path = self.directory / name
        path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
        return path

    def test_original_order_bounds_branches_and_cli(self):
        n, old = self.native, self.original
        files = list(n.iter_lean_files(repository_root=self.repository))
        self.assertEqual(files, list(old.iter_lean_files()))
        self.assertEqual(len(files), len({p.resolve() for p in files}))
        self.assertEqual(
            [p.name for p in files[:3]], ["Foundations.lean", "A.lean", "B.lean"]
        )
        hits = n.search_existing("commutator", repository_root=self.repository)
        self.assertEqual(hits, old.search_existing("commutator"))
        self.assertEqual(len(hits), 8)
        self.assertEqual(hits[-1]["line"], 3)
        self.assertTrue(hits[-1]["path"].endswith("Foundations/B.lean"))
        for limit in [0, 1, 7, 8, 10, 100]:
            self.assertEqual(
                n.search_existing("commutator", limit, repository_root=self.repository),
                old.search_existing("commutator", limit),
            )
        plan = n.build_plan(object_packet=self.packet, repository_root=self.repository)
        self.assertEqual(plan, old.build_plan(object_packet=self.packet))
        self.assertEqual(plan["item_count"], 3)
        self.assertEqual(
            [i["status"] for i in plan["items"]],
            ["mathformer_reused", "reuse_candidate", "candidate_required"],
        )
        self.assertEqual(
            [
                plan[k]
                for k in [
                    "reuse_count",
                    "reuse_candidate_count",
                    "candidate_required_count",
                ]
            ],
            [1, 1, 1],
        )
        self.assertEqual(
            [i["target_handoff"]["may_edit_target_theorem"] for i in plan["items"]],
            [True, False, False],
        )
        self.assertEqual(
            len(plan["items"][1]["existing_hits"]), 2
        )  # Exhaustion below eight.
        self.assertEqual(len(plan["items"][1]["existing_hits"][0]["evidence"]), 240)
        self.assertIn(
            "def missing_object_support_required : Prop := True",
            plan["items"][2]["candidate_lean_text"],
        )
        self.assertFalse((ROOT / plan["items"][2]["candidate_module_path"]).exists())
        # Empty input skips all item bodies. Native traversal has no object cap.
        for packet in [
            {},
            {"objects": [False, None, []]},
            {"objects": [{}]},
            {"objects": [{"object_class": "commutator"}]},
            {"objects": [{"object_class": "missing_object"}] * 65},
        ]:
            self.assertEqual(
                n.build_plan(object_packet=packet, repository_root=self.repository),
                old.build_plan(object_packet=packet),
            )
        # Compare both CLIs byte-for-byte, including file writes and print branches.
        path = self.packet_file(self.packet)
        for base in [
            [],
            ["--object-packet", str(path)],
            ["--self-test", "--object-packet", str(self.directory / "missing")],
        ]:
            for flags in [
                [],
                ["--json"],
                ["--output", str(self.directory / "nested/plan.json")],
                ["--output", str(self.directory / "nested/plan.json"), "--json"],
            ]:
                results = []
                for module in [old, n]:
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        code = module.main(
                            base + flags,
                            **(
                                {"repository_root": self.repository}
                                if module is n
                                else {}
                            ),
                        )
                    results.append(
                        (
                            code,
                            stream.getvalue(),
                            (
                                (self.directory / "nested/plan.json").read_text()
                                if "--output" in flags
                                else None
                            ),
                        )
                    )
                self.assertEqual(*results)
                self.assertEqual(results[0][0], 0)
        # Unknown arguments, malformed JSON and source type failures remain terminal.
        for packet in [
            {"objects": None},
            {
                "objects": [
                    {
                        "object_class": "absent",
                        "required_mathformerphysicslib_surfaces": [1],
                    }
                ]
            },
        ]:
            for module in [old, n]:
                with self.assertRaises(TypeError):
                    module.build_plan(
                        object_packet=packet,
                        **({"repository_root": self.repository} if module is n else {}),
                    )
        for module in [old, n]:
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                module.main(["--unknown"])
            self.assertEqual(error.exception.code, 2)

    def test_early_stop_and_read_failures(self):
        # A directory with a .lean suffix is a real read failure. Eight prior
        # matches stop before it; exhaustion searches reach it and must fail.
        (self.lean / "ZZ.lean").mkdir()
        for module in [self.original, self.native]:
            context = (
                {"repository_root": self.repository} if module is self.native else {}
            )
            self.assertEqual(len(module.search_existing("commutator", **context)), 8)
            with self.assertRaises(IsADirectoryError):
                module.search_existing("no_match", **context)

    def test_registered_tools_lunar_execution_and_failures(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_physics_lean_object_workbench_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document, json.loads((ROOT / AUTHORED).read_text()))
        from normalize_workflows_tools import source as normalization_source

        generated = next(
            row
            for row in normalization_source().inventory()
            if row["id"] == document["id"]
        )
        self.assertEqual(generated, document)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "object-workbench",
            StdioConfig(
                command=(
                    str(ROOT / ".venv/bin/python")
                    if (ROOT / ".venv/bin/python").exists()
                    else sys.executable
                ),
                args=["-c", server],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    assets = snapshot(doc)
                    workflow = workflow_documents([DESCRIPTOR], assets)[0]
                    return (
                        compile_workflow(
                            "mcp:object-workbench",
                            workflow,
                            tools if inventory is None else inventory,
                        ),
                        assets,
                    )

                workflow, assets = compile(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertEqual(workflow["runtime_status"], "ready")
                self.assertTrue(workflow["runtime_source"])
                self.assertTrue(workflow["prism_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def allow():
                    pass

                async def run(argv, doc=None):
                    w, a = compile(doc) if doc is not None else (workflow, assets)
                    self.assertTrue(w["runnable"], w["diagnostics"])
                    return await execute(
                        w,
                        a,
                        {"argv": argv, "repository_root": str(self.repository)},
                        remote,
                        allow,
                    )

                for packet in [
                    {},
                    {"objects": [None, 3]},
                    self.packet,
                    {"objects": [{"object_class": "commutator"}]},
                    {"objects": [{"object_class": "ordinaryCue"}]},
                    {"objects": [{"object_class": "missing"}] * 65},
                ]:
                    path = self.packet_file(packet)
                    expected = self.original.build_plan(object_packet=packet)
                    for flags in [
                        [],
                        ["--json"],
                        ["--output", str(self.directory / "runtime/plan.json")],
                        [
                            "--output",
                            str(self.directory / "runtime/plan.json"),
                            "--json",
                        ],
                    ]:
                        result = await run(["--object-packet", str(path), *flags])
                        self.assertEqual(result["status"], "accepted", result)
                        text = json.dumps(expected, ensure_ascii=False, indent=2)
                        stdout = (
                            text + "\n"
                            if "--json" in flags or "--output" not in flags
                            else ""
                        )
                        self.assertEqual(
                            result["outputs"],
                            {
                                "plan": expected,
                                "json_text": text,
                                "stdout_text": stdout,
                                "exit_code": 0,
                            },
                        )
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            [
                                PREFIX + n
                                for n in [
                                    "parse_options",
                                    "load_packet",
                                    "build_plan",
                                    "emit_plan",
                                ]
                            ],
                        )
                        if "--output" in flags:
                            self.assertEqual(
                                (self.directory / "runtime/plan.json").read_text(),
                                text + "\n",
                            )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                for argv in [
                    [],
                    [
                        "--self-test",
                        "--object-packet",
                        str(self.directory / "nonexistent"),
                    ],
                ]:
                    result = await run(argv)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"]["plan"],
                        (
                            self.original.build_plan(
                                object_packet=self.native.fixture_packet()
                            )
                            if argv
                            else self.original.build_plan(object_packet={})
                        ),
                    )
                    names = (
                        [
                            "parse_options",
                            "fixture_packet",
                            "build_plan",
                            "assert_fixture",
                            "emit_plan",
                        ]
                        if argv
                        else ["parse_options", "load_packet", "build_plan", "emit_plan"]
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [PREFIX + n for n in names],
                    )
                # Every advertised interface is called, including failing assertion.
                for name in [
                    "parse_options",
                    "fixture_packet",
                    "load_packet",
                    "build_plan",
                    "assert_fixture",
                    "emit_plan",
                ]:
                    self.assertIn(PREFIX + name, {t["name"] for t in tools})
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "assert_fixture",
                        {"plan": {"item_count": 0}, "native_json_text": "{}"},
                    )
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "build_plan",
                        {
                            "packet": {},
                            "native_packet_text": '{"objects":[{}]}',
                            "repository_root": str(self.repository),
                        },
                    )
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "emit_plan",
                        {
                            "options": {"output": None, "json": True},
                            "plan": {},
                            "native_json_text": '{"item_count":1}',
                        },
                    )
                # A compiler input fixture routes an empty packet through the
                # actual self-test assertion. No source step is replaced.
                asserting = deepcopy(document)
                args = asserting["flow"]["steps"][1]["cases"][0]["body"]["steps"][1][
                    "arguments"
                ]
                args["packet"] = {"literal": {}}
                args["native_packet_text"] = {"literal": "{}"}
                result = await run(["--self-test"], asserting)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), 4)
                self.assertEqual(result["calls"][-1]["tool"], PREFIX + "assert_fixture")
                bad_json = self.directory / "bad.json"
                bad_json.write_text("{bad")
                undecodable = self.directory / "bad-utf8.json"
                undecodable.write_bytes(b"\xff")
                for argv, count in [
                    (["--unknown"], 1),
                    (["--object-packet", str(bad_json)], 2),
                    (["--object-packet", str(undecodable)], 2),
                    (["--object-packet", str(self.directory / "missing")], 2),
                    (["--object-packet", str(self.packet_file({"objects": None}))], 3),
                    (["--output", str(self.directory)], 4),
                ]:
                    result = await run(argv)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), count)
                (self.lean / "ZZ.lean").mkdir()
                path = self.packet_file({"objects": [{"object_class": "no_match"}]})
                result = await run(["--object-packet", str(path)])
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 3)
                (self.lean / "ZZ.lean").rmdir()
                # Host budget fixtures exercise real runtime exhaustion without
                # adding bounds or retry behavior to the native object loop.
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 3
                result = await run([], budget)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    3,
                )
                self.assertIn("budget", str(result).lower())
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                w, a = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        w,
                        a,
                        {"argv": [], "repository_root": str(self.repository)},
                        remote,
                        pending,
                    )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
