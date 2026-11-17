#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic uv boundary, real native steps, MCP and Lunar/PRISM runtime.

There is no model or theorem compiler in this workflow. Only the external uv
lock resolver/checker process is substituted; no production uv command runs.
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
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml
from dependency_lock_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.contracts import workflow_documents
from mcp_connections.execution import execute, ExecutionRejected
from mcp_connections.models import StdioConfig
from mcp_connections.workflow_compiler import compile_workflow

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_environment_dependency_lock_workflow/workflow.yaml"
PROFILES = ["physics", "mcp", "documents", "providers", "knowledge-base"]
PACKAGES = ["sympy", "mcp", "docling", "openai", "anthropic", "huggingface-hub"]


def uv_fixture(argv, **kwargs):
    """Strict external-process fixture: validates native invocation and records it."""
    assert argv == ["uv", "lock", "--check"], argv
    assert set(kwargs) == {"cwd", "text", "capture_output"}, kwargs
    assert kwargs["text"] is True and kwargs["capture_output"] is True
    root = Path(kwargs["cwd"])
    config = json.loads((root / "uv-fixture.json").read_text())
    with (root / "uv-calls.jsonl").open("a") as stream:
        stream.write(
            json.dumps(
                {"argv": argv, "cwd": str(root), "text": True, "capture_output": True}
            )
            + "\n"
        )
    if config.get("launch_error"):
        raise FileNotFoundError("fixture uv executable absent")
    return SimpleNamespace(
        returncode=config["returncode"],
        stdout=config["stdout"],
        stderr=config["stderr"],
    )


if "--server" in sys.argv:
    # Import production registration, then substitute only the external process.
    from mcp_server import mcp

    source().subprocess = SimpleNamespace(run=uv_fixture)
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


class DependencyLockTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dependency-lock-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project = "\n".join(p + " = []" for p in PROFILES)
        self.lock = 'requires-python = ">=3.10"\n' + "\n".join(
            'name = "' + p + '"' for p in PACKAGES
        )
        self.reset()
        path = ROOT / "tests/mcp/fixtures/dependency_lock_original.py.txt"
        spec = importlib.util.spec_from_loader(
            "_dependency_oracle", SourceFileLoader("_dependency_oracle", str(path))
        )
        self.oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.oracle)

    def reset(self, code=0, launch_error=False):
        for name, text in [("pyproject.toml", self.project), ("uv.lock", self.lock)]:
            path = self.root / name
            if path.is_dir():
                path.rmdir()
            path.write_text(text)
        (self.root / "uv-fixture.json").write_text(
            json.dumps(
                {
                    "returncode": code,
                    "stdout": "resolved 雪\n",
                    "stderr": "diagnostic\n",
                    "launch_error": launch_error,
                }
            )
        )
        (self.root / "uv-calls.jsonl").write_text("")

    def cli(self, module, flag):
        stream = io.StringIO()
        with (
            patch.object(module, "REPO_ROOT", self.root),
            patch.object(module, "subprocess", SimpleNamespace(run=uv_fixture)),
            patch.object(
                sys, "argv", ["dependency-lock", *(["--json"] if flag else [])]
            ),
            redirect_stdout(stream),
        ):
            code = module.main()
        return code, stream.getvalue()

    def calls(self):
        return [
            json.loads(s)
            for s in (self.root / "uv-calls.jsonl").read_text().splitlines()
        ]

    def test_original_entrypoint_parity_and_all_bounded_checks(self):
        scenarios = [
            ("success", None, None),
            ("uv-fails", None, None),
            ("missing-project", None, None),
            ("missing-lock", None, None),
            ("abi", None, None),
        ]
        scenarios += [("profile", p, None) for p in PROFILES]
        scenarios += [("package", p, None) for p in PACKAGES]
        for name, item, _ in scenarios:
            for flag in [False, True]:
                with self.subTest(name=name, item=item, json=flag):
                    self.reset(code=7 if name == "uv-fails" else 0)
                    if name == "missing-project":
                        (self.root / "pyproject.toml").unlink()
                    if name == "missing-lock":
                        (self.root / "uv.lock").unlink()
                    if name == "profile":
                        (self.root / "pyproject.toml").write_text(
                            self.project.replace(item + " = [", item + " =(")
                        )
                    if name == "package":
                        (self.root / "uv.lock").write_text(
                            self.lock.replace('name = "' + item + '"', "removed")
                        )
                    if name == "abi":
                        (self.root / "uv.lock").write_text(
                            self.lock.replace("requires-python", "absent")
                        )
                    expected = self.cli(self.oracle, flag)
                    self.assertEqual(self.cli(source(), flag), expected)
                    self.assertEqual(expected[0], 0 if name == "success" else 1)
                    self.assertEqual(
                        len(self.calls()), 2
                    )  # exactly one invocation per CLI
                    if flag:
                        payload = json.loads(expected[1])
                        self.assertEqual(payload["ok"], name == "success")
                        self.assertEqual(len(payload["cases"]), 6)
                        self.assertEqual(payload["uv_stdout"], "resolved 雪\n")
                    else:
                        self.assertEqual(
                            expected[1], "PASS\n" if name == "success" else "FAIL\n"
                        )
        self.reset(launch_error=True)
        for module in [self.oracle, source()]:
            with self.assertRaises(FileNotFoundError):
                self.cli(module, True)
        self.assertEqual(len(self.calls()), 2)
        self.reset()
        (self.root / "uv.lock").unlink()
        (self.root / "uv.lock").mkdir()
        for module in [self.oracle, source()]:
            with self.assertRaises(IsADirectoryError):
                self.cli(module, True)
        # Presence is rechecked during evaluate, rather than inferred from texts.
        self.reset()
        texts = source().read_files(self.root)
        (self.root / "uv.lock").unlink()
        payload = source().build_payload(
            self.root, {"returncode": 0, "stdout": "", "stderr": ""}, texts
        )
        self.assertFalse(payload["cases"]["lock_present"])
        self.assertTrue(payload["cases"]["reference_packages_locked"])

    def test_registered_mcp_lunar_runtime_and_stopping(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_environment_dependency_lock_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 4},
        )
        self.assertIn(
            "tests/environment/run_dependency_lock_contract.py",
            [s["path"] for s in document["provenance"]["sources"]],
        )
        for s in document["provenance"]["sources"]:
            self.assertEqual(
                s["digest"],
                "sha256:" + hashlib.sha256((ROOT / s["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        async with manager.open(
            "dependency-lock",
            StdioConfig(
                command=sys.executable,
                args=[str(Path(__file__).resolve()), "--server"],
                cwd=str(ROOT),
            ),
            {"LUNAR_PLATFORM_ROOT": str(LUNAR)},
        ) as remote:
            inventory = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, tools=inventory):
                assets = snapshot(doc)
                return (
                    compile_workflow(
                        "mcp:dependency-lock",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools,
                    ),
                    assets,
                )

            compiled, assets = compile(document)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
            self.assertFalse(compile(document, [])[0]["runnable"])

            async def allow():
                pass

            async def run(doc=document, flag=True):
                c, a = compile(doc)
                self.assertTrue(c["runnable"], c["diagnostics"])
                return await execute(
                    c,
                    a,
                    {
                        "json_output": flag,
                        "context": {"repository_root": str(self.root)},
                    },
                    remote,
                    allow,
                )

            for scenario in [
                "success",
                "uv-fails",
                "missing",
                "profile-package",
                "abi",
            ]:
                for flag in [False, True]:
                    self.reset(code=4 if scenario == "uv-fails" else 0)
                    if scenario == "missing":
                        (self.root / "pyproject.toml").unlink()
                        (self.root / "uv.lock").unlink()
                    if scenario == "profile-package":
                        (self.root / "pyproject.toml").write_text("")
                        (self.root / "uv.lock").write_text("requires-python")
                    if scenario == "abi":
                        (self.root / "uv.lock").write_text(
                            self.lock.replace("requires-python", "absent")
                        )
                    expected_code, expected_stdout = self.cli(self.oracle, flag)
                    _, expected_json = self.cli(self.oracle, True)
                    (self.root / "uv-calls.jsonl").write_text("")
                    r = await run(flag=flag)
                    self.assertEqual(r["status"], "accepted", r)
                    self.assertEqual(
                        r["outputs"],
                        {
                            "payload": json.loads(expected_json),
                            "stdout": expected_stdout,
                            "exit_code": expected_code,
                        },
                    )
                    self.assertEqual(
                        [c["tool"] for c in r["calls"]],
                        [
                            "mathformer_dependency_lock_" + n
                            for n in [
                                "check_uv",
                                "read_files",
                                "build_payload",
                                "print_and_return",
                            ]
                        ],
                    )
                    self.assertEqual(len(self.calls()), 1)
                    self.assertTrue(r["runtime"]["effect_records"])
                    self.assertTrue(r["runtime"]["provenance"])
                    self.assertTrue(r["replay_artifacts"])
            self.reset(launch_error=True)
            r = await run()
            self.assertEqual(r["status"], "failed", r)
            self.assertIsNone(r["outputs"])
            self.assertEqual(len(r["calls"]), 1)
            self.assertEqual(len(self.calls()), 1)  # no retry or downstream steps
            self.reset()
            (self.root / "pyproject.toml").unlink()
            (self.root / "pyproject.toml").mkdir()
            r = await run()
            self.assertEqual(r["status"], "failed", r)
            self.assertEqual(len(r["calls"]), 2)
            self.assertEqual(len(self.calls()), 1)
            self.reset()
            bounded = deepcopy(document)
            bounded["policy"]["limits"]["max_operation_calls"] = 3
            r = await run(bounded)
            self.assertEqual(r["status"], "failed", r)
            self.assertIsNone(r["outputs"])
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in r["calls"]), 3
            )
            self.assertEqual(len(self.calls()), 1)
            c, a = compile(document)
            with self.assertRaises(ExecutionRejected):
                await execute(
                    c,
                    a,
                    {
                        "json_output": "true",
                        "context": {"repository_root": str(self.root)},
                    },
                    remote,
                    allow,
                )
            self.assertEqual(len(self.calls()), 1)
            timed = deepcopy(document)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            c, a = compile(timed)

            async def pending():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(
                    c,
                    a,
                    {
                        "json_output": True,
                        "context": {"repository_root": str(self.root)},
                    },
                    remote,
                    pending,
                )
            self.assertEqual(len(self.calls()), 1)
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
