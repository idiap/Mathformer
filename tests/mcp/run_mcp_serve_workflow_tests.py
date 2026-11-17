#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native entrypoint equivalence, registered tools, real PRISM compile/runtime."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
for site in (ROOT / ".venv/lib").glob("python*/site-packages"):
    sys.path.append(str(site))
import asyncio
from contextlib import redirect_stderr
from copy import deepcopy
import hashlib
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
import mcp_server as native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mcp_serve_workflow/workflow.yaml"


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
        for row in {
            row["path"]: row for row in document["provenance"]["sources"]
        }.values()
    ]


def config(path, transport="stdio", require=False):
    path.write_text(
        '[service]\ntransport = "'
        + transport
        + '"\nreadonly = true\ndefault_timeout_seconds = 37\n[security]\nrequire_auth_for_http = '
        + str(require).lower()
        + "\n"
    )


class ServeTests(unittest.TestCase):
    def test_entrypoint_equivalence(self):
        scope = dict(vars(native))
        exec((ROOT / "tests/mcp/fixtures/mcp_serve_original.py.txt").read_text(), scope)
        oracle = scope["main"]
        import uvicorn

        for argv in [
            [],
            ["--readonly"],
            ["--transport", "streamable-http"],
            [
                "--transport",
                "streamable-http",
                "--rate-limit",
                "0",
                "--auth-token",
                "fixture-only",
            ],
            ["--transport", "streamable-http", "--port", "9999"],
        ]:
            outcomes = []
            for runner in [oracle, native.main]:
                events = []

                def run_stdio(**kwargs):
                    events.append(("stdio", kwargs))

                def run_http(app, **kwargs):
                    events.append(("http", type(app).__name__, kwargs))
                    if kwargs["port"] == 9999:
                        raise RuntimeError("fixture failure")

                with (
                    patch.object(native.mcp, "run", run_stdio),
                    patch.object(uvicorn, "run", run_http),
                    patch.dict(os.environ, {}, clear=True),
                    redirect_stderr(io.StringIO()) as stderr,
                ):
                    try:
                        value = runner(argv)
                    except Exception as exc:
                        value = (type(exc).__name__, str(exc))
                    outcomes.append((value, events, stderr.getvalue()))
            self.assertEqual(*outcomes)
        with self.assertRaises(SystemExit) as exc, redirect_stderr(io.StringIO()):
            native.main(["--port", "invalid"])
        self.assertEqual(exc.exception.code, 2)

    def test_configuration_state_and_early_return(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixture.toml"
            config(path)
            args = native.mathformer_serve_parse(
                [
                    "--config",
                    str(path),
                    "--transport",
                    "streamable-http",
                    "--host",
                    "localhost",
                    "--port",
                    "8910",
                    "--rate-limit",
                    "7",
                    "--auth-token",
                    "fixture-only",
                ]
            )["args"]
            self.assertTrue(args["has_config"])
            saved = (
                native._AGENTC_SERVICE_CONFIG,
                native._READONLY,
                native.CALL_LOG_PATH,
                native._DEFAULT_TIMEOUT_SECONDS,
                native._EXEC_REGISTRY,
                native._ALLOWED_WRITE_ROOTS,
            )
            try:
                startup = native.mathformer_serve_load_config(args)["startup"]
                self.assertTrue(startup["valid"])
                runtime = native.mathformer_serve_apply_policy(startup)["runtime"]
                self.assertEqual(
                    runtime,
                    {
                        "transport": "streamable-http",
                        "host": "localhost",
                        "port": 8910,
                        "readonly": True,
                        "auth_token": "fixture-only",
                        "rate_limit": 7,
                        "require_auth_for_http": False,
                    },
                )
                self.assertTrue(native._READONLY)
                self.assertEqual(native._DEFAULT_TIMEOUT_SECONDS, 37)
                self.assertTrue(native._ALLOWED_WRITE_ROOTS)
                previous = native._AGENTC_SERVICE_CONFIG
                path.write_text("invalid toml [")
                with redirect_stderr(io.StringIO()) as stderr:
                    result = native.main(["--config", str(path)])
                self.assertEqual(result, 2)
                self.assertFalse(json.loads(stderr.getvalue())["ok"])
                self.assertIs(native._AGENTC_SERVICE_CONFIG, previous)
                self.assertTrue(native._READONLY)
            finally:
                (
                    native._AGENTC_SERVICE_CONFIG,
                    native._READONLY,
                    native.CALL_LOG_PATH,
                    native._DEFAULT_TIMEOUT_SECONDS,
                    native._EXEC_REGISTRY,
                    native._ALLOWED_WRITE_ROOTS,
                ) = saved

    def test_middleware_state_and_auth_order(self):
        async def scenario():
            reached = []

            async def app(scope, receive, send):
                reached.append(scope["type"])

            limiter = native._RateLimitMiddleware(app, 2)
            auth = native._BearerAuthMiddleware(limiter, "fixture-only")

            async def request(token="fixture-only", kind="http", ip="one"):
                messages = []

                async def send(value):
                    messages.append(value)

                async def receive():
                    return {"type": "http.disconnect"}

                await auth(
                    {
                        "type": kind,
                        "client": (ip, 1),
                        "headers": [(b"authorization", ("Bearer " + token).encode())],
                    },
                    receive,
                    send,
                )
                return messages[0]["status"] if messages else 200

            with patch.object(native.time, "monotonic", return_value=100):
                self.assertEqual(await request("wrong"), 401)
                self.assertEqual(limiter._windows, {})
                self.assertEqual(await request(), 200)
                self.assertEqual(await request(), 200)
                self.assertEqual(await request(), 429)
                self.assertEqual(limiter._windows, {"one": [100, 100]})
                self.assertEqual(await request(ip="two"), 200)
                self.assertEqual(await request(kind="websocket"), 200)
            with patch.object(native.time, "monotonic", return_value=160):
                self.assertEqual(await request(), 429)  # strict older-than cutoff
            with patch.object(native.time, "monotonic", return_value=160.1):
                self.assertEqual(await request(), 200)
                self.assertEqual(limiter._windows["one"], [160.1])
            self.assertEqual(len(reached), 5)

        asyncio.run(scenario())

    def test_registered_tools_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document["id"], "hub_mcp_serve_workflow")
        manager = SessionManager()
        async with manager.open(
            "serve-fixture",
            StdioConfig(
                command=sys.executable,
                args=["tests/mcp/fixtures/mcp_serve_boundary.py"],
                cwd=str(ROOT),
            ),
            {
                "MATHFORMER_MCP_TOKEN": "",
                "PYTHONPATH": os.pathsep.join(
                    str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")
                ),
            },
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            async def allow():
                pass

            async def run(argv, doc=None):
                doc = doc or document
                assets = snapshot(doc)
                workflow = compile_workflow(
                    "mcp:serve-fixture",
                    workflow_documents([DESCRIPTOR], assets)[0],
                    tools,
                )
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertEqual(set(workflow["bindings"]), set(doc["operations"]))
                return await execute(workflow, assets, {"argv": argv}, remote, allow)

            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "fixture.toml"
                config(path)
                parsed = await remote.call(
                    "mathformer_serve_parse",
                    {
                        "argv": [
                            "--config",
                            str(path),
                            "--transport",
                            "streamable-http",
                            "--port",
                            "8911",
                            "--readonly",
                            "--rate-limit",
                            "3",
                        ]
                    },
                )
                self.assertTrue(parsed["args"]["has_config"])
                startup = await remote.call("mathformer_serve_load_config", parsed)
                self.assertTrue(startup["startup"]["valid"])
                policy = await remote.call("mathformer_serve_apply_policy", startup)
                self.assertEqual(policy["runtime"]["port"], 8911)
                self.assertEqual(policy["runtime"]["rate_limit"], 3)
                self.assertTrue(policy["runtime"]["readonly"])
                self.assertEqual(policy["runtime"]["transport"], "streamable-http")
                cases = [
                    ([], 0, ["parse", "defaults", "apply_policy", "serve_stdio"]),
                    (
                        ["--transport", "streamable-http", "--readonly"],
                        0,
                        ["parse", "defaults", "apply_policy", "serve_http"],
                    ),
                    (
                        [
                            "--config",
                            str(path),
                            "--host",
                            "localhost",
                            "--port",
                            "8766",
                            "--rate-limit",
                            "0",
                        ],
                        0,
                        ["parse", "load_config", "apply_policy", "serve_stdio"],
                    ),
                    (
                        ["--config", str(Path(temp) / "missing.toml")],
                        2,
                        ["parse", "load_config", "invalid_config"],
                    ),
                ]
                for argv, code, names in cases:
                    result = await run(argv)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"exit_code": code})
                    self.assertEqual([c["operation"] for c in result["calls"]], names)
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                config(path, "streamable-http", True)
                result = await run(["--config", str(path)])
                self.assertEqual(result["outputs"], {"exit_code": 2})
                result = await run(
                    [
                        "--config",
                        str(path),
                        "--auth-token",
                        "fixture-only",
                        "--rate-limit",
                        "0",
                    ]
                )
                self.assertEqual(result["outputs"], {"exit_code": 0})
                result = await run(["--transport", "streamable-http", "--port", "9999"])
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), 4)
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 3
                result = await run([], bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    3,
                )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
