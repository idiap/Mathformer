#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Credential-free fixtures through actual MCP bindings and Lunar/PRISM.

This diagnostic workflow has no provider or theorem compiler boundary to fake.
Package metadata and executable discovery are inspected; no executable is run.
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

# Reuse installed application dependencies alongside the Lunar runtime.
APPLICATION_SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(APPLICATION_SITES)

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
import yaml
import mathformer_mcp_service as native
import mcp_service_config as config_source
import probe_mcp_service_dependencies as dependencies
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mcp_service_self_check_workflow/workflow.yaml"


def oracle():
    path = ROOT / "tests/mcp/fixtures/self_check_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "self_check_oracle", SourceFileLoader("self_check_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.REPO_ROOT = ROOT
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
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in {r["path"]: r for r in document["provenance"]["sources"]}.values()
    ]


class SelfCheckTests(unittest.TestCase):
    def test_scan_state_and_native_branches(self):
        states = dependencies.initialize_scans()
        for key, step, count in [
            ("packages", dependencies.package_next, 10),
            ("tools", dependencies.tool_next, 6),
        ]:
            state = states[key]
            for cursor in range(count):
                previous = deepcopy(state)
                state = step(state)
                self.assertEqual(state["cursor"], cursor + 1)
                self.assertEqual(len(state["rows"]), cursor + 1)
                self.assertEqual(state["rows"][:-1], previous["rows"])
                self.assertEqual(state["done"], cursor + 1 == count)
                self.assertEqual(previous["cursor"], cursor)
            with self.assertRaises(ValueError):
                step(state)
            for bad in (
                {"cursor": -1, "rows": [], "done": False},
                {"cursor": 1, "rows": [], "done": False},
            ):
                with self.assertRaises(ValueError):
                    step(bad)
        missing = dependencies.classify_dependencies(
            [
                {
                    "name": "fixture",
                    "family": "mcp",
                    "required": True,
                    "available": False,
                }
            ],
            [],
        )
        blocked = dependencies.assemble_report([], [], missing, [], "blocked")
        self.assertTrue(blocked["ok"])
        self.assertFalse(blocked["ready"])
        config = config_source.ServiceConfig(
            deepcopy(config_source.DEFAULT_CONFIG), None, "local"
        )
        config.data["service"]["transport"] = "streamable-http"
        config.data["security"]["require_auth_for_http"] = True
        self.assertFalse(native.evaluate_self_check_auth(config)["ok"])
        example = config_source.ServiceConfig(config.data, None, "example")
        self.assertTrue(native.evaluate_self_check_auth(example)["ok"])
        auth = native.evaluate_self_check_auth(example)
        report = native.assemble_self_check_report(
            example, blocked, {"ok": True}, {"ok": True}, [], {}, auth
        )
        self.assertTrue(
            report["ok"]
        )  # blocked dependencies alone do not fail self-check
        for field in ("config", "dependencies", "router", "audit", "findings", "auth"):
            cfg, dep, router, audit, findings, a = (
                example,
                blocked,
                {"ok": True},
                {"ok": True},
                [],
                auth,
            )
            if field == "config":
                cfg = config_source.ServiceConfig(
                    example.data, None, "example", ("invalid",)
                )
            elif field == "dependencies":
                dep = {"ok": False}
            elif field == "router":
                router = {"ok": False}
            elif field == "audit":
                audit = {"ok": False}
            elif field == "findings":
                findings = [{"path": "fixture", "line": 1, "kind": "secret_like_value"}]
            else:
                a = {"ok": False}
            self.assertFalse(
                native.assemble_self_check_report(
                    cfg, dep, router, audit, findings, {}, a
                )["ok"]
            )
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            root = Path(folder)
            (root / "lines").write_text("ordinary\napi_key = " + "x" * 40 + "\n")
            findings = config_source.scan_paths_for_secrets(
                [root / "absent", root, root / "lines"], repo_root=root
            )
            self.assertEqual(
                findings, [{"path": "lines", "line": 2, "kind": "secret_like_value"}]
            )

    def test_registered_tools_and_real_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_mcp_service_self_check_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        original = oracle()
        manager = SessionManager()
        server = (
            "import sys;sys.path.extend("
            + repr(APPLICATION_SITES)
            + ');sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        )
        failure = None
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            directory = Path(folder)
            async with manager.open(
                "self-check",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
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
                        compiled = compile_workflow(
                            "mcp:self-check",
                            selected,
                            tools if inventory is None else inventory,
                        )
                        return compiled, assets

                    compiled, assets = compile(document)
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(
                        set(compiled["bindings"]), set(document["operations"])
                    )
                    self.assertFalse(compile(document, [])[0]["runnable"])

                    async def authorize():
                        pass

                    async def run(path, doc=None):
                        c, a = compile(doc) if doc else (compiled, assets)
                        return await execute(
                            c, a, {"config_path": str(path)}, remote, authorize
                        )

                    # Ordinary invalid diagnostics still execute all nine steps.
                    for filename, text in [
                        ("stdio.toml", ""),
                        (
                            "http.example.toml",
                            '[service]\ntransport="streamable-http"\n[security]\nrequire_auth_for_http=true\n',
                        ),
                        (
                            "http.toml",
                            '[service]\ntransport="streamable-http"\n[security]\nrequire_auth_for_http=true\n',
                        ),
                        ("missing.toml", None),
                        ("malformed.toml", "not toml"),
                    ]:
                        path = directory / filename
                        if text is not None:
                            path.write_text(text)
                        original_expected = original.self_check(path)
                        expected = native.self_check(path)
                        extended = deepcopy(original_expected)
                        extended["service_coverage"]["mcp_tools"][:0] = [
                            "mathformer_self_check_" + n for n in document["operations"]
                        ]
                        self.assertEqual(expected, extended)
                        result = await run(path)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            result["outputs"],
                            {
                                "report": expected,
                                "exit_code": 0 if expected["ok"] else 1,
                                "stdout": json.dumps(expected, indent=2, sort_keys=True)
                                + "\n",
                            },
                        )
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            [
                                "mathformer_self_check_" + n
                                for n in document["operations"]
                            ],
                        )
                        self.assertEqual(len(result["calls"]), 9)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = original.main(
                                ["--config", str(path), "--self-check", "--json"]
                            )
                        self.assertEqual(code, result["outputs"]["exit_code"])
                        self.assertEqual(
                            stream.getvalue(),
                            json.dumps(original_expected, indent=2, sort_keys=True)
                            + "\n",
                        )
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = native.main(
                                ["--config", str(path), "--self-check", "--json"]
                            )
                        self.assertEqual(code, result["outputs"]["exit_code"])
                        self.assertEqual(stream.getvalue(), result["outputs"]["stdout"])
                        if filename == "http.toml":
                            self.assertFalse(expected["auth_policy"]["ok"])
                        if filename == "http.example.toml":
                            self.assertTrue(expected["auth_policy"]["ok"])
                    # Actual source exception at report assembly terminates before emit.
                    path = directory / "bad-port.toml"
                    path.write_text('[service]\nport="bad"\n')
                    with self.assertRaises(ValueError):
                        original.self_check(path)
                    with self.assertRaises(ValueError):
                        native.self_check(path)
                    result = await run(path)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 8)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    # Explicit descriptor budgets, distinct from native finite scans.
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 2
                    result = await run(directory / "stdio.toml", bounded)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        2,
                    )
                    self.assertIn("budget", str(result).lower())
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    c, a = compile(timed)

                    async def pending():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(
                            c,
                            a,
                            {"config_path": str(directory / "stdio.toml")},
                            remote,
                            pending,
                        )
                    # Compile the actual terminal graph with diagnostic values as
                    # fixture inputs. This reaches success even if this checkout's
                    # native hub audit reports unrelated uncontrolled entrypoints.
                    terminal = deepcopy(document)
                    terminal["inputs"] = deepcopy(
                        document["operations"]["assemble_report"]["inputs"]
                    )
                    terminal["operations"] = {
                        n: deepcopy(document["operations"][n])
                        for n in ("assemble_report", "emit")
                    }
                    terminal["flow"]["steps"] = deepcopy(document["flow"]["steps"][-2:])
                    terminal["flow"]["steps"][0]["arguments"] = {
                        n: {"ref": "inputs." + n} for n in terminal["inputs"]
                    }
                    c, a = compile(terminal)
                    self.assertTrue(c["runnable"], c["diagnostics"])
                    loaded = await remote.call(
                        "mathformer_self_check_load_config",
                        {"config_path": str(directory / "stdio.toml")},
                    )
                    deps = native.dependency_probe()
                    # Data fixture: missing required availability is classified by
                    # the real dependency source, not a replacement implementation.
                    packages = deepcopy(deps["python_packages"])
                    packages[0]["available"] = False
                    missing = dependencies.classify_dependencies(
                        packages, deps["external_tools"]
                    )
                    deps = dependencies.assemble_report(
                        packages,
                        deps["external_tools"],
                        missing,
                        deps["requirements"],
                        "blocked",
                    )
                    values = {
                        "config": loaded["config"],
                        "dependencies": deps,
                        "router": {"ok": True},
                        "audit": {"ok": True},
                        "findings": [],
                        "coverage": native.service_coverage_report(
                            directory / "stdio.toml", loaded["config"]["data"]
                        ),
                        "auth": native.evaluate_self_check_auth(
                            config_source.load_service_config(
                                directory / "stdio.toml", require_existing=True
                            )
                        ),
                    }
                    result = await execute(c, a, values, remote, authorize)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertTrue(result["outputs"]["report"]["ok"])
                    self.assertFalse(
                        result["outputs"]["report"]["dependencies"]["ready"]
                    )
                    self.assertEqual(result["outputs"]["exit_code"], 0)
                    self.assertEqual(len(result["calls"]), 2)
                    # Both exit values pass through the real registered emitter.
                    for ok in (True, False):
                        emitted = await remote.call(
                            "mathformer_self_check_emit",
                            {"report": {"ok": ok}, "exit_code": 0 if ok else 1},
                        )
                        self.assertEqual(
                            emitted,
                            {
                                "exit_code": 0 if ok else 1,
                                "stdout": json.dumps(
                                    {"ok": ok}, indent=2, sort_keys=True
                                )
                                + "\n",
                            },
                        )
                except Exception as error:
                    failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
