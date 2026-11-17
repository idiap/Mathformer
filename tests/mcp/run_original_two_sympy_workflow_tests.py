#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native source, registered MCP, and real Lunar PRISM parity in scratch roots.

This source has no model/provider or external compiler boundary: its generator
and checks are deterministic Python/SymPy. The fixture supplies LaTeX inputs and
isolated output mounts; all scientific steps and five local validators run for
real. No credentials, external prover/compiler, or promotion are used.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
packages = next((ROOT / ".venv/lib").glob("python*/site-packages"))
os.environ["PYTHONPATH"] = os.pathsep.join(
    filter(None, [str(packages), os.environ.get("PYTHONPATH")])
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
import generate_formalphysics_original_two_sympy as native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_formalphysics_original_two_sympy_workflow/workflow.yaml"
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
    for name in ("scripts", "backends", *(["skills"] if tools else [])):
        (root / name).symlink_to(ROOT / name, target_is_directory=True)
    source = root / "data/benchmarks/formal_science/physics_top10_sources"
    source.mkdir(parents=True)
    for case, spec in native.CASES.items():
        (source / f"{spec['rank']}_{case}.tex").write_text(
            f"Deterministic source fixture for {case}.\n"
        )
    return root


def mount(module, root):
    return patch.multiple(
        module,
        REPO_ROOT=root,
        SOURCE_ROOT=root / "data/benchmarks/formal_science/physics_top10_sources",
        ARTIFACT_ROOT=root / "artifacts/physics_sympy/from_scratch_sympy",
        LIB_ROOT=root / "libraries/MathformerPhysicsLib/SymPy",
    )


def oracle():
    path = ROOT / "tests/mcp/fixtures/original_two_sympy_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "original_sympy_oracle", SourceFileLoader("original_sympy_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_main(module, root, argv):
    out = io.StringIO()
    with (
        mount(module, root),
        patch.object(sys, "argv", ["generate.py", *argv]),
        redirect_stdout(out),
    ):
        code = module.main()
    return code, out.getvalue()


def snapshot(doc):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in doc["provenance"]["sources"]
    ]


