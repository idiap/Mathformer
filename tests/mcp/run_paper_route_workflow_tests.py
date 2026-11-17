#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Actual source steps, registered MCP and real Lunar/PRISM, on fixture inputs.

The selected paper route has no model/provider/compiler boundary. Its real
local Python leaves run only in temporary repositories. A separate deterministic
external compiler fixture checks native process failure semantics; no selected
production step, PRISM parser, checker, compiler or runtime is substituted.
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
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import tempfile
from types import SimpleNamespace
import unittest
import yaml

import mathformer as hub
from paper_route_tools import (
    ACTIONS,
    DEPENDENCIES,
    ROUTE,
    checked_registry,
    selected_match,
    check_state,
)
from paper_route_tree import (
    populate,
    reset_outputs,
    put,
    leaves,
    EVIDENCE,
    PLAN,
    AUDIT,
    CATALOG,
    FRAMEWORK,
    RFDE,
    OUTPUT,
    PACKET,
    GRAPH,
)
from reasoning_route_compiler import install as install_compiler
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_paper_workflow_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
AUTHORED = (
    "skills/control/workflow-contract-validator/references/paper-route.workflow.json"
)
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": list(ACTIONS)},
    "score": 31,
    "matched_terms": ["paper workflow", "evidence"],
}
REGISTRY = {
    key: hub.action_to_dict(hub.build_registry()[key])
    for key in (*ACTIONS, *DEPENDENCIES)
}
ORDER = [
    "initialize",
    "select_action",
    "run_child",
    "advance",
    "select_action",
    "run_child",
    "advance",
    "finish",
]


def original():
    scope = dict(vars(hub))
    exec((ROOT / "tests/mcp/fixtures/paper_route_original.py.txt").read_text(), scope)
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
            path=p,
            content=s,
            encoding="text",
            sha256=hashlib.sha256(s.encode()).hexdigest(),
        )
        for p, s in values.items()
    ]


def products(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in (root / OUTPUT).rglob("*")
        if p.is_file()
    }


