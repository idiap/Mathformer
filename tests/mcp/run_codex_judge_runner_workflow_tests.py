#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native parity and registered MCP tools through real Lunar and PRISM runtime.

WORKFLOW_CONTRACT_PATH is required: the host may supply a provisional contract.
No external models, compilers, credentials or scientific production runs.
"""

from tempfile import gettempdir

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
PYTHON = LUNAR / ".venv/bin/python"
if PYTHON.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(PYTHON), [str(PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]

import asyncio
from contextlib import asynccontextmanager, redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import shutil
import subprocess
import tempfile
from threading import Event
import unittest
from unittest.mock import patch
import yaml

from codex_judge_runner_tools import source
from codex_judge_provider import run as provider
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_formalphysics_codex_exec_judge_runner_workflow/workflow.yaml"
PREFIX = "mathformer_codex_judge_runner_"


def oracle():
    loader = SourceFileLoader(
        "_judge_runner_original",
        str(ROOT / "tests/mcp/fixtures/codex_judge_runner_original.py.txt"),
    )
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    module.REPO_ROOT = ROOT
    return module


def args_for(directory, **options):
    args = dict(
        prompts_json=str(directory / "input.json"),
        output_dir=str(directory / "out"),
        limit=1,
        execute=False,
        workers=1,
        resume=False,
        codex_bin="fixture-codex",
        sandbox="read-only",
        model=None,
        profile=None,
        timeout=17,
        case_id=None,
        candidate_id=None,
        judge_id=None,
        self_test=False,
        json=True,
    )
    args.update(options)
    return args


def prompts(directory, texts=("valid", "failed", "invalid")):
    rows = [
        dict(
            case_id=f"case{i}", candidate_id="candidate", judge_id="judge", prompt=text
        )
        for i, text in enumerate(texts)
    ]
    (directory / "input.json").write_text(json.dumps(rows))
    return rows


def namespace(args):
    from argparse import Namespace

    values = dict(args)
    for key in ("prompts_json", "output_dir"):
        values[key] = Path(values[key])
    return Namespace(**values)


def normalize(value):
    if isinstance(value, dict):
        return {
            k: "<clock>" if k == "created_at" else normalize(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [normalize(v) for v in value]
    return value


def tree(directory):
    return {
        str(p.relative_to(directory)): (
            normalize(json.loads(p.read_text()))
            if p.suffix == ".json"
            else p.read_text()
        )
        for p in directory.rglob("*")
        if p.is_file()
    }


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(path, (ROOT / path).read_text())
        for path in dict.fromkeys(
            row["path"] for row in document["provenance"]["sources"]
        )
    ]


class ObservedRemote:
    def __init__(self, remote, hook=None):
        self.remote, self.hook, self.seen = remote, hook, []

    async def tools(self):
        return await self.remote.tools()

    async def call(self, tool, arguments):
        result = await self.remote.call(tool, arguments)
        self.seen.append((tool, deepcopy(arguments), deepcopy(result)))
        if self.hook:
            self.hook(tool, arguments, result)
        return result


@asynccontextmanager
async def connected(manager, config):
    # SessionManager translates errors leaving its context. Re-raise assertion
    # errors after closing the transport so their original evidence is visible.
    failure = None
    async with manager.open("judge-runner", config, {}) as remote:
        try:
            yield remote
        except Exception as error:
            failure = error
    if failure is not None:
        raise failure


class RunnerTests(unittest.TestCase):
    def test_original_parity_native_order_and_exceptions(self):
        native, old = source(), oracle()
        with (
            tempfile.TemporaryDirectory() as raw,
            patch.object(native.subprocess, "run", side_effect=provider),
            patch.object(
                native.shutil,
                "which",
                return_value=str(
                    Path(gettempdir()) / "mathformer-test-fixtures/fixture/codex"
                ),
            ),
        ):
            root = Path(raw)
            rows = prompts(root)
            # Include the direct CLI's unlimited and negative slicing domains in
            # parity checks even though the advertised workflow specializes limit=1.
            variants = [
                {},
                {"execute": True},
                {"execute": True, "workers": 3},
                {"execute": True, "limit": None},
                {"limit": -1},
                {"limit": 0},
                {"case_id": "absent"},
                {"candidate_id": "absent"},
                {"judge_id": "absent"},
                {"execute": True, "case_id": "case1"},
                {"execute": True, "case_id": "case2"},
                {"resume": True},
                {"execute": True, "workers": 2, "case_id": "absent"},
            ]
            for options in variants:
                args = namespace(args_for(root, **options))
                snapshots = []
                for module in (old, native):
                    if args.output_dir.exists():
                        shutil.rmtree(args.output_dir)
                    if args.resume:
                        prompt_dir = args.output_dir / "prompts"
                        prompt_dir.mkdir(parents=True)
                        (
                            prompt_dir
                            / (module.prompt_identifier(rows[0], 0) + ".final.txt")
                        ).write_text('{"cached":true}')
                    manifest = module.run(args)
                    snapshots.append((normalize(manifest), tree(args.output_dir)))
                self.assertEqual(*snapshots, options)
            # Force completion out of order at the provider boundary. The actual
            # ThreadPoolExecutor/as_completed implementation must restore order.
            rows = prompts(root, ("first", "second"))
            args = namespace(args_for(root, execute=True, workers=2, limit=None))
            joined = Event()
            completed = []

            def out_of_order(command, **kwargs):
                if kwargs["input"] == "first":
                    self.assertTrue(joined.wait(5))
                result = provider(command, **kwargs)
                completed.append(kwargs["input"])
                if kwargs["input"] == "second":
                    joined.set()
                return result

            with patch.object(native.subprocess, "run", side_effect=out_of_order):
                manifest = native.run(args)
            self.assertEqual(completed, ["second", "first"])
            self.assertEqual(
                [r["case_id"] for r in manifest["rows"]], ["case0", "case1"]
            )
            state = native.initialize_run(namespace(args_for(root)))
            self.assertTrue(native.append_run_row(namespace(args_for(root)), state))
            with self.assertRaises(IndexError):
                native.append_run_row(namespace(args_for(root)), state)
            self.assertEqual(len(state["rows"]), 1)
            # Provider failure remains a row, main returns zero, no retry occurs.
            prompts(root, ("failed",))
            output = io.StringIO()
            with redirect_stdout(output):
                code = native.main(
                    [
                        "--prompts-json",
                        str(root / "input.json"),
                        "--output-dir",
                        str(root / "main"),
                        "--execute",
                        "--codex-bin",
                        "fixture-codex",
                        "--timeout",
                        "17",
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())["rows"][0]["returncode"], 9)
            for workers in (1, 2):
                prompts(root, ("timeout", "valid"))
                args = namespace(
                    args_for(
                        root,
                        execute=True,
                        workers=workers,
                        limit=None,
                        output_dir=str(root / f"timeout{workers}"),
                    )
                )
                for module in (old, native):
                    with self.assertRaises(subprocess.TimeoutExpired):
                        module.run(args)
                    self.assertFalse(
                        (
                            args.output_dir / "codex_exec_judge_run_manifest.json"
                        ).exists()
                    )
                    self.assertFalse(
                        (args.output_dir / "codex_exec_judge_results.json").exists()
                    )
                if workers == 2:
                    self.assertTrue(
                        (
                            args.output_dir
                            / "prompts"
                            / f'{native.prompt_identifier({"case_id":"case1","candidate_id":"candidate","judge_id":"judge"},1)}.final.txt'
                        ).exists()
                    )

    def test_registered_tools_real_lunar_prism(self):
        with tempfile.TemporaryDirectory(prefix="judge-runner-") as raw:
            asyncio.run(self.scenario(Path(raw)))

    async def scenario(self, root):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], Path(DESCRIPTOR).parent.name)
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 3},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        packages = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
        bootstrap = (
            "import sys,runpy; sys.path.extend("
            + repr(packages)
            + "); runpy.run_path("
            + repr(str(ROOT / "tests/mcp/fixtures/codex_judge_runner_server.py"))
            + ',run_name="__main__")'
        )
        async with connected(
            manager,
            StdioConfig(command=sys.executable, args=["-c", bootstrap], cwd=str(ROOT)),
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=None):
                snapshot = assets(doc)
                w = compile_workflow(
                    "mcp:judge-runner",
                    workflow_documents([DESCRIPTOR], snapshot)[0],
                    tools if inventory is None else inventory,
                )
                return w, snapshot

            workflow, snapshot = compile(document)
            self.assertTrue(workflow["runnable"], workflow["diagnostics"])
            self.assertTrue(workflow["runtime_source"])
            self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
            self.assertFalse(compile(document, [])[0]["runnable"])
            self.assertFalse(
                compile(
                    document, [t for t in tools if t["name"] != PREFIX + "persist"]
                )[0]["runnable"]
            )

            async def authorize():
                pass

            async def run(args, doc=None, hook=None):
                w, a = compile(doc) if doc else (workflow, snapshot)
                self.assertTrue(w["runnable"], w["diagnostics"])
                observed = ObservedRemote(remote, hook)
                result = await execute(
                    w,
                    a,
                    {"args": args, "context": {"working_directory": str(root)}},
                    observed,
                    authorize,
                )
                return result, observed

            index = 0

            async def case(text="valid", **options):
                nonlocal index
                directory = root / str(index)
                directory.mkdir()
                index += 1
                rows = prompts(directory, (text, "failed", "invalid"))
                args = args_for(directory, **options)
                return directory, rows, args

            for text, options, branch in [
                ("valid", {}, "append_row"),
                ("valid", {"execute": True}, "append_row"),
                ("embedded", {"execute": True, "workers": 2}, "parallel_batch"),
                ("invalid", {"execute": True}, "append_row"),
                ("failed", {"execute": True, "workers": 2}, "parallel_batch"),
                ("missing", {"execute": True}, "append_row"),
                ("valid", {"case_id": "absent"}, "empty_state"),
                (
                    "valid",
                    {"execute": True, "workers": 2, "case_id": "absent"},
                    "parallel_batch",
                ),
            ]:
                directory, rows, args = await case(text, **options)
                result, observed = await run(args)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [PREFIX + "initialize", PREFIX + branch, PREFIX + "persist"],
                )
                m = result["outputs"]["manifest"]
                self.assertEqual(
                    json.loads(Path(m["artifacts"]["manifest"]).read_text()), m
                )
                selected = [] if args["case_id"] == "absent" else rows[:1]
                self.assertEqual(observed.seen[0][2]["state"]["selected"], selected)
                self.assertEqual(observed.seen[0][2]["state"]["rows"], [])
                self.assertEqual(m["selected_prompt_count"], len(selected))
                self.assertEqual(m["rows"], observed.seen[1][2]["state"]["rows"])
                self.assertEqual(
                    json.loads(Path(m["artifacts"]["selected_prompts"]).read_text()),
                    selected,
                )
                expected = [
                    r["result"] for r in m["rows"] if args["execute"] and "result" in r
                ]
                self.assertEqual(
                    json.loads(Path(m["artifacts"]["results"]).read_text())["results"],
                    expected,
                )
                self.assertEqual(m["completed_result_count"], len(expected))
                if selected:
                    row = m["rows"][0]
                    self.assertEqual(Path(row["prompt_path"]).read_text(), text)
                    if not args["execute"]:
                        self.assertEqual(row["status"], "dry_run_prompt_written")
                        self.assertFalse(Path(row["final_message_path"]).exists())
                    else:
                        self.assertEqual(
                            row["returncode"], 9 if text == "failed" else 0
                        )
                        self.assertEqual(len(row["stderr"]), 4000)
                        self.assertEqual(
                            row["result"].get("error"),
                            (
                                "codex_exec_output_not_strict_json"
                                if text in ("invalid", "missing")
                                else None
                            ),
                        )
                        calls = [
                            json.loads(s)
                            for s in (directory / "out/provider_calls.jsonl")
                            .read_text()
                            .splitlines()
                        ]
                        self.assertEqual(len(calls), 1)
                        self.assertEqual(calls[0]["input"], text)
                        self.assertEqual(calls[0]["cwd"], str(ROOT))
                        self.assertEqual(calls[0]["timeout"], 17)
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
                for c in result["calls"]:
                    self.assertTrue(c["transport_call_performed"])
                    self.assertEqual(len(c["input_digest"]), 64)
                    self.assertEqual(len(c["output_digest"]), 64)
            # Resume runs before execute, including invalid cached JSON. Empty
            # cached files fall through to preparation or external execution.
            for execution in (False, True):
                for cached in ('{"cached":true}', "invalid", ""):
                    directory, rows, args = await case(
                        resume=True, execute=execution, workers=2 if execution else 1
                    )
                    prompt_dir = directory / "out/prompts"
                    prompt_dir.mkdir(parents=True)
                    final = prompt_dir / (
                        source().prompt_identifier(rows[0], 0) + ".final.txt"
                    )
                    final.write_text(cached)
                    result, _ = await run(args)
                    self.assertEqual(result["status"], "accepted", result)
                    m = result["outputs"]["manifest"]
                    row = m["rows"][0]
                    self.assertEqual(
                        row["status"],
                        (
                            "reused_existing_final_message"
                            if cached
                            else "completed" if execution else "dry_run_prompt_written"
                        ),
                    )
                    self.assertEqual(
                        (directory / "out/provider_calls.jsonl").exists(),
                        execution and not cached,
                    )
                    self.assertEqual(m["completed_result_count"], int(execution))
                    if cached:
                        self.assertEqual(
                            row["returncode"], 2 if cached == "invalid" else 0
                        )
            # Explicit cwd preserves CLI relative artifact and input paths.
            prompts(root, ("valid",))
            args = args_for(root, prompts_json="input.json", output_dir="relative")
            result, _ = await run(args)
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(
                result["outputs"]["manifest"]["artifacts"]["manifest"],
                "relative/codex_exec_judge_run_manifest.json",
            )
            self.assertTrue(
                (root / "relative/codex_exec_judge_run_manifest.json").is_file()
            )
            for execution in (False, True):
                directory, rows, args = await case(
                    execute=execution, codex_bin="unavailable-codex"
                )
                result, _ = await run(args)
                self.assertEqual(
                    result["status"], "failed" if execution else "accepted", result
                )
                if execution:
                    self.assertEqual(len(result["calls"]), 1)
                    self.assertFalse(
                        (
                            directory / "out/selected_codex_exec_judge_prompts.json"
                        ).exists()
                    )
            for workers in (1, 2):
                directory, rows, args = await case(
                    "timeout", execute=True, workers=workers
                )
                result, _ = await run(args)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), 2)
                self.assertFalse(
                    (directory / "out/codex_exec_judge_run_manifest.json").exists()
                )
                self.assertFalse(
                    (directory / "out/codex_exec_judge_results.json").exists()
                )
                self.assertEqual(
                    len(
                        (directory / "out/provider_calls.jsonl")
                        .read_text()
                        .splitlines()
                    ),
                    1,
                )
            # Missing/malformed input and native filesystem faults stop exactly
            # at the owning call; already-written source artifacts survive.
            for bad in ("missing", "malformed"):
                directory, _, args = await case()
                if bad == "missing":
                    (directory / "input.json").unlink()
                else:
                    (directory / "input.json").write_text("{}")
                result, _ = await run(args)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 1)
            for stage, count in [("initialize", 2), ("append_row", 3)]:
                directory, _, args = await case()

                def fault(tool, arguments, value):
                    if tool == PREFIX + stage:
                        state = value["state"]
                        if stage == "initialize":
                            shutil.rmtree(state["artifacts"]["prompt_dir"])
                        else:
                            Path(state["artifacts"]["manifest"]).mkdir()

                result, _ = await run(args, hook=fault)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), count)
                self.assertIsNone(result["outputs"])
                if stage == "append_row":
                    self.assertTrue(
                        (directory / "out/codex_exec_judge_results.json").exists()
                    )
            # Actual exact-bound success was exercised above. Force only the
            # descriptor condition to test PRISM exhaustion, keeping tools real.
            exhausted = deepcopy(document)
            exhausted["flow"]["steps"][1]["until"] = {"literal": False}
            directory, _, args = await case()
            result, _ = await run(args, doc=exhausted)
            self.assertEqual(result["status"], "failed", result)
            self.assertIn("exhaust", str(result).lower())
            self.assertEqual(len(result["calls"]), 2)
            self.assertFalse(
                (directory / "out/codex_exec_judge_run_manifest.json").exists()
            )
            budget = deepcopy(document)
            budget["policy"]["limits"]["max_operation_calls"] = 2
            directory, _, args = await case()
            result, _ = await run(args, doc=budget)
            self.assertEqual(result["status"], "failed", result)
            self.assertIn("budget", str(result).lower())
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 2
            )
            # Direct calls exercise the registered tool's exhaustion error too.
            directory, _, args = await case()
            context = {"working_directory": str(root)}
            initialized = await remote.call(
                PREFIX + "initialize", dict(args=args, context=context)
            )
            advanced = await remote.call(
                PREFIX + "append_row",
                dict(args=args, state=initialized["state"], context=context),
            )
            self.assertTrue(advanced["done"])
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "append_row",
                    dict(args=args, state=advanced["state"], context=context),
                )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(RunnerTests)
    )
    raise SystemExit(
        0
        if result.wasSuccessful()
        and result.testsRun
        and len(result.skipped) < result.testsRun
        else 1
    )
