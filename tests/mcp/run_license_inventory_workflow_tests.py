#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic metadata provider; real native steps, MCP, PRISM and filesystem.

No model, external compiler, or theorem prover participates in this workflow.
Only installed-distribution metadata is substituted, at its provider boundary.
The Lunar parser/checker/compiler and runtime are never substituted.
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
# The repository service's optional backend imports use its installed dependencies.
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
import asyncio
from contextlib import (
    redirect_stdout,
    redirect_stderr,
    contextmanager,
    asynccontextmanager,
)
from copy import deepcopy
from email.message import Message
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml
import generate_python_license_inventory as native
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.contracts import workflow_documents
from mcp_connections.models import StdioConfig
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_licenses_inventory_workflow/workflow.yaml"


def meta(fields):
    result = Message()
    for key, value in fields:
        result[key] = value
    return result


def distributions(config):
    for i, row in enumerate(config["packages"]):
        if config.get("fail_at") == i:
            raise RuntimeError("metadata fixture failure")
        yield SimpleNamespace(
            name=row.get("fallback", ""), metadata=meta(row["fields"])
        )
    if config.get("fail_at") == len(config["packages"]):
        raise RuntimeError("metadata fixture failure")


if "--server" in sys.argv:
    fixture = Path(sys.argv[sys.argv.index("--server") + 1])

    def provider():
        config = json.loads(fixture.read_text())
        log = fixture.with_suffix(".calls")
        with log.open("a") as stream:
            stream.write("begin\n")
        for distribution in distributions(config):
            with log.open("a") as stream:
                stream.write("yield\n")
            yield distribution
        with log.open("a") as stream:
            stream.write("exhausted\n")

    from mcp_server import mcp
    import mcp_server

    mcp_server._READONLY = "--readonly" in sys.argv
    native.metadata.distributions = provider
    mcp.run(transport="stdio")
    raise SystemExit


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in document["provenance"]["sources"]
    ]


@contextmanager
def cwd(path):
    before = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(before)


