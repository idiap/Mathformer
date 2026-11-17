#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native Dirac steps, registered MCP bindings, and Lunar PRISM runtime tests.

Only Lake is substituted. JSON helpers run in real Python subprocesses over
copied source/library inputs; fixture reports for branch unit scenarios are
explicit inputs to the actual native downstream tools, never step replacements.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
PYTHON = LUNAR / ".venv/bin/python"
if PYTHON.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(PYTHON), [str(PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
import yaml
from dirac_recursive_tools import SOURCE, source, register_dirac_recursive_tools
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_formalize_physics_lean_dirac_recursive_workflow/workflow.yaml"
FIXTURES = ROOT / "tests/mcp/fixtures"
PREFIX = "mathformer_dirac_"


def assets(doc):
    def asset(path, content):
        return {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(p, (ROOT / p).read_text())
        for p in dict.fromkeys(r["path"] for r in doc["provenance"]["sources"])
    ]


def fixture_root(root, doc, mode="pass"):
    root.mkdir()
    paths = [SOURCE] + [
        r["path"]
        for r in doc["provenance"]["sources"]
        if r["path"].startswith(
            (
                "skills/physics-",
                "skills/mathformerphysicslib/",
                "skills/autoformalization/",
            )
        )
        and r["path"].endswith(".py")
    ]
    for path in paths:
        dest = root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, dest)
    # Preserve both the source's legacy library path and the hub required path.
    for base in ("MathformerPhysicsLib", "libraries/MathformerPhysicsLib"):
        shutil.copytree(
            ROOT / "libraries/MathformerPhysicsLib/Lean/Foundations",
            root / base / "Lean/Foundations",
        )
        shutil.copyfile(
            ROOT / "libraries/MathformerPhysicsLib/Lean/Foundations.lean",
            root / base / "Lean/Foundations.lean",
        )
    dataset = root / "data/benchmarks/formal_science/FormalPhysics.json"
    dataset.parent.mkdir(parents=True)
    dataset.write_text(
        json.dumps(
            [
                {
                    "field": "Quantum Mechanics",
                    "question": f"Derive the Dirac quantum state identity for case {i}.",
                    "answer": "Use the normalized state, operator identities and the Born rule.",
                }
                for i in range(75)
            ]
        )
    )
    (root / "compiler-fixture.json").write_text(json.dumps({"mode": mode}))
    return root


def context(root, allow=True):
    return {"repository_root": str(root), "allow_mutating": allow}


def files(root):
    paths = list((root / "artifacts").rglob("*")) + list(
        (root / "MathformerPhysicsLib/Lean").glob("formalphysics_*/*")
    )
    if (root / "native_process_calls.jsonl").exists():
        paths.append(root / "native_process_calls.jsonl")
    return {str(p.relative_to(root)): p.read_text() for p in paths if p.is_file()}


def structured_files(mapping):
    # JSON transport can reorder object keys; arrays, payloads, and text bytes
    # remain observable. CLI-to-original comparison below also checks bytes.
    return {
        key: json.loads(value) if key.endswith(".json") else value
        for key, value in mapping.items()
    }


def canonical(value, root):
    return json.dumps(value, sort_keys=True).replace(str(root), "<ROOT>")


def baseline(root, original=True):
    native = source(root)
    if original:
        scope = {"__name__": "dirac_original", "__file__": str(ROOT / SOURCE)}
        exec((FIXTURES / "dirac_recursive_original.py.txt").read_text(), scope)
        for key in ("REPO_ROOT", "DATASET", "ARTIFACT_ROOT", "LEAN_ROOT"):
            scope[key] = getattr(native, key)
        main = scope["main"]
    else:
        main = native.main
    # Install exactly the same compiler boundary in this test interpreter.
    spec = __import__("importlib.util", fromlist=["util"]).spec_from_file_location(
        "compiler_fixture", FIXTURES / "dirac_startup/sitecustomize.py"
    )
    module = __import__("importlib.util", fromlist=["util"]).module_from_spec(spec)
    previous = __import__("subprocess").run
    spec.loader.exec_module(module)
    output = io.StringIO()
    try:
        with patch.object(sys, "argv", ["dirac", "--json"]), redirect_stdout(output):
            try:
                result = main()
            except (RuntimeError, OSError, ValueError, IndexError) as error:
                result = (type(error).__name__, str(error))
    finally:
        __import__("subprocess").run = previous
    return result, output.getvalue(), files(root)


class DiracTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        cls.temp = tempfile.TemporaryDirectory(prefix="dirac-runtime-")
        cls.base = Path(cls.temp.name)
        cls.env = {
            "PYTHONPATH": str(FIXTURES / "dirac_startup"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        cls.oldenv = {key: os.environ.get(key) for key in cls.env}
        os.environ.update(cls.env)

    @classmethod
    def tearDownClass(cls):
        for key, value in cls.oldenv.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cls.temp.cleanup()

    def test_source_equivalence(self):
        for mode in ("pass", "lean_failure", "foundation_failure", "launch_error"):
            results = []
            for original in (True, False):
                root = fixture_root(
                    self.base / f"equivalence-{mode}-{original}", self.doc, mode
                )
                outcome = baseline(root, original)
                if mode in ("pass", "lean_failure"):
                    self.assertEqual(outcome[0], int(mode == "lean_failure"))
                else:
                    self.assertIsInstance(outcome[0], tuple)
                    self.assertIn(
                        (
                            "command failed"
                            if mode == "foundation_failure"
                            else "deterministic compiler launch failure"
                        ),
                        outcome[0][1],
                    )
                results.append(canonical(outcome, root))
            self.assertEqual(*results, mode)

    def test_control_registration(self):
        import mathformer as hub

        audit = hub.audit_control(hub.build_registry())
        self.assertNotIn(
            "scripts/dirac_recursive_tools.py", audit["uncontrolled_entrypoints"]
        )
        self.assertNotIn(
            "tests/mcp/run_dirac_recursive_workflow_tests.py",
            audit["uncontrolled_entrypoints"],
        )

    def test_authored_generator(self):
        import importlib.util

        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("dirac_normalizer", path)
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        self.assertEqual(normalizer.dirac_recursive_route_descriptor(), self.doc)

    def test_write_guard(self):
        async def run():
            server = FastMCP("denied")

            def deny(path):
                raise ValueError("service write denied")

            register_dirac_recursive_tools(server, deny)
            root = fixture_root(self.base / "guard", self.doc)
            for ctx in (context(root), context(root, False)):
                with self.assertRaisesRegex(Exception, "write denied|allow_mutating"):
                    await server.call_tool(PREFIX + "load_and_pack", {"context": ctx})
            self.assertFalse((root / "artifacts").exists())

        asyncio.run(run())

    def test_lunar_compile_execute(self):
        self.assertEqual(
            self.doc["id"], "route_formalize_physics_lean_dirac_recursive_workflow"
        )
        self.assertEqual(self.doc["lifecycle"], "active")
        self.assertEqual(
            self.doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 25},
        )
        for row in self.doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        async with manager.open(
            "dirac",
            StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=[str(FIXTURES / "dirac_recursive_server.py"), str(self.base)],
                cwd=str(ROOT),
            ),
            self.env,
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]
                self.assertLessEqual(
                    {
                        op["execution"]["binding"]["target"]
                        for op in self.doc["operations"].values()
                    },
                    {t["name"] for t in tools},
                )

                def compile(doc, inventory=None):
                    received = assets(doc)
                    workflow = compile_workflow(
                        "mcp:dirac",
                        workflow_documents([DESCRIPTOR], received)[0],
                        tools if inventory is None else inventory,
                    )
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertTrue(workflow["prism_source"])
                    return workflow, received

                workflow, received = compile(self.doc)
                self.assertEqual(set(workflow["bindings"]), set(self.doc["operations"]))
                self.assertFalse(
                    compile_workflow(
                        "mcp:dirac", workflow_documents([DESCRIPTOR], received)[0], []
                    )["runnable"]
                )

                async def allow():
                    pass

                async def run(root, doc=None, inputs=None):
                    w, a = compile(doc) if doc else (workflow, received)
                    return await execute(
                        w, a, inputs or {"context": context(root)}, remote, allow
                    )

                for mode in (
                    "pass",
                    "lean_failure",
                    "foundation_failure",
                    "launch_error",
                ):
                    print("  full runtime fixture: " + mode, flush=True)
                    root = fixture_root(self.base / f"runtime-{mode}", self.doc, mode)
                    result = await run(root)
                    if mode in ("pass", "lean_failure"):
                        self.assertEqual(
                            result["status"],
                            "failed" if mode == "lean_failure" else "accepted",
                            str(result)[:3000],
                        )
                        if mode == "lean_failure":
                            self.assertIsNone(result["outputs"])
                            # Native reporting precedes the process-exit gate.
                            artifact = (
                                root / "artifacts/physics_lean/dirac_recursive_batch"
                            )
                            out = {
                                "report": json.loads(
                                    (artifact / "run_report.json").read_text()
                                ),
                                "recursive_plan": json.loads(
                                    (
                                        artifact / "recursive_grounding_plan.json"
                                    ).read_text()
                                ),
                                "exit_code": 1,
                            }
                        else:
                            out = result["outputs"]
                        expected_root = fixture_root(
                            self.base / f"baseline-{mode}", self.doc, mode
                        )
                        code, stdout, expected_files = baseline(expected_root)
                        self.assertEqual(out["exit_code"], code)
                        self.assertEqual(
                            canonical(out["report"], root),
                            canonical(json.loads(stdout), expected_root),
                        )
                        self.assertEqual(
                            canonical(structured_files(files(root)), root),
                            canonical(structured_files(expected_files), expected_root),
                        )
                        self.assertEqual(
                            json.loads(
                                (
                                    root
                                    / "artifacts/physics_lean/dirac_recursive_batch/recursive_grounding_plan.json"
                                ).read_text()
                            ),
                            out["recursive_plan"],
                        )
                        self.assertEqual(out["exit_code"], int(mode == "lean_failure"))
                        self.assertEqual(
                            result["calls"][-1]["status"],
                            "rejected" if mode == "lean_failure" else "accepted",
                        )
                        self.assertEqual(
                            out["report"]["lean_ok_count"],
                            4 if mode == "lean_failure" else 5,
                        )
                        self.assertEqual(
                            [i["source_index"] for i in out["report"]["selected"]],
                            [14, 15, 21, 52, 74],
                        )
                        names = [c["tool"] for c in result["calls"]]
                        self.assertEqual(
                            names,
                            [PREFIX + "load_and_pack"]
                            + [PREFIX + "write_next_source"] * 5
                            + [PREFIX + "build_grounding"]
                            + [PREFIX + "compile_next"] * 5
                            + [PREFIX + "review_next"] * 5
                            + [PREFIX + "check_next"] * 5
                            + [
                                PREFIX + "compute_guards",
                                PREFIX + "return_status",
                                PREFIX + "finish",
                            ],
                        )
                        self.assertEqual(len(result["calls"]), 25)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        self.assertEqual(
                            out["recursive_plan"]["next_policy"]["decision"], "recurse"
                        )
                        compiler_calls = [
                            json.loads(x)
                            for x in (root / "compiler_calls.jsonl")
                            .read_text()
                            .splitlines()
                        ]
                        self.assertEqual(len(compiler_calls), 6)
                        helper_calls = [
                            json.loads(x)
                            for x in (root / "native_process_calls.jsonl")
                            .read_text()
                            .splitlines()
                        ]
                        expected_helpers = (
                            [
                                "intake_physics_foundation_objects.py",
                                "design_foundation_surfaces.py",
                                "build_mathformerphysicslib_object_workbench.py",
                                "verify_foundation_modules.py",
                            ]
                            + [
                                "review_mathematical_final_hypotheses.py",
                                "review_physics_final_hypotheses.py",
                            ]
                            * 5
                            + ["check_derivation_completeness.py"] * 5
                        )
                        self.assertEqual(
                            [Path(c[0]).name for c in helper_calls], expected_helpers
                        )
                        self.assertEqual(compiler_calls[0]["argv"][1], "build")
                        self.assertEqual(
                            [
                                Path(c["argv"][-1]).parent.name
                                for c in compiler_calls[1:]
                            ],
                            [
                                "formalphysics_" + i
                                for i in ("0014", "0015", "0021", "0052", "0074")
                            ],
                        )
                    else:
                        self.assertEqual(result["status"], "failed", str(result)[:2000])
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            result["calls"][-1]["tool"],
                            PREFIX
                            + (
                                "build_grounding"
                                if mode == "foundation_failure"
                                else "compile_next"
                            ),
                        )
                        self.assertEqual(
                            len(result["calls"]),
                            7 if mode == "foundation_failure" else 10,
                        )
                        self.assertFalse(
                            (
                                root
                                / "artifacts/physics_lean/dirac_recursive_batch/run_report.json"
                            ).exists()
                        )
                        if mode == "foundation_failure":
                            self.assertEqual(result["calls"][-1]["status"], "rejected")
                            self.assertEqual(
                                len(
                                    (root / "compiler_calls.jsonl")
                                    .read_text()
                                    .splitlines()
                                ),
                                1,
                            )
                        else:
                            self.assertEqual(result["calls"][-1]["status"], "rejected")
                            self.assertFalse(
                                (
                                    root
                                    / "artifacts/physics_lean/dirac_recursive_batch/formalphysics_0052/lean_check.json"
                                ).exists()
                            )
                budget = deepcopy(self.doc)
                budget["policy"]["limits"]["max_operation_calls"] = 24
                root = fixture_root(self.base / "budget", self.doc)
                result = await run(root, budget)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(result["calls"]), 25)
                self.assertFalse(
                    result["calls"][-1].get("transport_call_performed", False)
                )
                self.assertIn("budget", result["calls"][-1]["error"])
                self.assertFalse(
                    (
                        root
                        / "artifacts/physics_lean/dirac_recursive_batch/run_report.json"
                    ).exists()
                )
                # A shorter descriptor bound fails before selection publication or
                # grounding; no production operation or stop predicate is replaced.
                bounded = deepcopy(self.doc)
                bounded["flow"]["steps"][1]["max_iterations"] = 4
                root = fixture_root(self.base / "bounded", self.doc)
                result = await run(root, bounded)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertEqual(len(result["calls"]), 5)
                self.assertFalse(
                    (
                        root
                        / "artifacts/physics_lean/dirac_recursive_batch/selection.json"
                    ).exists()
                )
                self.assertFalse((root / "compiler_calls.jsonl").exists())
                # Required input, native dataset error, authorization, and I/O errors
                # all stop before any later pass executes.
                for label in (
                    "denied",
                    "missing_required",
                    "bad_dataset",
                    "short_dataset",
                    "write_failure",
                    "outside",
                ):
                    root = fixture_root(self.base / label, self.doc)
                    ctx = context(root, label != "denied")
                    expected_calls = 1
                    if label == "missing_required":
                        (
                            root
                            / "libraries/MathformerPhysicsLib/Lean/Foundations/HilbertSpace.lean"
                        ).unlink()
                    if label == "bad_dataset":
                        (
                            root / "data/benchmarks/formal_science/FormalPhysics.json"
                        ).write_text("{")
                    if label == "short_dataset":
                        (
                            root / "data/benchmarks/formal_science/FormalPhysics.json"
                        ).write_text("[]")
                        expected_calls = 2
                    if label == "write_failure":
                        (
                            root / "MathformerPhysicsLib/Lean/formalphysics_0014"
                        ).write_text("file")
                        expected_calls = 2
                    if label == "outside":
                        ctx = context(self.base.parent)
                    result = await run(root, inputs={"context": ctx})
                    self.assertEqual(result["status"], "failed", label)
                    self.assertEqual(len(result["calls"]), expected_calls, label)
                    self.assertIsNone(result["outputs"])
                    self.assertFalse((root / "compiler_calls.jsonl").exists())
                # Observe actual per-call state, completion on fifth append, and
                # overrun rejection through the registered interfaces.
                root = fixture_root(self.base / "steps", self.doc)
                ctx = context(root)
                packet = await remote.call(PREFIX + "load_and_pack", {"context": ctx})
                histories = [packet["state"]]
                for i in range(5):
                    packet = await remote.call(
                        PREFIX + "write_next_source",
                        {"state": histories[-1], "context": ctx},
                    )
                    histories.append(packet["state"])
                    self.assertEqual(packet["done"], i == 4)
                    self.assertEqual(len(packet["state"]["selected"]), i + 1)
                self.assertEqual(
                    [len(s["selected"]) for s in histories], list(range(6))
                )
                with self.assertRaises(Exception):
                    await remote.call(
                        PREFIX + "write_next_source",
                        {"state": histories[-1], "context": ctx},
                    )
                for operation in ("review_next", "check_next"):
                    args = {"state": histories[-1], "context": ctx}
                    if operation == "check_next":
                        args["grounding"] = {
                            "concept_file": "unused",
                            "intake": {},
                            "surface": {},
                            "workbench": {},
                            "verification": {},
                        }
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(PREFIX + operation, args)
                tampered = deepcopy(histories[-1])
                tampered["selected"][0]["lean_path"] = "outside.lean"
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "compile_next", {"state": tampered, "context": ctx}
                    )
                self.assertFalse((root / "compiler_calls.jsonl").exists())
                self.assertFalse((root / "outside.lean").exists())
                ground = await remote.call(PREFIX + "build_grounding", {"context": ctx})
                state = histories[-1]
                for operation, key in [
                    ("compile_next", "lean_results"),
                    ("review_next", "review_reports"),
                    ("check_next", "completeness_reports"),
                ]:
                    for i in range(5):
                        args = {"state": state, "context": ctx}
                        if operation == "check_next":
                            args.update(ground)
                        before = deepcopy(state)
                        packet = await remote.call(PREFIX + operation, args)
                        state = packet["state"]
                        self.assertEqual(packet["done"], i == 4)
                        self.assertEqual(state[key][:-1], before[key])
                        self.assertEqual(
                            state[key][-1]["case_id"], state["selected"][i]["case_id"]
                        )
                    with self.assertRaises(Exception):
                        await remote.call(PREFIX + operation, args | {"state": state})
                frontier = len(
                    ground["grounding"]["surface"].get("recursive_frontier", [])
                )
                self.assertGreater(frontier, 0)
                for item in state["completeness_reports"]:
                    # Real checker receives the shared frontier count in each case.
                    self.assertEqual(
                        item["summary"]["recursive_frontier_count"], frontier
                    )
                    self.assertEqual(
                        item["artifacts"][0]["recursive_frontier_count"], frontier
                    )
                await self.branches(
                    remote, compile, allow, state, ground["grounding"], root
                )
            except Exception:
                import traceback

                traceback.print_exc()
                raise
        self.assertFalse(manager.active)

    async def branches(self, remote, compile, allow, state, grounding, root):
        # Execute the actual downstream graph with typed outcome fixtures as
        # input. The complete workflow above supplies their real counterparts.
        doc = deepcopy(self.doc)
        doc["inputs"].update(
            state={"type": "BatchState"}, grounding={"type": "Grounding"}
        )
        doc["flow"]["steps"] = [
            step
            for step in doc["flow"]["steps"]
            if step["id"] in ("guards", "classify", "finish")
        ]

        def replace(node):
            if isinstance(node, dict):
                if node.get("ref") == "steps.check.outputs.state":
                    node["ref"] = "inputs.state"
                if node.get("ref") == "steps.ground.outputs.grounding":
                    node["ref"] = "inputs.grounding"
                for value in node.values():
                    replace(value)
            elif isinstance(node, list):
                for value in node:
                    replace(value)

        replace(doc["flow"])
        w, a = compile(doc)
        cases = [
            ("blocked_target_restating_assumption", True, True, False),
            ("derivation_partial", False, True, False),
            ("derivation_partial", False, False, True),
            ("derivation_partial", False, False, False),
            ("complete_autoformalization", False, False, False),
            ("grounded_scaffold", False, False, False),
            ("derivation_partial", False, True, False),
            ("grounded_scaffold", False, False, False),
        ]
        for index, (expected, blocked, review_fail, frontier) in enumerate(cases):
            s = deepcopy(state)
            g = deepcopy(grounding)
            g["surface"]["recursive_frontier"] = (
                [{"id": "open-frontier"}] if frontier else []
            )
            g["verification"]["ok"] = index != 5
            for row in s["review_reports"]:
                row.update(
                    mathematical_status=(
                        "fail" if review_fail and index != 6 else "pass"
                    ),
                    physics_status="fail" if index == 6 else "pass",
                )
            for row in s["completeness_reports"]:
                row["status"] = (
                    "grounded_scaffold"
                    if index in (5, 7)
                    else "complete_autoformalization"
                )
            if blocked:
                s["completeness_reports"][0][
                    "status"
                ] = "blocked_target_restating_assumption"
            if index == 3:
                s["completeness_reports"][0]["status"] = "derivation_partial"
            result = await execute(
                w,
                a,
                {"context": context(root), "state": s, "grounding": g},
                remote,
                allow,
            )
            self.assertEqual(
                result["status"],
                "failed" if index == 5 else "accepted",
                str(result)[:2500],
            )
            if index == 5:
                self.assertIsNone(result["outputs"])
                artifact = root / "artifacts/physics_lean/dirac_recursive_batch"
                out = {
                    "report": json.loads((artifact / "run_report.json").read_text()),
                    "recursive_plan": json.loads(
                        (artifact / "recursive_grounding_plan.json").read_text()
                    ),
                    "exit_code": 1,
                }
            else:
                out = result["outputs"]
            self.assertEqual(out["report"]["status"], expected)
            self.assertEqual(out["recursive_plan"]["status"], expected)
            self.assertEqual(
                out["recursive_plan"]["next_policy"]["decision"],
                "complete" if expected == "complete_autoformalization" else "recurse",
            )
            self.assertEqual(out["exit_code"], int(index == 5))
            self.assertEqual(
                out["report"]["complete_autoformalization_ok"],
                expected == "complete_autoformalization",
            )
            self.assertEqual(
                [c["tool"] for c in result["calls"]],
                [
                    PREFIX + "compute_guards",
                    PREFIX + "return_status",
                    PREFIX + "finish",
                ],
            )
        with self.assertRaises(Exception):
            await remote.call(
                PREFIX + "write_reports",
                {
                    "state": state,
                    "grounding": grounding,
                    "status": "complete_autoformalization",
                    "context": context(root),
                },
            )


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    # A missing or entirely skipped fixture suite cannot qualify a binding.
    sys.exit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
