#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native/MCP/Lunar parity using isolated TeX fixtures; no external processes."""

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
import io
import json
import tempfile
import types
import unittest
from unittest.mock import patch
import yaml
import generate_formalphysics_extra_lean as native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_formalphysics_extra_lean_workflow/workflow.yaml"


def oracle():
    module = types.ModuleType("original_extra_lean")
    module.__file__ = str(ROOT / "scripts/generate_formalphysics_extra_lean.py")
    exec(
        compile(
            (ROOT / "tests/mcp/fixtures/extra_lean_original.py.txt").read_text(),
            module.__file__,
            "exec",
        ),
        module.__dict__,
    )
    return module


def fixture(root):
    source = root / "data/benchmarks/formal_science/physics_top10_sources"
    source.mkdir(parents=True)
    for case, spec in native.CASES.items():
        (source / f"{spec['rank']}_{case}.tex").write_text(
            f"fixture {case} -/ Unicode α\n"
        )
    return root


def run_main(module, root, argv):
    stream = io.StringIO()
    with (
        patch.multiple(
            module,
            REPO_ROOT=root,
            SOURCE_ROOT=root / "data/benchmarks/formal_science/physics_top10_sources",
            ARTIFACT_ROOT=root / "artifacts/physics_lean/from_scratch_lean",
            LIB_ROOT=root / "libraries/MathformerPhysicsLib/Lean",
        ),
        patch.object(sys, "argv", ["generator", *argv]),
        redirect_stdout(stream),
    ):
        code = module.main()
    return code, stream.getvalue()


def files(root):
    return {
        str(p.relative_to(root)): p.read_bytes()
        for base in ["artifacts", "libraries"]
        for p in (root / base).rglob("*")
        if p.is_file()
    }


def assets(document):
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


class ExtraLeanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="extra-lean-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_original_entrypoint_parity(self):
        for argv in ([], ["--promote-lib"]):
            old = fixture(self.root / ("old" + str(len(argv))))
            new = fixture(self.root / ("new" + str(len(argv))))
            self.assertEqual(run_main(oracle(), old, argv), run_main(native, new, argv))
            self.assertEqual(files(old), files(new))
            self.assertEqual(len(files(new)), 16 if argv else 8)
            self.assertTrue(all(b"- /" in text for text in files(new).values()))
        for argv, code in ((["--help"], 0), (["--bad"], 2)):
            with (
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as error,
            ):
                run_main(native, self.root, argv)
            self.assertEqual(error.exception.code, code)
        with self.assertRaises(ValueError):
            native.finish(native.initialize(False))
        with self.assertRaises(IndexError):
            native.write_current_case({"index": 8}, self.root)

    def test_registered_tools_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["id"], "hub_formalphysics_extra_lean_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        for source in doc["provenance"]["sources"]:
            self.assertEqual(
                source["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "extra-lean",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile_doc(document, inventory=tools):
                received = assets(document)
                result = compile_workflow(
                    "mcp:extra-lean",
                    workflow_documents([DESCRIPTOR], received)[0],
                    inventory,
                )
                return result, received

            compiled, received = compile_doc(doc)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertTrue(compiled["runtime_source"])
            self.assertFalse(compile_doc(doc, [])[0]["runnable"])

            async def authorize():
                pass

            async def run(root, promote=False, document=None):
                workflow, data = (
                    compile_doc(document) if document else (compiled, received)
                )
                return await execute(
                    workflow,
                    data,
                    {"repository_root": str(root), "promote_lib": promote},
                    remote,
                    authorize,
                )

            for promote in (False, True):
                root = fixture(self.root / str(promote))
                old = fixture(self.root / ("oracle" + str(promote)))
                code, stdout = run_main(
                    oracle(), old, ["--promote-lib"] if promote else []
                )
                result = await run(root, promote)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"],
                    {"generated": stdout.splitlines(), "returncode": code},
                )
                self.assertEqual(files(root), files(old))
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    ["mathformer_extra_lean_initialize"]
                    + [
                        "mathformer_extra_lean_write_case",
                        "mathformer_extra_lean_advance",
                    ]
                    * 8
                    + ["mathformer_extra_lean_finish"],
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
            state = (
                await remote.call(
                    "mathformer_extra_lean_initialize", {"promote_lib": False}
                )
            )["state"]
            root = fixture(self.root / "states")
            for index in range(8):
                self.assertEqual(state["index"], index)
                paths = (
                    await remote.call(
                        "mathformer_extra_lean_write_case",
                        {"state": state, "repository_root": str(root)},
                    )
                )["paths"]
                before = deepcopy(state)
                result = await remote.call(
                    "mathformer_extra_lean_advance", {"state": state, "paths": paths}
                )
                state = result["state"]
                self.assertEqual(state["generated"], before["generated"] + paths)
                self.assertEqual(result["done"], index == 7)
                self.assertFalse(state["promote_lib"])
            broken = fixture(self.root / "broken")
            case, spec = list(native.CASES.items())[1]
            (
                broken
                / "data/benchmarks/formal_science/physics_top10_sources"
                / f"{spec['rank']}_{case}.tex"
            ).unlink()
            result = await run(broken)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(len(result["calls"]), 4)
            self.assertEqual(len(files(broken)), 1)
            # Real filesystem copy failure after the artifact was written.
            blocked = fixture(self.root / "blocked")
            first = next(iter(native.CASES))
            (
                blocked
                / "libraries/MathformerPhysicsLib/Lean"
                / first
                / "MathformerPhysics.lean"
            ).mkdir(parents=True)
            result = await run(blocked, True)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 2)
            self.assertEqual(len(files(blocked)), 1)
            bounded = deepcopy(doc)
            bounded["flow"]["steps"][1]["max_iterations"] = 7
            root = fixture(self.root / "exhaustion")
            result = await run(root, document=bounded)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 15)
            self.assertEqual(len(files(root)), 7)
            self.assertIn("exhaust", str(result).lower())
            budget = deepcopy(doc)
            budget["policy"]["limits"]["max_operation_calls"] = 2
            root = fixture(self.root / "budget")
            result = await run(root, document=budget)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(files(root)), 1)
            self.assertIn("budget", str(result).lower())
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
