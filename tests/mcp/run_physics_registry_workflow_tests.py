#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Temporary filesystem fixtures through native source, MCP and real Lunar PRISM.

This workflow has no provider/model/compiler subprocess boundary. Tests run the
real PRISM parser, checker, compiler and runtime without scientific backends.
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
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import itertools
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
import yaml
from physics_registry_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathformerphysicslib_registry_build_workflow/workflow.yaml"


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


def original(context):
    path = ROOT / "tests/mcp/fixtures/physics_registry_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "registry_original", SourceFileLoader("registry_original", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    bound = source(context)
    for name in ("REPO_ROOT", "LIB_ROOT", "MANIFEST", "README"):
        setattr(module, name, getattr(bound, name))
    return module


def fixture(root, *, empty=False, markers=False):
    if root.exists():
        shutil.rmtree(root)
    root.mkdir()
    (root / "lean-toolchain").write_text("leanprover/lean4:fixture\n")
    lib = root / "MathformerPhysicsLib"
    lib.mkdir()
    (lib / "MANIFEST.json").write_text(
        json.dumps({"backends": {key: {} for key in ("Lean", "Isabelle", "SymPy")}})
    )
    (lib / "README.md").write_text(
        "prefix\n"
        + (
            "<!-- BEGIN GENERATED PHYSICS COVERAGE -->\nstale\n<!-- END GENERATED PHYSICS COVERAGE -->\nsuffix\n"
            if markers
            else "coverage absent\n"
        )
    )
    if not empty:
        # More cases than any advertised operation bound: collections must exhaust.
        for backend, (artifact, report) in source(
            {"repository_root": str(root), "allow_mutating": True}
        ).BACKEND_FILES.items():
            ids = (
                ["formalphysics_0000", "formalphysics_9999"]
                if backend != "Lean"
                else ["formalphysics_0000"]
                + [f"formalphysics_{i:04d}" for i in range(9000, 9014)]
            )
            for case in reversed(ids):
                directory = lib / backend / case
                directory.mkdir(parents=True)
                (directory / artifact).write_text(f"{backend} {case}")
                if case == "formalphysics_0000":
                    (directory / report).write_text('{"verified":true}')
            (lib / backend / "formalphysics_ignored").mkdir()
            (lib / backend / "formalphysics_file").write_text("not a directory")
        data = root / "data"
        data.mkdir()
        (data / "a_formalphysics_0000.txt").write_text("first source")
        (data / "z_formalphysics_0000.txt").write_text("second source")
    return lib