@asynccontextmanager
async def connection(manager, key, config):
    async with manager.open(key, config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}) as remote:
        try:
            yield remote
        except Exception:
            import traceback

            traceback.print_exc()
            raise


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="inventory-fixture-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.context = {"working_directory": str(self.root), "allow_mutating": True}
        self.config = {
            "packages": [
                {
                    "fields": [
                        ("Name", "zeta|x"),
                        ("Version", " 1\n 2 "),
                        ("License-Expression", "MIT"),
                        ("License", "ignored"),
                        ("Project-URL", "source, https://source"),
                        ("Project-URL", "Homepage, https://first"),
                        ("Project-URL", "homepage, https://second"),
                    ]
                },
                {
                    "fallback": "Alpha",
                    "fields": [
                        ("Version", "2"),
                        ("License", "X" * 90),
                        ("Classifier", "License :: OSI Approved :: MIT"),
                        ("Classifier", "License :: OSI Approved :: MIT"),
                        ("Classifier", "License :: BSD"),
                        ("Project-URL", "malformed"),
                        ("Home-page", " https://home "),
                    ],
                },
                {
                    "fields": [
                        ("Name", "beta"),
                        ("License", "short"),
                        ("Classifier", "License :: ignored"),
                        ("Project-URL", "other, https://fallback,extra"),
                    ]
                },
                {"fields": [("Name", "empty")]},
            ]
        }
        self.fixture = self.root / "metadata.json"
        self.reset()
        path = ROOT / "tests/mcp/fixtures/license_inventory_original.py.txt"
        spec = importlib.util.spec_from_loader(
            "_inventory_oracle", SourceFileLoader("_inventory_oracle", str(path))
        )
        self.oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.oracle)

    def reset(self):
        self.fixture.write_text(json.dumps(self.config))

    def cli(self, module, argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            cwd(self.root),
            patch.object(sys, "argv", [str(Path(__file__).resolve()), *argv]),
            patch.object(
                module.metadata, "distributions", lambda: distributions(self.config)
            ),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            try:
                code = module.main()
            except SystemExit as error:
                code = error.code
        return code, stdout.getvalue(), stderr.getvalue()

    def test_native_equivalence_and_metadata_decisions(self):
        with patch.object(
            native.metadata, "distributions", lambda: distributions(self.config)
        ):
            rows = native.package_rows()
            self.assertEqual(rows, self.oracle.package_rows())
        self.assertEqual([r[0] for r in rows], ["Alpha", "beta", "empty", "zeta|x"])
        self.assertEqual(rows[0][2:], ("MIT, BSD", "https://home"))
        self.assertEqual(rows[1][2:], ("short", "https://fallback,extra"))
        self.assertEqual(rows[2][2:], ("UNKNOWN", ""))
        self.assertEqual(rows[3][1:], ("1 2", "MIT", "https://first"))
        self.assertEqual(native.render(rows), self.oracle.render(rows))
        self.assertIn("zeta\\|x", native.render(rows))
        for argv in (
            [],
            ["--output", "nested/inventory.md"],
            ["--help"],
            ["--bad"],
            ["--output"],
        ):
            self.assertEqual(self.cli(native, argv), self.cli(self.oracle, argv))
        for length in (79, 80, 81, 139, 140, 141, 300):
            value = "L" * length
            for fields in (
                [("License", value)],
                [("License-Expression", value)],
                [("Home-page", value)],
            ):
                m = meta(fields)
                self.assertEqual(
                    native.license_summary(m), self.oracle.license_summary(m)
                )
                self.assertEqual(native.project_url(m), self.oracle.project_url(m))
        self.assertEqual(len(native.clean("x" * 90, max_len=80)), 80)
        self.assertEqual(native.escape_table("x|y\nz"), "x\\|y z")
        # All seven label priorities, first matching entry wins; malformed entries ignored.
        for label in native.PREFERRED_URL_LABELS:
            m = meta(
                [
                    ("Project-URL", "other, fallback"),
                    ("Project-URL", label.upper() + ", winner"),
                    ("Project-URL", label + ", loser"),
                ]
            )
            self.assertEqual(native.project_url(m), "winner")
        self.assertEqual(native.project_url(meta([("Project-URL", "bad")])), "")
        self.assertEqual(
            native.license_summary(meta([("License", "L" * 200)])), "L" * 137 + "..."
        )
        self.config["fail_at"] = 2
        for module in (native, self.oracle):
            with self.assertRaisesRegex(RuntimeError, "metadata fixture failure"):
                self.cli(module, ["--output", "never/report.md"])
        self.assertFalse((self.root / "never").exists())
        self.config = {"packages": []}
        self.assertEqual(self.cli(native, []), self.cli(self.oracle, []))
        self.assertIn(
            "distributions listed: `0`",
            (self.root / "docs/operations/PYTHON_DEPENDENCY_LICENSES.md").read_text(),
        )
        # No package cap: consume the entire provider, not a graph-imposed truncation.
        self.config = {
            "packages": [{"fields": [("Name", f"p{i}")]} for i in range(1201)]
        }
        with patch.object(
            native.metadata, "distributions", lambda: distributions(self.config)
        ):
            self.assertEqual(len(native.package_rows()), 1201)

    def test_registered_workflow(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_licenses_inventory_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for source in document["provenance"]["sources"]:
            self.assertEqual(
                source["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        config = StdioConfig(
            command=sys.executable,
            args=[str(Path(__file__).resolve()), "--server", str(self.fixture)],
            cwd=str(ROOT),
        )
        async with connection(manager, "inventory", config) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=tools):
                assets = snapshot(doc)
                compiled = compile_workflow(
                    "mcp:inventory",
                    workflow_documents([DESCRIPTOR], assets)[0],
                    inventory,
                )
                return compiled, assets

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
                        if t["name"] != "mathformer_license_inventory_write"
                    ],
                )[0]["runnable"]
            )

            async def authorize():
                pass

            async def run(argv=None, doc=document, context=None):
                c, a = compile(doc)
                return await execute(
                    c,
                    a,
                    {
                        "argv": [] if argv is None else argv,
                        "context": self.context if context is None else context,
                    },
                    remote,
                    authorize,
                )

            collected = await remote.call("mathformer_license_inventory_collect", {})
            with patch.object(
                native.metadata, "distributions", lambda: distributions(self.config)
            ):
                self.assertEqual(
                    collected["rows"], [list(r) for r in native.package_rows()]
                )
            for argv in ([], ["--output", "nested/report.md"]):
                code, stdout, stderr = self.cli(self.oracle, argv)
                output = (
                    argv[-1]
                    if argv
                    else "docs/operations/PYTHON_DEPENDENCY_LICENSES.md"
                )
                expected = (self.root / output).read_bytes()
                (self.root / output).write_text("stale")
                result = await run(argv)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"],
                    {"exit_code": code, "output_path": output, "stdout": stdout},
                )
                self.assertEqual((self.root / output).read_bytes(), expected)
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [
                        "mathformer_license_inventory_" + s
                        for s in ("parse", "collect", "render", "mkdir", "write")
                    ],
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
            self.assertTrue(
                self.fixture.with_suffix(".calls").read_text().endswith("exhausted\n")
            )
            # Help stops before provider discovery, even when discovery would fail.
            self.config["fail_at"] = 0
            self.reset()
            before = self.fixture.with_suffix(".calls").read_text()
            result = await run(["--help"])
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(result["outputs"]["exit_code"], 0)
            self.assertIsNone(result["outputs"]["output_path"])
            self.assertEqual(
                result["outputs"]["stdout"], self.cli(self.oracle, ["--help"])[1]
            )
            self.assertEqual(len(result["calls"]), 2)
            self.assertEqual(self.fixture.with_suffix(".calls").read_text(), before)
            result = await run(["--bad"])
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 1)
            # Native provider error after partial consumption is terminal, no retries or write.
            self.config["fail_at"] = 2
            self.reset()
            result = await run()
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 2)
            self.assertIsNone(result["outputs"])
            self.assertEqual(result["calls"][-1]["status"], "rejected")
            self.assertTrue(result["calls"][-1]["transport_call_performed"])
            del self.config["fail_at"]
            self.reset()
            denied = dict(self.context, allow_mutating=False)
            result = await run(context=denied)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 4)
            # Actual mkdir failure and actual write failure stop at their source occurrence.
            (self.root / "blocker").write_text("file")
            result = await run(["--output", "blocker/nested/report.md"])
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 4)
            (self.root / "directory").mkdir()
            result = await run(["--output", "directory"])
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 5)
            bounded = deepcopy(document)
            bounded["policy"]["limits"]["max_operation_calls"] = 2
            result = await run(["--output", "not-written/report.md"], doc=bounded)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 2
            )
            self.assertFalse((self.root / "not-written").exists())
            self.config = {"packages": []}
            self.reset()
            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            self.assertIn(
                "distributions listed: `0`",
                (
                    self.root / "docs/operations/PYTHON_DEPENDENCY_LICENSES.md"
                ).read_text(),
            )
        self.assertFalse(manager.active)
        config.args.append("--readonly")
        async with connection(manager, "readonly-inventory", config) as remote:
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    "mathformer_license_inventory_mkdir",
                    {"output": "readonly/report.md", "context": self.context},
                )
            self.assertFalse((self.root / "readonly").exists())
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
