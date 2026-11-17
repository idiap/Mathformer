#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native suite, registered MCP and Lunar/PRISM integration checks."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
import asyncio
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml
from mathlib_indexing_control_tools import source

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathlib_indexing_control_suite_workflow/workflow.yaml"


def process_boundary(settings, record):
    def run(command, **kwargs):
        record(command, kwargs)
        options = settings()
        position = source().COMMANDS.index(command[1:])
        if options.get("error") and position == options.get("at", 2):
            if options["error"] == "timeout":
                raise subprocess.TimeoutExpired(command, kwargs["timeout"])
            raise OSError("fixture launch failure")
        stdout = options.get("stdout", {}).get(str(position), '{"ok":true}')
        return SimpleNamespace(
            stdout=stdout,
            stderr="fixture stderr",
            returncode=1 if position == options.get("fail") else 0,
        )

    return SimpleNamespace(run=run, PIPE=subprocess.PIPE)


def fixture_server(control, log):
    from mcp_server import mcp

    native = source()

    def record(command, kwargs):
        with Path(log).open("a") as stream:
            stream.write(
                json.dumps(
                    {
                        "command": command,
                        "cwd": str(kwargs["cwd"]),
                        "timeout": kwargs["timeout"],
                    }
                )
                + "\n"
            )

    native.subprocess = process_boundary(
        lambda: json.loads(Path(control).read_text()), record
    )
    native.time = SimpleNamespace(time=lambda: 0.0)
    mcp.run(transport="stdio")


def artifacts(base):
    directory = base / "artifacts/mathlib_index"
    directory.mkdir(parents=True, exist_ok=True)
    values = {
        "index.json": {
            "version_stamp": dict.fromkeys(
                [
                    "lean_version",
                    "mathlib_git_revision",
                    "file_count",
                    "declaration_count",
                    "build_timestamp_utc",
                ],
                "fixture",
            ),
            "declarations": [{"theorem_shape": {}}] * 20 + [{}],
            "declaration_graph": {"fixture": []},
            "optional_rerankers": {
                "cache_path": "artifacts/mathlib_index/reranker_cache.json"
            },
        },
        "reranker_cache.json": {
            "enabled_by_default": False,
            "embedding_kind": "deterministic_token_hash",
            "entry_count": 1,
        },
        "term_annotation_self_test.json": {"ok": True, "results": [{"ok": True}]},
        "navigation_state_self_test.json": {
            "ok": True,
            "monotonic": {"ok": True},
            "gap_count": 1,
            "operation_catalog": [
                "descend",
                "inspect_sibling",
                "query_declarations",
                "verify_candidate",
                "mark_gap",
            ],
        },
    }
    for name, value in values.items():
        (directory / name).write_text(json.dumps(value))
    return directory


def original():
    path = ROOT / "tests/mcp/fixtures/indexing_control_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "indexing_original", SourceFileLoader("indexing_original", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
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
        for r in document["provenance"]["sources"]
    ]