class PaperRouteTests(unittest.TestCase):
    maxDiff = None

    def test_contract_generator_and_provenance(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(doc, json.loads((ROOT / AUTHORED).read_text()))
        spec = importlib.util.spec_from_file_location(
            "paper_route_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        self.assertEqual(normalizer.paper_route_descriptor(), doc)
        self.assertEqual(doc["id"], "route_paper_workflow_workflow")
        self.assertEqual(doc["aliases"], [ROUTE])
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 8},
        )
        self.assertEqual(
            doc["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertEqual(
            doc["policy"]["effects"]["filesystem"]["write"],
            ["artifacts/paper_skills/", "artifacts/workflow_hub/"],
        )
        self.assertTrue(
            any(
                row["path"] == "scripts/mathformer.py"
                and row["selector"] == "run_intent_match"
                for row in doc["provenance"]["sources"]
            )
        )
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        for name, op in doc["operations"].items():
            self.assertEqual(op["execution"]["mode"], "deterministic")
            self.assertEqual(
                op["execution"]["binding"]["target"], "mathformer_paper_route_" + name
            )
        native = checked_registry(REGISTRY)
        self.assertEqual(native[ACTIONS[0]].depends_on, DEPENDENCIES)
        self.assertFalse(native[ACTIONS[0]].command)
        self.assertEqual(native[ACTIONS[1]].command, ("{python}", CATALOG, "--json"))
        self.assertEqual(
            native[DEPENDENCIES[0]].command,
            ("{python}", EVIDENCE, "--output", PACKET, "--json"),
        )
        self.assertEqual(checked_registry({}), {})

    def test_original_entrypoint_and_shared_state(self):
        match, registry = selected_match(MATCH), checked_registry(REGISTRY)
        oracle = original()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            populate(root, ROOT)
            for dry, keep, bad in [
                (True, False, False),
                (False, False, False),
                (False, False, True),
                (False, True, True),
            ]:
                put(
                    root,
                    FRAMEWORK,
                    "Dashboard proves correctness.\n" if bad else "Fixture paper.\n",
                )
                observations, files = [], []
                for source in [oracle, hub]:
                    reset_outputs(root)
                    observations.append(
                        source.run_intent_match(
                            match,
                            registry,
                            hub.RunContext(dry_run=dry, keep_going=keep),
                            repository_root=root,
                        )
                    )
                    files.append(products(root))
                self.assertEqual(*observations)
                self.assertEqual(*files)
                self.assertEqual(
                    len(observations[0]["children"]), 1 if bad and not keep else 2
                )
        state = hub.initialize_intent_state()
        self.assertEqual(state, {"ok": True, "children": []})
        failed = {"ok": False, "marker": "retained"}
        updated, done = hub.advance_intent_state(
            state, failed, hub.RunContext(keep_going=True), 2
        )
        self.assertFalse(done)
        self.assertEqual(state["children"], [])
        self.assertEqual(updated, {"ok": False, "children": [failed]})
        final, done = hub.advance_intent_state(
            updated, {"ok": True}, hub.RunContext(keep_going=True), 2
        )
        self.assertTrue(done)
        self.assertFalse(final["ok"])
        self.assertEqual(hub.select_intent_action(updated, match), ACTIONS[1])
        with self.assertRaisesRegex(ValueError, "bounds"):
            check_state(final, selecting=True)
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            check_state({"ok": True, "children": [failed]})
        _, done = hub.advance_intent_state(state, {}, hub.RunContext(), 2)
        self.assertTrue(done)

    def test_native_dependency_guards_and_external_compiler_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            native = hub.build_registry()
            for keep in [False, True]:
                self.assertEqual(
                    hub.run_action("missing", native, hub.RunContext(keep_going=keep)),
                    {"ok": False, "status": "unknown_action", "action_id": "missing"},
                )
                self.assertEqual(
                    hub.run_action(
                        ACTIONS[0], native, hub.RunContext(), seen={ACTIONS[0]}
                    )["status"],
                    "dependency_cycle",
                )
                self.assertEqual(
                    hub.run_action(
                        ACTIONS[0], native, hub.RunContext(), extra_args=["--extra"]
                    )["status"],
                    "extra_args_for_sequence",
                )
                broken = dict(native)
                broken[ACTIONS[0]] = replace(
                    native[ACTIONS[0]], depends_on=(ACTIONS[0], "missing")
                )
                child = hub.run_action(
                    ACTIONS[0], broken, hub.RunContext(keep_going=keep)
                )
                self.assertFalse(child["ok"])
                self.assertEqual(
                    [c["status"] for c in child["children"]],
                    (
                        ["dependency_cycle", "unknown_action"]
                        if keep
                        else ["dependency_cycle"]
                    ),
                )
            # Only an external compiler boundary is replaced in this separate
            # generic controller test. The selected route below always runs its
            # real scripts and does not use this synthetic test action.
            saved = hub.subprocess
            try:
                for mode in ["success", "reject", "timeout", "write", "launch_error"]:
                    item = replace(
                        native[ACTIONS[1]],
                        command=("fixture-reasoning-compiler", mode),
                        required_paths=(),
                        timeout_seconds=3 if mode == "timeout" else None,
                    )
                    calls = install_compiler(hub, root)
                    if mode == "launch_error":
                        with self.assertRaisesRegex(OSError, "compiler launch failed"):
                            hub.run_action(
                                item.action_id,
                                {item.action_id: item},
                                hub.RunContext(),
                                repository_root=root,
                            )
                    else:
                        child = hub.run_action(
                            item.action_id,
                            {item.action_id: item},
                            hub.RunContext(),
                            repository_root=root,
                        )
                        self.assertEqual(child["ok"], mode == "success")
                        self.assertEqual(
                            child["status"],
                            {"write": "undeclared_writes", "timeout": "timeout"}.get(
                                mode, "completed"
                            ),
                        )
                        if mode == "success":
                            payload = json.loads(child["stdout"])
                            self.assertEqual(
                                payload["artifact"]["nodes"], ["input", "check"]
                            )
                            self.assertFalse(
                                payload["ok"]
                            )  # native exit code owns process success
                        elif mode == "reject":
                            self.assertEqual(child["returncode"], 7)
                        elif mode == "timeout":
                            self.assertEqual(
                                (child["stdout"], child["stderr"]),
                                ("partial", "deadline"),
                            )
                        elif mode == "write":
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                    self.assertEqual(
                        calls,
                        [{"argv": list(item.command), "timeout": item.timeout_seconds}],
                    )
                    (root / "undeclared.txt").unlink(missing_ok=True)
            finally:
                hub.subprocess = saved

    def test_registered_mcp_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            populate(root, ROOT)
            # Import the actual production registration. No service config or
            # credentials are loaded. The service write root is the fixture root.
            server = (
                'import sys;sys.dont_write_bytecode=True;sys.path.insert(0,"scripts");'
                "import mcp_server as s;s.apply_runtime_config(allowed_write_roots=["
                + repr(str(root))
                + "]);"
                's.mcp.run(transport="stdio")'
            )
            failure = None
            async with manager.open(
                "paper-route",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
            ) as remote:
                try:
                    await self.connected(remote, root)
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure is not None:
                raise failure
            reset_outputs(root)
            readonly_server = server.replace(
                "s.mcp.run(", "s._READONLY=True;s.mcp.run("
            )
            async with manager.open(
                "paper-route-readonly",
                StdioConfig(
                    command=sys.executable, args=["-c", readonly_server], cwd=str(ROOT)
                ),
                {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
            ) as remote:
                arguments = dict(
                    action_id=ACTIONS[0],
                    registry=REGISTRY,
                    context=vars(hub.RunContext()),
                    repository_root=str(root),
                )
                with self.assertRaises(Exception):
                    await remote.call("mathformer_paper_route_run_child", arguments)
                arguments["context"]["dry_run"] = True
                dry = await remote.call("mathformer_paper_route_run_child", arguments)
                self.assertTrue(dry["child"]["ok"])
                self.assertFalse(products(root))

    async def connected(self, remote, root):
        doc = yaml.safe_load(CONTRACT.read_text())
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(document, inventory=None):
            assets = snapshot(document)
            record = workflow_documents([DESCRIPTOR], assets)[0]
            self.assertTrue(record["validation"]["valid"], record)
            workflow = compile_workflow(
                "mcp:paper-route", record, tools if inventory is None else inventory
            )
            return workflow, assets

        workflow, assets = compile(doc)
        self.assertTrue(workflow["runnable"], workflow["diagnostics"])
        self.assertEqual(workflow["runtime_status"], "ready")
        self.assertTrue(workflow["prism_source"])
        self.assertTrue(workflow["runtime_source"])
        self.assertEqual(set(workflow["bindings"]), set(doc["operations"]))
        missing, _ = compile(
            doc, [t for t in tools if t["name"] != "mathformer_paper_route_run_child"]
        )
        self.assertFalse(missing["runnable"])
        self.assertTrue(missing["diagnostics"])

        async def authorize():
            pass

        base = {
            "match": MATCH,
            "registry": REGISTRY,
            "context": vars(hub.RunContext()),
            "repository_root": str(root),
        }

        async def run(inputs, changed=None):
            selected, received = compile(changed) if changed else (workflow, assets)
            self.assertTrue(selected["runnable"], selected["diagnostics"])
            return await execute(selected, received, inputs, remote, authorize)

        oracle = original()
        # Every source branch is driven by real manuscript/graph/filesystem
        # inputs. reset_outputs gives original and runtime identical evidence
        # snapshots, including the evidence regenerated on every dependency visit.
        for case, keep in [
            ("success", False),
            ("success", True),
            ("dry", False),
            ("framework", False),
            ("framework", True),
            ("rfde", False),
            ("catalogue", False),
            ("missing", False),
            ("missing", True),
            ("partial_write", False),
        ]:
            populate(root, ROOT)
            reset_outputs(root)
            if case == "framework":
                put(root, FRAMEWORK, "Dashboard proves correctness.\n")
            if case == "rfde":
                put(root, RFDE, "RFDE guarantees theorem correctness.\n")
            if case == "catalogue":
                put(root, GRAPH, "{broken JSON")
            if case == "missing":
                (root / EVIDENCE).unlink()
            inputs = deepcopy(base)
            inputs["context"].update(
                dry_run=case == "dry",
                keep_going=keep,
                write_report=True,
                allow_mutating=False,
            )

            def reset():
                reset_outputs(root)
                if case == "partial_write":
                    (root / OUTPUT / "paper_update_plan.json").mkdir(parents=True)

            reset()
            result = await run(inputs)
            actual_files = products(root)
            reset()
            expected = oracle.run_intent_match(
                selected_match(MATCH),
                checked_registry(REGISTRY),
                hub.RunContext(**inputs["context"]),
                repository_root=root,
            )
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(result["outputs"], {"result": expected}, case)
            self.assertEqual(actual_files, products(root), case)
            expected_order = (
                ORDER if len(expected["children"]) == 2 else ORDER[:4] + ["finish"]
            )
            self.assertEqual([c["operation"] for c in result["calls"]], expected_order)
            self.assertEqual(
                [c["tool"] for c in result["calls"]],
                ["mathformer_paper_route_" + op for op in expected_order],
            )
            self.assertEqual(expected["route"]["score"], MATCH["score"])
            self.assertEqual(expected["route"]["matched_terms"], MATCH["matched_terms"])
            self.assertTrue(result["runtime"]["effect_records"])
            self.assertTrue(result["runtime"]["provenance"])
            self.assertTrue(result["replay_artifacts"])
            self.assertFalse(
                (root / "artifacts/workflow_hub").exists()
            )  # reporting belongs to outer callers
            observed = list(leaves(expected))
            for leaf in observed:
                if "returncode" in leaf:
                    self.assertTrue(leaf["write_audit"]["ok"])
                    self.assertNotIn("timeout_seconds", leaf)
                    self.assertIsNone(leaf["action"]["timeout_seconds"])
            if case in ["success", "dry"]:
                self.assertTrue(expected["ok"])
                self.assertEqual(
                    [c["argv"][1] for c in observed],
                    [
                        EVIDENCE,
                        EVIDENCE,
                        PLAN,
                        EVIDENCE,
                        AUDIT,
                        EVIDENCE,
                        AUDIT,
                        CATALOG,
                    ],
                )
                if case == "dry":
                    self.assertFalse(actual_files)
                    self.assertTrue(all(c["status"] == "dry_run" for c in observed))
                else:
                    self.assertEqual(len(actual_files), 8)
                    packet = json.loads(actual_files[PACKET])
                    self.assertEqual(packet["feature_count"], 4)
                    self.assertEqual(len(packet["features"]), 4)
                    # Four separate captured invocations, even when the packet
                    # has identical content. The native builder does not list
                    # its own output as an evidence input.
                    summaries = [
                        json.loads(c["stdout"])
                        for c in observed
                        if c["argv"][1] == EVIDENCE
                    ]
                    self.assertEqual(len(summaries), 4)
                    self.assertTrue(
                        all(
                            s["output"] == str(root / PACKET)
                            and s["feature_count"] == 4
                            and s["missing_path_count"] == len(s["missing_paths"])
                            for s in summaries
                        )
                    )
                    plan = json.loads(actual_files[OUTPUT + "/paper_update_plan.json"])
                    self.assertEqual(plan["feature_count"], 4)
                    self.assertTrue(plan["paper_claim_delta"])
                    catalogue = json.loads(
                        actual_files[OUTPUT + "/workflow_catalog_for_paper.json"]
                    )
                    self.assertEqual(
                        [w["id"] for w in catalogue["workflows"]],
                        ["fixture-support", "preformalization-readiness-loop"],
                    )
                    self.assertEqual(
                        (
                            catalogue["core_workflow_count"],
                            catalogue["support_workflow_count"],
                        ),
                        (1, 1),
                    )
            else:
                self.assertFalse(expected["ok"])
                self.assertEqual(expected["status"], "intent_run_failed")
                if case == "framework":
                    self.assertEqual(len(expected["children"]), 2 if keep else 1)
                    self.assertEqual(
                        len(expected["children"][0]["children"]), 4 if keep else 3
                    )
                    audit = next(c for c in observed if c["argv"][1] == AUDIT)
                    self.assertEqual(audit["returncode"], 1)
                    findings = json.loads(audit["stdout"])["findings"]
                    self.assertEqual(
                        findings[0]["id"], "dashboard_correctness_overclaim"
                    )
                    if keep:
                        self.assertTrue(expected["children"][1]["ok"])
                if case == "partial_write":
                    self.assertIn(OUTPUT + "/paper_update_plan.md", actual_files)
                    self.assertNotIn(OUTPUT + "/paper_update_plan.json", actual_files)
                if case == "missing":
                    self.assertTrue(
                        expected["children"][0]["children"][0]["preflight_errors"]
                    )
                    self.assertEqual(
                        len(expected["children"][0]["children"]), 4 if keep else 1
                    )
                if case == "catalogue":
                    self.assertEqual(expected["children"][1]["returncode"], 1)

        populate(root, ROOT)
        reset_outputs(root)
        # Missing dependencies preserve ordinary unknown-action result data.
        for keep in [False, True]:
            inputs = deepcopy(base)
            del inputs["registry"][DEPENDENCIES[0]]
            inputs["context"]["keep_going"] = keep
            inputs["context"]["dry_run"] = True
            result = await run(inputs)
            self.assertEqual(result["status"], "accepted", result)
            output = result["outputs"]["result"]
            self.assertFalse(output["ok"])
            self.assertEqual(len(output["children"]), 2 if keep else 1)
            self.assertEqual(
                output["children"][0]["children"][0]["status"], "unknown_action"
            )
            self.assertEqual(len(output["children"][0]["children"]), 4 if keep else 1)
            # Missing route entries also fail dispatch as data, then the native
            # route-metadata serializer raises KeyError. Do not invent metadata
            # or a successful finish envelope at the transport boundary.
            inputs["registry"] = {}
            with self.assertRaises(KeyError):
                oracle.run_intent_match(
                    selected_match(MATCH),
                    {},
                    hub.RunContext(**inputs["context"]),
                    repository_root=root,
                )
            result = await run(inputs)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(result["calls"][-1]["operation"], "finish")
        # Forged declarations and out-of-bounds histories fail at real tools.
        for bad in ["registry", "match", "cursor"]:
            inputs = deepcopy(base)
            inputs["context"]["dry_run"] = True
            changed = None
            if bad == "registry":
                inputs["registry"][ACTIONS[0]]["depends_on"] = ["forged"]
            elif bad == "match":
                inputs["match"]["route"]["title"] = "forged"
            else:
                changed = deepcopy(doc)
                changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                    "state"
                ] = {"literal": {"ok": True, "children": [{"ok": True}, {"ok": True}]}}
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
        # Lunar owns the independent projection's hard bounds and budget.
        inputs = deepcopy(base)
        inputs["context"]["dry_run"] = True
        for budget in [1, 4, 7]:
            changed = deepcopy(doc)
            changed["policy"]["limits"]["max_operation_calls"] = budget
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]),
                budget,
            )
        for bound in [1, 2]:
            changed = deepcopy(doc)
            changed["flow"]["steps"][1]["max_iterations"] = bound
            changed["flow"]["steps"][1]["until"] = {"literal": False}
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                [c["operation"] for c in result["calls"]], ORDER[: 1 + 3 * bound]
            )
        # Required-path preflight stops before launch for an invalid mount.
        blocker = put(root, "not-a-directory", "fixture")
        invalid = deepcopy(base)
        invalid["repository_root"] = str(blocker)
        preflight = await run(invalid)
        self.assertEqual(preflight["status"], "accepted", preflight)
        self.assertFalse(preflight["outputs"]["result"]["ok"])
        # Service write root is enforced before any native action is visited.
        invalid["repository_root"] = str(root.parent / "outside-paper-fixture")
        denied = await run(invalid)
        self.assertEqual(denied["status"], "failed", denied)
        self.assertIsNone(denied["outputs"])
        self.assertFalse((root.parent / "outside-paper-fixture").exists())
        self.assertFalse(products(root))
        for omit in [False, True]:
            inputs = deepcopy(base)
            inputs["context"]["dry_run"] = True
            inputs["repository_root"] = None
            if omit:
                inputs.pop("repository_root")
            result = await run(inputs)
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(
                result["outputs"]["result"],
                hub.run_intent_match(
                    selected_match(MATCH),
                    checked_registry(REGISTRY),
                    hub.RunContext(dry_run=True),
                ),
            )


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