class RegistryTests(unittest.TestCase):
    def test_native_rows_validation_and_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            lib = fixture(root)
            context = {"repository_root": str(root), "allow_mutating": True}
            native, oracle = source(context), original(context)
            rows = native.build_registry()
            self.assertEqual(rows, oracle.build_registry())
            self.assertEqual(len(rows), 19)
            self.assertEqual(
                [r["backend"] for r in rows],
                ["Lean"] * 15 + ["Isabelle"] * 2 + ["SymPy"] * 2,
            )
            self.assertEqual(
                rows[0]["source_location"], "data/a_formalphysics_0000.txt"
            )
            self.assertTrue(rows[0]["public_root_imported"])
            self.assertEqual(
                rows[1]["provenance_blockers"],
                ["source_record_not_repository_addressable", "decisive_report_missing"],
            )
            native.write_registry(rows)
            self.assertEqual(native.validate_registry(rows), [])
            # Source hashes are informational; only artifact/report mismatches count.
            manifest = json.loads(native.MANIFEST.read_text())
            manifest["artifact_registry"][0]["source_sha256"] = "ignored"
            manifest["artifact_registry"][0]["artifact_sha256"] = "stale"
            manifest["artifact_registry"][0]["decisive_report_sha256"] = "stale"
            manifest["artifact_registry"].pop()
            manifest["artifact_registry"].extend([None, {"artifact_path": "extra"}])
            native.MANIFEST.write_text(json.dumps(manifest))
            errors = native.validate_registry(rows)
            self.assertEqual(errors, oracle.validate_registry(rows))
            self.assertEqual(len(errors), 4)
            self.assertTrue(errors[0].startswith("unregistered artifact:"))
            self.assertTrue(errors[1].endswith("extra"))
            self.assertTrue(errors[2].startswith("artifact hash mismatch:"))
            self.assertTrue(errors[3].startswith("decisive report hash mismatch:"))
            for module in (native, oracle):
                with (
                    patch.object(sys, "argv", ["registry", "--extra"]),
                    redirect_stderr(io.StringIO()),
                    self.assertRaises(SystemExit) as caught,
                ):
                    module.main()
                self.assertEqual(caught.exception.code, 2)
            native.MANIFEST.write_text("{broken")
            with self.assertRaises(json.JSONDecodeError):
                native.validate_registry(rows)
            # Preserve the root/library mismatch: relocated files are not a fallback.
            (root / "libraries").mkdir()
            lib.rename(root / "libraries/MathformerPhysicsLib")
            self.assertEqual(native.build_registry(), [])
            with self.assertRaises(FileNotFoundError):
                native.write_registry([])

    def test_registered_mcp_lunar_and_original_equivalence(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_mathformerphysicslib_registry_build_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            context = {"repository_root": str(root), "allow_mutating": True}
            failure = None
            async with manager.open(
                "registry",
                StdioConfig(
                    command=(
                        str(ROOT / ".venv/bin/python")
                        if (ROOT / ".venv/bin/python").exists()
                        else sys.executable
                    ),
                    args=["-c", server],
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
                        assets = snapshot(doc)
                        selected = workflow_documents([DESCRIPTOR], assets)[0]
                        return (
                            compile_workflow(
                                "mcp:registry",
                                selected,
                                tools if inventory is None else inventory,
                            ),
                            assets,
                        )

                    workflow, assets = compile(document)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(
                        set(workflow["bindings"]), set(document["operations"])
                    )
                    missing, _ = compile(document, [])
                    self.assertFalse(missing["runnable"])

                    async def authorize():
                        pass

                    async def run(flags, doc=None, ctx=None):
                        compiled, received = compile(doc) if doc else (workflow, assets)
                        return await execute(
                            compiled,
                            received,
                            {"flags": flags, "context": ctx or context},
                            remote,
                            authorize,
                        )

                    for empty in (False, True):
                        for write, check, json_output in itertools.product(
                            (False, True), repeat=3
                        ):
                            flags = {
                                "write": write,
                                "check": check,
                                "json": json_output,
                            }
                            lib = fixture(root, empty=empty, markers=check)
                            oracle = original(context)
                            stream = io.StringIO()
                            argv = ["registry"] + [
                                f"--{key}" for key, value in flags.items() if value
                            ]
                            with (
                                patch.object(sys, "argv", argv),
                                redirect_stdout(stream),
                            ):
                                code = oracle.main()
                            expected_files = {
                                p.name: p.read_bytes()
                                for p in (lib / "MANIFEST.json", lib / "README.md")
                            }
                            fixture(root, empty=empty, markers=check)
                            native_stream = io.StringIO()
                            with (
                                patch.object(sys, "argv", argv),
                                redirect_stdout(native_stream),
                            ):
                                native_code = source(context).main()
                            self.assertEqual(native_code, code)
                            self.assertEqual(
                                native_stream.getvalue(), stream.getvalue()
                            )
                            self.assertEqual(
                                {
                                    p.name: p.read_bytes()
                                    for p in (lib / "MANIFEST.json", lib / "README.md")
                                },
                                expected_files,
                            )
                            fixture(root, empty=empty, markers=check)
                            result = await run(flags)
                            self.assertEqual(result["status"], "accepted", result)
                            emitted = result["outputs"]["result"]
                            self.assertEqual(emitted["stdout"], stream.getvalue())
                            self.assertEqual(emitted["exit_code"], code)
                            self.assertEqual(
                                emitted["payload"]["case_count"], 0 if empty else 19
                            )
                            self.assertEqual(emitted["payload"]["ok"], code == 0)
                            self.assertEqual(
                                emitted["payload"]["counts"],
                                (
                                    {"Lean": 0, "Isabelle": 0, "SymPy": 0}
                                    if empty
                                    else {"Lean": 15, "Isabelle": 2, "SymPy": 2}
                                ),
                            )
                            self.assertEqual(
                                {
                                    p.name: p.read_bytes()
                                    for p in (lib / "MANIFEST.json", lib / "README.md")
                                },
                                expected_files,
                            )
                            names = (
                                ["build"]
                                + (["write"] if write else ["skip_write"])
                                + ["check_guard"]
                                + (["check"] if check or not write else ["skip_check"])
                                + ["emit"]
                            )
                            self.assertEqual(
                                [c["tool"] for c in result["calls"]],
                                [
                                    "mathformer_physics_registry_" + name
                                    for name in names
                                ],
                            )
                            self.assertTrue(result["replay_artifacts"])
                            self.assertTrue(result["runtime"]["effect_records"])
                    flags = {"write": True, "check": True, "json": True}
                    lib = fixture(root)
                    # Authorization failure stops before write, check guard or emission.
                    before = (lib / "MANIFEST.json").read_bytes()
                    failed = await run(flags, ctx={**context, "allow_mutating": False})
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual(len(failed["calls"]), 2)
                    self.assertEqual((lib / "MANIFEST.json").read_bytes(), before)
                    # No rollback when README fails after the manifest write.
                    (lib / "README.md").unlink()
                    failed = await run(flags)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(len(failed["calls"]), 2)
                    self.assertEqual(
                        len(
                            json.loads((lib / "MANIFEST.json").read_text())[
                                "artifact_registry"
                            ]
                        ),
                        19,
                    )
                    # Malformed manifest aborts check without retry or emit.
                    fixture(root)
                    (lib / "MANIFEST.json").write_text("{broken")
                    failed = await run({"write": False, "check": False, "json": True})
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(len(failed["calls"]), 4)
                    self.assertEqual(failed["calls"][-1]["status"], "rejected")
                    # Actual runtime call budget stops before third dispatch.
                    fixture(root)
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 2
                    failed = await run(flags, bounded)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in failed["calls"]
                        ),
                        2,
                    )
                    self.assertIn("budget", str(failed).lower())
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    compiled, received = compile(timed)

                    async def pending():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(
                            compiled,
                            received,
                            {"flags": flags, "context": context},
                            remote,
                            pending,
                        )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure
            # Exercise the actual server policy callbacks, with no launcher or
            # provider config. These are the service's ordinary runtime flags.
            for setting in (
                "service._READONLY=True",
                'service._ALLOWED_WRITE_ROOTS=[service.Path("/nonexistent-registry-policy-root")]',
            ):
                fixture(root)
                before = (lib / "MANIFEST.json").read_bytes()
                restricted_server = (
                    'import sys;sys.path.insert(0,"scripts");import mcp_server as service;'
                    + setting
                    + ';service.mcp.run(transport="stdio")'
                )
                async with manager.open(
                    "restricted",
                    StdioConfig(
                        command=(
                            str(ROOT / ".venv/bin/python")
                            if (ROOT / ".venv/bin/python").exists()
                            else sys.executable
                        ),
                        args=["-c", restricted_server],
                        cwd=str(ROOT),
                    ),
                    {},
                ) as restricted:
                    failed = await execute(
                        workflow,
                        assets,
                        {"flags": flags, "context": context},
                        restricted,
                        authorize,
                    )
                self.assertFalse(manager.active)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(len(failed["calls"]), 2)
                self.assertEqual((lib / "MANIFEST.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
