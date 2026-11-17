#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native route + MCP + real Lunar/PRISM; only external boundaries substituted.

The real inventory child runs solely in temporary repositories. Its metadata
provider is deterministic. Separate external compiler fixtures exercise timeout,
capture, write audit and launch failure without changing production bindings.
"""

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
PROVIDER = FIXTURES / "licenses_metadata"
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(FIXTURES),
    str(PROVIDER),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
import generate_python_license_inventory as leaf
from licenses_inventory_route_tools import (
    ACTION,
    ROUTE,
    checked_registry,
    selected_match,
    check_state,
)
from licenses_metadata_provider import provider
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.client import MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_licenses_inventory_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {"route_id": ROUTE, "score": 29, "matched_terms": ["license", "inventory"]}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select_action", "run_action", "advance", "finish"]
OUTPUT = "docs/operations/PYTHON_DEPENDENCY_LICENSES.md"


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "licenses_inventory_route_original.py.txt").read_text(), scope)
    return SimpleNamespace(**scope)


def snapshot(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=path,
            content=content,
            encoding="text",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
        )
        for path, content in values.items()
    ]


def populate(root):
    (root / "scripts").mkdir(exist_ok=True)
    shutil.copyfile(
        ROOT / "scripts/generate_python_license_inventory.py",
        root / "scripts/generate_python_license_inventory.py",
    )


class LicensesRouteTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="licenses-route-")
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name).resolve()
        self.root = self.directory / "repository"
        self.root.mkdir()
        self.fixture = self.directory / "metadata.json"
        self.config = {
            "packages": [
                {
                    "fields": [
                        ("Name", "zeta|x"),
                        ("Version", "1"),
                        ("License-Expression", "MIT"),
                        ("License", "ignored"),
                        ("Project-URL", "source, https://source"),
                        ("Project-URL", "Homepage, https://home"),
                    ]
                },
                {
                    "fallback": "Alpha",
                    "fields": [
                        ("Version", "2"),
                        ("License", "L" * 90),
                        ("Classifier", "License :: MIT"),
                        ("Classifier", "License :: MIT"),
                        ("Classifier", "License :: BSD"),
                        ("Home-page", " https://fallback "),
                    ],
                },
                {
                    "fields": [
                        ("Name", "beta"),
                        ("License", "short"),
                        ("Classifier", "License :: ignored"),
                        ("Project-URL", "other, https://other"),
                    ]
                },
                {"fields": [("Name", "empty")]},
            ]
        }
        self.save()
        self.environment = {
            "PYTHONPATH": os.pathsep.join([str(PROVIDER), *SITES]),
            "PYTHONDONTWRITEBYTECODE": "1",
            "LICENSES_METADATA_FIXTURE": str(self.fixture),
        }

    def save(self):
        self.fixture.write_text(json.dumps(self.config))

    def expected_content(self):
        with patch.object(
            leaf.metadata, "distributions", lambda: provider(self.fixture)
        ):
            return leaf.render(leaf.package_rows())

    def test_identity_generator_binding_and_provenance(self):
        spec = importlib.util.spec_from_file_location(
            "licenses_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(normalizer.licenses_inventory_route_descriptor(), document)
        self.assertEqual(document["id"], "route_licenses_inventory_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            document["policy"]["effects"]["filesystem"]["write"], ["docs/"]
        )
        self.assertEqual(document["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertTrue(
            any(
                s["path"] == "scripts/mathformer.py"
                and s["selector"] == "run_intent_match"
                for s in document["provenance"]["sources"]
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        item = checked_registry(REGISTRY)[ACTION]
        self.assertEqual(
            item.command, ("{python}", "scripts/generate_python_license_inventory.py")
        )
        self.assertEqual(item.depends_on, ())
        self.assertIsNone(item.timeout_seconds)

    def test_original_controller_equivalence_and_state(self):
        match, registry = selected_match(MATCH), checked_registry(REGISTRY)
        with patch.dict(os.environ, self.environment):
            for ready in [False, True]:
                if ready:
                    populate(self.root)
                for dry in [False, True]:
                    for allow in [False, True]:
                        for keep in [False, True]:
                            context = hub.RunContext(
                                dry_run=dry, allow_mutating=allow, keep_going=keep
                            )
                            expected = original().run_intent_match(
                                match, registry, context, repository_root=self.root
                            )
                            actual = hub.run_intent_match(
                                match, registry, context, repository_root=self.root
                            )
                            self.assertEqual(actual, expected)
                            self.assertEqual(len(actual["children"]), 1)
                            self.assertEqual(actual["ok"], ready and (dry or allow))
        for keep in [False, True]:
            for child in [{"ok": True}, {"ok": False}, {}]:
                state = hub.initialize_intent_state()
                updated, done = hub.advance_intent_state(
                    state, child, hub.RunContext(keep_going=keep), 1
                )
                self.assertEqual(state, {"ok": True, "children": []})
                self.assertEqual(
                    updated, {"ok": bool(child.get("ok", False)), "children": [child]}
                )
                self.assertTrue(done)
                check_state(updated)
                with self.assertRaises(ValueError):
                    check_state(updated, selecting=True)
            state, done = hub.advance_intent_state(
                hub.initialize_intent_state(),
                {"ok": False},
                hub.RunContext(keep_going=keep),
                2,
            )
            self.assertEqual(done, not keep)
            state, done = hub.advance_intent_state(
                state, {"ok": True}, hub.RunContext(keep_going=keep), 2
            )
            self.assertFalse(state["ok"])
            self.assertTrue(done)

    def test_metadata_decisions_and_exhaustion(self):
        with patch.object(
            leaf.metadata, "distributions", lambda: provider(self.fixture)
        ):
            rows = leaf.package_rows()
        self.assertEqual(
            rows,
            [
                ("Alpha", "2", "MIT, BSD", "https://fallback"),
                ("beta", "", "short", "https://other"),
                ("empty", "", "UNKNOWN", ""),
                ("zeta|x", "1", "MIT", "https://home"),
            ],
        )
        self.assertIn("zeta\\|x", leaf.render(rows))
        from email.message import Message

        for label in leaf.PREFERRED_URL_LABELS:
            meta = Message()
            for value in [
                "other, fallback",
                label.upper() + ", winner",
                label + ", loser",
            ]:
                meta["Project-URL"] = value
            self.assertEqual(leaf.project_url(meta), "winner")
        self.assertEqual(
            self.fixture.with_suffix(".calls").read_text().splitlines(),
            ["begin", *(["yield"] * 4), "exhausted"],
        )

    def test_external_compiler_capture_failure_timeout_and_audit(self):
        saved = hub.subprocess
        try:
            for mode in ["success", "reject", "write", "timeout", "launch_error"]:
                item = replace(
                    hub.build_registry()[ACTION],
                    command=("fixture-reasoning-compiler", mode),
                    required_paths=(),
                    timeout_seconds=3 if mode == "timeout" else None,
                )
                calls = install(hub, self.root)
                if mode == "launch_error":
                    with self.assertRaisesRegex(OSError, "compiler launch failed"):
                        hub.run_action(
                            ACTION,
                            {ACTION: item},
                            hub.RunContext(allow_mutating=True),
                            repository_root=self.root,
                        )
                else:
                    child = hub.run_action(
                        ACTION,
                        {ACTION: item},
                        hub.RunContext(allow_mutating=True),
                        repository_root=self.root,
                    )
                    self.assertEqual(child["ok"], mode == "success")
                    self.assertEqual(
                        child["status"],
                        {"write": "undeclared_writes", "timeout": "timeout"}.get(
                            mode, "completed"
                        ),
                    )
                    if mode == "reject":
                        self.assertEqual(child["returncode"], 7)
                    if mode == "write":
                        self.assertEqual(
                            child["write_audit"]["unexpected_paths"], ["undeclared.txt"]
                        )
                    if mode == "timeout":
                        self.assertEqual(
                            (child["returncode"], child["stdout"], child["stderr"]),
                            (None, "partial", "deadline"),
                        )
                self.assertEqual(
                    calls,
                    [{"argv": list(item.command), "timeout": item.timeout_seconds}],
                )
                (self.root / "undeclared.txt").unlink(missing_ok=True)
        finally:
            hub.subprocess = saved

    def test_registered_mcp_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "licenses-route",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            self.environment,
        ) as remote:
            try:
                await self.connected(remote)
            except Exception:
                import traceback

                traceback.print_exc()
                raise
        self.assertFalse(manager.active)
        readonly = server.replace(
            'mcp.run(transport="stdio")',
            'import mcp_server;mcp_server._READONLY=True;mcp.run(transport="stdio")',
        )
        async with manager.open(
            "readonly-licenses",
            StdioConfig(command=sys.executable, args=["-c", readonly], cwd=str(ROOT)),
            self.environment,
        ) as remote:
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    "mathformer_licenses_route_run",
                    {
                        "action": ACTION,
                        "registry": REGISTRY,
                        "context": vars(hub.RunContext(allow_mutating=True)),
                        "repository_root": str(self.root),
                    },
                )
            dry = await remote.call(
                "mathformer_licenses_route_run",
                {
                    "action": ACTION,
                    "registry": REGISTRY,
                    "context": vars(hub.RunContext(dry_run=True)),
                    "repository_root": str(self.root),
                },
            )
            self.assertEqual(dry["child"]["status"], "dry_run")
        self.assertFalse(manager.active)
        restricted = server.replace(
            'mcp.run(transport="stdio")',
            'import mcp_server;from pathlib import Path;mcp_server._ALLOWED_WRITE_ROOTS=[Path("/nonexistent-test-write-mount")];mcp.run(transport="stdio")',
        )
        async with manager.open(
            "restricted-licenses",
            StdioConfig(command=sys.executable, args=["-c", restricted], cwd=str(ROOT)),
            self.environment,
        ) as remote:
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    "mathformer_licenses_route_run",
                    {
                        "action": ACTION,
                        "registry": REGISTRY,
                        "context": vars(hub.RunContext(allow_mutating=True)),
                        "repository_root": str(self.root),
                    },
                )
        self.assertFalse(manager.active)

    async def connected(self, remote):
        document = yaml.safe_load(CONTRACT.read_text())
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(doc, inventory=tools):
            assets = snapshot(doc)
            workflow = workflow_documents([DESCRIPTOR], assets)[0]
            self.assertTrue(workflow["validation"]["valid"], workflow)
            compiled = compile_workflow("mcp:licenses-route", workflow, inventory)
            return compiled, assets

        compiled, assets = compile(document)
        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
        self.assertEqual(compiled["runtime_status"], "ready")
        self.assertTrue(compiled["prism_source"])
        self.assertTrue(compiled["runtime_source"])
        self.assertEqual(set(compiled["bindings"]), set(ORDER))
        self.assertFalse(
            compile(
                document,
                [t for t in tools if t["name"] != "mathformer_licenses_route_run"],
            )[0]["runnable"]
        )

        async def authorize():
            pass

        async def run(inputs, changed=None):
            c, a = compile(changed) if changed else (compiled, assets)
            return await execute(c, a, inputs, remote, authorize)

        base = {
            "context": vars(hub.RunContext()),
            "match": MATCH,
            "registry": REGISTRY,
            "repository_root": str(self.root),
        }
        for ready in [False, True]:
            if ready:
                populate(self.root)
            for dry in [False, True]:
                for allow in [False, True]:
                    for keep in [False, True]:
                        inputs = deepcopy(base)
                        inputs["context"].update(
                            dry_run=dry, allow_mutating=allow, keep_going=keep
                        )
                        result = await run(inputs)
                        self.assertEqual(result["status"], "accepted", result)
                        with patch.dict(os.environ, self.environment):
                            expected = original().run_intent_match(
                                selected_match(MATCH),
                                checked_registry(REGISTRY),
                                hub.RunContext(**inputs["context"]),
                                repository_root=self.root,
                            )
                        self.assertEqual(result["outputs"], {"result": expected})
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], ORDER
                        )
                        self.assertEqual(len(expected["children"]), 1)
                        self.assertEqual(expected["route"]["score"], MATCH["score"])
                        self.assertEqual(
                            expected["route"]["matched_terms"], MATCH["matched_terms"]
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
        inputs = deepcopy(base)
        inputs["context"]["allow_mutating"] = True
        expected = self.expected_content()
        (self.root / OUTPUT).write_text("stale")
        result = await run(inputs)
        child = result["outputs"]["result"]["children"][0]
        self.assertEqual((self.root / OUTPUT).read_text(), expected)
        self.assertEqual(
            child["argv"],
            [sys.executable, "scripts/generate_python_license_inventory.py"],
        )
        self.assertEqual(child["stdout"], "wrote " + OUTPUT + "\n")
        self.assertEqual(child["write_audit"]["unexpected_paths"], [])
        # Empty and large providers reach exhaustion without cap or retry.
        for count in [0, 1201]:
            self.config = {
                "packages": [{"fields": [("Name", f"p{i}")]} for i in range(count)]
            }
            self.save()
            self.fixture.with_suffix(".calls").unlink()
            result = await run(inputs)
            self.assertTrue(result["outputs"]["result"]["ok"])
            content = (self.root / OUTPUT).read_text()
            self.assertIn(f"distributions listed: `{count}`", content)
            self.assertEqual(
                self.fixture.with_suffix(".calls").read_text().splitlines(),
                ["begin", *(["yield"] * count), "exhausted"],
            )
        # Native provider error becomes nonzero child data; finish still runs.
        self.config["fail_at"] = 2
        self.save()
        self.fixture.with_suffix(".calls").unlink()
        before = (self.root / OUTPUT).read_bytes()
        for keep in [False, True]:
            inputs["context"]["keep_going"] = keep
            result = await run(inputs)
            self.assertEqual(result["status"], "accepted", result)
            output = result["outputs"]["result"]
            self.assertFalse(output["ok"])
            self.assertEqual(output["status"], "intent_run_failed")
            self.assertIn(
                "RuntimeError: metadata fixture failure",
                output["children"][0]["stderr"],
            )
            self.assertNotEqual(output["children"][0]["returncode"], 0)
            self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
            self.assertEqual((self.root / OUTPUT).read_bytes(), before)
        self.assertEqual(
            self.fixture.with_suffix(".calls").read_text().splitlines(),
            ["begin", "yield", "yield", "failed"] * 2,
        )
        self.config = {"packages": []}
        self.save()
        # Real mkdir/write failures propagate as failed children without retries.
        shutil.rmtree(self.root / "docs")
        (self.root / "docs").write_text("blocker")
        result = await run(inputs)
        self.assertIn(
            "NotADirectoryError", result["outputs"]["result"]["children"][0]["stderr"]
        )
        (self.root / "docs").unlink()
        (self.root / OUTPUT).mkdir(parents=True)
        result = await run(inputs)
        self.assertIn(
            "IsADirectoryError", result["outputs"]["result"]["children"][0]["stderr"]
        )
        for forged in ["registry", "match", "cursor"]:
            bad, changed = deepcopy(base), None
            bad["context"]["dry_run"] = True
            if forged == "registry":
                bad["registry"][ACTION]["command"] = ["forged-command"]
            elif forged == "match":
                bad["match"]["route_id"] = "forged.route"
                with self.assertRaises(ExecutionRejected):
                    await run(bad)
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_licenses_route_select",
                        {"state": hub.initialize_intent_state(), "match": bad["match"]},
                    )
                continue
            else:
                changed = deepcopy(document)
                changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                    "state"
                ] = {"literal": {"ok": True, "children": [{"ok": True}]}}
            result = await run(bad, changed)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
        unknown = deepcopy(base)
        unknown["registry"] = {}
        result = await run(unknown)
        # Admission is failure data; native final metadata packing subsequently
        # raises KeyError for a missing declaration. Preserve both boundaries.
        self.assertEqual(result["status"], "failed", result)
        self.assertIsNone(result["outputs"])
        self.assertEqual(result["calls"][-1]["operation"], "finish")
        with self.assertRaises(KeyError):
            original().run_intent_match(
                selected_match(MATCH), {}, hub.RunContext(), repository_root=self.root
            )
        child = await remote.call(
            "mathformer_licenses_route_run",
            {
                "action": ACTION,
                "registry": {},
                "context": vars(hub.RunContext()),
                "repository_root": str(self.root),
            },
        )
        self.assertEqual(
            child,
            {"child": {"ok": False, "status": "unknown_action", "action_id": ACTION}},
        )
        bounded = deepcopy(base)
        bounded["context"]["dry_run"] = True
        for limit in [1, 3, 4]:
            changed = deepcopy(document)
            changed["policy"]["limits"]["max_operation_calls"] = limit
            result = await run(bounded, changed)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]),
                limit,
            )
        changed = deepcopy(document)
        changed["flow"]["steps"][1]["until"] = {"literal": False}
        result = await run(bounded, changed)
        self.assertEqual(result["status"], "failed", result)
        self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:-1])
        for omitted in [False, True]:
            bounded["repository_root"] = None
            if omitted:
                bounded.pop("repository_root")
            result = await run(bounded)
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
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
