#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Original-source, real aggregate MCP and Lunar/PRISM deterministic fixtures.

The selected source has no provider/model or external compiler boundary. Fixed
presets, native argv and isolated files are the fixtures; no production stage is
substituted. PRISM parsing, checking, compilation and execution run unmodified.
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
from collections import Counter
from contextlib import redirect_stdout, redirect_stderr, chdir
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
import mathformer as hub
from theory_evolution_model_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.workflow_contract.validator import validate
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_paper_theory_evolution_model_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/theory-evolution-model.workflow.json"


def load_module(name, path):
    spec = importlib.util.spec_from_loader(name, SourceFileLoader(name, str(path)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def oracle():
    return load_module(
        "theory_original",
        ROOT / "tests/mcp/fixtures/theory_evolution_model_original.py.txt",
    )


def invoke(module, argv):
    stream, errors = io.StringIO(), io.StringIO()
    with (
        patch.object(sys, "argv", ["theory-model", *argv]),
        redirect_stdout(stream),
        redirect_stderr(errors),
    ):
        try:
            code = module.main()
        except SystemExit as error:
            code = error.code
    return code, stream.getvalue(), errors.getvalue()


def snapshot(document):
    def asset(path, content):
        return {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


class TheoryModelTests(unittest.TestCase):
    def test_original_cli_equivalence_and_fixed_prior(self):
        old, native = oracle(), source()
        self.assertEqual(native.default_model(), old.default_model())
        self.assertEqual(
            native.vector(anchor_coverage=1), old.vector(anchor_coverage=1)
        )
        self.assertEqual(native.vector()["dashboard_inspection"], 0.0)
        model = native.default_model()
        self.assertEqual(len(model["metrics"]), 13)
        self.assertEqual(len(model["protected_metrics"]), 5)
        self.assertEqual(len(model["phases"]), 8)
        self.assertEqual(sum(p["duration_steps"] for p in model["phases"]), 57)
        self.assertEqual(len(model["couplings"]), 6)
        self.assertEqual(len(model["observability_scenarios"]), 3)
        self.assertEqual(model["initial_state"]["anchor_validity"], 0.75)
        self.assertEqual(
            model["noise"],
            {"gain_sigma": 0.08, "regression_scale": 0.04, "cost_sigma": 0.15},
        )
        for phase in model["phases"]:
            self.assertEqual(set(phase["target"]), set(model["metrics"]))
        with tempfile.TemporaryDirectory() as directory, chdir(directory):
            output = Path("nested/prior.json")
            for preset in [[], ["--preset", "default-mathformer-theory"]]:
                for json_report in [False, True]:
                    argv = [*preset, "--output", str(output)] + (
                        ["--json"] if json_report else []
                    )
                    expected = invoke(old, argv)
                    data = output.read_bytes()
                    output.unlink()
                    self.assertEqual(invoke(native, argv), expected)
                    self.assertEqual(output.read_bytes(), data)
                    self.assertEqual(
                        data.decode(),
                        json.dumps(model, indent=2, sort_keys=True) + "\n",
                    )
            for argv in [
                [],
                ["--help"],
                ["--preset", "invalid"],
                ["--output", str(output), "--unknown"],
            ]:
                self.assertEqual(invoke(native, argv), invoke(old, argv))
            blocker = Path("blocker")
            blocker.write_text("blocked")
            for module in [old, native]:
                with self.assertRaises(OSError):
                    invoke(module, ["--output", str(blocker / "prior.json")])
            # Observe actual calls without replacing any native functions.
            calls = Counter()

            def observe(frame, event, arg):
                if event == "call" and frame.f_code.co_filename == native.__file__:
                    calls[frame.f_code.co_name] += 1

            previous = sys.getprofile()
            try:
                sys.setprofile(observe)
                self.assertEqual(invoke(native, ["--output", "counted.json"])[0], 0)
            finally:
                sys.setprofile(previous)
            self.assertEqual(calls["default_model"], 1)
            self.assertEqual(
                calls["vector"], 9
            )  # initial state plus eight static targets
            self.assertEqual(calls["persist_prior"], 1)
            self.assertEqual(calls["report_and_return"], 1)

    def test_native_errors_and_hub_preflight_without_launch(self):
        native = source()
        with self.assertRaises(KeyError):
            native.construct_prior({"preset": "unknown"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "serialization.json"
            with self.assertRaises(TypeError):
                native.persist_prior({"output": str(path)}, {"invalid": {1}})
            self.assertFalse(path.exists())
            closed = io.StringIO()
            closed.close()
            with redirect_stdout(closed), self.assertRaises(ValueError):
                native.report_and_return(
                    {"json": True}, native.default_model(), str(path)
                )
            registry = hub.build_registry()
            item = registry["paper:theory-evolution-model"]
            self.assertFalse(item.depends_on)
            self.assertIsNone(item.timeout_seconds)
            dry = hub.run_action(item.action_id, registry, hub.RunContext(dry_run=True))
            self.assertTrue(dry["ok"])
            self.assertEqual(dry["status"], "dry_run")
            self.assertEqual(dry["argv"][1:], list(item.command)[1:])
            bad = hub.run_action(
                item.action_id,
                registry,
                hub.RunContext(dry_run=True),
                extra_args=["--unexpected"],
            )
            self.assertFalse(bad["ok"])
            self.assertNotIn("status", bad)  # preflight precedes dry-run
            missing = replace(
                item, required_paths=("__absent_theory_model_source__.py",)
            )
            denied = hub.prepare_leaf_boundary(
                missing, hub.RunContext(dry_run=True), []
            )
            self.assertFalse(denied["execute"])
            self.assertIn("missing required path", str(denied["payload"]))
            # Exercise the real post-execution audit on isolated snapshots.
            before = hub.snapshot_repository(Path(directory))
            (Path(directory) / "undeclared.txt").write_text("fixture")
            failed = hub.finish_leaf_boundary(
                item,
                {"snapshot": before},
                {"ok": True, "stderr": ""},
                repository_root=Path(directory),
            )
            self.assertFalse(failed["ok"])
            self.assertEqual(failed["status"], "undeclared_writes")

    def test_contract_validation_and_generator_retention(self):
        authored_path = ROOT / AUTHORED
        result = validate(
            authored_path, repository_root=ROOT, require_declared_bindings=True
        )
        self.assertTrue(result["valid"], result["errors"])
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document, json.loads(authored_path.read_text()))
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        normalizer = load_module(
            "theory_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        generated = next(
            row for row in normalizer.inventory() if row["id"] == document["id"]
        )
        self.assertEqual(generated, document)

    def test_real_registered_aggregate_mcp_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_paper_theory_evolution_model_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 4},
        )
        manager = SessionManager()
        server = ROOT / "tests/mcp/fixtures/theory_evolution_model_server.py"
        # The aggregate server uses the repository's native backend dependencies;
        # the parent process uses Lunar's actual PRISM runtime environment.
        native_python = ROOT / ".venv/bin/python"
        self.assertTrue(
            native_python.is_file(), "Repository MCP environment is required"
        )
        failure = None
        with tempfile.TemporaryDirectory(prefix="theory-model-") as temporary:
            directory = Path(temporary)
            config = StdioConfig(
                command=str(native_python),
                args=[str(server), str(directory)],
                cwd=str(ROOT),
            )
            async with manager.open("theory", config, {}) as remote:
                try:
                    tools = [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in await remote.tools()
                    ]
                    self.assertIn(
                        "mathformer_run_workflow", {tool["name"] for tool in tools}
                    )

                    def compile(doc, inventory=None):
                        assets = snapshot(doc)
                        selected = workflow_documents([DESCRIPTOR], assets)[0]
                        compiled = compile_workflow(
                            "mcp:theory",
                            selected,
                            tools if inventory is None else inventory,
                        )
                        return compiled, assets

                    workflow, assets = compile(document)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(
                        set(workflow["bindings"]), set(document["operations"])
                    )
                    self.assertFalse(compile(document, [])[0]["runnable"])
                    for tool_name in [
                        "parse",
                        "construct",
                        "persist",
                        "report",
                        "help",
                    ]:
                        reduced = [
                            tool
                            for tool in tools
                            if tool["name"] != "mathformer_theory_model_" + tool_name
                        ]
                        self.assertFalse(compile(document, reduced)[0]["runnable"])

                    async def authorize():
                        pass

                    async def run(argv, doc=None):
                        compiled, received = compile(doc) if doc else (workflow, assets)
                        return await execute(
                            compiled,
                            received,
                            {
                                "argv": argv,
                                "context": {"working_directory": str(directory)},
                            },
                            remote,
                            authorize,
                        )

                    for explicit in [False, True]:
                        for json_report in [False, True]:
                            output = f"nested/{explicit}-{json_report}.json"
                            argv = (
                                (
                                    ["--preset", "default-mathformer-theory"]
                                    if explicit
                                    else []
                                )
                                + ["--output", output]
                                + (["--json"] if json_report else [])
                            )
                            with chdir(directory):
                                expected = invoke(oracle(), argv)
                            data = (directory / output).read_bytes()
                            (directory / output).unlink()
                            result = await run(argv)
                            self.assertEqual(result["status"], "accepted", result)
                            self.assertEqual((directory / output).read_bytes(), data)
                            self.assertEqual(json.loads(data), oracle().default_model())
                            self.assertEqual(
                                result["outputs"],
                                {
                                    "result": {
                                        "ok": True,
                                        "output": output,
                                        "model_id": "default-mathformer-theory",
                                        "metric_count": 13,
                                        "phase_count": 8,
                                    },
                                    "exit_code": 0,
                                    "report": expected[1],
                                },
                            )
                            self.assertEqual(
                                [c["tool"] for c in result["calls"]],
                                [
                                    "mathformer_theory_model_" + name
                                    for name in [
                                        "parse",
                                        "construct",
                                        "persist",
                                        "report",
                                    ]
                                ],
                            )
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                    absent = directory / "must-not-write.json"
                    result = await run(["--help", "--output", str(absent)])
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertIsNone(result["outputs"]["result"])
                    self.assertEqual(result["outputs"]["exit_code"], 0)
                    self.assertIn("--preset", result["outputs"]["report"])
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [
                            "mathformer_theory_model_parse",
                            "mathformer_theory_model_help",
                        ],
                    )
                    self.assertFalse(absent.exists())
                    for argv in [
                        [],
                        ["--preset", "unknown", "--output", str(absent)],
                        ["--output", str(absent), "--unexpected"],
                    ]:
                        result = await run(argv)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(len(result["calls"]), 1)
                        self.assertEqual(result["calls"][0]["status"], "rejected")
                        self.assertFalse(absent.exists())
                    blocker = directory / "blocker"
                    blocker.write_text("blocked")
                    failed = await run(["--output", str(blocker / "prior.json")])
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual(len(failed["calls"]), 3)
                    self.assertEqual(failed["calls"][-1]["status"], "rejected")
                    self.assertEqual(blocker.read_text(), "blocked")
                    # Bounds are enforced by Lunar; no simulated evolution loop.
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 2
                    failed = await run(["--output", str(absent)], bounded)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertIn("budget", str(failed).lower())
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in failed["calls"]
                        ),
                        2,
                    )
                    self.assertFalse(absent.exists())
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    compiled, received = compile(timed)

                    async def pending():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(
                            compiled,
                            received,
                            {
                                "argv": ["--output", str(absent)],
                                "context": {"working_directory": str(directory)},
                            },
                            remote,
                            pending,
                        )
                    self.assertFalse(absent.exists())
                    # The aggregate registration's real policy blocks escaped paths.
                    escaped = directory.parent / (directory.name + "-outside.json")
                    failed = await run(["--output", str(escaped)])
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(len(failed["calls"]), 3)
                    self.assertFalse(escaped.exists())
                except Exception as error:
                    failure = error
            if failure:
                raise failure
            readonly = StdioConfig(
                command=str(native_python),
                args=[str(server), str(directory), "--readonly"],
                cwd=str(ROOT),
            )
            async with manager.open("readonly", readonly, {}) as remote:
                with self.assertRaises(Exception):
                    await remote.call(
                        "mathformer_theory_model_persist",
                        {
                            "args": {"output": str(absent)},
                            "prior": oracle().default_model(),
                            "context": {"working_directory": str(directory)},
                        },
                    )
                self.assertFalse(absent.exists())
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
