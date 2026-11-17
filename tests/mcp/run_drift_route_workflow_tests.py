#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native route fixtures through production MCP and Lunar/PRISM.

Only an isolated temporary repository contains executable fixture inputs. Its
monitor is the byte-identical native Python source, using the route's empty argv
tail. No production inputs, credentials, providers or theorem compilers are used.
There is no provider/compiler boundary in this route to substitute. The actual
PRISM parser, checker, compiler and runtime are exercised without substitution.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
PYTHON = LUNAR / ".venv/bin/python"
if PYTHON.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(PYTHON), [str(PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
SITES = [str(path) for path in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import asdict
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import yaml

import mathformer as hub
from drift_monitor_route_tools import ACTION, ROUTE, selected_match
from normalize_workflows_tools import source as normalizer
from mcp_connections.client import SessionManager
from mcp_connections.contracts import workflow_documents
from mcp_connections.execution import execute, ExecutionRejected
from mcp_connections.models import StdioConfig
from mcp_connections.workflow_compiler import compile_workflow

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_monitor_physics_lean_drift_workflow/workflow.yaml"
INTERFACE = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
MONITOR = "skills/physics-lean/physics-lean-drift-pathology-monitor/scripts/monitor_physics_lean_drift_pathologies.py"
CONTEXT = asdict(hub.RunContext())
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 17,
    "matched_terms": ["drift", "physics"],
}


def original():
    namespace = dict(vars(hub))
    path = ROOT / "tests/mcp/fixtures/drift_route_original.py.txt"
    exec(compile(path.read_text(), str(path), "exec"), namespace)
    return namespace["run_intent_match"]


def snapshot(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    files = {row["path"] for row in document["provenance"]["sources"]} | {INTERFACE}
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(path, (ROOT / path).read_text()) for path in sorted(files)
    ]


class DriftRouteTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        cls.temporary = tempfile.TemporaryDirectory(prefix="mathformer-drift-fixture-")
        cls.directory = Path(cls.temporary.name)
        cls.mount = cls.directory / "repository"
        target = cls.mount / MONITOR
        target.parent.mkdir(parents=True)
        target.write_bytes((ROOT / MONITOR).read_bytes())
        cls.empty = cls.directory / "missing-inputs"
        cls.empty.mkdir()
        cls.registry = {ACTION: hub.build_registry()[ACTION]}
        cls.projection = {
            key: hub.action_to_dict(value) for key, value in cls.registry.items()
        }
        spec = importlib.util.spec_from_file_location(
            "fixture_native_drift", ROOT / MONITOR
        )
        cls.monitor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.monitor)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_contract_identity_policy_provenance_and_generator(self):
        document = self.document
        self.assertEqual(document["id"], "route_monitor_physics_lean_drift_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(document["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertEqual(document["policy"]["resume"]["mode"], "none")
        self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 1)
        self.assertEqual(document["flow"]["steps"][1]["on_exhausted"], "fail")
        self.assertIn(
            "scripts/mathformer.py",
            [r["path"] for r in document["provenance"]["sources"]],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertEqual(normalizer().drift_monitor_route_descriptor(), document)
        self.assertIsNone(self.registry[ACTION].timeout_seconds)
        self.assertEqual(self.registry[ACTION].command, ("{python}", MONITOR))

    def test_native_and_frozen_controller_equivalence(self):
        match = selected_match(MATCH)
        for root, dry_run in (
            (self.empty, False),
            (self.mount, True),
            (self.mount, False),
        ):
            for keep_going in (False, True):
                with self.subTest(
                    root=root.name, dry_run=dry_run, keep_going=keep_going
                ):
                    context = hub.RunContext(dry_run=dry_run, keep_going=keep_going)
                    expected = original()(
                        match, self.registry, context, repository_root=root
                    )
                    actual = hub.run_intent_match(
                        match, self.registry, context, repository_root=root
                    )
                    self.assertEqual(actual, expected)
                    self.assertEqual(len(actual["children"]), 1)
                    self.assertEqual(actual["ok"], root != self.empty)
                    self.assertEqual(actual["route"]["score"], 17)
                    self.assertEqual(
                        actual["route"]["matched_terms"], MATCH["matched_terms"]
                    )
                    child = actual["children"][0]
                    self.assertEqual(child["argv"], [sys.executable, MONITOR])
                    if not dry_run and root == self.mount:
                        self.assertEqual(child["returncode"], 0)
                        self.assertEqual(child["stderr"], "")
                        self.assertTrue(child["write_audit"]["ok"])
                        self.assertEqual(json.loads(child["stdout"])["status"], "pass")
        # Admission is data, but packing a match with no registered metadata is
        # a native KeyError. The adapter must not invent a successful finish.
        child = hub.run_action(ACTION, {}, hub.RunContext(), repository_root=self.empty)
        self.assertEqual(
            child, {"ok": False, "status": "unknown_action", "action_id": ACTION}
        )
        with self.assertRaises(KeyError):
            original()(match, {}, hub.RunContext(), repository_root=self.empty)

    def test_monitor_scientific_outcomes_and_output_are_independent(self):
        m = self.monitor

        def report(source="", lean="", **packets):
            inputs = dict(
                source_text=source,
                lean_text=lean,
                type_packet={},
                assumption_packet={},
                unit_report={},
                semantics_report={},
                assumption_report={},
                dimension_report={},
            )
            inputs.update(packets)
            analysis = m.inspect_pack(**inputs)
            findings = m.apply_rules(analysis)
            self.assertEqual(analysis["findings"], [])
            self.assertEqual(m.summarize(analysis, findings), m.build_report(**inputs))
            return m.summarize(analysis, findings)

        self.assertEqual(report()["status"], "pass")
        warning = report(
            lean="theorem condition (x : Real) (hpos : 0 < x) : True := by trivial"
        )
        self.assertEqual(warning["status"], "warn")
        self.assertEqual(warning["category_counts"]["implicit_premise_selection"], 1)
        labeled = report(
            lean="theorem condition (x : Real) (hpos : 0 < x) : True := by trivial",
            assumption_packet={"assumptions": [{"status": "source-backed"}]},
        )
        self.assertEqual(labeled["category_counts"]["implicit_premise_selection"], 0)
        strategy = report(
            "Differentiate an integral.", "theorem alternate : True := by funext x"
        )
        self.assertEqual(strategy["category_counts"]["proof_strategy_substitution"], 1)
        self.assertEqual(strategy["status"], "warn")
        failed = report(
            "Quantum ket psi in Hilbert space; integrate the vector field.",
            "theorem bad (q p : Real) (h : q * p = p * q) : q * p = p * q := by simpa using h\n"
            "def scalarA : Real := 0\ndef scalarB : Real := 1",
            assumption_report={"findings": [{"code": "hidden_strengthening"}]},
        )
        self.assertEqual(failed["status"], "fail")
        self.assertGreater(failed["category_counts"]["notational_collapse"], 0)
        self.assertGreater(failed["category_counts"]["abstraction_elevation"], 0)
        self.assertGreater(failed["category_counts"]["implicit_premise_selection"], 0)
        self.assertFalse(failed["grounding_debt_report"]["ok"])
        debt_only = report(lean="abbrev Law (_ : Prop) : Prop := True")
        self.assertFalse(debt_only["grounding_debt_report"]["ok"])
        self.assertEqual(debt_only["status"], "pass")
        for value in (warning, failed):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(m.emit({}, value), 0)
            self.assertEqual(
                out.getvalue(), json.dumps(value, ensure_ascii=False, indent=2) + "\n"
            )
        options = vars(m.parse_args([]))
        self.assertFalse(options["self_test"])
        self.assertEqual(m.build_report(**m.load_inputs(options))["status"], "pass")
        # The CLI self-test branch remains separate; all its real assertions run.
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(m.main(["--self-test"]), 0)
        self.assertEqual(json.loads(out.getvalue())["status"], "fail")
        output = self.directory / "scientific-fail.json"
        self.assertEqual(m.emit({"output": str(output)}, failed), 0)
        self.assertEqual(json.loads(output.read_text()), failed)
        source = self.directory / "paper.txt"
        source.write_text("Quantum ket psi in Hilbert space.")
        lean = self.directory / "fixture.lean"
        lean.write_text("def scalar : Real := 0")
        critic = self.directory / "critic.json"
        critic.write_text(json.dumps({"findings": [{"code": "hidden_strengthening"}]}))
        with redirect_stdout(io.StringIO()):
            code = m.main(
                [
                    "--source-file",
                    str(source),
                    "--lean-file",
                    str(lean),
                    "--assumption-critic-report",
                    str(critic),
                    "--output",
                    str(output),
                ]
            )
        self.assertEqual(code, 0)
        emitted = json.loads(output.read_text())
        self.assertEqual(emitted["status"], "fail")
        self.assertEqual(
            emitted["prior_critic_codes"]["assumptions"], ["hidden_strengthening"]
        )
        critic.write_text("{invalid-json")
        with self.assertRaises(json.JSONDecodeError):
            m.load_inputs({"assumption_critic_report": str(critic)})

    def test_real_registered_mcp_lunar_execution_and_failures(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        # Import production registration without main(): no service configuration
        # or credential files are loaded, and no providers are configured.
        server = (
            'import sys;sys.dont_write_bytecode=True;sys.path.insert(0,"scripts");'
            f"sys.path.extend({SITES!r});"
            'from mcp_server import mcp;mcp.run(transport="stdio")'
        )
        failure = None
        async with manager.open(
            "drift",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile_document(document, inventory=None):
                    assets = snapshot(document)
                    selected = workflow_documents([DESCRIPTOR], assets)[0]
                    workflow = compile_workflow(
                        "mcp:drift", selected, tools if inventory is None else inventory
                    )
                    return workflow, assets

                workflow, assets = compile_document(self.document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(
                    set(workflow["bindings"]), set(self.document["operations"])
                )
                unavailable, _ = compile_document(self.document, [])
                self.assertFalse(unavailable["runnable"])
                default = await remote.call(
                    "mathformer_drift_route_dispatch",
                    {
                        "action_id": ACTION,
                        "context": dict(CONTEXT, dry_run=True),
                        "registry": self.projection,
                        "repository_root": None,
                    },
                )
                self.assertEqual(
                    default["child"],
                    hub.run_action(ACTION, self.registry, hub.RunContext(dry_run=True)),
                )

                async def authorize():
                    pass

                async def run(
                    root, context=None, registry=None, document=None, match=None
                ):
                    compiled, received = (
                        compile_document(document) if document else (workflow, assets)
                    )
                    inputs = {
                        "context": CONTEXT if context is None else context,
                        "match": MATCH if match is None else match,
                        "registry": self.projection if registry is None else registry,
                        "repository_root": str(root),
                    }
                    return await execute(compiled, received, inputs, remote, authorize)

                for root, dry_run in (
                    (self.empty, False),
                    (self.mount, True),
                    (self.mount, False),
                ):
                    for keep_going in (False, True):
                        context = dict(CONTEXT, dry_run=dry_run, keep_going=keep_going)
                        result = await run(root, context)
                        self.assertEqual(result["status"], "accepted", result)
                        expected = original()(
                            selected_match(MATCH),
                            self.registry,
                            hub.RunContext(**context),
                            repository_root=root,
                        )
                        self.assertEqual(result["outputs"], {"result": expected})
                        self.assertEqual(
                            [call["tool"] for call in result["calls"]],
                            [
                                "mathformer_drift_route_" + op
                                for op in (
                                    "initialize",
                                    "select",
                                    "dispatch",
                                    "advance",
                                    "finish",
                                )
                            ],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        self.assertEqual(
                            len(result["outputs"]["result"]["children"]), 1
                        )
                # Admission failure reaches advance, then native metadata packing
                # raises. Exactly one dispatch, no retry or recovery is invented.
                failed = await run(self.empty, registry={})
                self.assertEqual(failed["status"], "failed", failed)
                self.assertIsNone(failed["outputs"])
                self.assertEqual(len(failed["calls"]), 5)
                self.assertEqual(failed["calls"][-1]["status"], "rejected")
                admitted = await remote.call(
                    "mathformer_drift_route_dispatch",
                    {
                        "action_id": ACTION,
                        "context": CONTEXT,
                        "registry": {},
                        "repository_root": str(self.empty),
                    },
                )
                self.assertEqual(admitted["child"]["status"], "unknown_action")
                for keep_going in (False, True):
                    child = {"ok": False, "status": "fixture_failure"}
                    advanced = await remote.call(
                        "mathformer_drift_route_advance",
                        {
                            "state": {"ok": True, "children": []},
                            "child": child,
                            "context": dict(CONTEXT, keep_going=keep_going),
                        },
                    )
                    self.assertEqual(
                        advanced,
                        {"state": {"ok": False, "children": [child]}, "done": True},
                    )
                    with self.assertRaises(Exception):
                        await remote.call(
                            "mathformer_drift_route_select",
                            {"state": advanced["state"], "match": MATCH},
                        )
                # Service-level policy is still applied by the actual tools.
                malformed = deepcopy(self.projection)
                malformed[ACTION]["command"].append("--self-test")
                failed = await run(self.empty, registry=malformed)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(len(failed["calls"]), 3)
                forged = deepcopy(MATCH)
                forged["route"]["title"] = "caller-authored metadata"
                failed = await run(self.empty, match=forged)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(len(failed["calls"]), 2)
                # Exhaustion is unreachable for the admitted singleton. This
                # deliberate condition mutation verifies the real PRISM bound.
                exhausted = deepcopy(self.document)
                exhausted["flow"]["steps"][1]["until"] = {"literal": False}
                failed = await run(self.empty, document=exhausted)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(failed["failure_disposition"], "fail")
                self.assertEqual(len(failed["calls"]), 4)
                self.assertIsNone(failed["outputs"])
                bounded = deepcopy(self.document)
                bounded["policy"]["limits"]["max_operation_calls"] = 3
                failed = await run(self.empty, document=bounded)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in failed["calls"]
                    ),
                    3,
                )
                self.assertIn("budget", str(failed).lower())
                invalid = deepcopy(MATCH)
                invalid["route"]["action_ids"].append(ACTION)
                with self.assertRaises(ExecutionRejected):
                    await run(self.empty, match=invalid)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
