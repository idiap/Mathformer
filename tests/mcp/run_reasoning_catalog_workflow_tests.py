#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic filesystem fixtures through real native, MCP and PRISM paths.

This workflow has no model/provider or external compiler boundary. The actual
ERFL parser/validator and Lunar PRISM compiler/runtime execute without substitutes.
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
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import shutil
import tempfile
import unittest
import yaml
from reasoning_catalog_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_reasoning_flow_catalog_workflow/workflow.yaml"


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


class CatalogTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(exist_ok=True, parents=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="reasoning-fixture-", dir=base)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.context = {"repository_root": str(self.root)}
        self.native = source(self.context)
        # Small real canonical profile; do not run against production catalogues.
        profile = ROOT / "examples/reasoning_flows/deductive_reasoning.rflow"
        if not profile.exists():
            profile = sorted((ROOT / "examples/reasoning_flows").glob("*.rflow"))[0]
        from reasoning_catalog_tools import source as load

        production = load({"repository_root": str(ROOT)})
        styles = production.parse_reasoning_styles(production.REASONING_TYPES_FILE)
        style = next(s for s in styles if s.style_id == profile.stem)
        for path in [
            self.native.ERFL_REGISTRY_FILE,
            self.native.REASONING_TYPES_FILE,
            self.native.SKILL_HOOKS_FILE,
            self.native.ACTION_REGISTRY_FILE,
            self.native.DEFAULT_OUTPUT_FILE,
            self.native.DEFAULT_FLOWS_DIR / "placeholder",
        ]:
            path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(production.ERFL_REGISTRY_FILE, self.native.ERFL_REGISTRY_FILE)
        shutil.copyfile(profile, self.native.DEFAULT_FLOWS_DIR / profile.name)
        rows = [
            "reasoning_styles:",
            f"  - id: {style.style_id}",
            f"    goal: {style.goal}",
            "    control_skills:",
        ]
        rows += [f"      - {x}" for x in style.control_skills]
        rows += ["    stages:"]
        for stage in style.stages:
            rows += [
                f"      - primitive: {stage.primitive}",
                "        skill_options:",
            ] + [f"          - {x}" for x in stage.skill_options]
        self.native.REASONING_TYPES_FILE.write_text("\n".join(rows) + "\n")
        self.native.SKILL_HOOKS_FILE.write_text(
            "loop_contracts:\n  - id: fixture_loop\n    required_hooks:\n      - fixture_hook\ndirect_request_routing:\n"
        )
        self.native.ACTION_REGISTRY_FILE.write_text("")

    def oracle(self):
        path = ROOT / "tests/mcp/fixtures/reasoning_catalog_original.py.txt"
        spec = importlib.util.spec_from_loader(
            "_catalog_oracle", SourceFileLoader("_catalog_oracle", str(path))
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

    def cli(self, module, extra=()):
        stream = io.StringIO()
        args = [
            "--flows-dir",
            str(self.native.DEFAULT_FLOWS_DIR),
            "--output-file",
            str(self.native.DEFAULT_OUTPUT_FILE),
            "--materializations-file",
            str(self.native.DEFAULT_MATERIALIZATIONS_FILE),
            "--json",
            *extra,
        ]
        with redirect_stdout(stream), redirect_stderr(io.StringIO()):
            code = module.main(args)
        return code, stream.getvalue()

    def test_native_equivalence_and_finite_input_exhaustion(self):
        oracle = self.oracle()
        self.assertEqual(
            self.cli(self.native, ["--check"]), self.cli(oracle, ["--check"])
        )
        self.assertEqual(self.cli(self.native), self.cli(oracle))
        self.assertEqual(
            self.cli(self.native, ["--check"]), self.cli(oracle, ["--check"])
        )
        construction = self.native.construct_catalog(self.native.DEFAULT_FLOWS_DIR)
        self.assertTrue(construction["ok"], construction)
        self.assertEqual(construction["metadata"]["profile_count"], 1)
        self.assertEqual(construction["metadata"]["loop_contract_count"], 1)
        self.assertEqual(
            construction["metadata"]["sha256"],
            hashlib.sha256(construction["semantic"].encode()).hexdigest(),
        )
        # Extra profile fails at correspondence gate, before malformed text parsing.
        (self.native.DEFAULT_FLOWS_DIR / "extra.rflow").write_text("invalid")
        result = self.native.construct_catalog(self.native.DEFAULT_FLOWS_DIR)
        self.assertIn("extra_profiles", result["error"])
        self.assertEqual(
            self.cli(self.native, ["--check"]), self.cli(oracle, ["--check"])
        )
        for p in self.native.DEFAULT_FLOWS_DIR.glob("*.rflow"):
            p.unlink()
        self.assertIn(
            "missing_profiles",
            self.native.construct_catalog(self.native.DEFAULT_FLOWS_DIR)["error"],
        )
        self.native.REASONING_TYPES_FILE.write_text("reasoning_styles:\n")
        self.assertIn(
            "No reasoning styles",
            self.native.construct_catalog(self.native.DEFAULT_FLOWS_DIR)["error"],
        )

    def test_registered_tools_and_lunar_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_control_reasoning_flow_catalog_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "reasoning",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=tools):
                assets = snapshot(doc)
                compiled = compile_workflow(
                    "mcp:reasoning",
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

            async def run(doc=document, context=None):
                c, a = compile(doc)
                return await execute(
                    c, a, {"context": context or self.context}, remote, authorize
                )

            def expected():
                code, text = self.cli(self.native, ["--check"])
                return {"result": {"payload": json.loads(text), "exit_code": code}}

            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(result["outputs"], expected())
            self.assertFalse(result["outputs"]["result"]["payload"]["ok"])
            self.assertEqual(
                [c["tool"] for c in result["calls"]],
                [
                    "mathformer_reasoning_catalog_" + s
                    for s in ("construct", "compare", "emit")
                ],
            )
            self.assertTrue(result["runtime"]["effect_records"])
            self.assertTrue(result["replay_artifacts"])
            # Write only fixture documents via real standalone renderer.
            self.cli(self.native)
            result = await run()
            self.assertEqual(result["outputs"], expected())
            self.assertTrue(result["outputs"]["result"]["payload"]["ok"])
            self.native.DEFAULT_MATERIALIZATIONS_FILE.write_text("stale")
            result = await run()
            self.assertEqual(result["outputs"], expected())
            self.assertTrue(
                result["outputs"]["result"]["payload"]["semantic_synchronized"]
            )
            self.assertFalse(
                result["outputs"]["result"]["payload"]["materializations_synchronized"]
            )
            # Ordered read exception drops metadata and synchronization flags.
            self.native.DEFAULT_OUTPUT_FILE.write_bytes(b"\xff")
            result = await run()
            self.assertEqual(result["outputs"], expected())
            self.assertIn("error", result["outputs"]["result"]["payload"])
            self.assertNotIn("profile_count", result["outputs"]["result"]["payload"])
            # Native parser failure selects failure conversion, never comparison.
            for path in self.native.DEFAULT_FLOWS_DIR.glob("*.rflow"):
                path.write_text("invalid")
            result = await run()
            self.assertEqual(result["outputs"], expected())
            self.assertEqual(
                [c["tool"] for c in result["calls"]],
                [
                    "mathformer_reasoning_catalog_" + s
                    for s in ("construct", "construction_failure", "emit")
                ],
            )
            # Budget exhaustion stops before the third transport call, without retry.
            bounded = deepcopy(document)
            bounded["policy"]["limits"]["max_operation_calls"] = 2
            result = await run(bounded)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 2
            )
            self.assertIn("budget", str(result).lower())
            # Invalid repository context is a binding failure, not native validation data.
            result = await run(context={"repository_root": str(Path(gettempdir()))})
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(len(result["calls"]), 1)
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
