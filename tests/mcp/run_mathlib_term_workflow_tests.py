#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native ontology/compiler fixtures through real MCP and PRISM.
No external provider/compiler boundary exists in this workflow; none is mocked.
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
from mathlib_term_tools import source, SOURCE
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathlib_term_annotations_workflow/workflow.yaml"


def oracle():
    loader = SourceFileLoader(
        "terms_oracle",
        str(ROOT / "tests/mcp/fixtures/term_annotations_original.py.txt"),
    )
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    return module


def assets(document):
    texts = {DESCRIPTOR: json.dumps(document)}
    texts.update(
        {
            r["path"]: (ROOT / r["path"]).read_text()
            for r in document["provenance"]["sources"]
        }
    )
    return [
        {
            "path": p,
            "content": s,
            "encoding": "text",
            "sha256": hashlib.sha256(s.encode()).hexdigest(),
        }
        for p, s in texts.items()
    ]


class TermsTests(unittest.TestCase):
    def test_original_and_annotation_branches(self):
        n = source()
        old = oracle()
        with tempfile.TemporaryDirectory() as directory:
            nout = n.SELF_TEST_OUTPUT
            oout = old.SELF_TEST_OUTPUT
            try:
                n.SELF_TEST_OUTPUT = Path(directory) / "new.json"
                old.SELF_TEST_OUTPUT = Path(directory) / "old.json"
                for module in (n, old):
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        code = module.main(["--self-test", "--json"])
                    self.assertEqual(code, 0)
                    if module is n:
                        first = stream.getvalue()
                    else:
                        self.assertEqual(stream.getvalue(), first)
                self.assertEqual(
                    n.SELF_TEST_OUTPUT.read_bytes(), old.SELF_TEST_OUTPUT.read_bytes()
                )
            finally:
                n.SELF_TEST_OUTPUT = nout
                old.SELF_TEST_OUTPUT = oout
            # Real ontology fixtures cover ties, negative scores and unique winners.
            for text in [
                "compact",
                "compact operator open cover finite subcover",
                "A convex set in a real vector space",
                "",
                "compact compact",
            ]:
                actual = n.annotate_text(text)
                expected = old.annotate_text(text)
                actual.pop("generated_at_utc")
                expected.pop("generated_at_utc")
                self.assertEqual(actual, expected)
            profile_path = Path(directory) / "ontology.json"

            def annotate(concepts, text="token"):
                profile_path.write_text(json.dumps({"concepts": concepts}))
                actual = n.annotate_text(text, profile_path=profile_path)
                expected = old.annotate_text(text, profile_path=profile_path)
                actual.pop("generated_at_utc")
                expected.pop("generated_at_utc")
                self.assertEqual(actual, expected)
                return actual

            a = {
                "concept_id": "a",
                "surface_terms": ["token", "token"],
                "domain_tags": ["test"],
            }
            b = {**a, "concept_id": "b"}
            tie = annotate([b, a])
            row = tie["annotations"][0]
            self.assertEqual(row["verification_state"], "ambiguous")
            self.assertIsNone(row["selected_concept_id"])
            self.assertEqual(
                [r["concept_id"] for r in row["normalized_candidates"]], ["a", "b"]
            )
            self.assertEqual(len(tie["gap_ledger"]), 1)
            gap = annotate([{**a, "negative_context_clues": ["token"]}])
            self.assertEqual(gap["annotations"][0]["verification_state"], "gap")
            self.assertIsNone(gap["annotations"][0]["selected_concept_id"])
            high = annotate(
                [{**a, "required_context_clues": ["clue", "token"]}], "clue token token"
            )
            self.assertEqual(high["annotation_count"], 2)
            self.assertEqual(high["gap_ledger"], [])
            self.assertEqual(high["annotations"][0]["confidence"], "high")
            self.assertEqual(high["annotations"][0]["selected_concept_id"], "a")
            self.assertEqual(annotate([], "token")["annotation_count"], 0)
            report = {
                "annotations": [
                    {
                        "selected_concept_id": None,
                        "normalized_candidates": [{"concept_id": "bad"}],
                    }
                ],
                "annotation_count": 1,
            }
            row = n.check_fixture(
                {
                    "id": "x",
                    "expect_concept": "bad",
                    "expect_any": ["absent"],
                    "forbid_first": "bad",
                },
                report,
            )
            self.assertFalse(row["ok"])
            state = n.initialize_fixture_state()
            for case in n.SELF_TEST_CASES:
                state, done = n.check_append(
                    state, case, {"annotations": [], "annotation_count": 0}
                )
                self.assertEqual(done, state["index"] == 5)
            self.assertEqual(len(state["results"]), 5)
            self.assertFalse(
                n.write_self_test(state["results"], Path(directory) / "failure.json")[
                    "ok"
                ]
            )
            with self.assertRaises(IndexError):
                n.select_fixture(state)
            with self.assertRaises(FileNotFoundError):
                n.annotate_text("x", profile_path=Path(directory) / "missing")

    def test_real_mcp_compile_execute(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_mathlib_term_annotations_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertIn(SOURCE, [r["path"] for r in document["provenance"]["sources"]])
        # The repository generator keeps the authored graph on regeneration.
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("terms_generator", path)
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(
            next(d for d in generator.inventory() if d["id"] == document["id"]),
            document,
        )
        self.assertIn(
            "register_mathlib_term_tools(mcp, _analysis_write_policy)",
            (ROOT / "scripts/mcp_server.py").read_text(),
        )

        for r in document["provenance"]["sources"]:
            self.assertEqual(
                r["digest"],
                "sha256:" + hashlib.sha256((ROOT / r["path"]).read_bytes()).hexdigest(),
            )
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="term-fixture-", dir=base) as temporary:
            directory = Path(temporary)
            manager = SessionManager()
            server = 'import sys;sys.path.insert(0,"scripts");from mcp.server.fastmcp import FastMCP;from mathlib_term_tools import register_mathlib_term_tools;mcp=FastMCP("terms");register_mathlib_term_tools(mcp);mcp.run(transport="stdio")'
            async with manager.open(
                "terms",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    a = assets(doc)
                    w = compile_workflow(
                        "mcp:terms",
                        workflow_documents([DESCRIPTOR], a)[0],
                        tools if inventory is None else inventory,
                    )
                    return w, a

                w, a = compile(document)
                self.assertTrue(w["runnable"], w["diagnostics"])
                self.assertTrue(w["runtime_source"])
                self.assertEqual(set(w["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(doc, path):
                    w, a = compile(doc)
                    self.assertTrue(w["runnable"], w["diagnostics"])
                    return await execute(w, a, {"output": str(path)}, remote, authorize)

                result = await run(document, directory / "report.json")
                self.assertEqual(result["status"], "accepted", result)
                report = json.loads((directory / "report.json").read_text())
                self.assertTrue(report["ok"])
                self.assertEqual(len(report["results"]), 5)
                self.assertEqual(
                    result["outputs"],
                    {
                        "report": report,
                        "exit_code": 0,
                        "stdout": json.dumps(report, indent=2, sort_keys=True) + "\n",
                    },
                )
                self.assertEqual(len(result["calls"]), 18)
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    ["mathformer_terms_initialize"]
                    + [
                        "mathformer_terms_" + s
                        for _ in range(5)
                        for s in ("select_fixture", "annotate", "check_append")
                    ]
                    + ["mathformer_terms_write_report", "mathformer_terms_emit"],
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
                # Deterministic compiler input fixtures change only graph constants;
                # every source step and MCP binding remains real.
                failed_doc = deepcopy(document)
                body = failed_doc["flow"]["steps"][1]["body"]["steps"]
                body[1]["arguments"]["fixture"] = {
                    "literal": {"id": "empty", "text": ""}
                }
                failed = await run(failed_doc, directory / "failed.json")
                self.assertEqual(failed["status"], "accepted", failed)
                self.assertEqual(failed["outputs"]["exit_code"], 1)
                self.assertFalse(failed["outputs"]["report"]["ok"])
                self.assertEqual(len(failed["outputs"]["report"]["results"]), 5)
                self.assertEqual(len(failed["calls"]), 18)
                bounded = deepcopy(document)
                bounded["flow"]["steps"][1]["max_iterations"] = 4
                failed = await run(bounded, directory / "exhausted.json")
                self.assertEqual(failed["status"], "failed", failed)
                self.assertFalse((directory / "exhausted.json").exists())
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 3
                failed = await run(bounded, directory / "budget.json")
                self.assertEqual(failed["status"], "failed")
                self.assertIn("budget", str(failed).lower())
                # Native filesystem exception propagates, no emit or retry.
                blocker = directory / "blocker"
                blocker.write_text("file")
                failed = await run(document, blocker / "report.json")
                self.assertEqual(failed["status"], "failed")
                self.assertIsNone(failed["outputs"])
                self.assertEqual(len(failed["calls"]), 17)
                failed = await run(
                    document, str(Path(gettempdir()) / "outside-term-policy.json")
                )
                self.assertEqual(failed["status"], "failed")
            self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
