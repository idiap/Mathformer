#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real route, registered MCP, Lunar compiler, PRISM checker/runtime; offline boundaries."""

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
sys.path[:0] = [
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp"),
    str(ROOT / "tests/mcp/fixtures"),
    str(LUNAR / "app/backend"),
    str(LUNAR.parent / "abducer/abducer-prism/src"),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml
import mathformer as hub
from prism_native_route_tools import (
    ACTION,
    ROUTE,
    checked_registry,
    selected_match,
    StepProcess,
)
from run_prism_verification_workflow_tests import (
    fixture,
    native,
    stable,
    CompilerProviderFixture,
)
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_prism_native_semantic_parallel_e2e_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 19,
    "matched_terms": ["native", "parallel", "e2e"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
PREFIX = "mathformer_prism_route_"
EXPECTED = (
    ["initialize"] + ["validate_entry"] * 14 + ["await_entry"] * 14 + ["finalize"]
)


def snapshot(doc):
    values = {
        r["path"]: (ROOT / r["path"]).read_text() for r in doc["provenance"]["sources"]
    }
    values[DESCRIPTOR] = json.dumps(doc)
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    return [
        dict(
            path=p,
            content=s,
            encoding="text",
            sha256=hashlib.sha256(s.encode()).hexdigest(),
        )
        for p, s in values.items()
    ]


def put(root, path, text, executable=False):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    if executable:
        target.chmod(0o755)
    return target


def populate(base):
    root = base / "repository"
    root.mkdir()
    fixture(root)  # exact generated plans/hashes with refreshed source fingerprints
    put(
        root,
        "scripts/prism/reviewed_reasoning_projections.json",
        native.PROJECTION_SPECS.read_text(),
    )
    # Trampoline imports the real verifier and replaces only external run/verify-run.
    put(
        root,
        "scripts/prism/verify_mathformer_prism.py",
        "from types import SimpleNamespace\n"
        "from prism_route_boundary import Boundary\n"
        "from prism_verification_tools import native\n"
        "native.subprocess = SimpleNamespace(run=Boundary().run)\n"
        "raise SystemExit(native.main())\n",
    )
    put(
        base,
        "to_prism/.venv/bin/prism",
        "# fixture preflight capability; external calls are intercepted\n",
    )
    # Preserve the registered uv argv, using a test-only launcher without installs/network.
    put(
        base,
        "bin/uv",
        "#!" + sys.executable + "\nimport os,sys\n"
        'assert sys.argv[1:3] == ["run", "python"]\n'
        "os.execv(sys.executable,[sys.executable,*sys.argv[3:]])\n",
        True,
    )
    put(
        base,
        "bin/codex",
        "#!" + sys.executable + '\nraise AssertionError("live provider forbidden")\n',
        True,
    )
    return root


def original():
    scope = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/prism_native_route_original.py.txt").read_text(),
        scope,
    )
    return scope["run_intent_match"]


def find_states(value):
    tokens = set()

    def walk(v):
        if isinstance(v, dict):
            if "session_id" in v:
                tokens.add(v["session_id"])
            for c in v.values():
                walk(c)
        elif isinstance(v, list):
            for c in v:
                walk(c)
        elif isinstance(v, str) and v.startswith("{") and "session_id" in v:
            try:
                walk(json.loads(v))
            except ValueError:
                pass

    walk(value)
    return tokens


class RouteTests(unittest.TestCase):
    maxDiff = None

    def test_authored_generator_identity_policy_and_provenance(self):
        spec = importlib.util.spec_from_file_location(
            "prism_route_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        d = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.prism_native_route_descriptor(), d)
        self.assertEqual(d["id"], "route_prism_native_semantic_parallel_e2e_workflow")
        self.assertEqual(d["aliases"], [ROUTE])
        self.assertEqual(d["lifecycle"], "active")
        self.assertEqual(
            d["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 31},
        )
        self.assertEqual(
            d["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertEqual(d["policy"]["resume"]["mode"], "none")
        for row in d["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertTrue(
            any(
                s["selector"] == "run_intent_match"
                and s["path"] == "scripts/mathformer.py"
                for s in d["provenance"]["sources"]
            )
        )
        self.assertEqual(
            set(d["operations"]),
            {"initialize", "validate_entry", "await_entry", "retain_state", "finalize"},
        )
        for op in d["operations"]:
            self.assertEqual(
                d["operations"][op]["execution"]["binding"]["target"], PREFIX + op
            )
        with self.assertRaisesRegex(ValueError, "registry"):
            bad = deepcopy(REGISTRY)
            bad[ACTION]["command"] = ["arbitrary"]
            checked_registry(bad)
        with self.assertRaisesRegex(ValueError, "route"):
            selected_match(
                {
                    "route": {"route_id": "forged", "action_ids": [ACTION]},
                    "score": 1,
                    "matched_terms": [],
                }
            )

    def test_native_timeout_capture_and_unexpected_launch_errors(self):
        # Only the process boundary is replaced here; timeout conversion/audit are real.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = replace(
                hub.build_registry()[ACTION],
                command=("fixture-prism-compiler",),
                required_paths=(),
                required_tools=(),
            )
            for timeout in [False, True]:
                calls = []

                def run(argv, **kwargs):
                    calls.append((argv, kwargs))
                    if timeout:
                        raise subprocess.TimeoutExpired(
                            argv, kwargs["timeout"], output="partial", stderr="deadline"
                        )
                    return subprocess.CompletedProcess(
                        argv, 7, "fixture output", "fixture reject"
                    )

                with patch.object(
                    hub,
                    "subprocess",
                    SimpleNamespace(
                        run=run,
                        PIPE=subprocess.PIPE,
                        TimeoutExpired=subprocess.TimeoutExpired,
                    ),
                ):
                    child = hub.run_leaf_action(
                        item,
                        hub.RunContext(allow_mutating=True),
                        (),
                        repository_root=root,
                    )
                self.assertFalse(child["ok"])
                self.assertTrue(child["write_audit"]["ok"])
                self.assertEqual(child["status"], "timeout" if timeout else "completed")
                self.assertEqual(child["returncode"], None if timeout else 7)
                self.assertEqual(calls[0][0], list(item.command))
                self.assertEqual(calls[0][1]["timeout"], 3600)
            with patch.object(
                hub.subprocess, "run", side_effect=OSError("launch error")
            ):
                process = StepProcess(item, {"argv": list(item.command)}, root)
                with self.assertRaisesRegex(OSError, "launch error"):
                    process.receive()
                with self.assertRaisesRegex(OSError, "launch error"):
                    process.close()

    def test_registered_route_lunar_prism_and_native_comparison(self):
        asyncio.run(self.scenario())

    def test_native_worker_bounds_and_report_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            root = fixture(Path(directory))
            output = root / "tests/fixture-report.json"
            boundary = CompilerProviderFixture(synchronize=False)
            with patch.object(native, "subprocess", SimpleNamespace(run=boundary.run)):
                session = native.VerificationSession(
                    root,
                    "fixture-compiler",
                    99,
                    output,
                    "codex",
                    {"control_validation_loop"},
                )
                try:
                    for i in range(14):
                        self.assertEqual(session.validate_entry(), i == 13)
                    session.prepare_runtime()
                    self.assertEqual(session.executor._max_workers, 4)
                    self.assertEqual(len(session.futures), 1)
                    self.assertTrue(session.await_entry())
                    session.finish_runtime()
                    self.assertIsNone(session.resources)
                    self.assertFalse(session.temporary.exists())
                    before = session.before
                    session.before = "changed"
                    with self.assertRaisesRegex(
                        native.VerificationError, "canonical semantic sources changed"
                    ):
                        session.write_report()
                    session.before = before
                    skills = session.skills_before
                    session.skills_before = "changed"
                    with self.assertRaisesRegex(
                        native.VerificationError, "canonical skill sources changed"
                    ):
                        session.write_report()
                    session.skills_before = skills
                    self.assertFalse(output.exists())
                    report = session.write_report()
                    self.assertEqual(report["workflow_count"], 1)
                    self.assertEqual(report["catalog_workflow_count"], 14)
                    self.assertEqual(report["jobs"], 1)
                    self.assertFalse(report["actual_run_overlap"])
                    output.unlink()
                    session.results = [
                        dict(session.results[0], run_started_ns=1, run_ended_ns=2),
                        dict(session.results[0], run_started_ns=2, run_ended_ns=3),
                    ]
                    with self.assertRaisesRegex(
                        native.VerificationError, "did not observe overlapping"
                    ):
                        session.write_report()
                    self.assertFalse(output.exists())
                finally:
                    session.close()

    async def scenario(self):
        # Every non-dry invocation targets this isolated tree. No production run,
        # credentials, theorem prover, or provider executable is reachable.
        with tempfile.TemporaryDirectory(prefix="prism-native-route-") as directory:
            base = Path(directory).resolve()
            root = populate(base)
            log = base / "boundary.jsonl"
            paths = [
                str(ROOT / "scripts"),
                str(ROOT / "tests/mcp"),
                str(ROOT / "tests/mcp/fixtures"),
                str(LUNAR / "app/backend"),
                str(LUNAR.parent / "abducer/abducer-prism/src"),
                *SITES,
            ]
            environment = {
                "PATH": str(base / "bin") + os.pathsep + os.environ["PATH"],
                "PYTHONPATH": os.pathsep.join(paths),
                "PYTHONDONTWRITEBYTECODE": "1",
                "LUNAR_PLATFORM_ROOT": str(LUNAR),
                "WORKFLOW_CONTRACT_PATH": str(CONTRACT),
                "PRISM_ROUTE_FIXTURE_LOG": str(log),
            }
            manager = SessionManager()
            failure = None
            server = 'from mcp_server import mcp;mcp.run(transport="stdio")'
            async with manager.open(
                "prism-route",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                environment,
            ) as remote:
                try:
                    await self.connected(remote, root, log, environment)
                except Exception as exc:
                    failure = exc
            self.assertFalse(manager.active)
            if failure:
                raise failure

    async def connected(self, remote, root, log, environment):
        d = yaml.safe_load(CONTRACT.read_text())
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(doc, inventory=tools):
            assets = snapshot(doc)
            record = workflow_documents([DESCRIPTOR], assets)[0]
            self.assertTrue(record["validation"]["valid"], record["validation"])
            compiled = compile_workflow("mcp:prism-route", record, inventory)
            return compiled, assets

        compiled, assets = compile(d)
        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
        self.assertEqual(compiled["runtime_status"], "ready")
        self.assertEqual(set(compiled["bindings"]), set(d["operations"]))
        self.assertTrue(compiled["runtime_source"])
        self.assertTrue(compiled["prism_source"])
        self.assertFalse(compile(d, [])[0]["runnable"])

        async def authorize():
            pass

        catalog = json.loads(
            (root / "mathformer-prism/workflow_catalog.json").read_text()
        )
        inputs = {
            "context": vars(hub.RunContext(allow_mutating=True)),
            "catalog": catalog,
            "registry": REGISTRY,
            "match": MATCH,
            "repository_root": str(root),
        }
        report = root / "mathformer-prism/tests/native-semantic-parallel-e2e.json"

        def reset():
            report.parent.mkdir(exist_ok=True)
            report.write_text("old fixture output\n")
            log.unlink(missing_ok=True)

        async def run(values=None, changed=None):
            c, a = compile(changed) if changed else (compiled, assets)
            self.assertTrue(c["runnable"], c["diagnostics"])
            return await execute(c, a, values or inputs, remote, authorize)

        def calls():
            return (
                [json.loads(s) for s in log.read_text().splitlines()]
                if log.exists()
                else []
            )

        def ops(result):
            return [c["operation"] for c in result["calls"]]

        async def close(result):
            tokens = find_states(result.get("replay_artifacts", {}))
            self.assertTrue(tokens)
            for token in tokens:
                self.assertTrue(
                    (
                        await remote.call(
                            PREFIX + "close", {"state": {"session_id": token}}
                        )
                    )["closed"]
                )

        # Native entrypoint vs compiled graph: exact argv, output, audit and route metadata.
        reset()
        result = await run()
        self.assertEqual(result["status"], "accepted", result)
        child = result["outputs"]["result"]["children"][0]
        self.assertTrue(child["ok"], child)
        self.assertEqual(ops(result), EXPECTED)
        self.assertEqual(len(result["calls"]), 30)
        self.assertEqual(
            [c["tool"] for c in result["calls"]], [PREFIX + s for s in EXPECTED]
        )
        self.assertEqual(len(calls()), 56)
        self.assertTrue(all(r["timeout"] is None for r in calls()))
        self.assertTrue(result["runtime"]["effect_records"])
        self.assertTrue(result["replay_artifacts"])
        observed = json.loads(report.read_text())
        self.assertEqual(observed["workflow_count"], 14)
        self.assertEqual(observed["jobs"], 4)
        self.assertTrue(observed["actual_run_overlap"])
        self.assertTrue(observed["source_unchanged"])
        self.assertEqual(len(observed["negative_controls"]), 4)
        self.assertEqual(child["write_audit"]["unexpected_paths"], [])
        self.assertEqual(child["argv"], list(hub.build_registry()[ACTION].command))
        reset()
        with patch.dict(os.environ, environment):
            expected = original()(
                selected_match(MATCH),
                checked_registry(REGISTRY),
                hub.RunContext(**inputs["context"]),
                repository_root=root,
            )
        self.assertEqual(result["outputs"], {"result": expected})
        self.assertEqual(stable(observed), stable(json.loads(report.read_text())))

        # Preflight, mutation denial, dry-run and unknown admission preserve early returns.
        for kind in ["dry", "deny", "missing_path", "missing_registry"]:
            reset()
            values = deepcopy(inputs)
            if kind == "dry":
                values["context"]["dry_run"] = True
            if kind == "deny":
                values["context"]["allow_mutating"] = False
            if kind == "missing_registry":
                values["registry"] = {}
            required = root / "scripts/prism/reviewed_reasoning_projections.json"
            original_text = required.read_text()
            if kind == "missing_path":
                required.unlink()
            for keep in [False, True]:
                values["context"]["keep_going"] = keep
                actual = await run(values)
                if kind == "missing_registry":
                    self.assertEqual(actual["status"], "failed")
                    self.assertEqual(
                        ops(actual),
                        ["initialize", "retain_state", "retain_state", "finalize"],
                    )
                    with self.assertRaises(KeyError):
                        original()(
                            selected_match(MATCH),
                            {},
                            hub.RunContext(**values["context"]),
                            repository_root=root,
                        )
                    self.assertFalse(calls())
                    continue
                self.assertEqual(actual["status"], "accepted", actual)
                with patch.dict(os.environ, environment):
                    oracle = original()(
                        selected_match(MATCH),
                        checked_registry(values["registry"]),
                        hub.RunContext(**values["context"]),
                        repository_root=root,
                    )
                self.assertEqual(actual["outputs"], {"result": oracle})
                self.assertEqual(len(oracle["children"]), 1)
                self.assertEqual(
                    ops(actual),
                    ["initialize", "retain_state", "retain_state", "finalize"],
                )
                self.assertFalse(calls())
            if kind == "missing_path":
                required.write_text(original_text)

        # Static failure stops immediately; no runtime calls, route failure as data.
        taxonomy = (
            root / "mathformer-prism" / catalog["workflows"][2]["semantic_taxonomy"]
        )
        before = taxonomy.read_text()
        bad = json.loads(before)
        bad["review_status"] = "pending"
        taxonomy.write_text(json.dumps(bad))
        reset()
        actual = await run()
        self.assertEqual(actual["status"], "accepted", actual)
        self.assertFalse(actual["outputs"]["result"]["ok"])
        self.assertEqual(
            ops(actual),
            ["initialize"] + ["validate_entry"] * 3 + ["retain_state", "finalize"],
        )
        self.assertFalse(calls())
        self.assertEqual(report.read_text(), "old fixture output\n")
        self.assertIn(
            "taxonomy not approved",
            actual["outputs"]["result"]["children"][0]["stderr"],
        )
        taxonomy.write_text(before)

        # Runtime failures are collected through every submitted future, then joined.
        mode = root / "mathformer-prism/boundary-mode.json"
        for failure in [
            {"run_fail": "control_validation_loop"},
            {"offline_fail": True},
            {"duplicate_calls": True},
            {"promote": True},
        ]:
            mode.write_text(json.dumps(failure))
            reset()
            actual = await run()
            self.assertEqual(actual["status"], "accepted", actual)
            self.assertFalse(actual["outputs"]["result"]["ok"])
            self.assertEqual(ops(actual), EXPECTED)
            self.assertEqual(
                actual["outputs"]["result"]["children"][0]["returncode"], 1
            )
            self.assertEqual(
                sum(r["argv"][1:3] == ["run", "main.prism"] for r in calls()), 14
            )
            self.assertEqual(report.read_text(), "old fixture output\n")
            self.assertTrue(
                all(
                    not Path(r["argv"][-1]).parent.exists()
                    for r in calls()
                    if r["argv"][1] == "run"
                )
            )
        mode.unlink()

        # Initialization errors become native subprocess failure and still audit.
        catalog_path = root / "mathformer-prism/workflow_catalog.json"
        bad = deepcopy(catalog)
        bad["source_fingerprint"] = "sha256:stale"
        catalog_path.write_text(json.dumps(bad))
        values = deepcopy(inputs)
        values["catalog"] = bad
        reset()
        actual = await run(values)
        self.assertEqual(actual["status"], "accepted", actual)
        self.assertEqual(
            ops(actual), ["initialize", "retain_state", "retain_state", "finalize"]
        )
        self.assertFalse(actual["outputs"]["result"]["ok"])
        self.assertFalse(calls())
        self.assertIn(
            "fingerprint is stale", actual["outputs"]["result"]["children"][0]["stderr"]
        )
        catalog_path.write_text(json.dumps(catalog))

        # Graph exhaustion never promotes or writes a success report. Explicit close
        # performs source finally/join and native audit for host-side interruption.
        for index in [1, 2]:
            reset()
            changed = deepcopy(d)
            changed["flow"]["steps"][index]["max_iterations"] = 13
            exhausted = await run(changed=changed)
            self.assertEqual(exhausted["status"], "failed", exhausted)
            self.assertIsNone(exhausted["outputs"])
            self.assertIn("exhaust", str(exhausted).lower())
            self.assertEqual(report.read_text(), "old fixture output\n")
            await close(exhausted)
            if index == 2:
                self.assertEqual(
                    sum(r["argv"][1:3] == ["run", "main.prism"] for r in calls()), 14
                )
        reset()
        changed = deepcopy(d)
        changed["policy"]["limits"]["max_operation_calls"] = 3
        failed = await run(changed=changed)
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(
            sum(bool(c.get("transport_call_performed")) for c in failed["calls"]), 3
        )
        await close(failed)

        # Exact state and native arguments protect the registered capability.
        reset()
        initialized = (await remote.call(PREFIX + "initialize", inputs))["state"]
        updated = (
            await remote.call(PREFIX + "validate_entry", {"state": initialized})
        )["state"]
        self.assertEqual(updated["cursor"], 1)
        with self.assertRaises(Exception):
            await remote.call(PREFIX + "validate_entry", {"state": initialized})
        with self.assertRaises(Exception):
            await remote.call(PREFIX + "await_entry", {"state": updated})
        await remote.call(PREFIX + "close", {"state": updated})
        values = deepcopy(inputs)
        values["catalog"]["workflow_count"] = 13
        failed = await run(values)
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(ops(failed), ["initialize"])
        self.assertFalse(calls())
        values = deepcopy(inputs)
        values["registry"][ACTION]["timeout_seconds"] = 1
        failed = await run(values)
        self.assertEqual(failed["status"], "failed")
        self.assertFalse(calls())


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    outcome = program.result
    raise SystemExit(
        0 if outcome.wasSuccessful() and outcome.testsRun > len(outcome.skipped) else 1
    )
