#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Fixture-only ERFL validation through registered MCP and real Lunar PRISM.

There are no provider/model or external compiler boundaries in this static
workflow. Nothing is substituted: the ERFL parser and PRISM compiler/runtime run.
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
from reasoning_flow_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_reasoning_flow_language_workflow/workflow.yaml"
VALID = """erfl 0.3
reasoning valid_flow {
  goal "produce a calibrated result" -> status
  steps a:A[gap::Context->candidate::Claim] -assume> d:D[candidate::Claim->claim::Claim] -test> p:P[claim::Claim->evidence::Evidence] -assess> r:R[claim::Claim,evidence::Evidence->assessment::Assessment] -calibrate> e:E[claim::Claim,assessment::Assessment->status::Decision]
  on e.accepted => accept
  on e.blocked => stop
}
"""
REPEAT = """  repeat 0..32 [x:X[claim::Claim,assessment::Assessment->repair::Plan] -revise> f:F[claim::Claim,repair::Plan->candidate2::Bundle] -test> p2:P[candidate2::Bundle->evidence2::Evidence] -assess> r2:R[candidate2::Bundle,evidence2::Evidence->assessment2::Assessment] -calibrate> e2:E[candidate2::Bundle,assessment2::Assessment->iteration_status::Decision]] until e2.accepted measure unresolved_findings
"""


def snapshot(doc):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in doc["provenance"]["sources"]
    ]


class ReasoningFlowTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="erfl-fixture-", dir=base)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.context = {"repository_root": str(self.root), "program": "rflow"}
        self.native = source(self.context)
        self.registry = self.root / "registry.json"
        registry = json.loads(self.native.DEFAULT_REGISTRY.read_text())
        self.registry.write_text(json.dumps(registry))
        (self.root / "skills").mkdir()
        reasoning = ["primitive_types:"] + [
            "  - id: " + x["reasoning_primitive"]
            for x in registry["operation_types"].values()
        ]
        reasoning += ["reasoning_styles:", "  - id: valid_flow"]
        self.native.REASONING_REGISTRY.write_text("\n".join(reasoning) + "\n")
        outputs = ["semantic_kinds:"] + [
            "  - id: " + k.lower() for k in registry["semantic_kinds"]
        ]
        outputs += [
            "output_types:",
            "output_type_semantic_kind_contracts:",
            "reasoning_type_output_defaults:",
        ]
        outputs += [
            "  - id: " + x["reasoning_primitive"]
            for x in registry["operation_types"].values()
        ]
        self.native.OUTPUT_REGISTRY.write_text("\n".join(outputs) + "\n")
        self.profiles = self.root / "examples/reasoning_flows"
        self.profiles.mkdir(parents=True)
        self.valid = self.profiles / "valid.rflow"
        self.valid.write_text(VALID)
        self.empty = self.root / "empty"
        self.empty.mkdir()
        loader = SourceFileLoader(
            "_erfl_oracle",
            str(ROOT / "tests/mcp/fixtures/reasoning_flow_original.py.txt"),
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.oracle = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.oracle
        loader.exec_module(self.oracle)
        for name in ("REPO_ROOT", "REASONING_REGISTRY", "OUTPUT_REGISTRY"):
            setattr(self.oracle, name, getattr(self.native, name))

    def request(self, paths=None, **flags):
        return dict(
            paths=[str(p) for p in (paths if paths is not None else [self.valid])],
            registry=str(self.registry),
            strict=flags.get("strict", False),
            check_registries=flags.get("check_registries", False),
            self_test=flags.get("self_test", False),
            json=flags.get("json", True),
        )

    def cli(self, module, request):
        argv = [*request["paths"], "--registry", request["registry"]]
        argv += [
            "--" + k.replace("_", "-")
            for k in ("strict", "check_registries", "self_test", "json")
            if request[k]
        ]
        stdout, stderr = io.StringIO(), io.StringIO()
        previous = sys.argv[0]
        sys.argv[0] = "rflow"
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                try:
                    code = module.main(argv)
                except SystemExit as error:
                    code = int(error.code)
        finally:
            sys.argv[0] = previous
        payload = (
            json.loads(stdout.getvalue())
            if request["json"] and stdout.getvalue()
            else None
        )
        return dict(
            exit_code=code,
            payload=payload,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
        )

    def test_fixture_workflow(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_control_reasoning_flow_language_workflow")
        self.assertEqual(document["lifecycle"], "active")
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
            "erfl",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=tools):
                    assets = snapshot(doc)
                    compiled = compile_workflow(
                        "mcp:erfl",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        inventory,
                    )
                    return compiled, assets

                compiled, assets = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(request, doc=None):
                    c, a = compile(doc) if doc else (compiled, assets)
                    return await execute(
                        c,
                        a,
                        {"request": request, "context": self.context},
                        remote,
                        authorize,
                    )

                async def compare(request, steps):
                    expected = self.cli(self.oracle, request)
                    self.assertEqual(self.cli(self.native, request), expected)
                    result = await run(request)
                    self.assertEqual(result["status"], "accepted", result)
                    actual = result["outputs"]["result"]
                    # Text mode still carries the semantic payload in the adapter.
                    if not request["json"]:
                        expected["payload"] = actual["payload"]
                    self.assertEqual(actual, expected)
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_reasoning_flow_" + s for s in steps],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    return actual

                normal = ["prepare", "expand", "validate_next", "finish"]
                passed = await compare(self.request(check_registries=True), normal)
                self.assertEqual(passed["exit_code"], 0)
                self.assertEqual(passed["payload"]["flow_count"], 1)
                await compare(self.request(json=False), normal)
                # Sorted nonrecursive expansion, argument ordering, duplicate preservation,
                # missing-file continuation and syntax failure remain observable.
                scan = self.root / "scan"
                scan.mkdir()
                (scan / "z.rflow").write_text(VALID)
                (scan / "a.rflow").write_text("bad syntax")
                (scan / "ignored.txt").write_text("bad")
                (scan / "nested").mkdir()
                (scan / "nested/x.rflow").write_text("bad")
                missing = self.root / "absent.rflow"
                mixed = await compare(
                    self.request([scan, missing, self.valid, self.valid]),
                    ["prepare", "expand"] + ["validate_next"] * 5 + ["finish"],
                )
                self.assertEqual(mixed["exit_code"], 1)
                self.assertEqual(
                    [r["source"] for r in mixed["payload"]["flows"]],
                    [
                        str(scan / "a.rflow"),
                        str(scan / "z.rflow"),
                        str(missing),
                        str(self.valid),
                        str(self.valid),
                    ],
                )
                self.assertEqual(mixed["payload"]["valid_flow_count"], 3)
                for request in (
                    self.request([self.empty]),
                    self.request([self.empty], check_registries=True),
                ):
                    empty = await compare(
                        request, ["prepare", "expand", "settle", "finish"]
                    )
                    self.assertEqual(empty["exit_code"], 0)
                    self.assertEqual(empty["payload"]["flows"], [])
                await compare(
                    self.request([]),
                    ["prepare", "early_exit", "settle", "terminal_result"],
                )
                tested = await compare(
                    self.request([], self_test=True),
                    ["prepare", "self_test", "settle", "terminal_result"],
                )
                self.assertTrue(tested["payload"]["self_test"]["ok"])
                # Registry failures precede both self-test and missing-path rejection.
                request = self.request([], self_test=True)
                request["registry"] = str(missing)
                await compare(
                    request, ["prepare", "early_exit", "settle", "terminal_result"]
                )
                self.registry.write_text("{broken")
                await compare(
                    self.request([]),
                    ["prepare", "early_exit", "settle", "terminal_result"],
                )
                self.registry.write_text(self.native.DEFAULT_REGISTRY.read_text())
                # Static repeats exercise both bounds and calibration obligations.
                for repeat, expected_code in (
                    (REPEAT, 0),
                    (REPEAT.replace("0..32", "0..33"), 1),
                    (REPEAT.replace("e2.accepted", "e.accepted"), 1),
                ):
                    self.valid.write_text(
                        VALID.replace("  on e.accepted", repeat + "  on e.accepted")
                    )
                    repeated = await compare(self.request(), normal)
                    self.assertEqual(repeated["exit_code"], expected_code)
                self.valid.write_text(
                    VALID.replace(
                        "reasoning valid_flow",
                        '@KB unused connect(file("fixture"))\nreasoning valid_flow',
                    )
                )
                warn = await compare(self.request(), normal)
                strict = await compare(self.request(strict=True), normal)
                self.assertEqual(warn["exit_code"], 0)
                self.assertEqual(strict["exit_code"], 1)
                self.valid.write_text(VALID)
                # Registry findings affect completion even when every file passes.
                self.native.OUTPUT_REGISTRY.write_text("semantic_kinds:\n")
                failed = await compare(self.request(check_registries=True), normal)
                self.assertEqual(failed["exit_code"], 1)
                self.assertTrue(failed["payload"]["registry_findings"])
                # A real read error aborts the source step and prevents finish.
                # A directory named *.rflow expands into an unreadable-as-file path.
                (scan / "directory.rflow").mkdir()
                for module in (self.oracle, self.native):
                    with self.assertRaises(IsADirectoryError):
                        self.cli(module, self.request([scan]))
                error = await run(self.request([scan]))
                self.assertEqual(error["status"], "failed")
                self.assertIsNone(error["outputs"])
                self.assertEqual(error["calls"][-1]["status"], "rejected")
                self.assertNotIn(
                    "mathformer_reasoning_flow_finish",
                    [c["tool"] for c in error["calls"]],
                )
                # Descriptor exhaustion is a host constraint, with no invented native
                # failure or implicit retry. Lower only the fixture contract bound.
                small = deepcopy(document)
                loop = small["flow"]["steps"][2]
                self.assertEqual(loop["max_iterations"], 4096)
                loop["max_iterations"] = 1
                exhausted = await run(self.request([self.valid, self.valid]), small)
                self.assertEqual(exhausted["status"], "failed")
                self.assertIsNone(exhausted["outputs"])
                self.assertEqual(
                    [c["tool"] for c in exhausted["calls"]],
                    [
                        "mathformer_reasoning_flow_" + x
                        for x in ("prepare", "expand", "validate_next")
                    ],
                )
                # Check exact upper bound and source-owned report history without
                # transporting 4096 growing histories over stdio.
                prepared = await remote.call(
                    "mathformer_reasoning_flow_prepare",
                    {
                        "request": self.request([self.valid] * 4096),
                        "context": self.context,
                    },
                )
                expanded = await remote.call(
                    "mathformer_reasoning_flow_expand", {"session": prepared["session"]}
                )
                state = expanded["state"]
                self.assertEqual(len(state["expanded_paths"]), 4096)
                for _ in range(4095):
                    state = self.native.validate_next_path(state)
                final = await remote.call(
                    "mathformer_reasoning_flow_validate_next", {"state": state}
                )
                self.assertTrue(final["done"])
                self.assertEqual(final["state"]["cursor"], 4096)
                self.assertEqual(len(final["state"]["reports"]), 4096)
                self.assertTrue(all(r["ok"] for r in final["state"]["reports"]))
                overflow = await run(self.request([scan] * 2049))
                self.assertEqual(overflow["status"], "failed")
                self.assertIsNone(overflow["outputs"])
                self.assertEqual(len(overflow["calls"]), 2)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
