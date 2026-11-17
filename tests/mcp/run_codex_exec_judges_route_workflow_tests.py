#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit test interpreter and source-path setup
"""Offline native route/MCP/Lunar/PRISM integration and provider-boundary fixtures."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
PATHS = [
    str(ROOT / "scripts"),
    str(LUNAR / "app/backend"),
    str(LUNAR.parent / "abducer/abducer-prism/src"),
    *SITES,
]
sys.path[:0] = PATHS

import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
from threading import Event, Lock
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from codex_exec_judges_route_tools import (
    ACTIONS,
    ROUTE,
    SOURCE,
    checked_registry,
    selected_match,
)
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_report_formalphysics_codex_exec_judges_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
PREFIX = "mathformer_codex_exec_judges_"
PROMPTS = "artifacts/formalphysics_comparative_analysis/hub_selected_examples_report/codex_exec_judge_prompts.json"
OUTPUT = "artifacts/formalphysics_judge_synthesis/codex_exec_judges/latest"
REGISTRY = {key: hub.action_to_dict(hub.build_registry()[key]) for key in ACTIONS}
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": list(ACTIONS)},
    "score": 17,
    "matched_terms": ["codex", "judge"],
}


def put(root, name, value):
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value)
    return target


def populate(root):
    # These are the actual source modules, unchanged, on an isolated repository mount.
    for path in [SOURCE, str(Path(SOURCE).with_name("build_synthesis_report.py"))]:
        put(root, path, (ROOT / path).read_text())
    put(
        root,
        PROMPTS,
        json.dumps(
            [
                {
                    "case_id": "case" + str(i),
                    "candidate_id": "candidate",
                    "judge_id": "judge",
                    "prompt": "fixture " + str(i),
                }
                for i in range(3)
            ]
        ),
    )
    return root


def load_native(root):
    path = root / SOURCE
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location("judge_runner_fixture", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/codex_exec_judges_route_original.py.txt"
        ).read_text(),
        scope,
    )
    return scope["run_intent_match"]


def snapshot(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    values[DESCRIPTOR] = json.dumps(document)
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    return [
        {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }
        for path, content in values.items()
    ]


class CodexProviderFixture:
    """Only the external model process is substituted; source parsing/persistence run."""

    def __init__(self, *, failure=None, overlap=False):
        self.failure = failure
        self.overlap = overlap
        self.second = Event()
        self.lock = Lock()
        self.calls = []
        self.completed = []

    def run(self, argv, **kwargs):
        assert argv[1] == "exec" and argv[-1] == "-"
        assert "--model" not in argv and "--profile" not in argv
        assert set(kwargs) == {"cwd", "input", "text", "capture_output", "timeout"}
        assert kwargs["timeout"] == 900 and kwargs["text"] and kwargs["capture_output"]
        index = int(kwargs["input"].split()[-1])
        with self.lock:
            self.calls.append(index)
        if self.overlap and index == 0:
            assert self.second.wait(10), "concurrent provider fixture did not overlap"
        final = Path(argv[argv.index("--output-last-message") + 1])
        if self.failure == "timeout":
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        if self.failure == "error":
            raise OSError("provider boundary unavailable")
        final.write_text(
            "not JSON" if self.failure == "invalid" else json.dumps({"decision": index})
        )
        with self.lock:
            self.completed.append(index)
        if index == 1:
            self.second.set()
        code = 7 if self.failure == "exit" and index == 0 else 0
        return subprocess.CompletedProcess(
            argv, code, "", "fixture stderr" if code else ""
        )


class RouteTests(unittest.TestCase):
    maxDiff = None

    def test_contract_generator_and_native_capability_pins(self):
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("judge_route_normalizer", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        d = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.codex_exec_judges_route_descriptor(), d)
        self.assertEqual(d["lifecycle"], "active")
        self.assertEqual(d["aliases"], [ROUTE])
        self.assertEqual(
            d["policy"]["limits"], {"wall_time_seconds": 3600, "max_operation_calls": 8}
        )
        self.assertEqual(
            d["policy"]["failure"]["retry"], {"max_attempts": 1, "retryable_codes": []}
        )
        self.assertEqual(d["policy"]["resume"]["mode"], "none")
        self.assertEqual(d["flow"]["steps"][1]["max_iterations"], 2)
        self.assertEqual(d["flow"]["steps"][1]["on_exhausted"], "fail")
        self.assertEqual([REGISTRY[a]["timeout_seconds"] for a in ACTIONS], [120, 1200])
        for row in d["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertTrue(
            any(
                r["path"] == "scripts/mathformer.py"
                and r["selector"] == "run_intent_match"
                for r in d["provenance"]["sources"]
            )
        )
        for name, operation in d["operations"].items():
            self.assertEqual(operation["execution"]["binding"]["target"], PREFIX + name)
        bad = deepcopy(REGISTRY)
        bad[ACTIONS[0]]["command"] = ["arbitrary"]
        with self.assertRaisesRegex(ValueError, "registry"):
            checked_registry(bad)
        bad = deepcopy(MATCH)
        bad["route"]["action_ids"].reverse()
        with self.assertRaisesRegex(ValueError, "route"):
            selected_match(bad)

    def test_native_runner_selection_preparation_resume_and_empty_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = populate(Path(directory))
            native = load_native(root)
            for limit, expected in [(None, 3), (1, 1), (0, 0), (-1, 2)]:
                args = native.parse_args(
                    [
                        "--prompts-json",
                        str(root / PROMPTS),
                        "--output-dir",
                        str(root / ("prepare" + str(limit))),
                    ]
                )
                args.limit = limit
                with patch.object(
                    native,
                    "subprocess",
                    SimpleNamespace(
                        run=lambda *a, **k: self.fail("preparation called provider")
                    ),
                ):
                    report = native.run(args)
                self.assertEqual(report["selected_prompt_count"], expected)
                self.assertEqual(report["completed_result_count"], 0)
                self.assertEqual(len(report["rows"]), expected)
                self.assertEqual(
                    json.loads(Path(report["artifacts"]["results"]).read_text())[
                        "results"
                    ],
                    [],
                )
                for row in report["rows"]:
                    self.assertEqual(row["status"], "dry_run_prompt_written")
                    self.assertEqual(
                        Path(row["prompt_path"]).read_text(),
                        "fixture " + row["case_id"][-1],
                    )
                    self.assertNotIn("--model", row["command"])
            args = native.parse_args(
                [
                    "--prompts-json",
                    str(root / PROMPTS),
                    "--output-dir",
                    str(root / "resume"),
                    "--case-id",
                    "case1",
                    "--candidate-id",
                    "candidate",
                    "--judge-id",
                    "judge",
                    "--resume",
                ]
            )
            first = native.run(args)
            self.assertEqual(first["selected_prompt_count"], 1)
            final = Path(first["rows"][0]["final_message_path"])
            final.write_text('{"vote":true}')
            reused = native.run(args)
            self.assertEqual(
                reused["rows"][0]["status"], "reused_existing_final_message"
            )
            self.assertEqual(reused["rows"][0]["result"]["case_id"], "case1")
            args.judge_id = "absent"
            self.assertEqual(native.run(args)["rows"], [])

    def test_native_provider_failures_ordering_and_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = populate(Path(directory))
            native = load_native(root)
            # Executable is only an admission capability: the fixture intercepts every call.
            codex = put(root, "codex-fixture", "#!/bin/sh\nexit 99\n")
            codex.chmod(0o755)

            def args(name, *extra):
                return native.parse_args(
                    [
                        "--prompts-json",
                        str(root / PROMPTS),
                        "--output-dir",
                        str(root / name),
                        "--codex-bin",
                        str(codex),
                        "--execute",
                        *extra,
                    ]
                )

            provider = CodexProviderFixture(overlap=True)
            with patch.object(native, "subprocess", SimpleNamespace(run=provider.run)):
                report = native.run(args("parallel", "--workers", "3"))
            self.assertLess(provider.completed.index(1), provider.completed.index(0))
            self.assertEqual(
                [r["result"]["decision"] for r in report["rows"]], [0, 1, 2]
            )
            self.assertEqual(report["completed_result_count"], 3)
            for mode in ["exit", "invalid"]:
                provider = CodexProviderFixture(failure=mode)
                values = args(mode)
                with patch.object(
                    native, "subprocess", SimpleNamespace(run=provider.run)
                ):
                    report = native.run(values)
                    # Failed rows do not stop processing or make native main fail.
                    self.assertEqual(
                        native.main(
                            [
                                "--prompts-json",
                                str(root / PROMPTS),
                                "--output-dir",
                                str(root / (mode + "main")),
                                "--codex-bin",
                                str(codex),
                                "--execute",
                            ]
                        ),
                        0,
                    )
                self.assertEqual(len(provider.calls), 6)
                self.assertEqual(len(report["rows"]), 3)
                self.assertEqual(report["completed_result_count"], 3)
                self.assertEqual(
                    report["rows"][0]["returncode"], 7 if mode == "exit" else 0
                )
                if mode == "invalid":
                    self.assertEqual(
                        report["rows"][0]["result"]["error"],
                        "codex_exec_output_not_strict_json",
                    )
            for mode, error in [
                ("timeout", subprocess.TimeoutExpired),
                ("error", OSError),
            ]:
                provider = CodexProviderFixture(failure=mode)
                values = args(mode)
                with patch.object(
                    native, "subprocess", SimpleNamespace(run=provider.run)
                ):
                    with self.assertRaises(error):
                        native.run(values)
                self.assertEqual(provider.calls, [0])  # no retries or later rows
                self.assertTrue(
                    (
                        values.output_dir / "selected_codex_exec_judge_prompts.json"
                    ).exists()
                )
                self.assertFalse(
                    (values.output_dir / "codex_exec_judge_results.json").exists()
                )
                self.assertFalse(
                    (values.output_dir / "codex_exec_judge_run_manifest.json").exists()
                )

    def test_real_mcp_lunar_compiler_and_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        with tempfile.TemporaryDirectory(prefix="codex-judge-route-") as directory:
            root = populate(Path(directory).resolve())
            manager = SessionManager()
            # Import registrations only: do not invoke main/config or read provider credentials.
            environment = {
                "PYTHONPATH": os.pathsep.join(PATHS),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            async with manager.open(
                "judge-route",
                StdioConfig(
                    command=sys.executable,
                    args=[
                        "-c",
                        'from mcp_server import mcp;mcp.run(transport="stdio")',
                    ],
                    cwd=str(ROOT),
                ),
                environment,
            ) as remote:
                await self.connected(remote, root)
            self.assertFalse(manager.active)

    async def connected(self, remote, root):
        d = yaml.safe_load(CONTRACT.read_text())
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(document, inventory=tools):
            assets = snapshot(document)
            record = workflow_documents([DESCRIPTOR], assets)[0]
            self.assertTrue(record["validation"]["valid"])
            return compile_workflow("mcp:judge-route", record, inventory), assets

        compiled, assets = compile(d)
        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
        self.assertEqual(compiled["runtime_status"], "ready")
        self.assertEqual(set(compiled["bindings"]), set(d["operations"]))
        self.assertTrue(compiled["prism_source"])
        self.assertTrue(compiled["runtime_source"])
        self.assertFalse(
            compile(d, [t for t in tools if t["name"] != PREFIX + "run_action"])[0][
                "runnable"
            ]
        )

        async def authorize():
            pass

        inputs = {
            "match": MATCH,
            "context": vars(hub.RunContext()),
            "registry": REGISTRY,
            "repository_root": str(root),
        }

        async def run(values=None, changed=None):
            c, a = compile(changed) if changed is not None else (compiled, assets)
            self.assertTrue(c["runnable"], c["diagnostics"])
            return await execute(
                c, a, values if values is not None else inputs, remote, authorize
            )

        def operations(result):
            return [row["operation"] for row in result["calls"]]

        expected_ops = (
            ["initialize_intent_state"]
            + ["select_intent_action", "run_action", "advance_intent_state"] * 2
            + ["finish_intent_state"]
        )
        # Successful actual self-test + native one-prompt preparation, no model call.
        result = await run()
        self.assertEqual(result["status"], "accepted", result)
        output = result["outputs"]["result"]
        self.assertTrue(output["ok"])
        self.assertEqual(operations(result), expected_ops)
        self.assertEqual(
            [c["tool"] for c in result["calls"]],
            [PREFIX + name for name in expected_ops],
        )
        self.assertEqual([c["action"]["id"] for c in output["children"]], list(ACTIONS))
        self.assertEqual(
            output["route"],
            hub.intent_match_to_dict(selected_match(MATCH), checked_registry(REGISTRY)),
        )
        for i, child in enumerate(output["children"]):
            self.assertEqual(
                child["argv"],
                hub.resolve_command(hub.build_registry()[ACTIONS[i]].command),
            )
            self.assertEqual(child["returncode"], 0)
            self.assertTrue(child["write_audit"]["ok"])
            self.assertEqual(child["write_audit"]["unexpected_paths"], [])
        manifest = json.loads(
            (root / OUTPUT / "codex_exec_judge_run_manifest.json").read_text()
        )
        self.assertFalse(manifest["execute"])
        self.assertFalse(manifest["resume"])
        self.assertEqual(manifest["workers"], 1)
        self.assertEqual(manifest["selected_prompt_count"], 1)
        self.assertEqual(manifest["rows"][0]["status"], "dry_run_prompt_written")
        self.assertEqual(manifest["rows"][0]["case_id"], "case0")
        self.assertTrue(result["runtime"]["effect_records"])
        self.assertTrue(result["runtime"]["provenance"])
        self.assertTrue(result["replay_artifacts"])

        # Exact independent original-entrypoint comparison on deterministic native paths.
        for mode in ["dry", "first_preflight", "second_preflight", "bad_json"]:
            for keep in [False, True]:
                values = deepcopy(inputs)
                values["context"].update(dry_run=mode == "dry", keep_going=keep)
                script = root / SOURCE
                prompts = root / PROMPTS
                backup_script, backup_prompts = script.read_text(), prompts.read_text()
                if mode == "first_preflight":
                    script.unlink()
                elif mode == "second_preflight":
                    prompts.unlink()
                elif mode == "bad_json":
                    prompts.write_text("broken JSON")
                shutil.rmtree(root / OUTPUT, ignore_errors=True)
                actual = await run(values)
                self.assertEqual(actual["status"], "accepted", actual)
                got = actual["outputs"]["result"]
                count = 1 if mode == "first_preflight" and not keep else 2
                self.assertEqual(len(got["children"]), count)
                self.assertEqual(len(actual["calls"]), 2 + 3 * count)
                self.assertEqual(got["ok"], mode == "dry")
                self.assertEqual(
                    got["status"],
                    "intent_run_completed" if mode == "dry" else "intent_run_failed",
                )
                shutil.rmtree(root / OUTPUT, ignore_errors=True)
                oracle = original()(
                    selected_match(MATCH),
                    checked_registry(REGISTRY),
                    hub.RunContext(**values["context"]),
                    repository_root=root,
                )
                # Native self-test JSON contains source-owned random temporary paths;
                # compare all other output, including subprocess errors and audits.
                for observed in [got, oracle]:
                    if mode in ["second_preflight", "bad_json"]:
                        self.assertTrue(
                            json.loads(observed["children"][0]["stdout"])["ok"]
                        )
                        observed["children"][0][
                            "stdout"
                        ] = "<native self-test temporary paths>"
                self.assertEqual(got, oracle)
                put(root, SOURCE, backup_script)
                put(root, PROMPTS, backup_prompts)

        # Sticky failure and history are exercised through the advertised real ports.
        context = vars(hub.RunContext(keep_going=True, dry_run=True))
        state = (await remote.call(PREFIX + "initialize_intent_state", {}))["state"]
        missing = await remote.call(
            PREFIX + "run_action",
            dict(
                action_id=ACTIONS[0],
                context=context,
                registry={},
                repository_root=str(root),
            ),
        )
        self.assertEqual(missing["child"]["status"], "unknown_action")
        first = await remote.call(
            PREFIX + "advance_intent_state",
            dict(state=state, child=missing["child"], context=context, action_count=2),
        )
        self.assertFalse(first["done"])
        good = await remote.call(
            PREFIX + "run_action",
            dict(
                action_id=ACTIONS[1],
                context=context,
                registry=REGISTRY,
                repository_root=str(root),
            ),
        )
        final = await remote.call(
            PREFIX + "advance_intent_state",
            dict(
                state=first["state"],
                child=good["child"],
                context=context,
                action_count=2,
            ),
        )
        self.assertTrue(final["done"])
        self.assertFalse(final["state"]["ok"])
        self.assertEqual(final["state"]["children"], [missing["child"], good["child"]])
        self.assertEqual(state, {"ok": True, "children": []})
        with self.assertRaises(Exception):
            await remote.call(
                PREFIX + "select_intent_action",
                {"state": final["state"], "match": MATCH},
            )

        # The second native append reaches the exact bound normally; a smaller host
        # bound exhausts and never invokes finish. No fabricated operation output.
        values = deepcopy(inputs)
        values["context"]["dry_run"] = True
        short = deepcopy(d)
        short["flow"]["steps"][1]["max_iterations"] = 1
        exhausted = await run(values, short)
        self.assertEqual(exhausted["status"], "failed", exhausted)
        self.assertIsNone(exhausted["outputs"])
        self.assertIn("exhaust", str(exhausted).lower())
        self.assertEqual(operations(exhausted), expected_ops[:4])
        budget = deepcopy(d)
        budget["policy"]["limits"]["max_operation_calls"] = 4
        failed = await run(values, budget)
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(
            sum(bool(c.get("transport_call_performed")) for c in failed["calls"]), 4
        )
        self.assertIsNone(failed["outputs"])
        # Unexpected materialization errors propagate, with no retry or finish.
        values = deepcopy(inputs)
        values["registry"][ACTIONS[0]]["timeout_seconds"] = 1
        failed = await run(values)
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(operations(failed), expected_ops[:3])
        self.assertIsNone(failed["outputs"])
        # Missing registry metadata is an original KeyError at finish, not a
        # fabricated success. Child unknown_action still flows as ordinary data.
        values = deepcopy(inputs)
        values["registry"] = {}
        failed = await run(values)
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(operations(failed), expected_ops[:4] + ["finish_intent_state"])
        with self.assertRaises(KeyError):
            original()(
                selected_match(MATCH), {}, hub.RunContext(), repository_root=root
            )
        # Service policy remains effective on the new ports.
        import mcp_server

        with patch.object(mcp_server, "_READONLY", True):
            with self.assertRaisesRegex(Exception, "read-only"):
                await mcp_server.mcp.call_tool(
                    PREFIX + "run_action",
                    dict(
                        action_id=ACTIONS[0],
                        context=vars(hub.RunContext()),
                        registry=REGISTRY,
                        repository_root=str(root),
                    ),
                )
        with patch.object(mcp_server, "_ALLOWED_WRITE_ROOTS", [root / "denied"]):
            with self.assertRaisesRegex(Exception, "service roots"):
                await mcp_server.mcp.call_tool(
                    PREFIX + "run_action",
                    dict(
                        action_id=ACTIONS[0],
                        context=vars(hub.RunContext()),
                        registry=REGISTRY,
                        repository_root=str(root),
                    ),
                )
            # A hub dry-run performs no write and retains the native escape hatch.
            await mcp_server.mcp.call_tool(
                PREFIX + "run_action",
                dict(
                    action_id=ACTIONS[0],
                    context=context,
                    registry=REGISTRY,
                    repository_root=str(root),
                ),
            )


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    outcome = program.result
    raise SystemExit(
        0 if outcome.wasSuccessful() and outcome.testsRun > len(outcome.skipped) else 1
    )
