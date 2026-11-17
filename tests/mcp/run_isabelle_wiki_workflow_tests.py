#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native Isabelle wiki stages through registered MCP and real Lunar/PRISM."""

from tempfile import gettempdir

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
SITES = [str(path) for path in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)
BOUNDARY = ROOT / "tests/mcp/fixtures/isabelle_route_boundary"
# Child interpreters inherit only test compiler discovery/build substitution.
os.environ["PYTHONPATH"] = os.pathsep.join([str(BOUNDARY), *SITES])
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

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

from isabelle_wiki_tools import source, register_isabelle_wiki_tools, transport_state
from isabelle_wiki_runtime import isolate
from isabelle_route_tree import populate, stable, LEAF, GROUND, DRAFT, CHECK, LATEX
from mcp_connections.client import SessionManager
from mcp_connections.contracts import workflow_documents
from mcp_connections.models import StdioConfig
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_isabelle_wiki_workflow/workflow.yaml"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/isabelle-wiki.workflow.json"
)
ORDER = ["prepare", "ground", "draft", "check", "finalize"]


def original(root):
    loader = SourceFileLoader(
        "wiki_original", str(ROOT / "tests/mcp/fixtures/isabelle_wiki_original.py.txt")
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return isolate(module, root)


def snapshot(document):
    texts = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    texts[DESCRIPTOR] = json.dumps(document)
    return [
        {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
        for path, text in texts.items()
    ]


def scenario(
    root, name, *, compiler="success", ground_failure=False, draft_failure=False
):
    (root / ".isabelle-route-fixture.json").write_text(
        json.dumps({"compiler": compiler})
    )
    output = root / "artifacts/isabelle" / name
    output.mkdir(parents=True)
    if ground_failure:
        (output / "wiki_injective_composition.grounding.json").mkdir()
    if draft_failure:
        # Real filesystem failure at the native drafter write; no fake stage.
        (output / "session/AutoformalizedWikiInjectiveComposition.thy").mkdir(
            parents=True
        )
    return output


class WikiTests(unittest.TestCase):
    maxDiff = None

    def test_contract_identity_native_generator_and_digests(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(json.loads(AUTHORED.read_text()), document)
        spec = importlib.util.spec_from_file_location(
            "wiki_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(generator.isabelle_wiki_descriptor(), document)
        self.assertEqual(document["id"], "hub_isabelle_wiki_workflow")
        self.assertEqual(document["aliases"], ["isabelle:wiki"])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            document["policy"]["failure"]["retry"],
            {"max_attempts": 1, "retryable_codes": []},
        )
        self.assertEqual(
            [step["operation"] for step in document["flow"]["steps"]], ORDER
        )
        self.assertTrue(
            any(
                row["path"] == LEAF and row["selector"] == "run_case"
                for row in document["provenance"]["sources"]
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

    def test_native_process_errors_and_timeout_capture(self):
        # Actual process boundary, no model or theorem prover is started.
        native = source()
        with self.assertRaises(FileNotFoundError):
            native.run_command(
                [
                    str(
                        Path(gettempdir())
                        / "mathformer-test-fixtures/nonexistent/mathformer-fixture-executable"
                    )
                ],
                timeout_sec=60,
            )
        result = native.run_command(
            [sys.executable, "-c", "import time; time.sleep(1)"], timeout_sec=0
        )
        self.assertTrue(result["timeout"])
        self.assertFalse(result["ok"])
        self.assertIsNone(result["returncode"])
        self.assertEqual(result["stderr"], "timeout after 0s")
        # Python preserves partial output as bytes even with text=True.
        partial = native.run_command(
            [
                sys.executable,
                "-c",
                "import sys,time;sys.stdout.write('{\"ok\":true}');sys.stdout.flush();time.sleep(10)",
            ],
            timeout_sec=1,
        )
        self.assertEqual(partial["stdout"], b'{"ok":true}')
        state = {"report": {"steps": {"grounding": partial}}}
        wire = transport_state(state)
        json.dumps(wire)
        self.assertEqual(transport_state(wire, unpack=True), state)
        self.assertIsInstance(state["report"]["steps"]["grounding"]["stdout"], bytes)
        self.assertIsNone(native.parse_json("invalid-json"))
        self.assertEqual(native.parse_json(b'{"ok": true}'), {"ok": True})
        with self.assertRaises(UnicodeDecodeError):
            native.parse_json(b"\xff")

    def test_service_admission_at_every_writing_port(self):
        async def checks():
            from mcp.server.fastmcp import FastMCP

            with tempfile.TemporaryDirectory() as directory:
                state = {
                    "output_dir": directory,
                    "session_dir": directory
                    + str(Path(gettempdir()) / "mathformer-test-fixtures/session"),
                    "theory_file": directory
                    + str(
                        Path(gettempdir()) / "mathformer-test-fixtures/session/T.thy"
                    ),
                    "latex_file": str(ROOT / LATEX),
                    "report": {},
                }

                def deny():
                    raise ValueError("read-only")

                for authorize, allowed, message in [
                    (deny, lambda p: True, "read-only"),
                    (lambda: None, lambda p: False, "outside configured service roots"),
                ]:
                    mcp = FastMCP("wiki-admission")
                    register_isabelle_wiki_tools(mcp, authorize, allowed)
                    for name, args in [
                        (
                            "prepare",
                            {
                                "output_dir": directory
                                + str(
                                    Path(gettempdir())
                                    / "mathformer-test-fixtures/output"
                                )
                            },
                        ),
                        ("ground", {"state": state}),
                        ("draft", {"state": state}),
                        ("execute", {"state": state, "timeout_sec": 240}),
                    ]:
                        with self.assertRaisesRegex(Exception, message):
                            await mcp.call_tool(
                                "mathformer_isabelle_wiki_" + name, args
                            )
                self.assertEqual(list(Path(directory).iterdir()), [])

        asyncio.run(checks())

    def test_registered_tools_lunar_execution_and_original_equivalence(self):
        asyncio.run(self.connected())

    async def connected(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        with tempfile.TemporaryDirectory(prefix="isabelle-wiki-fixture-") as directory:
            root = Path(directory).resolve()
            populate(root, ROOT)
            # More than the native match/snippet caps: test traversal accumulation.
            for i in range(10):
                (root / f"library/Fixture{i:02}.thy").write_text(
                    ("lemma injective_composition: True by simp\n") * (i + 5)
                )
            manager = SessionManager()
            async with manager.open(
                "wiki",
                StdioConfig(
                    command=sys.executable,
                    args=[
                        str(ROOT / "tests/mcp/fixtures/isabelle_wiki_runtime.py"),
                        str(root),
                    ],
                    cwd=str(root),
                ),
                {
                    "PYTHONPATH": os.environ["PYTHONPATH"],
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            ) as remote:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    assets = snapshot(doc)
                    workflow = workflow_documents([DESCRIPTOR], assets)[0]
                    self.assertTrue(workflow["validation"]["valid"], workflow)
                    compiled = compile_workflow(
                        "mcp:wiki", workflow, tools if inventory is None else inventory
                    )
                    return compiled, assets

                compiled, assets = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertEqual(compiled["runtime_status"], "ready")
                self.assertTrue(compiled["prism_source"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(ORDER))
                for operation in ORDER:
                    missing = [
                        t
                        for t in tools
                        if t["name"]
                        != document["operations"][operation]["execution"]["binding"][
                            "target"
                        ]
                    ]
                    self.assertFalse(compile(document, missing)[0]["runnable"])

                async def authorize():
                    pass

                async def run(output, changed=None):
                    graph, received = (
                        compile(changed) if changed else (compiled, assets)
                    )
                    return await execute(
                        graph,
                        received,
                        {"output_dir": str(output), "timeout_sec": 240},
                        remote,
                        authorize,
                    )

                scenarios = [
                    ({}, True),
                    ({"compiler": "reject"}, False),
                    ({"compiler": "missing"}, False),
                    ({"compiler": "timeout"}, False),
                    ({"compiler": "crash"}, False),
                    ({"compiler": "placeholder"}, False),
                    ({"compiler": "exit-disagrees"}, True),
                    ({"compiler": "outer-timeout-empty"}, False),
                    ({"ground_failure": True}, False),
                    ({"draft_failure": True}, False),
                ]
                for index, (options, expected) in enumerate(scenarios):
                    with self.subTest(options=options):
                        output = scenario(root, str(index), **options)
                        result = await run(output)
                        # Source report ok=false is data, not a rejected tool call.
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], ORDER
                        )
                        report = result["outputs"]["report"]
                        self.assertEqual(report["ok"], expected)
                        self.assertEqual(
                            set(report["steps"]), {"grounding", "draft", "execution"}
                        )
                        self.assertEqual(
                            report["theory_file"],
                            f"artifacts/isabelle/{index}str(Path(gettempdir()) / 'mathformer-test-fixtures/session/AutoformalizedWikiInjectiveComposition.thy')",
                        )
                        self.assertFalse(
                            (output / "wiki_injective_composition.e2e.json").exists()
                        )
                        # main owns the terminal file/exit status outside run_case's graph.
                        oracle = original(root)
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = oracle.main(["--output-dir", str(output), "--json"])
                        saved = json.loads(
                            (output / "wiki_injective_composition.e2e.json").read_text()
                        )
                        self.assertEqual(code, 0 if expected else 1)
                        self.assertEqual(json.loads(stream.getvalue()), saved)
                        self.assertEqual(stable(report), stable(saved))
                        (output / "wiki_injective_composition.e2e.json").unlink()

                        if not options.get("ground_failure"):
                            grounding = report["steps"]["grounding"]["parsed"]
                            self.assertEqual(grounding["theory_count"], 11)
                            self.assertEqual(
                                [row["concept"] for row in grounding["concepts"]],
                                ["injective", "composition"],
                            )
                            for row in grounding["concepts"]:
                                self.assertEqual(row["match_count"], 11)
                                self.assertEqual(len(row["matches"]), 8)
                                self.assertEqual(len(row["matches"][0]["snippets"]), 4)
                                self.assertEqual(row["matches"][0]["score"], 14 * 4)
                                self.assertEqual(
                                    row["proposed_imports"],
                                    ["Fixture09", "Fixture08", "Fixture07"],
                                )
                        if not options.get("draft_failure"):
                            draft = report["steps"]["draft"]["parsed"]
                            self.assertTrue(report["steps"]["draft"]["ok"])
                            self.assertEqual(draft["style"], "isar_direct")
                            theory = (
                                output
                                / "session/AutoformalizedWikiInjectiveComposition.thy"
                            )
                            self.assertIn(
                                'shows "inj (g \\<circ> f)"', theory.read_text()
                            )
                            if not options.get("compiler", "").startswith(
                                "outer-timeout"
                            ):
                                self.assertIn(
                                    "session Mathformer_Isabelle = HOL",
                                    (output / "session/ROOT").read_text(),
                                )
                        execution = report["steps"]["execution"]
                        if options.get("compiler") == "exit-disagrees":
                            self.assertEqual(execution["returncode"], 9)
                            self.assertTrue(execution["parsed"]["ok"])
                        if options.get("compiler") == "timeout":
                            self.assertTrue(execution["parsed"]["timeout"])
                            self.assertEqual(
                                execution["parsed"]["stdout"], "partial build"
                            )
                        if options.get("compiler") == "placeholder":
                            self.assertTrue(execution["parsed"]["process_ok"])
                            self.assertEqual(
                                execution["parsed"]["placeholder_report"]["markers"],
                                ["sorry"],
                            )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])

                for mode, stopped in [
                    ("outer-timeout-bytes", ORDER),
                    ("outer-timeout-invalid", ORDER[:-1]),
                ]:
                    output = scenario(root, mode, compiler=mode)
                    result = await run(output)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual([c["operation"] for c in result["calls"]], stopped)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    with self.assertRaises(
                        TypeError if mode.endswith("bytes") else UnicodeDecodeError
                    ):
                        original(root).main(["--output-dir", str(output), "--json"])
                    self.assertFalse(
                        (output / "wiki_injective_composition.e2e.json").exists()
                    )

                # Source returns false for parsed truthy values; execution exit is ignored.
                state = source().prepare_case(output_dir=root / "predicate")
                for parsed, expected in [
                    ({"ok": True}, True),
                    ({"ok": 1}, False),
                    ({"ok": "true"}, False),
                    (None, False),
                    ([], False),
                ]:
                    state["report"]["steps"] = {
                        "grounding": {"ok": True},
                        "draft": {"ok": True},
                        "execution": {"ok": False, "parsed": parsed},
                    }
                    response = await remote.call(
                        "mathformer_isabelle_wiki_finalize", {"state": state}
                    )
                    self.assertEqual(response["report"]["ok"], expected)

                # A real preparation exception aborts with no later transport call.
                blocked = root / "blocked"
                blocked.write_text("not a directory")
                result = await run(blocked)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual([c["operation"] for c in result["calls"]], ["prepare"])

                for limit in [1, 3, 4]:
                    output = scenario(root, f"budget-{limit}")
                    changed = deepcopy(document)
                    changed["policy"]["limits"]["max_operation_calls"] = limit
                    result = await run(output, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        limit,
                    )
                    self.assertEqual(
                        [c["operation"] for c in result["calls"][:limit]], ORDER[:limit]
                    )

                calls = [
                    json.loads(line)
                    for line in (root / "artifacts/isabelle/fixture-calls.jsonl")
                    .read_text()
                    .splitlines()
                ]
                first = calls[:4]
                self.assertEqual(
                    [row["argv"][1] for row in first[:3]], [GROUND, DRAFT, CHECK]
                )
                self.assertEqual([row["timeout"] for row in first], [60, 60, 255, 240])
                self.assertEqual(
                    first[0]["argv"][2:6],
                    ["--concept", "injective", "--concept", "composition"],
                )
                self.assertEqual(
                    first[2]["argv"][-3:], ["--timeout-sec", "240", "--json"]
                )
                self.assertEqual(
                    first[3]["argv"][:3],
                    [
                        str(
                            Path(gettempdir())
                            / "mathformer-test-fixtures/fixture/isabelle"
                        ),
                        "build",
                        "-D",
                    ],
                )
            self.assertFalse(manager.active)


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
