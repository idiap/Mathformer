#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native main/MCP/Lunar/PRISM parity on isolated deterministic input fixtures.

No provider or external compiler is used by this workflow. Lunar's actual PRISM
parser, checker, compiler and interpreter run without replacements.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]
APPLICATION_SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(APPLICATION_SITES)
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import tempfile
import types
import unittest
from unittest.mock import patch
import yaml
from generative_probe_workflow_tools import source_runner
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_test_generative_workflow/workflow.yaml"


def mount(native, root):
    native.REPO_ROOT = root
    native.CRITERIA = root / "tests/generative/quality_criteria.json"
    native.PROBES = root / "tests/generative/probes/probes.json"
    native.ARTIFACT_ROOT = root / "artifacts/test_program/generative"


def fixture(root, data):
    path = root / "tests/generative/probes/probes.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    (root / "tests/generative/quality_criteria.json").write_text(
        json.dumps({"required_fields": ["probe_id", "forbidden_claims", "goal"]})
    )


def snapshot(document):
    values = {
        r["path"]: (ROOT / r["path"]).read_text()
        for r in document["provenance"]["sources"]
    }
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=p,
            content=s,
            encoding="text",
            sha256=hashlib.sha256(s.encode()).hexdigest(),
        )
        for p, s in values.items()
    ]


def without_timestamp(report):
    result = dict(report)
    result.pop("run_id")
    return result


