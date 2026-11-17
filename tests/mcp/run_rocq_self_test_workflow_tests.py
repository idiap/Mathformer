#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Execute the structural Rocq workflow through real MCP and Lunar PRISM."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT), str(ROOT / "scripts")]
import asyncio
from copy import deepcopy
import hashlib
import json
import shutil
import tempfile
import types
import unittest
import yaml
from backends.rocq.MathformerRocq import autoformalize as native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_rocq_self_test_workflow/workflow.yaml"
DEFAULTS = dict(
    manifest_file="tests/latex/wiki_level/manifest.json",
    output_dir="artifacts/rocq_self_test",
)


def stable(value):
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items() if k != "generated_at_utc"}
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


def fixtures(root):
    shutil.copytree(
        ROOT / "tests/latex/wiki_level",
        root / "tests/latex/wiki_level",
        dirs_exist_ok=True,
    )
    return root / "tests/latex/wiki_level"


def snapshot(doc):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in doc["provenance"]["sources"]
    ]


class RocqSelfTest(unittest.TestCase):
    def test_original_parity_and_state(self):
        original = types.ModuleType("_original_rocq_self_test")
        original.__file__ = str(ROOT / "backends/rocq/MathformerRocq/autoformalize.py")
        sys.modules[original.__name__] = original
        exec(
            compile(
                (
                    ROOT / "tests/mcp/fixtures/rocq_self_test_original.py.txt"
                ).read_text(),
                original.__file__,
                "exec",
            ),
            original.__dict__,
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "output"
            expected = original.self_test(out)
            files = {p.name: p.read_bytes() for p in out.glob("*.v")}
            actual = native.self_test(out)
            self.assertEqual(stable(actual), stable(expected))
            self.assertEqual({p.name: p.read_bytes() for p in out.glob("*.v")}, files)
            state = native.initialize_draft(native.DEFAULT_MANIFEST, out)
            states = []
            for i in range(5):
                previous = deepcopy(state)
                advanced = native.draft_next(state)
                states.append(advanced["done"])
                state = advanced["state"]
                self.assertEqual(len(previous["reports"]), i)
                self.assertEqual(state["cursor"], i + 1)
                self.assertEqual(len(state["reports"]), i + 1)
            self.assertEqual(states, [False] * 4 + [True])
            state = native.begin_reread(state)
            (
                out / native.CASE_TEMPLATES[native.DEFAULT_CASE_ORDER[0]].file_name
            ).write_text("Admitted.")
            for i in range(5):
                advanced = native.validate_next(state)
                state = advanced["state"]
                self.assertEqual(advanced["done"], i == 4)
            self.assertFalse(native.aggregate_self_test(state)["ok"])
            self.assertEqual(
                [v["ok"] for v in state["validations"]], [False] + [True] * 4
            )

    def test_lunar_mcp_paths(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["lifecycle"], "active")
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        async with manager.open(
            "rocq-self",
            StdioConfig(
                command=sys.executable,
                args=["-B", "tests/mcp/fixtures/rocq_self_test_server.py"],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            try:
                inventory = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile_doc(document, tools=inventory):
                    assets = snapshot(document)
                    workflow = compile_workflow(
                        "mcp:rocq-self",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools,
                    )
                    return workflow, assets

                workflow, assets = compile_doc(doc)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(doc["operations"]))
                self.assertFalse(compile_doc(doc, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(root, document=doc, authorization=authorize):
                    w, a = compile_doc(document)
                    self.assertTrue(w["runnable"], w["diagnostics"])
                    return await execute(
                        w,
                        a,
                        dict(defaults=DEFAULTS, repository_root=str(root)),
                        remote,
                        authorization,
                    )

                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp).resolve()
                    fixtures(root)
                    result = await run(root)
                    self.assertEqual(result["status"], "accepted", result)
                    report = result["outputs"]["result"]
                    self.assertTrue(report["ok"])
                    self.assertEqual(len(result["calls"]), 13)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["initialize"]
                        + ["draft_next"] * 5
                        + ["begin_reread"]
                        + ["validate_next"] * 5
                        + ["aggregate"],
                    )
                    self.assertEqual(
                        [r["case_id"] for r in report["draft"]["reports"]],
                        native.DEFAULT_CASE_ORDER,
                    )
                    self.assertEqual(len(report["validations"]), 5)
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    # Compare all fields to the native step implementation with the same explicit context.
                    state = native.initialize_draft(
                        root / DEFAULTS["manifest_file"],
                        root / DEFAULTS["output_dir"],
                        repository_root=root,
                    )
                    for _ in range(5):
                        state = native.draft_next(state)["state"]
                    state = native.begin_reread(state)
                    for _ in range(5):
                        state = native.validate_next(state)["state"]
                    self.assertEqual(
                        stable(report), stable(native.aggregate_self_test(state))
                    )
                    # False validation is data: both passes still visit all five cases.
                    manifest = json.loads(
                        (root / DEFAULTS["manifest_file"]).read_text()
                    )
                    case = next(
                        c
                        for c in manifest["cases"]
                        if c["id"] == native.DEFAULT_CASE_ORDER[0]
                    )
                    latex = root / case["latex_file"]
                    latex.write_text(
                        latex.read_text() + "\n\\begin{proof}Admitted\\end{proof}\n"
                    )
                    # Put the marker in the theorem environment, before existing content.
                    latex.write_text(
                        latex.read_text().replace(
                            "\\begin{theorem}", "\\begin{theorem} Admitted ", 1
                        )
                    )
                    result = await run(root)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertFalse(result["outputs"]["result"]["ok"])
                    self.assertEqual(len(result["calls"]), 13)
                    self.assertEqual(len(result["outputs"]["result"]["validations"]), 5)
                    fixtures(root)
                    # Native metadata errors abort the draft pass, with no retries or reread.
                    case = next(
                        c
                        for c in manifest["cases"]
                        if c["id"] == native.DEFAULT_CASE_ORDER[1]
                    )
                    latex = root / case["latex_file"]
                    latex.write_text(
                        latex.read_text().replace(case["id"], "wrong_case")
                    )
                    result = await run(root)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["initialize", "draft_next", "draft_next"],
                    )
                    fixtures(root)
                    # Delete the second output between passes, exercising reread IO failure.
                    checks = 0

                    async def remove_before_reread():
                        nonlocal checks
                        checks += 1
                        if checks == 16:
                            (
                                root
                                / DEFAULTS["output_dir"]
                                / native.CASE_TEMPLATES[
                                    native.DEFAULT_CASE_ORDER[1]
                                ].file_name
                            ).unlink()

                    result = await run(root, authorization=remove_before_reread)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["initialize"]
                        + ["draft_next"] * 5
                        + ["begin_reread"]
                        + ["validate_next"] * 2,
                    )
                    # Exercise real loop exhaustion with the same native five-item state.
                    bounded = deepcopy(doc)
                    bounded["flow"]["steps"][1]["max_iterations"] = 4
                    result = await run(root, bounded)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 5)
                    bounded = deepcopy(doc)
                    bounded["policy"]["limits"]["max_operation_calls"] = 3
                    result = await run(root, bounded)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertIn("budget", json.dumps(result).lower())
                    (root / DEFAULTS["manifest_file"]).unlink()
                    result = await run(root)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], ["initialize"]
                    )
            except Exception as error:
                failure = error
            else:
                failure = None
        if failure:
            raise failure
        self.assertFalse(manager.active)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(RocqSelfTest)
    )
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
