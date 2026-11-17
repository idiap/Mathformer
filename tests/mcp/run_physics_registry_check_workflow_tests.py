#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic read-only native/MCP/Lunar fixtures, without scientific tools.

There are no provider or theorem compiler calls in this source. The PRISM parser,
checker, compiler and runtime are real; no production mock mode is used.
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
from contextlib import redirect_stdout
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
from physics_registry_tools import source
from run_physics_registry_workflow_tests import fixture
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathformerphysicslib_registry_check_workflow/workflow.yaml"
FLAGS = {"write": False, "check": True, "json": True}


def original(context):
    path = ROOT / "tests/mcp/fixtures/physics_registry_check_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "registry_check_original",
        SourceFileLoader("registry_check_original", str(path)),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    native = source(context)
    for name in ("REPO_ROOT", "LIB_ROOT", "MANIFEST", "README"):
        setattr(module, name, getattr(native, name))
    return module


def snapshot(document):
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
            "content": t,
            "encoding": "text",
            "sha256": hashlib.sha256(t.encode()).hexdigest(),
        }
        for p, t in texts.items()
    ]


def files(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file()
    }


class RegistryCheckTests(unittest.TestCase):
    def test_registered_native_sequence(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(
                os.environ.get("WORKFLOW_CONTRACT_PATH", ROOT / DESCRIPTOR)
            ).read_text()
        )
        self.assertEqual(
            document["id"], "hub_mathformerphysicslib_registry_check_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 4},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");import mcp_server as service;service._READONLY=True;service.mcp.run(transport="stdio")'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            context = {"repository_root": str(root), "allow_mutating": False}
            failure = None
            async with manager.open(
                "registry-check",
                StdioConfig(
                    command=str(ROOT / ".venv/bin/python"),
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
                        result = compile_workflow(
                            "mcp:registry-check",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools if inventory is None else inventory,
                        )
                        return result, assets

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

                    async def run(doc=None, flags=None):
                        compiled, received = compile(doc) if doc else (workflow, assets)
                        return await execute(
                            compiled,
                            received,
                            {"flags": flags or FLAGS, "context": context},
                            remote,
                            authorize,
                        )

                    for mode in ("empty", "valid", "errors", "duplicate_last_wins"):
                        lib = fixture(root, empty=mode == "empty")
                        native, oracle = source(context), original(context)
                        rows = native.build_registry()
                        self.assertEqual(rows, oracle.build_registry())
                        self.assertEqual(len(rows), 0 if mode == "empty" else 19)
                        if rows:
                            self.assertEqual(
                                [r["backend"] for r in rows],
                                ["Lean"] * 15 + ["Isabelle"] * 2 + ["SymPy"] * 2,
                            )
                            self.assertEqual(
                                rows[0]["source_location"],
                                "data/a_formalphysics_0000.txt",
                            )
                            self.assertTrue(rows[0]["public_root_imported"])
                            self.assertEqual(
                                rows[1]["provenance_blockers"],
                                [
                                    "source_record_not_repository_addressable",
                                    "decisive_report_missing",
                                ],
                            )
                        registered = deepcopy(rows)
                        if mode == "errors":
                            registered.pop()
                            registered[0]["artifact_sha256"] = "bad"
                            registered[0]["decisive_report_sha256"] = "bad"
                            registered += [None, {"artifact_path": "extra"}]
                        elif mode == "duplicate_last_wins":
                            bad = {**rows[0], "artifact_sha256": "bad"}
                            registered = [bad] + registered
                            registered[-1]["source_sha256"] = "informational only"
                        (lib / "MANIFEST.json").write_text(
                            json.dumps({"artifact_registry": registered})
                        )
                        before = files(root)
                        outputs = []
                        for module in (oracle, native):
                            stream = io.StringIO()
                            with (
                                patch.object(
                                    sys, "argv", ["registry", "--check", "--json"]
                                ),
                                redirect_stdout(stream),
                            ):
                                code = module.main()
                            outputs.append((code, stream.getvalue()))
                        self.assertEqual(outputs[0], outputs[1])
                        result = await run()
                        self.assertEqual(result["status"], "accepted", result)
                        emitted = result["outputs"]["result"]
                        self.assertEqual(
                            (emitted["exit_code"], emitted["stdout"]), outputs[0]
                        )
                        self.assertEqual(emitted["payload"], json.loads(outputs[0][1]))
                        self.assertEqual(
                            emitted["exit_code"], 3 if mode == "errors" else 0
                        )
                        if mode == "errors":
                            errors = emitted["payload"]["errors"]
                            self.assertEqual(len(errors), 4)
                            self.assertTrue(
                                errors[0].startswith("unregistered artifact:")
                            )
                            self.assertTrue(errors[1].endswith("extra"))
                            self.assertTrue(
                                errors[2].startswith("artifact hash mismatch:")
                            )
                            self.assertTrue(
                                errors[3].startswith("decisive report hash mismatch:")
                            )
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            [
                                "mathformer_physics_registry_" + n
                                for n in ("discover", "skip_write", "check", "emit")
                            ],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        self.assertEqual(files(root), before)
                    # Invalid manifest fails in validate, without retry or emit.
                    for malformed in (True, False):
                        fixture(root)
                        if malformed:
                            (lib / "MANIFEST.json").write_text("{broken")
                        else:
                            (lib / "MANIFEST.json").unlink()
                        before = files(root)
                        failed = await run()
                        self.assertEqual(failed["status"], "failed", failed)
                        self.assertIsNone(failed["outputs"])
                        self.assertEqual(len(failed["calls"]), 3)
                        self.assertEqual(failed["calls"][-1]["status"], "rejected")
                        self.assertEqual(files(root), before)
                    fixture(root)
                    # Failure in discover prevents all dependent operations.
                    artifact = lib / "Lean/formalphysics_0000/MathformerPhysics.lean"
                    artifact.unlink()
                    artifact.mkdir()
                    failed = await run()
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(len(failed["calls"]), 1)
                    fixture(root)
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 2
                    failed = await run(bounded)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertIsNone(failed["outputs"])
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
                            {"flags": FLAGS, "context": context},
                            remote,
                            pending,
                        )
                    for invalid in (
                        {**FLAGS, "write": True},
                        {**FLAGS, "check": False},
                        {**FLAGS, "json": False},
                    ):
                        with self.assertRaises(ExecutionRejected):
                            await run(flags=invalid)
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
