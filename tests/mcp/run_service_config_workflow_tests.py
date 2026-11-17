#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native CLI parity and registered MCP tools through real Lunar/PRISM execution."""

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
import yaml
import mcp_service_config as native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mcp_service_config_workflow/workflow.yaml"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])


def original(root):
    path = ROOT / "tests/mcp/fixtures/mcp_service_config_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "service_original_oracle",
        SourceFileLoader("service_original_oracle", str(path)),
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.REPO_ROOT = root
    module.CONFIG_ROOT = root / "config"
    module.DEFAULT_LOCAL_CONFIG = module.CONFIG_ROOT / "mathformer_mcp.local.toml"
    module.EXAMPLE_CONFIG = module.CONFIG_ROOT / "mathformer_mcp.example.toml"
    return module


def cli(module, argv, root):
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code = (
                module.main(argv, repo_root=root)
                if module is native
                else module.main(argv)
            )
        except SystemExit as error:
            code = error.code
    return code, stdout.getvalue(), stderr.getvalue()


def asset(path, text):
    return {
        "path": path,
        "content": text,
        "encoding": "text",
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def snapshot(document):
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


class ServiceConfigTests(unittest.TestCase):
    def test_native_entrypoint_parity_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            oracle = original(root)
            cases = [
                ("", []),
                ("", ["--config", "missing.toml"]),
                ("", ["--config", "missing.toml", "--require-existing"]),
                ('[service]\ntransport="streamable-http"\n', ["--config", "case.toml"]),
                ("[service]\nport=0\n", ["--config", "case.toml"]),
                ("invalid toml [", ["--config", "case.toml"]),
                (
                    '[security]\nmcp_bearer_token="synthetic"\n',
                    ["--config", "case.example.toml"],
                ),
            ]
            for content, argv in cases:
                (root / "case.toml").write_text(content)
                (root / "case.example.toml").write_text(content)
                for flags in [[], ["--json"], ["--json", "--scan-tracked"]]:
                    with self.subTest(argv=argv, content=content, flags=flags):
                        self.assertEqual(
                            cli(native, argv + flags, root),
                            cli(oracle, argv + flags, root),
                        )
            # Default-local selection uses only the explicit repository context.
            (root / "config/mathformer_mcp.local.toml").write_text(
                "[service]\nport=3210\n"
            )
            self.assertEqual(
                cli(native, ["--json"], root), cli(oracle, ["--json"], root)
            )
            self.assertEqual(
                json.loads(cli(native, ["--json"], root)[1])["runtime_settings"][
                    "port"
                ],
                3210,
            )
            for argv, code in [(["--help"], 0), (["--unknown"], 2)]:
                actual, expected = cli(native, argv, root), cli(oracle, argv, root)
                self.assertEqual(actual[0], code)
                self.assertEqual(actual, expected)

    def test_native_first_example_match_and_validation_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            example = root / "case.example.toml"
            example.write_text("# token " + "x" * 40 + "\n# secret " + "y" * 40 + "\n")
            config = native.load_service_config(example, repo_root=root)
            self.assertEqual(sum("near offset" in error for error in config.errors), 1)
            data = native.deep_copy_config(native.DEFAULT_CONFIG)
            data["service"].update(
                transport="invalid",
                port="bad",
                rate_limit_per_minute=-1,
                default_timeout_seconds="bad",
            )
            data["paths"]["artifacts_dir"] = str(root.parent / "outside")
            errors, _ = native.validate_config(
                data, path=None, kind="local", repo_root=root
            )
            self.assertEqual(len(errors), 6)
            data = native.deep_copy_config(native.DEFAULT_CONFIG)
            data["service"]["transport"] = "streamable-http"
            data["security"]["require_auth_for_http"] = True
            errors, _ = native.validate_config(
                data, path=None, kind="local", repo_root=root
            )
            self.assertEqual(
                errors,
                ["streamable-http service config requires security.mcp_bearer_token"],
            )

    def test_real_registered_tools_and_lunar_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document["id"], "hub_mcp_service_config_workflow")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        # Production server registration, bypassing only its CLI startup/config loading.
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "service-config",
            StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=["-c", server],
                cwd=str(ROOT),
            ),
            {},
        ) as remote:
            try:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile_doc(doc):
                    assets = snapshot(doc)
                    workflow = compile_workflow(
                        "mcp:service-config",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools,
                    )
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(set(workflow["bindings"]), set(doc["operations"]))
                    return workflow, assets

                workflow, assets = compile_doc(document)

                async def allow():
                    pass

                async def run(root, argv, doc=None):
                    bound, received = (
                        (workflow, assets) if doc is None else compile_doc(doc)
                    )
                    return await execute(
                        bound,
                        received,
                        {"argv": argv, "repo_root": str(root)},
                        remote,
                        allow,
                    )

                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    (root / "config").mkdir()
                    # Missing/directories/empty files do not produce findings.
                    (root / "README.md").mkdir()
                    (root / "TODO.md").write_text("")
                    oracle = original(root)
                    cases = [
                        ([], None),
                        (["--json"], None),
                        (["--json", "--scan-tracked"], None),
                        (["--config", "missing", "--json"], None),
                        (["--config", "missing", "--require-existing", "--json"], None),
                        (["--config", "case.toml", "--json"], "not toml ["),
                        (["--config", "case.toml", "--json"], "[service]\nport=0\n"),
                        (
                            ["--config", "case.toml", "--json"],
                            '[service]\ntransport="streamable-http"\n',
                        ),
                        (
                            ["--config", "case.toml", "--json"],
                            '[external_api_keys]\nopenai_api_key="synthetic-value"\n',
                        ),
                    ]
                    for argv, content in cases:
                        if content is not None:
                            (root / "case.toml").write_text(content)
                        result = await run(root, argv)
                        self.assertEqual(result["status"], "accepted", result)
                        code, text, _ = cli(oracle, argv, root)
                        self.assertEqual(result["outputs"]["exit_code"], code)
                        self.assertEqual(result["outputs"]["stdout"], text)
                        expected = json.loads(cli(oracle, [*argv, "--json"], root)[1])
                        self.assertEqual(result["outputs"]["report"], expected)
                        self.assertEqual(len(result["calls"]), 5)
                        self.assertEqual(
                            [call["tool"] for call in result["calls"]],
                            [
                                "mathformer_service_config_" + x
                                for x in [
                                    "parse",
                                    "load",
                                    "scan" if "--scan-tracked" in argv else "no_scan",
                                    "report",
                                    "emit",
                                ]
                            ],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                    # Scan collects every matching line in file order, with no cap or early stop.
                    text = "\n".join(
                        [
                            "api_key=" + "x" * 40,
                            "plain " + "y" * 40,
                            "token=" + "z" * 40,
                        ]
                    )
                    (root / "TODO.md").write_text(text)
                    (root / "AGENTS.md").write_text("secret=" + "q" * 40)
                    result = await run(root, ["--json", "--scan-tracked"])
                    self.assertEqual(result["status"], "accepted", result)
                    report = result["outputs"]["report"]
                    self.assertFalse(report["ok"])
                    self.assertEqual(result["outputs"]["exit_code"], 1)
                    self.assertEqual(
                        [
                            (x["path"], x["line"])
                            for x in report["secret_scan_findings"]
                        ],
                        [("TODO.md", 1), ("TODO.md", 3), ("AGENTS.md", 1)],
                    )
                    self.assertEqual(
                        report,
                        json.loads(cli(oracle, ["--json", "--scan-tracked"], root)[1]),
                    )
                    result = await run(root, ["--json"])
                    self.assertTrue(result["outputs"]["report"]["ok"])
                    self.assertEqual(
                        result["outputs"]["report"]["secret_scan_findings"], []
                    )
                    # Invalid numeric values validate first, then native runtime conversion fails.
                    (root / "case.toml").write_text('[service]\nport="bad"\n')
                    with self.assertRaises(ValueError):
                        cli(oracle, ["--config", "case.toml"], root)
                    result = await run(root, ["--config", "case.toml"])
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 4)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    for argv in [["--help"], ["--unknown"]]:
                        result = await run(root, argv)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(len(result["calls"]), 1)
                    # A selected example directory is a caught parse error followed by an
                    # uncaught native example-text read error; no report/emit or retry.
                    (root / "directory.example.toml").mkdir()
                    with self.assertRaises(IsADirectoryError):
                        cli(oracle, ["--config", "directory.example.toml"], root)
                    result = await run(root, ["--config", "directory.example.toml"])
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 2)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    # A symlink loop is skipped as absent, as in native Path.exists.
                    (root / "TODO.md").unlink()
                    (root / "TODO.md").symlink_to(root / "TODO.md")
                    result = await run(root, ["--json", "--scan-tracked"])
                    # Path.exists treats a symlink loop as absent, preserving the native skip.
                    self.assertEqual(result["status"], "accepted", result)
                    # Bound exhaustion rejects before dispatching the fifth tool; no retry.
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 4
                    result = await run(root, ["--json"], bounded)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), 5)
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        4,
                    )
                    self.assertIn("budget", json.dumps(result).lower())
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    bound, received = compile_doc(timed)

                    async def blocked_authority():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(
                            bound,
                            received,
                            {"argv": [], "repo_root": str(root)},
                            remote,
                            blocked_authority,
                        )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
