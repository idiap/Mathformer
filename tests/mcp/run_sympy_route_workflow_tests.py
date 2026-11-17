#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline native-source, MCP, binding and real Lunar/PRISM integration tests."""

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

import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import json
import re
import tempfile
from types import SimpleNamespace
import unittest
import yaml
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
import mathformer as hub
from sympy_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
    register_sympy_route_tools,
)
from sympy_route_boundary import populate, install, SCRIPT, OUTPUT
from sympy_controlled_suite_tools import source

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
BASE = "skills/control/workflow-contract-validator/"
DESCRIPTOR = (
    BASE
    + "references/normalized-workflows/route/route_formalize_sympy_workflow/workflow.yaml"
)
SCHEMA = BASE + "references/normalized-workflows/hub-interface.schema.json"
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 23,
    "matched_terms": ["sympy", "identity"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "dispatch", "advance", "finish"]
STAGES = [
    "parse",
    "assumptions",
    "grounding",
    "draft",
    "execute",
    "identity",
    "counterexamples",
    "trace",
    "consistency",
]


def original():
    scope = dict(vars(hub))
    exec((ROOT / "tests/mcp/fixtures/sympy_route_original.py.txt").read_text(), scope)
    return SimpleNamespace(**scope)


def stable(value):
    if isinstance(value, dict):
        return {
            k: stable(v)
            for k, v in value.items()
            if k not in ("duration_ms", "generated_at")
        }
    if isinstance(value, list):
        return [stable(v) for v in value]
    if isinstance(value, str):
        try:
            return stable(json.loads(value))
        except (ValueError, TypeError):
            # run() retains only the final 4000 characters, so a stage's
            # timestamp can also occur in a deliberately truncated JSON tail.
            return re.sub(r'("generated_at"\s*:\s*")[^"]*"', r'\1<TIME>"', value)
    return value


def differences(left, right, path="result"):
    if (
        isinstance(left, dict)
        and isinstance(right, dict)
        and left.keys() == right.keys()
    ):
        return [
            row
            for key in left
            for row in differences(left[key], right[key], path + "." + key)
        ]
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        return [
            row
            for i, (a, b) in enumerate(zip(left, right))
            for row in differences(a, b, f"{path}[{i}]")
        ]
    return [] if left == right else [(path, repr(left)[:180], repr(right)[:180])]


def snapshot(doc):
    texts = {
        r["path"]: (ROOT / r["path"]).read_text() for r in doc["provenance"]["sources"]
    }
    texts.update({DESCRIPTOR: json.dumps(doc), SCHEMA: (ROOT / SCHEMA).read_text()})
    return [
        dict(
            path=p,
            content=t,
            encoding="text",
            sha256=hashlib.sha256(t.encode()).hexdigest(),
        )
        for p, t in texts.items()
    ]


def commands(root):
    path = root / "artifacts/sympy/commands.jsonl"
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


class Observed:
    def __init__(self, remote):
        self.remote, self.events = remote, []

    async def tools(self):
        return await self.remote.tools()

    async def call(self, name, args):
        result = await self.remote.call(name, args)
        self.events.append((name, deepcopy(args), deepcopy(result)))
        return result


