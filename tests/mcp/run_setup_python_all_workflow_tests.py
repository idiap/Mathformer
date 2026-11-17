#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Original/native parity and actual MCP + Lunar PRISM setup execution, offline."""

from tempfile import gettempdir

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
import asyncio
from contextlib import redirect_stdout
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
import install_env as native
from setup_all_boundary import Boundary, DEPS
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_setup_python_all_workflow/workflow.yaml"


def oracle():
    loader = SourceFileLoader(
        "setup_python_all_original",
        str(ROOT / "tests/mcp/fixtures/setup_python_all_original.py.txt"),
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in document["provenance"]["sources"]
    ]


def run_native(module, root, argv, mode="success"):
    stream = io.StringIO()
    boundary = Boundary(root, mode)
    with (
        patch.object(module, "ROOT_DIR", root),
        patch.dict(os.environ, {"VENV_PATH": "environment"}),
        patch.object(sys, "argv", ["install_env.py", *argv]),
        patch.object(module.shutil, "which", boundary.which),
        patch.object(module.subprocess, "run", boundary.run),
        redirect_stdout(stream),
    ):
        try:
            outcome = ("return", module.main())
        except (SystemExit, Exception) as error:
            outcome = (type(error).__name__, str(error))
    return outcome, stream.getvalue(), boundary.calls


