#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native/MCP/Lunar integration tests, using an explicit contract.

There is no provider/model or external compiler boundary in this workflow.
Filesystem graph fixtures and received contract snapshots drive the real source,
registered tools, PRISM parser/checker/compiler and runtime without substitutes.
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
from unittest.mock import patch
import yaml
from paper_workflow_catalog_tools import source, SOURCE
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.workflow_contract.validator import validate
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_paper_workflow_catalog_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/paper-workflow-catalog.workflow.json"
FIXTURES = ROOT / "tests/mcp/fixtures"


def oracle(root):
    path = FIXTURES / "paper_workflow_catalog_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "_catalog_original", SourceFileLoader("_catalog_original", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.REPO_ROOT = root
    module.DEFAULT_GRAPH = root / "artifacts/workflow_graphs/workflow_graphs.json"
    module.DEFAULT_OUTPUT = (
        root / "artifacts/paper_skills/workflow_catalog_for_paper.json"
    )
    return module


def cli(module, args):
    stream = io.StringIO()
    with patch.object(sys, "argv", ["catalog", *args]), redirect_stdout(stream):
        code = module.main()
    return code, stream.getvalue()


def snapshot(document):
    def asset(path, content):
        return dict(
            path=path,
            content=content,
            encoding="text",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in document["provenance"]["sources"]
    ]


