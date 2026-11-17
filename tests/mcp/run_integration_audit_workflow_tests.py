#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native/MCP/Lunar integration, without production audit runs.

This audit has no model/provider or external compiler boundary. Fixtures are real
input files; Lunar's PRISM parser, checker, compiler and runtime run unmodified.
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
from contextlib import redirect_stdout, ExitStack
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
import audit_workflow_skill_integration as native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_workflow_skill_integration_audit_workflow/workflow.yaml"


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


class IntegrationAuditTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        tmp = tempfile.TemporaryDirectory(prefix="integration-audit-fixture-", dir=base)
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.output = self.root / "artifacts/workflow_graphs"
        self.graph = self.root / "graph.json"
        self.hooks = self.root / "hooks.yaml"
        self.hub = self.root / "hub.md"
        self.names = ["a-graph", "b-owner", "c-route", "d-runtime", "e-doc", "f-orphan"]
        for name in self.names:
            self.skill("skills/theme/" + name + "/SKILL.md", name)
        # Later project inventory wins the duplicate, preserving the native scan order.
        self.skill("proj_skills/duplicate/SKILL.md", "a-graph", "later description")
        self.graph.write_text(
            json.dumps(
                {
                    "skill_inventory": {"modeled": ["a-graph"]},
                    "summary": {"z": 1, "a": 2},
                    "stacks": {"ignored": {"ordered_hooks": [{"skill": "f-orphan"}]}},
                }
            )
        )
        self.hooks.write_text("""runtime_contract:
  shared_runtime_scripts:
    - skills/d-runtime/scripts/run.py
    - skills/a-graph/scripts/run.py
hooks:
  - id: graph
    owner_skill: a-graph
  - id: owner
    owner_skill: b-owner
  - id: duplicate
    owner_skill: b-owner
direct_request_routing:
  one: a-graph
  two: b-owner
  three: c-route
loop_contracts:
  - id: metadata_only
""")
        self.hub.write_text("""- [e-doc](before): uncategorized
### Group Count: `4`
- [a-graph](graph): desc
- [b-owner](owner): desc
- [c-route](route): desc
- [d-runtime](runtime): desc
""")
        path = ROOT / "tests/mcp/fixtures/integration_audit_original.py.txt"
        spec = importlib.util.spec_from_loader(
            "_integration_audit_oracle",
            SourceFileLoader("_integration_audit_oracle", str(path)),
        )
        self.oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.oracle)
        self.oracle.REPO_ROOT = self.root

    def skill(self, rel, name, description="description"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nname: {name}\ndescription: {description}\n---\n")

    def options(self, **extra):
        return {
            "graph": "graph.json",
            "hooks": "hooks.yaml",
            "hub": "hub.md",
            "json": True,
            **extra,
        }

    def cli(self, module, options):
        argv = ["audit"]
        for key, value in options.items():
            if key == "json":
                if value:
                    argv.append("--json")
            else:
                argv += ["--" + key.replace("_", "-"), str(value)]
        stream = io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(patch.object(sys, "argv", argv))
            stack.enter_context(patch.object(module, "REPO_ROOT", self.root))
            stack.enter_context(patch.object(module, "DEFAULT_OUTPUT_DIR", self.output))
            stack.enter_context(redirect_stdout(stream))
            code = module.main()
        return code, stream.getvalue(), self.files()

    def files(self):
        return {
            path.name: path.read_text()
            for path in sorted(self.output.glob("*"))
            if path.is_file()
        }

    def test_shared_source_equivalence_and_rendering(self):
        for json_mode in [True, False]:
            self.assertEqual(
                self.cli(native, self.options(json=json_mode)),
                self.cli(self.oracle, self.options(json=json_mode)),
            )
        # Absolute inputs are preserved, and source output path resolution is shared.
        absolute = self.options(
            graph=str(self.graph),
            hooks=str(self.hooks),
            hub=str(self.hub),
            output_dir=str(self.output),
        )
        self.assertEqual(self.cli(native, absolute), self.cli(self.oracle, absolute))
        self.assertEqual(
            native.resolve_paths({}, self.root),
            {
                "graph": str(
                    self.root / "artifacts/workflow_graphs/workflow_graphs.json"
                ),
                "hooks": str(self.root / "skills/SKILL_HOOKS.yaml"),
                "hub": str(self.root / "docs/architecture/AGENTIC_HUB.md"),
                "output_dir": str(self.output),
                "json": False,
            },
        )
        report = self.oracle.build_report(self.graph, self.hooks, self.hub)
        self.assertEqual(report["summary"]["available_skills"], 6)
        self.assertEqual(
            [r["status"] for r in report["classification"]["rows"]],
            [
                "visualized_in_graph",
                "workflow_hook_owner",
                "direct_route_only",
                "shared_runtime_only",
                "documented_agent_only",
                "no_integration_evidence",
            ],
        )
        self.assertEqual(
            report["classification"]["rows"][0]["evidence"],
            [
                "graph_modeled",
                "hook_owner",
                "direct_route",
                "shared_runtime_script",
                "agentic_hub_documented",
            ],
        )
        self.assertEqual(
            report["classification"]["rows"][0]["path"],
            "proj_skills/duplicate/SKILL.md",
        )
        self.assertEqual(
            report["classification"]["rows"][4]["category"], "Uncategorized"
        )
        self.assertEqual(report["hooks"]["owner_counts"]["b-owner"], 2)
        self.assertEqual(
            report["proposal"]["candidate_next_workflow_stacks"], ["metadata_only"]
        )
        for i in range(14):
            self.skill(f"skills/theme/z-{i:02}/SKILL.md", f"z-{i:02}")
        self.assertEqual(
            self.cli(native, self.options()), self.cli(self.oracle, self.options())
        )
        markdown = self.files()["workflow_skill_integration_audit.md"]
        self.assertIn("(+3 more)", markdown)
        self.assertIn("- `z-13`", markdown)

    def test_registered_tools_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_control_workflow_skill_integration_audit_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertIn(
            "scripts/audit_workflow_skill_integration.py",
            [r["path"] for r in document["provenance"]["sources"]],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "integration-audit",
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
                    "mcp:integration-audit",
                    workflow_documents([DESCRIPTOR], assets)[0],
                    inventory,
                )
                return compiled, assets

            workflow, assets = compile(document)
            self.assertTrue(workflow["runnable"], workflow["diagnostics"])
            self.assertTrue(workflow["runtime_source"])
            self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
            self.assertFalse(compile(document, [])[0]["runnable"])

            async def authorize():
                pass

            async def run(options=None, doc=document):
                c, a = compile(doc)
                self.assertTrue(c["runnable"], c["diagnostics"])
                return await execute(
                    c,
                    a,
                    {
                        "options": options or self.options(),
                        "context": {"repository_root": str(self.root)},
                    },
                    remote,
                    authorize,
                )

            for json_mode in [True, False]:
                expected = self.cli(self.oracle, self.options(json=json_mode))
                result = await run(self.options(json=json_mode))
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"]["report"],
                    json.loads(expected[2]["workflow_skill_integration_audit.json"]),
                )
                self.assertEqual(result["outputs"]["stdout"], expected[1])
                self.assertEqual(result["outputs"]["exit_code"], expected[0])
                self.assertEqual(self.files(), expected[2])
                self.assertTrue(result["outputs"]["result"]["ok"])
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [
                        "mathformer_integration_audit_" + s
                        for s in [
                            "resolve",
                            "inventory",
                            "graph",
                            "registries",
                            "classify",
                            "assemble",
                            "publish",
                        ]
                    ],
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
            # Empty modeled inventory falls back to finite stack hooks, with union/dedup.
            self.graph.write_text(
                json.dumps(
                    {
                        "skill_inventory": {"modeled": []},
                        "stacks": {
                            "one": {
                                "ordered_hooks": [
                                    {"skill": "a-graph"},
                                    {"skill": "b-owner"},
                                ]
                            },
                            "two": {
                                "ordered_hooks": [
                                    {"skill": "b-owner"},
                                    {"skill": "f-orphan"},
                                ]
                            },
                        },
                    }
                )
            )
            expected = self.cli(self.oracle, self.options())
            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(
                result["outputs"]["report"]["graph"],
                {"modeled": ["a-graph", "b-owner", "f-orphan"], "summary": {}},
            )
            self.assertEqual(
                result["outputs"]["report"]["summary"]["no_integration_evidence"], 0
            )
            self.assertIn("None.", self.files()["workflow_skill_integration_audit.md"])
            self.assertEqual(self.files(), expected[2])
            # Empty repositories are successful, not a retry/convergence condition.
            import shutil

            shutil.rmtree(self.root / "skills")
            shutil.rmtree(self.root / "proj_skills")
            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(
                result["outputs"]["report"]["summary"]["available_skills"], 0
            )
            self.assertEqual(
                result["outputs"]["report"]["classification"],
                {"rows": [], "buckets": {}},
            )
            self.assertEqual(
                result["outputs"]["report"],
                self.oracle.build_report(self.graph, self.hooks, self.hub),
            )
            # Malformed graph and missing registry stop exactly at their source step.
            self.graph.write_text("{")
            result = await run()
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 3)
            self.assertIsNone(result["outputs"])
            with self.assertRaises(json.JSONDecodeError):
                self.oracle.build_report(self.graph, self.hooks, self.hub)
            self.graph.write_text("{}")
            self.hooks.unlink()
            result = await run()
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 4)
            self.hooks.write_text("")
            # Native writes JSON first: failed Markdown leaves that JSON in place.
            md = self.output / "workflow_skill_integration_audit.md"
            md.unlink()
            md.mkdir()
            result = await run()
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 7)
            self.assertTrue(
                (self.output / "workflow_skill_integration_audit.json").is_file()
            )
            self.assertTrue(md.is_dir())
            md.rmdir()
            # No downstream publish on call-budget exhaustion; no silent success/retry.
            (self.output / "workflow_skill_integration_audit.json").unlink()
            bounded = deepcopy(document)
            bounded["policy"]["limits"]["max_operation_calls"] = 6
            result = await run(doc=bounded)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 6
            )
            self.assertIn("budget", str(result).lower())
            self.assertEqual(self.files(), {})
            # Native scans are finite, not artificially loop-bounded. Host wall budget is enforced.
            timed = deepcopy(document)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            c, a = compile(timed)

            async def pending_authority():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(
                    c,
                    a,
                    {
                        "options": self.options(),
                        "context": {"repository_root": str(self.root)},
                    },
                    remote,
                    pending_authority,
                )
            result = await run(self.options(output_dir="outside"))
            self.assertEqual(result["status"], "failed", result)
            self.assertFalse((self.root / "outside").exists())
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
