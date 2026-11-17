#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Filesystem fixtures through native source, real MCP and Lunar PRISM.

This workflow uses no model/provider or external compiler. Nothing is substituted:
Lunar's PRISM parser, checker, compiler and runtime all execute for real.
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
from dataclasses import asdict
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import re
import tempfile
import unittest
import yaml
from library_docs_tools import source, ARGV
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_docs_library_workflow/workflow.yaml"


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


def stable(value):
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items() if k != "generated_at_utc"}
    if isinstance(value, list):
        return [stable(v) for v in value]
    if isinstance(value, str):
        return re.sub(
            r"- Generated at UTC: `[^`]+`", "- Generated at UTC: `<clock>`", value
        )
    return value


class LibraryDocsTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(exist_ok=True, parents=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="library-docs-fixture-", dir=base)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.context = {"repository_root": str(self.root)}
        self.native = source(self.context)
        self.output = self.root / "docs/libraries/mathformerlib"
        self.write(
            "MathformerLib/Z.lean",
            """import Mathlib.Data.Nat.Basic Mathlib.Logic.Basic -- imports
/-! Module fixture notes. -/
namespace Outer
namespace Inner
/-- Original source (NL): Reflexivity.
Original source (LaTeX): `0=0`.
-/
theorem refl_zero : (0 : Nat) = 0 := by
  rfl
/-- Generated note (NL): Truth. -/
lemma truth : True := by
  trivial
end Inner
end Outer
""",
        )
        self.write("MathformerLib/A.lean", "def first : Nat := 1\n")
        self.write("libraries/MathformerLib.lean", "import MathformerLib.A\n")
        self.write("Mathformer/C.lean", "namespace C\ndef last : Nat := 2\nend C\n")

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def oracle(self):
        path = ROOT / "tests/mcp/fixtures/library_docs_original.py.txt"
        spec = importlib.util.spec_from_loader(
            "_library_docs_oracle", SourceFileLoader("_library_docs_oracle", str(path))
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        module.REPO_ROOT = self.root
        return module

    def cli(self, module, extra=()):
        stream = io.StringIO()
        with redirect_stdout(stream), redirect_stderr(io.StringIO()):
            code = module.main([*ARGV, *extra])
        return code, stream.getvalue()

    def files(self):
        return {
            p.relative_to(self.output).as_posix(): (
                json.dumps(stable(json.loads(p.read_text())), sort_keys=True)
                if p.suffix == ".json"
                else stable(p.read_text())
            )
            for p in self.output.rglob("*")
            if p.is_file()
        }

    def test_native_equivalence_discovery_scanner_and_branches(self):
        oracle = self.oracle()
        self.assertEqual(self.cli(self.native), self.cli(oracle))
        expected = self.files()
        self.cli(self.native)
        self.assertEqual(self.files(), expected)
        roots = [
            Path("missing"),
            Path("MathformerLib"),
            Path("MathformerLib/A.lean"),
            Path("MathformerLib"),
            Path("Mathformer"),
        ]
        records = self.native.collect_docs(roots, None)
        self.assertEqual(
            [m.module for m in records],
            ["MathformerLib.A", "MathformerLib.Z", "Mathformer.C"],
        )
        self.assertEqual(
            [asdict(m) for m in records],
            [asdict(oracle.scan_module(p, {})) for p in oracle.iter_lean_files(roots)],
        )
        z = records[1]
        self.assertEqual(z.imports, ["Mathlib.Data.Nat.Basic", "Mathlib.Logic.Basic"])
        self.assertEqual(
            [d.qualified_name for d in z.declarations],
            ["Outer.Inner.refl_zero", "Outer.Inner.truth"],
        )
        self.assertNotIn("Generated note", z.declarations[0].code)
        self.assertTrue(z.declarations[-1].code.endswith("end Outer"))
        self.assertIn("Module fixture notes", z.module_comment.body)
        self.assertEqual(z.sha256, hashlib.sha256(z.path.read_bytes()).hexdigest())
        self.assertEqual(
            [m.status for m in records], ["accepted", "accepted", "candidate"]
        )
        registry = self.write(
            "registry.json",
            json.dumps({"modules": [{"module": z.module, "status": "reviewed"}]}),
        )
        self.assertEqual(
            self.native.collect_docs([Path("MathformerLib/Z.lean")], registry)[
                0
            ].status,
            "reviewed",
        )
        registry.write_text("{invalid")
        with self.assertRaises(json.JSONDecodeError):
            self.native.collect_docs(roots, registry)
        # Empty scan still succeeds unless the separate native --expect-docs branch is selected.
        for p in self.root.rglob("*.lean"):
            p.unlink()
        self.assertEqual(self.cli(self.native), self.cli(oracle))
        self.assertEqual(
            self.cli(self.native, ["--expect-docs"]),
            self.cli(oracle, ["--expect-docs"]),
        )
        self.assertEqual(self.cli(self.native, ["--expect-docs"])[0], 3)
        self.assertFalse(json.loads((self.output / "manifest.json").read_text())["ok"])
        self.assertTrue(
            (self.output / "modules/MathformerLib/Z.md").exists()
        )  # stale pages retained
        self.assertEqual(self.native.collect_docs([Path("missing")], None), [])
        # Self-test remains a separate native CLI branch, isolated from production.
        native_code, native_text = self.cli(self.native, ["--self-test"])
        oracle_code, oracle_text = self.cli(oracle, ["--self-test"])
        native_result, oracle_result = json.loads(native_text), json.loads(oracle_text)
        native_result.pop(
            "fixture"
        )  # temporary fixture pathname is intentionally unique
        oracle_result.pop("fixture")
        self.assertEqual(native_code, oracle_code)
        self.assertEqual(stable(native_result), stable(oracle_result))
        # Ordered logging remains owned by native main, including the no-docs error event.
        log = self.root / "events.jsonl"
        code, _ = self.cli(
            self.native,
            [
                "--include-root",
                "missing",
                "--expect-docs",
                "--reasoning-log-file",
                str(log),
            ],
        )
        self.assertEqual(code, 3)
        self.assertEqual(
            [json.loads(line)["step"] for line in log.read_text().splitlines()],
            [
                "mathformer_library_docs_start",
                "mathformer_library_docs_complete",
                "mathformer_library_docs_error",
            ],
        )

    def test_registered_tools_and_lunar_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_docs_library_workflow")
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
            "library",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=tools):
                assets = snapshot(doc)
                result = compile_workflow(
                    "mcp:library",
                    workflow_documents([DESCRIPTOR], assets)[0],
                    inventory,
                )
                return result, assets

            compiled, assets = compile(document)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
            self.assertFalse(
                compile(
                    document,
                    [
                        t
                        for t in tools
                        if t["name"] != "mathformer_library_docs_publish_docs"
                    ],
                )[0]["runnable"]
            )

            async def authorize():
                pass

            async def run(doc=document, context=None, argv=ARGV):
                c, a = compile(doc)
                return await execute(
                    c,
                    a,
                    {"argv": argv, "context": context or self.context},
                    remote,
                    authorize,
                )

            # Direct MCP calls verify advertised ports and source state serialization.
            configured = await remote.call(
                "mathformer_library_docs_configure",
                {"argv": ARGV, "context": self.context},
            )
            collected = await remote.call(
                "mathformer_library_docs_collect_modules",
                {"config": configured["config"], "context": self.context},
            )
            records = collected["modules"]
            self.assertEqual(
                [m["module"] for m in records],
                [
                    "MathformerLib.A",
                    "MathformerLib.Z",
                    "libraries.MathformerLib",
                    "Mathformer.C",
                ],
            )
            self.assertEqual(
                records[1]["declarations"][0]["qualified_name"], "Outer.Inner.refl_zero"
            )
            self.assertIn(
                "Reflexivity", records[1]["declarations"][0]["comment"]["body"]
            )
            self.assertEqual(
                records[1]["sha256"],
                hashlib.sha256(
                    (self.root / "MathformerLib/Z.lean").read_bytes()
                ).hexdigest(),
            )
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    "mathformer_library_docs_configure",
                    {"argv": ARGV + ["--self-test"], "context": self.context},
                )
            invalid = dict(configured["config"], output_dir=str(Path(gettempdir())))
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    "mathformer_library_docs_publish_docs",
                    {"config": invalid, "modules": records, "context": self.context},
                )
            # Compare actual transport output and files with original entrypoint.
            code, stdout = self.cli(self.oracle())
            manifest = json.loads((self.output / "manifest.json").read_text())
            self.assertNotIn("manifest_file", manifest)
            manifest["manifest_file"] = "docs/libraries/mathformerlib/manifest.json"
            expected = self.files()
            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(
                stable(result["outputs"]),
                stable(
                    {
                        "result": {
                            "returncode": code,
                            "stdout": stdout,
                            "manifest": manifest,
                        }
                    }
                ),
            )
            self.assertEqual(self.files(), expected)
            self.assertEqual(
                [c["tool"] for c in result["calls"]],
                [
                    "mathformer_library_docs_" + s
                    for s in (
                        "configure",
                        "collect_modules",
                        "publish_docs",
                        "complete_main",
                    )
                ],
            )
            self.assertTrue(result["runtime"]["effect_records"])
            self.assertTrue(result["replay_artifacts"])
            self.assertEqual(
                result["outputs"]["result"]["manifest"]["summary"]["module_count"], 4
            )
            # Native failure during scan must stop before publication without retry.
            self.write("MathformerLib/A.lean", "\ufffd").write_bytes(b"\xff")
            result = await run()
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(len(result["calls"]), 2)
            (self.root / "MathformerLib/A.lean").unlink()
            # Real publication failure after collection, preserving previous files.
            (self.output / "INDEX.md").unlink()
            (self.output / "INDEX.md").mkdir()
            result = await run()
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 3)
            self.assertTrue((self.output / "modules/MathformerLib/Z.md").exists())
            (self.output / "INDEX.md").rmdir()
            for p in self.root.rglob("*.lean"):
                p.unlink()
            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(result["outputs"]["result"]["returncode"], 0)
            self.assertFalse(result["outputs"]["result"]["manifest"]["ok"])
            self.assertEqual(
                result["outputs"]["result"]["manifest"]["summary"]["module_count"], 0
            )
            self.assertTrue((self.output / "modules/MathformerLib/Z.md").exists())
            bounded = deepcopy(document)
            bounded["policy"]["limits"]["max_operation_calls"] = 2
            result = await run(bounded)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 2
            )
            self.assertIn("budget", str(result).lower())
            result = await run(context={"repository_root": str(Path(gettempdir()))})
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 1)
            with self.assertRaises(ExecutionRejected):
                await run(argv=ARGV + ["--self-test"])
        self.assertFalse(manager.active)
        # The same registered service enforces its real read-only policy before writing.
        readonly_server = 'import sys;sys.path.insert(0,"scripts");import mcp_server;mcp_server._READONLY=True;mcp_server.mcp.run(transport="stdio")'
        before = self.files()
        async with manager.open(
            "readonly-library",
            StdioConfig(
                command=sys.executable, args=["-c", readonly_server], cwd=str(ROOT)
            ),
            {},
        ) as remote:
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    "mathformer_library_docs_publish_docs",
                    {
                        "config": configured["config"],
                        "modules": [],
                        "context": self.context,
                    },
                )
            self.assertEqual(self.files(), before)
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
