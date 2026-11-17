#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated native/MCP/PRISM parity tests. No model or Isabelle process exists here."""

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
from importlib.machinery import SourceFileLoader
import importlib.util
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
import generate_formalphysics_extra_isabelle as native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_formalphysics_extra_isabelle_workflow/workflow.yaml"


def oracle():
    path = ROOT / "tests/mcp/fixtures/extra_isabelle_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "extra_isabelle_oracle", SourceFileLoader("extra_isabelle_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(root):
    source = root / native.SOURCE_ROOT.relative_to(native.REPO_ROOT)
    source.mkdir(parents=True)
    for case, spec in native.CASES.items():
        (source / f"{spec['rank']}_{case}.tex").write_text(
            f"fixture {case} \\<close> <close>\n", encoding="utf-8"
        )
    return root


def context(module, root):
    return patch.multiple(
        module,
        REPO_ROOT=root,
        SOURCE_ROOT=root / "data/benchmarks/formal_science/physics_top10_sources",
        ARTIFACT_ROOT=root / "artifacts/physics_isabelle/from_scratch_isabelle",
        LIB_ROOT=root / "libraries/MathformerPhysicsLib/Isabelle",
    )


def run_main(module, root, argv):
    stream = io.StringIO()
    with (
        context(module, root),
        patch.object(sys, "argv", ["generate_formalphysics_extra_isabelle.py", *argv]),
        redirect_stdout(stream),
    ):
        code = module.main()
    return code, stream.getvalue()


def outputs(root):
    return {
        str(p.relative_to(root)): p.read_bytes()
        for base in ("artifacts", "libraries")
        for p in (root / base).rglob("*")
        if p.is_file()
    }


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


class IsabelleWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="extra-isabelle-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def test_native_parity_and_argparse(self):
        original = oracle()
        self.assertEqual(list(original.CASES), list(native.CASES))
        self.assertEqual(len(native.CASES), 8)
        for argv in ([], ["--promote-lib"]):
            old = fixture(self.directory / ("old" + str(len(argv))))
            new = fixture(self.directory / ("new" + str(len(argv))))
            self.assertEqual(run_main(native, new, argv), run_main(original, old, argv))
            self.assertEqual(outputs(new), outputs(old))
            self.assertEqual(len(outputs(new)), 32 if argv else 16)
        for argv, code in ((["--bad"], 2), (["--help"], 0)):
            with (
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as error,
            ):
                native.initialize(argv)
            self.assertEqual(error.exception.code, code)
        state = native.initialize([])
        files = {
            "artifact_theory": "a",
            "artifact_root": "b",
            "lib_theory": None,
            "lib_root": None,
        }
        with self.assertRaises(ValueError):
            native.advance(state, files, self.directory)
        with self.assertRaises(IndexError):
            native.write_case_at(8, False, self.directory)
        self.assertEqual(state, {"cursor": 0, "promote_lib": False, "generated": []})

    def test_real_registered_mcp_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_formalphysics_extra_isabelle_workflow")
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
            "extra-isabelle",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=tools):
                assets = snapshot(doc)
                selected = workflow_documents([DESCRIPTOR], assets)[0]
                return (
                    compile_workflow("mcp:extra-isabelle", selected, inventory),
                    assets,
                )

            compiled, assets = compile(document)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
            self.assertFalse(compile(document, [])[0]["runnable"])

            async def authorize():
                pass

            async def run(root, argv=None, doc=None):
                workflow, received = compile(doc) if doc else (compiled, assets)
                return await execute(
                    workflow,
                    received,
                    {"argv": argv or [], "repository_root": str(root)},
                    remote,
                    authorize,
                )

            for argv in ([], ["--promote-lib"]):
                root = fixture(self.directory / ("runtime" + str(len(argv))))
                old = fixture(self.directory / ("oracle" + str(len(argv))))
                code, stdout = run_main(oracle(), old, argv)
                result = await run(root, argv)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"],
                    {"generated": stdout.splitlines(), "exit_code": code},
                )
                self.assertEqual(outputs(root), outputs(old))
                self.assertEqual(len(result["calls"]), 18)
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    ["mathformer_extra_isabelle_initialize"]
                    + [
                        "mathformer_extra_isabelle_write_case",
                        "mathformer_extra_isabelle_advance",
                    ]
                    * 8
                    + ["mathformer_extra_isabelle_finish"],
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
            # Real input read failure on case two leaves exactly case one's files.
            broken = fixture(self.directory / "broken")
            second, spec = list(native.CASES.items())[1]
            (
                broken
                / "data/benchmarks/formal_science/physics_top10_sources"
                / f"{spec['rank']}_{second}.tex"
            ).unlink()
            failed = await run(broken)
            self.assertEqual(failed["status"], "failed", failed)
            self.assertIsNone(failed["outputs"])
            self.assertEqual(len(failed["calls"]), 4)
            self.assertEqual(len(outputs(broken)), 2)
            self.assertEqual(failed["calls"][-1]["status"], "rejected")
            # Real write error after theory output retains the partial theory.
            blocked = fixture(self.directory / "blocked")
            first = next(iter(native.CASES))
            target = (
                blocked / "artifacts/physics_isabelle/from_scratch_isabelle" / first
            )
            (target / "ROOT").mkdir(parents=True)
            failed = await run(blocked)
            self.assertEqual(failed["status"], "failed", failed)
            self.assertEqual(len(failed["calls"]), 2)
            self.assertTrue((target / "MathformerPhysics.thy").is_file())
            for argv in (["--bad"], ["--help"]):
                failed = await run(self.directory, argv)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(len(failed["calls"]), 1)
            # Transport real source state; done changes only at fixed cardinality.
            state = (
                await remote.call("mathformer_extra_isabelle_initialize", {"argv": []})
            )["state"]
            root = fixture(self.directory / "state")
            for cursor in range(8):
                self.assertEqual(state["cursor"], cursor)
                files = (
                    await remote.call(
                        "mathformer_extra_isabelle_write_case",
                        {
                            "cursor": cursor,
                            "promote_lib": False,
                            "repository_root": str(root),
                        },
                    )
                )["files"]
                old = deepcopy(state)
                result = await remote.call(
                    "mathformer_extra_isabelle_advance",
                    {"state": state, "files": files, "repository_root": str(root)},
                )
                state = result["state"]
                self.assertEqual(state["generated"][:-2], old["generated"])
                self.assertEqual(result["done"], cursor == 7)
                self.assertIsNone(files["lib_theory"])
            bounded = deepcopy(document)
            bounded["flow"]["steps"][1]["max_iterations"] = 7
            root = fixture(self.directory / "exhaustion")
            failed = await run(root, doc=bounded)
            self.assertEqual(failed["status"], "failed", failed)
            self.assertEqual(len(failed["calls"]), 15)
            self.assertEqual(len(outputs(root)), 14)
            self.assertIn("exhaust", str(failed).lower())
            budget = deepcopy(document)
            budget["policy"]["limits"]["max_operation_calls"] = 2
            root = fixture(self.directory / "budget")
            failed = await run(root, doc=budget)
            self.assertEqual(failed["status"], "failed", failed)
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in failed["calls"]), 2
            )
            self.assertEqual(len(outputs(root)), 2)
            self.assertIn("budget", str(failed).lower())
            timed = deepcopy(document)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            selected, received = compile(timed)

            async def pending():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(
                    selected,
                    received,
                    {"argv": [], "repository_root": str(root)},
                    remote,
                    pending,
                )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