class SuiteTests(unittest.TestCase):
    def test_original_equivalence(self):
        native, old = source(), original()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            artifacts(base)
            output = base / "report.json"
            for options in (
                {},
                {"fail": 1},
                {"stdout": {"0": "invalid json"}},
                {"stdout": {"1": '{"ok":false}'}},
                {"error": "timeout"},
                {"error": "os"},
                {"stdout": {"0": "[]"}},
            ):
                outcomes = []
                histories = []
                for module in (old, native):
                    calls = []
                    boundary = process_boundary(
                        lambda: options, lambda c, k: calls.append((c, k))
                    )
                    with (
                        patch.object(module, "REPO_ROOT", base),
                        patch.object(module, "OUTPUT_PATH", output),
                        patch.object(module, "subprocess", boundary),
                        patch.object(module, "time", SimpleNamespace(time=lambda: 0.0)),
                    ):
                        output.unlink(missing_ok=True)
                        try:
                            outcomes.append(module.run_suite())
                        except (
                            subprocess.TimeoutExpired,
                            OSError,
                            AttributeError,
                        ) as error:
                            outcomes.append(type(error))
                            self.assertFalse(output.exists())
                        histories.append(calls)
                self.assertEqual(outcomes[0], outcomes[1])
                self.assertEqual(histories[0], histories[1])
                self.assertTrue(
                    all(
                        k["timeout"] == 240 and k["cwd"] == base
                        for c, k in histories[1]
                    )
                )
                if isinstance(outcomes[1], dict):
                    self.assertEqual(len(histories[1]), 6)
                    self.assertEqual(json.loads(output.read_text()), outcomes[1])
            state = {"position": 0, "results": []}
            for i in range(6):
                advanced = native.advance_state(state, {"ok": False, "position": i})
                self.assertEqual(advanced["done"], i == 5)
                state = advanced["state"]
            self.assertEqual([r["position"] for r in state["results"]], list(range(6)))
            self.assertFalse(native.commands_passed(state))
            with self.assertRaises(IndexError):
                native.execute_command(state, base)

    def test_registered_lunar_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        from mcp_connections.client import SessionManager
        from mcp_connections.models import StdioConfig
        from mcp_connections.contracts import workflow_documents
        from mcp_connections.workflow_compiler import compile_workflow
        from mcp_connections.execution import execute

        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["lifecycle"], "active")
        for r in document["provenance"]["sources"]:
            self.assertEqual(
                r["digest"],
                "sha256:" + hashlib.sha256((ROOT / r["path"]).read_bytes()).hexdigest(),
            )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            artifact_dir = artifacts(base)
            output = base / "report.json"
            control = base / "control.json"
            log = base / "calls.jsonl"
            control.write_text("{}")
            manager = SessionManager()
            async with manager.open(
                "indexing-fixture",
                StdioConfig(
                    command=sys.executable,
                    args=[
                        str(Path(__file__).resolve()),
                        "--serve-fixture",
                        str(control),
                        str(log),
                    ],
                    cwd=str(ROOT),
                ),
                {"LUNAR_PLATFORM_ROOT": str(LUNAR)},
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=tools):
                    assets = snapshot(doc)
                    compiled = compile_workflow(
                        "mcp:indexing-fixture",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        inventory,
                    )
                    return compiled, assets

                compiled, assets = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(options=None, doc=document):
                    control.write_text(json.dumps(options or {}))
                    log.unlink(missing_ok=True)
                    output.unlink(missing_ok=True)
                    c, a = (compiled, assets) if doc is document else compile(doc)
                    self.assertTrue(c["runnable"], c["diagnostics"])
                    return await execute(
                        c,
                        a,
                        {"repo_root": str(base), "output": str(output)},
                        remote,
                        authorize,
                    )

                for options in (
                    {},
                    {"fail": 1},
                    {"stdout": {"2": '{"ok":false}'}},
                    {"stdout": {"0": "not json"}},
                ):
                    result = await run(options)
                    self.assertEqual(result["status"], "accepted", result)
                    report = result["outputs"]["report"]
                    self.assertEqual(json.loads(output.read_text()), report)
                    expected_ok = not (
                        options.get("fail") is not None
                        or "2" in options.get("stdout", {})
                    )
                    self.assertEqual(report["ok"], expected_ok)
                    self.assertEqual(
                        len(report["oracle_checks"]), 5 if expected_ok else 0
                    )
                    self.assertEqual(len(result["calls"]), 15 if expected_ok else 14)
                    records = [
                        json.loads(line) for line in log.read_text().splitlines()
                    ]
                    self.assertEqual(
                        [r["command"] for r in records],
                        [[sys.executable, *p] for p in source().COMMANDS],
                    )
                    self.assertTrue(
                        all(
                            r["timeout"] == 240 and r["cwd"] == str(base)
                            for r in records
                        )
                    )
                    self.assertEqual(
                        report["results"][0]["payload"],
                        (
                            {"stdout": "not json"}
                            if options.get("stdout", {}).get("0")
                            else {"ok": True}
                        ),
                    )
                    self.assertTrue(result["replay_artifacts"])
                # First twenty declarations only; a malformed twenty-first is ignored.
                self.assertTrue(
                    (await run())["outputs"]["report"]["oracle_checks"][1]["ok"]
                )
                index = artifact_dir / "index.json"
                value = json.loads(index.read_text())
                value["declarations"][19] = {}
                index.write_text(json.dumps(value))
                result = await run()
                self.assertFalse(result["outputs"]["report"]["ok"])
                self.assertEqual(
                    result["outputs"]["report"]["summary"]["oracle_fail"], 1
                )
                for options, count in [
                    ({"error": "timeout"}, 3),
                    ({"error": "os"}, 3),
                    ({"stdout": {"0": "[]"}}, 1),
                ]:
                    result = await run(options)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertFalse(output.exists())
                    self.assertEqual(len(log.read_text().splitlines()), count)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                for content in ("{", "[]"):
                    index.write_text(content)
                    result = await run()
                    self.assertEqual(result["status"], "failed", result)
                    self.assertFalse(output.exists())
                    self.assertEqual(len(result["calls"]), 14)
                artifacts(base)
                # Exhaustion stops after five results; no oracle or report is run.
                bounded = deepcopy(document)
                bounded["flow"]["steps"][0]["max_iterations"] = 5
                result = await run(doc=bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertFalse(output.exists())
                self.assertEqual(len(log.read_text().splitlines()), 5)
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 3
                result = await run(doc=bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertIn("budget", str(result).lower())
                self.assertFalse(output.exists())
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    3,
                )
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                c, a = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        c,
                        a,
                        {"repo_root": str(base), "output": str(output)},
                        remote,
                        pending,
                    )
            self.assertFalse(manager.active)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve-fixture":
        fixture_server(*sys.argv[2:])
    else:
        unittest.main(verbosity=2)
