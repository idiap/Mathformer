#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Fixture-only generation/check through native ERFL, MCP and real Lunar PRISM.

No external provider, model or compiler occurs in this workflow. Use the real
ERFL and PRISM parser/checker/compiler/runtime with deterministic local inputs.
"""

from tempfile import gettempdir

import os
from pathlib import Path
import sys

LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
import unittest
import yaml

from run_reasoning_catalog_workflow_tests import CatalogTests, ROOT
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_docs_reasoning_flow_catalog_workflow/workflow.yaml"


class RenderTests(CatalogTests):
    def oracle(self):
        path = ROOT / "tests/mcp/fixtures/reasoning_catalog_render_original.py.txt"
        spec = importlib.util.spec_from_loader(
            "_render_oracle", SourceFileLoader("_render_oracle", str(path))
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        for name in (
            "REPO_ROOT",
            "REASONING_TYPES_FILE",
            "SKILL_HOOKS_FILE",
            "ACTION_REGISTRY_FILE",
            "ERFL_REGISTRY_FILE",
        ):
            setattr(module, name, getattr(self.native, name))
        return module

    def test_native_text_and_write_failure_equivalence(self):
        oracle = self.oracle()
        for check in (True, False, True):
            for json_output in (False, True):
                request = self.request(check=check, json_output=json_output)
                self.assertEqual(
                    self.invoke(self.native, request), self.invoke(oracle, request)
                )
        # Real second-file failure proves the first write survives with no rollback.
        self.native.DEFAULT_OUTPUT_FILE.unlink()
        self.native.DEFAULT_MATERIALIZATIONS_FILE.unlink()
        self.native.DEFAULT_MATERIALIZATIONS_FILE.mkdir()
        request = self.request()
        self.assertEqual(
            self.invoke(self.native, request), self.invoke(oracle, request)
        )
        self.assertTrue(self.native.DEFAULT_OUTPUT_FILE.is_file())
        self.assertIn("Is a directory", self.invoke(self.native, request)[1])

    def request(self, check=False, json_output=True):
        return dict(
            flows_dir=str(self.native.DEFAULT_FLOWS_DIR),
            output_file=str(self.native.DEFAULT_OUTPUT_FILE),
            materializations_file=str(self.native.DEFAULT_MATERIALIZATIONS_FILE),
            check=check,
            json=json_output,
        )

    def invoke(self, module, request):
        args = [
            "--flows-dir",
            request["flows_dir"],
            "--output-file",
            request["output_file"],
            "--materializations-file",
            request["materializations_file"],
        ]
        if request["check"]:
            args.append("--check")
        if request["json"]:
            args.append("--json")
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = module.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_docs_reasoning_flow_catalog_workflow")
        self.assertEqual(document["lifecycle"], "active")
        authored = (
            ROOT
            / "skills/control/workflow-contract-validator/references/reasoning-catalog-render.workflow.json"
        )
        self.assertEqual(document, json.loads(authored.read_text()))
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

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

        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "render",
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
                    return (
                        compile_workflow(
                            "mcp:render",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            inventory,
                        ),
                        assets,
                    )

                compiled, assets = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(request, doc=document, context=None):
                    c, a = compile(doc)
                    return await execute(
                        c,
                        a,
                        {"request": request, "context": context or self.context},
                        remote,
                        authorize,
                    )

                async def compare(request):
                    # Run oracle first, then workflow; resulting bytes and payload must match.
                    code, text, _ = self.invoke(self.oracle(), request)
                    expected = json.loads(text) if request["json"] else None
                    before = {
                        k: Path(request[k]).read_bytes()
                        for k in ("output_file", "materializations_file")
                        if Path(request[k]).is_file()
                    }
                    result = await run(request)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"]["exit_code"], code)
                    if expected is not None:
                        self.assertEqual(result["outputs"]["result"], expected)
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [
                            "mathformer_reasoning_catalog_render_" + s
                            for s in (
                                "construct",
                                "compare" if request["check"] else "generate",
                                "emit",
                            )
                        ],
                    )
                    for key, content in before.items():
                        self.assertEqual(Path(request[key]).read_bytes(), content)
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    return result["outputs"]["result"]

                # Absent documents, successful generation, synchronized check and text emission.
                self.assertFalse((await compare(self.request(check=True)))["ok"])
                self.assertTrue((await compare(self.request()))["ok"])
                self.assertTrue((await compare(self.request(check=True)))["ok"])
                await compare(self.request(json_output=False))
                self.native.DEFAULT_MATERIALIZATIONS_FILE.write_text("stale")
                stale = await compare(self.request(check=True))
                self.assertTrue(stale["semantic_synchronized"])
                self.assertFalse(stale["materializations_synchronized"])
                self.native.DEFAULT_OUTPUT_FILE.write_bytes(b"\xff")
                self.assertIn("error", await compare(self.request(check=True)))
                # Second write failure with a fresh first file; no rollback.
                self.native.DEFAULT_OUTPUT_FILE.unlink()
                self.native.DEFAULT_MATERIALIZATIONS_FILE.unlink()
                self.native.DEFAULT_MATERIALIZATIONS_FILE.mkdir()
                failed = await run(self.request())
                self.assertEqual(failed["status"], "accepted", failed)
                self.assertEqual(failed["outputs"]["exit_code"], 1)
                self.assertTrue(self.native.DEFAULT_OUTPUT_FILE.is_file())
                self.assertIn("error", failed["outputs"]["result"])
                await compare(self.request())
                self.native.DEFAULT_MATERIALIZATIONS_FILE.rmdir()
                # Budget stops before disposition, so no document can be written.
                self.native.DEFAULT_OUTPUT_FILE.unlink()
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 1
                exhausted = await run(self.request(), bounded)
                self.assertEqual(exhausted["status"], "failed", exhausted)
                self.assertIn("budget", str(exhausted).lower())
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed"))
                        for c in exhausted["calls"]
                    ),
                    1,
                )
                self.assertFalse(self.native.DEFAULT_OUTPUT_FILE.exists())
                # Native construction failure prevents writes in either branch.
                for path in self.native.DEFAULT_FLOWS_DIR.glob("*.rflow"):
                    path.write_text("invalid")
                for check in (False, True):
                    invalid = await compare(self.request(check=check))
                    self.assertFalse(invalid["ok"])
                    self.assertIn("error", invalid)
                    self.assertFalse(self.native.DEFAULT_OUTPUT_FILE.exists())
                rejected = await run(
                    self.request(), context={"repository_root": str(Path(gettempdir()))}
                )
                self.assertEqual(rejected["status"], "failed", rejected)
                self.assertIsNone(rejected["outputs"])
                self.assertEqual(len(rejected["calls"]), 1)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    # Importing the shared fixture class must not execute its unrelated workflow.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RenderTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(
        0 if result.wasSuccessful() and result.testsRun and not result.skipped else 1
    )
