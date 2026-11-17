#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline registered-tool integration through the real Lunar/PRISM runtime."""

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
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
    str(ROOT),
]
sys.path.extend(SITES)
os.environ["PYTHONPATH"] = os.pathsep.join(SITES)
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
import mathformer as hub
from physics_sympy_controlled_route_tools import (
    selected_match,
    register_physics_sympy_controlled_route_tools,
    PREFIX,
    OUTPUT,
    ACTION,
)
from physics_sympy_controlled_tree import populate, FILES
from reasoning_route_compiler import install as compiler_fixture

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
BASE = "skills/control/workflow-contract-validator/"
AUTHORED = ROOT / BASE / "references/physics-sympy-controlled-route.workflow.json"
DESCRIPTOR = (
    BASE
    + "references/normalized-workflows/route/route_formalize_physics_sympy_workflow/workflow.yaml"
)
MATCH = {"score": 17, "matched_terms": ["physics", "sympy"]}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/physics_sympy_controlled_route_original.py.txt"
        ).read_text(),
        scope,
    )
    return SimpleNamespace(**scope)


def stable(value):
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items() if k not in ("generated_at",)}
    if isinstance(value, list):
        return [stable(v) for v in value]
    if isinstance(value, str):
        try:
            return stable(json.loads(value))
        except (ValueError, TypeError):
            return value
    return value


def snapshot(doc):
    texts = {
        r["path"]: (ROOT / r["path"]).read_text() for r in doc["provenance"]["sources"]
    }
    texts[DESCRIPTOR] = json.dumps(doc)
    return [
        dict(
            path=p,
            content=t,
            encoding="text",
            sha256=hashlib.sha256(t.encode()).hexdigest(),
        )
        for p, t in texts.items()
    ]


