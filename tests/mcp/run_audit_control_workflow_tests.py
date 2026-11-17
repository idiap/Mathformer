#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native audit parity and real MCP/Lunar/PRISM execution on filesystem fixtures.

No model/provider or external compiler occurs in this workflow. The real PRISM
parser, checker, compiler and runtime are used without substitutes.
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
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import tempfile
import unittest
import yaml
import mathformer as hub
from workflow_runtime.audit_control_tools import native_registry
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_hub_audit_workflow/workflow.yaml"
STEPS = [
    "registered",
    "matrix",
    "hooks",
    "pack_sources",
    "inspect_paths",
    "dependencies",
    "report",
]


def oracle():
    path = ROOT / "tests/mcp/fixtures/audit_control_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "audit_oracle", SourceFileLoader("audit_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in document["provenance"]["sources"]
    ]


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.original = oracle()
        self.original.REPO_ROOT = self.root

    def file(self, name, text=""):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def expected(self, registry):
        value = self.original.audit_control(native_registry(registry))
        self.assertEqual(hub.audit_control(native_registry(registry), self.root), value)
        return value

    def matrix(self, text):
        return self.file("tests/test_program/run_comprehensive_tests.py", text)

    def test_native_inventory_order_fallback_and_failures(self):
        registry = {
            "one": {
                "action_id": "different",
                "command": [
                    "python",
                    "scripts/a.py",
                    "--skip.py",
                    "scripts/gone.py",
                    "scripts/a.py",
                ],
                "depends_on": ["missing", "missing", "one"],
            }
        }
        self.file("scripts/a.py")
        self.file("scripts/z.py")
        self.file("tests/fixtures/skip.py")
        self.file("tests/__init__.py")
        self.file("benchmarks/deep/check.py")
        self.file("paper_skills/one/scripts/check.py")
        self.file("examples/demo.py")
        self.file("scripts/mathformer.py")
        self.file("skills/a/b/scripts/check.py")
        self.file(
            "skills/SKILL_HOOKS.yaml",
            "skills/a/b/scripts/check.py skills/a/b/scripts/absent.py",
        )
        self.matrix(
            "def load_matrix():\n    return [{'command':['python','examples/demo.py']}]\n"
        )
        report = self.expected(registry)
        self.assertFalse(report["ok"])
        self.assertEqual(report["registry_script_count"], 1)
        self.assertEqual(report["direct_registered_missing_paths"], [])
        self.assertEqual(
            report["dependency_errors"],
            [{"action_id": "different", "missing_dependency": "missing"}] * 2,
        )
        self.assertEqual(
            report["uncontrolled_entrypoints"],
            [
                "benchmarks/deep/check.py",
                "paper_skills/one/scripts/check.py",
                "scripts/z.py",
                "tests/test_program/run_comprehensive_tests.py",
            ],
        )
        self.assertEqual(report["controlled_count"], 4)
        self.matrix("other = 1\n")
        self.assertEqual(self.expected(registry)["matrix_script_count"], 0)
        for text in [
            'raise RuntimeError("import failure")\n',
            'def load_matrix():\n    raise RuntimeError("load failure")\n',
        ]:
            self.matrix(text)
            for call in [
                lambda: self.original.audit_control(native_registry(registry)),
                lambda: hub.audit_control(native_registry(registry), self.root),
            ]:
                with self.assertRaises(RuntimeError):
                    call()
        (self.root / "tests/test_program/run_comprehensive_tests.py").unlink()
        (self.root / "skills/SKILL_HOOKS.yaml").unlink()
        self.assertEqual(self.expected({})["skill_hook_script_count"], 0)

    def test_registered_tools_compile_and_execute(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_hub_audit_workflow")
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
            "audit",
            StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=["-B", "-c", server],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    received = assets(doc)
                    workflow = workflow_documents([DESCRIPTOR], received)[0]
                    qualified = compile_workflow(
                        "mcp:audit", workflow, tools if inventory is None else inventory
                    )
                    return qualified, received

                workflow, received = compile(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(STEPS))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def allow():
                    pass

                async def run(registry, doc=None):
                    w, a = compile(doc) if doc else (workflow, received)
                    return await execute(
                        w,
                        a,
                        {"registry": registry, "repository_root": str(self.root)},
                        remote,
                        allow,
                    )

                async def check(registry):
                    result = await run(registry)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"], {"result": self.expected(registry)}
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_audit_" + s for s in STEPS],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    return result

                empty = await check({})
                self.assertTrue(empty["outputs"]["result"]["ok"])
                self.file("scripts/registered.py")
                registry = {
                    "first": {
                        "action_id": "first",
                        "command": [
                            "python",
                            "scripts/registered.py",
                            "scripts/absent.py",
                        ],
                        "depends_on": ["missing", "missing"],
                    }
                }
                self.file(
                    "skills/SKILL_HOOKS.yaml",
                    "skills/a/b/scripts/hook.py skills/a/b/scripts/absent.py",
                )
                self.file("skills/a/b/scripts/hook.py")
                self.file("examples/matrix.py")
                self.matrix(
                    "def load_matrix():\n    return [{'command':['python','examples/matrix.py']}]\n"
                )
                # Many findings and edges must complete, with no artificial native scan cap.
                for i in range(120):
                    self.file(f"tests/case_{i:03}.py")
                registry["many"] = {
                    "action_id": "many",
                    "command": [],
                    "depends_on": ["absent"] * 150,
                }
                result = await check(registry)
                self.assertEqual(
                    len(result["outputs"]["result"]["dependency_errors"]), 152
                )
                self.assertFalse(result["outputs"]["result"]["ok"])
                self.matrix("no_loader_function = True\n")
                await check(registry)
                # Real tools preserve state between stages, including disappearance after extraction.
                paths = await remote.call(
                    "mathformer_audit_registered",
                    {"registry": registry, "repository_root": str(self.root)},
                )
                self.assertEqual(paths, {"paths": ["scripts/registered.py"]})
                packed = await remote.call(
                    "mathformer_audit_pack_sources",
                    {"registered": paths["paths"], "matrix": [], "hooks": []},
                )
                (self.root / "scripts/registered.py").unlink()
                findings = await remote.call(
                    "mathformer_audit_inspect_paths",
                    {**packed, "repository_root": str(self.root)},
                )
                self.assertEqual(
                    findings["findings"]["direct_missing"], ["scripts/registered.py"]
                )
                # Read/import/load errors stop at their native stage; later stages never run.
                for text in [
                    'raise ValueError("fixture import")\n',
                    'def load_matrix():\n    raise ValueError("fixture load")\n',
                ]:
                    self.matrix(text)
                    result = await run(registry)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_audit_registered", "mathformer_audit_matrix"],
                    )
                (self.root / "tests/test_program/run_comprehensive_tests.py").unlink()
                hook = self.root / "skills/SKILL_HOOKS.yaml"
                hook.unlink()
                hook.mkdir()
                result = await run({})
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 3)
                hook.rmdir()
                await check(registry)
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 6
                result = await run(registry, budget)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    6,
                )
                self.assertIn("budget", str(result).lower())
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                w, a = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        w,
                        a,
                        {"registry": {}, "repository_root": str(self.root)},
                        remote,
                        pending,
                    )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
