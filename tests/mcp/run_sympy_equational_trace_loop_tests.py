#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Execute the explicitly supplied contract through registered MCP and Lunar/PRISM."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
    str(ROOT),
]
sys.path.extend(SITES)

import asyncio
from contextlib import chdir, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch
import yaml
from sympy_controlled_suite_tools import source, register_sympy_equational_trace_tools
from sympy_equational_trace_boundary import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/loop/loop_sympy_equational_trace_loop_workflow/workflow.yaml"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/sympy-equational-trace-loop.workflow.json"
)
PREFIX = "mathformer_sympy_equational_trace_"
ORDER = [
    "parse",
    "assumptions",
    "grounding",
    "draft",
    "execute",
    "identity",
    "counterexamples",
    "trace",
    "consistency",
]


def fixture(root, mode=None):
    root = root.resolve()
    root.mkdir(parents=True)
    for relative in source().SOURCES:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    if mode:
        (root / "boundary.json").write_text(json.dumps(mode))
    return root


def snapshot(doc):
    texts = {DESCRIPTOR: json.dumps(doc)}
    texts.update(
        {
            r["path"]: (ROOT / r["path"]).read_text()
            for r in doc["provenance"]["sources"]
        }
    )
    return [
        dict(
            path=p,
            content=t,
            encoding="text",
            sha256=hashlib.sha256(t.encode()).hexdigest(),
        )
        for p, t in texts.items()
    ]


def ledger(root):
    path = root / "commands.jsonl"
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def stable(value, root):
    """Compare source data/argv/history, excluding measured time and mount spelling."""
    if isinstance(value, dict):
        return {
            k: stable(v, root)
            for k, v in value.items()
            if k not in ("duration_ms", "generated_at", "stdout", "stderr")
        }
    if isinstance(value, list):
        return [stable(v, root) for v in value]
    if isinstance(value, str):
        return value.replace(str(root), "$WORKSPACE").replace(
            "$WORKSPACE/artifacts/sympy_api/index.json",
            "artifacts/sympy_api/index.json",
        )
    return value


def original(root, json_output=True):
    module = types.ModuleType("frozen_sympy_equational_trace")
    module.__file__ = str(ROOT / "tests/sympy/run_controlled_suite.py")
    backup = ROOT / "tests/mcp/fixtures/sympy_equational_trace_original.py.txt"
    exec(compile(backup.read_text(), module.__file__, "exec"), module.__dict__)
    install(module)
    token = module.WORKING_DIRECTORY.set(root)
    stream = io.StringIO()
    argv = ["suite", "--artifact-root", str(root / "out")]
    if json_output:
        argv.append("--json")
    try:
        with chdir(root), patch.object(sys, "argv", argv), redirect_stdout(stream):
            code = module.main()
    finally:
        module.WORKING_DIRECTORY.reset(token)
    return (
        code,
        json.loads((root / "out/suite_report.json").read_text()),
        stream.getvalue(),
    )