class SympyTests(unittest.TestCase):
    def test_native_and_registered_runtime(self):
        with tempfile.TemporaryDirectory(prefix="original-sympy-") as temp:
            asyncio.run(self.scenario(Path(temp)))

    async def scenario(self, directory):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_formalphysics_original_two_sympy_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        old = oracle()
        self.assertEqual(list(native.CASES), list(old.CASES))
        self.assertEqual(len(native.CASES), 10)
        oldroot = fixture(directory / "oracle")
        expected = run_main(old, oldroot, ["--json"])
        newroot = fixture(directory / "native")
        self.assertEqual(run_main(native, newroot, ["--json"]), expected)
        aggregate = json.loads(expected[1])
        self.assertEqual(expected[0], 0)
        for summary in aggregate["summaries"]:
            self.assertEqual(
                summary["source_sha256"],
                hashlib.sha256(
                    (newroot / summary["source_ref"]).read_bytes()
                ).hexdigest(),
            )
            self.assertEqual(
                json.loads((newroot / summary["reports"]["summary"]).read_text()),
                summary,
            )
            for path in summary["reports"].values():
                self.assertTrue((newroot / path).is_file(), path)
            self.assertEqual(
                (newroot / summary["artifact"]).read_bytes(),
                (oldroot / summary["artifact"]).read_bytes(),
            )
        with (
            redirect_stderr(io.StringIO()),
            patch.object(sys, "argv", ["script", "--bad"]),
            self.assertRaises(SystemExit),
        ):
            native.main()
        self.assertFalse((newroot / "libraries").exists())

        async def session(root, checks, mode=""):
            manager = SessionManager()
            config = StdioConfig(
                command=sys.executable,
                args=[
                    str(ROOT / "tests/mcp/fixtures/original_two_sympy_server.py"),
                    str(root),
                    mode,
                ],
                cwd=str(ROOT),
            )
            async with manager.open(
                "original-sympy", config, {"PYTHONPATH": os.environ["PYTHONPATH"]}
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    assets = snapshot(doc)
                    compiled = compile_workflow(
                        "mcp:original-sympy",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools if inventory is None else inventory,
                    )
                    return compiled, assets

                compiled, assets = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(doc=None, options=None, context=None):
                    selected, received = compile(doc) if doc else (compiled, assets)
                    return await execute(
                        selected,
                        received,
                        {"options": options or OPTIONS, "context": context or CONTEXT},
                        remote,
                        authorize,
                    )

                await checks(remote, run)
            self.assertFalse(manager.active)

        root = fixture(directory / "runtime")

        async def full(remote, run):
            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(
                result["outputs"],
                {"result": aggregate, "exit_code": expected[0], "stdout": expected[1]},
            )
            expected_calls = (
                ["initialize"]
                + ["select_case", "write_case", "advance"] * 10
                + ["aggregate", "emit_json"]
            )
            self.assertEqual(
                [c["tool"] for c in result["calls"]],
                ["mathformer_original_two_sympy_" + n for n in expected_calls],
            )
            self.assertTrue(result["runtime"]["effect_records"])
            self.assertTrue(result["replay_artifacts"])
            self.assertFalse((root / "libraries").exists())
            # Actual transported state, including incomplete summaries, never stops early.
            state = (await remote.call("mathformer_original_two_sympy_initialize", {}))[
                "state"
            ]
            for i, summary in enumerate(aggregate["summaries"]):
                selected = await remote.call(
                    "mathformer_original_two_sympy_select_case", {"state": state}
                )
                self.assertEqual(selected["case"]["id"], list(native.CASES)[i])
                s = deepcopy(summary)
                if i == 0:
                    s["status"] = "incomplete"
                advanced = await remote.call(
                    "mathformer_original_two_sympy_advance",
                    {"state": state, "summary": s, "summary_json": native.json_safe(s)},
                )
                self.assertEqual(
                    advanced["state"]["summaries"][:-1], state["summaries"]
                )
                self.assertEqual(advanced["done"], i == 9)
                state = advanced["state"]
            final = await remote.call(
                "mathformer_original_two_sympy_aggregate", {"state": state}
            )
            self.assertEqual(final["exit_code"], 3)
            self.assertFalse(final["result"]["ok"])
            text = await remote.call(
                "mathformer_original_two_sympy_emit_paths", {"result": final["result"]}
            )
            self.assertEqual(
                text["stdout"].splitlines(),
                [
                    s[k] if k == "artifact" else s["reports"][k]
                    for s in aggregate["summaries"]
                    for k in ("artifact", "summary", "consistency")
                ],
            )
            with self.assertRaises(Exception):
                await remote.call(
                    "mathformer_original_two_sympy_select_case", {"state": state}
                )
            for ctx in (
                {**CONTEXT, "allow_mutating": False},
                {**CONTEXT, "dry_run": True},
            ):
                denied = await run(context=ctx)
                self.assertEqual(denied["status"], "failed")
                self.assertEqual(len(denied["calls"]), 3)
            bounded = deepcopy(document)
            bounded["flow"]["steps"][1]["max_iterations"] = 1
            failed = await run(doc=bounded)
            self.assertEqual(failed["status"], "failed")
            self.assertIsNone(failed["outputs"])
            self.assertEqual(len(failed["calls"]), 4)
            self.assertIn("exhaust", str(failed).lower())
            budget = deepcopy(document)
            budget["policy"]["limits"]["max_operation_calls"] = 2
            failed = await run(doc=budget)
            self.assertEqual(failed["status"], "failed")
            self.assertIn("budget", str(failed).lower())
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in failed["calls"]), 2
            )
            paths = await run(options={**OPTIONS, "json": False})
            self.assertEqual(paths["status"], "accepted", paths)
            self.assertEqual(paths["outputs"]["stdout"], text["stdout"])

        await session(root, full)

        broken = fixture(directory / "broken")
        case, spec = list(native.CASES.items())[2]
        (
            broken
            / "data/benchmarks/formal_science/physics_top10_sources"
            / f"{spec['rank']}_{case}.tex"
        ).unlink()

        async def missing(remote, run):
            result = await run()
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(len(result["calls"]), 9)
            self.assertEqual(len(list((broken / "artifacts").rglob("summary.json"))), 2)
            self.assertFalse(
                (broken / "artifacts/physics_sympy/from_scratch_sympy" / case).exists()
            )
            with self.assertRaises(FileNotFoundError):
                run_main(old, broken, ["--json"])

        await session(broken, missing)
        absent = fixture(directory / "absent", tools=False)

        async def tool_failure(remote, run):
            result = await run()
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 3)
            self.assertIsNone(result["outputs"])
            self.assertFalse(list((absent / "artifacts").rglob("summary.json")))
            self.assertTrue(list((absent / "artifacts").rglob("workflow_plan.json")))
            with self.assertRaisesRegex(RuntimeError, "tool failed:"):
                run_main(old, absent, ["--json"])

        await session(absent, tool_failure)
        incomplete = fixture(directory / "incomplete")

        async def noncomplete(remote, run):
            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(result["outputs"]["exit_code"], 3)
            self.assertFalse(result["outputs"]["result"]["ok"])
            self.assertEqual(len(result["outputs"]["result"]["summaries"]), 10)
            self.assertEqual(len(result["calls"]), 33)

        await session(incomplete, noncomplete, mode="incomplete")


if __name__ == "__main__":
    unittest.main(verbosity=2)
