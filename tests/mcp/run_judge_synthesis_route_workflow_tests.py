#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - select the host's Lunar interpreter before imports
"""Offline native/original parity, registered MCP and real Lunar/PRISM execution."""

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
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
FIXTURES = ROOT / "tests/mcp/fixtures"
PATHS = [
    str(ROOT / "scripts"),
    str(FIXTURES),
    str(LUNAR / "app/backend"),
    *[str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")],
]
sys.path[:0] = PATHS

import asyncio
from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import re
import shutil
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from judge_synthesis_route_tools import ACTIONS, ROUTE, checked_registry, selected_match
from judge_synthesis_route_boundary import (
    SOURCE,
    SMOKE,
    PROTOCOL,
    INPUT,
    OUTPUT,
    populate,
)
from judge_synthesis_report_tools import source as smoke_source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_report_formalphysics_judge_synthesis_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
PREFIX = "mathformer_judge_synthesis_route_"
REGISTRY = {key: hub.action_to_dict(hub.build_registry()[key]) for key in ACTIONS}
MATCH = {"score": 23, "matched_terms": ["formalphysics judge synthesis"]}
OPS = ["initialize"] + ["select_action", "execute_action", "advance"] * 2 + ["finish"]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "judge_synthesis_route_original.py.txt").read_text(), scope)
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
            "path": p,
            "content": t,
            "encoding": "text",
            "sha256": hashlib.sha256(t.encode()).hexdigest(),
        }
        for p, t in values.items()
    ]


def artifacts(root):
    directory = root / OUTPUT
    if not directory.is_dir():
        return {}
    return {
        p.name: re.sub(
            r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?\+00:00", "<date>", p.read_text()
        )
        for p in directory.iterdir()
        if p.is_file()
    }


def reset(root):
    path = root / OUTPUT
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()
    (root / "undeclared.json").unlink(missing_ok=True)
    log = root.parent / "native-processes.jsonl"
    log.unlink(missing_ok=True)


class Observed:
    def __init__(self, remote):
        self.remote, self.seen = remote, []

    async def tools(self):
        return await self.remote.tools()

    async def call(self, tool, arguments):
        result = await self.remote.call(tool, arguments)
        self.seen.append(
            (tool.removeprefix(PREFIX), deepcopy(arguments), deepcopy(result))
        )
        return result


class RouteTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.startup = tempfile.TemporaryDirectory()
        (Path(cls.startup.name) / "sitecustomize.py").write_text(
            "from judge_synthesis_route_boundary import install\ninstall()\n"
        )

    @classmethod
    def tearDownClass(cls):
        cls.startup.cleanup()

    def environment(self, root):
        return dict(
            PYTHONDONTWRITEBYTECODE="1",
            JUDGE_SYNTHESIS_TEST_ROOT=str(root),
            PYTHONPATH=os.pathsep.join([self.startup.name, str(FIXTURES)]),
        )

    @contextmanager
    def native_boundary(self, root):
        """Observe and forward native Python calls; deny any other process/network."""
        native_run = subprocess.run
        expected = {
            tuple(hub.resolve_command(hub.build_registry()[a].command)) for a in ACTIONS
        }
        calls = []

        def forward(argv, **kwargs):
            self.assertIn(tuple(argv), expected)
            self.assertEqual(Path(kwargs["cwd"]).resolve(), root)
            calls.append((list(argv), kwargs["timeout"]))
            return native_run(argv, **kwargs)

        def forbidden(*args, **kwargs):
            raise AssertionError("unexpected provider network call")

        with (
            patch.dict(os.environ, self.environment(root), clear=True),
            patch.object(subprocess, "run", forward),
            patch.object(socket, "create_connection", forbidden),
            patch.object(socket.socket, "connect", forbidden),
        ):
            yield calls

    def test_authored_generator_provenance_and_native_capabilities(self):
        normalizer = load(
            "judge_synthesis_route_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        d = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(normalizer.judge_synthesis_route_descriptor(), d)
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
        self.assertEqual([REGISTRY[a]["timeout_seconds"] for a in ACTIONS], [180, 300])
        self.assertEqual(
            REGISTRY[ACTIONS[1]]["command"][2:],
            ["--comparative-report", INPUT, "--output-dir", OUTPUT, "--json"],
        )
        self.assertTrue(
            any(
                row["path"] == "scripts/mathformer.py"
                and row["selector"] == "run_intent_match"
                for row in d["provenance"]["sources"]
            )
        )
        for row in d["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        for field, value in [
            ("command", ["arbitrary"]),
            ("timeout_seconds", 1),
            ("depends_on", [ACTIONS[1]]),
        ]:
            bad = deepcopy(REGISTRY)
            bad[ACTIONS[0]][field] = value
            with self.assertRaisesRegex(ValueError, "registry"):
                checked_registry(bad)

    def test_actual_report_steps_recorded_provider_and_compiler_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            populate(root, ROOT)
            builder = load("judge_synthesis_route_builder", root / SOURCE)
            fixture = smoke_source()
            result_file = root / "recorded-judges.json"
            fixture.write_codex_results(result_file)
            args = builder.parse_args(
                [
                    "--comparative-report",
                    str(root / INPUT),
                    "--codex-results-json",
                    str(result_file),
                    "--output-dir",
                    str(root / OUTPUT),
                    "--json",
                ]
            )
            # Supplied evidence uses the actual parser, attachment, aggregation,
            # five-aspect traversal and renderer. No provider/compiler is called.
            with self.native_boundary(root) as calls:
                loaded = builder.load_inputs(args)
                report = builder.attach_results(loaded)
                synthesis = builder.build_synthesis(report)
                with redirect_stdout(io.StringIO()):
                    emitted = builder.emit(args, synthesis)
                with self.assertRaisesRegex(AssertionError, "unexpected provider"):
                    socket.create_connection(("provider.invalid", 443))
                with self.assertRaises(AssertionError):
                    subprocess.run(["lean", "--version"])
            self.assertEqual(calls, [])
            self.assertEqual(
                synthesis["approaches"]["current_mathformer_lean"]["accepted_count"], 1
            )
            self.assertEqual(
                synthesis["approaches"]["external_formaldiscovery"]["blocked_count"], 1
            )
            self.assertEqual(
                synthesis["judge_review_synthesis"]["codex_exec_results_ingested"], 2
            )
            self.assertFalse(synthesis["policy"]["reference_answer_is_gold"])
            self.assertTrue(synthesis["synthesis_todos"])
            self.assertEqual(emitted["returncode"], 0)
            self.assertEqual(
                set(artifacts(root)),
                {
                    "synthesis_report.json",
                    "synthesis_report.md",
                    "synthesis_report.html",
                    "synthesis_todos.md",
                },
            )
            for gap, text in [(0, "tied"), (0.5, "slightly"), (0.75, "clear")]:
                approaches = {
                    "first": {"aspect_scores": dict.fromkeys(builder.ASPECTS, 3 + gap)},
                    "second": {"aspect_scores": dict.fromkeys(builder.ASPECTS, 3)},
                }
                state = builder.pack_aspects(approaches)
                for i in range(5):
                    _, done = builder.compare_next_aspect(state)
                    self.assertEqual(state["index"], i + 1)
                    self.assertEqual(len(state["rows"]), i + 1)
                    self.assertEqual(done, i == 4)
                    self.assertIn(text, state["rows"][-1]["interpretation"])
                before = deepcopy(state)
                with self.assertRaises(IndexError):
                    builder.compare_next_aspect(state)
                self.assertEqual(state, before)

    def test_registered_mcp_lunar_prism_and_native_original_parity(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        d = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory(prefix="judge-synthesis-route-") as raw:
            root = Path(raw).resolve() / "repo"
            populate(root, ROOT)
            startup = (
                "from judge_synthesis_route_boundary import serve;serve("
                + repr(str(root))
                + ","
                + repr(self.startup.name)
                + ","
                + repr(str(FIXTURES))
                + ")"
            )
            manager, failure = SessionManager(), None
            async with manager.open(
                "judge-synthesis-route",
                StdioConfig(
                    command=sys.executable, args=["-c", startup], cwd=str(ROOT)
                ),
                {"PYTHONPATH": os.pathsep.join(PATHS), "PYTHONDONTWRITEBYTECODE": "1"},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile_doc(document, inventory=tools):
                        assets = snapshot(document)
                        record = workflow_documents([DESCRIPTOR], assets)[0]
                        self.assertTrue(record["validation"]["valid"], record)
                        return (
                            compile_workflow(
                                "mcp:judge-synthesis-route", record, inventory
                            ),
                            assets,
                        )

                    compiled, assets = compile_doc(d)
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertEqual(compiled["runtime_status"], "ready")
                    self.assertTrue(compiled["prism_source"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(set(compiled["bindings"]), set(d["operations"]))
                    self.assertFalse(compile_doc(d, [])[0]["runnable"])
                    self.assertFalse(
                        compile_doc(
                            d,
                            [
                                t
                                for t in tools
                                if t["name"] != PREFIX + "execute_action"
                            ],
                        )[0]["runnable"]
                    )
                    advertised = {t["name"]: t for t in tools}
                    for op in d["operations"].values():
                        b = op["execution"]["binding"]
                        self.assertEqual(b["target"], b["operation"])
                        interface = advertised[b["target"]]
                        self.assertEqual(
                            set(interface["inputSchema"]["properties"]),
                            set(op["inputs"]),
                        )
                        self.assertEqual(
                            set(interface["outputSchema"]["properties"]),
                            set(op["outputs"]),
                        )

                    async def allow():
                        pass

                    async def run(values, changed=None):
                        c, a = (
                            compile_doc(changed)
                            if changed is not None
                            else (compiled, assets)
                        )
                        self.assertTrue(c["runnable"], c["diagnostics"])
                        observed = Observed(remote)
                        result = await execute(c, a, values, observed, allow)
                        return result, observed.seen

                    inputs = dict(
                        match=MATCH,
                        registry=REGISTRY,
                        context=vars(hub.RunContext()),
                        repository_root=str(root),
                    )
                    for mode in [
                        "native",
                        "dry",
                        "missing_smoke",
                        "missing_protocol",
                        "missing_input",
                        "invalid_json",
                        "write_failure",
                        "partial_write",
                        "undeclared_write",
                    ]:
                        for keep in [False, True]:
                            reset(root)
                            populate(root, ROOT)
                            if mode == "missing_smoke":
                                (root / SMOKE).unlink()
                            if mode == "missing_protocol":
                                (root / PROTOCOL).unlink()
                            if mode == "missing_input":
                                (root / INPUT).unlink()
                            if mode == "invalid_json":
                                (root / INPUT).write_text("{invalid")

                            def block_output():
                                if mode == "write_failure":
                                    (root / OUTPUT).parent.mkdir(
                                        parents=True, exist_ok=True
                                    )
                                    (root / OUTPUT).write_text(
                                        "blocks output directory"
                                    )
                                if mode == "partial_write":
                                    (root / OUTPUT / "synthesis_report.md").mkdir(
                                        parents=True
                                    )
                                if mode == "undeclared_write":
                                    (root / OUTPUT).mkdir(parents=True)
                                    (root / "undeclared.json").write_text("{}")
                                    (
                                        root / OUTPUT / "synthesis_report.json"
                                    ).symlink_to(root / "undeclared.json")

                            block_output()
                            values = deepcopy(inputs)
                            values["context"].update(
                                keep_going=keep, dry_run=mode == "dry"
                            )
                            result, seen = await run(values)
                            self.assertEqual(result["status"], "accepted", result)
                            actual_files = artifacts(root)
                            log = root.parent / "native-processes.jsonl"
                            launches = (
                                [
                                    json.loads(line)
                                    for line in log.read_text().splitlines()
                                ]
                                if log.exists()
                                else []
                            )
                            reset(root)
                            block_output()
                            with self.native_boundary(root) as native_calls:
                                expected = original()(
                                    selected_match(MATCH),
                                    checked_registry(REGISTRY),
                                    hub.RunContext(**values["context"]),
                                    repository_root=root,
                                )
                            self.assertEqual(result["outputs"], {"result": expected})
                            self.assertEqual(actual_files, artifacts(root))
                            got = result["outputs"]["result"]
                            early = (
                                mode in ["missing_smoke", "missing_protocol"]
                                and not keep
                            )
                            count = 1 if early else 2
                            self.assertEqual(len(got["children"]), count)
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]],
                                OPS[:4] + ["finish"] if early else OPS,
                            )
                            self.assertEqual(
                                [s[0] for s in seen],
                                [c["operation"] for c in result["calls"]],
                            )
                            self.assertEqual(got["ok"], mode in ["native", "dry"])
                            self.assertEqual(
                                got["status"],
                                (
                                    "intent_run_completed"
                                    if got["ok"]
                                    else "intent_run_failed"
                                ),
                            )
                            self.assertEqual(got["route"]["score"], MATCH["score"])
                            self.assertEqual(
                                got["route"]["matched_terms"], MATCH["matched_terms"]
                            )
                            advances = [v for op, _, v in seen if op == "advance"]
                            self.assertEqual(
                                [len(v["state"]["children"]) for v in advances],
                                list(range(1, count + 1)),
                            )
                            self.assertEqual(
                                [v["done"] for v in advances],
                                [True] if early else [False, True],
                            )
                            for index, child in enumerate(got["children"]):
                                self.assertEqual(
                                    child["argv"],
                                    hub.resolve_command(
                                        hub.build_registry()[ACTIONS[index]].command
                                    ),
                                )
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["replay_artifacts"])
                            if mode == "native":
                                self.assertEqual(
                                    [timeout for _, timeout in native_calls], [180, 300]
                                )
                                self.assertEqual(
                                    [row["timeout"] for row in launches],
                                    [180, None, 300],
                                )
                                self.assertTrue(
                                    json.loads(got["children"][0]["stdout"])["ok"]
                                )
                                report = json.loads(
                                    actual_files["synthesis_report.json"]
                                )
                                self.assertEqual(
                                    report["judge_review_synthesis"][
                                        "codex_exec_results_ingested"
                                    ],
                                    0,
                                )
                                self.assertEqual(len(report["aspect_comparison"]), 5)
                                self.assertTrue(
                                    any(
                                        "pending" in json.dumps(t).lower()
                                        for t in report["synthesis_todos"]
                                    )
                                )
                                for marker in smoke_source().HTML_MARKERS:
                                    self.assertIn(
                                        marker, actual_files["synthesis_report.html"]
                                    )
                                self.assertTrue(
                                    all(c["write_audit"]["ok"] for c in got["children"])
                                )
                            if mode == "missing_smoke" and keep:
                                self.assertFalse(got["ok"])
                                self.assertTrue(got["children"][1]["ok"])
                            if mode in [
                                "missing_input",
                                "invalid_json",
                                "write_failure",
                                "partial_write",
                            ]:
                                self.assertTrue(got["children"][0]["ok"])
                                self.assertEqual(got["children"][1]["returncode"], 1)
                                self.assertTrue(got["children"][1]["stderr"])
                            if mode == "partial_write":
                                self.assertEqual(
                                    set(actual_files), {"synthesis_report.json"}
                                )
                            if mode == "undeclared_write":
                                child = got["children"][1]
                                self.assertEqual(child["returncode"], 0)
                                self.assertEqual(child["status"], "undeclared_writes")
                                self.assertEqual(
                                    child["write_audit"]["unexpected_paths"],
                                    ["undeclared.json"],
                                )
                    reset(root)
                    populate(root, ROOT)
                    values = deepcopy(inputs)
                    values["context"]["dry_run"] = True
                    for change in ["exhaust", "never_done", "budget"]:
                        short = deepcopy(d)
                        if change == "exhaust":
                            short["flow"]["steps"][1]["max_iterations"] = 1
                        if change == "never_done":
                            short["flow"]["steps"][1]["until"] = {"literal": False}
                        if change == "budget":
                            short["policy"]["limits"]["max_operation_calls"] = 4
                        result, seen = await run(values, short)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            [s[0] for s in seen],
                            OPS[:7] if change == "never_done" else OPS[:4],
                        )
                        self.assertNotIn("finish", [s[0] for s in seen])
                    bad = deepcopy(values)
                    bad["registry"][ACTIONS[0]]["command"] = ["arbitrary"]
                    result, seen = await run(bad)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(result["calls"][-1]["operation"], "execute_action")
                    self.assertIsNone(result["outputs"])
                    bad["registry"] = {}
                    result, _ = await run(bad)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(result["calls"][-1]["operation"], "finish")
                    with self.assertRaises(KeyError):
                        original()(
                            selected_match(MATCH),
                            {},
                            hub.RunContext(dry_run=True),
                            repository_root=root,
                        )
                    # Port-level immutable history, sticky failure, exact second
                    # iteration stop and exhausted-cursor rejection.
                    context = vars(hub.RunContext(dry_run=True, keep_going=True))
                    state = (await remote.call(PREFIX + "initialize", {}))["state"]
                    child = (
                        await remote.call(
                            PREFIX + "execute_action",
                            dict(
                                action_id=ACTIONS[0],
                                registry={},
                                context=context,
                                repository_root=str(root),
                            ),
                        )
                    )["child"]
                    advanced = await remote.call(
                        PREFIX + "advance",
                        dict(state=state, child=child, context=context),
                    )
                    self.assertFalse(advanced["done"])
                    good = (
                        await remote.call(
                            PREFIX + "execute_action",
                            dict(
                                action_id=ACTIONS[1],
                                registry=REGISTRY,
                                context=context,
                                repository_root=str(root),
                            ),
                        )
                    )["child"]
                    final = await remote.call(
                        PREFIX + "advance",
                        dict(state=advanced["state"], child=good, context=context),
                    )
                    self.assertTrue(final["done"])
                    self.assertFalse(final["state"]["ok"])
                    self.assertEqual(final["state"]["children"], [child, good])
                    self.assertEqual(state, {"ok": True, "children": []})
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            PREFIX + "select_action",
                            dict(state=final["state"], match=MATCH),
                        )
                    # The nullable context port retains the real default mount;
                    # only a dry run is allowed against the project itself.
                    default = await remote.call(
                        PREFIX + "execute_action",
                        dict(
                            action_id=ACTIONS[1],
                            registry=REGISTRY,
                            context=context,
                            repository_root=None,
                        ),
                    )
                    self.assertEqual(default["child"]["status"], "dry_run")
                    self.assertEqual(default["child"]["cwd"], hub.rel(hub.REPO_ROOT))
                    timed = deepcopy(d)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    c, a = compile_doc(timed)

                    async def wait_authority():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(c, a, values, remote, wait_authority)
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure is not None:
                raise failure
        # Exercise the actual production registration's service restrictions.
        import mcp_server as server

        args = dict(
            action_id=ACTIONS[0],
            context=vars(hub.RunContext()),
            registry=REGISTRY,
            repository_root=str(Path(gettempdir())),
        )
        with patch.object(server, "_READONLY", True):
            with self.assertRaisesRegex(Exception, "read-only"):
                await server.mcp.call_tool(PREFIX + "execute_action", args)
        with patch.object(
            server, "_ALLOWED_WRITE_ROOTS", [Path(str(Path(gettempdir()) / "denied"))]
        ):
            with self.assertRaisesRegex(Exception, "service roots"):
                await server.mcp.call_tool(PREFIX + "execute_action", args)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RouteTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(
        0
        if result.wasSuccessful() and result.testsRun > 0 and not result.skipped
        else 1
    )