class Observed:
    def __init__(self, remote):
        self.remote, self.events = remote, []

    async def tools(self):
        return await self.remote.tools()

    async def call(self, name, args):
        result = await self.remote.call(name, args)
        self.events.append((name, deepcopy(args), deepcopy(result)))
        return result


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())

    def test_authored_contract_and_provenance(self):
        self.assertEqual(self.doc["id"], "loop_sympy_equational_trace_loop_workflow")
        self.assertEqual(self.doc["lifecycle"], "active")
        self.assertEqual(self.doc, json.loads(AUTHORED.read_text()))
        self.assertEqual(
            self.doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 15},
        )
        self.assertEqual(self.doc["policy"]["effects"]["network"], [])
        for row in self.doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(
            "tests/sympy/run_controlled_suite.py",
            [r["path"] for r in self.doc["provenance"]["sources"]],
        )
        import importlib.util

        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("equational_normalizer", path)
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        selected = [
            x
            for x in normalizer.parse_loop_contracts(
                (ROOT / normalizer.HOOKS).read_text().splitlines()
            )
            if x["id"] == "sympy_equational_trace_loop"
        ]
        self.assertEqual(len(selected), 1)
        # Exercise the real generator branch without unrelated inventory rows
        # (the working tree has an existing duplicate mathlib loop identity).
        with (
            patch.object(normalizer.hub, "build_registry", return_value={}),
            patch.object(normalizer.hub, "build_intent_routes", return_value=[]),
            patch.object(normalizer, "parse_loop_contracts", return_value=selected),
        ):
            self.assertEqual(
                next(d for d in normalizer.inventory() if d["id"] == self.doc["id"]),
                self.doc,
            )

    def test_native_paths_concepts_and_fail_fast_stages(self):
        native = source()
        install(native)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            packet = base / "concepts.json"
            packet.write_text(
                json.dumps(
                    {"units": [{"concepts": ["z", "a", "z"]}, {"concepts": ["b", "a"]}]}
                )
            )
            self.assertEqual(native.concepts_from_parse(packet), ["a", "b", "z"])
            packet.write_text('{"units": []}')
            self.assertEqual(
                native.concepts_from_parse(packet), ["symbolic_simplification"]
            )
            packet.write_text("{broken")
            with self.assertRaises(json.JSONDecodeError):
                native.concepts_from_parse(packet)
            token = native.WORKING_DIRECTORY.set(base)
            try:
                preflight = native.initialize(
                    base / "preflight", base / "api/index.json"
                )
                for _ in range(2):
                    preflight = native.preflight_step(preflight)["state"]
                self.assertTrue(preflight["preflight_ok"])
            finally:
                native.WORKING_DIRECTORY.reset(token)
            # Every nonzero stage exits that case at the failed command. All
            # preceding packets are written by the real local stage functions.
            for index, stage in enumerate(ORDER):
                with self.subTest(stage=stage):
                    root = fixture(base / stage, {"stage": stage, "fault": "nonzero"})
                    token = native.WORKING_DIRECTORY.set(root)
                    try:
                        report = native.run_case(
                            native.SOURCES[0], base / "api/index.json", root / "out"
                        )
                    finally:
                        native.WORKING_DIRECTORY.reset(token)
                    self.assertFalse(report["ok"])
                    expected = index + 1
                    self.assertEqual(len(report["results"]), expected)
                    self.assertEqual(
                        [r["id"].split(".")[-1] for r in report["results"]],
                        ORDER[:expected],
                    )
            asyncio.run(self.policy(base))

    async def policy(self, base):
        from mcp.server.fastmcp import FastMCP

        server = FastMCP("policy")
        enabled = [True]

        def authorize():
            if not enabled[0]:
                raise PermissionError("readonly")

        register_sympy_equational_trace_tools(
            server, authorize, lambda p: p.resolve().is_relative_to(base.resolve())
        )
        root = fixture(base / "policy")
        args = {
            "context": {"working_directory": str(root), "allow_mutating": True},
            "artifact_root": "custom",
            "json_output": False,
        }
        entered = (await server.call_tool(PREFIX + "initialize", args))[1]["state"]
        self.assertEqual(entered["root"], str((root / "custom").resolve()))
        self.assertEqual(entered["cursor"], 0)
        self.assertEqual(entered["case_reports"], [])
        self.assertFalse(entered["json_output"])
        enabled[0] = False
        with self.assertRaisesRegex(Exception, "readonly"):
            await server.call_tool(PREFIX + "preflight_step", {"state": entered})
        enabled[0] = True
        for mutation, message in [
            ({"root": str(base.parent / "outside")}, "write roots"),
            ({"api_index": str(root / "wrong")}, "API index"),
            ({"python": "arbitrary-python"}, "executable"),
        ]:
            with self.assertRaisesRegex(Exception, message):
                await server.call_tool(
                    PREFIX + "preflight_step", {"state": {**entered, **mutation}}
                )
        args["context"]["allow_mutating"] = False
        with self.assertRaisesRegex(Exception, "allow_mutating"):
            await server.call_tool(PREFIX + "initialize", args)

    def test_registered_mcp_lunar_prism_runtime(self):
        with tempfile.TemporaryDirectory(prefix="sympy-equational-") as tmp:
            asyncio.run(self.scenario(Path(tmp)))

    async def scenario(self, base):
        manager = SessionManager()
        server = (
            "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
            + repr(
                [
                    str(ROOT / "scripts"),
                    str(ROOT / "tests/mcp/fixtures"),
                    str(ROOT),
                    *SITES,
                ]
            )
            + ";from sympy_equational_trace_boundary import serve;serve("
            + repr(str(base))
            + ")"
        )
        failure = None
        async with manager.open(
            "equational",
            StdioConfig(
                command=sys.executable,
                args=["-c", server],
                cwd=str(ROOT),
                timeout_seconds=600,
            ),
            {},
        ) as remote:
            try:
                inventory = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compiled(document, tools=None):
                    assets = snapshot(document)
                    workflow = compile_workflow(
                        "mcp:equational",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        inventory if tools is None else tools,
                    )
                    return workflow, assets

                workflow, assets = compiled(self.doc)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(self.doc["operations"]))
                for operation in self.doc["operations"].values():
                    target = operation["execution"]["binding"]["target"]
                    self.assertFalse(
                        compiled(
                            self.doc, [t for t in inventory if t["name"] != target]
                        )[0]["runnable"]
                    )

                async def allow():
                    pass

                async def run(root, document=None, json_output=True, **overrides):
                    graph, files = (
                        compiled(document) if document else (workflow, assets)
                    )
                    self.assertTrue(graph["runnable"], graph["diagnostics"])
                    observer = Observed(remote)
                    inputs = {
                        "context": {
                            "working_directory": str(root),
                            "allow_mutating": True,
                        },
                        "artifact_root": "out",
                        "json_output": json_output,
                        **overrides,
                    }
                    result = await execute(graph, files, inputs, observer, allow)
                    return result, observer.events

                root = fixture(base / "success")
                result, events = await run(root)
                self.assertEqual(result["status"], "accepted", str(result)[:5000])
                completion = result["outputs"]["completion"]
                self.assertEqual(completion["exit_code"], 0)
                report = json.loads(Path(completion["suite_report"]).read_text())
                self.assertEqual(json.loads(completion["stdout"]), report)
                self.assertTrue(Path(completion["index_html"]).is_file())
                self.assertEqual(len(result["calls"]), 15)
                self.assertEqual(
                    [e[0] for e in events],
                    [PREFIX + "initialize"]
                    + [PREFIX + "preflight_step"] * 2
                    + [PREFIX + "prepare_cases"]
                    + [
                        name
                        for _ in range(5)
                        for name in [PREFIX + "suite_case", PREFIX + "collect_case"]
                    ]
                    + [PREFIX + "finish"],
                )
                self.assertEqual(
                    [e[2]["done"] for e in events if e[0].endswith("preflight_step")],
                    [False, True],
                )
                collected = [e[2] for e in events if e[0].endswith("collect_case")]
                self.assertEqual(
                    [e["state"]["cursor"] for e in collected], [1, 2, 3, 4, 5]
                )
                self.assertEqual([e["done"] for e in collected], [False] * 4 + [True])
                self.assertEqual(
                    [len(e["state"]["case_reports"]) for e in collected],
                    [1, 2, 3, 4, 5],
                )
                self.assertEqual(len(ledger(root)), 47)
                self.assertTrue(all(row["timeout"] == 180 for row in ledger(root)))
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
                for case in report["cases"]:
                    self.assertEqual(
                        [r["id"].split(".")[-1] for r in case["results"]], ORDER
                    )
                    self.assertTrue(Path(case["artifact"]).is_file())
                    self.assertTrue(Path(case["html"]).is_file())
                    self.assertEqual(
                        json.loads(
                            (
                                Path(case["html"]).parent
                                / "sympy_consistency_report.json"
                            ).read_text()
                        ),
                        case["consistency"],
                    )
                    cmd = case["results"][6]["cmd"]
                    self.assertEqual(cmd[cmd.index("--max-n") + 1], "100")
                    self.assertEqual(len(case["results"]), 9)
                    for check in case["results"]:
                        self.assertGreaterEqual(check["duration_ms"], 0)
                        self.assertLessEqual(len(check["stdout"]), 4000)
                        self.assertLessEqual(len(check["stderr"]), 4000)
                oldroot = fixture(base / "original-success")
                code, old, output = original(oldroot)
                self.assertEqual(code, completion["exit_code"])
                self.assertEqual(json.loads(output), old)
                self.assertEqual(stable(report, root), stable(old, oldroot))
                self.assertEqual(
                    stable(ledger(root), root), stable(ledger(oldroot), oldroot)
                )
                self.assertEqual(
                    Path(completion["index_html"]).read_bytes(),
                    (oldroot / "out/index.html").read_bytes(),
                )
                for case, previous in zip(report["cases"], old["cases"]):
                    self.assertEqual(
                        Path(case["artifact"]).read_bytes(),
                        Path(previous["artifact"]).read_bytes(),
                    )

                for stage, count in [("dependency_probe", 1), ("api_index", 2)]:
                    mode = {"stage": stage, "fault": "nonzero"}
                    root = fixture(base / stage, mode)
                    result, events = await run(root, json_output=False)
                    self.assertEqual(result["status"], "accepted", result)
                    out = result["outputs"]["completion"]
                    self.assertEqual(out["exit_code"], 1)
                    self.assertIsNone(out["index_html"])
                    self.assertEqual(out["stdout"], "sympy controlled suite ok=False\n")
                    report = json.loads(Path(out["suite_report"]).read_text())
                    self.assertEqual(len(report["results"]), count)
                    self.assertEqual(len(events), count + 4)
                    self.assertFalse(any(e[0].endswith("suite_case") for e in events))
                    last = report["results"][-1]
                    self.assertEqual(last["returncode"], 7)
                    self.assertEqual(len(last["stdout"]), 4000)
                    self.assertEqual(len(last["stderr"]), 4000)
                    self.assertTrue(last["stdout"].endswith("TAIL"))
                    self.assertFalse((root / "out/index.html").exists())
                    oldroot = fixture(base / (stage + "-original"), mode)
                    code, old, printed = original(oldroot, False)
                    self.assertEqual(code, 1)
                    self.assertEqual(printed, out["stdout"])
                    self.assertEqual(stable(report, root), stable(old, oldroot))

                # Failure inside one case retains its prefix and later cases run.
                for stage, prefix in [("parse", 1), ("identity", 6)]:
                    root = fixture(
                        base / ("case-" + stage),
                        {
                            "stage": stage,
                            "case": "sum_first_odd_numbers",
                            "fault": "nonzero",
                        },
                    )
                    result, events = await run(root)
                    self.assertEqual(result["status"], "accepted", str(result)[:3000])
                    self.assertEqual(result["outputs"]["completion"]["exit_code"], 1)
                    report = json.loads((root / "out/suite_report.json").read_text())
                    self.assertEqual(
                        [c["ok"] for c in report["cases"]],
                        [False, True, True, True, True],
                    )
                    first = report["cases"][0]
                    self.assertEqual(len(first["results"]), prefix)
                    self.assertEqual("case_id" in first, stage != "parse")
                    self.assertEqual(len(events), 15)
                    self.assertEqual(len(ledger(root)), 2 + prefix + 4 * 9)
                    final = events[-2][2]["state"]
                    self.assertEqual(final["cursor"], 5)
                    self.assertEqual(final["case_reports"], report["cases"])

                for fault in ["timeout", "launch"]:
                    mode = {"stage": "parse", "fault": fault}
                    root = fixture(base / fault, mode)
                    result, events = await run(root)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertFalse((root / "out/suite_report.json").exists())
                    self.assertEqual(result["calls"][-1]["operation"], "suite_case")
                    self.assertEqual(len(ledger(root)), 3)
                    oldroot = fixture(base / (fault + "-original"), mode)
                    with self.assertRaises(
                        subprocess.TimeoutExpired if fault == "timeout" else OSError
                    ):
                        original(oldroot)
                    self.assertFalse((oldroot / "out/suite_report.json").exists())
                    self.assertEqual(
                        stable(ledger(root), root), stable(ledger(oldroot), oldroot)
                    )

                root = fixture(base / "report-write-failure")
                (root / "out/index.html").mkdir(parents=True)
                result, _ = await run(root)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(result["calls"][-1]["operation"], "finish")
                self.assertFalse((root / "out/suite_report.json").exists())

                for loop in ["preflight", "cases"]:
                    root = fixture(base / ("exhaust-" + loop))
                    document = deepcopy(self.doc)
                    node = (
                        document["flow"]["steps"][1]
                        if loop == "preflight"
                        else document["flow"]["steps"][3]
                    )
                    node["max_iterations"] = 1
                    result, events = await run(root, document)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["failure_disposition"], "fail")
                    self.assertIsNone(result["outputs"])
                    self.assertFalse((root / "out/suite_report.json").exists())
                    self.assertEqual(len(events), 2 if loop == "preflight" else 6)
                root = fixture(base / "budget")
                document = deepcopy(self.doc)
                document["policy"]["limits"]["max_operation_calls"] = 2
                result, _ = await run(root, document)
                self.assertEqual(result["status"], "failed")
                self.assertIn("budget", str(result).lower())
                root = fixture(base / "denied")
                result, _ = await run(
                    root,
                    context={"working_directory": str(root), "allow_mutating": False},
                )
                self.assertEqual(result["status"], "failed")
                self.assertFalse((root / "out").exists())
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
