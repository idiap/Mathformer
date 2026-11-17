#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402
"""Local input fixtures, frozen source oracle and real Lunar/PRISM execution.

This planner has no model/provider or external compiler step. Artifact modules
are deterministic input fixtures (not patched production steps); compiler
fixtures vary the supplied contract, inventory and budgets. The real PRISM
parser/checker/compiler/runtime and real registered MCP tools run throughout.
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
import yaml

from sympy_goal_plan_tools import source, SOURCE
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_sympy_goal_sample_plan_0000_workflow/workflow.yaml"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/sympy-goal-plan.workflow.json"
)
ORIGINAL = ROOT / "tests/mcp/fixtures/sympy_goal_plan_original.py.txt"
PREFIX = "mathformer_sympy_goal_plan_"
CASE_ID = "formalphysics_0000"
WORKFLOW_ID = "hub_physics_sympy_goal_sample_plan_0000_workflow"


def oracle():
    loader = SourceFileLoader("sympy_plan_original", str(ORIGINAL))
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    # Restore original repository and CLI identity after relocating the snapshot.
    module.REPO_ROOT = ROOT
    module.SYMPY_ROOT = source().SYMPY_ROOT
    module.__file__ = str(ROOT / SOURCE)
    return module


def comparable(plan):
    plan = deepcopy(plan)
    plan.pop("created_at", None)

    def scrub(value):
        if isinstance(value, dict):
            value.pop("traceback_tail", None)  # extraction changes source line numbers
            for v in value.values():
                scrub(v)
        elif isinstance(value, list):
            for v in value:
                scrub(v)

    scrub(plan)
    for command in plan["commands"].values():
        command[0] = "<worker-python>"
    return plan


def snapshot(doc):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in doc["provenance"]["sources"]
    ]


def artifact_text(mode):
    """An executable local input with histories that expose imports and retries."""
    n = source()
    text = "\n".join("# " + m for m in n.COMMENTARY_MARKERS) + "\n"
    text += 'CALLS = []\nprint("fixture import")\n'
    text += "\n".join(name + " = []" for name in n.REQUIRED_SURFACES) + "\n"
    text += """def _gate(name, *args):
    CALLS.append([name, list(args)])
    print('gate:' + name)
    return {'ok': True, 'history': list(CALLS)}
"""
    for name in n.REQUIRED_FUNCTIONS:
        text += f"def {name}(*args):\n    return _gate({name!r}, *args)\n"
    if mode == "failed":
        for name in n.VALIDATOR_FUNCTIONS:
            text += f'def {name}(*args):\n    report = _gate({name!r}, *args)\n    report["ok"] = False\n    return report\n'
    elif mode == "exception_report":
        text += 'def validate_dimensions():\n    _gate("validate_dimensions")\n    raise ValueError("first-call failure")\n'
    elif mode == "retry":
        text += """def validate_dimensions(*args):
    report = _gate('validate_dimensions', *args)
    if not args:
        raise TypeError('retry exactly once')
    return report
"""
    elif mode == "retry_failure":
        text += """def validate_dimensions(*args):
    _gate('validate_dimensions', *args)
    if not args:
        raise TypeError('retry once')
    raise RuntimeError('second-call escapes')