class SetupTests(unittest.TestCase):
    def test_original_entrypoint_parity_and_branches(self):
        original = oracle()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            for mode in ("success", "missing_uv", "missing_python", "fail_1", "fail_2"):
                for module in (original, native):
                    import shutil

                    shutil.rmtree(root / "environment", ignore_errors=True)
                    value = run_native(module, root, ["--all-extras"], mode)
                    if module is original:
                        expected = value
                    else:
                        self.assertEqual(value, expected)
            for argv in (
                ["--skip-python"],
                ["--skip-python", "--with-lean"],
                ["--skip-python", "--with-lean", "--skip-lean"],
                [],
            ):
                expected = run_native(original, root, argv)
                self.assertEqual(run_native(native, root, argv), expected)
                if "--skip-python" in argv and "--with-lean" not in argv:
                    self.assertEqual(expected[2], [])
            with patch.object(native.sys, "version_info", (3, 9)):
                with self.assertRaisesRegex(SystemExit, "3.10"):
                    native.initialize(["--bad-argument"])
            args = native.parse_args(
                ["--all-extras", "--with-benchmarks", "--with-mcp"]
            )
            self.assertEqual(native.selected_python_deps(args), DEPS)
            requirements = root / "requirements.txt"
            requirements.write_text(
                "# comment\n\n mcp>=1.6,<2 \nsympy>=1.12,<2\nmcp>=1.6,<2\n"
            )
            with patch.object(native, "MCP_SERVICE_REQUIREMENTS", requirements):
                self.assertEqual(
                    native.selected_python_deps(
                        native.parse_args(["--mcp-service", "--all-extras"])
                    ),
                    [
                        "mcp>=1.6,<2",
                        "sympy>=1.12,<2",
                        "huggingface_hub>=0.23,<1",
                        "numpy>=1.26,<3",
                        "docling>=2",
                    ],
                )
            with self.assertRaises(SystemExit):
                native.read_requirements(root / "absent")
            with patch.object(native.os, "name", "nt"):
                self.assertEqual(
                    str(native.venv_python(root)), str(root / "Scripts/python.exe")
                )

    def test_authored_generator_contract(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        authored = json.loads(
            (
                ROOT
                / "skills/control/workflow-contract-validator/references/setup-python-all.workflow.json"
            ).read_text()
        )
        self.assertEqual(authored, document)
        generator = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        ).read_text()
        self.assertIn("if native == 'setup:python-all':", generator)
        self.assertIn(
            "references/setup-python-all.workflow.json".split("/")[-1], generator
        )

    def test_registered_tools_real_prism_and_failure_bounds(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_setup_python_all_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        for mode in (
            "success",
            "missing_uv",
            "missing_python",
            "fail_1",
            "fail_2",
            "readonly",
            "write_denied",
        ):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder).resolve()
                manager = SessionManager()
                failure = None
                async with manager.open(
                    "setup",
                    StdioConfig(
                        command=sys.executable,
                        args=[
                            "-B",
                            str(ROOT / "tests/mcp/fixtures/setup_python_all_server.py"),
                            mode,
                            str(root),
                        ],
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
                                    "mcp:setup",
                                    selected,
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

                        async def run(doc=None, authorized=True):
                            c, a = compile(doc) if doc else (compiled, assets)
                            return await execute(
                                c, a, {"allow_mutating": authorized}, remote, authorize
                            )

                        result = await run()
                        calls = (
                            [
                                json.loads(s)
                                for s in (root / "launches.jsonl")
                                .read_text()
                                .splitlines()
                            ]
                            if (root / "launches.jsonl").exists()
                            else []
                        )
                        if mode == "success":
                            self.assertEqual(result["status"], "accepted", result)
                            self.assertEqual(result["outputs"], {"exit_code": 0})
                            self.assertEqual(len(result["calls"]), 6)
                            self.assertEqual(
                                [c["tool"] for c in result["calls"]],
                                [
                                    "mathformer_setup_python_all_" + name
                                    for name in (
                                        "initialize",
                                        "prepare_environment",
                                        "select_dependencies",
                                        "install_dependencies",
                                        "setup_lean",
                                        "complete",
                                    )
                                ],
                            )
                            expected = run_native(oracle(), root, ["--all-extras"])
                            self.assertEqual(calls, expected[2])
                            self.assertEqual(
                                [r["command"][1] for r in calls], ["venv", "pip"]
                            )
                            self.assertFalse((root / ".lake").exists())
                            self.assertTrue(
                                native.venv_python(root / "environment").is_file()
                            )
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["replay_artifacts"])
                            # Settings preserve ambient VENV_PATH and immutable profile.
                            initialized = await remote.call(
                                "mathformer_setup_python_all_initialize", {}
                            )
                            self.assertEqual(
                                initialized["args"],
                                {
                                    k: (
                                        "environment"
                                        if k == "venv_path"
                                        else getattr(
                                            native.parse_args(["--all-extras"]), k
                                        )
                                    )
                                    for k in initialized["args"]
                                },
                            )
                            environment = {
                                "uv": str(
                                    Path(gettempdir())
                                    / "mathformer-test-fixtures/fixture/uv"
                                ),
                                "venv_path": str(root / "environment"),
                                "python_bin": str(
                                    native.venv_python(root / "environment")
                                ),
                            }
                            selected = await remote.call(
                                "mathformer_setup_python_all_select_dependencies",
                                {
                                    "args": initialized["args"],
                                    "environment": environment,
                                },
                            )
                            self.assertEqual(selected, {"dependencies": DEPS})
                            with self.assertRaises(ValueError):
                                await remote.call(
                                    "mathformer_setup_python_all_setup_lean",
                                    {"args": initialized["args"], "installed": False},
                                )
                            with self.assertRaises(ValueError):
                                await remote.call(
                                    "mathformer_setup_python_all_complete",
                                    {"finished": False},
                                )
                            malformed = deepcopy(initialized["args"])
                            malformed["skip_python"] = True
                            with self.assertRaises(ValueError):
                                await remote.call(
                                    "mathformer_setup_python_all_prepare_environment",
                                    {"args": malformed, "allow_mutating": True},
                                )
                            budget = deepcopy(document)
                            budget["policy"]["limits"]["max_operation_calls"] = 2
                            bounded = await run(budget)
                            self.assertEqual(bounded["status"], "failed")
                            self.assertIn("budget", str(bounded).lower())
                            self.assertEqual(
                                sum(
                                    bool(c.get("transport_call_performed"))
                                    for c in bounded["calls"]
                                ),
                                2,
                            )
                            self.assertNotIn(
                                "mathformer_setup_python_all_complete",
                                [c["tool"] for c in bounded["calls"]],
                            )
                            denied = await run(authorized=False)
                            self.assertEqual(denied["status"], "failed")
                            self.assertEqual(len(denied["calls"]), 2)
                            timed = deepcopy(document)
                            timed["policy"]["limits"]["wall_time_seconds"] = 1
                            c, a = compile(timed)

                            async def pending():
                                await asyncio.Event().wait()

                            with self.assertRaises(TimeoutError):
                                await execute(
                                    c, a, {"allow_mutating": True}, remote, pending
                                )
                        else:
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(result["calls"][-1]["status"], "rejected")
                            count = {
                                "missing_uv": 0,
                                "missing_python": 1,
                                "fail_1": 1,
                                "fail_2": 2,
                                "readonly": 0,
                                "write_denied": 0,
                            }[mode]
                            self.assertEqual(len(calls), count)
                            expected_steps = 4 if mode == "fail_2" else 2
                            self.assertEqual(len(result["calls"]), expected_steps)
                            self.assertNotIn(
                                "mathformer_setup_python_all_complete",
                                [c["tool"] for c in result["calls"]],
                            )
                    except Exception as error:
                        failure = error
                self.assertFalse(manager.active)
                if failure:
                    raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