class ControlledRouteTests(unittest.TestCase):
    maxDiff = None

    def test_authored_generator_provenance_and_native_identity(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(doc, json.loads(AUTHORED.read_text()))
        generator = load(
            ROOT / BASE / "scripts/normalize_workflows.py", "controlled_normalizer"
        )
        self.assertEqual(generator.physics_sympy_controlled_route_descriptor(), doc)
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(doc["aliases"], ["formalize.physics.sympy"])
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 13},
        )
        self.assertEqual(doc["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertEqual(doc["policy"]["resume"]["mode"], "none")
        self.assertEqual(doc["flow"]["steps"][1]["max_iterations"], 1)
        self.assertEqual(
            doc["flow"]["steps"][1]["body"]["steps"][1]["cases"][0]["body"]["steps"][0][
                "max_iterations"
            ],
            8,
        )
        self.assertTrue(
            any(
                s["path"] == "scripts/mathformer.py"
                and s["selector"] == "run_intent_match"
                for s in doc["provenance"]["sources"]
            )
        )
        for source in doc["provenance"]["sources"]:
            self.assertEqual(
                source["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest(),
            )
        item = hub.build_registry()[ACTION]
        self.assertEqual(item.depends_on, ())
        self.assertIsNone(item.timeout_seconds)
        self.assertEqual(list(item.command), [".venv/bin/python", FILES[0], "--json"])
        for keep in (False, True):
            state = hub.initialize_intent_state()
            state, done = hub.advance_intent_state(
                state, {"ok": False}, hub.RunContext(keep_going=keep), 1
            )
            self.assertTrue(done)
            self.assertEqual(state, {"ok": False, "children": [{"ok": False}]})

    def test_real_source_inputs_validation_and_dependency_classifier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = populate(Path(tmp).resolve() / "repo", ROOT)
            pipeline = load(root / FILES[1], "controlled_native_inputs")
            cli = load(root / FILES[0], "controlled_native_cli")
            cases = pipeline.controlled_suite_initialize(root / OUTPUT)
            draft = pipeline.controlled_suite_generate(root / OUTPUT, cases)
            report = pipeline.controlled_suite_assess(draft)
            # A report is an actual source-step input, not a replacement method.
            # Deliberately invalid validation data must persist and must not
            # prevent the next independent source case from executing.
            report["status"] = "blocked"
            cases = pipeline.controlled_suite_append(
                root / OUTPUT, cases, draft, report, True
            )
            self.assertFalse(cases[0]["controlled_validation_ok"])
            self.assertIn("consistency", cases[0])
            cases = pipeline.controlled_suite_step(root / OUTPUT, cases, False)
            self.assertEqual(
                [c["case_id"] for c in cases], pipeline.controlled_case_ids()[:2]
            )
            self.assertEqual(cases[0]["status"], "blocked")
            final = pipeline.controlled_suite_finalize(root / OUTPUT, cases)
            self.assertFalse(final["ok"])
            self.assertTrue((root / OUTPUT / "suite_report.json").exists())
            with self.assertRaisesRegex(ValueError, "exhausted"):
                pipeline.controlled_suite_generate(root / OUTPUT, [{}] * 8)
            missing = ModuleNotFoundError("No module named 'sympy'", name="sympy")
            blocker = cli.controlled_exception_report(missing)
            self.assertFalse(blocker["ok"])
            self.assertEqual(blocker["case_count"], 0)
            self.assertIsNone(
                cli.controlled_exception_report(
                    ModuleNotFoundError("other", name="other")
                )
            )
            self.assertIsNone(cli.controlled_exception_report(ValueError("bad input")))

    def test_policy_and_native_compiler_boundary_fixture(self):
        async def policy():
            server = FastMCP("policy")
            register_physics_sympy_controlled_route_tools(
                server,
                lambda: (_ for _ in ()).throw(PermissionError("read-only service")),
                lambda p: True,
            )
            with self.assertRaisesRegex(Exception, "read-only"):
                await server.call_tool(
                    PREFIX + "prepare_attempt",
                    dict(
                        state=hub.initialize_intent_state(),
                        context=vars(hub.RunContext()),
                        repository_root=None,
                    ),
                )
            restricted = FastMCP("restricted")
            register_physics_sympy_controlled_route_tools(
                restricted, lambda: None, lambda p: False
            )
            with self.assertRaisesRegex(Exception, "service roots"):
                await restricted.call_tool(
                    PREFIX + "prepare_attempt",
                    dict(
                        state=hub.initialize_intent_state(),
                        context=vars(hub.RunContext()),
                        repository_root=None,
                    ),
                )

        asyncio.run(policy())
        # This route has no provider or external compiler call. The deterministic
        # external compiler fixture independently verifies its shared hub process
        # capture boundary, without changing a production action or PRISM.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            boundary = SimpleNamespace()
            calls = compiler_fixture(boundary, root)
            for mode in ("accept", "reject", "timeout", "write", "launch_error"):
                action = replace(
                    hub.build_registry()[ACTION],
                    command=("fixture-reasoning-compiler", mode),
                    required_paths=(),
                    timeout_seconds=30,
                )
                with patch.object(hub, "subprocess", boundary.subprocess):
                    if mode == "launch_error":
                        with self.assertRaises(OSError):
                            hub.run_leaf_action(
                                action, hub.RunContext(), (), repository_root=root
                            )
                        continue
                    result = hub.run_leaf_action(
                        action, hub.RunContext(), (), repository_root=root
                    )
                self.assertEqual(result["ok"], mode == "accept")
                self.assertEqual(
                    result["status"],
                    (
                        "timeout"
                        if mode == "timeout"
                        else "undeclared_writes" if mode == "write" else "completed"
                    ),
                )
            self.assertEqual([c["timeout"] for c in calls], [30] * 5)

    def test_registered_mcp_lunar_prism_runtime(self):
        asyncio.run(self.connected())

    async def connected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr(
                    [
                        str(ROOT / "scripts"),
                        str(ROOT / "tests/mcp/fixtures"),
                        str(ROOT),
                        *SITES,
                    ]
                )
                + ";from physics_sympy_controlled_tree import serve;serve("
                + repr(str(base))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "controlled",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
            ) as remote:
                try:
                    await self.checks(base, remote)
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure

    async def checks(self, base, remote):
        doc = yaml.safe_load(CONTRACT.read_text())
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(document, inventory=None):
            assets = snapshot(document)
            parsed = workflow_documents([DESCRIPTOR], assets)[0]
            self.assertTrue(parsed["validation"]["valid"], parsed)
            compiled = compile_workflow(
                "mcp:controlled", parsed, tools if inventory is None else inventory
            )
            return compiled, assets

        compiled, assets = compile(doc)
        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
        self.assertEqual(compiled["runtime_status"], "ready")
        self.assertIsNotNone(compiled["runtime_source"])
        unbound, _ = compile(doc, [])
        self.assertFalse(unbound["runnable"])

        async def authorize():
            pass

        async def run(root, *, dry=False, keep=False, document=None):
            graph, received = (
                compile(document) if document is not None else (compiled, assets)
            )
            self.assertTrue(graph["runnable"], graph["diagnostics"])
            inputs = dict(
                context=vars(hub.RunContext(dry_run=dry, keep_going=keep)),
                match=MATCH,
                repository_root=str(root),
            )
            return await execute(graph, received, inputs, remote, authorize), inputs

        for keep in (False, True):
            root = base / f"missing-{keep}"
            root.mkdir()
            result, inputs = await run(root, keep=keep)
            self.assertEqual(result["status"], "accepted", result)
            self.assertFalse(result["outputs"]["result"]["ok"])
            self.assertEqual(
                result["outputs"]["result"],
                original().run_intent_match(
                    selected_match(MATCH),
                    hub.build_registry(),
                    hub.RunContext(**inputs["context"]),
                    repository_root=root,
                ),
            )
            self.assertEqual(
                [c["operation"] for c in result["calls"]],
                [
                    "initialize_route",
                    "prepare_attempt",
                    "return_early",
                    "advance_route",
                    "finish_route",
                ],
            )
        root = populate(base / "dry", ROOT)
        result, inputs = await run(root, dry=True)
        self.assertEqual(result["status"], "accepted", result)
        self.assertTrue(result["outputs"]["result"]["ok"])
        self.assertFalse((root / OUTPUT).exists())
        self.assertEqual(
            result["outputs"]["result"],
            original().run_intent_match(
                selected_match(MATCH),
                hub.build_registry(),
                hub.RunContext(**inputs["context"]),
                repository_root=root,
            ),
        )
        root = populate(base / "complete", ROOT)
        result, inputs = await run(root)
        self.assertEqual(result["status"], "accepted", result)
        output = result["outputs"]["result"]
        self.assertTrue(output["ok"], output)
        child = output["children"][0]
        suite = json.loads(child["stdout"])
        self.assertEqual(child["returncode"], 0)
        self.assertEqual(len(result["calls"]), 13)
        self.assertEqual(
            [c["operation"] for c in result["calls"]],
            ["initialize_route", "prepare_attempt"]
            + ["process_case"] * 8
            + ["finish_suite", "advance_route", "finish_route"],
        )
        self.assertEqual(suite["case_count"], 8)
        self.assertEqual(
            [c["case_id"] for c in suite["cases"]], suite["controlled_case_ids"]
        )
        self.assertTrue(
            all(
                c["status"] == "complete" and c["controlled_validation_ok"]
                for c in suite["cases"]
            )
        )
        self.assertTrue(all("consistency" not in c for c in suite["cases"]))
        self.assertTrue(child["write_audit"]["ok"])
        self.assertEqual(
            json.loads((root / OUTPUT / "suite_report.json").read_text()), suite
        )
        for case in suite["cases"]:
            for field in (
                "artifact",
                "consistency_report_path",
                "validation_path",
                "expectation_path",
                "equational_derivation_path",
                "equational_derivation_html_path",
            ):
                self.assertTrue((root / case[field]).is_file())
        self.assertTrue(result["runtime"]["effect_records"])
        self.assertTrue(result["runtime"]["provenance"])
        self.assertTrue(result["replay_artifacts"])
        # Original authoritative entrypoint, same isolated source and interpreter.
        # After an initial run, identical bytes make write-audit comparison fair.
        repeated, _ = await run(root)
        expected = original().run_intent_match(
            selected_match(MATCH),
            hub.build_registry(),
            hub.RunContext(**inputs["context"]),
            repository_root=root,
        )
        actual = repeated["outputs"]["result"]
        self.assertEqual(stable(actual), stable(expected))
        # Filesystem input faults execute the real exception path, including an
        # early initialize failure and a failure after a persisted case prefix.
        for position in (None, 1):
            root = populate(base / f"failure-{position}", ROOT)
            if position is None:
                (root / OUTPUT).parent.mkdir(parents=True)
                (root / OUTPUT).write_text("directory blocked")
            else:
                first_ids = suite["controlled_case_ids"]
                target = root / OUTPUT / first_ids[position]
                target.parent.mkdir(parents=True)
                target.write_text("case directory blocked")
            result, _ = await run(root, keep=True)
            self.assertEqual(result["status"], "accepted", result)
            child = result["outputs"]["result"]["children"][0]
            self.assertFalse(child["ok"])
            self.assertEqual(child["returncode"], 1)
            self.assertIn("Traceback", child["stderr"])
            self.assertEqual(child["stdout"], "")
            self.assertFalse((root / OUTPUT / "suite_report.json").exists())
            self.assertEqual(
                sum(c["operation"] == "process_case" for c in result["calls"]),
                0 if position is None else 2,
            )
            if position is not None:
                self.assertTrue(
                    (
                        root
                        / OUTPUT
                        / suite["controlled_case_ids"][0]
                        / "controlled_validation.json"
                    ).exists()
                )
        # Exhaustion at seven prevents suite finalization, while the actual eighth
        # true done condition exited normally above.
        changed = deepcopy(doc)
        changed["flow"]["steps"][1]["body"]["steps"][1]["cases"][0]["body"]["steps"][0][
            "max_iterations"
        ] = 7
        root = populate(base / "exhausted", ROOT)
        result, _ = await run(root, document=changed)
        self.assertEqual(result["status"], "failed", result)
        self.assertEqual(result["failure_disposition"], "fail")
        self.assertIsNone(result["outputs"])
        self.assertEqual(
            sum(c["operation"] == "process_case" for c in result["calls"]), 7
        )
        self.assertFalse(any(c["operation"] == "finish_suite" for c in result["calls"]))
        self.assertFalse((root / OUTPUT / "suite_report.json").exists())
        changed = deepcopy(doc)
        changed["policy"]["limits"]["max_operation_calls"] = 2
        root = populate(base / "budget", ROOT)
        result, _ = await run(root, document=changed)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(
            sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 2
        )
        root = populate(base / "launch-error", ROOT)
        (root / ".venv/bin/python").unlink()
        result, _ = await run(root)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(
            [c["operation"] for c in result["calls"]],
            ["initialize_route", "prepare_attempt"],
        )
        launches = [
            json.loads(line)
            for line in (base / "launches.jsonl").read_text().splitlines()
        ]
        self.assertTrue(
            all(
                launch["argv"] == [".venv/bin/python", FILES[0], "--json"]
                for launch in launches
            )
        )
        self.assertEqual(
            sum(launch["cwd"] == str(base / "complete") for launch in launches), 2
        )


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ControlledRouteTests)
    )
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
