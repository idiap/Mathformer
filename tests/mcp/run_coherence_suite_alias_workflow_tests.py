#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native oracle equivalence and actual registered MCP / Lunar / PRISM execution.

Only the external process boundary is substituted, in a separate test fixture.
The parser, checker, compiler, runtime, controller and audits run unchanged.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]

import asyncio
from copy import deepcopy
import hashlib
import json
import tempfile
import unittest
import yaml
import mathformer as hub
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

ALIAS = "physics-lib:coherence-suite"
SUITE = "mathformerphysicslib:coherence-suite"
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lib_coherence_suite_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/coherence-suite-alias-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])


def snapshot(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    paths = {row["path"] for row in document["provenance"]["sources"]} | {SCHEMA}
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(p, (ROOT / p).read_text()) for p in sorted(paths)
    ]


def oracle():
    scope = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/coherence_suite_alias_original.py.txt").read_text(),
        scope,
    )
    return scope["run_action"]


class CoherenceAliasTests(unittest.TestCase):
    def test_native_guards_state_and_frozen_entrypoint(self):
        registry = hub.build_registry()
        original = oracle()
        self.assertEqual(registry[ALIAS].depends_on, (SUITE,))
        self.assertEqual(len(registry[SUITE].depends_on), 9)
        self.assertFalse(registry[ALIAS].command)
        self.assertFalse(registry[SUITE].command)
        for action, seen, args, status in [
            ("missing", ["missing"], ["x"], "unknown_action"),
            (ALIAS, [ALIAS], ["x"], "dependency_cycle"),
            (ALIAS, [], ["x"], "extra_args_for_sequence"),
        ]:
            admission = hub.admit_action(action, registry, args, seen)
            self.assertEqual(admission["status"], status)
            self.assertEqual(
                hub.run_action(
                    action, registry, hub.RunContext(), seen=set(seen), extra_args=args
                ),
                original(
                    action, registry, hub.RunContext(), seen=set(seen), extra_args=args
                ),
            )
        for keep in [False, True]:
            for seen in [
                [],
                [ALIAS],
                [SUITE],
                *([dep] for dep in registry[SUITE].depends_on),
            ]:
                context = hub.RunContext(dry_run=True, keep_going=keep)
                self.assertEqual(
                    hub.run_action(ALIAS, registry, context, seen=set(seen)),
                    original(ALIAS, registry, context, seen=set(seen)),
                )
        admission = hub.admit_action(SUITE, registry, seen=[ALIAS, "caller"])
        state = hub.initialize_dependencies(admission)
        initial = deepcopy(state)
        for index in range(9):
            before = deepcopy(state)
            child = {"ok": index != 2, "ordinal": index}
            state, done = hub.advance_dependencies(
                registry[SUITE], state, child, hub.RunContext(keep_going=True)
            )
            self.assertEqual(before["index"], index)
            self.assertEqual(state["index"], index + 1)
            self.assertEqual(state["children"], before["children"] + [child])
            self.assertEqual(state["ancestry"], initial["ancestry"])
            self.assertEqual(state["dependencies_ok"], index < 2)
            self.assertEqual(done, index == 8)
        self.assertEqual(initial["children"], [])
        self.assertEqual(
            hub.finish_dependencies(registry[SUITE], state)["status"], "sequence_failed"
        )

    def test_registered_tools_compiler_and_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document["id"], "hub_physics_lib_coherence_suite_workflow")
        self.assertEqual(document["aliases"], [ALIAS])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 25},
        )
        self.assertTrue(
            any(
                row["path"] == "scripts/mathformer.py"
                and row["selector"]
                == "run_action (with build_registry and prepare_action)"
                for row in document["provenance"]["sources"]
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        authored = json.loads(
            (
                ROOT
                / "skills/control/workflow-contract-validator/references/coherence-suite-alias.workflow.json"
            ).read_text()
        )
        self.assertEqual(authored, document)
        manager = SessionManager()
        server_python = ROOT / ".venv/bin/python"
        self.assertTrue(
            server_python.exists(), "Mathformer MCP environment is required"
        )
        deps = hub.build_registry()[SUITE].depends_on
        for mode in ["success", "fail", "timeout", "write", "preflight", "exception"]:
            with tempfile.TemporaryDirectory(prefix="coherence-alias-") as directory:
                print("MCP/PRISM boundary scenario:", mode, flush=True)
                async with manager.open(
                    "coherence-alias",
                    StdioConfig(
                        command=str(server_python),
                        args=[
                            str(
                                ROOT
                                / "tests/mcp/fixtures/coherence_suite_alias_boundary_server.py"
                            ),
                            mode,
                            directory,
                        ],
                        cwd=str(ROOT),
                    ),
                    {},
                ) as remote:
                    failure = None
                    try:
                        tools = [
                            t.model_dump(by_alias=True, exclude_none=True)
                            for t in await remote.tools()
                        ]

                        def compile(doc, inventory=None):
                            assets = snapshot(doc)
                            selected = workflow_documents([DESCRIPTOR], assets)[0]
                            result = compile_workflow(
                                "mcp:coherence-alias",
                                selected,
                                tools if inventory is None else inventory,
                            )
                            return result, assets

                        compiled, assets = compile(document)
                        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                        self.assertTrue(compiled["runtime_source"])
                        self.assertEqual(
                            set(compiled["bindings"]), set(document["operations"])
                        )
                        if mode == "success":
                            self.assertFalse(
                                compile(
                                    document,
                                    [
                                        t
                                        for t in tools
                                        if t["name"]
                                        != "mathformer_coherence_alias_visit"
                                    ],
                                )[0]["runnable"]
                            )

                        async def authorize():
                            pass

                        async def run(
                            context, seen=None, extra_args=None, changed=None
                        ):
                            await remote.call("fixture_reset", {})
                            workflow, received = (
                                compile(changed) if changed else (compiled, assets)
                            )
                            self.assertTrue(
                                workflow["runnable"], workflow["diagnostics"]
                            )
                            values = {
                                "context": context,
                                "extra_args": extra_args or [],
                                "seen": seen or [],
                                "repository_root": directory,
                            }
                            result = await execute(
                                workflow, received, values, remote, authorize
                            )
                            ledger = (await remote.call("fixture_ledger", {}))["calls"]
                            return result, ledger

                        for keep in [False, True]:
                            context = vars(hub.RunContext(keep_going=keep))
                            result, ledger = await run(context)
                            if mode == "exception":
                                self.assertEqual(result["status"], "failed", result)
                                self.assertIsNone(result["outputs"])
                                self.assertEqual(
                                    [c["operation"] for c in result["calls"]],
                                    [
                                        "admit",
                                        "initialize",
                                        "admit",
                                        "initialize",
                                        "visit_leaf",
                                        "advance",
                                        "visit_leaf",
                                        "advance",
                                        "visit_leaf",
                                    ],
                                )
                                self.assertEqual(len(ledger), 3)
                                self.assertEqual(
                                    result["calls"][-1]["status"], "rejected"
                                )
                                continue
                            self.assertEqual(
                                result["status"], "accepted", result["calls"]
                            )
                            expected = await remote.call(
                                "fixture_original",
                                {"context": context, "extra_args": [], "seen": []},
                            )
                            self.assertEqual(result["outputs"], expected)
                            native = result["outputs"]["result"]
                            suite = native["children"][0]
                            count = 9 if mode == "success" or keep else 3
                            self.assertEqual(
                                [c["action"]["id"] for c in suite["children"]],
                                list(deps[:count]),
                            )
                            self.assertEqual(suite["ok"], mode == "success")
                            self.assertEqual(native["ok"], mode == "success")
                            self.assertEqual(
                                native["status"],
                                (
                                    "sequence_completed"
                                    if mode == "success"
                                    else "sequence_failed"
                                ),
                            )
                            self.assertEqual(len(result["calls"]), 7 + 2 * count)
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]],
                                ["admit", "initialize", "admit", "initialize"]
                                + ["visit_leaf", "advance"] * count
                                + ["finish", "advance", "finish"],
                            )
                            self.assertEqual(
                                [c["action"] for c in ledger],
                                (
                                    list(deps[:count])
                                    if mode != "preflight"
                                    else [d for d in deps[:count] if d != deps[2]]
                                ),
                            )
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                            if mode == "success":
                                self.assertFalse(
                                    json.loads(suite["children"][0]["stdout"])["ok"]
                                )
                                self.assertTrue(
                                    all(
                                        c["write_audit"]["ok"]
                                        for c in suite["children"]
                                    )
                                )
                                self.assertTrue(
                                    all(c["timeout"] is None for c in ledger)
                                )
                            elif mode == "preflight":
                                self.assertIn(
                                    "missing required path:",
                                    suite["children"][2]["preflight_errors"][0],
                                )
                                self.assertNotIn("returncode", suite["children"][2])
                            elif mode == "fail":
                                self.assertEqual(suite["children"][2]["returncode"], 7)
                                self.assertEqual(
                                    suite["children"][2]["stderr"],
                                    "deterministic compiler diagnostic",
                                )
                            elif mode == "timeout":
                                self.assertEqual(
                                    suite["children"][2]["status"], "timeout"
                                )
                                self.assertEqual(
                                    suite["children"][2]["stdout"], "partial"
                                )
                            elif mode == "write":
                                self.assertEqual(
                                    suite["children"][2]["status"], "undeclared_writes"
                                )
                                self.assertEqual(
                                    suite["children"][2]["write_audit"][
                                        "unexpected_paths"
                                    ],
                                    ["undeclared.txt"],
                                )
                        if mode == "success":
                            # Exercise alias rejection, nested rejection and leaf cycles
                            # through the graph, with the frozen source as oracle.
                            for keep, seen, args in [
                                (False, [ALIAS], ["bad"]),
                                (False, [], ["bad"]),
                                (False, [SUITE], []),
                                (True, [SUITE], []),
                                (False, [deps[2]], []),
                                (True, [deps[2]], []),
                                (False, ["caller"], []),
                            ]:
                                context = vars(
                                    hub.RunContext(dry_run=True, keep_going=keep)
                                )
                                result, ledger = await run(context, seen, args)
                                self.assertEqual(
                                    result["status"], "accepted", result["calls"]
                                )
                                self.assertEqual(ledger, [])
                                expected = await remote.call(
                                    "fixture_original",
                                    {
                                        "context": context,
                                        "extra_args": args,
                                        "seen": seen,
                                    },
                                )
                                self.assertEqual(result["outputs"], expected)
                            admission = await remote.call(
                                "mathformer_coherence_alias_admit",
                                {
                                    "action": "missing",
                                    "extra_args": ["bad"],
                                    "seen": ["missing"],
                                },
                            )
                            rejected = await remote.call(
                                "mathformer_coherence_alias_reject",
                                {"action": "missing", **admission},
                            )
                            self.assertEqual(
                                rejected["result"],
                                {
                                    "ok": False,
                                    "status": "unknown_action",
                                    "action_id": "missing",
                                },
                            )
                            # Observe immutable state transitions through real tools.
                            admission = await remote.call(
                                "mathformer_coherence_alias_admit",
                                {"action": SUITE, "extra_args": [], "seen": [ALIAS]},
                            )
                            state = (
                                await remote.call(
                                    "mathformer_coherence_alias_initialize", admission
                                )
                            )["state"]
                            for index in range(9):
                                before = deepcopy(state)
                                advanced = await remote.call(
                                    "mathformer_coherence_alias_advance",
                                    {
                                        "action": SUITE,
                                        "state": state,
                                        "child": {"ok": index != 2},
                                        "context": vars(
                                            hub.RunContext(keep_going=True)
                                        ),
                                    },
                                )
                                state = advanced["state"]
                                self.assertEqual(
                                    state["children"],
                                    before["children"] + [{"ok": index != 2}],
                                )
                                self.assertEqual(state["index"], index + 1)
                                self.assertEqual(state["dependencies_ok"], index < 2)
                                self.assertEqual(advanced["done"], index == 8)
                            context = vars(hub.RunContext(dry_run=True))
                            for budget in [4, 24]:
                                bounded = deepcopy(document)
                                bounded["policy"]["limits"][
                                    "max_operation_calls"
                                ] = budget
                                result, ledger = await run(context, changed=bounded)
                                self.assertEqual(result["status"], "failed", result)
                                self.assertIsNone(result["outputs"])
                                self.assertEqual(
                                    sum(
                                        bool(c.get("transport_call_performed"))
                                        for c in result["calls"]
                                    ),
                                    budget,
                                )
                                self.assertEqual(ledger, [])
                            short = deepcopy(document)
                            short["flow"]["steps"][2]["max_iterations"] = 2
                            result, ledger = await run(context, changed=short)
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(result["failure_disposition"], "fail")
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]],
                                [
                                    "admit",
                                    "initialize",
                                    "admit",
                                    "initialize",
                                    "visit_leaf",
                                    "advance",
                                    "visit_leaf",
                                    "advance",
                                ],
                            )
                            broken = deepcopy(document)
                            broken["flow"]["steps"][2]["body"]["cases"][0]["body"][
                                "steps"
                            ][0]["arguments"]["state"] = {
                                "literal": {
                                    "index": 9,
                                    "children": [],
                                    "dependencies_ok": True,
                                    "ancestry": [ALIAS, SUITE],
                                }
                            }
                            result, _ = await run(context, changed=broken)
                            self.assertEqual(result["status"], "failed", result)
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]],
                                [
                                    "admit",
                                    "initialize",
                                    "admit",
                                    "initialize",
                                    "visit_leaf",
                                ],
                            )
                            timed = deepcopy(document)
                            timed["policy"]["limits"]["wall_time_seconds"] = 1
                            workflow, received = compile(timed)

                            async def pending():
                                await asyncio.Event().wait()

                            with self.assertRaises(TimeoutError):
                                await execute(
                                    workflow,
                                    received,
                                    {
                                        "context": context,
                                        "extra_args": [],
                                        "seen": [],
                                        "repository_root": directory,
                                    },
                                    remote,
                                    pending,
                                )
                    except Exception as error:
                        failure = error
                if failure:
                    raise failure
        self.assertFalse(manager.active)


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    sys.exit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