class CatalogueTests(unittest.TestCase):
    def setUp(self):
        self.document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.model = json.loads(
            (FIXTURES / "paper_workflow_catalog_graph.json").read_text()
        )
        temp = tempfile.TemporaryDirectory(prefix="paper-catalog-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.original = oracle(self.root)
        self.graph = self.original.DEFAULT_GRAPH
        self.graph.parent.mkdir(parents=True)
        self.graph.write_text(json.dumps(self.model, ensure_ascii=False))

    def test_contract_registration_and_native_generator(self):
        result = validate(
            ROOT / AUTHORED, repository_root=ROOT, require_declared_bindings=True
        )
        self.assertTrue(result["valid"], result)
        self.assertEqual(self.document, json.loads((ROOT / AUTHORED).read_text()))
        self.assertEqual(self.document["lifecycle"], "active")
        self.assertEqual(self.document["aliases"], ["paper:workflow-catalog"])
        self.assertIn(
            SOURCE, [r["path"] for r in self.document["provenance"]["sources"]]
        )
        for row in self.document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("_catalog_normalizer", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Render this authored workflow without inventorying unrelated repository
        # contracts (which may be undergoing their own normalization).
        files, catalog = module.render_descriptors([self.document])
        workflow_files = [
            text for path, text in files.items() if path.name == "workflow.yaml"
        ]
        self.assertEqual(len(workflow_files), 1)
        self.assertEqual(yaml.safe_load(workflow_files[0]), self.document)
        self.assertEqual(catalog["workflows"][0]["id"], self.document["id"])
        import mathformer as hub

        action = hub.build_registry()["paper:workflow-catalog"]
        self.assertEqual(action.depends_on, ())
        self.assertIsNone(action.timeout_seconds)
        self.assertEqual(action.command[-1], "--json")
        audit = hub.audit_control(hub.build_registry())
        for path in [
            "scripts/paper_workflow_catalog_tools.py",
            "tests/mcp/run_paper_workflow_catalog_tests.py",
        ]:
            self.assertNotIn(path, audit["uncontrolled_entrypoints"])
        import mathformer_mcp_service

        names = mathformer_mcp_service.service_coverage_report(Path("unused"))[
            "mcp_tools"
        ]
        for op in self.document["operations"].values():
            self.assertIn(op["execution"]["binding"]["target"], names)

    def test_source_parity_branch_order_and_bounds(self):
        native = source()
        packet = native.catalogue(self.model)
        self.assertEqual(packet, self.original.catalogue(self.model))
        self.assertEqual(
            [w["id"] for w in packet["workflows"]], list(self.model["stacks"])
        )
        # Independent expected vocabulary asserts every first-match relation arm,
        # including overlaps and the nested physics/SymPy branch.
        expected = [
            "support",
            "intake/expand",
            "intake/expand",
            "ground",
            "draft/execute/repair",
            "consistency",
            "consistency",
            "physics/symbolic",
            "physics",
            "premise/atp",
            "symbolic",
            "observe/reflect",
            "reflect",
            "control",
            "support",
            "intake/expand",
        ]
        for workflow, relation in zip(packet["workflows"], expected, strict=True):
            self.assertEqual(
                workflow["transition_relation"],
                "$"
                + ", ".join(
                    r"\Rel_{\mathrm{" + token + "}}" for token in relation.split("/")
                )
                + "$",
            )
        row = packet["workflows"][1]
        self.assertEqual(row["kind"], "core")
        self.assertEqual(row["hook_count"], 8)
        self.assertEqual(len(row["first_hooks"]), 5)
        self.assertEqual([h["index"] for h in row["first_hooks"]], list(range(5)))
        self.assertNotIn("ignored", row["first_hooks"][0])
        self.assertEqual(packet["core_workflow_count"], 10)
        self.assertEqual(packet["support_workflow_count"], 6)
        for model in [
            self.model,
            {"stacks": {}, "summary": self.model["summary"]},
            {
                "stacks": {
                    f"z-{i}": {"label": str(i), "family": "support"}
                    for i in range(1051)
                },
                "summary": self.model["summary"],
            },
        ]:
            actual = native.catalogue(model)
            self.assertEqual(actual, self.original.catalogue(model))
            self.assertEqual(len(actual["workflows"]), len(model["stacks"]))
            self.assertEqual(
                native.markdown_report(actual), self.original.markdown_report(actual)
            )
            self.assertEqual(
                native.latex_table(actual), self.original.latex_table(actual)
            )
        self.assertIn(r"\&\_\%\$\#\{\}\textbackslash{}", native.latex_table(packet))
        for model in [
            {},
            {"stacks": None},
            {"stacks": {"broken": {}}},
            {"stacks": {"bad": {"label": "x", "family": "f", "ordered_hooks": [{}]}}},
        ]:
            for module in [native, self.original]:
                with self.assertRaises((KeyError, TypeError, AttributeError)):
                    module.catalogue(model)
        for args, code in [(["--help"], 0), (["--unknown"], 2)]:
            with (
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as error,
            ):
                native.parse_paths(args, self.root)
            self.assertEqual(error.exception.code, code)
        self.assertEqual(
            native.parse_paths([], self.root),
            {
                "graph": str(self.graph),
                "output": str(self.original.DEFAULT_OUTPUT),
                "json": False,
            },
        )
        for args in [
            [],
            ["--json"],
            ["--graph", str(self.graph), "--output", "nested/catalog.json", "--json"],
        ]:
            expected = cli(self.original, args)
            output = self.root / (
                "nested/catalog.json"
                if "--output" in args
                else "artifacts/paper_skills/workflow_catalog_for_paper.json"
            )
            content = [
                output.with_suffix(s).read_bytes() for s in [".json", ".md", ".tex"]
            ]
            with (
                patch.object(native, "REPO_ROOT", self.root),
                patch.object(native, "DEFAULT_GRAPH", self.graph),
                patch.object(native, "DEFAULT_OUTPUT", self.original.DEFAULT_OUTPUT),
            ):
                self.assertEqual(cli(native, args), expected)
            self.assertEqual(
                [output.with_suffix(s).read_bytes() for s in [".json", ".md", ".tex"]],
                content,
            )

    def test_registered_mcp_real_prism_compile_execute(self):
        asyncio.run(self.runtime())

    async def runtime(self):
        manager = SessionManager()
        failure = None
        async with manager.open(
            "paper-catalog",
            StdioConfig(
                command=(
                    str(ROOT / ".venv/bin/python")
                    if (ROOT / ".venv/bin/python").exists()
                    else sys.executable
                ),
                args=[
                    "tests/mcp/fixtures/paper_workflow_catalog_server.py",
                    str(self.root),
                ],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=tools):
                    assets = snapshot(doc)
                    received = workflow_documents([DESCRIPTOR], assets)[0]
                    return (
                        compile_workflow("mcp:paper-catalog", received, inventory),
                        assets,
                    )

                compiled, assets = compile(self.document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(
                    set(compiled["bindings"]), set(self.document["operations"])
                )
                for op in self.document["operations"].values():
                    target = op["execution"]["binding"]["target"]
                    advertised = next(t for t in tools if t["name"] == target)
                    self.assertEqual(
                        set(advertised["inputSchema"]["properties"]), set(op["inputs"])
                    )
                    self.assertEqual(
                        set(advertised["inputSchema"]["required"]), set(op["inputs"])
                    )
                    self.assertEqual(
                        set(advertised["outputSchema"]["properties"]),
                        set(op["outputs"]),
                    )
                    self.assertFalse(
                        compile(
                            self.document, [t for t in tools if t["name"] != target]
                        )[0]["runnable"]
                    )

                async def allow():
                    pass

                async def run(argv, doc=None, context=None):
                    c, a = compile(doc) if doc else (compiled, assets)
                    return await execute(
                        c,
                        a,
                        {
                            "argv": argv,
                            "context": context or {"repository_root": str(self.root)},
                        },
                        remote,
                        allow,
                    )

                for flag in [False, True]:
                    args = ["--output", "out/catalog.json"] + (
                        ["--json"] if flag else []
                    )
                    expected_code, stdout = cli(self.original, args)
                    output = self.root / "out/catalog.json"
                    expected_result = (
                        json.loads(stdout)
                        if flag
                        else self.original.write_outputs(
                            self.original.catalogue(self.model), output
                        )
                    )
                    content = [
                        output.with_suffix(s).read_bytes()
                        for s in [".json", ".md", ".tex"]
                    ]
                    for s in [".json", ".md", ".tex"]:
                        output.with_suffix(s).unlink()
                    result = await run(args)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"],
                        {
                            "catalogue": self.original.catalogue(self.model),
                            "result": expected_result,
                            "exit_code": expected_code,
                        },
                    )
                    self.assertEqual(
                        [
                            output.with_suffix(s).read_bytes()
                            for s in [".json", ".md", ".tex"]
                        ],
                        content,
                    )
                    self.assertEqual(
                        json.loads(output.read_text())["workflows"][0]["id"],
                        "z-support",
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [
                            "mathformer_paper_catalog_" + s
                            for s in [
                                "parse_paths",
                                "load_graph",
                                "catalogue",
                                "write_outputs",
                                "emit_result",
                            ]
                        ],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    self.assertIn(
                        stdout, (self.root / "mcp-diagnostics.log").read_text()
                    )
                # Exhaust source collections without an invented iteration cap.
                for count in [0, 1051]:
                    model = {
                        "stacks": {
                            f"z-{i}": {"label": str(i), "family": "f"}
                            for i in range(count)
                        },
                        "summary": self.model["summary"],
                    }
                    self.graph.write_text(json.dumps(model))
                    result = await run(["--output", "large.json", "--json"])
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"]["result"]["workflow_count"], count
                    )
                    self.assertEqual(
                        json.loads((self.root / "large.json").read_text()),
                        self.original.catalogue(model),
                    )
                    self.assertEqual(len(result["calls"]), 5)
                self.graph.write_text(json.dumps(self.model))
                # Runtime operation budget fails before publication; no retry.
                bounded = deepcopy(self.document)
                bounded["policy"]["limits"]["max_operation_calls"] = 3
                result = await run(["--output", "budget.json"], bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    3,
                )
                self.assertFalse((self.root / "budget.json").exists())
                # Native errors terminate at their true step and leave prior writes.
                cases = [
                    ("missing", "absent.json", None, 2),
                    ("decode", "bad.json", "{", 2),
                    ("schema", "bad.json", '{"stacks":{"broken":{}},"summary":{}}', 3),
                    ("render", "bad.json", '{"stacks":{},"summary":{}}', 4),
                ]
                for name, graph, content, calls in cases:
                    if content is not None:
                        (self.root / graph).write_text(content)
                    result = await run(["--graph", graph, "--output", name + ".json"])
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), calls)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    self.assertEqual(
                        (self.root / (name + ".json")).is_file(), name == "render"
                    )
                    self.assertFalse((self.root / (name + ".tex")).exists())
                    with self.assertRaises(
                        (FileNotFoundError, json.JSONDecodeError, KeyError)
                    ):
                        cli(
                            self.original,
                            ["--graph", graph, "--output", "oracle-" + name + ".json"],
                        )
                for flag in ["--help", "--unknown"]:
                    result = await run([flag])
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 1)
                    self.assertEqual(result["calls"][0]["status"], "rejected")
                self.assertIn("Read an existing", self.document["description"])
                self.assertIn(
                    "Collect workflow graph evidence",
                    (self.root / "mcp-diagnostics.log").read_text(),
                )
                (self.root / "partial.md").mkdir()
                result = await run(["--output", "partial.json"])
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 4)
                self.assertEqual(
                    json.loads((self.root / "partial.json").read_text()),
                    self.original.catalogue(self.model),
                )
                self.assertFalse((self.root / "partial.tex").exists())
                (self.root / "late.tex").mkdir()
                result = await run(["--output", "late.json"])
                self.assertEqual(result["status"], "failed", result)
                self.assertTrue((self.root / "late.md").is_file())
                # Service authority is checked before writes or source parsing.
                result = await run(
                    [], context={"repository_root": str(self.root / "unconfigured")}
                )
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 1)
                with tempfile.TemporaryDirectory() as outside:
                    dest = Path(outside) / "denied.json"
                    result = await run(["--output", str(dest)])
                    self.assertEqual(result["status"], "failed", result)
                    self.assertFalse(dest.exists())
                    # Native CLI performs these writes then fails relative_to;
                    # the service intentionally narrows its configured authority.
                    with self.assertRaises(ValueError):
                        cli(self.original, ["--output", str(dest)])
                    self.assertTrue(dest.with_suffix(".tex").exists())
            except BaseException as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