class ProbeWorkflowTests(unittest.TestCase):
    def test_native_entrypoint_parity_and_unbounded_traversal(self):
        oracle = types.ModuleType("probe_original")
        oracle.__file__ = str(ROOT / "tests/run_generative.py")
        exec(
            compile(
                (
                    ROOT / "tests/mcp/fixtures/generative_probe_original.py.txt"
                ).read_text(),
                oracle.__file__,
                "exec",
            ),
            oracle.__dict__,
        )
        native = source_runner()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            mount(native, root)
            mount(oracle, root)
            good = dict(probe_id="ok", forbidden_claims=["x"], goal="g")
            for data in [
                {},
                {"probes": []},
                {"probes": [{}, good, {"probe_id": "last"}]},
                {"probes": [good] * 10001},
            ]:
                fixture(root, data)
                reports = []
                for module in (oracle, native):
                    stream = io.StringIO()
                    with (
                        patch.object(
                            sys,
                            "argv",
                            ["run_generative.py", "--json", "--validate-only"],
                        ),
                        redirect_stdout(stream),
                    ):
                        code = module.main()
                    report = json.loads(stream.getvalue())
                    self.assertEqual(
                        report,
                        json.loads(
                            (
                                root
                                / "artifacts/test_program/generative/probe_validation_report.json"
                            ).read_text()
                        ),
                    )
                    self.assertEqual(code, 0 if report["ok"] else 3)
                    reports.append(without_timestamp(report))
                self.assertEqual(*reports)
            fixture(root, {"probes": [None]})
            for module in (oracle, native):
                with self.assertRaises(TypeError):
                    module.validate()
            native.PROBES.write_text("{bad")
            for module in (oracle, native):
                with self.assertRaises(json.JSONDecodeError):
                    module.validate()
            native.PROBES.unlink()
            for module in (oracle, native):
                with self.assertRaises(FileNotFoundError):
                    module.validate()

    def test_registered_mcp_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_test_generative_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertIn(
            "tests/run_generative.py",
            [row["path"] for row in document["provenance"]["sources"]],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr([str(ROOT / "scripts"), *APPLICATION_SITES])
                + ";from mcp.server.fastmcp import FastMCP;from generative_probe_workflow_tools import register_generative_probe_workflow_tools;from pathlib import Path;mcp=FastMCP('probes');register_generative_probe_workflow_tools(mcp,path_allowed=lambda p: Path(p).resolve().is_relative_to(Path("
                + repr(str(root))
                + ")));mcp.run(transport='stdio')"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "probe-steps",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile_doc(doc, inventory=None):
                        assets = snapshot(doc)
                        compiled = compile_workflow(
                            "mcp:probe-steps",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools if inventory is None else inventory,
                        )
                        return compiled, assets

                    compiled, assets = compile_doc(document)
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(
                        set(compiled["bindings"]), set(document["operations"])
                    )
                    self.assertFalse(compile_doc(document, [])[0]["runnable"])

                    async def authorize():
                        pass

                    async def run(data, argv=None, doc=None, count=None):
                        fixture(root, data)
                        c, a = compile_doc(doc) if doc else (compiled, assets)
                        self.assertTrue(c["runnable"], c["diagnostics"])
                        return await execute(
                            c,
                            a,
                            {
                                "request": {
                                    "argv": ["--json"] if argv is None else argv,
                                    "probe_count": (
                                        len(data.get("probes", []))
                                        if count is None
                                        else count
                                    ),
                                },
                                "context": {"repository_root": str(root)},
                            },
                            remote,
                            authorize,
                        )

                    good = dict(probe_id="good", forbidden_claims=["wrong"], goal="g")
                    for data, argv in [
                        ({}, []),
                        ({"probes": []}, ["--json"]),
                        ({"probes": [good]}, ["--json", "--validate-only"]),
                        (
                            {
                                "probes": [
                                    {},
                                    good,
                                    {"probe_id": "last", "forbidden_claims": []},
                                ]
                            },
                            [],
                        ),
                    ]:
                        result = await run(data, argv)
                        self.assertEqual(result["status"], "accepted", result)
                        report = result["outputs"]["report"]
                        completion = result["outputs"]["completion"]
                        self.assertEqual(
                            report,
                            json.loads((root / completion["report_path"]).read_text()),
                        )
                        self.assertEqual(
                            completion["exit_code"], 0 if report["ok"] else 3
                        )
                        native = source_runner()
                        mount(native, root)
                        self.assertEqual(
                            without_timestamp(report),
                            without_timestamp(native.validate()),
                        )
                        output = io.StringIO()
                        with redirect_stdout(output):
                            native.publish_report(report, "--json" in argv, root)
                        self.assertEqual(completion["stdout"], output.getvalue())
                        self.assertEqual(
                            sum(
                                c["operation"] == "inspect_probe"
                                for c in result["calls"]
                            ),
                            len(data.get("probes", [])),
                        )
                        if report["probe_count"] == 3:
                            self.assertEqual(
                                report["errors"],
                                [
                                    "<missing-id> missing forbidden_claims, goal, probe_id",
                                    "<missing-id> has no forbidden claims",
                                    "last missing goal",
                                    "last has no forbidden claims",
                                ],
                            )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                    # Real compiler/runtime guard behavior at and beyond a reduced bound.
                    bounded = deepcopy(document)
                    loop = bounded["flow"]["steps"][1]
                    loop["max_iterations"] = 2
                    self.assertEqual(
                        (await run({"probes": [good, good]}, doc=bounded))["status"],
                        "accepted",
                    )
                    loop["max_iterations"] = 1
                    result = await run({"probes": [{}, good]}, doc=bounded)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["initialize", "inspect_probe"],
                    )
                    # Exceptions prevent report generation/publishing; normal validation failures do not.
                    output = (
                        root
                        / "artifacts/test_program/generative/probe_validation_report.json"
                    )
                    output.unlink()
                    result = await run({"probes": [None, good]})
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(result["calls"][-1]["operation"], "inspect_probe")
                    self.assertFalse(output.exists())
                    result = await run({"probes": []}, count=1)
                    self.assertEqual(result["status"], "failed")
                    self.assertFalse(output.exists())
                    output.mkdir()
                    result = await run({"probes": [good]})
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(result["calls"][-1]["operation"], "publish")
                    output.rmdir()

                    async def initialize(count, argv=None):
                        return await remote.call(
                            "mathformer_probe_initialize",
                            {
                                "request": {"argv": argv or [], "probe_count": count},
                                "context": {"repository_root": str(root)},
                            },
                        )

                    fixture(root, {"probes": [good] * 10000})
                    entry = await initialize(10000)
                    self.assertEqual(len(entry["state"]["probes"]), 10000)
                    self.assertEqual(entry["state"]["index"], 0)
                    fixture(root, {"probes": [good] * 10001})
                    with self.assertRaises(MCPConnectionError):
                        await initialize(10001)
                    fixture(root, {"probes": [good, {}]})
                    entry = await initialize(2)
                    advanced = await remote.call(
                        "mathformer_probe_inspect_probe", entry
                    )
                    self.assertEqual(advanced["state"]["index"], 1)
                    self.assertEqual(advanced["state"]["errors"], [])
                    self.assertEqual(
                        advanced["state"]["probes"], entry["state"]["probes"]
                    )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call("mathformer_probe_inspect_probe", entry)
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_probe_build_report",
                            {"state": advanced["state"], "runtime": entry["runtime"]},
                        )
                    fixture(root, {})
                    entry = await initialize(0)
                    with self.assertRaises(MCPConnectionError):
                        await remote.call("mathformer_probe_inspect_probe", entry)
                    (root / "tests/generative/probes/probes.json").write_text("{bad")
                    with self.assertRaises(MCPConnectionError):
                        await initialize(0)
                    (root / "tests/generative/probes/probes.json").unlink()
                    with self.assertRaises(MCPConnectionError):
                        await initialize(0)
                    fixture(root, {})
                    with self.assertRaises(MCPConnectionError):
                        await initialize(0, ["--unknown"])
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 1
                    self.assertEqual(
                        (await run({"probes": [good]}, doc=budget))["status"], "failed"
                    )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
