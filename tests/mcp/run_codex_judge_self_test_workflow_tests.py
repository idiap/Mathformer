#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Fixed native fixture, registered MCP and real Lunar/PRISM execution.

No provider or external compiler is reachable in this self-test. The only test
substitution is a rejecting external Codex process boundary. PRISM parsing,
checking, compilation and execution are real, with the explicit host contract.
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
from datetime import datetime
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
import yaml
from codex_judge_self_test_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_formalphysics_codex_exec_judge_runner_self_test_workflow/workflow.yaml"
PREFIX = "mathformer_codex_judge_self_test_"
ORDER = ["fixture_args", "select_pack", "prepare_append", "persist", "check_cleanup"]


def oracle():
    loader = SourceFileLoader(
        "_codex_judge_original",
        str(ROOT / "tests/mcp/fixtures/codex_judge_self_test_original.py.txt"),
    )
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    module.REPO_ROOT = ROOT
    return module


def normalize(value, root):
    if isinstance(value, str):
        return value.replace(str(root), "<temporary>")
    if isinstance(value, list):
        return [normalize(v, root) for v in value]
    if isinstance(value, dict):
        return {
            k: "<native-clock>" if k == "created_at" else normalize(v, root)
            for k, v in value.items()
        }
    return value


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(p, (ROOT / p).read_text())
        for p in dict.fromkeys(r["path"] for r in document["provenance"]["sources"])
    ]


def forbid_codex(*args, **kwargs):
    raise AssertionError(
        "External Codex provider process is unreachable in this self-test"
    )


class ObservedRemote:
    """Forward every real MCP call unchanged; inspect/fault actual temporary files."""

    def __init__(self, remote, hook=None):
        self.remote, self.hook, self.seen = remote, hook, []

    async def tools(self):
        return await self.remote.tools()

    async def call(self, tool, arguments):
        value = await self.remote.call(tool, arguments)
        self.seen.append((tool, deepcopy(arguments), deepcopy(value)))
        if self.hook:
            self.hook(tool, arguments, value)
        return value


