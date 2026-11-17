#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real native normalization, production MCP registration and Lunar/PRISM execution.

No provider, model or external compiler is involved in this source. Fixtures are
filesystem inputs, not substitutes for source steps or the PRISM implementation.
All writes are isolated under artifacts/workflow_hub and removed after testing.
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
import tempfile
import unittest
import yaml
from normalize_workflows_tools import source, output_path, files_from
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_normalize_workflows_workflow/workflow.yaml"


def oracle():
    path = ROOT / "tests/mcp/fixtures/normalize_workflows_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "normalize_oracle", SourceFileLoader("normalize_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The frozen source resides in a fixture directory; restore its real read context.
    module.REPO_ROOT = ROOT
    module.SCRIPT_DIR = source().SCRIPT_DIR
    return module


def snapshot(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


class NormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = source()
        cls.descriptors = cls.native.inventory()
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="normalize-fixture-", dir=base
        )
        cls.directory = Path(cls.temporary.name)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_original_inventory_render_and_check_equivalence(self):
        native, original = self.native, oracle()
        old_descriptors = original.inventory()

        # The selected descriptor is now authored, as for the other migrated actions.
        def without_self(rows):
            return [
                r for r in rows if r["id"] != "hub_control_normalize_workflows_workflow"
            ]

        self.assertEqual(without_self(self.descriptors), without_self(old_descriptors))
        self.assertEqual(
            self.descriptors, sorted(self.descriptors, key=lambda d: d["id"])
        )
        self.assertEqual(len(self.descriptors), len(old_descriptors))
        files, catalog = native.render_descriptors(self.descriptors)
        old_files, old_catalog = original.render()
        self.assertEqual(catalog["counts"], old_catalog["counts"])
        for path, text in old_files.items():
            if (
                path.name != "catalog.json"
                and "hub_control_normalize_workflows_workflow" not in str(path)
            ):
                self.assertEqual(files[path], text)
        # Empty output traverses every expected file, accumulates all misses, and
        # skips validation on every one: no early failure or invented retry.
        output = self.directory / "empty"
        result = native.check(output)
        self.assertEqual(result, original.check(output))
        self.assertEqual(len(result["errors"]), len(files))
        self.assertFalse(result["ok"])
        self.assertFalse(output.exists())
        for argv in (["--check"], ["--write", "--json"]):
            options = native.parse_options(argv)
            self.assertEqual(
                options, {"write": "--write" in argv, "json": "--json" in argv}
            )
            stream = io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(native.finish(result, options), 1)
            self.assertEqual(
                stream.getvalue(),
                (json.dumps(result, indent=2) if options["json"] else f"FAIL: {result}")
                + "\n",
            )
        for argv in ([], ["--check", "--write"], ["--invalid"]):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                native.parse_options(argv)
            self.assertEqual(error.exception.code, 2)

    def test_native_matching_stale_validation_unexpected_and_io_failure(self):
        native = self.native
        # Real declarative profile has only inline types and source-backed provenance.
        descriptor = next(
            d
            for d in self.descriptors
            if d["extensions"]["mathformer.source"]["category"] == "profile"
        )
        files, catalog = native.render_descriptors([descriptor])
        output = self.directory / "small"
        native.write_files(files, output)
        result = native.check_rendered(files, catalog, output)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["descriptor_count"], 1)
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(native.finish(result, {"json": False}), 0)
        self.assertTrue(stream.getvalue().startswith("PASS:"))
        path = next(p for p in files if p.name == "workflow.yaml")
        (output / path).write_text("stale")
        result = native.check_rendered(files, catalog, output)
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("missing or stale", result["errors"][0])
        # Matching but invalid descriptor is validated rather than skipped.
        bad = dict(files)
        bad[path] = "{}\n"
        native.write_files(bad, output)
        result = native.check_rendered(bad, catalog, output)
        self.assertFalse(result["ok"])
        self.assertTrue(any("required property" in e for e in result["errors"]))
        native.write_files(files, output)
        extra = output / "extra/workflow.yaml"
        extra.parent.mkdir()
        extra.write_text("{}")
        result = native.check_rendered(files, catalog, output)
        self.assertEqual(result["errors"], [f"unexpected descriptor: {extra}"])
        self.assertTrue(extra.exists())
        blocker = self.directory / "blocked"
        blocker.write_text("file")
        with self.assertRaises(OSError):
            native.write_files(files, blocker)
        from types import SimpleNamespace

        def actions(edges):
            return {
                key: SimpleNamespace(depends_on=children)
                for key, children in edges.items()
            }

        native.audit_action_dependencies(
            actions({"root": ["shared", "other"], "other": ["shared"], "shared": []})
        )
        native.audit_action_dependencies({})
        for edges, message in (
            ({"a": ["missing"]}, "unknown action dependency"),
            ({"a": ["a"]}, "action dependency cycle"),
            ({"a": ["b"], "b": ["c"], "c": ["a"]}, "action dependency cycle"),
        ):
            with self.assertRaisesRegex(ValueError, message):
                native.audit_action_dependencies(actions(edges))
        empty_files, empty_catalog = native.render_descriptors([])
        self.assertEqual(list(empty_files), [Path("catalog.json")])
        self.assertTrue(all(count == 0 for count in empty_catalog["counts"].values()))
        with self.assertRaises(ValueError):
            output_path(str(Path(gettempdir()) / "unauthorized"))
        with self.assertRaises(ValueError):
            files_from(
                {"files": {"../escape": "x"}, "file_order": ["../escape"]}, output
            )

    def test_real_registered_mcp_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_control_normalize_workflows_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 6},
        )
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
            "normalization",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    assets = snapshot(doc)
                    selected = workflow_documents([DESCRIPTOR], assets)[0]
                    qualified = compile_workflow(
                        "mcp:normalization",
                        selected,
                        tools if inventory is None else inventory,
                    )
                    return qualified, assets

                workflow, assets = compile(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                missing, _ = compile(document, [])
                self.assertFalse(missing["runnable"])

                async def authorize():
                    pass

                async def run(argv, output, doc=None):
                    selected, received = compile(doc) if doc else (workflow, assets)
                    return await execute(
                        selected,
                        received,
                        {"argv": argv, "output_directory": str(output)},
                        remote,
                        authorize,
                    )

                help_result = await run(
                    ["--help"], self.directory / "help-never-written"
                )
                self.assertEqual(help_result["status"], "accepted", help_result)
                self.assertEqual(
                    help_result["outputs"], {"result": None, "exit_code": 0}
                )
                self.assertEqual(
                    [c["tool"] for c in help_result["calls"]],
                    ["mathformer_normalize_parse", "mathformer_normalize_finish"],
                )
                self.assertFalse((self.directory / "help-never-written").exists())
                output = self.directory / "runtime"
                result = await run(["--check", "--json"], output)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"],
                    {"result": self.native.check(output), "exit_code": 1},
                )
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [
                        "mathformer_normalize_" + n
                        for n in ("parse", "inventory", "render", "check", "finish")
                    ],
                )
                self.assertFalse(output.exists())
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
                # Real write branch runs all six bound tools. No production output
                # is touched; any schema/provenance errors are native result data.
                result = await run(["--write"], output)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [
                        "mathformer_normalize_" + n
                        for n in (
                            "parse",
                            "inventory",
                            "render",
                            "write",
                            "check",
                            "finish",
                        )
                    ],
                )
                expected = self.native.check(output)
                self.assertEqual(
                    result["outputs"],
                    {"result": expected, "exit_code": 0 if expected["ok"] else 1},
                )
                files, catalog = self.native.render_descriptors(self.descriptors)
                self.assertEqual(
                    len(list(output.rglob("workflow.yaml"))), len(self.descriptors)
                )
                for path, text in files.items():
                    self.assertEqual((output / path).read_text(), text)
                # Exercise transported intermediate state and the successful check
                # outcome using the actual registered tools on a bounded fixture.
                profiles = [
                    d
                    for d in self.descriptors
                    if d["extensions"]["mathformer.source"]["category"] == "profile"
                ][:2]
                rendered = await remote.call(
                    "mathformer_normalize_render",
                    {
                        "descriptors": [
                            json.dumps(d, ensure_ascii=False) for d in profiles
                        ]
                    },
                )
                packed = rendered["rendered"]
                self.assertEqual(packed["catalog"]["counts"]["profile"], 2)
                small = self.directory / "transported"
                await remote.call(
                    "mathformer_normalize_write",
                    {"rendered": packed, "output_directory": str(small)},
                )
                checked = await remote.call(
                    "mathformer_normalize_check",
                    {"rendered": packed, "output_directory": str(small)},
                )
                self.assertTrue(checked["result"]["ok"], checked)
                finished = await remote.call(
                    "mathformer_normalize_finish",
                    {
                        "result": checked["result"],
                        "options": {"json": True, "write": True},
                    },
                )
                self.assertEqual(finished, {"exit_code": 0})
                for argv in ([], ["--check", "--write"], ["--check", "--extra"]):
                    failed = await run(argv, output)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(len(failed["calls"]), 1)
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual(failed["calls"][0]["status"], "rejected")
                failed = await run(
                    ["--check"], str(Path(gettempdir()) / "outside-policy")
                )
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(len(failed["calls"]), 4)
                self.assertIsNone(failed["outputs"])
                blocker = self.directory / "runtime-blocked"
                blocker.write_text("file")
                failed = await run(["--write"], blocker)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(len(failed["calls"]), 4)
                self.assertIsNone(failed["outputs"])
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 3
                failed = await run(
                    ["--write"], self.directory / "never-written", bounded
                )
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in failed["calls"]
                    ),
                    3,
                )
                self.assertEqual(failed["calls"][-1]["status"], "rejected")
                self.assertIn("budget", str(failed).lower())
                self.assertFalse((self.directory / "never-written").exists())
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                compiled, received = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        compiled,
                        received,
                        {"argv": ["--check"], "output_directory": str(output)},
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
