#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Run actual source steps, registered MCP and real Lunar/PRISM in scratch roots.

The fixed source has no provider or external compiler boundary. SymPy artifact
rendering, imports, checks, five helper processes, reports and audits run for real.
Only filesystem inputs/mounts differ from production. No promotion is performed.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
# Lunar owns PRISM. Reuse the project-installed scientific packages as well.
project_packages = next((ROOT / ".venv/lib").glob("python*/site-packages"))
os.environ["PYTHONPATH"] = os.pathsep.join(
    filter(None, [str(project_packages), os.environ.get("PYTHONPATH")])
)
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
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
import generate_formalphysics_extra_sympy as native
import generate_formalphysics_original_two_sympy as helper
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_formalphysics_extra_sympy_workflow/workflow.yaml"
OPTIONS = {"json": True, "promote_lib": False}
CONTEXT = {
    "dry_run": False,
    "json_output": True,
    "keep_going": False,
    "allow_mutating": True,
    "write_report": False,
}


def fixture(root, tools=True):
    root.mkdir(parents=True)
    for name in ("scripts", "backends", "libraries", *(["skills"] if tools else [])):
        (root / name).symlink_to(ROOT / name, target_is_directory=True)
    source = root / "data/benchmarks/formal_science/physics_top10_sources"
    source.mkdir(parents=True)
    for case, spec in native.CASES.items():
        (source / f"{spec['rank']}_{case}.tex").write_text(
            f"Deterministic source fixture for {case}.\n"
        )
    (root / "unchanged.txt").write_text("before snapshot: preserve this file\n")
    return root


def mount(root):
    return patch.multiple(
        helper,
        REPO_ROOT=root,
        SOURCE_ROOT=root / "data/benchmarks/formal_science/physics_top10_sources",
        ARTIFACT_ROOT=root / "artifacts/physics_sympy/from_scratch_sympy",
        LIB_ROOT=root / "libraries/MathformerPhysicsLib/SymPy",
    )


def oracle():
    path = ROOT / "tests/mcp/fixtures/extra_sympy_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "extra_sympy_oracle", SourceFileLoader("extra_sympy_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_main(module, root, argv):
    stream = io.StringIO()
    with (
        mount(root),
        patch.object(sys, "argv", ["generate_formalphysics_extra_sympy.py", *argv]),
        redirect_stdout(stream),
    ):
        code = module.main()
    return code, stream.getvalue()