class JudgeSelfTestTests(unittest.TestCase):
    def test_native_original_parity_and_state(self):
        native, original = source(), oracle()
        with patch.object(native.subprocess, "run", side_effect=forbid_codex):
            with tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                args = native.self_test_args(root)
                self.assertEqual(
                    vars(args),
                    vars(
                        original.parse_args(
                            [
                                "--prompts-json",
                                str(root / "prompts.json"),
                                "--output-dir",
                                str(root / "out"),
                                "--limit",
                                "1",
                            ]
                        )
                    ),
                )
                snapshots = []
                for module in [original, native]:
                    if (root / "out").exists():
                        shutil.rmtree(root / "out")
                    manifest = module.run(args)
                    datetime.fromisoformat(manifest["created_at"])
                    tree = {}
                    for p in (root / "out").rglob("*"):
                        if p.is_file():
                            value = p.read_text()
                            if p.suffix == ".json":
                                value = normalize(json.loads(value), root)
                            tree[str(p.relative_to(root))] = value
                    snapshots.append((normalize(manifest, root), tree))
                self.assertEqual(*snapshots)
                shutil.rmtree(root / "out")
                state = native.initialize_run(args)
                self.assertEqual(len(state["selected"]), 1)
                self.assertEqual(state["rows"], [])
                self.assertFalse(Path(state["artifacts"]["results"]).exists())
                self.assertTrue(native.append_run_row(args, state))
                self.assertEqual(len(state["rows"]), 1)
                row = state["rows"][0]
                self.assertEqual(row["status"], "dry_run_prompt_written")
                self.assertEqual(
                    Path(row["prompt_path"]).read_text(), "Return strict JSON."
                )
                self.assertFalse(Path(row["final_message_path"]).exists())
                self.assertEqual(
                    row["command"],
                    native.codex_command(args, Path(row["final_message_path"])),
                )
                # Exhaustion does not append another row or silently wrap the cursor.
                with self.assertRaises(IndexError):
                    native.append_run_row(args, state)
                self.assertEqual(len(state["rows"]), 1)
                manifest = native.persist_run(args, state)
                self.assertEqual(
                    json.loads(Path(manifest["artifacts"]["results"]).read_text()),
                    {"schema_version": 1, "style": native.STYLE, "results": []},
                )
                self.assertEqual(
                    json.loads(Path(manifest["artifacts"]["manifest"]).read_text()),
                    manifest,
                )
                self.assertTrue(native.check_self_test(manifest)["ok"])
                # Same short-circuit ordering: a wrong count never dereferences paths.
                self.assertFalse(
                    native.check_self_test(
                        {"selected_prompt_count": 0, "artifacts": {}}
                    )["ok"]
                )
                for name in ["selected_prompts", "results"]:
                    p = Path(manifest["artifacts"][name])
                    saved = p.read_bytes()
                    p.unlink()
                    self.assertFalse(native.check_self_test(manifest)["ok"])
                    p.write_bytes(saved)
                bad = deepcopy(state["selected"]) * 3
                self.assertEqual(
                    native.select_prompts(bad, args), original.select_prompts(bad, args)
                )
                self.assertEqual(len(native.select_prompts(bad, args)), 1)
                args.case_id = "absent"
                self.assertEqual(native.run(args)["selected_prompt_count"], 0)
                (root / "prompts.json").write_text("{}")
                for module in [native, original]:
                    with self.assertRaises(ValueError):
                        module.run(args)
            reports = []
            for module in [original, native]:
                report = module.self_test()
                self.assertTrue(report["ok"])
                for p in report["artifacts"].values():
                    self.assertFalse(Path(p).exists())
                reports.append(
                    normalize(report, Path(report["artifacts"]["manifest"]).parents[1])
                )
                output = io.StringIO()
                with redirect_stdout(output):
                    code = module.main(["--self-test", "--json"])
                self.assertEqual(code, 0)
                self.assertTrue(json.loads(output.getvalue())["ok"])
            self.assertEqual(*reports)

    def test_registered_mcp_lunar_success_failures_and_bounds(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"],
            "hub_physics_lean_formalphysics_codex_exec_judge_runner_self_test_workflow",
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 120, "max_operation_calls": 5},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys; sys.path.insert(0,"scripts"); from mcp_server import mcp; from codex_judge_self_test_tools import source; from tests_codex_boundary import forbid_codex; source().subprocess.run=forbid_codex; mcp.run(transport="stdio")'
        # The bootstrap substitutes only the prohibited external provider boundary.
        boundary_dir = tempfile.TemporaryDirectory()
        self.addCleanup(boundary_dir.cleanup)
        boundary_file = Path(boundary_dir.name) / "tests_codex_boundary.py"
        boundary_file.write_text(
            'def forbid_codex(*args, **kwargs):\n    raise AssertionError("No external Codex provider calls permitted")\n'
        )
        packages = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
        server = (
            "import sys; sys.path.extend("
            + repr(packages)
            + "); sys.path.insert(0,"
            + repr(boundary_dir.name)
            + "); "
            + server
        )
        abandoned = []
        failure = None
        async with manager.open(
            "judge-smoke",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    snapshot = assets(doc)
                    compiled = compile_workflow(
                        "mcp:judge-smoke",
                        workflow_documents([DESCRIPTOR], snapshot)[0],
                        tools if inventory is None else inventory,
                    )
                    return compiled, snapshot

                workflow, snapshot = compile(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                for op in ORDER:
                    self.assertTrue(any(t["name"] == PREFIX + op for t in tools))
                self.assertFalse(compile(document, [])[0]["runnable"])
                missing = [t for t in tools if t["name"] != PREFIX + "persist"]
                self.assertFalse(compile(document, missing)[0]["runnable"])

                async def allow():
                    pass

                async def run(doc=None, hook=None):
                    w, a = compile(doc) if doc else (workflow, snapshot)
                    self.assertTrue(w["runnable"], w["diagnostics"])
                    observed = ObservedRemote(remote, hook)
                    result = await execute(w, a, {}, observed, allow)
                    return result, observed

                result, observed = await run()
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    [c["tool"] for c in result["calls"]], [PREFIX + n for n in ORDER]
                )
                report = result["outputs"]["result"]
                self.assertTrue(report["ok"])
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
                for c in result["calls"]:
                    self.assertTrue(c["transport_call_performed"])
                    self.assertEqual(len(c["input_digest"]), 64)
                    self.assertEqual(len(c["output_digest"]), 64)
                fixture = observed.seen[0][2]
                self.assertFalse(Path(fixture["args"]["tmp"]).exists())
                for path in report["artifacts"].values():
                    self.assertFalse(Path(path).exists())
                selected = observed.seen[1][2]["state"]
                advanced = observed.seen[2][2]
                manifest = observed.seen[3][2]["manifest"]
                self.assertEqual(selected["rows"], [])
                self.assertEqual(len(selected["selected"]), 1)
                self.assertTrue(advanced["done"])
                self.assertEqual(advanced["state"]["selected"], selected["selected"])
                self.assertEqual(len(advanced["state"]["rows"]), 1)
                self.assertEqual(manifest["rows"], advanced["state"]["rows"])
                self.assertEqual(manifest["completed_result_count"], 0)
                self.assertEqual(
                    manifest["filters"],
                    dict(case_id=None, candidate_id=None, judge_id=None, limit=1),
                )
                self.assertEqual(manifest["execute"], False)
                self.assertEqual(manifest["workers"], 1)
                self.assertEqual(manifest["resume"], False)

                # Inspect actual source files while the owned scope is still alive.
                def inspect(tool, args, value):
                    if tool == PREFIX + "persist":
                        m = value["manifest"]
                        self.assertEqual(
                            json.loads(Path(m["artifacts"]["manifest"]).read_text()), m
                        )
                        self.assertEqual(
                            json.loads(
                                Path(m["artifacts"]["selected_prompts"]).read_text()
                            ),
                            selected["selected"],
                        )
                        self.assertEqual(
                            json.loads(Path(m["artifacts"]["results"]).read_text())[
                                "results"
                            ],
                            [],
                        )
                        row = m["rows"][0]
                        self.assertEqual(
                            Path(row["prompt_path"]).read_text(), "Return strict JSON."
                        )
                        self.assertFalse(Path(row["final_message_path"]).exists())

                self.assertEqual((await run(hook=inspect))[0]["status"], "accepted")
                # A false file check is a normal report, not an execution exception.
                for absent in ["selected_prompts", "results"]:

                    def remove(tool, args, value):
                        if tool == PREFIX + "persist":
                            Path(value["manifest"]["artifacts"][absent]).unlink()

                    result, observed = await run(hook=remove)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertFalse(result["outputs"]["result"]["ok"])
                    self.assertEqual(len(result["calls"]), 5)
                    self.assertFalse(Path(observed.seen[0][2]["args"]["tmp"]).exists())
                # Filesystem faults hit real native errors, stop once, and close scope.
                for stage, count in [
                    ("fixture_args", 2),
                    ("select_pack", 3),
                    ("prepare_append", 4),
                ]:

                    def fault(tool, args, value):
                        if tool != PREFIX + stage:
                            return
                        if stage == "fixture_args":
                            Path(value["args"]["prompts_json"]).unlink()
                        elif stage == "select_pack":
                            shutil.rmtree(value["state"]["artifacts"]["prompt_dir"])
                        else:
                            Path(value["state"]["artifacts"]["results"]).mkdir()

                    result, observed = await run(hook=fault)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), count)
                    self.assertFalse(Path(observed.seen[0][2]["args"]["tmp"]).exists())
                # Exact-bound completion was successful above. Force the compiler's
                # exhaustion path without changing a native tool or its return data.
                exhausted = deepcopy(document)
                exhausted["flow"]["steps"][2]["until"] = {"literal": False}
                result, observed = await run(exhausted)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertEqual(len(result["calls"]), 3)
                self.assertIsNone(result["outputs"])
                abandoned.append(Path(observed.seen[0][2]["args"]["tmp"]))
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 2
                result, observed = await run(budget)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    2,
                )
                self.assertIn("budget", str(result).lower())
                self.assertIsNone(result["outputs"])
                abandoned.append(Path(observed.seen[0][2]["args"]["tmp"]))
                # Calls cannot alter execute/model/path defaults or replay a closed scope.
                fixture = await remote.call(PREFIX + "fixture_args", {})
                changed = deepcopy(fixture)
                changed["args"]["execute"] = True
                with self.assertRaises(MCPConnectionError):
                    await remote.call(PREFIX + "select_pack", changed)
                self.assertFalse(Path(fixture["args"]["tmp"]).exists())
                with self.assertRaises(MCPConnectionError):
                    await remote.call(PREFIX + "select_pack", fixture)
                fixture = await remote.call(PREFIX + "fixture_args", {})
                state = await remote.call(PREFIX + "select_pack", fixture)
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "persist", dict(state, context=fixture["context"])
                    )
                self.assertFalse(Path(fixture["args"]["tmp"]).exists())
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        # Host interruption has no v1 finally node: server lifespan owns fallback cleanup.
        for path in abandoned:
            self.assertFalse(path.exists(), str(path))
        if failure:
            raise failure


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(JudgeSelfTestTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(
        0
        if result.wasSuccessful()
        and result.testsRun > 0
        and len(result.skipped) < result.testsRun
        else 1
    )