class SympyRouteTests(unittest.TestCase):
    maxDiff = None

    def test_contract_generator_and_native_identity(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        spec = importlib.util.spec_from_file_location(
            "sympy_route_normalizer", ROOT / BASE / "scripts/normalize_workflows.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.sympy_route_descriptor(), doc)
        self.assertEqual(
            doc,
            json.loads(
                (ROOT / BASE / "references/sympy-route.workflow.json").read_text()
            ),
        )
        self.assertEqual(doc["id"], "route_formalize_sympy_workflow")
        self.assertEqual(doc["aliases"], [ROUTE])
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(doc["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertEqual(doc["policy"]["resume"]["mode"], "none")
        self.assertTrue(
            any(
                r["path"] == "scripts/mathformer.py"
                and r["selector"] == "run_intent_match"
                for r in doc["provenance"]["sources"]
            )
        )
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        item = checked_registry(REGISTRY)[ACTION]
        self.assertEqual(item.depends_on, ())
        self.assertIsNone(item.timeout_seconds)
        self.assertEqual(list(item.command)[1:], [SCRIPT, "--json"])
        self.assertEqual(selected_match(MATCH).route.action_ids, (ACTION,))

    def test_native_state_stop_and_each_case_failure_boundary(self):
        for keep in (False, True):
            for child in ({"ok": True}, {"ok": False}):
                initial = hub.initialize_intent_state()
                advanced, done = hub.advance_intent_state(
                    initial, child, hub.RunContext(keep_going=keep), 1
                )
                self.assertEqual(initial, {"ok": True, "children": []})
                self.assertEqual(advanced, {"ok": child["ok"], "children": [child]})
                self.assertTrue(done)
                with self.assertRaisesRegex(ValueError, "bounds"):
                    check_state(advanced, selecting=True)
        state, _ = hub.advance_intent_state(
            {"ok": False, "children": [{"ok": False}]},
            {"ok": True},
            hub.RunContext(keep_going=True),
            2,
        )
        self.assertFalse(state["ok"])
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            saved = hub.subprocess
            try:
                install(hub, base)
                # All earlier source stages are real. Only the targeted Python
                # command boundary fails. Later stages of that case cannot run.
                for i, stage in enumerate(STAGES):
                    root = populate(
                        base / stage,
                        ROOT,
                        {
                            "stage": stage,
                            "case": "sum_first_odd_numbers",
                            "fault": "nonzero",
                        },
                    )
                    native = source()
                    token = native.WORKING_DIRECTORY.set(root)
                    try:
                        report = (
                            native.run_case(
                                native.SOURCES[0], root / "index.json", root / "out"
                            )
                            if i < 2
                            else None
                        )
                    finally:
                        native.WORKING_DIRECTORY.reset(token)
                    if i < 2:
                        self.assertFalse(report["ok"])
                        self.assertEqual(
                            [r["id"].split(".")[-1] for r in report["results"]],
                            STAGES[: i + 1],
                        )
                    else:
                        # Native preflight supplies the real API index before
                        # this case; the suite still visits subsequent cases.
                        result = hub.run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            hub.RunContext(),
                            repository_root=root,
                        )
                        suite = json.loads(result["children"][0]["stdout"])
                        self.assertFalse(result["ok"])
                        self.assertEqual(len(suite["cases"]), 5)
                        self.assertEqual(
                            [
                                r["id"].split(".")[-1]
                                for r in suite["cases"][0]["results"]
                            ],
                            STAGES[: i + 1],
                        )
                        self.assertTrue(all(c["ok"] for c in suite["cases"][1:]))
            finally:
                hub.subprocess = saved

    def test_service_policy(self):
        async def scenario():
            permissions = {"allowed": False, "path": True}

            def authorize():
                if not permissions["allowed"]:
                    raise PermissionError("service read-only")

            server = FastMCP("sympy-policy")
            register_sympy_route_tools(
                server, authorize, lambda path: permissions["path"]
            )
            with tempfile.TemporaryDirectory() as tmp:
                args = dict(
                    action_id=ACTION,
                    registry=REGISTRY,
                    context=vars(hub.RunContext()),
                    repository_root=tmp,
                )
                for allow, path, message in [
                    (False, True, "read-only"),
                    (True, False, "service roots"),
                ]:
                    permissions.update(allowed=allow, path=path)
                    with self.assertRaisesRegex(Exception, message):
                        await server.call_tool("mathformer_sympy_route_dispatch", args)
                args["context"]["dry_run"] = True
                result = await server.call_tool("mathformer_sympy_route_dispatch", args)
                self.assertIn("preflight_errors", str(result))

        asyncio.run(scenario())

    def test_registered_mcp_real_lunar_prism_runtime(self):
        with tempfile.TemporaryDirectory(prefix="sympy-route-") as tmp:
            asyncio.run(self.scenario(Path(tmp).resolve()))

    async def scenario(self, base):
        doc = yaml.safe_load(CONTRACT.read_text())
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
            + ";from sympy_route_boundary import serve;serve("
            + repr(str(base))
            + ")"
        )
        manager = SessionManager()
        async with manager.open(
            "sympy-route",
            StdioConfig(
                command=sys.executable,
                args=["-c", server],
                cwd=str(ROOT),
                timeout_seconds=600,
            ),
            {"PYTHONDONTWRITEBYTECODE": "1"},
        ) as remote:
            failure = None
            try:
                await self.checks(base, remote, doc)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure

    async def checks(self, base, remote, doc):
        inventory = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(document, tools=None):
            assets = snapshot(document)
            parsed = workflow_documents([DESCRIPTOR], assets)[0]
            self.assertTrue(parsed["validation"]["valid"], parsed)
            return (
                compile_workflow(
                    "mcp:sympy-route", parsed, inventory if tools is None else tools
                ),
                assets,
            )

        graph, assets = compile(doc)
        self.assertTrue(graph["runnable"], graph["diagnostics"])
        self.assertEqual(graph["runtime_status"], "ready")
        self.assertTrue(graph["runtime_source"])
        self.assertTrue(graph["prism_source"])
        self.assertEqual(set(graph["bindings"]), set(ORDER))
        for op in doc["operations"].values():
            name = op["execution"]["binding"]["target"]
            self.assertFalse(
                compile(doc, [t for t in inventory if t["name"] != name])[0]["runnable"]
            )

        async def authorize():
            pass

        async def run(root, *, dry=False, keep=False, document=None, mutations=None):
            compiled, received = compile(document) if document else (graph, assets)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            inputs = dict(
                context=vars(hub.RunContext(dry_run=dry, keep_going=keep)),
                match=deepcopy(MATCH),
                registry=deepcopy(REGISTRY),
                repository_root=str(root) if root is not None else None,
            )
            if mutations:
                mutations(inputs)
            observed = Observed(remote)
            result = await execute(compiled, received, inputs, observed, authorize)
            return result, inputs, observed.events

        for keep in (False, True):
            root = base / f"missing-{keep}"
            root.mkdir()
            result, inputs, events = await run(root, keep=keep)
            expected = original().run_intent_match(
                selected_match(MATCH),
                checked_registry(REGISTRY),
                hub.RunContext(**inputs["context"]),
                repository_root=root,
            )
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(result["outputs"], {"result": expected})
            self.assertFalse(expected["ok"])
            self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
        root = populate(base / "dry", ROOT)
        result, inputs, events = await run(root, dry=True)
        self.assertEqual(
            result["outputs"],
            {
                "result": original().run_intent_match(
                    selected_match(MATCH),
                    checked_registry(REGISTRY),
                    hub.RunContext(**inputs["context"]),
                    repository_root=root,
                )
            },
        )
        self.assertFalse((root / OUTPUT).exists())
        root = populate(base / "complete", ROOT)
        result, inputs, events = await run(root)
        self.assertEqual(result["status"], "accepted", result)
        output = result["outputs"]["result"]
        self.assertTrue(output["ok"], output)
        self.assertEqual(output["route"]["score"], MATCH["score"])
        self.assertEqual(output["route"]["matched_terms"], MATCH["matched_terms"])
        self.assertEqual(len(output["children"]), 1)
        child = output["children"][0]
        self.assertTrue(child["write_audit"]["ok"])
        suite = json.loads(child["stdout"])
        self.assertEqual(
            suite, json.loads((root / OUTPUT / "suite_report.json").read_text())
        )
        self.assertTrue((root / OUTPUT / "index.html").is_file())
        self.assertEqual([Path(c["source"]) for c in suite["cases"]], source().SOURCES)
        self.assertTrue(all(c["ok"] for c in suite["cases"]))
        self.assertEqual(
            [r["id"] for r in suite["preflight"]], ["dependency_probe", "api_index"]
        )
        self.assertEqual(len(commands(root)), 47)
        self.assertTrue(all(r["timeout"] == 180 for r in commands(root)))
        for case in suite["cases"]:
            self.assertEqual([r["id"].split(".")[-1] for r in case["results"]], STAGES)
            counter = next(
                r for r in case["results"] if r["id"].endswith(".counterexamples")
            )
            self.assertEqual(counter["cmd"][counter["cmd"].index("--max-n") + 1], "100")
        self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
        self.assertEqual(events[0][2], {"state": {"ok": True, "children": []}})
        self.assertEqual(events[1][2], {"action_id": ACTION})
        self.assertEqual(
            events[3][2], {"state": {"ok": True, "children": [child]}, "done": True}
        )
        self.assertTrue(result["runtime"]["effect_records"])
        self.assertTrue(result["runtime"]["provenance"])
        self.assertTrue(result["replay_artifacts"])
        # Compare the frozen authoritative route over the identical source
        # suite and Python boundary, excluding measured times only.
        expected = await remote.call("fixture_sympy_route_original", inputs)
        repeated, _, _ = await run(root)
        self.assertEqual(
            differences(stable(repeated["outputs"]["result"]), stable(expected)), []
        )
        for stage in ("dependency_probe", "api_index"):
            root = populate(base / stage, ROOT, {"stage": stage, "fault": "nonzero"})
            result, _, _ = await run(root, keep=True)
            self.assertEqual(result["status"], "accepted", result)
            child = result["outputs"]["result"]["children"][0]
            self.assertFalse(child["ok"])
            report = json.loads(child["stdout"])
            self.assertFalse(report["ok"])
            self.assertNotIn("cases", report)
            self.assertEqual(
                len(report["results"]), 1 if stage == "dependency_probe" else 2
            )
            self.assertFalse((root / OUTPUT / "index.html").exists())
        for fault in ("nonzero", "timeout", "launch"):
            root = populate(
                base / fault,
                ROOT,
                {"stage": "identity", "case": "sum_first_odd_numbers", "fault": fault},
            )
            result, _, _ = await run(root, keep=True)
            self.assertEqual(result["status"], "accepted", result)
            output = result["outputs"]["result"]
            self.assertFalse(output["ok"])
            child = output["children"][0]
            self.assertEqual(child["returncode"], 1)
            rows = commands(root)
            self.assertEqual(
                [r["stage"] for r in rows[:8]],
                ["dependency_probe", "api_index"] + STAGES[:6],
            )
            if fault == "nonzero":
                report = json.loads(child["stdout"])
                self.assertEqual(len(report["cases"]), 5)
                self.assertTrue(all(c["ok"] for c in report["cases"][1:]))
                self.assertEqual(len(report["cases"][0]["results"]), 6)
                self.assertEqual(len(report["cases"][0]["results"][-1]["stdout"]), 4000)
            else:
                self.assertEqual(len(rows), 8)
                self.assertIn("Traceback", child["stderr"])
                self.assertFalse((root / OUTPUT / "suite_report.json").exists())
        for outer in ("launch", "write"):
            root = populate(base / ("outer-" + outer), ROOT, {"outer": outer})
            result, _, _ = await run(root)
            if outer == "launch":
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:3])
            else:
                self.assertEqual(result["status"], "accepted", result)
                child = result["outputs"]["result"]["children"][0]
                self.assertFalse(child["ok"])
                self.assertEqual(child["status"], "undeclared_writes")
                self.assertEqual(
                    child["write_audit"]["unexpected_paths"], ["unexpected.txt"]
                )
                self.assertTrue(json.loads(child["stdout"])["ok"])
        root = populate(base / "bounds", ROOT)
        for limit in (1, 3, 4):
            changed = deepcopy(doc)
            changed["policy"]["limits"]["max_operation_calls"] = limit
            result, _, _ = await run(root, dry=True, document=changed)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]),
                limit,
            )
        changed = deepcopy(doc)
        changed["flow"]["steps"][1]["until"] = {"literal": False}
        result, _, _ = await run(root, dry=True, document=changed)
        self.assertEqual(result["status"], "failed", result)
        self.assertEqual(result["failure_disposition"], "fail")
        self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:-1])
        timed = deepcopy(doc)
        timed["policy"]["limits"]["wall_time_seconds"] = 1
        timed_graph, timed_assets = compile(timed)

        async def waiting_authority():
            await asyncio.Event().wait()

        with self.assertRaises(TimeoutError):
            await execute(timed_graph, timed_assets, inputs, remote, waiting_authority)
        for name in ("registry", "match"):

            def forge(inputs):
                if name == "registry":
                    inputs["registry"][ACTION]["command"] = ["unregistered-program"]
                else:
                    inputs["match"]["route"]["title"] = "forged"

            result, _, _ = await run(root, dry=True, mutations=forge)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
        result, _, _ = await run(None, dry=True)
        self.assertEqual(
            result["outputs"],
            {
                "result": hub.run_intent_match(
                    selected_match(MATCH),
                    checked_registry(REGISTRY),
                    hub.RunContext(dry_run=True),
                )
            },
        )


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