"""
    elif mode == "missing_function":
        text += "del validate_dimensions\n"
    elif mode == "partial":
        text += "# TODO: unfinished support\ndel CLAIM\n"
    elif mode == "markers":
        text += "# TODO FIXME\n# raise NotImplementedError\n" * 141
    elif mode == "import_error":
        text += 'raise RuntimeError("cannot import input")\n'
    elif mode == "removed_during_import":
        text += "from pathlib import Path\nPath(__file__).unlink()\n"
    return text


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sympy-goal-plan-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.native, self.old = source(), oracle()

    def artifact(self, mode):
        path = self.directory / (mode + ".py")
        path.write_text(artifact_text(mode))
        return path

    def request(self, path, **changes):
        return dict(
            case=CASE_ID,
            sympy_file=str(path) if path else None,
            run_gates=True,
            output=None,
            reasoning_log=None,
            **changes,
        )

    def plan(self, module, path, gates=True):
        with redirect_stdout(io.StringIO()):
            return module.build_plan(CASE_ID, path, run_gates=gates)

    def test_native_source_equivalence_and_fixed_bounds(self):
        self.assertEqual(
            hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
            "9f295f9ee0cda6b7c5bda1b932a6293ac7ac700630e1761f45f0c7128a0b6801",
        )
        for mode in [
            "complete",
            "partial",
            "failed",
            "exception_report",
            "retry",
            "markers",
            "import_error",
            "missing",
            "removed_during_import",
        ]:
            path = (
                self.artifact(mode)
                if mode != "missing"
                else self.directory / "absent.py"
            )
            for gates in [False, True]:
                if mode == "removed_during_import":
                    path = self.artifact(mode)
                expected = self.plan(self.old, path, gates)
                if mode == "removed_during_import":
                    path = self.artifact(mode)
                actual = self.plan(self.native, path, gates)
                self.assertEqual(comparable(actual), comparable(expected))
                if mode == "removed_during_import" and gates:
                    self.assertEqual(actual["next_action"], "recurse")
                    self.assertEqual(actual["open_frontier_count"], 0)
                if mode == "markers":
                    markers = [
                        f for f in actual["findings"] if f["code"] == "open_marker"
                    ]
                    self.assertEqual(len(markers), 423)
                if gates and mode in {
                    "complete",
                    "failed",
                    "retry",
                    "exception_report",
                }:
                    reports = actual["current_evidence"]["executable_gates"][
                        "validators"
                    ]
                    self.assertEqual(
                        [r["name"] for r in reports], self.native.VALIDATOR_FUNCTIONS
                    )
                    history = reports[-1]["summary"]["history"]
                    self.assertEqual(len(history), 13 if mode == "retry" else 12)
                    if mode == "retry":
                        self.assertEqual(
                            history[:2],
                            [
                                ["validate_dimensions", []],
                                ["validate_dimensions", [None]],
                            ],
                        )
                if mode == "failed" and gates:
                    self.assertEqual(actual["open_frontier_count"], 12)
                    self.assertEqual(
                        [f["code"] for f in actual["findings"]][-1], "run_all_failed"
                    )
        for mode, error in [
            ("retry_failure", RuntimeError),
            ("missing_function", AttributeError),
        ]:
            path = self.artifact(mode)
            for module in [self.old, self.native]:
                with self.assertRaises(error):
                    self.plan(module, path)
        bad = self.directory / "utf8.py"
        bad.write_bytes(b"\xff")
        for module in [self.old, self.native]:
            with self.assertRaises(UnicodeDecodeError):
                self.plan(module, bad)
        # Native CLI serialization, logging and output bytes still use shared code.
        for mode in ["complete", "partial", "import_error", "missing"]:
            path = (
                self.artifact(mode)
                if mode != "missing"
                else self.directory / "absent.py"
            )
            outputs = []
            for module in [self.old, self.native]:
                stream = io.StringIO()
                with redirect_stdout(stream):
                    code = module.main(
                        [
                            "--case",
                            CASE_ID.removeprefix("formalphysics_"),
                            "--sympy-file",
                            str(path),
                            "--run-gates",
                            "--json",
                        ]
                    )
                raw = stream.getvalue()
                prefix, payload = raw.split('{\n  "style"', 1)
                plan = json.loads('{\n  "style"' + payload)
                self.assertEqual(
                    raw[len(prefix) :],
                    json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
                )
                outputs.append((code, prefix, comparable(plan)))
            self.assertEqual(*outputs)

    def test_lunar_registered_tools_and_real_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc, json.loads(AUTHORED.read_text()))
        self.assertEqual(doc["id"], WORKFLOW_ID)
        self.assertEqual(doc["lifecycle"], "active")
        from normalize_workflows_tools import source as generator

        generated = next(d for d in generator().inventory() if d["id"] == doc["id"])
        self.assertEqual(doc, generated)
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(SOURCE, [r["path"] for r in doc["provenance"]["sources"]])
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "sympy-goal-plan",
            StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
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

                def compile(document, inventory=None):
                    assets = snapshot(document)
                    w = workflow_documents([DESCRIPTOR], assets)[0]
                    return (
                        compile_workflow(
                            "mcp:sympy-goal-plan",
                            w,
                            tools if inventory is None else inventory,
                        ),
                        assets,
                    )

                workflow, assets = compile(doc)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertEqual(workflow["runtime_status"], "ready")
                self.assertTrue(workflow["prism_source"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(doc["operations"]))
                self.assertFalse(compile(doc, [])[0]["runnable"])

                async def allow():
                    pass

                async def run(request, document=None):
                    w, a = (
                        compile(document)
                        if document is not None
                        else (workflow, assets)
                    )
                    self.assertTrue(w["runnable"], w["diagnostics"])
                    return await execute(
                        w,
                        a,
                        {
                            "request": request,
                            "context": {"working_directory": str(self.directory)},
                        },
                        remote,
                        allow,
                    )

                for mode in [
                    "complete",
                    "partial",
                    "failed",
                    "exception_report",
                    "retry",
                    "markers",
                    "import_error",
                    "missing",
                    "removed_during_import",
                ]:
                    for gates in [False, True]:
                        path = (
                            self.artifact(mode)
                            if mode != "missing"
                            else self.directory / "absent.py"
                        )
                        expected = self.plan(self.old, path, gates)
                        if mode == "removed_during_import":
                            path = self.artifact(mode)
                        request = self.request(path)
                        request["run_gates"] = gates
                        result = await run(request)
                        self.assertEqual(result["status"], "accepted", result)
                        actual = result["outputs"]["plan"]
                        self.assertEqual(comparable(actual), comparable(expected))
                        self.assertEqual(result["outputs"]["exit_code"], 0)
                        self.assertEqual(
                            json.loads(result["outputs"]["json_text"]), actual
                        )
                        self.assertTrue(
                            result["outputs"]["stdout_text"].endswith(
                                result["outputs"]["json_text"] + "\n"
                            )
                        )
                        names = ["initialize"]
                        if mode != "missing":
                            names += ["scan_import"]
                            if mode != "import_error":
                                names += [
                                    "inspect",
                                    "gates" if gates else "add_finding",
                                ]
                            else:
                                names += ["add_finding"]
                        else:
                            names += ["add_finding"]
                        names += ["classify", "assemble", "emit"]
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            [PREFIX + n for n in names],
                        )
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        if mode == "retry" and gates:
                            history = actual["current_evidence"]["executable_gates"][
                                "validators"
                            ][-1]["summary"]["history"]
                            self.assertEqual(len(history), 13)
                            self.assertEqual(
                                result["outputs"]["stdout_text"].count(
                                    "fixture import"
                                ),
                                1,
                            )
                # The documented absent default is preserved; no production input runs.
                self.assertFalse(self.native.case_path(CASE_ID, None).exists())
                result = await run(self.request(None))
                self.assertEqual(
                    result["outputs"]["plan"]["goal_status"], "missing_artifact"
                )
                # Source-owned output then reasoning-log append, including partial plans.
                for mode in ["complete", "partial"]:
                    path = self.artifact(mode)
                    request = self.request(path)
                    request.update(
                        output="nested/plan.json",
                        reasoning_log="nested/reasoning.jsonl",
                    )
                    result = await run(request)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        (self.directory / request["output"]).read_text(),
                        result["outputs"]["json_text"] + "\n",
                    )
                    self.assertNotIn('"style"', result["outputs"]["stdout_text"])
                    log = [
                        json.loads(line)
                        for line in (self.directory / request["reasoning_log"])
                        .read_text()
                        .splitlines()
                    ]
                    self.assertTrue(log)
                    self.assertIn(
                        result["outputs"]["plan"]["goal_status"], json.dumps(log[-1])
                    )
                # Second TypeError-call failure and missing getattr escape; no downstream calls.
                for mode, count in [
                    ("retry_failure", 4),
                    ("missing_function", 4),
                    ("utf8", 2),
                ]:
                    path = self.artifact(mode)
                    if mode == "utf8":
                        path.write_bytes(b"\xff")
                    result = await run(self.request(path))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), count)
                path = self.artifact("complete")
                request = self.request(path)
                request["output"] = str(
                    self.directory
                )  # write fails; log is not attempted
                request["reasoning_log"] = "unreached.jsonl"
                result = await run(request)
                self.assertEqual(result["status"], "failed", result)
                self.assertFalse((self.directory / "unreached.jsonl").exists())
                request.update(
                    output="survives.json", reasoning_log=str(self.directory)
                )
                result = await run(request)
                self.assertEqual(result["status"], "failed", result)
                self.assertTrue((self.directory / "survives.json").exists())
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "inspect", {"state": {"_native_json": "{}"}}
                    )
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "emit",
                        {
                            "request": self.request(path),
                            "context": {"working_directory": str(self.directory)},
                            "plan": {},
                            "plan_json": '{"x":1}',
                            "prior_stdout": "",
                        },
                    )
                budget = deepcopy(doc)
                budget["policy"]["limits"]["max_operation_calls"] = 6
                result = await run(self.request(path), budget)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    6,
                )
                self.assertIn("budget", str(result).lower())
                timed = deepcopy(doc)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                w, a = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        w,
                        a,
                        {
                            "request": self.request(path),
                            "context": {"working_directory": str(self.directory)},
                        },
                        remote,
                        pending,
                    )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


def main():
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(PlannerTests)
    )
    return 0 if result.wasSuccessful() and result.testsRun and not result.skipped else 1


if __name__ == "__main__":
    sys.exit(main())
