#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated native/MCP/PRISM parity tests. No model or Lean process exists here."""

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
import generate_formalphysics_original_two_lean as native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_formalphysics_original_two_lean_workflow/workflow.yaml"


def oracle():
    path = ROOT / "tests/mcp/fixtures/original_two_lean_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "original_two_lean_oracle",
        SourceFileLoader("original_two_lean_oracle", str(path)),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(root):
    source = root / native.SOURCE_ROOT.relative_to(native.REPO_ROOT)
    source.mkdir(parents=True)
    for case, spec in native.CASES.items():
        (source / f"{spec['rank']}_{case}.tex").write_text(
            f"fixture {case} -/\n", encoding="utf-8"
        )
    return root


def context(module, root):
    return patch.multiple(
        module,
        REPO_ROOT=root,
        SOURCE_ROOT=root / "data/benchmarks/formal_science/physics_top10_sources",
        ARTIFACT_ROOT=root / "artifacts/physics_lean/from_scratch_lean",
        LIB_ROOT=root / "libraries/MathformerPhysicsLib/Lean",
    )


def run_main(module, root, argv):
    stream = io.StringIO()
    with (
        context(module, root),
        patch.object(
            sys, "argv", ["generate_formalphysics_original_two_lean.py", *argv]
        ),
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


class LeanWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="original-two-lean-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def test_native_parity_and_errors(self):
        original = oracle()
        self.assertEqual(
            list(native.CASES), ["formalphysics_0000", "formalphysics_0020"]
        )
        old, new = fixture(self.directory / "old"), fixture(self.directory / "new")
        self.assertEqual(run_main(native, new, []), run_main(original, old, []))
        self.assertEqual(outputs(new), outputs(old))
        self.assertEqual(len(outputs(new)), 2)
        for text in outputs(new).values():
            self.assertTrue(text.startswith(b"import Mathlib"))
            self.assertIn(b"- /", text)
        for argv, code in ((["--bad"], 2), (["--help"], 0)):
            with (
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as error,
            ):
                native.initialize(argv)
            self.assertEqual(error.exception.code, code)
        with self.assertRaises(IndexError):
            native.select_case(["a", "b"])
        self.assertEqual(native.initialize([]), {"promote_lib": False, "generated": []})
        # Compare original and shared-step failures and their surviving files.
        for module, root in ((native, new), (original, old)):
            for p in (root / "artifacts").rglob("*.lean"):
                p.unlink()
            second, spec = list(module.CASES.items())[1]
            (
                root
                / "data/benchmarks/formal_science/physics_top10_sources"
                / f"{spec['rank']}_{second}.tex"
            ).unlink()
            stream = io.StringIO()
            with (
                context(module, root),
                patch.object(sys, "argv", ["generate.py"]),
                redirect_stdout(stream),
                self.assertRaises(FileNotFoundError),
            ):
                module.main()
            self.assertEqual(stream.getvalue(), "")
            self.assertEqual(len(outputs(root)), 1)
        self.assertEqual(outputs(new), outputs(old))

    def test_registered_mcp_and_real_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_formalphysics_original_two_lean_workflow")
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
            "original-two-lean",
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

                def compile(doc, inventory=tools):
                    assets = snapshot(doc)
                    selected = workflow_documents([DESCRIPTOR], assets)[0]
                    return (
                        compile_workflow("mcp:original-two-lean", selected, inventory),
                        assets,
                    )

                compiled, assets = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(root, doc=None, argv=None):
                    workflow, received = compile(doc) if doc else (compiled, assets)
                    return await execute(
                        workflow,
                        received,
                        {"argv": argv or [], "repository_root": str(root)},
                        remote,
                        authorize,
                    )

                root, old = fixture(self.directory / "runtime"), fixture(
                    self.directory / "oracle"
                )
                code, stdout = run_main(oracle(), old, [])
                result = await run(root)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"],
                    {"generated": stdout.splitlines(), "exit_code": code},
                )
                self.assertEqual(outputs(root), outputs(old))
                expected = (
                    ["initialize"]
                    + ["select_case", "write_case", "append_and_test"] * 2
                    + ["finish"]
                )
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    ["mathformer_original_two_lean_" + n for n in expected],
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
                self.assertFalse((root / "libraries").exists())
                # Transport state is real path accumulation; stop only after case two.
                initial = await remote.call(
                    "mathformer_original_two_lean_initialize", {"argv": []}
                )
                generated = initial["generated"]
                state_root = fixture(self.directory / "state")
                for cursor in range(2):
                    selected = await remote.call(
                        "mathformer_original_two_lean_select_case",
                        {"generated": generated},
                    )
                    self.assertEqual(selected["case"], list(native.CASES)[cursor])
                    written = (
                        await remote.call(
                            "mathformer_original_two_lean_write_case",
                            {
                                "case": selected["case"],
                                "promote_lib": False,
                                "repository_root": str(state_root),
                            },
                        )
                    )["written"]
                    self.assertIsNone(written["library"])
                    before = list(generated)
                    advanced = await remote.call(
                        "mathformer_original_two_lean_append_and_test",
                        {
                            "generated": generated,
                            "written": written,
                            "repository_root": str(state_root),
                        },
                    )
                    generated = advanced["generated"]
                    self.assertEqual(generated[:-1], before)
                    self.assertEqual(advanced["done"], cursor == 1)
                for argv in (["--promote-lib"], ["--bad"], ["--help"]):
                    with self.assertRaises(ExecutionRejected):
                        await run(root, argv=argv)
                    with self.assertRaises(Exception):
                        await remote.call(
                            "mathformer_original_two_lean_initialize", {"argv": argv}
                        )
                with self.assertRaises(Exception):
                    await remote.call(
                        "mathformer_original_two_lean_write_case",
                        {
                            "case": list(native.CASES)[0],
                            "promote_lib": True,
                            "repository_root": str(root),
                        },
                    )
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
                self.assertEqual(len(failed["calls"]), 6)
                self.assertEqual(failed["calls"][-1]["status"], "rejected")
                self.assertEqual(len(outputs(broken)), 1)
                blocked = fixture(self.directory / "blocked")
                first = next(iter(native.CASES))
                target = (
                    blocked
                    / "artifacts/physics_lean/from_scratch_lean"
                    / first
                    / "mathformer_typed_candidate.lean"
                )
                target.mkdir(parents=True)
                failed = await run(blocked)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(len(failed["calls"]), 3)
                self.assertEqual(outputs(blocked), {})
                bounded = deepcopy(document)
                bounded["flow"]["steps"][1]["max_iterations"] = 1
                exhausted = fixture(self.directory / "exhausted")
                failed = await run(exhausted, doc=bounded)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(len(failed["calls"]), 4)
                self.assertEqual(len(outputs(exhausted)), 1)
                self.assertIn("exhaust", str(failed).lower())
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 3
                failed = await run(fixture(self.directory / "budget"), doc=budget)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in failed["calls"]
                    ),
                    3,
                )
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
            except Exception:
                import traceback

                traceback.print_exc()
                raise
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