def snapshot(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    schema = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
    return [
        asset(DESCRIPTOR, json.dumps(document)),
        asset(schema, (ROOT / schema).read_text()),
    ] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


class SympyWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="extra-sympy-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )

    def test_source_shared_steps_and_original_aggregate(self):
        original = oracle()
        self.assertEqual(list(native.CASES), list(original.CASES))
        old_root, new_root = fixture(self.directory / "old"), fixture(
            self.directory / "new"
        )
        expected = run_main(original, old_root, ["--json"])
        actual = run_main(native, new_root, ["--json"])
        self.assertEqual(actual, expected)
        code, text = actual
        result = json.loads(text)
        self.assertEqual(code, 0)
        self.assertEqual(result["case_count"], 8)
        self.assertEqual(
            [s["case_id"] for s in result["summaries"]], list(native.CASES)
        )
        for summary in result["summaries"]:
            case = summary["case_id"]
            spec = native.CASES[case]
            source = (
                new_root
                / "data/benchmarks/formal_science/physics_top10_sources"
                / f"{spec['rank']}_{case}.tex"
            )
            self.assertEqual(
                summary["source_sha256"],
                hashlib.sha256(source.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                (new_root / summary["artifact"]).read_bytes(),
                (old_root / summary["artifact"]).read_bytes(),
            )
            self.assertEqual(
                json.loads((new_root / summary["reports"]["summary"]).read_text()),
                summary,
            )
            for path in summary["reports"].values():
                self.assertTrue((new_root / path).is_file(), path)
        # Test native formatting and aggregate failure as pure data, no step replacement.
        incomplete = deepcopy(result["summaries"])
        incomplete[0]["status"] = "incomplete"
        for summaries, expected_code in ((result["summaries"], 0), (incomplete, 3)):
            stream = io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(
                    native.finish(summaries, {"json": False}), expected_code
                )
            self.assertEqual(
                stream.getvalue().splitlines(),
                [
                    p
                    for s in summaries
                    for p in (
                        s["artifact"],
                        s["reports"]["summary"],
                        s["reports"]["consistency"],
                    )
                ],
            )
        with (
            redirect_stderr(io.StringIO()),
            patch.object(sys, "argv", ["extra", "--invalid"]),
            self.assertRaises(SystemExit) as error,
        ):
            native.main()
        self.assertEqual(error.exception.code, 2)
        # Real input failure interrupts both entrypoints before any aggregate.
        for module, name in ((native, "new-fail"), (original, "old-fail")):
            root = fixture(self.directory / name)
            next((root / "data").rglob("*0066.tex")).unlink()
            with self.assertRaises(FileNotFoundError):
                run_main(module, root, ["--json"])
            self.assertFalse((root / "artifacts").exists())
        self.assertFalse(
            (new_root / "libraries/MathformerPhysicsLib/SymPy").resolve()
            == new_root / "libraries/MathformerPhysicsLib/SymPy"
        )

    def test_registered_mcp_real_prism_runtime_and_stopping(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = self.document
        self.assertEqual(document["id"], "hub_formalphysics_extra_sympy_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 20},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

        async def scenario(root, mode="", checks=None):
            manager = SessionManager()
            config = StdioConfig(
                command=sys.executable,
                args=[
                    str(ROOT / "tests/mcp/fixtures/extra_sympy_server.py"),
                    str(root),
                    mode,
                ],
                cwd=str(ROOT),
            )
            async with manager.open(
                "extra-sympy", config, {"PYTHONPATH": os.environ["PYTHONPATH"]}
            ) as remote:
                failure = None
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile(doc, inventory=None):
                        assets = snapshot(doc)
                        return (
                            compile_workflow(
                                "mcp:extra-sympy",
                                workflow_documents([DESCRIPTOR], assets)[0],
                                tools if inventory is None else inventory,
                            ),
                            assets,
                        )

                    compiled, assets = compile(document)
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(
                        set(compiled["bindings"]), set(document["operations"])
                    )
                    self.assertFalse(compile(document, [])[0]["runnable"])

                    async def authorize():
                        pass

                    async def run(context=None, doc=None):
                        selected, received = compile(doc) if doc else (compiled, assets)
                        return await execute(
                            selected,
                            received,
                            {"context": context or CONTEXT, "options": OPTIONS},
                            remote,
                            authorize,
                        )

                    await checks(remote, run, compile)
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure

        async def full(remote, run, compile):
            for ctx in (
                {**CONTEXT, "allow_mutating": False},
                {**CONTEXT, "dry_run": True},
            ):
                result = await run(ctx)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [
                        "mathformer_extra_sympy_prepare",
                        "mathformer_extra_sympy_initialize",
                        "mathformer_extra_sympy_skip",
                        "mathformer_extra_sympy_return_boundary",
                    ],
                )
                payload = result["outputs"]["result"]
                self.assertEqual(payload["ok"], ctx["dry_run"])
                self.assertEqual(bool(payload["preflight_errors"]), not ctx["dry_run"])
                self.assertNotIn("write_audit", payload)
                self.assertFalse((root / "artifacts").exists())
            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            payload = result["outputs"]["result"]
            aggregate = json.loads(payload["stdout"])
            self.assertEqual(payload["returncode"], 0)
            self.assertEqual(aggregate["case_count"], 8)
            self.assertEqual(
                [s["case_id"] for s in aggregate["summaries"]], list(native.CASES)
            )
            self.assertTrue(aggregate["ok"])
            self.assertEqual(len(result["calls"]), 20)
            self.assertEqual(
                [c["tool"] for c in result["calls"]],
                ["mathformer_extra_sympy_prepare", "mathformer_extra_sympy_initialize"]
                + ["mathformer_extra_sympy_visit", "mathformer_extra_sympy_advance"] * 8
                + ["mathformer_extra_sympy_finish", "mathformer_extra_sympy_audit"],
            )
            self.assertEqual(payload["status"], "undeclared_writes")
            self.assertFalse(payload["ok"])
            self.assertNotIn(
                "unchanged.txt", payload["write_audit"]["unexpected_paths"]
            )
            self.assertTrue(
                all(
                    p.startswith("artifacts/physics_sympy/")
                    for p in payload["write_audit"]["unexpected_paths"]
                )
            )
            self.assertTrue(result["runtime"]["effect_records"])
            self.assertTrue(result["replay_artifacts"])
            # Compare transported native result with original entrypoint's actual helper run.
            old = fixture(self.directory / "runtime-oracle")
            self.assertEqual(
                (payload["returncode"], payload["stdout"]),
                run_main(oracle(), old, ["--json"]),
            )
            # Enforce source-authority and route specialization even on direct tool calls.
            state = (await remote.call("mathformer_extra_sympy_initialize", {}))[
                "state"
            ]
            for args in (
                {"options": {"json": True, "promote_lib": True}, "context": CONTEXT},
                {"options": OPTIONS, "context": {**CONTEXT, "allow_mutating": False}},
            ):
                with self.assertRaises(Exception):
                    await remote.call(
                        "mathformer_extra_sympy_visit", {"state": state, **args}
                    )
            # A shortened loop exhausts; there is no fabricated successful aggregate/audit.
            bounded = deepcopy(document)
            bounded["flow"]["steps"][2]["max_iterations"] = 1
            exhausted = await run(doc=bounded)
            self.assertEqual(exhausted["status"], "failed", exhausted)
            self.assertIsNone(exhausted["outputs"])
            self.assertEqual(len(exhausted["calls"]), 4)
            budget = deepcopy(document)
            budget["policy"]["limits"]["max_operation_calls"] = 2
            failed = await run(doc=budget)
            self.assertEqual(failed["status"], "failed")
            self.assertIn("budget", str(failed).lower())
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in failed["calls"]), 2
            )

        root = fixture(self.directory / "runtime")
        await scenario(root, checks=full)

        async def failed_source(remote, run, compile):
            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            payload = result["outputs"]["result"]
            self.assertEqual(payload["returncode"], 1)
            self.assertEqual(payload["stdout"], "")
            self.assertIn("FileNotFoundError", payload["stderr"])
            self.assertEqual(
                len(result["calls"]), 10
            )  # two completed, then termination; audit still runs
            self.assertEqual(len(list((broken / "artifacts").rglob("summary.json"))), 2)
            self.assertFalse(
                any("0119" in str(p) for p in (broken / "artifacts").rglob("*"))
            )

        broken = fixture(self.directory / "broken")
        spec = native.CASES["formalphysics_0172"]
        (
            broken
            / "data/benchmarks/formal_science/physics_top10_sources"
            / f"{spec['rank']}_formalphysics_0172.tex"
        ).unlink()
        await scenario(broken, checks=failed_source)

        async def failed_helper(remote, run, compile):
            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            payload = result["outputs"]["result"]
            self.assertEqual(payload["returncode"], 1)
            self.assertIn("tool failed:", payload["stderr"])
            self.assertEqual(payload["stdout"], "")
            self.assertEqual(len(result["calls"]), 6)
            self.assertFalse(list((no_tools / "artifacts").rglob("summary.json")))
            self.assertTrue(list((no_tools / "artifacts").rglob("workflow_plan.json")))

        no_tools = fixture(self.directory / "missing-helper", tools=False)
        await scenario(no_tools, checks=failed_helper)

        async def incomplete(remote, run, compile):
            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            payload = result["outputs"]["result"]
            aggregate = json.loads(payload["stdout"])
            self.assertEqual(len(aggregate["summaries"]), 8)
            self.assertFalse(aggregate["ok"])
            self.assertEqual(payload["returncode"], 3)
            self.assertEqual(len(result["calls"]), 20)

        await scenario(
            fixture(self.directory / "incomplete"), mode="incomplete", checks=incomplete
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
